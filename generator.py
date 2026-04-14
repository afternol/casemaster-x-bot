"""
CaseMaster Pro X Bot — コンテンツ生成モジュール
Claude Sonnet API を使って10種のコンテンツタイプのツイートを生成する。
"""
import random
import re
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY, SITE_URL, CONTENT_DIR

JST = timezone(timedelta(hours=9))

# ── バリデーション設定 ───────────────────────────────────────────

# コードで機械的に検出する禁止フレーズ（Claudeの自己チェックに依存しない）
FORBIDDEN_PHRASES = [
    "一度だけ", "まず1回", "試しに", "1回だけ",
    "合格率", "内定率", "合格保証", "内定保証",
    "業界No.1", "業界ナンバーワン", "唯一の",
    "casemasterpro.com",           # 誤URL（ハイフンなし）
    "casemaster pro.com",
]

MAX_TWEET_LENGTH = 280
MIN_TWEET_LENGTH = 230  # 上限ぎりぎりを狙う下限
MAX_RETRIES = 3

# ── 共通フォーマット指示（全プロンプトに埋め込む） ────────────────
FORMAT_RULES = """
【文字数・フォーマット共通ルール】
- 文字数: 250〜280文字（X投稿の上限は280文字。上限ぎりぎりまで使うこと。230文字未満は不合格）
- 改行を積極的に活用し、スマホで見たときに読みやすい構造にする
- 箇条書き（「・」や「▶」）、区切り線（「─────」等）、番号リスト（①②③）など視認性を高める工夫をする
- 1文は短く。長い説明は改行で区切る
- ハッシュタグは末尾の1つだけ（改行して最後の行に置く）
- ツイート本文のみ出力（前置きや説明は不要）
"""

_client: anthropic.Anthropic | None = None
_system_prompt: str | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _get_system_prompt() -> str:
    """character.md + 今日の日付をシステムプロンプトとして返す（日付は毎回動的に付与）"""
    global _system_prompt
    if _system_prompt is None:
        path = CONTENT_DIR / "character.md"
        _system_prompt = path.read_text(encoding="utf-8")
    today = datetime.now(JST).strftime("%Y年%m月%d日")
    return f"{_system_prompt}\n\n---\n\n## 今日の日付\n{today}（JST）\nこの日付を踏まえて就活・転職の時期感覚を持った投稿をしてください。"


def _load_yaml(filename: str) -> list[dict]:
    path = CONTENT_DIR / filename
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _call_claude(prompt: str) -> str:
    client = _get_client()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=_get_system_prompt(),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ── コンテンツタイプ別生成関数 ─────────────────────────────────

def _gen_relatable(recent_block: str = "") -> str:
    """あるある共感型：読者が「わかる！」「自分のことだ」と感じる共感ネタ"""
    themes = [
        "ケース面接前日",
        "ケース面接の本番中",
        "グループディスカッション（GD）中",
        "フェルミ推定を初めて練習するとき",
        "コンサル志望を友人に話したとき",
        "ケース面接の面接官に沈黙を見せられたとき",
        "フレームワークを覚えたばかりのとき",
        "MBB志望と周りに言ったとき",
        "コンサル内定者の話を聞いたとき",
        "ケース面接後の振り返りのとき",
        "フェルミ推定の答えがどこか調べようとしたとき",
        "ロジカルシンキングを意識しすぎているとき",
    ]
    theme = random.choice(themes)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
「{theme}」をテーマにした「あるある共感型」のツイートを書いてください。
{recent_block}
{FORMAT_RULES}
追加条件:
- 「〇〇あるある」「わかる人いる？」「これ私だけじゃないはず」などの共感を呼ぶフックで始める
- コンサル志望者・ケース面接受験者だけが「あ〜これね」と感じる具体的なネタを3〜4個箇条書きで
- ユーモアを大事にしつつ、最後は前向きなメッセージか実践的なヒントで締める
- 絵文字2〜3個
- 構造例：【フック1行】→【あるある箇条書き3〜4項目】→【締め1行】→【ハッシュタグ】
- ハッシュタグは「#ケース面接」「#コンサル就活」のどちらか1つ"""
    return _call_claude(prompt)


