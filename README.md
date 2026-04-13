# CaseMaster Pro — X Bot

@CaseMasterPro アカウントの自動投稿システム。  
GitHub Actions + Claude Haiku + Supabase + Tweepy で動作する。

## 構成

```
casemaster-x-bot/
├── .github/workflows/
│   ├── schedule.yml   # 毎日0:30 JST: 本日の投稿3件を生成しキューに登録
│   └── poster.yml     # 30分ごと: キューから投稿時刻を過ぎたものをXに投稿
├── content/
│   ├── frameworks.yml # フレームワーク素材
│   ├── fermi.yml      # フェルミ推定問題素材
│   └── character.md   # キャラクター設定
├── config.py          # 設定・定数
├── generator.py       # Claude Haiku でツイート本文を生成
├── scheduler.py       # 本日の投稿枠選択 → 本文生成 → Supabase登録
├── poster.py          # Supabaseキュー確認 → Tweepy で投稿
├── supabase_setup.sql # テーブル作成SQL
└── requirements.txt
```

## セットアップ

### 1. Supabase テーブル作成
`supabase_setup.sql` を Supabase の SQL Editor で実行する。

### 2. GitHub Secrets を登録

| Secret名 | 内容 |
|---|---|
| `X_API_KEY` | X Developer Portal > Consumer Key |
| `X_API_SECRET` | Consumer Secret |
| `X_ACCESS_TOKEN` | Access Token |
| `X_ACCESS_TOKEN_SECRET` | Access Token Secret |
| `ANTHROPIC_API_KEY` | Anthropic Console |
| `SUPABASE_URL` | Project Settings > API > Project URL |
| `SUPABASE_SERVICE_KEY` | Project Settings > API > service_role key |
| `SITE_URL` | `https://casemasterpro.com`（任意） |

### 3. GitHub リポジトリにプッシュ
Actions が自動的にスケジュール実行される。

## 投稿スケジュール

6つの時間枠から毎日3枠を選ぶ（日付シードで冪等）。

| 枠名 | 時間帯 (JST) |
|---|---|
| 朝A | 6:55 〜 8:20 |
| 朝B | 9:10 〜 10:40 |
| 昼 | 11:45 〜 13:35 |
| 午後 | 14:20 〜 16:10 |
| 夕方 | 17:30 〜 19:40 |
| 夜 | 20:45 〜 23:10 |

## コンテンツタイプ（9種）

| タイプ | 内容 | 重み |
|---|---|---|
| framework | フレームワーク解説 | 15 |
| tips | 面接実践tips | 15 |
| question | 練習問題 | 13 |
| fermi | フェルミ推定問題 | 12 |
| mistake | よくある失敗・NG | 12 |
| terminology | コンサル用語解説 | 10 |
| industry | 業界別ケース切り口 | 10 |
| quote | 名言・格言 | 8 |
| promo | ツール紹介 | 5 |

## ローカル実行・テスト

```bash
# 依存ライブラリ
pip install -r requirements.txt

# .env を用意
cp .env.example .env
# → 各値を記入

# ドライラン（DB・X投稿なし）
python scheduler.py --dry
python poster.py --dry

# コンテンツ生成テスト（1件）
python generator.py tips
python generator.py framework
```

## API使用量目安（X Free Tier）

- 投稿: 3件/日 × 30日 = 90件/月（上限500件/月に対して余裕あり）
- poster.yml は30分ごとに実行されるが、投稿がない場合は即終了する
