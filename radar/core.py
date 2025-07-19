# 【最終確定版テンプレート】この内容を radar/core.py に貼り付けてください

import os
import yaml
import json
import requests
from datetime import datetime, timezone
from twitchAPI.twitch import Twitch
import asyncio # 非同期処理に必要

# 作成した全ての分析モジュール（センサー）をインポートします
from .signals import steam_ccu, slot_fit, competition
from . import utils

def load_config():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

async def main():
    print("🚀 Hot Games Radar PRO - 起動します...")
    cfg = load_config()

    try:
        twitch_api = Twitch(os.environ['TWITCH_CLIENT_ID'], os.environ['TWITCH_CLIENT_SECRET'])
        await twitch_api.authenticate_app([])
        print("✅ Twitch APIの認証に成功しました。")
    except Exception as e:
        print(f"❌ Twitch APIの初期化または認証に失敗しました: {e}"); return

    utils.update_steam_app_list()
    steam_app_list = {}
    try:
        with open(utils.STEAM_APP_LIST_FILE, 'r', encoding='utf-8') as f:
            steam_app_list = json.load(f)
    except FileNotFoundError:
        print("⚠️ Steamアプリリストファイルが見つかりません。")

    print("📡 Twitchから注目ゲームのリストを取得中...")
    games_to_analyze = []
    try:
        # ★★★【最終確定版のロジック】★★★
        # config.yamlから調査したい件数を取得
        target_count = cfg.get('analysis_target_count', 200)
        
        # Twitch APIに「1ページ100件で」とリクエストを出す
        # async forが、自動で次のページを読み込みに行ってくれます
        async for game in twitch_api.get_top_games(first=100):
            # ゲーム以外のカテゴリを除外
            if game.name != 'Just Chatting':
                games_to_analyze.append(game)
            
            # ★★★【最重要ポイント】★★★
            # リストの件数が目標に達したら、ループを強制的にストップする
            if len(games_to_analyze) >= target_count:
                break
        
        print(f"✅ {len(games_to_analyze)}件のゲームを分析対象とします。")

    except Exception as e:
        print(f"❌ ゲームリストの取得に失敗しました: {e}"); return

    print("⚙️ 各ゲームのスコアを計算中...")
    scored_games = []
    
    ENABLED_SIGNALS = [steam_ccu, slot_fit, competition]

    # asyncio.gatherを使って、全ゲームのスコアリングを並行して効率的に行う
    tasks = []
    for game_data in games_to_analyze:
        tasks.append(analyze_single_game(game_data, cfg, twitch_api, steam_app_list, ENABLED_SIGNALS))
    
    scored_games_results = await asyncio.gather(*tasks)
    # Noneが返ってきたタスクを除外
    scored_games = [game for game in scored_games_results if game is not None]

    scored_games.sort(key=lambda x: x['total_score'], reverse=True)
    print("✅ スコア計算完了！")

    print("📨 結果をDiscordに送信中...")
    send_results_to_discord(scored_games, cfg)
    print("🎉 全ての処理が正常に完了しました！")


async def analyze_single_game(game_data, cfg, twitch_api, steam_app_list, signal_modules):
    """１つのゲームを分析するための非同期関数"""
    game = {'id': game_data.id, 'name': game_data.name}
    
    appid = utils.get_steam_appid(game['name'], steam_app_list)
    if appid:
        game['steam_appid'] = appid

    game_scores, game_flags = {}, []
    
    for signal_module in signal_modules:
        try:
            # 各分析モジュールも非同期で呼び出す
            result = await signal_module.score(game=game, cfg=cfg, twitch_api=twitch_api)
            if result:
                game_scores.update(result)
                if 'source_hit_flags' in result:
                    game_flags.extend(result.pop('source_hit_flags'))
        except Exception as e:
            # 実行ログがエラーで埋まらないように、ここでは警告をprintしない
            pass

    game['total_score'] = sum(v for k, v in game_scores.items() if isinstance(v, (int, float)))
    game['flags'] = list(set(game_flags))
    return game


def send_results_to_discord(games, cfg):
    # (この関数は変更なし)
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL_3D')
    if not webhook_url:
        print("⚠️ Discord Webhook URLが設定されていません。"); return

    embed = {"content": f"**Hot Games Radar PRO** - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC", "embeds": []}
    
    # スコアが一定以上のゲームだけを通知する（金の卵フィルター）
    score_threshold = cfg.get('notification_score_threshold', 10)
    
    notified_count = 0
    for game in games:
        if notified_count >= 5: break # 最大5件まで通知
        if game['total_score'] >= score_threshold:
            rank = notified_count + 1
            rank_emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🔹"
            description = " ".join([f"`{flag}`" for flag in game['flags']])
            embed_field = {"title": f"{rank_emoji} {rank}位: {game['name']} (スコア: {game['total_score']:.0f})", "description": description or "注目ポイントあり", "color": 5814783}
            embed["embeds"].append(embed_field)
            notified_count += 1
    
    if not embed["embeds"]:
        print("✅ 通知対象の注目ゲームはありませんでした。"); return
    try:
        response = requests.post(webhook_url, json=embed)
        response.raise_for_status()
        print(f"✅ Discordへ{notified_count}件の通知に成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"❌ Discordへの通知に失敗しました: {e}")

# (この部分は変更なし)
# if __name__ == "__main__":
#     asyncio.run(main())