def _gen_before_after(recent_block: str = "") -> str:
    """NG→OK対比型：具体的な言葉・行動レベルで Before/After を対比"""
    situations = [
        "冒頭の構造化（「少し考えさせてください」）",
        "問題の切り分け方（原因分析の仮説立て）",
        "フェルミ推定のセグメント設定",
        "売上減少ケースの分解方法",
        "面接官からの深掘り質問への対処",
        "GDでの論点整理の発言",
        "「施策」を問われたときの答え方",
        "結論ファーストでの答え方",
        "定量的な根拠の示し方",
        "ケースの最後の提言まとめ方",
        "時間管理が苦しくなったときの対処",
        "「それは本当にイシューですか？」と聞かれたとき",
    ]
    situation = random.choice(situations)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
「{situation}」の場面を題材に「NG→OK対比型」のツイートを書いてください。
{recent_block}
{FORMAT_RULES}
追加条件:
- 「○○してませんか？」「ここで差がつく」などの問題提起フックで始める
- ❌ NGパターン：実際に受験生がやりがちな"リアルな発言・行動"を具体的に1〜2行で描写
- ✅ OKパターン：正しいアプローチを同じ粒度で具体的に1〜2行
- なぜNGか・なぜOKかを1行添える
- 絵文字2〜3個
- 構造例：【フック1行】→【❌NG具体描写】→【✅OK改善版】→【理由1行】→【ハッシュタグ】
- ハッシュタグは「#ケース面接」「#就活対策」のどちらか1つ"""
    return _call_claude(prompt)


def _gen_quiz(recent_block: str = "") -> str:
    """問いかけクイズ型：読者に考えさせてから答えやヒントを示す"""
    quiz_themes = [
        "MECEの定義を15文字以内で言えますか？",
        "フェルミ推定で最初にやることは？",
        "ロジックツリーとイシューツリーの違いは？",
        "ケース面接で面接官が最も見ているポイントは？",
        "売上 = ? × ? に分解すると何になる？",
        "3C分析の3つのCとは何？",
        "バリューチェーンを使うのはどんなとき？",
        "コンサルの選考で「ケース面接」がある理由は？",
        "仮説思考と情報収集思考、どちらが先？",
        "MECE漏れを素早くチェックする方法は？",
    ]
    quiz = random.choice(quiz_themes)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
以下の問いを使った「問いかけクイズ型」のツイートを書いてください。

問い: {quiz}
{recent_block}
{FORMAT_RULES}
追加条件:
- 「突然ですが、問題です」「30秒で答えられますか？」などのキャッチーな導入で始める
- 問いを1行で目立たせる（枠・記号など）
- 「答えはこの下↓」「3秒考えてみてください」など引き込む仕掛けを入れる
- 正解・解説を2〜3行で丁寧に説明（「一般的には」「基本的には」「〜とされています」などの留保表現を必ず使う。断定しない）
- 「これ答えられたら合格レベル！」などの締めコメント
- 絵文字2〜3個
- 構造例：【導入1行】→【問い提示1行】→【引き込み1行】→【答え・解説2〜3行】→【締め1行】→【ハッシュタグ】
- ハッシュタグは「#ケース面接」「#コンサル就活」のどちらか1つ"""
    return _call_claude(prompt)


def _gen_numbered(recent_block: str = "") -> str:
    """数字フック型：「〇つのポイント」「〇選」形式で整理された情報を提供"""
    topics = [
        "ケース面接で差がつく",
        "面接官が見ているといわれる",
        "フェルミ推定を速くする",
        "初心者が勘違いしがちな",
        "ケース面接通過者に共通する",
        "ケース面接直前にやること",
        "構造化が苦手な人に効く",
        "GDで印象が上がる",
        "コンサル思考を鍛える",
        "仮説思考を身につける",
    ]
    counts = [3, 4, 5]
    topic = random.choice(topics)
    count = random.choice(counts)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
