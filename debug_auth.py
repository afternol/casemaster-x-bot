"""
認証診断スクリプト
- どのアカウントとして認証されているか確認
- 実際に投稿できるか確認（Consumer Key+Secret と Access Token+Secret の組み合わせ検証）
"""
import sys
import tweepy
from config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET

print("=" * 50)
print("[debug] 認証情報の先頭4文字確認")
print(f"  X_API_KEY prefix:             {X_API_KEY[:4]}...")
print(f"  X_API_SECRET prefix:          {X_API_SECRET[:4]}...")
print(f"  X_ACCESS_TOKEN prefix:        {X_ACCESS_TOKEN[:4]}...")
print(f"  X_ACCESS_TOKEN_SECRET prefix: {X_ACCESS_TOKEN_SECRET[:4]}...")
print("=" * 50)

client = tweepy.Client(
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True,
)

# Step 1: 認証ユーザー確認（読み取り）
print("\n[Step1] get_me() — 認証ユーザー確認")
try:
    me = client.get_me()
    print(f"  ✅ 認証成功: id={me.data.id}, name={me.data.name}, username={me.data.username}")
except tweepy.TweepyException as e:
    print(f"  ❌ 失敗: {e}")
    if hasattr(e, "api_codes"):
        print(f"  api_codes: {e.api_codes}")
    if hasattr(e, "response") and e.response is not None:
        print(f"  response: {e.response.text[:300]}")
    sys.exit(1)

# Step 2: user_auth=True で投稿テスト
print("\n[Step2] create_tweet(user_auth=True) — 投稿テスト")
dry_run = "--dry" in sys.argv
test_text = "ケース面接で一番重要なのは「何を解くか」を定義すること。冒頭15秒の問いの言語化が通過率を大きく左右する。 #ケース面接"

if dry_run:
    print(f"  [DRY RUN] テキスト({len(test_text)}文字): {test_text}")
else:
    try:
        response = client.create_tweet(text=test_text, user_auth=True)
        tweet_id = response.data["id"]
        print(f"  ✅ 投稿成功: tweet_id={tweet_id}")
        print(f"  URL: https://x.com/i/web/status/{tweet_id}")
    except tweepy.TweepyException as e:
        print(f"  ❌ 投稿失敗: {e}")
        if hasattr(e, "api_codes"):
            print(f"  api_codes: {e.api_codes}")
        if hasattr(e, "api_messages"):
            print(f"  api_messages: {e.api_messages}")
        if hasattr(e, "response") and e.response is not None:
            print(f"  status_code: {e.response.status_code}")
            print(f"  response_body: {e.response.text[:500]}")
        sys.exit(1)
