"""
402 Payment Required などで status=failed になった過去レコードを
今後の空き枠 (TIME_WINDOWS) に再分散して status=pending に戻す。

Daily Schedule とは別枠（slot_index offset を変える）に挿し込むので
通常スケジュールと共存できる。

使い方:
  python requeue_failed.py --dry        # ドライラン
  python requeue_failed.py              # 本実行
  python requeue_failed.py --max 3      # 1日あたり最大追加件数 (default 2)
  python requeue_failed.py --days 30    # 直近N日分のfailedを対象 (default 60)
"""
import sys
import random
from datetime import date, datetime, timedelta, timezone

from config import (
    SUPABASE_URL, SUPABASE_SERVICE_KEY,
    TIME_WINDOWS, DAILY_POST_COUNT,
)
from supabase import create_client
from scheduler import random_time_in_window, select_windows

JST = timezone(timedelta(hours=9))


def parse_args():
    dry      = "--dry" in sys.argv
    max_per_day = 2
    days     = 60
    for i, a in enumerate(sys.argv):
        if a == "--max" and i + 1 < len(sys.argv):
            max_per_day = int(sys.argv[i + 1])
        if a == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])
    return dry, max_per_day, days


def get_used_slots(sb, start_date: date, end_date: date) -> dict[date, set[tuple[int, int]]]:
    """指定範囲内の pending/posted レコードのスケジュール時刻 (h, m) を日付別に取得"""
    start_iso = datetime(start_date.year, start_date.month, start_date.day,
                         0, 0, 0, tzinfo=JST).isoformat()
    end_iso   = datetime(end_date.year, end_date.month, end_date.day,
                         23, 59, 59, tzinfo=JST).isoformat()
    rows = (
        sb.table("x_post_queue")
        .select("scheduled_at, status")
        .in_("status", ["pending", "posted"])
        .gte("scheduled_at", start_iso)
        .lte("scheduled_at", end_iso)
        .execute()
    ).data
    used: dict[date, set[tuple[int, int]]] = {}
    for r in rows:
        dt = datetime.fromisoformat(r["scheduled_at"]).astimezone(JST)
        d  = dt.date()
        used.setdefault(d, set()).add((dt.hour, dt.minute))
    return used


MORNING_WINDOWS = [w for w in TIME_WINDOWS if w["name"] in ("朝A", "朝B")]


def find_next_free_slot(start_day: date, max_per_day: int,
                        used: dict[date, set[tuple[int, int]]],
                        added_today: dict[date, int]) -> tuple[date, dict, int]:
    """
    start_day 以降で、当日追加件数が max_per_day 未満で、
    朝A or 朝B からランダム選択した未使用枠を返す。
    日付シードでランダム化するので冪等。
    """
    d = start_day
    attempts = 0
    while attempts < 365:
        already = len(used.get(d, set())) + added_today.get(d, 0)
        # その日に既に DAILY_POST_COUNT + max_per_day 件以上あれば次の日
        if already >= DAILY_POST_COUNT + max_per_day:
            d += timedelta(days=1)
            attempts += 1
            continue
        # 朝A/朝B の順序を日付シードでランダム化
        rng = random.Random(int(d.strftime("%Y%m%d")) + 7777)
        windows_shuffled = MORNING_WINDOWS[:]
        rng.shuffle(windows_shuffled)
        # 既に使われた枠を避けて選ぶ
        for offset in range(20, 100):  # offset 20+ で通常スケジュールと衝突回避
            for window in windows_shuffled:
                t = random_time_in_window(window, d, offset)
                key = (t.hour, t.minute)
                if key not in used.get(d, set()):
                    return d, window, offset
        # その日の全枠が埋まったら次の日
        d += timedelta(days=1)
        attempts += 1
    raise RuntimeError("空き枠が見つかりませんでした")


def main():
    dry, max_per_day, days = parse_args()
    print(f"[requeue] dry_run={dry} max_per_day={max_per_day} days={days}")

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # 1) failed レコードを取得
    cutoff = (datetime.now(JST) - timedelta(days=days)).isoformat()
    failed = (
        sb.table("x_post_queue")
        .select("id, content_type, scheduled_at, text, error")
        .eq("status", "failed")
        .gte("scheduled_at", cutoff)
        .order("scheduled_at")
        .execute()
    ).data
    print(f"[requeue] failed レコード: {len(failed)} 件")
    if not failed:
        print("[requeue] 対象なし。終了。")
        return

    for r in failed[:5]:
        print(f"  - id={r['id'][:8]} type={r['content_type']} "
              f"sched={r['scheduled_at']} text={r['text'][:30]}...")
    if len(failed) > 5:
        print(f"  ... 他 {len(failed) - 5} 件")

    # 2) 既存枠のマッピングを取得（今日 ~ 今日+60日）
    today = datetime.now(JST).date()
    end_day = today + timedelta(days=60)
    used = get_used_slots(sb, today, end_day)
    print(f"[requeue] 既存枠マップ取得: "
          f"{sum(len(v) for v in used.values())} 件 / {len(used)} 日")

    # 3) 各 failed を空き枠に再割当
    added_today: dict[date, int] = {}
    plan = []   # (id, new_scheduled_at_iso, window_name, day)
    next_day = today

    for r in failed:
        d, window, offset = find_next_free_slot(next_day, max_per_day, used, added_today)
        t = random_time_in_window(window, d, offset)
        # 当日が今より過去ならスキップ（次の日へ）
        now = datetime.now(JST)
        while t <= now + timedelta(minutes=10):
            offset += 1
            t = random_time_in_window(window, d, offset)
            if offset > 200:
                d += timedelta(days=1)
                offset = 20
                t = random_time_in_window(window, d, offset)

        used.setdefault(d, set()).add((t.hour, t.minute))
        added_today[d] = added_today.get(d, 0) + 1
        plan.append((r["id"], t.isoformat(), window["name"], d, r["content_type"], r["text"]))
        # 次の探索開始日: 当日件数が上限なら翌日、そうでなければ同日続行
        if added_today.get(d, 0) >= max_per_day:
            next_day = d + timedelta(days=1)
        else:
            next_day = d

    # 4) プラン表示
    print(f"\n[requeue] 再分散プラン:")
    for pid, sched, wname, d, ctype, text in plan[:30]:
        print(f"  {d} {sched[11:16]} JST [{wname}枠] type={ctype} "
              f"id={pid[:8]} text={text[:30]}...")
    if len(plan) > 30:
        print(f"  ... 他 {len(plan) - 30} 件")

    print(f"\n[requeue] 合計 {len(plan)} 件、{len(set(p[3] for p in plan))} 日間に分散")

    if dry:
        print("[requeue] [DRY RUN] DB更新スキップ")
        return

    # 5) DB更新
    print(f"\n[requeue] DB更新中...")
    for pid, sched, _, _, _, _ in plan:
        sb.table("x_post_queue").update({
            "status": "pending",
            "scheduled_at": sched,
            "error": None,
        }).eq("id", pid).execute()
    print(f"[requeue] 完了: {len(plan)} 件を pending に戻しました")


if __name__ == "__main__":
    main()
