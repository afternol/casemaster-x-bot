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
SITE_URL = os.getenv("SITE_URL", "https://casemaster-pro.com/")

# ── 投稿時間枠（JST）──────────────────────────────────────────
# 6枠から毎日3枠をランダム選択（日付シードで冪等）
TIME_WINDOWS = [
    {"name": "朝A",  "start": (6, 55),  "end": (8, 20)},
    {"name": "朝B",  "start": (9, 10),  "end": (10, 40)},
    {"name": "昼",   "start": (11, 45), "end": (13, 35)},
    {"name": "午後", "start": (14, 20), "end": (16, 10)},
    {"name": "夕方", "start": (17, 30), "end": (19, 40)},
    {"name": "夜",   "start": (20, 45), "end": (23, 10)},
]

# 1日の投稿数
DAILY_POST_COUNT = 3

# ── コンテンツタイプと重み ───────────────────────────────────
# 30種類: 同じ構造の連続を避けるため幅広いフォーマットを用意
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
    "promo":            2,   # ツール紹介型
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
