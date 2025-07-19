# 【この内容で radar/signals/upcoming_event.py を作成・保存してください】

import pandas as pd
from datetime import datetime
import pytz
import os

def score(game, cfg, horizon, **_):
    """
    events.csvを読み込み、未来のイベントまでの日数に応じてスコアを計算する。
    """
    csv_path = 'events.csv'
    if not os.path.exists(csv_path):
        return {} # ファイルがなければ何もしない

    try:
        # encoding='utf-8' を指定して日本語の文字化けを防ぐ
        events_df = pd.read_csv(csv_path, parse_dates=['start_jst', 'end_jst'], encoding='utf-8')
    except Exception as e:
        print(f"⚠️ events.csvの読み込みに失敗しました: {e}")
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