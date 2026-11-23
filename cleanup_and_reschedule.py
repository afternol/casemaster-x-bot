"""
今日の pending レコードを削除し、scheduler と同じルール（1日1件・20:00 JST）で作り直す。
使い方: python cleanup_and_reschedule.py [--dry]
"""
import sys
from datetime import datetime, timedelta, timezone

from config import SUPABASE_SERVICE_KEY, SUPABASE_URL
from scheduler import schedule_today

JST = timezone(timedelta(hours=9))


def main() -> int:
    from supabase import create_client

    dry_run = "--dry" in sys.argv
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    today = datetime.now(JST).date()
    today_start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=JST).isoformat()
    today_end   = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=JST).isoformat()

    rows = (
        sb.table("x_post_queue")
        .select("id, content_type, scheduled_at, status")
        .gte("scheduled_at", today_start)
        .lte("scheduled_at", today_end)
        .execute()
    ).data or []
    print(f"[cleanup] {today} (JST) の全レコード: {len(rows)} 件")
    pending = [r for r in rows if r["status"] == "pending"]
    for r in rows:
        print(f"  status={r['status']} type={r['content_type']} scheduled={r['scheduled_at']}")

    if dry_run:
        print(f"[cleanup] [DRY RUN] pending {len(pending)} 件の削除をスキップ")
        return schedule_today(dry_run=True)

    for r in pending:
        sb.table("x_post_queue").delete().eq("id", r["id"]).eq("status", "pending").execute()
    print(f"[cleanup] pending 削除: {len(pending)} 件")
    return schedule_today(dry_run=False)


if __name__ == "__main__":
    sys.exit(main())
