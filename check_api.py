"""X API の認証と利用可否だけを確認する（投稿しない）。自分のアカウント情報を1回読むだけ。"""
import os
import tweepy

client = tweepy.Client(
    consumer_key=os.environ["X_API_KEY"],
    consumer_secret=os.environ["X_API_SECRET"],
    access_token=os.environ["X_ACCESS_TOKEN"],
    access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
)
try:
    me = client.get_me(user_auth=True)
    print("OK: 認証成功 / account =", me.data.username if me and me.data else None)
except tweepy.HTTPException as e:
    print("NG: status =", e.response.status_code)
    print("body =", e.response.text[:500])
    raise SystemExit(1)
