"""
1件生成して即投稿するスクリプト
コンテンツタイプをランダムに選択し、生成→Tweepy投稿→Supabase記録
"""
import sys
import random
from datetime import datetime, timezone

import tweepy

from config import (
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
    SUPABASE_URL, SUPABASE_SERVICE_KEY, CONTENT_TYPES,
)
from generator import generate_tweet_text, twitter_weight
from supabase import create_client

dry_run = "--dry" in sys.argv

# コンテンツタイプを重み付きでランダム選択
types   = list(CONTENT_TYPES.keys())
weights = list(CONTENT_TYPES.values())
content_type = random.choices(types, weights=weights, k=1)[0]

print(f"[generate_and_post] type={content_type}")

# 過去ツイートを取得して重複回避
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
result = (
    sb.table("x_post_queue")
    .select("text")
    .eq("status", "posted")
    .order("posted_at", desc=True)
    .limit(30)
    .execute()
)
recent_tweets = [r["text"] for r in result.data]
print(f"[generate_and_post] 過去ツイート {len(recent_tweets)} 件を重複チェック用に取得")

# ツイート生成
text = generate_tweet_text(content_type, recent_tweets=recent_tweets)
w = twitter_weight(text)
print(f"\n生成テキスト（{len(text)}文字 / Twitter重み{w}）:\n{text}\n")

if dry_run:
    print("[DRY RUN] 投稿スキップ")
    sys.exit(0)

# 投稿
client = tweepy.Client(
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True,
)

try:
    response = client.create_tweet(text=text, user_auth=True)
    tweet_id = str(response.data["id"])
    now = datetime.now(timezone.utc).isoformat()
    print(f"✅ 投稿成功: tweet_id={tweet_id}")
    print(f"URL: https://x.com/casemaster_pro/status/{tweet_id}")

    # Supabase に記録
    sb.table("x_post_queue").insert({
        "content_type": content_type,
        "text": text,
        "scheduled_at": now,
        "status": "posted",
        "tweet_id": tweet_id,
        "posted_at": now,
    }).execute()
    print("✅ Supabase に記録完了")

except tweepy.TweepyException as e:
    print(f"❌ 投稿失敗: {e}")
    if hasattr(e, "response") and e.response is not None:
        print(f"response_body: {e.response.text}")
    sys.exit(1)
