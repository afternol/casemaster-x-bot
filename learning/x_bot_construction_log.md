# CaseMaster Pro X Bot — 構築・運用ナレッジ

作成日: 2026-04-13  
対象アカウント: @casemaster_pro  
リポジトリ: https://github.com/afternol/casemaster-x-bot

---

## 1. 全体構成の概要

### アーキテクチャ選定

| 選択肢 | 採用理由 / 不採用理由 |
|---|---|
| GitHub Actions（採用） | PCが不要・無料枠で運用可能・cronで定時実行できる |
| Vercel | Next.jsのホスティング用途。cronジョブには不向き |
| Windows タスクスケジューラ | PCの電源が入っている必要があり安定性に欠ける |
| APScheduler（常駐プロセス） | サーバーが必要で管理コストが高い |

### 技術スタック
- **言語**: Python 3.11
- **X投稿**: Tweepy v4（OAuth 1.0a）
- **コンテンツ生成**: Claude Sonnet（Anthropic API）
- **キュー管理**: Supabase（PostgreSQL）
- **スケジューリング**: GitHub Actions cron

---

## 2. ファイル構成と役割

```
casemaster-x-bot/
├── .github/workflows/
│   ├── schedule.yml    # 毎日0:30 JST: 本日の投稿を生成・Supabaseに登録
│   └── poster.yml      # 30分ごと: キューから投稿時刻を過ぎたものをXに投稿
├── content/
│   ├── character.md    # システムプロンプト（トーン・禁止事項・仕様）
│   ├── frameworks.yml  # フレームワーク素材（15種）
│   └── fermi.yml       # フェルミ推定問題素材（15問）
├── config.py           # 設定・定数（時間枠・コンテンツタイプ・重み）
├── generator.py        # Claude APIでツイートを生成・バリデーション
├── scheduler.py        # 本日の枠選択・生成・Supabase INSERT
├── poster.py           # キュー確認・Tweepy投稿
├── supabase_setup.sql  # x_post_queueテーブル作成SQL
├── requirements.txt
└── learning/           # 構築・運用ナレッジ（本ファイル）
```

---

## 3. 投稿フロー（全体）

```
毎日 0:30 JST
GitHub Actions (schedule.yml)
    ↓
scheduler.py
    ① 日付シードで6枠から3枠を選択（冪等）
    ② Supabaseから過去30件の投稿済みテキストを取得（重複回避用）
    ③ 各枠のコンテンツタイプを重み付きで選択
    ④ Claude Sonnet でツイート本文を生成
    ⑤ Pythonコードでバリデーション（失敗時は最大3回リトライ）
    ⑥ Supabase x_post_queue に INSERT（scheduled_atを指定）
    ↓
30分ごと
GitHub Actions (poster.yml)
    ↓
poster.py
    ① scheduled_at ≤ 現在時刻 かつ status=pending を検索
    ② 該当なし → 即終了
    ③ 該当あり → Tweepyで投稿
    ④ Supabaseのstatusを "posted" に更新（tweet_id・posted_atも記録）
```

---

## 4. 投稿時間の設計

### 6つの時間枠（JST）

| 枠名 | 時間帯 | 想定ユーザー行動 |
|---|---|---|
| 朝A | 6:55〜8:20 | 通勤・通学前 |
| 朝B | 9:10〜10:40 | 始業前・授業前の隙間 |
| 昼 | 11:45〜13:35 | 昼休み |
| 午後 | 14:20〜16:10 | 午後の休憩 |
| 夕方 | 17:30〜19:40 | 帰宅中 |
| 夜 | 20:45〜23:10 | 自宅でリラックス時 |

### 日次選択のロジック
- 6枠から3枠を**日付シードのランダム**で選択
- シード = `int(YYYYMMDD)` → 同じ日に何度実行しても同じ3枠が選ばれる（冪等性）
- 朝枠が選ばれる確率: 約80%（P(朝なし) = C(4,3)/C(6,3) = 20%）
- 各枠内の時刻も日付+スロットインデックスでシード → 毎日異なる時刻で投稿

