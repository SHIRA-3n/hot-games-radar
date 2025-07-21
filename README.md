# 🎮 Hot Games Radar

日本のストリーマー向けゲーム市場分析ツール

## 概要

Hot Games Radarは、Twitch、Steam、Google Trends、Twitterなどの複数のデータソースを分析し、日本のストリーマーにとって配信に適したゲームを発見するためのツールです。

### 主な機能

- **市場競合分析**: 日本のストリーマーの競合密度を分析
- **トレンド検出**: Google TrendsとTwitterで急上昇中のゲームを発見
- **配信最適化**: あなたの配信スケジュールに合ったゲームを推奨
- **オーディエンス分析**: 日本語視聴者の割合を評価
- **イベント追跡**: 今後のゲームイベントとアップデートを監視
- **自動通知**: Discord webhookで分析結果を自動通知

## セットアップ

### 1. 依存関係のインストール

```bash
pip3 install -r requirements.txt
```

### 2. 環境変数の設定

以下の環境変数を設定してください：

```bash
export TWITCH_CLIENT_ID="your_twitch_client_id"
export TWITCH_CLIENT_SECRET="your_twitch_client_secret"
export DISCORD_WEBHOOK_URL_3D="discord_webhook_for_3_day_notifications"
export DISCORD_WEBHOOK_URL_7D="discord_webhook_for_7_day_notifications"
export DISCORD_WEBHOOK_URL_30D="discord_webhook_for_30_day_notifications"
```

### 3. 設定ファイルのカスタマイズ

`config.yaml`を編集して、あなたのチャンネル情報と配信スケジュールを設定：

```yaml
channel_profile:
  avg_viewers: 10  # あなたの配信の平均視聴者数

stream_slots:
  mon: ["24-27"]  # あなたの配信スケジュール（24時間形式）
  tue: ["24-27"]
  # ... 他の曜日も同様に設定
```

## 使用方法

### 分析の実行

```bash
python3 run.py
```

分析が開始され、最大1000件のゲームが並行して処理されます。結果は設定されたDiscord webhookに自動送信されます。

## アーキテクチャ

### シグナル処理システム

各シグナルモジュール（`radar/signals/`）が独立してゲームの異なる側面を分析：

- **competition.py**: 日本のストリーマー競合分析
- **google_trends.py**: Google検索トレンド分析
- **steam_ccu.py**: Steam同時接続ユーザー追跡
- **twitch_drops.py**: Twitch Dropsキャンペーン検出
- **jp_ratio.py**: 日本語オーディエンス浸透度分析
- **slot_fit.py**: 配信スケジュール最適化スコア
- **twitter.py**: Twitterセンチメント分析
- **upcoming_event.py**: ゲームイベントカレンダー
- **market_health.py**: 総合市場健全性評価
- **steam_news.py**: Steamニュース更新監視

### スコア計算

各シグナルは0-1のスコアを返し、`config.yaml`の重みに基づいて加重平均で最終スコアを算出します。

## カスタマイズ

### 新しいシグナルの追加

1. `radar/signals/your_signal.py`に新しいファイルを作成
2. `calculate_signal()`関数を実装（app_id -> スコアの辞書を返す）
3. `radar/core.py`にインポートと呼び出しを追加
4. `config.yaml`に対応する重みを追加

### 通知設定

`config.yaml`の`notification_score_threshold`を調整してスコア閾値を変更し、通知頻度をコントロールできます。

## 技術仕様

- **Python 3.13.5**
- **非同期処理**: asyncio を使用した並行API処理
- **外部API**: Twitch API、Steam API、Google Trends、Twitter API
- **文字列マッチング**: rapidfuzzを使用したファジーマッチング
- **認証**: OAuth2対応

---

**注意**: 各APIの利用規約を遵守し、適切なレート制限を設定してご利用ください。