「{topic}{count}つのこと」というテーマで「数字フック型」のツイートを書いてください。
{recent_block}
{FORMAT_RULES}
追加条件:
- 「{topic}{count}つのこと」など数字を使ったフックで始める
- ①②③…の番号付きリストで{count}項目を列挙
- 各項目は「タイトル + 一言補足」の形式でコンパクトに
- 「保存して繰り返し見るのがおすすめ」など活用の促しで締める
- 絵文字1〜2個
- 構造例：【タイトル1行（数字強調）】→【番号付きリスト{count}項目】→【締め1行】→【ハッシュタグ】
- ハッシュタグは「#ケース面接」「#就活」のどちらか1つ"""
    return _call_claude(prompt)


def _gen_mini_story(recent_block: str = "") -> str:
    """1コマストーリー型：臨場感ある短編で読者を引き込む"""
    scenarios = [
        "ケース面接の本番で頭が真っ白になった瞬間",
        "面接官に「本当にそれがイシューですか？」と聞かれたとき",
        "GDで誰も発言しない沈黙が30秒続いたとき",
        "フェルミ推定で自信満々に答えたら大外れだったとき",
        "練習を始めて1ヶ月で「変わった」と感じた瞬間",
        "初めてコンサルの先輩のケース回答を聞いたときの衝撃",
        "面接終了直後に「あそこで言えたのに…」と思ったとき",
        "ESに「志望動機はコンサルで〇〇したい」と書いたがうまく言語化できなかったとき",
    ]
    scenario = random.choice(scenarios)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
「{scenario}」をテーマに「1コマストーリー型」のツイートを書いてください。
{recent_block}
{FORMAT_RULES}
追加条件:
- 場面・状況を一人称または三人称で臨場感を持って描写（2〜3行）
- 読者が「わかる」「怖い」「自分もこうなりそう」と感じるリアルな描写
- 教訓・実践できるポイントを1〜2行で自然に添える（説教にならないように）
- 短くても物語として完結させる
- 絵文字1〜2個
- 構造例：【状況描写2〜3行】→【転換・気づき1行】→【教訓・実践ポイント1〜2行】→【ハッシュタグ】
- ハッシュタグは「#ケース面接」「#コンサル就活」のどちらか1つ"""
    return _call_claude(prompt)


def _gen_save_card(recent_block: str = "") -> str:
    """保存推奨まとめ型：「スクショ必須」「保存して」のCTAと共に知識をコンパクトにまとめる"""
    card_topics = [
        "ケース面接の基本フレームワーク4選",
        "フェルミ推定で使う頻出数値まとめ",
        "ケース面接の時間配分（30分版）",
        "MECEに分解するコツ3パターン",
        "GDで評価される発言パターン",
        "ケース面接 頻出8業界のKPI",
        "仮説思考の3ステップ",
        "構造化発言の型（結論→理由→具体例）",
        "フェルミ推定の分解パターン5種",
        "コンサル選考フローまとめ",
    ]
    topic = random.choice(card_topics)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
「{topic}」をテーマに「保存推奨まとめ型」のツイートを書いてください。
{recent_block}
{FORMAT_RULES}
追加条件:
- 「📌 保存推奨」「🔖 スクショしてください」などのCTA行で始める
- タイトルをはっきり1行で示す
- 内容を箇条書き・番号・表形式（テキストで）などで視認性高くまとめる
- 具体的な数値（人口・市場規模・割合など）を使う場合は必ず「目安」「参考値」「一般的に〜とされる」などの留保表現を付ける。数値を断定しない
- 「これ一枚でケース面接の基礎が整理できます」などの締め
- 絵文字1〜2個（冒頭のCTA絵文字を除く）
- 構造例：【CTA1行】→【タイトル1行】→【まとめ内容（箇条書き等）】→【締め1行】→【ハッシュタグ】
- ハッシュタグは「#ケース面接」「#就活対策」のどちらか1つ"""
    return _call_claude(prompt)


