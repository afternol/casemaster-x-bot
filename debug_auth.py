"""
認証診断スクリプト v3
特殊文字・書式を段階的に取り除いて 403 の原因を特定する
"""
import sys
import tweepy
from config import (
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
)

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
    print(f"  len={len(text)}")
    if dry_run:
        print(f"  [DRY RUN] {repr(text[:80])}")
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

# 失敗したテキスト（Supabase から取得した実物）
FAILING_TEXT = '「日本の自動販売機の台数は？」\n\n自信満々に手を挙げた。\n「約500万台です。根拠は人口÷20で——」\n\n面接官が静かに言った。\n「実際は約200〜250万台ですね」\n\n頭が真っ白になった。\n数字は合っていると思っていた。\nでも人口比例で割った時点で、すでに間違いだった。\n\n─────────────\n\n自動販売機は「人口」より「設置場所の密度」で考える。\n駅・工場・学校・オフィス・屋外スペース……\n\nフェルミは「何を軸に分解するか」が9割。\n自信より、分解の筋道を先に点検しよう。\n\n#ケース面接 #コンサル就活'

print("=" * 60)
print(f"元テキスト: {len(FAILING_TEXT)}文字")
print("=" * 60)

# Test 1: 罫線 ─────────── を削除
t1 = FAILING_TEXT.replace("─────────────", "")
success = try_post("罫線(─)削除版", t1)
if success and not dry_run:
    print("  → 罫線が原因と判明")
    sys.exit(0)

# Test 2: 罫線 + 空行を削除して1改行に統一
import re
t2 = re.sub(r'\n{2,}', '\n', FAILING_TEXT.replace("─────────────", ""))
success = try_post("罫線削除 + 空行を1改行に", t2)
if success and not dry_run:
    print("  → 罫線と空行が原因と判明")
    sys.exit(0)

# Test 3: 特殊記号を全て置換（÷→/、——→—、……→...、─→-）
t3 = FAILING_TEXT.replace("─────────────", "---").replace("——", "—").replace("÷", "/").replace("……", "...")
success = try_post("特殊記号を全置換版", t3)
if success and not dry_run:
    print("  → 特殊記号が原因と判明")
    sys.exit(0)

# Test 4: ハッシュタグを1個だけに
t4 = FAILING_TEXT.replace("─────────────", "---").replace("——", "—").replace("÷", "/").replace("……", "...").replace("#ケース面接 #コンサル就活", "#ケース面接")
success = try_post("特殊記号置換 + ハッシュタグ1個版", t4)
if success and not dry_run:
    print("  → 複数ハッシュタグも関係していた可能性")
    sys.exit(0)

# Test 5: プレーンテキスト（日本語のみ、記号・改行なし）
t5 = "フェルミ推定では分解の軸が重要です。自動販売機の台数を「人口÷定数」で出すと間違い。設置場所の密度で考えることが正解への近道。分解の筋道を先に点検しましょう。 #ケース面接"
success = try_post("プレーンテキスト版", t5)
if success and not dry_run:
    print("  → フォーマット（改行・罫線）が根本原因")
    sys.exit(0)

if not dry_run:
    print("\n❌ 全テスト失敗 — トークンまたはアカウントレベルの問題の可能性")
