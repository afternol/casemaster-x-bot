"""
CaseMaster Pro X Bot — スケジューラ
毎日 0:30 JST に GitHub Actions で実行される。

今日の投稿 1 件（POST_TIME_JST = 20:00 JST 固定）を Claude で生成し、
Supabase の x_post_queue テーブルに登録する。
- 今日の pending/posted が既に DAILY_POST_COUNT 件あれば何もしない（冪等・成功扱い）
- コンテンツタイプは日付シードで決定。PROMO_WEEKDAY（日曜）は promo 固定
- 検証に通らなかった／生成に失敗した場合は failed 行として記録し、終了コード 1
"""
import random
import sys
from datetime import date, datetime, timedelta, timezone

from config import (
    CONTENT_TYPES, DAILY_POST_COUNT, POST_TIME_JST, PROMO_WEEKDAY, STALE_AFTER_HOURS,
    SUPABASE_SERVICE_KEY, SUPABASE_URL,
)

JST = timezone(timedelta(hours=9))


def today_jst() -> date:
    return datetime.now(JST).date()


def slot_time(day: date) -> datetime:
    """その日の投稿予定時刻（JST・固定）"""
    hour, minute = POST_TIME_JST
    return datetime(day.year, day.month, day.day, hour, minute, 0, tzinfo=JST)


def pick_content_type(day: date) -> str:
    """PROMO_WEEKDAY は promo、それ以外は promo を除く重み付き抽選（日付シードで冪等）"""
    if day.weekday() == PROMO_WEEKDAY:
        return "promo"
    rng = random.Random(int(day.strftime("%Y%m%d")))
    pool = {t: w for t, w in CONTENT_TYPES.items() if t != "promo" and w > 0}
    return rng.choices(list(pool.keys()), weights=list(pool.values()), k=1)[0]


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


def count_valid_rows(sb, day: date) -> int:
    """その日（JST）の pending/posted 件数（failed は数えない）"""
    day_start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=JST).isoformat()
    day_end   = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=JST).isoformat()
    rows = (
        sb.table("x_post_queue")
        .select("id")
        .in_("status", ["pending", "posted"])
        .gte("scheduled_at", day_start)
        .lte("scheduled_at", day_end)
        .execute()
    ).data or []
    return len(rows)


def _record_failure(sb, content_type: str, text: str, scheduled_at: datetime, error: str) -> None:
    """生成失敗を failed 行として残す（GitHub Actions 上の失敗と DB 双方で追えるように）"""
    try:
        sb.table("x_post_queue").insert({
            "content_type": content_type,
            "text": text or "",
            "scheduled_at": scheduled_at.isoformat(),
            "status": "failed",
            "error": error[:2000],
        }).execute()
    except Exception as e:  # 記録失敗でも本来のエラーを優先して非ゼロ終了させる
        print(f"[scheduler] failed 行の記録にも失敗: {type(e).__name__}: {e}")


def schedule_today(dry_run: bool = False) -> int:
    """終了コードを返す（0=成功/対象なし、1=生成失敗）"""
    from generator import TweetValidationError, generate_tweet_text

    today = today_jst()
    scheduled_at = slot_time(today)
    content_type = pick_content_type(today)
    print(f"[scheduler] {today} — 予定 {scheduled_at.strftime('%H:%M')} JST | type={content_type}")

    if datetime.now(JST) >= scheduled_at + timedelta(hours=STALE_AFTER_HOURS):
        print("[scheduler] 本日の投稿時刻を大きく過ぎているため生成しません（stale 回避）")
        return 0

    sb = None
    if not dry_run:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        valid = count_valid_rows(sb, today)
        if valid >= DAILY_POST_COUNT:
            print(f"[scheduler] 今日は有効な投稿が {valid} 件（>= {DAILY_POST_COUNT}）。スキップ。")
            return 0

    recent_tweets = fetch_recent_tweets(sb) if sb else []
    print(f"[scheduler] 過去ツイート {len(recent_tweets)} 件を重複チェック用に取得")

    try:
        text = generate_tweet_text(content_type, recent_tweets=recent_tweets)
    except TweetValidationError as e:
        msg = f"[invalid] 最大リトライ後も検証NG: {'; '.join(e.errors)}"
        print(f"[scheduler] {msg}")
        if sb:
            _record_failure(sb, content_type, e.last_text, scheduled_at, msg)
        return 1
    except Exception as e:
        msg = f"[gen_error] {type(e).__name__}: {e}"
        print(f"[scheduler] 生成エラー: {msg}")
        if sb:
            _record_failure(sb, content_type, "", scheduled_at, msg)
        return 1

    print(f"    → {len(text)}文字: {text[:60]}{'...' if len(text) > 60 else ''}")

    if dry_run:
        print("[scheduler] [DRY RUN] 登録スキップ")
        return 0

    sb.table("x_post_queue").insert({
        "content_type": content_type,
        "text": text,
        "scheduled_at": scheduled_at.isoformat(),
        "status": "pending",
    }).execute()
    print("[scheduler] 完了: 1 件をキューに追加")
    return 0


if __name__ == "__main__":
    sys.exit(schedule_today(dry_run="--dry" in sys.argv))
