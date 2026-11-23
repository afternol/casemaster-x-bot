"""
CaseMaster Pro X Bot — テキスト検証・リンク加工ルール（外部ライブラリ非依存）

generator.py（生成時）と poster.py（投稿直前）の両方から使う。
- twitter_weight : X の重み付き文字数（URL は t.co 短縮で一律 23）
- add_utm        : casemaster-pro.com への URL に UTM パラメータを付与（冪等）
- check_text     : 重み上限・禁止表現・リンク先の機械チェック
"""
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SITE_DOMAIN = "casemaster-pro.com"           # ハイフン必須
SITE_HOSTS = {SITE_DOMAIN, "www." + SITE_DOMAIN}

MAX_TWEET_WEIGHT = 280   # X の重み上限（日本語1文字=2、ASCII=1、URL=23）
MIN_TWEET_WEIGHT = 180   # 短すぎる投稿を防ぐ下限（生成時のみ適用）
TCO_URL_WEIGHT = 23      # X は URL を長さに関係なく t.co 換算で 23 と数える

UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign")

# コードで機械的に検出する禁止フレーズ（全タイプ共通・大文字小文字無視）
FORBIDDEN_PHRASES = [
    "一度だけ", "まず1回", "試しに", "1回だけ",
    "合格率", "内定率", "合格保証", "内定保証",
    "業界No.1", "No.1", "Ｎｏ.１", "No1", "ナンバーワン", "唯一の", "最高の",
    "casemasterpro.com",           # 誤URL（ハイフンなし）
    "casemaster pro.com",
]

# promo タイプのみ追加で禁止（プラン仕様の誤認を招く表現）
PROMO_FORBIDDEN_PHRASES = [
    "保証", "何度でも無料", "無料で無制限", "完全無料",
]

_URL_CHARS = r"A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%"
_URL_RE = re.compile(rf"https?://[{_URL_CHARS}]+", re.IGNORECASE)
# スキームなしの自サイトドメイン（X は自動リンク化する）
_BARE_SITE_RE = re.compile(
    rf"(?<![A-Za-z0-9\-./@])(?:www\.)?casemaster-pro\.com(?:/[{_URL_CHARS}]*)?",
    re.IGNORECASE,
)
# スキームなしの一般ドメイン（重み計算用。X はこれも URL=23 と数える）
_BARE_DOMAIN_RE = re.compile(
    rf"(?<![A-Za-z0-9\-./@])(?:[A-Za-z0-9\-]+\.)+(?:com|jp|net|org|io|co|ai|me|info|biz|app|dev)"
    rf"(?![A-Za-z0-9\-])(?:/[{_URL_CHARS}]*)?",
    re.IGNORECASE,
)
_TRAILING_PUNCT = ".,;:!?'\")]"


def _split_trailing(url: str) -> tuple[str, str]:
    """URL 末尾に付いた文末記号を切り離す"""
    trail = ""
    while url and url[-1] in _TRAILING_PUNCT:
        trail = url[-1] + trail
        url = url[:-1]
    return url, trail


def _ensure_scheme(text: str) -> str:
    """スキームなしの casemaster-pro.com を https:// 付きにする"""
    return _BARE_SITE_RE.sub(lambda m: "https://" + m.group(0), text)


def _is_site_url(url: str) -> bool:
    try:
        return (urlsplit(url).hostname or "").lower() in SITE_HOSTS
    except ValueError:
        return False


def iter_site_urls(text: str) -> list[str]:
    """テキスト内の casemaster-pro.com への URL（スキーム補完後）を返す"""
    urls = []
    for m in _URL_RE.finditer(_ensure_scheme(text)):
        url, _ = _split_trailing(m.group(0))
        if _is_site_url(url):
            urls.append(url)
    return urls


def with_utm(url: str, campaign: str) -> str:
    """1つの URL に UTM を付与する（既存クエリは保持、既存 utm_* は置換）"""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k not in UTM_KEYS]
    query += [("utm_source", "x"), ("utm_medium", "social"), ("utm_campaign", campaign)]
    return urlunsplit(("https", parts.netloc.lower(), parts.path or "/",
                       urlencode(query), parts.fragment))


def add_utm(text: str, campaign: str) -> str:
    """テキスト中の casemaster-pro.com への URL すべてに UTM を付与する（冪等）"""
    def _repl(m: re.Match) -> str:
        url, trail = _split_trailing(m.group(0))
        if not _is_site_url(url):
            return m.group(0)
        return with_utm(url, campaign) + trail

    return _URL_RE.sub(_repl, _ensure_scheme(text))


def twitter_weight(text: str) -> int:
    """
    X の重み付き文字数（保守的近似）。
    URL は t.co 換算で 23、それ以外は ASCII=1 / 非ASCII（日本語・記号・絵文字）=2。
    """
    url_count = 0

    def _strip(m: re.Match) -> str:
        nonlocal url_count
        url, trail = _split_trailing(m.group(0))
        url_count += 1
        return trail

    rest = _URL_RE.sub(_strip, text)
    rest = _BARE_DOMAIN_RE.sub(_strip, rest)
    weight = url_count * TCO_URL_WEIGHT
    for ch in rest:
        weight += 1 if ord(ch) <= 0x007F else 2
    return weight


def check_text(text: str, content_type: str, check_min: bool = False) -> list[str]:
    """
    投稿テキストを機械的に検証し、エラーメッセージのリストを返す（空なら合格）。
    check_min=True のときは下限重みもチェックする（生成時のみ）。
    """
    errors: list[str] = []

    if not text.strip():
        return ["空のテキスト"]

    w = twitter_weight(text)
    if w > MAX_TWEET_WEIGHT:
        errors.append(f"文字数超過: Twitter重み{w}（上限{MAX_TWEET_WEIGHT}）")
    elif check_min and w < MIN_TWEET_WEIGHT:
        errors.append(f"文字数不足: Twitter重み{w}（最低{MIN_TWEET_WEIGHT}以上必要）")

    lowered = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            errors.append(f"禁止フレーズ含む: 「{phrase}」")
    if content_type == "promo":
        for phrase in PROMO_FORBIDDEN_PHRASES:
            if phrase in text:
                errors.append(f"promo禁止フレーズ含む: 「{phrase}」")

    site_urls = iter_site_urls(text)
    if content_type == "promo" and not site_urls:
        errors.append(f"promoタイプにURL（https://{SITE_DOMAIN}/）が含まれていない")
    for url in site_urls:
        if (urlsplit(url).path or "/") != "/":
            errors.append(f"リンク先はトップページ（https://{SITE_DOMAIN}/）のみ可: {url}")

    return errors
