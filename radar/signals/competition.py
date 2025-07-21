import asyncio

async def score(game, cfg, twitch_api, **_):
    """
    競合（日本人配信者）の状況を分析し、市場の参入しやすさを評価する。
    """
    my_avg_viewers = cfg.get('channel_profile', {}).get('avg_viewers', 10)
    
    # --- ★★★【改善①】競合の定義を、より現実的に修正★★★ ---
    # あなたの視聴者数の0.3倍～2.5倍の配信者を「直接的な競合」と定義
    competitor_range_min = my_avg_viewers * 0.3
    competitor_range_max = my_avg_viewers * 2.5
    
    if not game.get('id'):
        return {}

    try:
        # 配信言語が'ja'（日本語）のものだけに絞り込む
        streams = [s async for s in twitch_api.get_streams(game_id=[game['id']], language='ja', first=100)]
    except Exception as e:
        print(f"⚠️ competition.pyでのAPIエラー: {e}")
        return {}
        
    competitor_count = 0
    for stream in streams:
        if competitor_range_min <= stream.viewer_count <= competitor_range_max:
            competitor_count += 1

    bonus = 0
    penalty = 0
    tags = []
    
    # --- ★★★【改善②】ボーナス判定を「多段階評価」に進化★★★ ---
    base_bonus = cfg.get('weights', {}).get('blue_ocean_bonus', 25)
    if competitor_count == 0:
        bonus = base_bonus * 1.5  # 競合ゼロなら、ボーナス1.5倍！
        tags.append("競合ゼロ🚀")
    elif competitor_count <= 3:
        bonus = base_bonus      # 3人以下なら、満額ボーナス
        tags.append(f"競合わずか({competitor_count}人)✨")
    elif competitor_count <= 5:
        bonus = base_bonus * 0.7  # 5人以下でも、少しだけボーナス
        tags.append(f"競合少なめ({competitor_count}人)👍")

    # ペナルティ判定は、現在のconfig.yamlの設定をそのまま活用
    penalty_rule = cfg.get('penalties', {}).get('competitor_penalty', {})
    if competitor_count > penalty_rule.get('threshold', 20):
        penalty = penalty_rule.get('weight', 25)
        if penalty > 0:
            tags.append(f"激戦区🔥({competitor_count}人)")

    final_score = bonus - penalty
    if final_score != 0:
        return {"competition_score": final_score, "source_hit_flags": tags}
    
    return {}