"""
ワンショット投稿スクリプト
手動でドラフトしたツイートを即時投稿する（Supabaseキューを経由しない）
使い方: python post_now.py
"""
import sys
from config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
import tweepy

TWEET_TEXT = """ケース面接、ここで多くの人が損をしている🎯

「少し考えさせてください」の15秒。

❌ ありがちなNG
頭の中でいきなり計算を始める
→ 5分後に「何を解いていたっけ？」となる
→ 論点がズレたまま走り続ける

✅ 変わる一手
「○○社の売上改善、という理解でよいですか？」
「ゴールは利益改善か、売上拡大か確認させてください」

問いを30秒で言語化するだけで
残り25分の密度が大きく変わる。

面接官が見ているのは「答えの速さ」ではなく
「何を解くかを定義できるか」。

#ケース面接 #コンサル就活"""


def main():
    dry_run = "--dry" in sys.argv

    print(f"文字数: {len(TWEET_TEXT)}")
    print(f"プレビュー:\n{TWEET_TEXT}\n")

    if dry_run:
        print("[DRY RUN] 投稿をスキップしました。")
        return

    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True,
    )

    try:
        response = client.create_tweet(text=TWEET_TEXT, user_auth=True)
        tweet_id = response.data["id"]
        print(f"✅ 投稿成功！ tweet_id={tweet_id}")
        print(f"URL: https://x.com/casemaster_pro/status/{tweet_id}")
    except tweepy.TweepyException as e:
        print(f"❌ 投稿失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
