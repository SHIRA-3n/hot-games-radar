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

    tasks = [analyze_single_game(game_data, cfg, twitch_api, steam_app_list, ENABLED_SIGNALS) for game_data in games_to_analyze]
    results = await asyncio.gather(*tasks)

    scored_games = []
    errored_games = []
    for game, error in results:
        if error:
            # エラーがあったゲームをリストに追加
            errored_games.append({'name': game['name'], 'error': error})
        else:
            # 成功したゲームをリストに追加
            scored_games.append(game)

    scored_games.sort(key=lambda x: x['total_score'], reverse=True)
    print("✅ スコア計算完了！")

    print("📨 結果をDiscordに送信中...")
    # 通知担当に、成功リストと失敗リストの両方を渡す
    send_results_to_discord(scored_games, errored_games, cfg)
    print("🎉 全ての処理が正常に完了しました！")


async def analyze_single_game(game_data, cfg, twitch_api, steam_app_list, signal_modules):
    """１つのゲームを分析し、成功なら結果を、失敗ならエラーメッセージを返す"""
    game = {'id': game_data.id, 'name': game_data.name}
    error_messages = []

    appid = utils.get_steam_appid(game['name'], steam_app_list)
    if appid:
        game['steam_appid'] = appid

    game_scores, game_flags = {}, []
    
    # asyncio.gatherを使って、各センサーの処理を並行して行う
    tasks = [module.score(game=game, cfg=cfg, twitch_api=twitch_api) for module in signal_modules]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, Exception):
            # もしセンサーがエラーを返したら、エラーメッセージを記録
            error_messages.append(str(res))
        elif isinstance(res, dict) and res:
            game_scores.update(res)
            if 'source_hit_flags' in res:
                game_flags.extend(result.pop('source_hit_flags'))

    game['total_score'] = sum(v for k, v in game_scores.items() if isinstance(v, (int, float)))
    game['flags'] = list(set(game_flags))
    
    # 最終的なエラーの有無を返す
    error_summary = ", ".join(error_messages) if error_messages else None
    return game, error_summary


def send_results_to_discord(games, errored_games, cfg):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL_3D')
    if not webhook_url:
        print("⚠️ Discord Webhook URLが設定されていません。"); return

    # --- デザインの最終調整 ---
    
    # 1. ひとつの大きなEmbed（カード）を作成。タイトルをシンプルに。
    embed = {
        "title": "📈 Hot Games Radar - 分析レポート",
        "color": 5814783,
        "fields": []
    }

    # 2. スコアの高いゲームの情報をフィールドとして追加
    score_threshold = cfg.get('notification_score_threshold', 10)
    game_count = cfg.get('notification_game_count', 10)
    
    notified_count = 0
    for game in games:
        if notified_count >= game_count: break
        if game['total_score'] >= score_threshold:
            
            # --- ★★★【アップグレード①】タイトル部分の組み立て★★★ ---
            game_title = game['name']
            if 'steam_appid' in game:
                # [テキスト](URL) というMarkdown形式で、タイトル自体をリンクにする
                game_title = f"[{game['name']}]({f'https://store.steampowered.com/app/{game["steam_appid"]}'})"

            # --- ★★★【アップグレード②】値（value）部分の組み立て★★★ ---
            # リンクをなくし、タグだけをシンプルに表示
            tags = " ".join([f"`{flag}`" for flag in game['flags']])
            
            embed["fields"].append({
                "name": f"{'🥇🥈🥉'[notified_count] if notified_count < 3 else '🔹'} {notified_count + 1}位: {game_title} (スコア: {game['total_score']:.0f})",
                "value": tags or "注目ポイントあり" # タグがなければ「注目ポイントあり」と表示
            })
            notified_count += 1

    # 3. エラーが出たゲームの情報の追加（変更なし）
    if cfg.get('notification_include_errors', True) and errored_games:
        error_list_str = "\n".join([f"- {g['name']}" for g in errored_games[:5]])
        embed["fields"].append({
            "name": "⚠️ 一部センサーでエラーが検出されたゲーム",
            "value": error_list_str
        })

    # 4. 通知する内容がなければ送信しない（変更なし）
    if not embed["fields"]:
        print("✅ 通知対象の注目ゲームはありませんでした。"); return

    try:
        response = requests.post(webhook_url, json={"embeds": [embed]})
        response.raise_for_status()
        print(f"✅ Discordへ{notified_count}件の注目ゲームと、{len(errored_games)}件のエラー報告を通知しました。")
    except requests.exceptions.RequestException as e:
        print(f"❌ Discordへの通知に失敗しました: {e}")

# (この部分は変更なし)
# if __name__ == "__main__":
#     asyncio.run(main())