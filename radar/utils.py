import requests
import json
import os
from datetime import datetime, timedelta
from rapidfuzz import fuzz, process # 新しい「あいまい検索」ライブラリをインポート

STEAM_APP_LIST_FILE = 'steam_app_list.json'

def update_steam_app_list():
    """Steamの全アプリリストを取得し、ローカルに保存する関数"""
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
        
        # 今回は、あいまい検索用に、生のゲーム名のリストと、
        # {ゲーム名: appid} の辞書の両方を用意する
        app_names = [app['name'] for app in apps if app.get('name')]
        app_dict = {app['name']: app['appid'] for app in apps if app.get('name')}
        
        # 2つのデータをまとめて一つのjsonに保存
        data_to_save = {'names': app_names, 'dict': app_dict}
        
        with open(STEAM_APP_LIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False) # indentなしでファイルサイズを圧縮
        print("✅ Steamアプリリストの更新が完了しました。")
    except requests.exceptions.RequestException as e:
        print(f"❌ Steamアプリリストの更新に失敗しました: {e}")

def get_steam_appid(game_name, app_list_data):
    """
    「編集距離」を用いた、賢い“あいまい検索”でAppIDを探す。
    """
    if not app_list_data or 'names' not in app_list_data or 'dict' not in app_list_data:
        return None
        
    app_names = app_list_data['names']
    app_dict = app_list_data['dict']

    # --- ★★★【改善①】“あいまい検索”で、最も似ている候補を1つだけ見つける★★★ ---
    
    # rapidfuzzライブラリを使い、最も一致スコアが高い候補を抽出
    # score_cutoff=90 は、「90%以上似ているもの」だけに絞り込む、非常に厳しい基準
    best_match = process.extractOne(game_name, app_names, scorer=fuzz.WRatio, score_cutoff=90)
    
    if best_match:
        # 最も似ていると判断されたゲーム名を取得
        matched_name = best_match[0]
        # その名前を元に、辞書からAppIDを返す
        return app_dict.get(matched_name)
            
    # 厳しい基準で見つからなければ、諦める
    return None