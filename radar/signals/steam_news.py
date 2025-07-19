# 【この内容で radar/signals/steam_news.py を作成・保存してください】

import requests

# ニュースの見出しや本文で、盛り上がりの兆候を示すキーワード
UPDATE_KEYWORDS = ['update', 'patch', 'dlc', 'new season', 'expansion', 'アップデート', 'パッチ']

def score(game, cfg, **_):
    """
    Steam News APIを使い、直近の公式ニュースからアップデート等の兆候を検知する。
    """
    # ゲーム情報にSteam AppIDがなければ分析できない
    appid = game.get('steam_appid')
    if not appid:
        return {}

    # Steam News APIのエンドポイント
    URL = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={appid}&count=5"
    
    try:
        response = requests.get(URL, timeout=5)
        response.raise_for_status()
        news_items = response.json().get('appnews', {}).get('newsitems', [])
    except requests.exceptions.RequestException:
        # APIエラーの場合は静かに処理を終了
        return {}

    update_found = False
    for item in news_items:
        title = item.get('title', '').lower()
        contents = item.get('contents', '').lower()
        
        # タイトルか本文にキーワードが含まれているかチェック
        if any(keyword in title or keyword in contents for keyword in UPDATE_KEYWORDS):
            update_found = True
            break # 兆候が見つかれば、それ以上探す必要はない

    if update_found:
        # config.yamlから重みを取得
        weight = cfg.get('weights', {}).get('steam_news_update', 30) # 新しい重み項目
        if weight > 0:
            return {"steam_news_score": weight, "source_hit_flags": ["📈アプデ予告？"]}

    return {}