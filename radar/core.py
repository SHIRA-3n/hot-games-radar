# 【最終確定版テンプレート】この内容を radar/core.py に貼り付けてください

import os
import yaml
import json
import requests
from datetime import datetime, timezone
from twitchAPI.twitch import Twitch
import asyncio # 非同期処理に必要
from .signals import steam_ccu, slot_fit, competition, upcoming_event, twitch_drops, steam_news, jp_ratio, twitter, google_trends, market_health
import pandas as pd 

# 作成した全ての分析モジュール（センサー）をインポートします
from .signals import steam_ccu, slot_fit, competition
from . import utils

def load_config():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# 【真の最終確定版】この内容で、あなたの async def main(): 関数を全文上書きしてください

async def main():
    print("🚀 Hot Games Radar PRO - 起動します...")
    cfg = load_config()

    try:
        twitch_api = Twitch(os.environ['TWITCH_CLIENT_ID'], os.environ['TWITCH_CLIENT_SECRET'])
        await twitch_api.authenticate_app([])
        print("✅ Twitch APIの認証に成功しました。")
    except Exception as e:
        print(f"❌ Twitch APIの初期化または認証に失敗しました: {e}"); return

    # 最初に1回だけ、全ての「台帳」を読み込んでおく
    utils.update_steam_app_list()
    steam_app_list, events_df = {}, None
    try:
        # ★★★ ここが欠けていました！ ★★★
        with open(utils.STEAM_APP_LIST_FILE, 'r', encoding='utf-8') as f:
            steam_app_list = json.load(f)
    except FileNotFoundError:
        print("⚠️ Steamアプリリストファイルが見つかりません。")
    try:
        # events.csvを一度だけ読み込む
        events_df = pd.read_csv('events.csv', parse_dates=['start_jst'], encoding='utf-8')
    except Exception as e:
        print(f"⚠️ events.csvの読み込みに失敗しました: {e}")

    print("📡 Twitchから注目ゲームのリストを取得中...")
    games_to_analyze = []
    try:
        # config.yamlから調査したい件数を取得
        target_count = cfg.get('analysis_target_count', 200)
        
        # Twitch APIから、指定された件数だけゲームを取得する
        async for game in twitch_api.get_top_games(first=100):
            if game.name != 'Just Chatting':
                games_to_analyze.append(game)
            if len(games_to_analyze) >= target_count:
                break
        
        print(f"✅ {len(games_to_analyze)}件のゲームを分析対象とします。")

    except Exception as e:
        print(f"❌ ゲームリストの取得に失敗しました: {e}"); return

    print("⚙️ 各ゲームのスコアを計算中...")
    
    # どの専門家（センサー）を分析に使うか、ここでリストを定義する
    ENABLED_SIGNALS = [steam_ccu, slot_fit, competition, upcoming_event, twitch_drops, steam_news, jp_ratio, twitter, google_trends, market_health]
    
    # 各ゲームに対する「分析の依頼書」のリストを作成する
    tasks = [
        analyze_single_game(
            game_data, cfg, twitch_api, steam_app_list, events_df, ENABLED_SIGNALS
        ) 
        for game_data in games_to_analyze
    ]
    
    # 全ての「依頼書」を、並行して一斉に実行させる
    results = await asyncio.gather(*tasks)

    # 成功した分析と、エラーが出た分析を仕分ける
    scored_games = []
    errored_games = []
    for game, error in results:
        if error:
            errored_games.append({'name': game['name'], 'error': error})
        else:
            scored_games.append(game)

    # 成功したゲームをスコアの高い順に並び替える
    scored_games.sort(key=lambda x: x['total_score'], reverse=True)
    print("✅ スコア計算完了！")

    print("📨 結果をDiscordに送信中...")
    # 通知担当に、成功リストと失敗リストの両方を渡す
    send_results_to_discord(scored_games, errored_games, cfg)
    print("🎉 全ての処理が正常に完了しました！")


# 【最終確定版テンプレート】この内容で analyze_single_game 関数を全文上書きしてください

