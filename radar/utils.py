# radar/utils.py

import requests
import json
import os
from datetime import datetime, timedelta

STEAM_APP_LIST_FILE = 'steam_app_list.json'

def update_steam_app_list():
    """Steamの全アプリリストを取得し、ローカルに保存する関数"""
    # 最後に更新してから24時間以内なら、更新しない（API負荷軽減のため）
    if os.path.exists(STEAM_APP_LIST_FILE):
        last_modified_time = datetime.fromtimestamp(os.path.getmtime(STEAM_APP_LIST_FILE))
        if datetime.now() - last_modified_time < timedelta(days=1):
            print("✅ Steamアプリリストは最新です。")
            return

    print("🔄 Steamアプリリストを更新中...")
    try:
        url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        apps = response.json().get('applist', {}).get('apps', [])
        
        # 扱いやすいように {ゲーム名(小文字): appid} の形式で保存
        app_dict = {app['name'].lower(): app['appid'] for app in apps if app.get('name')}
        
        with open(STEAM_APP_LIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(app_dict, f, ensure_ascii=False, indent=2)
        print("✅ Steamアプリリストの更新が完了しました。")
    except requests.exceptions.RequestException as e:
        print(f"❌ Steamアプリリストの更新に失敗しました: {e}")

def get_steam_appid(game_name, app_list):
    """ローカルのアプリリストから、ゲーム名に一致するAppIDを探す関数"""
    if not app_list:
        return None
    return app_list.get(game_name.lower())