"""
CaseMaster Pro X Bot — コンテンツ生成モジュール
Claude Haiku API を使って9種のコンテンツタイプのツイートを生成する。
"""
import random
import yaml
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY, SITE_URL, CONTENT_DIR

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _load_yaml(filename: str) -> list[dict]:
    path = CONTENT_DIR / filename
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _call_claude(prompt: str) -> str:
    client = _get_client()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ── コンテンツタイプ別生成関数 ─────────────────────────────────

def _gen_framework(recent_block: str = "") -> str:
    items = _load_yaml("frameworks.yml")
    item = random.choice(items)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
以下のフレームワークについて、就活生・転職希望者向けに実践的に解説するツイートを1つ書いてください。

フレームワーク名: {item['name']}
説明: {item['description']}
{recent_block}
条件:
- 140文字以内（厳守）
- 絵文字を1〜2個使う
- 実際のケース面接でいつ使うかを一言添える
- ハッシュタグは「#ケース面接」「#コンサル就活」のどちらか1つだけ末尾に
- ツイート本文のみ出力（前置き不要）"""
    return _call_claude(prompt)


def _gen_fermi(recent_block: str = "") -> str:
    items = _load_yaml("fermi.yml")
    item = random.choice(items)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
以下のフェルミ推定問題を使った練習促進ツイートを書いてください。

問題: {item['question']}
ヒント（ツイートには出さない。問題の難易度把握のみに使う）: {item['hint']}
{recent_block}
条件:
- 140文字以内（厳守）
- 「今日の練習問題💡」「フェルミ推定チャレンジ🧮」などの導入
- 解答は書かない（考えてもらう形式。「解けたらコメントで！」等のCTA可）
- ハッシュタグは「#フェルミ推定」「#ケース面接」のどちらか1つだけ末尾に
- ツイート本文のみ出力（前置き不要）"""
    return _call_claude(prompt)


def _gen_tips(recent_block: str = "") -> str:
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
ケース面接を受ける就活生・転職希望者に向けた実践的なtipsを1つツイートしてください。
{recent_block}
条件:
- 140文字以内（厳守）
- 「〇〇するだけで」「NG→OK」の対比、「面接官が見ているのは〇〇」などの具体的切り口
- 即実践できる内容（抽象論は避ける）
- 絵文字1〜2個
- ハッシュタグは「#ケース面接」「#就活対策」のどちらか1つだけ末尾に
- ツイート本文のみ出力（前置き不要）"""
    return _call_claude(prompt)


def _gen_terminology(recent_block: str = "") -> str:
    terms = [
        "MECE", "イシューツリー", "ロジックツリー", "ボトムアップ推計", "トップダウン推計",
        "仮説思考", "構造化思考", "感度分析", "KPI設計", "バリューチェーン",
        "コア・コンピタンス", "差別化戦略", "ポジショニング", "ベンチマーク分析",
        "ゼロベース思考", "クリティカルシンキング", "ムダ・ムラ・ムリ",
        "サンクコスト", "機会費用", "限界費用",
    ]
    term = random.choice(terms)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
以下の用語を就活生向けに端的に解説するツイートを書いてください。

用語: {term}
{recent_block}
条件:
- 140文字以内（厳守）
- 「{term}とは？」または「【{term}】」で始める
- 本質を一言でつく解説 ＋ ケース面接での使いどころ
- 絵文字1個
- ハッシュタグは「#コンサル用語」「#ケース面接」のどちらか1つだけ末尾に
- ツイート本文のみ出力（前置き不要）"""
    return _call_claude(prompt)


def _gen_mistake(recent_block: str = "") -> str:
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
ケース面接でよくある失敗・NGパターンを1つ取り上げて、改善策とともにツイートしてください。
{recent_block}
条件:
- 140文字以内（厳守）
- 「〇〇してしまいがち」「多くの人がやるミス」などの共感入り口
- 失敗パターン → 一言改善策の流れ
- 絵文字1〜2個
- ハッシュタグは「#ケース面接」「#就活」のどちらか1つだけ末尾に
- ツイート本文のみ出力（前置き不要）"""
    return _call_claude(prompt)


def _gen_industry(recent_block: str = "") -> str:
    industries = [
        "コンサルティング業界", "外資系金融", "総合商社", "メーカー（製造業）",
        "ITサービス・SaaS", "小売・EC", "不動産", "物流・運輸",
        "食品・飲料メーカー", "医療・ヘルスケア", "メディア・広告",
        "エネルギー・インフラ", "自動車・モビリティ", "通信業界",
    ]
    industry = random.choice(industries)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
{industry}のケース面接で押さえるべき論点・分析の切り口をツイートしてください。
{recent_block}
条件:
- 140文字以内（厳守）
- 「{industry}のケースが出たら〇〇を押さえよう」のような実践的な内容
- 業界特有のKPIや収益構造の論点を1〜2個具体的に挙げる
- 絵文字1〜2個
- ハッシュタグは「#ケース面接」「#業界研究」のどちらか1つだけ末尾に
- ツイート本文のみ出力（前置き不要）"""
    return _call_claude(prompt)