def _gen_seasonal(recent_block: str = "") -> str:
    """時事・季節連動型：今日の日付から就活シーズンを判断し、タイムリーな内容を投稿"""
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
今日の日付を踏まえて、「時事・季節連動型」のツイートを書いてください。

就活・コンサル転職のタイムラインを参考にしてください：
- 1〜3月: 外資コンサル本選考ピーク・冬インターン
- 4〜5月: 国内コンサル本選考・外資内定後の準備期間
- 6〜8月: 夏インターン（外資系中心）・大手国内サマーインターン
- 9〜11月: 秋選考・外資早期内定・転職活動活発化
- 12月: 外資コンサル早期選考・翌年の対策開始

{recent_block}
{FORMAT_RULES}
追加条件:
- 「この時期」「今の時期」「〇月の今」など時期感を出す
- 今のシーズンに合わせた具体的なアドバイスや行動指針を提示
- 「今からできること」「まだ間に合う」「この時期にやっておくべき」など行動促進
- 焦らせるのではなく、前向きに背中を押すトーン
- 絵文字2〜3個
- 構造例：【時期感フック1行】→【この時期の状況・課題2行】→【具体的なアドバイス2〜3行】→【励まし締め1行】→【ハッシュタグ】
- ハッシュタグは「#ケース面接」「#コンサル就活」「#就活」のいずれか1つ"""
    return _call_claude(prompt)


def _gen_fermi(recent_block: str = "") -> str:
    """フェルミ推定問題型：練習問題を提示して考える習慣を促す"""
    items = _load_yaml("fermi.yml")
    item = random.choice(items)
    prompt = f"""あなたはコンサル・ケース面接対策アカウントです。
以下のフェルミ推定問題を使った練習促進ツイートを書いてください。

問題: {item['question']}
ヒント（ツイートには出さない。問題の難易度把握のみに使う）: {item['hint']}
{recent_block}
{FORMAT_RULES}
追加条件:
- 「💡 今日の練習問題」「🧮 フェルミ推定チャレンジ」などの導入行で始める
- 問題を1行で提示（枠線や強調で目立たせる）
- 「どう分解するか？」「どの数値を使うか？」など考え方の視点を箇条書きで1〜2個示す（解答は書かない）
- 「解けたらコメントで！」「答え合わせはAIと👇」等のCTAで締める
- 構造例：【導入1行】→【問題1行】→【着眼点2行】→【CTA1行】→【ハッシュタグ】
- ハッシュタグは「#フェルミ推定」「#ケース面接」のどちらか1つ"""
    return _call_claude(prompt)


def _gen_question(recent_block: str = "") -> str:
    """ケース練習問題型：実際のケース問題を提示して解くことを促す"""
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
{FORMAT_RULES}
追加条件:
- 「💼 今週のケース問題」などの導入行で始める
- 問題を枠や記号で目立たせて1行で提示
- 考える際のフレームや着眼点を箇条書きで2〜3個示唆する（解答は書かない）
- 「あなたならどう解く？」「コメントで教えてください！」などのCTAで締める
- 継続・反復練習の大切さを自然に盛り込む
- 絵文字1〜2個
- 構造例：【導入1行】→【問題提示1行】→【着眼点箇条書き2〜3項目】→【CTA1行】→【ハッシュタグ】
- ハッシュタグは「#ケース面接」「#コンサル就活」のどちらか1つ"""
    return _call_claude(prompt)


