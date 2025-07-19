# radar/signals/slot_fit.py
import os
from datetime import datetime, timedelta
import pytz

JST = pytz.timezone('Asia/Tokyo')

def get_relevant_slots(cfg, now_jst):
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
    dt_slots = []
    for slot in slots:
        start_hour, end_hour = map(int, slot.split('-'))
        start_time = now_jst.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=start_hour)
        end_time = now_jst.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=end_hour)
        dt_slots.append((start_time, end_time))
    return dt_slots

def score(game, cfg, **_):
    if not game.get('event_start_jst') or not game.get('event_end_jst'): return {}
    now_jst = datetime.now(JST)
    event_start_jst = game['event_start_jst']
    relevant_slots = get_relevant_slots(cfg, now_jst)
    datetime_slots = parse_slots_to_datetime(relevant_slots, now_jst)
    fit_score = 0
    for start_slot, end_slot in datetime_slots:
        if (start_slot - timedelta(hours=3)) <= event_start_jst <= end_slot:
            fit_score = 1.0; break
        elif start_slot <= now_jst <= end_slot and game.get('is_event_active'):
            fit_score = 0.7
    weight = cfg['weights'].get('slot_fit', 0)
    final_score = fit_score * weight
    if final_score > 0: return {"slot_fit": final_score, "source_hit_flags": ["Slot Fit⤴️"]}
    return {}