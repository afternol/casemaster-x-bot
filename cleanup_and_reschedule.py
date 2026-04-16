"""
今日のpendingレコードを全削除し、schedule.pyを再実行して140文字ルールで再登録する
"""
import sys
from datetime import datetime, timedelta, timezone

from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from supabase import create_client

JST = timezone(timedelta(hours=9))
dry_run = "--dry" in sys.argv

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
today = datetime.now(JST).date()

today_start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=JST).isoformat()
today_end   = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=JST).isoformat()

print(f"[cleanup] 対象日: {today} (JST)")
print(f"[cleanup] 範囲: {today_start} 〜 {today_end}")

# 削除対象を確認
result = (
    sb.table("x_post_queue")
    .select("id, content_type, scheduled_at, status, text")
    .gte("scheduled_at", today_start)
    .lte("scheduled_at", today_end)
    .execute()
)
rows = result.data
print(f"[cleanup] 今日のレコード: {len(rows)} 件")
for r in rows:
    print(f"  status={r['status']} type={r['content_type']} scheduled={r['scheduled_at']}")
    print(f"  text({len(r['text'])}文字): {r['text'][:60]}...")

# pendingのみ削除（postedは残す）
pending_rows = [r for r in rows if r["status"] == "pending"]
print(f"\n[cleanup] 削除対象(pending): {len(pending_rows)} 件")

if not pending_rows:
    print("[cleanup] 削除対象なし。終了。")
    sys.exit(0)

if dry_run:
    print("[cleanup] [DRY RUN] 削除スキップ")
    sys.exit(0)

for r in pending_rows:
    sb.table("x_post_queue").delete().eq("id", r["id"]).execute()
    print(f"  削除: id={r['id'][:8]}... type={r['content_type']}")

print(f"[cleanup] 削除完了: {len(pending_rows)} 件")
print("\n[cleanup] scheduler.py を実行して新ルールで再登録します...")

# scheduler を直接呼び出す
import scheduler as sched
sched.schedule_today(dry_run=False)
