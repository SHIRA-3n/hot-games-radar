# 【最終版テンプレート】この内容を radar/core.py に貼り付けてください

import os
import yaml
import json
import requests
from datetime import datetime, timezone
from twitchAPI.twitch import Twitch

# 作成した全ての分析モジュール（センサー）をインポートします
from .signals import steam_ccu, slot_fit, competition
# 新しい翻訳機をインポート
from . import utils

def load_config():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

async def main():
    print("🚀 Hot Games Radar PRO - 起動します...")
    cfg = load_config()

    try:
        # 1. まずTwitch APIのクライアントを作成
        twitch_api = Twitch(os.environ['TWITCH_CLIENT_ID'], os.environ['TWITCH_CLIENT_SECRET'])
        
        # ★★★【最後のアップグレード！】★★★
        # 2. 「アプリとして」の権限を要求して認証する
        #    []は「特別な権限は不要です」という意味。
        await twitch_api.authenticate_app([])
        
        print("✅ Twitch APIの認証に成功しました。")
    except Exception as e:
        print(f"❌ Twitch APIの初期化または認証に失敗しました: {e}")
        return

    # ★★★【アップグレード①】SteamのAppIDリストを準備★★★
    utils.update_steam_app_list()
    steam_app_list = {}
    try:
        with open(utils.STEAM_APP_LIST_FILE, 'r', encoding='utf-8') as f:
            steam_app_list = json.load(f)
    except FileNotFoundError:
        print("⚠️ Steamアプリリストファイルが見つかりません。")

    print("📡 Twitchから注目ゲームのリストを取得中...")
    try:
        # Twitchの上位ゲームを取得 (Just Chattingなどは除外)
        games_to_analyze = [g async for g in twitch_api.get_top_games(first=20) if g.name != 'Just Chatting']
        print(f"✅ {len(games_to_analyze)}件のゲームを分析対象とします。")
    except Exception as e:
        print(f"❌ ゲームリストの取得に失敗しました: {e}"); return

    print("⚙️ 各ゲームのスコアを計算中...")
    scored_games = []
    
    ENABLED_SIGNALS = [steam_ccu, slot_fit, competition]

    for game_data in games_to_analyze:
        # 司令塔が扱う「ゲーム情報」辞書を作成
        game = {'id': game_data.id, 'name': game_data.name, 'viewer_count': 0} # viewer_countは後で取得

        # ★★★【アップグレード②】ゲーム名からSteam AppIDを検索して追加★★★
        appid = utils.get_steam_appid(game['name'], steam_app_list)
        if appid:
            game['steam_appid'] = appid

        game_scores, game_flags = {}, []
        
        for signal_module in ENABLED_SIGNALS:
            try:
                result = signal_module.score(game=game, cfg=cfg, twitch_api=twitch_api)
                if result:
                    game_scores.update(result)
                    if 'source_hit_flags' in result:
                        game_flags.extend(result.pop('source_hit_flags'))
            except Exception as e:
                print(f"⚠️ {game['name']} の {signal_module.__name__} でエラー: {e}")

        game['total_score'] = sum(v for k, v in game_scores.items() if isinstance(v, (int, float)))
        game['flags'] = list(set(game_flags))
        scored_games.append(game)

    scored_games.sort(key=lambda x: x['total_score'], reverse=True)
    print("✅ スコア計算完了！")

    print("📨 結果をDiscordに送信中...")
    send_results_to_discord(scored_games, cfg)
    print("🎉 全ての処理が正常に完了しました！")

def send_results_to_discord(games, cfg):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL_3D')
    if not webhook_url:
        print("⚠️ Discord Webhook URLが設定されていません。"); return

    embed = {"content": f"**Hot Games Radar PRO** - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC", "embeds": []}
    for rank, game in enumerate(games[:5], 1):
        if game['total_score'] <= 0: continue # スコアが0以下のゲームは通知しない
        rank_emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🔹"
        description = " ".join([f"`{flag}`" for flag in game['flags']])
        embed_field = {"title": f"{rank_emoji} {rank}位: {game['name']} (スコア: {game['total_score']:.0f})", "description": description or "注目ポイントあり", "color": 5814783}
        embed["embeds"].append(embed_field)
    
    if not embed["embeds"]: # 通知するゲームがなければ送信しない
        print("✅ 通知対象の注目ゲームはありませんでした。"); return
    try:
        response = requests.post(webhook_url, json=embed)
        response.raise_for_status()
        print("✅ Discordへの通知に成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"❌ Discordへの通知に失敗しました: {e}")

if __name__ == "__main__":
    main()