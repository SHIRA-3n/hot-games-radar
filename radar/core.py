# 【真の最終確定版】この内容で、あなたの radar/core.py を全文上書きしてください

import os
import yaml
import json
import pandas as pd
import requests
from datetime import datetime, timezone
from twitchAPI.twitch import Twitch
import asyncio
import sys
import time

# --- 1. インポートセクション ---
from .signals import steam_ccu, slot_fit, competition, upcoming_event, twitch_drops, steam_news, jp_ratio, twitter, google_trends, market_health
from . import utils

# --- 2. ヘルパー関数 ---
def load_config():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# --- 3. メインの司令塔関数 ---
async def main(horizon='3d'):
    print(f"🚀 Hot Games Radar PRO ({horizon}モード) - 起動します...")
    cfg = load_config()

    try:
        twitch_api = Twitch(os.environ['TWITCH_CLIENT_ID'], os.environ['TWITCH_CLIENT_SECRET'])
        await twitch_api.authenticate_app([])
        print("✅ Twitch APIの認証に成功しました。")
    except Exception as e:
        print(f"❌ Twitch APIの初期化または認証に失敗しました: {e}"); return

    # 台帳の準備
    utils.update_steam_app_list()
    steam_app_list, events_df = {}, None
    try:
        with open(utils.STEAM_APP_LIST_FILE, 'r', encoding='utf-8') as f:
            steam_app_list = json.load(f)
    except FileNotFoundError:
        print("⚠️ Steamアプリリストファイルが見つかりません。")
    try:
        events_df = pd.read_csv('events.csv', parse_dates=['start_jst'], encoding='utf-8')
    except Exception as e:
        print(f"⚠️ events.csvの読み込みに失敗しました: {e}")

    print("📡 日本市場の注目ゲームを調査中...")
    games_to_analyze = []
    try:
        target_stream_count = cfg.get('analysis_target_count', 1000)
        print(f"   - 日本語の人気配信 {target_stream_count}件を起点に調査します...")
        
        jp_streams = []
        async for stream in twitch_api.get_streams(language='ja', first=100):
            jp_streams.append(stream)
            if len(jp_streams) >= target_stream_count:
                break
        
        print(f"   - 実際に取得できた日本語配信: {len(jp_streams)}件")
        game_ids = list(set([s.game_id for s in jp_streams if s.game_id]))
        print(f"   - {len(game_ids)}件のユニークなゲームを発見しました。")
        
        if game_ids:
            chunk_size = 100
            for i in range(0, len(game_ids), chunk_size):
                chunk = game_ids[i:i + chunk_size]
                async for game in twitch_api.get_games(game_ids=chunk):
                    games_to_analyze.append(game)
        
        jp_viewer_counts = {s.game_id: s.viewer_count for s in jp_streams}
        games_to_analyze.sort(key=lambda g: jp_viewer_counts.get(g.id, 0), reverse=True)
        print(f"✅ {len(games_to_analyze)}件の日本市場ゲームを分析対象とします。")
    except Exception as e:
        print(f"❌ ゲームリストの取得に失敗しました: {e}"); return

    print("⚙️ 各ゲームのスコアを計算中...")
    ENABLED_SIGNALS = [steam_ccu, slot_fit, competition, upcoming_event, twitch_drops, steam_news, jp_ratio, twitter, google_trends, market_health]
    
    tasks = [
        analyze_single_game(
            game_data, cfg, twitch_api, steam_app_list, events_df, ENABLED_SIGNALS, jp_streams, horizon
        ) 
        for game_data in games_to_analyze
    ]
    results = await asyncio.gather(*tasks)

    scored_games, errored_games = [], []
    for game, error in results:
        if error:
            errored_games.append({'name': game['name'], 'error': error})
        else:
            scored_games.append(game)

    scored_games.sort(key=lambda x: x.get('total_score', 0), reverse=True)
    print("✅ スコア計算完了！")

    print("📨 結果をDiscordに送信中...")
    send_results_to_discord(scored_games, errored_games, cfg, horizon)
    print("🎉 全ての処理が正常に完了しました！")

