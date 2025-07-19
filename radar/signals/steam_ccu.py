# 【最終版テンプレート】この内容を radar/signals/steam_ccu.py に貼り付けてください

import os
import requests

def score(game, cfg, **_):
    """
    司令塔から渡されたゲーム情報に含まれるSteam AppIDを元に、
    現在のプレイヤー数を取得し、スコアを計算する。
    """
    # 1. ゲーム情報に、翻訳済みのSteam AppIDが含まれているかチェック
    steam_appid = game.get('steam_appid')
    if not steam_appid:
        # AppIDがなければ、何もせず処理を終了
        return {}

    # 2. Steam APIキーを安全に読み込む
    steam_api_key = os.environ.get('STEAM_API_KEY')
    if not steam_api_key:
        print("⚠️ steam_ccu: STEAM_API_KEYが設定されていません。")
        return {}

    # 3. Steam APIにプレイヤー数を問い合わせる
    URL = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={steam_appid}&key={steam_api_key}"
    try:
        response = requests.get(URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        player_count = data.get("response", {}).get("player_count", 0)
    except requests.exceptions.RequestException as e:
        print(f"⚠️ steam_ccu: APIリクエストエラー: {e}")
        return {}

    # 4. プレイヤー数に基づいてスコアを計算する（これは一例です）
    steam_score = 0
    # 例えば、現在のプレイヤー数が1万人を超えていたら加点する
    if player_count > 10000:
        steam_score = cfg['weights'].get('steam_ccu_ratio', 8)

    if steam_score > 0:
        return {"steam_ccu_score": steam_score, "source_hit_flags": [f"Steam人気({player_count // 1000}k)📈"]}
    else:
        return {}