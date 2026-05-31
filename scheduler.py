"""
CaseMaster Pro X Bot — スケジューラ
毎日 0:30 JST に GitHub Actions で実行される。

今日の投稿枠3つをランダム選択し、Claude で本文を生成して
Supabase の x_post_queue テーブルに登録する。
日付シードで冪等（再実行しても重複しない）。
"""
import random
import sys
from datetime import date, datetime, timedelta, timezone

from config import TIME_WINDOWS, DAILY_POST_COUNT, CONTENT_TYPES
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from generator import generate_tweet_text

JST = timezone(timedelta(hours=9))


def today_jst() -> date:
    return datetime.now(JST).date()


def select_windows(today: date) -> list[dict]:
    """日付シードで DAILY_POST_COUNT 個の枠を選ぶ（冪等）"""
    seed = int(today.strftime("%Y%m%d"))
    rng = random.Random(seed)
    return rng.sample(TIME_WINDOWS, DAILY_POST_COUNT)


def random_time_in_window(window: dict, today: date, slot_index: int) -> datetime:
    """指定枠内のランダムな時刻（JST）を返す（日付＋スロットでシード）"""
    seed = int(today.strftime("%Y%m%d")) + slot_index * 1000
    rng = random.Random(seed)
    start_min = window["start"][0] * 60 + window["start"][1]
    end_min   = window["end"][0]   * 60 + window["end"][1]
    chosen_min = rng.randint(start_min, end_min)
    second = rng.randint(0, 59)
    return datetime(
        today.year, today.month, today.day,
        chosen_min // 60, chosen_min % 60, second,
        tzinfo=JST,
    )


def pick_content_type(today: date, slot_index: int) -> str:
    """重み付きでコンテンツタイプを選択（日付＋スロットでシード）"""
    seed = int(today.strftime("%Y%m%d")) + slot_index * 9999
    rng = random.Random(seed)
    types   = list(CONTENT_TYPES.keys())
    weights = list(CONTENT_TYPES.values())
    return rng.choices(types, weights=weights, k=1)[0]


def fetch_recent_tweets(sb, limit: int = 30) -> list[str]:
    """投稿済みツイートのテキストを新しい順に取得する"""
    result = (
        sb.table("x_post_queue")
        .select("text")
        .eq("status", "posted")
        .order("posted_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [row["text"] for row in result.data]


def window_of(dt: datetime) -> str | None:
    """与えられた時刻(JST)がどの TIME_WINDOWS 枠に属するかを返す（なければ None）"""
    minute = dt.hour * 60 + dt.minute
    for w in TIME_WINDOWS:
        start_min = w["start"][0] * 60 + w["start"][1]
        end_min   = w["end"][0]   * 60 + w["end"][1]
        if start_min <= minute <= end_min:
            return w["name"]
    return None


def schedule_today(dry_run: bool = False) -> None:
    today   = today_jst()
    windows = select_windows(today)

    print(f"[scheduler] {today} — 選択枠: {[w['name'] for w in windows]}")

    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # 既存行を確認し、「不足している枠だけ」を埋める（failed 行はカウントしない）
    # ※従来はステータス無視で1件でもあれば全枠スキップしていたため、
    #   過去の failed/再配置行が1件残ると残りの枠が永久に作られなかった。
    occupied_windows: set[str] = set()
    valid_count = 0
    if not dry_run:
        today_start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=JST).isoformat()
        today_end   = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=JST).isoformat()
        existing = (
            sb.table("x_post_queue")
            .select("scheduled_at,status")
            .gte("scheduled_at", today_start)
            .lte("scheduled_at", today_end)
            .execute()
        )
        for row in existing.data or []:
            if row.get("status") in ("pending", "posted"):
                valid_count += 1
                try:
                    dt = datetime.fromisoformat(row["scheduled_at"]).astimezone(JST)
                    wname = window_of(dt)
                    if wname:
                        occupied_windows.add(wname)
                except (ValueError, KeyError):
                    pass

        if valid_count >= DAILY_POST_COUNT:
            print(f"[scheduler] 今日は有効な投稿が {valid_count} 件（>= {DAILY_POST_COUNT}）。スキップ。")
            return
        if valid_count > 0:
            print(f"[scheduler] 今日は有効な投稿が {valid_count} 件のみ。不足分 {DAILY_POST_COUNT - valid_count} 件を補充。")

    # 過去ツイートを取得して重複回避に使う
    recent_tweets = fetch_recent_tweets(sb)
    print(f"[scheduler] 過去ツイート {len(recent_tweets)} 件を重複チェック用に取得")

    need = DAILY_POST_COUNT - valid_count
    records = []
    for i, window in enumerate(windows):
        if not dry_run and len(records) >= need:
            break
        # 既に有効な投稿で埋まっている枠はスキップ（重複回避）
        if window["name"] in occupied_windows:
            print(f"  [{window['name']}枠] 既に登録済み。スキップ。")
            continue

        scheduled_at = random_time_in_window(window, today, i)
        content_type = pick_content_type(today, i)

        print(f"  [{window['name']}枠] {scheduled_at.strftime('%H:%M:%S')} | type={content_type} | 生成中...")
        text = generate_tweet_text(content_type, recent_tweets=recent_tweets)
        char_count = len(text)
        print(f"    → {char_count}文字: {text[:60]}{'...' if char_count > 60 else ''}")

        # 生成したツイートも次の枠の重複チェック対象に追加
        recent_tweets.insert(0, text)

        if dry_run:
            print(f"    [DRY RUN] 登録スキップ")
            continue

        records.append({
            "content_type": content_type,
            "text": text,
            "scheduled_at": scheduled_at.isoformat(),
            "status": "pending",
        })

    if not dry_run and records:
        sb.table("x_post_queue").insert(records).execute()
        print(f"[scheduler] 完了: {len(records)} 件をキューに追加")
    elif dry_run:
        print(f"[scheduler] ドライラン完了: {len(windows)} 件を生成（未登録）")


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    schedule_today(dry_run=dry)