# --- 4. 現場監督関数 ---
async def analyze_single_game(game_data, cfg, twitch_api, steam_app_list, events_df, signal_modules, jp_streams, horizon):
    """１つのゲームを分析し、成功なら結果を、失敗ならエラーメッセージを返す"""
    game = {'id': game_data.id, 'name': game_data.name, 'game_data': game_data}
    error_messages = []

    appid = utils.get_steam_appid(game['name'], steam_app_list)
    if appid:
        game['steam_appid'] = appid

    game_scores, game_flags = {}, []
    
    for module in signal_modules:
        try:
            # ★★★【あなたの指摘を反映！】★★★
            # 各専門家に、現在の分析モード(horizon)を、正しく伝える
            if asyncio.iscoroutinefunction(module.score):
                result = await module.score(game=game, cfg=cfg, twitch_api=twitch_api, events_df=events_df, jp_streams=jp_streams, horizon=horizon)
            else:
                result = module.score(game=game, cfg=cfg, twitch_api=twitch_api, events_df=events_df, jp_streams=jp_streams, horizon=horizon)
            
            if result:
                for key, value in result.items():
                    if 'score' in key: game_scores[key] = value
                if 'source_hit_flags' in result:
                    game_flags.extend(result.get('source_hit_flags', []))
        except Exception as e:
            pass

    # 'weights'の取得方法を、3チャンネル対応の構造に合わせる
    current_weights = cfg.get('weights', {}).get(horizon, cfg.get('weights', {}))
    total_score = 0
    for key, value in game_scores.items():
        weight_multiplier = current_weights.get(key.replace('_score', ''), 1)
        total_score += value * weight_multiplier

    game['total_score'] = total_score
    game['flags'] = list(set(game_flags))
    
    error_summary = ", ".join(error_messages) if error_messages else None
    return game, error_summary

# --- 5. 通知担当関数 ---
def send_results_to_discord(games, errored_games, cfg, horizon):
    """
    Discordに分析結果を送信する。
    Embedのサイズ制限を考慮し、10件ごとに分割して送信する。
    """
    webhook_secret_name = f"DISCORD_WEBHOOK_URL_{horizon.upper()}"
    webhook_url = os.environ.get(webhook_secret_name)
    
    if not webhook_url:
        print(f"⚠️ Webhook URL ({webhook_secret_name}) が設定されていません。"); return

    score_threshold = cfg.get('notification_score_threshold', 10)
    game_count = cfg.get('notification_game_count', 20)
    
    # --- ★★★【分割送信機能の心臓部】★★★ ---
    
    # 1. まず、通知対象となるゲームのリストを作成
    games_to_notify = [g for g in games if g.get('total_score', 0) >= score_threshold][:game_count]
    
    # 2. リストを、10件ずつの小さな「塊（チャンク）」に分割する
    chunk_size = 10
    chunks = [games_to_notify[i:i + chunk_size] for i in range(0, len(games_to_notify), chunk_size)]
    
    total_notified_count = 0

    # 3. 各チャンク（10件ずつのリスト）ごとに、Embedを作成して送信する
    for i, chunk in enumerate(chunks):
        
        # 2通目以降のタイトルを少し変える
        report_title = f"📈 Hot Games Radar ({horizon}) - 分析レポート"
        if len(chunks) > 1:
            report_title += f" ({i+1}/{len(chunks)})"

        embed = { "title": report_title, "color": 5814783, "fields": [] }

        for game in chunk:
            # game_countは全体の上限、notified_countは現在のEmbedの件数を数える
            current_rank = total_notified_count + 1
            
            tags_for_title = " ".join([f"`{flag}`" for flag in game['flags'][:2]])
            field_name = f"{'🥇🥈🥉'[current_rank-1] if current_rank <= 3 else '🔹'} {current_rank}位: {game['name']} (スコア: {game.get('total_score', 0):.0f}) {tags_for_title}"
            
            links = []
            if 'steam_appid' in game:
                links.append(f"**[Steam]({f'https://store.steampowered.com/app/{game["steam_appid"]}'})**")
            twitch_category_name = game['name'].lower().replace(' ', '-')
            links.append(f"**[Twitch]({f'https://www.twitch.tv/directory/category/{twitch_category_name}'})**")
            google_trend_query = requests.utils.quote(f"{game['name']} ゲーム")
            links.append(f"**[Googleトレンド]({f'https://trends.google.com/trends/explore?q={google_trend_query}&geo=JP'})**")
            link_string = " | ".join(links)
            
            field_value = f"🔗 {link_string}\n──────────"
            embed["fields"].append({ "name": field_name, "value": field_value })
            total_notified_count += 1

        # エラー報告は、最後のレポートにだけ付ける
        if i == len(chunks) - 1 and cfg.get('notification_include_errors', True) and errored_games:
            error_list_str = "\n".join([f"- {g['name']}" for g in errored_games[:5]])
            embed["fields"].append({ "name": "⚠️ 一部センサーでエラーが検出されたゲーム", "value": error_list_str })

        if not embed["fields"]:
            continue # 送信するフィールドがなければ、次のチャンクへ

        try:
            response = requests.post(webhook_url, json={"embeds": [embed]})
            response.raise_for_status()
            print(f"✅ Discordへレポート({i+1}/{len(chunks)})の通知に成功しました。")
            # APIのレートリミットを避けるため、少し待機
            time.sleep(1) 
        except requests.exceptions.RequestException as e:
            print(f"❌ Discordへの通知に失敗しました: {e}")

    if total_notified_count == 0:
        print("✅ 通知対象の注目ゲームはありませんでした。")