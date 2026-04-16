"""
CaseMaster Pro X Bot — 投稿実行モジュール
30分ごとに GitHub Actions で実行される。

Supabase の x_post_queue から scheduled_at を過ぎた pending レコードを取得し、
Tweepy で X に投稿する。
"""
import sys
from datetime import datetime, timezone

import tweepy

from config import (
    X_API_KEY, X_API_SECRET,
    X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
    SUPABASE_URL, SUPABASE_SERVICE_KEY,
)


def _get_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True,
    )


def run_poster(dry_run: bool = False) -> None:
    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    now_iso = datetime.now(timezone.utc).isoformat()

    # scheduled_at <= now かつ status = pending のレコードを取得
    result = (
        sb.table("x_post_queue")
        .select("*")
        .eq("status", "pending")
        .lte("scheduled_at", now_iso)
        .order("scheduled_at")
        .limit(5)
        .execute()
    )
    rows = result.data

    if not rows:
        print("[poster] 投稿対象なし")
        return

    print(f"[poster] {len(rows)} 件を投稿します")
    client = None if dry_run else _get_client()

    # 認証アカウント確認（どのユーザーとして認証されているか）
    if client:
        try:
            me = client.get_me()
            print(f"[poster] 認証ユーザー: id={me.data.id} name={me.data.name}")
        except Exception as auth_err:
            print(f"[poster] 認証確認失敗: {auth_err}")

    for row in rows:
        row_id = row["id"]
        text   = row["text"]
        ctype  = row["content_type"]
        sched  = row["scheduled_at"]

        print(f"  id={row_id} type={ctype} scheduled={sched}")
        # テキスト詳細ログ（問題診断用）
        print(f"  [text] len={len(text)} repr_first100={repr(text[:100])}")
        text_stripped = text.strip()
        if text_stripped != text:
            print(f"  [warn] テキストに前後の空白/改行あり → strip() 適用")
            text = text_stripped

        if dry_run:
            print(f"  [DRY RUN] {text[:80]}{'...' if len(text) > 80 else ''}")
            continue

        try:
            response = client.create_tweet(text=text, user_auth=True)
            tweet_id = str(response.data["id"])

            sb.table("x_post_queue").update({
                "status":    "posted",
                "tweet_id":  tweet_id,
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "error":     None,
            }).eq("id", row_id).execute()

            print(f"  [完了] tweet_id={tweet_id}")

        except tweepy.TweepyException as e:
            error_msg = str(e)
            # 詳細エラー情報を出力（根本原因特定用）
            print(f"  [失敗] {error_msg}")
            if hasattr(e, "api_codes"):
                print(f"  [詳細] api_codes={e.api_codes}")
            if hasattr(e, "api_messages"):
                print(f"  [詳細] api_messages={e.api_messages}")
            if hasattr(e, "response") and e.response is not None:
                print(f"  [詳細] status_code={e.response.status_code}")
                try:
                    print(f"  [詳細] response_body={e.response.text[:500]}")
                except Exception:
                    pass

            sb.table("x_post_queue").update({
                "status": "failed",
                "error":  error_msg,
            }).eq("id", row_id).execute()

    print("[poster] 処理完了")


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    run_poster(dry_run=dry)
