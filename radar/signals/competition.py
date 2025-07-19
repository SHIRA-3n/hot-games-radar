# radar/signals/competition.py
import os

def score(game, cfg, twitch_api, **_):
    my_avg_viewers = cfg.get('channel_profile', {}).get('avg_viewers', 30)
    competitor_range_min = my_avg_viewers * 0.5
    competitor_range_max = my_avg_viewers * 5
    if not game.get('id'): return {}
    try:
        streams = twitch_api.get_streams(game_id=[game['id']], first=100)['data']
    except Exception as e:
        print(f"競合分析中のAPIエラー: {e}"); return {}
    competitor_count = sum(1 for s in streams if competitor_range_min <= s['viewer_count'] <= competitor_range_max)
    bonus, penalty, tags = 0, 0, []
    if game.get('viewer_count', 0) >= 1000 and competitor_count <= 5:
        bonus = cfg['weights'].get('blue_ocean_bonus', 0)
        if bonus > 0: tags.append("競合少なめ🚀")
    penalty_rule = cfg['penalties'].get('competitor_penalty', {})
    if competitor_count > penalty_rule.get('threshold', 20):
        penalty = penalty_rule.get('weight', 0)
        if penalty > 0: tags.append("激戦区🔥")
    final_score = bonus - penalty
    if final_score != 0: return {"competition_score": final_score, "source_hit_flags": tags}
    return {}