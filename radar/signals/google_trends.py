from pytrends.request import TrendReq
import pandas as pd
import time

# Googleトレンドに接続するためのオブジェクトを準備
pytrends = TrendReq(hl='ja-JP', tz=540)

def score(game, cfg, **_):
    """
    Googleトレンドを使い、日本でのゲーム名の検索インタレストが
    直近で急上昇しているかを評価する。
    """
    weight = cfg.get('weights', {}).get('trends_jp_spike', 0)
    if weight == 0:
        return {}

    # --- ★★★【改善①】複数のキーワード候補で、賢く検索★★★ ---
    # ゲーム名から、考えられる検索キーワードのリストを作成
    game_name = game['name']
    keywords = [
        f"{game_name} ゲーム", # 最も基本的な検索
        game_name,             # ゲーム名単体
    ]
    # もしゲーム名にスペースがあれば、スペースなしのバージョンも追加 (例: Apex Legends -> ApexLegends)
    if ' ' in game_name:
        keywords.append(game_name.replace(' ', ''))

    best_spike_ratio = 0
    
    # 各キーワードでトレンドを調査し、最も良い結果を採用
    for keyword in keywords:
        try:
            # Google APIへの負荷を軽減するため、少しだけ待機
            time.sleep(1) 
            
            pytrends.build_payload([keyword], cat=0, timeframe='today 7-d', geo='JP')
            df = pytrends.interest_over_time()
            
            if df.empty or len(df) < 3 or keyword not in df.columns:
                continue

            past_avg = df[keyword].head(5).mean()
            recent_avg = df[keyword].tail(2).mean()

            if past_avg < 5:
                continue
            
            # 現在の急上昇率を計算
            current_spike_ratio = recent_avg / past_avg if past_avg > 0 else 0
            
            # これまでで最も高い急上昇率を記録
            if current_spike_ratio > best_spike_ratio:
                best_spike_ratio = current_spike_ratio

        except Exception as e:
            # APIエラーは頻発するので、ループを継続
            continue
    
    # 最も良かった結果が、2倍以上の上昇を示していれば「急上昇」と判断
    if best_spike_ratio > 2:
        final_score = weight * (best_spike_ratio / 2)
        return {"trends_jp_spike_score": final_score, "source_hit_flags": [f"🔍Gトレンド急上昇({best_spike_ratio:.1f}倍)"]}

    return {}