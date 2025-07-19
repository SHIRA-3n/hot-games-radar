# 【最終版テンプレート】この内容を radar/signals/competition.py に貼り付けてください

import os

# ▼▼▼【修正点①】関数を非同期モードにアップグレード▼▼▼
async def score(game, cfg, twitch_api, **_):
    """
    ゲームの競合状況を分析し、ブルーオーシャンなら加点、激戦区なら減点する関数。
    """
    my_avg_viewers = cfg.get('channel_profile', {}).get('avg_viewers', 30)
    competitor_range_min = my_avg_viewers * 0.5
    competitor_range_max = my_avg_viewers * 5
    
    if not game.get('id'):
        return {}

    try:
        # ▼▼▼【修正点②】「回転寿司」のお寿司を、全部お皿に乗せる書き方▼▼▼
        # async for を使って、流れてくる配信データ(s)を、一つずつstreamsというリストに格納する
        streams = [s async for s in twitch_api.get_streams(game_id=[game['id']], first=100)]

    except Exception as e:
        print(f"⚠️ competition.pyでのAPIエラー: {e}")
        return {}
        
    competitor_count = 0
    for stream in streams:
        if competitor_range_min <= stream.viewer_count <= competitor_range_max:
            competitor_count += 1

    bonus, penalty, tags = 0, 0, []
    
    # viewer_countは、この時点ではまだ取得できていないので、一旦この条件は外します
    # if game.get('viewer_count', 0) >= 1000 and competitor_count <= 5:
    if competitor_count <= 5: # シンプルに競合が5人以下ならボーナス
        bonus = cfg['weights'].get('blue_ocean_bonus', 0)
        if bonus > 0:
            tags.append("競合少なめ🚀")

    penalty_rule = cfg['penalties'].get('competitor_penalty', {})
    if competitor_count > penalty_rule.get('threshold', 20):
        penalty = penalty_rule.get('weight', 0)
        if penalty > 0:
            tags.append("激戦区🔥")

    final_score = bonus - penalty
    if final_score != 0:
        return {"competition_score": final_score, "source_hit_flags": tags}
    
    return {}