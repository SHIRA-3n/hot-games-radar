import os
import requests
import time

# 過去のデータを取得するためのエンドポイント（非公式APIのため、将来変更される可能性あり）
HISTORY_URL = "https://steamcharts.com/app/{appid}/chart-data.json"

def get_recent_player_history(appid):
    """SteamChartsから直近のプレイヤー数履歴を取得するヘルパー関数"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'} # Botアクセスを偽装
        response = requests.get(HISTORY_URL.format(appid=appid), headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # UNIXタイムスタンプとプレイヤー数のリストを取得
        timestamps = [entry[0] // 1000 for entry in data]
        players = [entry[1] for entry in data]
        
        # 過去30日間の平均プレイヤー数を計算
        # （ここでは簡略化のため、取得データ全体の平均を使う）
        if players:
            return sum(players) / len(players)
    except Exception:
        return None
    return None

def score(game, cfg, **_):
    """
    現在のプレイヤー数と、過去の平均プレイヤー数を比較し、
    その「伸び率（勢い）」を評価する。
    """
    steam_appid = game.get('steam_appid')
    if not steam_appid:
        return {}

    steam_api_key = os.environ.get('STEAM_API_KEY')
    if not steam_api_key:
        print("⚠️ steam_ccu: STEAM_API_KEYが設定されていません。")
        return {}

    # --- 1. 現在のプレイヤー数を取得 ---
    try:
        current_players_url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={steam_appid}&key={steam_api_key}"
        response = requests.get(current_players_url, timeout=5)
        response.raise_for_status()
        current_players = response.json().get("response", {}).get("player_count", 0)
    except requests.exceptions.RequestException:
        return {} # 現在のプレイヤー数が取れなければ分析不能

    # --- 2. 過去の平均プレイヤー数を取得 ---
    # 外部サイトへの負荷を考慮し、1秒待機
    time.sleep(1)
    past_avg_players = get_recent_player_history(steam_appid)

    # --- 3. 「勢い」をスコアリング ---
    # 過去のデータが取得できた場合のみ、「伸び率」を評価
    if past_avg_players and past_avg_players > 50: # ノイズ（平均50人以下）を除外
        ratio = current_players / past_avg_players
        
        # 伸び率が1.5倍（50%増）以上の場合にスコアを加算
        if ratio >= 1.5:
            weight = cfg.get('weights', {}).get('steam_ccu_ratio', 8)
            # 伸び率が大きいほど、スコアも高くなるように調整
            final_score = weight * (ratio / 1.5)
            return {"steam_ccu_ratio_score": final_score, "source_hit_flags": [f"Steam人気急増({ratio:.1f}倍)🔥"]}

    # 過去のデータが取れなかった場合は、以前の「絶対数」で評価
    if current_players > 10000:
        weight = cfg.get('weights', {}).get('steam_ccu_ratio', 8)
        return {"steam_ccu_score": weight, "source_hit_flags": [f"Steam人気({current_players // 1000}k)📈"]}
        
    return {}