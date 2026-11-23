"""
CaseMaster Pro X Bot — 設定モジュール
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ── X API 認証情報 ───────────────────────────────────────────
X_API_KEY             = os.getenv("X_API_KEY", "")
X_API_SECRET          = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN        = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")

# ── Claude API ──────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Supabase ────────────────────────────────────────────────
SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ── サイト情報 ───────────────────────────────────────────────
# リンクは常にトップページ（UTM は text_rules.add_utm が付与する）。
# GitHub Actions で secret 未設定だと空文字が渡るため `or` でデフォルトに倒す。
# ハイフンなしドメイン等の誤設定も既定値に矯正する（値はログに出さない）。
_DEFAULT_SITE_URL = "https://casemaster-pro.com/"


def _normalize_site_url(raw: str) -> str:
    from urllib.parse import urlsplit
    raw = (raw or "").strip()
    try:
        host = (urlsplit(raw).hostname or "").lower()
    except ValueError:
        host = ""
    if host not in ("casemaster-pro.com", "www.casemaster-pro.com"):
        if raw:
            print("[config] SITE_URL が casemaster-pro.com ではないため既定値を使用します")
        return _DEFAULT_SITE_URL
    return f"https://{host}/"


SITE_URL = _normalize_site_url(os.getenv("SITE_URL", ""))

# ── 投稿スケジュール（JST）────────────────────────────────────
# 1日1投稿・固定時刻。20:00 JST は学生・社会人ともに X を見る夜のゴールデンタイム。
# poster.yml は30分ごとに起動し、時刻を過ぎた pending を1件だけ投稿する。
POST_TIME_JST = (20, 0)

# 1日の投稿数（scheduler はこの件数を超えて生成しない）
DAILY_POST_COUNT = 1

# 予定時刻から STALE_AFTER_HOURS 時間以上過ぎた pending は投稿せず failed（[stale]）にする
# （ワークフロー停止→再開時の一斉投稿を防ぐ）
STALE_AFTER_HOURS = 3

# 直近 MIN_POST_INTERVAL_HOURS 時間以内に投稿済みなら、次の投稿は見送る（二重投稿防止）
MIN_POST_INTERVAL_HOURS = 12

# promo（ツール紹介）は週1回、この曜日に固定（Python の weekday: 月=0 … 日=6）
# 1日1投稿 × 週1回 ≒ 全体の約14%。日曜夜は翌週の対策計画を立てるタイミング。
PROMO_WEEKDAY = 6

# ── コンテンツタイプと重み ───────────────────────────────────
# 30種類: 同じ構造の連続を避けるため幅広いフォーマットを用意
# promo は PROMO_WEEKDAY に固定配信するため、ランダム抽選の重みは 0
CONTENT_TYPES = {
    # ── 既存10種 ───────────────────────────────────────────
    "relatable":        7,   # あるある共感型
    "before_after":     7,   # NG→OK対比型
    "numbered":         6,   # 数字フック型
    "question":         6,   # ケース練習問題型
    "mini_story":       6,   # 1コマストーリー型
    "quiz":             4,   # 問いかけクイズ型
    "save_card":        4,   # 保存推奨まとめ型
    "seasonal":         3,   # 時事・季節連動型
    "fermi":            3,   # フェルミ推定問題型
    "promo":            0,   # ツール紹介型（PROMO_WEEKDAY に週1固定。抽選対象外）
    # ── A. 深掘り解説系 ───────────────────────────────────
    "framework_deep":   6,   # フレームワーク深掘り（3C/4P/PEST等を1つ詳述）
    "terminology":      5,   # コンサル用語解説（イシュー/MECE/So What等）
    "industry_brief":   2,   # 業界別キーポイント解説
    # ── B. 思考法・スキル系 ───────────────────────────────
    "how_to_step":      5,   # 「○○のやり方をN段階で」
    "checklist":        5,   # 「これできてる？」チェックリスト型
    "common_mistake":   4,   # よくある失敗パターン
    "mind_shift":       4,   # 常識転換型「実は逆」
    "analogy":          4,   # 例え話アナロジー（料理/スポーツ）
    # ── C. 数字・データ系 ─────────────────────────────────
    "number_intuition": 2,   # 数字感覚クイズ（人口/市場規模）
    "data_insight":     2,   # データインサイト（業界統計）
    "counterintuitive": 4,   # 直感反する真実「実は」
    # ── D. インタラクション系 ─────────────────────────────
    "poll":             2,   # 二択ポーリング「A or B?」
    "dialogue":         3,   # 面接官×受験者の2行対話
    "ask_pattern":      2,   # 「みんなはどっち派？」型
    # ── E. ストーリー・感情系 ─────────────────────────────
    "confession":       3,   # 弱み告白型「実は私も…」
    "encouragement":    3,   # 励まし・応援型
    "failure_lesson":   2,   # 失敗から学び型
    "transformation":   3,   # 人物のBefore/After成長談
    # ── F. メタ・哲学系 ───────────────────────────────────
    "truth_bomb":       3,   # 短い真実宣言（3行で刺す）
    "principle":        3,   # コンサル思考の原則
}

# ── パス ────────────────────────────────────────────────────
LOG_DIR     = Path(__file__).parent / "logs"
CONTENT_DIR = Path(__file__).parent / "content"