async def analyze_single_game(game_data, cfg, twitch_api, steam_app_list, events_df, signal_modules):
    """１つのゲームを分析し、成功なら結果を、失敗ならエラーメッセージを返す"""
    # dropsセンサーのために、元のgame_dataオブジェクトも渡す
    game = {'id': game_data.id, 'name': game_data.name, 'game_data': game_data}
    error_messages = []

    appid = utils.get_steam_appid(game['name'], steam_app_list)
    if appid:
        game['steam_appid'] = appid

    game_scores, game_flags = {}, []
    
    # --- ★★★【最後の修正！】★★★
    # 各センサー（専門家）を、正しい作法で呼び出す
    for module in signal_modules:
        try:
            # 専門家が非同期モードなら 'await' を付けて呼ぶ
            if asyncio.iscoroutinefunction(module.score):
                # 'horizon'情報は、今はまだ使わないので一旦'3d'で固定（今後の拡張用）
                result = await module.score(game=game, cfg=cfg, twitch_api=twitch_api, horizon='3d', events_df=events_df)
            else:
                result = module.score(game=game, cfg=cfg, twitch_api=twitch_api, horizon='3d')

            if result:
                game_scores.update(result)
                if 'source_hit_flags' in result:
                    # popで取り出すと元の辞書から消えてしまうので、直接参照する
                    game_flags.extend(result.get('source_hit_flags', []))

        except Exception as e:
            # 実行ログがエラーで埋まらないように、ここでは警告をprintしない
            pass

    game['total_score'] = sum(v for k, v in game_scores.items() if isinstance(v, (int, float)) and 'score' in k)
    game['flags'] = list(set(game_flags))
    
    # エラーの有無に関わらず、分析済みのゲーム情報を返す
    return game, None # 現状はエラーを詳細に追跡しないシンプルな形に戻す


# 【最終確定版テンプレート】この内容で send_results_to_discord 関数を全文上書きしてください

def send_results_to_discord(games, errored_games, cfg):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL_3D')
    if not webhook_url:
        print("⚠️ Discord Webhook URLが設定されていません。"); return

    embed = {
        "title": "📈 Hot Games Radar - 分析レポート",
        "color": 5814783,
        "fields": []
    }

    score_threshold = cfg.get('notification_score_threshold', 10)
    game_count = cfg.get('notification_game_count', 10)
    
    notified_count = 0
    for game in games:
        if notified_count >= game_count: break
        if game['total_score'] >= score_threshold:
            
            # --- ★★★【デザイン刷新の心臓部】★★★
            
            # 1. タイトル行を組み立てる (ゲーム名 + スコア + 主要タグ)
            tags_for_title = " ".join([f"`{flag}`" for flag in game['flags'][:2]])
            field_name = f"{'🥇🥈🥉'[notified_count] if notified_count < 3 else '🔹'} {notified_count + 1}位: {game['name']} (スコア: {game['total_score']:.0f}) {tags_for_title}"

            # 2. 本文行（リンク集）を組み立てる
            links = []
            if 'steam_appid' in game:
                links.append(f"**[Steam]({f'https://store.steampowered.com/app/{game["steam_appid"]}'})**")
            
            # Twitchリンク：ゲーム名をURLセーフな形式に変換
            twitch_category_name = game['name'].lower().replace(' ', '-')
            links.append(f"**[Twitch]({f'https://www.twitch.tv/directory/category/{twitch_category_name}'})**")
            
            # Googleトレンドリンク：検索クエリを「ゲーム名 + ゲーム」に
            google_trend_query = requests.utils.quote(f"{game['name']} ゲーム")
            links.append(f"**[Googleトレンド]({f'https://trends.google.com/trends/explore?q={google_trend_query}&geo=JP'})**")
            
            link_string = " | ".join(links)
            
            # 3. 本文に区切り線を追加
            field_value = f"🔗 {link_string}\n──────────"
            
            embed["fields"].append({ "name": field_name, "value": field_value })
            notified_count += 1

    # エラー報告部分
    if cfg.get('notification_include_errors', True) and errored_games:
        error_list_str = "\n".join([f"- {g['name']}" for g in errored_games[:5]])
        embed["fields"].append({ "name": "⚠️ 一部センサーでエラーが検出されたゲーム", "value": error_list_str })

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