### bot判定を避けるための設計
- 毎日同じ時刻に投稿しない（枠内でランダム）
- 3枠が自然な時間帯に分散するよう設計

---

## 5. コンテンツ生成の設計

### 9つのコンテンツタイプと重み

| タイプ | 重み | 概要 | 素材 |
|---|---|---|---|
| framework | 15 | フレームワーク解説 | frameworks.yml（15種） |
| tips | 15 | 面接実践tips | プロンプト |
| question | 13 | 練習問題 | プロンプト内10問 |
| fermi | 12 | フェルミ推定問題 | fermi.yml（15問） |
| mistake | 12 | よくある失敗・NG | プロンプト |
| terminology | 10 | コンサル用語解説 | プロンプト内20語 |
| industry | 10 | 業界別ケース切り口 | プロンプト内14業界 |
| quote | 8 | 名言・格言 | プロンプト内8件 |
| promo | 5 | ツール紹介 | プロンプト |

**設計思想**: 役立つ情報（非promo）が95%、ツール紹介が5%。価値提供を優先してフォロワーを獲得し、自然な流れで集客する。

### Claude APIへの渡し方
```python
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=300,
    system=character_md_content + 今日のJST日付,  # システムプロンプト
    messages=[{"role": "user", "content": タイプ別プロンプト}]
)
```

- **システムプロンプト**: character.md（ルール・仕様・禁止事項）＋当日の日付（JST動的付与）
- **ユーザープロンプト**: タイプ別の生成指示＋過去ツイートの重複回避ブロック
- **モデル**: claude-sonnet-4-6（精度重視。当初haiku→sonnetに変更）

---

## 6. 重複回避の仕組み

### 2段階の重複防止

**段階1: 過去ツイートをプロンプトに渡す**
```python
# scheduler.py
recent_tweets = fetch_recent_tweets(sb, limit=30)  # Supabaseから取得
text = generate_tweet_text(content_type, recent_tweets=recent_tweets)
recent_tweets.insert(0, text)  # 同日の次の枠でも使う
```

**段階2: Claudeへの指示（プロンプト内）**
```
【重要】以下の過去ツイートと同じネタ・似た切り口・似た文章は絶対に避けてください:
- [過去ツイート1]
- [過去ツイート2] ...
```

同日3枠の間でも順次リストに追加することで、同日内の重複も防ぐ。

---

## 7. バリデーションの設計思想

### Claudeの自己チェックに依存しない理由
- Claudeは「確認した」と言いながらハルシネーションを起こすことがある
- ルールの遵守をAIに任せることは信頼性が低い
- コードによる機械的チェックは100%再現性がある

### Pythonコードによるバリデーション（generator.py）

```python
FORBIDDEN_PHRASES = [
    "一度だけ", "まず1回", "試しに", "1回だけ",   # 単発利用促進
    "合格率", "内定率", "合格保証", "内定保証",      # 誇大表現
    "業界No.1", "業界ナンバーワン", "唯一の",        # 根拠なし
    "casemasterpro.com",                            # 誤URL（ハイフンなし）
]
```

| チェック項目 | 方法 |
|---|---|
| 140文字以内 | `len(text) > 140` |
| 禁止フレーズ | 文字列一致 |
| 誤URL検出 | `casemasterpro.com` の有無 |
| promoのURL必須 | `casemaster-pro.com` の存在確認 |

**リトライ**: 失敗時は違反内容をプロンプトに追記して再生成（最大3回）。

---

## 8. character.mdの設計思想

### なぜシステムプロンプトとして使うか
- 9種すべてのコンテンツタイプに自動でルールが適用される
- character.mdを編集・プッシュするだけで全体に即反映
- 個別のプロンプトに同じルールを重複記述しなくて済む

### 盛り込む内容の分類と判断基準

| 種類 | character.mdに入れるか | 理由 |
|---|---|---|
| トーン・文体 | ✅ 入れる | Claudeが解釈できる |
| 禁止フレーズ・表現 | ✅ 入れる（＋コードでも検証） | 二重防御 |
| 正確な仕様（価格・回数） | ✅ 入れる | コードから取得した事実のみ記載 |
| 季節性（月別カレンダー） | ❌ 入れない | 陳腐化リスク・会社によって違う |
| 自己チェックリスト | ❌ 入れない | Claudeの自己申告は信頼性が低い |
| 今日の日付 | コードで動的に付与 | 毎回最新の日付が渡される |

