# 【真の最終版テンプレート】この内容で upcoming_event.py を全文上書き

import pandas as pd
from datetime import datetime
import pytz

# score関数の引数を、司令塔が渡してくれるものだけに整理
def score(game, cfg, events_df, **_):
    """
    司令塔から渡されたイベントデータフレームを元に、スコアを計算する。
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
        
        # 30日以内のイベントのみを評価対象とする
        if 0 <= days_until_event <= 30:
            proximity_bonus = (31 - days_until_event) / 31
            current_score = event['hype_weight'] * proximity_bonus
            
            if current_score > best_score:
                best_score = current_score
                if days_until_event == 0:
                    best_flag = f"EVENT(本日開始!): {event['event_name']}"
                else:
                    best_flag = f"EVENT({days_until_event}日後): {event['event_name']}"

    if best_score > 0:
        weight = cfg.get('weights', {}).get('upcoming_event_score', 1)
        final_score = best_score * weight
        if final_score > 0:
            return {"upcoming_event_score": final_score, "source_hit_flags": [best_flag]}
            
    return {}