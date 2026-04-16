"""
認証診断スクリプト v5
「フラグされたテキスト」vs「文字数」の切り分けテスト
"""
import sys
import tweepy
from config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET

dry_run = "--dry" in sys.argv

client = tweepy.Client(
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True,
)

def try_post(label: str, text: str):
    print(f"\n[TEST] {label}")
    print(f"  len={len(text)}, has_newline={chr(10) in text}")
    if dry_run:
        print(f"  [DRY RUN] {repr(text[:120])}")
        return True
    try:
        response = client.create_tweet(text=text, user_auth=True)
        tweet_id = response.data["id"]
        print(f"  ✅ 成功: tweet_id={tweet_id}")
        return True
    except tweepy.TweepyException as e:
        print(f"  ❌ 失敗: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"  response_body: {e.response.text}")
        return False

# Test D: 全く新しい240文字テキスト（問題テキストと無関係・単一段落）
t_d = "コンサル就活で差がつくのは「問いを定義する力」です。ケースを渡されて即座に解き始めるのは危険。まず冒頭30秒で「何を解くべきか」を確認する。問いが正確なら、フレームワークも自然に決まる。問いがズレれば、どれだけ緻密に計算しても的外れになる。面接官が評価するのは答えの速さより、問いへの向き合い方です。 #ケース面接"
print(f"Test D length: {len(t_d)}")
success = try_post("全く新しい240文字テキスト（単一段落）", t_d)
if success and not dry_run:
    print("  → 失敗テキストが個別フラグされていた（長さは問題なし）")
    sys.exit(0)

# Test E: 短い150文字の新テキスト
t_e = "ケース面接で「問いの定義」を最初に確認する人は少ない。でも面接官が最も注目するのはここ。冒頭30秒で問いを正確に言語化できれば、残りの時間の密度が格段に上がる。 #ケース面接"
print(f"Test E length: {len(t_e)}")
success = try_post("新テキスト150文字（短め）", t_e)
if success and not dry_run:
    print("  → 200文字超えが制限")
    sys.exit(0)

if not dry_run:
    print("\n全テスト失敗 → アカウントまたはAPIプランの制限の可能性が高い")
    print("確認事項: X Developer Portalのアプリのアクセスレベル（Free/Basic/Pro）")
