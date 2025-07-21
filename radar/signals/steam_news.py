import requests
from datetime import datetime, timedelta

# --- ★★★【改善①】キーワードを「重要度」でランク分け★★★ ---

# Sランク：ゲームの根幹に関わる、最も重要なアップデート
S_RANK_KEYWORDS = ['dlc', 'expansion', 'new season', '大型アップデート']

# Aランク：比較的重要なコンテンツ追加やイベント
A_RANK_KEYWORDS = ['update', 'event', 'アップデート', 'イベント']

# Bランク：軽微な修正や日常的なお知らせ（これらは“加点しない”ために使う）
B_RANK_KEYWORDS = ['patch', 'hotfix', 'bug fix', 'maintenance', 'パッチ', '修正', 'メンテナンス']

def score(game, cfg, **_):
    """
    Steamニュースのキーワードの“重要度”と“鮮度”の両方を評価する。
    """
    appid = game.get('steam_appid')
    if not appid:
        return {}

    URL = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={appid}&count=5"
    
    try:
        response = requests.get(URL, timeout=5)
        response.raise_for_status()
        news_items = response.json().get('appnews', {}).get('newsitems', [])
    except requests.exceptions.RequestException:
        return {}

    best_score_multiplier = 0
    detected_rank = ""

    for item in news_items:
        content = (item.get('title', '') + " " + item.get('contents', '')).lower()
        
        # --- ★★★【改善②】ニュースの“重要度”を判定★★★ ---
        current_rank = None
        # Bランク（軽微な修正）のキーワードが含まれていたら、このニュースは無視する
        if any(keyword in content for keyword in B_RANK_KEYWORDS):
            continue
        # Sランク（超重要）のキーワードが含まれていたら
        elif any(keyword in content for keyword in S_RANK_KEYWORDS):
            current_rank = "S"
        # Aランク（重要）のキーワードが含まれていたら
        elif any(keyword in content for keyword in A_RANK_KEYWORDS):
            current_rank = "A"
        
        # 重要なニュースが見つかった場合のみ、鮮度を評価
        if current_rank:
            news_date = datetime.fromtimestamp(item['date'])
            days_ago = (datetime.now() - news_date).days
            
            # 鮮度と重要度ランクを元に、スコア倍率を決定
            freshness_multiplier = 0
            if days_ago <= 3: freshness_multiplier = 1.0  # 3日以内なら満点
            elif days_ago <= 7: freshness_multiplier = 0.7 # 1週間以内なら7割

            # Sランクニュースなら、さらに倍率を1.5倍にブースト！
            rank_multiplier = 1.5 if current_rank == "S" else 1.0
            
            current_total_multiplier = freshness_multiplier * rank_multiplier
            
            if current_total_multiplier > best_score_multiplier:
                best_score_multiplier = current_total_multiplier
                detected_rank = current_rank

    if best_score_multiplier > 0:
        weight = cfg.get('weights', {}).get('steam_news_update', 15)
        final_score = weight * best_score_multiplier
        
        tag = f"📈[S]大型アプデ予告!" if detected_rank == "S" else "📈[A]アプデ予告？"
        
        return {"steam_news_score": final_score, "source_hit_flags": [tag]}

    return {}