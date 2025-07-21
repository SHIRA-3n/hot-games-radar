from datetime import datetime, timedelta
import pytz

# このセンサーは非同期である必要はありません
def score(game, cfg, events_df, **_):
    """
    司令塔から渡されたイベント台帳(events_df)を元に、
    イベント日時と、あなたの配信スケジュールの相性を評価する。
    """
    # イベント台帳がなければ、分析不能
    if events_df is None or events_df.empty:
        return {}
        
    # --- ★★★【改善①】イベント台帳から、このゲームの情報を取得★★★ ---
    game_events = events_df[events_df['game_name'].str.lower() == game['name'].lower()]
    if game_events.empty:
        return {} # このゲームに関するイベントは登録されていない

    # --- これ以降は、あなたの元の優れたロジックを、ほぼそのまま活用します ---
    
    JST = pytz.timezone('Asia/Tokyo')
    now_jst = datetime.now(JST)
    
    # 複数のイベントがある場合、最もフィットするもので評価
    best_fit_score = 0
    
    for _, event in game_events.iterrows():
        # タイムゾーン情報を付与
        event_start_jst = event['start_jst'].tz_localize('Asia/Tokyo') if event['start_jst'].tzinfo is None else event['start_jst']

        # あなたの配信スケジュールを取得
        relevant_slots = get_relevant_slots(cfg, now_jst)
        datetime_slots = parse_slots_to_datetime(relevant_slots, now_jst)
    
        current_fit_score = 0
        for start_slot, end_slot in datetime_slots:
            # イベント開始が、配信スロットの3時間前から配信終了までの間にあるか (最高評価)
            if (start_slot - timedelta(hours=3)) <= event_start_jst <= end_slot:
                current_fit_score = 1.0; break
        
        if current_fit_score > best_fit_score:
            best_fit_score = current_fit_score

    if best_fit_score > 0:
        weight = cfg.get('weights', {}).get('slot_fit', 30)
        final_score = best_fit_score * weight
        return {"slot_fit_score": final_score, "source_hit_flags": ["⏰配信時間に最適！"]}

    return {}

# --- 以下は、あなたのコードに含まれていたヘルパー関数です（変更なし） ---

def get_relevant_slots(cfg, now_jst):
    """今日と明日の配信スケジュールを取得する"""
    today_weekday = now_jst.strftime('%a').lower()
    tomorrow_weekday = (now_jst + timedelta(days=1)).strftime('%a').lower()
    slots = []
    slots.extend(cfg['stream_slots'].get(today_weekday, []))
    for slot in cfg['stream_slots'].get(tomorrow_weekday, []):
        start_hour, end_hour = map(int, slot.split('-'))
        if start_hour < 12:
            slots.append(f"{start_hour+24}-{end_hour+24}")
    return slots

def parse_slots_to_datetime(slots, now_jst):
    """['21-27'] のような文字列を、具体的な日時の範囲に変換する"""
    dt_slots = []
    for slot in slots:
        start_hour, end_hour = map(int, slot.split('-'))
        start_time = now_jst.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=start_hour)
        end_time = now_jst.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=end_hour)
        dt_slots.append((start_time, end_time))
    return dt_slots