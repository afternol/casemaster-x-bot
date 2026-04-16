"""
認証診断スクリプト v4
改行（\\n）が直接の原因かを確定テスト
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

# 元の失敗テキスト（改行あり・259文字）
FAILING_TEXT = '「日本の自動販売機の台数は？」\n\n自信満々に手を挙げた。\n「約500万台です。根拠は人口÷20で——」\n\n面接官が静かに言った。\n「実際は約200〜250万台ですね」\n\n頭が真っ白になった。\n数字は合っていると思っていた。\nでも人口比例で割った時点で、すでに間違いだった。\n\n─────────────\n\n自動販売機は「人口」より「設置場所の密度」で考える。\n駅・工場・学校・オフィス・屋外スペース……\n\nフェルミは「何を軸に分解するか」が9割。\n自信より、分解の筋道を先に点検しよう。\n\n#ケース面接 #コンサル就活'

# Test A: 全改行をスペースに置換（同じ内容・単一行）
t_a = FAILING_TEXT.replace('\n', ' ').replace('─────────────', '').replace('  ', ' ')
success = try_post("全改行→スペース（同内容・単一行）", t_a)
if success and not dry_run:
    print("  → \\n（改行）が直接の原因！")
    sys.exit(0)

# Test B: 改行1個はOK、\\n\\n（空行）だけNGか？
t_b = FAILING_TEXT.replace('\n\n', '\n').replace('─────────────', '').strip()
success = try_post("空行(\\n\\n)を単改行に（\\n単体はそのまま）", t_b)
if success and not dry_run:
    print("  → 空行（\\n\\n）が原因！")
    sys.exit(0)

# Test C: 改行なし・長め（220文字程度）
t_c = "ケース面接で重要なのは「分解の軸」を正しく選ぶこと。自動販売機の台数を人口比例で計算すると大外れ。正しくは設置場所の密度で考える。駅・工場・学校・オフィスの設置数を積み上げる。フェルミ推定では「何を軸に分解するか」が答えの精度を9割決める。 #ケース面接"
success = try_post("改行なし・長め（220文字）", t_c)
if success and not dry_run:
    print("  → 改行なし長文はOK")
    sys.exit(0)

if not dry_run:
    print("\n❌ 全テスト失敗 — アカウントまたはアプリレベルの制限の可能性")