### 季節性について（重要な教訓）
当初、character.mdに「6〜8月はサマーインターン」などの月別カレンダーをハードコードしようとしたが、以下の理由でやめた：
- 就活カレンダーは外資・国内・転職で大きく異なる
- 経団連ルールも形骸化しており会社ごとに違う
- ファイルが古くなっても気づかず誤情報を発信するリスクがある

**解決策**: 毎回の生成時に今日のJST日付をシステムプロンプトに動的追記。就活シーズンの判断はClaudeに委ねる。

---

## 9. Supabaseテーブル設計

```sql
CREATE TABLE x_post_queue (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type text        NOT NULL,
    text         text        NOT NULL,
    scheduled_at timestamptz NOT NULL,
    status       text        NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'posted', 'failed')),
    tweet_id     text,        -- 投稿成功時のX上のID
    posted_at    timestamptz, -- 実際の投稿日時
    error        text,        -- 失敗時のエラーメッセージ
    created_at   timestamptz NOT NULL DEFAULT now()
);
```

**statusの活用**:
- `pending` + `scheduled_at <= now()` → 投稿対象
- `posted` → 重複回避のソースデータ（過去30件を取得）
- `failed` → エラー調査・手動再投稿の判断材料

---

## 10. GitHub Actions設定

### schedule.yml（毎日0:30 JST）
```yaml
on:
  schedule:
    - cron: '30 15 * * *'  # UTC 15:30 = JST 翌0:30
  workflow_dispatch:        # 手動実行も可能（dry_run選択可）
```

### poster.yml（30分ごと）
```yaml
on:
  schedule:
    - cron: '*/30 * * * *'
  workflow_dispatch:        # 手動実行も可能（dry_run選択可）
```

### GitHub Actions無料枠の消費量（Privateリポジトリ）
| ワークフロー | 頻度 | 実行時間/回 | 月間合計 |
|---|---|---|---|
| poster.yml | 48回/日 | 約20〜30秒 | 約400〜720分/月 |
| schedule.yml | 1回/日 | 約30秒 | 約15分/月 |
| **合計** | | | **約415〜735分/月** |

無料枠2,000分/月に対して余裕あり。PCへの負荷はゼロ（GitHub側のクラウドで実行）。

---

## 11. X API認証の構造と注意点

### アプリとアカウントの関係
- Developer Portalでは「アプリ」と「Xアカウント」が分離している
- **アプリ**: Consumer Key/Secretを持つ
- **アクセストークン**: 特定のXアカウントへの投稿権限をアプリに付与する
- アクセストークンの「For @○○」表示で、どのアカウントへの権限かを確認できる

### 今回のトラブルと教訓

**トラブル1: 401 Unauthorized（アプリ違い）**
- 原因: Developer Portalに2つのアプリがあり、誤ったアプリのキーを使用
- `casemaster-pro-bot`（不完全）ではなく `20433390493902356448casemaster_`（正しい）のキーが必要
- **教訓**: アプリ名とXアカウント名は一致しないことがある。アクセストークンの「For @○○」で確認する

**トラブル2: 402 Payment Required（クレジット不足）**
- 原因: 「Pay Per Use」プランで残高0だった
- **教訓**: Pay Per Useは都度クレジット補充が必要。月次で残高確認する

**トラブル3: user_auth=Trueの必要性**
- Tweepy v4では `create_tweet()` に `user_auth=True` を明示しないとOAuth 2.0が使われ投稿できない
- **正しい実装**:
```python
client.create_tweet(text=text, user_auth=True)
```

### スレッド投稿の実装
```python
r1 = client.create_tweet(text=tweet1, user_auth=True)
r2 = client.create_tweet(text=tweet2, in_reply_to_tweet_id=r1.data['id'], user_auth=True)
r3 = client.create_tweet(text=tweet3, in_reply_to_tweet_id=r2.data['id'], user_auth=True)
```

