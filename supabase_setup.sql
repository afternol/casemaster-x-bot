-- x_post_queue テーブル
-- Supabase SQL Editor で実行してください

CREATE TABLE IF NOT EXISTS x_post_queue (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  content_type text        NOT NULL,
  text         text        NOT NULL,
  scheduled_at timestamptz NOT NULL,
  status       text        NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'posted', 'failed')),
  tweet_id     text,
  posted_at    timestamptz,
  error        text,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- インデックス（poster.py の検索を高速化）
CREATE INDEX IF NOT EXISTS idx_x_post_queue_status_scheduled
  ON x_post_queue (status, scheduled_at);

-- RLS は無効（service_role key でアクセスするため）
ALTER TABLE x_post_queue DISABLE ROW LEVEL SECURITY;

-- 確認用クエリ
-- SELECT * FROM x_post_queue ORDER BY scheduled_at DESC LIMIT 20;
