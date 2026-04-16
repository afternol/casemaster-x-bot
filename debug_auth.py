"""
認証診断スクリプト v2
- 認証確認
- Supabase から pending レコードを取得してテキストを検査
- 実際に投稿して 403 の原因を特定
"""
import sys
import tweepy
from config import (
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
    SUPABASE_URL, SUPABASE_SERVICE_KEY,
)

dry_run = "--dry" in sys.argv

print("=" * 60)
print("[debug] 認証情報プレフィックス確認")
print(f"  X_API_KEY:             {X_API_KEY[:6]}...")
print(f"  X_API_SECRET:          {X_API_SECRET[:6]}...")
print(f"  X_ACCESS_TOKEN:        {X_ACCESS_TOKEN[:6]}...")
print(f"  X_ACCESS_TOKEN_SECRET: {X_ACCESS_TOKEN_SECRET[:6]}...")
print("=" * 60)

client = tweepy.Client(
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True,
)

# Step 1: 認証確認
print("\n[Step1] get_me() — 認証ユーザー確認")
try:
    me = client.get_me()
    print(f"  ✅ 認証成功: @{me.data.username} (id={me.data.id})")
except tweepy.TweepyException as e:
    print(f"  ❌ 認証失敗: {e}")
    sys.exit(1)

# Step 2: Supabase から pending レコードを取得して検査
print("\n[Step2] Supabase pending レコード取得・テキスト検査")
from supabase import create_client
from datetime import datetime, timezone

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
result = (
    sb.table("x_post_queue")
    .select("*")
    .eq("status", "pending")
    .order("scheduled_at")
    .limit(3)
    .execute()
)
rows = result.data
print(f"  pending件数: {len(rows)}")

for row in rows:
    text = row["text"]
    print(f"\n  --- id={row['id'][:8]}... type={row['content_type']} scheduled={row['scheduled_at']} ---")
    print(f"  len(text)={len(text)}")
    print(f"  repr(全文)={repr(text)}")

    # 問題のある文字チェック
    stripped = text.strip()
    if stripped != text:
        print(f"  ⚠️  前後に空白/改行あり（{len(text) - len(stripped)}文字差）")
    if '\r' in text:
        print(f"  ⚠️  \\r (CR) が含まれている")
    if '\x00' in text:
        print(f"  ⚠️  null バイトが含まれている")
    if len(text) > 280:
        print(f"  ⚠️  280文字超過: {len(text)}文字")

# Step 3: pending の最初のレコードを実際に投稿テスト
if rows:
    target = rows[0]
    text = target["text"].strip()
    print(f"\n[Step3] pending最初のレコードを投稿テスト（dry_run={dry_run}）")
    print(f"  対象: type={target['content_type']} scheduled={target['scheduled_at']}")
    print(f"  テキスト({len(text)}文字): {text[:100]}...")

    if dry_run:
        print("  [DRY RUN] 投稿スキップ")
    else:
        try:
            response = client.create_tweet(text=text, user_auth=True)
            tweet_id = response.data["id"]
            print(f"  ✅ 投稿成功: tweet_id={tweet_id}")
            print(f"  URL: https://x.com/casemaster_pro/status/{tweet_id}")

            # Supabase を更新
            from datetime import datetime, timezone
            sb.table("x_post_queue").update({
                "status": "posted",
                "tweet_id": str(tweet_id),
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "error": None,
            }).eq("id", target["id"]).execute()
            print("  ✅ Supabase status → posted に更新")

        except tweepy.TweepyException as e:
            print(f"  ❌ 投稿失敗: {e}")
            if hasattr(e, "api_codes"):
                print(f"  api_codes: {e.api_codes}")
            if hasattr(e, "api_messages"):
                print(f"  api_messages: {e.api_messages}")
            if hasattr(e, "response") and e.response is not None:
                print(f"  status_code: {e.response.status_code}")
                print(f"  response_body: {e.response.text}")
else:
    print("\n[Step3] pending レコードなし — スキップ")