### 固定ツイートの設定
X API v2では固定ツイートのAPIがないため、X上で手動設定する。
対象ツイートの「…」→「プロフィールに固定する」。

---

## 12. コンテンツ戦略の設計思想

### マネタイズの観点
- **Explorer（無料）→ Pro/Elite転換**が主な収益源
- 無料ユーザーには「月3回では足りない」と自然に感じさせる
- Elite（¥9,800/月・月30回）が人気プランで最重要誘導先
- 「毎日練習するほど上達する」訴求 → 高頻度利用 → 上位プラン転換

### 禁止事項の根拠

| 禁止表現 | 理由 |
|---|---|
| 「合格率○○%」 | 根拠となるデータが存在しない |
| 「一度だけ試して」 | 単発利用を促すと課金転換率が下がる |
| 「業界No.1」 | 比較データなし・景品表示法リスク |
| 成功事例の創作 | 実績不明・ユーザーへの不誠実 |
| 誇張した効果表現 | AIの限界を隠すことは信頼を損なう |

### ハルシネーション防止の多層防御

```
Layer 1: character.md（システムプロンプト）
  → 禁止表現・正確な仕様をClaudeに伝える

Layer 2: Pythonバリデーション（generator.py）
  → 文字数・禁止フレーズ・URLをコードで機械的に検証

Layer 3: リトライ（最大3回）
  → 失敗時は違反内容を追記して再生成
```

---

## 13. GitHub Secretsの一覧

| Secret名 | 用途 | 取得場所 |
|---|---|---|
| `X_API_KEY` | X API Consumer Key | Developer Portal > アプリ > Keys and Tokens |
| `X_API_SECRET` | X API Consumer Secret | 同上 |
| `X_ACCESS_TOKEN` | @casemaster_proへの投稿権限 | 同上 > Access Token and Secret |
| `X_ACCESS_TOKEN_SECRET` | 同上 | 同上 |
| `ANTHROPIC_API_KEY` | Claude API | console.anthropic.com |
| `SUPABASE_URL` | SupabaseプロジェクトURL | Project Settings > API |
| `SUPABASE_SERVICE_KEY` | Supabase service_roleキー | 同上 |
| `SITE_URL` | https://casemaster-pro.com/ | 固定値 |

---

## 14. 運用上の注意点

### 月次チェックリスト
- [ ] X API Pay Per Useのクレジット残高確認・補充
- [ ] Supabase `x_post_queue` の `status='failed'` 行を確認
- [ ] GitHub Actions実行ログで投稿品質チェック
- [ ] フォロワー数・エンゲージメント率の確認

### コンテンツ追加・変更方法
| 変更内容 | 対象ファイル |
|---|---|
| フレームワーク素材追加 | `content/frameworks.yml` |
| フェルミ推定問題追加 | `content/fermi.yml` |
| 投稿ルール・トーン変更 | `content/character.md` |
| 禁止フレーズ追加 | `generator.py` の `FORBIDDEN_PHRASES` |
| 投稿時間帯変更 | `config.py` の `TIME_WINDOWS` |
| コンテンツタイプの重み変更 | `config.py` の `CONTENT_TYPES` |

### ドライランでの事前確認方法
```bash
# GitHub Actionsの手動実行でdry_run=trueを選択
# またはローカルで:
python scheduler.py --dry
python poster.py --dry
python generator.py tips       # 特定タイプの生成テスト
python generator.py framework
```

---

## 15. 今後の改善アイデア

- **エンゲージメント計測**: いいね・RT数をSupabaseに記録し、タイプ別の効果測定
- **高パフォーマンスコンテンツの重み自動調整**: 反応が多いタイプの重みを増やす
- **画像付き投稿**: フレームワーク図などを画像で投稿するとエンゲージメント向上が期待できる
- **季節イベント対応**: 就活解禁・インターン応募期などに合わせた特別コンテンツの手動追加
- **フォロワー属性分析**: どの時間帯・タイプが反応されやすいかを定期的に確認する
