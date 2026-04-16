"""
今日のpendingレコードを全削除し、不足分を140文字ルールで補充する
"""
import sys
import random
from datetime import date, datetime, timedelta, timezone

from config import (
    SUPABASE_URL, SUPABASE_SERVICE_KEY,
    TIME_WINDOWS, DAILY_POST_COUNT, CONTENT_TYPES,
)
from supabase import create_client
from generator import generate_tweet_text
from scheduler import select_windows, random_time_in_window, pick_content_type, fetch_recent_tweets

JST = timezone(timedelta(hours=9))
dry_run = "--dry" in sys.argv

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
today = datetime.now(JST).date()

today_start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=JST).isoformat()
today_end   = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=JST).isoformat()

print(f"[cleanup] 対象日: {today} (JST)")

# 現在のレコードを全確認
result = (
    sb.table("x_post_queue")
    .select("id, content_type, scheduled_at, status, text")
    .gte("scheduled_at", today_start)
    .lte("scheduled_at", today_end)
    .execute()
)
rows = result.data
print(f"[cleanup] 今日の全レコード: {len(rows)} 件")
for r in rows:
    print(f"  status={r['status']} type={r['content_type']} scheduled={r['scheduled_at']}")
    print(f"  text({len(r['text'])}文字): {r['text'][:60]}...")

# pending のみ削除
pending_rows = [r for r in rows if r["status"] == "pending"]
posted_rows  = [r for r in rows if r["status"] == "posted"]
print(f"\n[cleanup] pending={len(pending_rows)}件 / posted={posted_rows and len(posted_rows)}件")

if dry_run:
    print("[cleanup] [DRY RUN] 削除スキップ")
    sys.exit(0)

for r in pending_rows:
    sb.table("x_post_queue").delete().eq("id", r["id"]).execute()
    print(f"  削除: id={r['id'][:8]}... type={r['content_type']}")
print(f"[cleanup] 削除完了: {len(pending_rows)} 件")

# posted の件数を確認し、DAILY_POST_COUNT に足りない分だけ追加登録
already_posted = len(posted_rows)
need = DAILY_POST_COUNT - already_posted
print(f"\n[cleanup] 投稿済={already_posted}件 / 必要={DAILY_POST_COUNT}件 / 追加登録={need}件")

if need <= 0:
    print("[cleanup] 追加登録不要。終了。")
    sys.exit(0)

# 過去ツイートを重複回避用に取得
recent_tweets = fetch_recent_tweets(sb)
print(f"[cleanup] 過去ツイート {len(recent_tweets)} 件を重複チェック用に取得")

# 今日の全6枠から need 個を選択（日付シード + オフセットで冪等）
all_windows = select_windows(today)
# need 個取れない場合は残り枠から補充
if len(all_windows) < need:
    # 全6枠からランダムに追加
    all_windows = random.sample(TIME_WINDOWS, min(need, len(TIME_WINDOWS)))
windows_to_use = all_windows[:need]

records = []
for i, window in enumerate(windows_to_use):
    scheduled_at = random_time_in_window(window, today, i + 10)  # offset 10で既存と重複しないシード
    content_type = pick_content_type(today, i + 10)

    print(f"  [{window['name']}枠] {scheduled_at.strftime('%H:%M')} JST | type={content_type} | 生成中...")
    text = generate_tweet_text(content_type, recent_tweets=recent_tweets)
    recent_tweets.insert(0, text)
    print(f"    → {len(text)}文字: {text[:60]}{'...' if len(text) > 60 else ''}")

    records.append({
        "content_type": content_type,
        "text": text,
        "scheduled_at": scheduled_at.isoformat(),
        "status": "pending",
    })

sb.table("x_post_queue").insert(records).execute()
print(f"\n[cleanup] 完了: {len(records)} 件を新ルール(140文字)でキューに追加")
