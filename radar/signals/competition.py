import asyncio
import time

async def score(game, cfg, twitch_api, **_):
    """
    競合（日本人配信者）の状況を分析し、市場の参入しやすさを評価する。
    APIへの負荷を考慮し、待機処理を挟む。
    """
    # ★★★【最後の働き方改革！】★★★
    # Twitch APIへの連続アクセスを防ぐため、1秒間待機する
    # これにより、レートリミットに遭遇する可能性を劇的に減らす
    await asyncio.sleep(1)

    my_avg_viewers = cfg.get('channel_profile', {}).get('avg_viewers', 10)
    competitor_range_min = my_avg_viewers * 0.3
    competitor_range_max = my_avg_viewers * 2.5
    
    if not game.get('id'):
        return {}

    try:
        streams = [s async for s in twitch_api.get_streams(game_id=[game['id']], language='ja', first=100)]
    except Exception as e:
        # レートリミット等でエラーになっても、警告は出さずに静かに終了
        # print(f"⚠️ competition.pyでのAPIエラー: {e}")
        return {}
        
    competitor_count = 0
    for stream in streams:
        if competitor_range_min <= stream.viewer_count <= competitor_range_max:
            competitor_count += 1

    bonus, penalty, tags = 0, 0, []
    
    base_bonus = cfg.get('weights', {}).get('blue_ocean_bonus', 25)
    if competitor_count == 0:
        bonus = base_bonus * 1.5
        tags.append("競合ゼロ🚀")
    elif competitor_count <= 3:
        bonus = base_bonus
        tags.append(f"競合わずか({competitor_count}人)✨")
    elif competitor_count <= 5:
        bonus = base_bonus * 0.7
        tags.append(f"競合少なめ({competitor_count}人)👍")

    penalty_rule = cfg.get('penalties', {}).get('competitor_penalty', {})
    if competitor_count > penalty_rule.get('threshold', 20):
        penalty = penalty_rule.get('weight', 25)
        if penalty > 0:
            tags.append(f"激戦区🔥({competitor_count}人)")

    final_score = bonus - penalty
    if final_score != 0:
        return {"competition_score": final_score, "source_hit_flags": tags}
    
    return {}