# CaseMaster Pro — X Bot

@CaseMasterPro アカウントの自動投稿システム。  
GitHub Actions + Claude Haiku + Supabase + Tweepy で動作する。

## 構成

```
casemaster-x-bot/
├── .github/workflows/
│   ├── schedule.yml   # 毎日0:30 JST: 本日の投稿1件(20:00 JST)を生成しキューに登録 + keepalive
│   ├── poster.yml     # 30分ごと: 投稿時刻を過ぎたpendingを1件だけXに投稿
│   └── requeue_failed.yml # 手動: failed行を空き日の20:00に1日1件で再投入
├── content/
│   ├── frameworks.yml # フレームワーク素材
│   ├── fermi.yml      # フェルミ推定問題素材
│   └── character.md   # キャラクター設定
├── config.py          # 設定・定数
├── generator.py       # Claude でツイート本文を生成（検証NGは例外・キューに入れない）
├── text_rules.py      # 重み付き文字数(URL=23)・禁止表現・UTM付与（generator/poster共通）
├── scheduler.py       # 本日の1件(20:00 JST)の本文生成 → Supabase登録
├── poster.py          # Supabaseキュー確認 → 1件だけ Tweepy で投稿
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
| `SITE_URL` | `https://casemaster-pro.com/`（任意・**ハイフン必須**。未設定/誤設定時はこの既定値を使用） |

### 3. GitHub リポジトリにプッシュ
Actions が自動的にスケジュール実行される。

## 投稿スケジュール

**1日1投稿・毎日 20:00 JST 固定**（`config.POST_TIME_JST`）。

| 時刻 (JST) | 処理 |
|---|---|
| 0:30 | `schedule.yml`: 当日分1件を生成し pending 登録（既に pending/posted があればスキップ） |
| 20:00 以降の最初の poster 実行（通常 20:00〜20:30 台） | `poster.yml`: 1件投稿 |
| 23:00 を過ぎても未投稿 | 次の poster 実行で `failed`（error=`[stale]...`）にし、投稿しない |

- poster は1回の実行で最大1件。直近12時間以内に投稿済みなら見送る（二重投稿防止）
- promo（ツール紹介）は **毎週日曜（`PROMO_WEEKDAY`）に固定** ＝ 全体の約14%。それ以外の日は promo 以外から重み付き抽選
- 生成が検証NG（重み280超・禁止表現など）の場合はキューに入れず `failed`（`[invalid]`）を記録し、ワークフローは失敗終了
- 投稿失敗（402/403/429等）は行に error を記録し、ワークフローは失敗終了（GitHub からメール通知）

## リンク計測（UTM）

casemaster-pro.com への URL には必ず `utm_source=x&utm_medium=social&utm_campaign=<content_type>` を付与する
（既存クエリがあれば `&` で連結、既存 utm_* は置換）。リンク先はトップページのみ。
ハイフンなしドメイン `casemasterpro.com` は禁止フレーズとして検出する。

## keepalive（60日自動無効化の防止）

GitHub は60日間リポジトリに活動がないと scheduled workflow を無効化する。
`schedule.yml` の最終ステップが、最終コミットから30日以上経っていれば `.keepalive` を更新してコミットする。
GITHUB_TOKEN による push は他ワークフローを起動しないためループしない。

## コンテンツタイプ（30種）

種類と抽選の重みは `config.CONTENT_TYPES` を参照（promo は重み0で抽選対象外、日曜に固定配信）。

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
python generator.py relatable
python generator.py promo
```

## API使用量目安（X Free Tier）

- 投稿: 1件/日 × 30日 = 約30件/月
- poster.yml は30分ごとに実行されるが、投稿がない場合は即終了する（X API は呼ばない）