def _gen_question(recent_block: str = "") -> str:
    question_types = [
        "コンビニチェーンの売上が前年比15%減少している。原因と対策を考えよ。",
        "大手ECが食料品即配市場に参入する際の戦略を立案せよ。",
        "日本の電動キックボードシェアライド市場規模を推計せよ。",
        "赤字が続く地方百貨店の立て直し策を3つ提案せよ。",
        "製造業のコストを20%削減するための施策を優先順位付きで提示せよ。",
        "スマートフォンメーカーが新興国市場に参入する戦略を考えよ。",
        "コーヒーチェーンの新業態を1つ立案し、収益性を試算せよ。",
        "航空会社の利益率改善策を、売上・コスト両面から検討せよ。",
        "医療機器メーカーがデジタルヘルス領域に進出する場合の戦略は？",
        "物流会社がドライバー不足問題を解決する方法を考えよ。",
    ]
    question = random.choice(question_types)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
以下のケース問題を使った練習促進ツイートを書いてください。

問題: {question}
{recent_block}
条件:
- 140文字以内（厳守）
- 「今週のケース問題💼」「これを解けたら本番でも戦える」などの導入
- 考える際のフレームや着眼点を1つだけ示唆する（解答は書かない）
- 絵文字1個
- ハッシュタグは「#ケース面接」「#コンサル就活」のどちらか1つだけ末尾に
- ツイート本文のみ出力（前置き不要）"""
    return _call_claude(prompt)


def _gen_quote(recent_block: str = "") -> str:
    quotes = [
        {"text": "問いを正しく立てれば、答えの半分は出ている。", "author": "コンサルの格言"},
        {"text": "データは過去を語り、仮説は未来を語る。", "author": "戦略思考の原則"},
        {"text": "複雑な問題をシンプルに解く。それがプロの仕事だ。", "author": "マッキンゼー流思考法"},
        {"text": "考えることをやめた瞬間、成長も止まる。", "author": "ビジネス格言"},
        {"text": "事実を集めるのではなく、仮説を持って動け。", "author": "コンサルの鉄則"},
        {"text": "MECEに考えることは、思考の無駄を省くことだ。", "author": "ロジカルシンキングの原則"},
        {"text": "答えよりも、問いの質が結果を決める。", "author": "イシュー思考の格言"},
        {"text": "相手の期待値を超えることが、信頼の積み上げになる。", "author": "コンサルの心得"},
    ]
    quote = random.choice(quotes)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
以下の言葉を引用したツイートを書いてください。ケース面接や論理的思考に絡めたコメントを添えてください。

言葉: 「{quote['text']}」（{quote['author']}）
{recent_block}
条件:
- 140文字以内（厳守）
- 引用を冒頭に入れ、「ケース面接でも〇〇」「この思考が〇〇につながる」などのコメントを添える
- 絵文字1個
- ハッシュタグは「#ケース面接」「#名言」のどちらか1つだけ末尾に
- ツイート本文のみ出力（前置き不要）"""
    return _call_claude(prompt)


def _gen_promo(recent_block: str = "") -> str:
    angles = [
        "AIと本番同様のケース面接練習ができる点",
        "即時フィードバックで弱点が一目でわかる点",
        "フェルミ推定・フレームワーク演習が充実している点",
        "無料で月3回使える手軽さ",
        "6軸スコアで成長が数値で見える点",
        "一人でも面接練習できる点（相手不要）",
    ]
    angle = random.choice(angles)
    prompt = f"""あなたはケース面接対策AIツール「CaseMaster Pro」の公式アカウントです。
以下の角度から、宣伝くさくなく自然にツールを紹介するツイートを書いてください。

紹介する角度: {angle}
サイトURL: {SITE_URL}
{recent_block}
条件:
- 140文字以内（厳守）
- 「〇〇で悩んでいる方へ」「こんな練習方法があります」などの入り方（ハードな売り込みは避ける）
- URLを末尾に含める
- 絵文字1〜2個
- ハッシュタグは「#ケース面接」のみ末尾に
- ツイート本文のみ出力（前置き不要）"""
    return _call_claude(prompt)


# ── ディスパッチテーブル ────────────────────────────────────────

_GENERATORS = {
    "framework":   _gen_framework,
    "fermi":       _gen_fermi,
    "tips":        _gen_tips,
    "terminology": _gen_terminology,
    "mistake":     _gen_mistake,
    "industry":    _gen_industry,
    "question":    _gen_question,
    "quote":       _gen_quote,
    "promo":       _gen_promo,
}


def _build_recent_block(recent_tweets: list[str]) -> str:
    """過去ツイートリストをプロンプト用テキストに変換する"""
    if not recent_tweets:
        return ""
    lines = "\n".join(f"- {t}" for t in recent_tweets[:30])
    return f"""
【重要】以下の過去ツイートと同じネタ・似た切り口・似た文章は絶対に避けてください:
{lines}
"""


def generate_tweet_text(content_type: str, recent_tweets: list[str] | None = None) -> str:
    """指定タイプのツイートテキストを生成して返す。
    recent_tweets: 過去の投稿済みツイートテキストのリスト（重複回避に使用）
    """
    gen_fn = _GENERATORS.get(content_type)
    if gen_fn is None:
        raise ValueError(f"Unknown content_type: {content_type!r}. Must be one of {list(_GENERATORS)}")
    recent_block = _build_recent_block(recent_tweets or [])
    return gen_fn(recent_block=recent_block)


# ── CLI ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    ctype = sys.argv[1] if len(sys.argv) > 1 else "tips"
    print(f"[generate] type={ctype}")
    text = generate_tweet_text(ctype)
    print(f"\n{text}\n({len(text)}文字)")
