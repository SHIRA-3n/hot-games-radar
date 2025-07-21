def score(game, cfg, jp_streams, **_):
    """
    【高速化版】司令塔から渡された日本語配信リスト(jp_streams)を元に、
    VPCと人気集中度を分析する。APIへの追加リクエストは行わない。
    """

    vpc_weight = cfg.get('weights', {}).get('viewers_per_ch', 0)
    top_share_penalty = cfg.get('penalties', {}).get('top_share', {})
    
    if vpc_weight == 0 and not top_share_penalty:
        return {}

    # --- ★★★【効率化！】★★★ ---
    # 司令塔から渡されたリストの中から、このゲームの配信だけを抽出
    streams_for_this_game = [s for s in jp_streams if s.game_id == game.get('id')]
        
    if not streams_for_this_game:
        return {}
        
    total_viewers = sum(s.viewer_count for s in streams_for_this_game)
    streamer_count = len(streams_for_this_game)
    
    final_scores = {}
    final_flags = []

    # --- 分析①：【日本の】VPC ---
    if vpc_weight > 0 and streamer_count > 0:
        viewers_per_channel = total_viewers / streamer_count
        vpc_score = viewers_per_channel * vpc_weight
        final_scores["viewers_per_ch_score"] = min(vpc_score, 50)
        final_flags.append(f"👥VPC(JP): {viewers_per_channel:.1f}")

    # --- 分析②：【日本の】人気集中度 ---
    if top_share_penalty and total_viewers > 0:
        threshold = top_share_penalty.get('threshold', 0.7)
        weight = top_share_penalty.get('weight', 80)
            
        top_streamer = max(streams_for_this_game, key=lambda s: s.viewer_count)
        top_streamer_viewers = top_streamer.viewer_count
            
        top_share_ratio = top_streamer_viewers / total_viewers
            
        if top_share_ratio > threshold:
            final_scores["top_share_penalty"] = -weight
            final_flags.append(f"🎯人気集中(JP): {top_share_ratio:.0%}")
        
    if final_scores:
        return {**final_scores, "source_hit_flags": final_flags}
            
    return {}