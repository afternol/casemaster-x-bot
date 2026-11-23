"""
402 Payment Required などで status=failed になった過去レコードを、
今後の「まだ投稿が入っていない日」の固定投稿時刻（POST_TIME_JST）に
1日1件ずつ割り当てて status=pending に戻す。

1日1投稿ルールを守るため、pending/posted が既にある日には入れない。
割り当てた日は Daily Schedule が「有効な投稿あり」と判断して新規生成をスキップする。
検証NG（重み超過・禁止表現）や生成失敗の行は再投入しない。

使い方:
  python requeue_failed.py --dry        # ドライラン
  python requeue_failed.py              # 本実行
  python requeue_failed.py --days 30    # 直近N日分のfailedを対象 (default 14)
  python requeue_failed.py --limit 7    # 再投入する最大件数 (default 7)
"""
import sys
from datetime import date, datetime, timedelta, timezone

from config import DAILY_POST_COUNT, SUPABASE_SERVICE_KEY, SUPABASE_URL
from scheduler import slot_time
from text_rules import add_utm, check_text

JST = timezone(timedelta(hours=9))
SKIP_ERROR_PREFIXES = ("[invalid]", "[gen_error]")


def parse_args():
    dry = "--dry" in sys.argv
    days, limit = 14, 7
    for i, a in enumerate(sys.argv):
        if a == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])
        if a == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
    return dry, days, limit


def get_used_days(sb, start_date: date, end_date: date) -> dict[date, int]:
    """日付ごとの pending/posted 件数"""
    start_iso = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=JST).isoformat()
    end_iso   = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=JST).isoformat()
    rows = (
        sb.table("x_post_queue")
        .select("scheduled_at")
        .in_("status", ["pending", "posted"])
        .gte("scheduled_at", start_iso)
        .lte("scheduled_at", end_iso)
        .execute()
    ).data or []
    used: dict[date, int] = {}
    for r in rows:
        d = datetime.fromisoformat(r["scheduled_at"]).astimezone(JST).date()
        used[d] = used.get(d, 0) + 1
    return used


def main() -> int:
    from supabase import create_client

    dry, days, limit = parse_args()
    print(f"[requeue] dry_run={dry} days={days} limit={limit}")
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    cutoff = (datetime.now(JST) - timedelta(days=days)).isoformat()
    failed = (
        sb.table("x_post_queue")
        .select("id, content_type, scheduled_at, text, error")
        .eq("status", "failed")
        .gte("scheduled_at", cutoff)
        .order("scheduled_at")
        .execute()
    ).data or []
    print(f"[requeue] failed レコード: {len(failed)} 件")

    candidates = []
    for r in failed:
        if (r.get("error") or "").startswith(SKIP_ERROR_PREFIXES):
            continue
        text = add_utm((r.get("text") or "").strip(), r["content_type"])
        if check_text(text, r["content_type"]):
            continue
        candidates.append((r, text))
    print(f"[requeue] 再投入可能（検証OK）: {len(candidates)} 件 → 最大 {limit} 件を再投入")
    candidates = candidates[:limit]
    if not candidates:
        print("[requeue] 対象なし。終了。")
        return 0

    now = datetime.now(JST)
    today = now.date()
    used = get_used_days(sb, today, today + timedelta(days=len(candidates) + 60))

    plan = []
    d = today
    for r, text in candidates:
        while used.get(d, 0) >= DAILY_POST_COUNT or slot_time(d) <= now + timedelta(minutes=10):
            d += timedelta(days=1)
        used[d] = used.get(d, 0) + 1
        plan.append((r["id"], slot_time(d), r["content_type"], text))

    print("\n[requeue] 再配置プラン:")
    for pid, t, ctype, text in plan:
        print(f"  {t.strftime('%Y-%m-%d %H:%M')} JST type={ctype} id={pid[:8]} text={text[:30]}...")

    if dry:
        print("[requeue] [DRY RUN] DB更新スキップ")
        return 0

    for pid, t, _, text in plan:
        sb.table("x_post_queue").update({
            "status": "pending",
            "scheduled_at": t.isoformat(),
            "text": text,
            "error": None,
        }).eq("id", pid).execute()
    print(f"[requeue] 完了: {len(plan)} 件を pending に戻しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
