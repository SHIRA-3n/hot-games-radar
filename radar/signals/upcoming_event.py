# 【最終版テンプレート】この内容で upcoming_event.py を全文上書き

import pandas as pd
from datetime import datetime
import pytz

def score(game, cfg, events_df, **_):
    """
    司令塔から渡されたイベントデータフレームを元に、スコアを計算する。
    """
    # 司令塔からデータが渡されなければ、何もしない
    if events_df is None or events_df.empty:
        return {}

    # このゲームに関連するイベントを探す
    game_events = events_df[events_df['game_name'].str.lower() == game['name'].lower()]
    if game_events.empty:
        return {}

    # 最も近い未来のイベントでスコアを計算
    today = datetime.now(pytz.timezone('Asia/Tokyo'))
    best_score = 0
    best_flag = None

    for _, event in game_events.iterrows():
        # タイムゾーン情報がない場合は、JSTとして扱う
        start_time = event['start_jst'].tz_localize('Asia/Tokyo') if event['start_jst'].tzinfo is None else event['start_jst']
        
        days_until_event = (start_time - today).days
        
        current_score = 0
        current_flag = None
        
        # horizonに応じてスコアを計算
        # "week"モードで、イベントが7日以内の場合
        if horizon == '7d' and 0 <= days_until_event <= 7:
            # 日が近いほどスコアが高くなるように調整
            current_score = event['hype_weight'] * ((8 - days_until_event) / 8) # 0日後もスコアが出るように調整
            current_flag = f"EVENT({days_until_event}日後): {event['event_name']}"
            
        # "month"モードで、イベントが30日以内の場合
        elif horizon == '30d' and 0 <= days_until_event <= 30:
            current_score = event['hype_weight']
            current_flag = f"EVENT({days_until_event}日後): {event['event_name']}"
        
        # "now"モードでも、まさに今日開始のイベントは高評価
        elif horizon == '3d' and days_until_event == 0:
             current_score = event['hype_weight']
             current_flag = f"EVENT(本日開始!): {event['event_name']}"

        # 複数のイベントがある場合、最もスコアが高いものを採用
        if current_score > best_score:
            best_score = current_score
            best_flag = current_flag
            
    if best_score > 0:
        # 重み付けはconfig.yamlで行うので、ここでは計算済みのスコアをそのまま返す
        return {"upcoming_event_score": best_score, "source_hit_flags": [best_flag]}
            
    return {}