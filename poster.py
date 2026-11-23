"""
CaseMaster Pro X Bot — 投稿実行モジュール
30分ごとに GitHub Actions で実行される。

1回の実行で投稿するのは最大 1 件。
1. 予定時刻から STALE_AFTER_HOURS 時間以上過ぎた pending は投稿せず failed（[stale]）にする
2. 直近 MIN_POST_INTERVAL_HOURS 時間以内に投稿済みなら見送る（二重投稿防止）
3. 時刻を過ぎた pending を 1 件だけ UTM 付与・最終検証してから投稿する

終了コード: 0 = 投稿成功 / 対象なし / 見送り、1 = 投稿失敗・検証NG（行に error を記録済み）
"""
import sys
from datetime import datetime, timedelta, timezone

from config import (
    MIN_POST_INTERVAL_HOURS, STALE_AFTER_HOURS,
    SUPABASE_SERVICE_KEY, SUPABASE_URL,
    X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_API_KEY, X_API_SECRET,
)
from text_rules import add_utm, check_text, twitter_weight


def _get_client():
    import tweepy
    return tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
        # True だと 429 時に最大15分スリープ → ジョブタイムアウトで原因が隠れる
        wait_on_rate_limit=False,
    )


def _describe_error(e: Exception) -> str:
    parts = [f"{type(e).__name__}: {e}"]
    resp = getattr(e, "response", None)
    if resp is not None:
        parts.append(f"status_code={getattr(resp, 'status_code', '?')}")
        try:
            parts.append(f"body={resp.text[:500]}")
        except Exception:
            pass
    return " | ".join(parts)


def _mark_stale(sb, now: datetime, dry_run: bool) -> None:
    cutoff = (now - timedelta(hours=STALE_AFTER_HOURS)).isoformat()
    stale = (
        sb.table("x_post_queue")
        .select("id,scheduled_at,content_type")
        .eq("status", "pending")
        .lt("scheduled_at", cutoff)
        .execute()
    ).data or []
    for row in stale:
        print(f"[poster] stale（{STALE_AFTER_HOURS}h超過）→ 投稿せず failed: "
              f"id={row['id']} type={row['content_type']} scheduled={row['scheduled_at']}")
        if dry_run:
            continue
        sb.table("x_post_queue").update({
            "status": "failed",
            "error": f"[stale] 予定時刻から{STALE_AFTER_HOURS}時間以上経過したため投稿せずスキップ",
        }).eq("id", row["id"]).eq("status", "pending").execute()


def run_poster(dry_run: bool = False) -> int:
    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    now = datetime.now(timezone.utc)

    # 1) 古すぎる pending は一斉投稿せずスキップ扱いにする
    _mark_stale(sb, now, dry_run)

    # 2) 投稿対象（予定時刻を過ぎ、かつ stale でない pending）を最古から 1 件
    rows = (
        sb.table("x_post_queue")
        .select("*")
        .eq("status", "pending")
        .lte("scheduled_at", now.isoformat())
        .gte("scheduled_at", (now - timedelta(hours=STALE_AFTER_HOURS)).isoformat())
        .order("scheduled_at")
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        print("[poster] 投稿対象なし")
        return 0

    # 3) 直近に投稿済みなら見送り（1日1投稿の安全弁）
    recent = (
        sb.table("x_post_queue")
        .select("id,posted_at")
        .eq("status", "posted")
        .gte("posted_at", (now - timedelta(hours=MIN_POST_INTERVAL_HOURS)).isoformat())
        .limit(1)
        .execute()
    ).data or []
    if recent:
        print(f"[poster] 直近{MIN_POST_INTERVAL_HOURS}時間以内に投稿済み（posted_at={recent[0]['posted_at']}）。見送り。")
        return 0

    row = rows[0]
    row_id = row["id"]
    ctype = row["content_type"]
    text = add_utm(row["text"].strip(), ctype)
    print(f"[poster] id={row_id} type={ctype} scheduled={row['scheduled_at']} "
          f"len={len(text)} weight={twitter_weight(text)}")

    # 4) 投稿直前の最終チェック（重み上限・禁止表現・リンク先）
    errors = check_text(text, ctype)
    if errors:
        msg = f"[invalid] 投稿前チェックNG: {'; '.join(errors)}"
        print(f"[poster] {msg}")
        if not dry_run:
            sb.table("x_post_queue").update({"status": "failed", "error": msg}).eq("id", row_id).execute()
        return 1

    if dry_run:
        print(f"[poster] [DRY RUN] {text}")
        return 0

    # 5) 投稿
    try:
        response = _get_client().create_tweet(text=text, user_auth=True)
        tweet_id = str(response.data["id"])
    except Exception as e:
        msg = _describe_error(e)
        print(f"[poster] [失敗] {msg}")
        sb.table("x_post_queue").update({"status": "failed", "error": msg[:2000]}).eq("id", row_id).execute()
        return 1

    print(f"[poster] [完了] tweet_id={tweet_id}")
    try:
        sb.table("x_post_queue").update({
            "status":    "posted",
            "text":      text,          # UTM 付与後の実投稿テキストを保存
            "tweet_id":  tweet_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "error":     None,
        }).eq("id", row_id).execute()
    except Exception as e:
        # 投稿は成功しているが DB が pending のまま → 次回再投稿の恐れがあるため必ず失敗として通知
        print(f"[poster] [要対応] 投稿済みだがDB更新失敗 id={row_id} tweet_id={tweet_id}: {type(e).__name__}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_poster(dry_run="--dry" in sys.argv))
