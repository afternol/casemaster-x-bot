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
SITE_URL = os.getenv("SITE_URL", "https://casemasterpro.com")

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
CONTENT_TYPES = {
    "framework":   15,  # フレームワーク解説
    "fermi":       12,  # フェルミ推定問題
    "tips":        15,  # 面接tips
    "terminology": 10,  # コンサル用語解説
    "mistake":     12,  # よくある失敗・NGパターン
    "industry":    10,  # 業界別ケース切り口
    "question":    13,  # 面接練習問題
    "quote":        8,  # 名言・格言
    "promo":        5,  # ツール紹介
}

# ── パス ────────────────────────────────────────────────────
LOG_DIR     = Path(__file__).parent / "logs"
CONTENT_DIR = Path(__file__).parent / "content"
