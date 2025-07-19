# 【最終版テンプレート】この内容を radar/core.py に貼り付けてください

import os
import yaml
import json
from datetime import datetime, timezone
import requests

# twitchAPIのラッパーなどをインポート（プロジェクトの構成に合わせて調整）
from twitchAPI.twitch import Twitch

# 作成した全ての分析モジュール（センサー）をインポートします
from .signals import steam, twitch_data, twitter, slot_fit, competition # 仮のモジュール名

# ---------------------------------
# 設定ファイルの読み込み
# ---------------------------------
def load_config():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# ---------------------------------
# メインの処理
# ---------------------------------
def main():
    print("🚀 Hot Games Radar PRO - 起動します...")
    
    # 1. 設定ファイルを読み込む
    cfg = load_config()
    
    # 2. 各APIクライアントを初期化
    #    GitHub Actionsの環境変数からキーを安全に読み込みます
    try:
        twitch_api = Twitch(os.environ['TWITCH_CLIENT_ID'], os.environ['TWITCH_CLIENT_SECRET'])
    except Exception as e:
        print(f"❌ Twitch APIの初期化に失敗しました: {e}")
        return

    # 3. 分析対象となるゲームのリストを取得する (例: Twitchの上位ゲーム)
    #    この部分は実際のロジックに合わせて実装が必要です
    print("📡 Twitchから注目ゲームのリストを取得中...")
    try:
        # ここでは例としてダミーデータを使います
        games_to_analyze = [
            {'id': '509658', 'name': 'Just Chatting', 'viewer_count': 500000},
            {'id': '21779', 'name': 'League of Legends', 'viewer_count': 150000},
            {'id': '32982', 'name': 'Grand Theft Auto V', 'viewer_count': 120000},
        ]
        print(f"✅ {len(games_to_analyze)}件のゲームを分析対象とします。")
    except Exception as e:
        print(f"❌ ゲームリストの取得に失敗しました: {e}")
        return
        
    # 4. 各ゲームのスコアを計算
    print("⚙️ 各ゲームのスコアを計算中...")
    scored_games = []
    
    # 利用する分析モジュール（センサー）のリスト
    ENABLED_SIGNALS = [
        # steam,       # steam.py が完成したらコメントを外す
        # twitch_data, # twitch_data.py が完成したらコメントを外す
        # twitter,     # twitter.py が完成したらコメントを外す
        slot_fit,
        competition,
    ]

    for game in games_to_analyze:
        game_scores = {}
        game_flags = []
        
        # 全てのセンサーでスコアを計算
        for signal_module in ENABLED_SIGNALS:
            try:
                # 各モジュールに、ゲーム情報、設定、APIクライアントを渡してスコアを計算させる
                result = signal_module.score(game=game, cfg=cfg, twitch_api=twitch_api)
                
                if result:
                    game_scores.update(result)
                    # 通知用のタグがあれば追加
                    if 'source_hit_flags' in result:
                        game_flags.extend(result.pop('source_hit_flags'))

            except Exception as e:
                print(f"⚠️ {game['name']} の {signal_module.__name__} でエラー: {e}")

        # 合計スコアを計算
        total_score = sum(v for k, v in game_scores.items() if isinstance(v, (int, float)))
        
        game['total_score'] = total_score
        game['scores'] = game_scores
        game['flags'] = list(set(game_flags)) # 重複を削除
        scored_games.append(game)

    # 5. スコアの高い順に並び替え
    scored_games.sort(key=lambda x: x['total_score'], reverse=True)
    print("✅ スコア計算完了！")

    # 6. 結果をDiscordに送信
    print("📨 結果をDiscordに送信中...")
    send_results_to_discord(scored_games, cfg)
    
    # 7. (任意)結果をGoogle Sheetsに記録
    # log_to_google_sheets(scored_games)

    print("🎉 全ての処理が正常に完了しました！")


# ---------------------------------
# Discordへの送信処理
# ---------------------------------
def send_results_to_discord(games, cfg):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL_3D') #今は3d(now)用のみ
    if not webhook_url:
        print("⚠️ Discord Webhook URLが設定されていません。")
        return

    # Embed（カード形式のメッセージ）を作成
    embed = {
        "content": f"**Hot Games Radar PRO** - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC",
        "embeds": []
    }

    for rank, game in enumerate(games[:5], 1): # 上位5件を通知
        rank_emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🔹"
        
        description = ""
        for flag in game['flags']:
            description += f"`{flag}` "

        embed_field = {
            "title": f"{rank_emoji} {rank}位: {game['name']} (スコア: {game['total_score']:.0f})",
            "description": description if description else "注目ポイントなし",
            "color": 5814783 # Discordのブランドカラー
        }
        embed["embeds"].append(embed_field)
    
    try:
        response = requests.post(webhook_url, json=embed)
        response.raise_for_status() # エラーがあれば例外を発生
        print("✅ Discordへの通知に成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"❌ Discordへの通知に失敗しました: {e}")


# ---------------------------------
# このファイルが直接実行された時にmain()を呼び出すおまじない
# ---------------------------------
if __name__ == "__main__":
    main()