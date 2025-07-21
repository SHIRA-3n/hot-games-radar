import pandas as pd
from datetime import datetime
import pytz

# ★★★【改善①】引数に horizon を追加★★★
def score(game, cfg, events_df, horizon='3d', **_):
    """
    司令塔から渡されたhorizon(3d/7d/30d)に応じて、
    未来のイベントを評価する。
    """
    if events_df is None or events_df.empty:
        return {}

    game_events = events_df[events_df['game_name'].str.lower() == game['name'].lower()]
    if game_events.empty:
        return {}

    today = datetime.now(pytz.timezone('Asia/Tokyo'))
    best_score = 0
    best_flag = None

    for _, event in game_events.iterrows():
        start_time = event['start_jst'].tz_localize('Asia/Tokyo') if event['start_jst'].tzinfo is None else event['start_jst']
        days_until_event = (start_time - today).days
        
        # --- ★★★【改善②】horizonに応じた、賢いスコアリング★★★ ---
        
        current_score = 0
        
        # --- now (3d) モードの評価 ---
        # 「まさに今日」開始されるイベントを最高に評価
        if horizon == '3d' and -1 <= days_until_event <= 1: # 昨日～明日
            current_score = event['hype_weight'] * 1.5 # 1.5倍ブースト！
            
        # --- week (7d) モードの評価 ---
        # 「7日以内」に開始されるイベントを評価
        elif horizon == '7d' and 0 <= days_until_event <= 7:
            # 日が近いほどスコアが高くなる
            proximity_bonus = (8 - days_until_event) / 8
            current_score = event['hype_weight'] * proximity_bonus
            
        # --- month (30d) モードの評価 ---
        # 「30日以内」に開始されるイベントを評価
        elif horizon == '30d' and 0 <= days_until_event <= 30:
            # 月モードでは、近さよりもイベント自体の重要度を評価
            current_score = event['hype_weight']

        # --- スコアとフラグの更新 ---
        if current_score > best_score:
            best_score = current_score
            if days_until_event <= 0:
                best_flag = f"EVENT(開催中!): {event['event_name']}"
            else:
                best_flag = f"EVENT({days_until_event}日後): {event['event_name']}"

    if best_score > 0:
        # config.yamlの重み付けは、各horizonモードごとに適用される
        weight = cfg.get('weights', {}).get(horizon, {}).get('upcoming_event_score', 1)
        final_score = best_score * weight
        if final_score > 0:
            return {"upcoming_event_score": final_score, "source_hit_flags": [best_flag]}
            
    return {}