def _gen_promo(recent_block: str = "") -> str:
    """ツール紹介型：押しつけがましくなく自然にCaseMaster Proを紹介する"""
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
{FORMAT_RULES}
追加条件:
- 「〇〇で悩んでいる方へ」「こんな練習方法があります」などの入り方（ハードな売り込みは避ける）
- 具体的なメリットや使い方のイメージを2〜3行で説明
- URLを末尾の行に含める
- 絵文字2〜3個
- 構造例：【共感フック1行】→【メリット解説2〜3行】→【誘導1行】→【URL】→【ハッシュタグ】
- ハッシュタグは「#ケース面接」のみ
- 【重要】「一度だけ」「まず1回」など単発利用を促す表現は絶対に使わない
- 「毎日」「繰り返し」「継続」「積み上げ」など継続・反復利用を促す表現を自然に盛り込む"""
    return _call_claude(prompt)


# ── ディスパッチテーブル ────────────────────────────────────────

_GENERATORS = {
    "relatable":    _gen_relatable,
    "before_after": _gen_before_after,
    "quiz":         _gen_quiz,
    "numbered":     _gen_numbered,
    "mini_story":   _gen_mini_story,
    "save_card":    _gen_save_card,
    "seasonal":     _gen_seasonal,
    "fermi":        _gen_fermi,
    "question":     _gen_question,
    "promo":        _gen_promo,
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


def _validate(text: str, content_type: str) -> list[str]:
    """
    ツイートテキストをコードで機械的に検証する。
    Claudeの自己チェックには依存しない。
    戻り値: エラーメッセージのリスト（空リストなら合格）
    """
    errors = []

    # 1. 文字数チェック（上限・下限）
    if len(text) > MAX_TWEET_LENGTH:
        errors.append(f"文字数超過: {len(text)}文字（上限{MAX_TWEET_LENGTH}文字）")
    elif len(text) < MIN_TWEET_LENGTH:
        errors.append(f"文字数不足: {len(text)}文字（最低{MIN_TWEET_LENGTH}文字以上必要）")

    # 2. 禁止フレーズチェック
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            errors.append(f"禁止フレーズ含む: 「{phrase}」")

    # 3. promoタイプはURLが必須かつ正しいURLであること
    if content_type == "promo":
        if "casemaster-pro.com" not in text:
            errors.append("promoタイプにURLが含まれていない")

    # 4. 空チェック
    if not text.strip():
        errors.append("空のテキスト")

    return errors


def generate_tweet_text(content_type: str, recent_tweets: list[str] | None = None) -> str:
    """
    指定タイプのツイートテキストを生成して返す。
    バリデーション失敗時は最大MAX_RETRIES回まで再生成する。
    recent_tweets: 過去の投稿済みツイートテキストのリスト（重複回避に使用）
    """
    gen_fn = _GENERATORS.get(content_type)
    if gen_fn is None:
        raise ValueError(f"Unknown content_type: {content_type!r}. Must be one of {list(_GENERATORS)}")

    recent_block = _build_recent_block(recent_tweets or [])

    for attempt in range(1, MAX_RETRIES + 1):
        text = gen_fn(recent_block=recent_block)
        errors = _validate(text, content_type)

        if not errors:
            if attempt > 1:
                print(f"    [validation] {attempt}回目で合格")
            return text

        print(f"    [validation] 試行{attempt}/{MAX_RETRIES} 失敗: {errors}")
        # 再生成時はバリデーション失敗理由をプロンプトに追加
        violation_note = "【前回の生成で以下の違反がありました。必ず修正してください】\n" + "\n".join(f"- {e}" for e in errors)
        recent_block = f"{violation_note}\n\n{recent_block}"

    # 最大リトライ後もNG → 最後の生成結果を警告付きで返す（止めるより投稿を優先）
    print(f"    [validation] 最大リトライ到達。最終テキストを使用（要確認）")
    return text


# ── CLI ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    ctype = sys.argv[1] if len(sys.argv) > 1 else "relatable"
    print(f"[generate] type={ctype}")
    text = generate_tweet_text(ctype)
    print(f"\n{text}\n({len(text)}文字)")
