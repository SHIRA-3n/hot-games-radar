import asyncio

async def score(game, cfg, twitch_api, **_):
    """
    【日本市場特化】
    日本の配信者のデータに基づき、VPCと人気集中度を分析する。
    """
    vpc_weight = cfg.get('weights', {}).get('viewers_per_ch', 0)
    top_share_penalty = cfg.get('penalties', {}).get('top_share', {})
    
    if vpc_weight == 0 and not top_share_penalty:
        return {}

    try:
        # --- ★★★【改善①】分析対象を「日本の配信者」に限定★★★ ---
        # このゲームの「日本語」配信を最大100件まで取得
        streams = [s async for s in twitch_api.get_streams(game_id=[game['id']], language='ja', first=100)]
        
        if not streams:
            return {}
        
        # --- これ以降の分析は、全て「日本のデータ」に基づいて行われる ---
        
        total_viewers = sum(s.viewer_count for s in streams)
        streamer_count = len(streams)
        
        final_scores = {}
        final_flags = []

        # --- 分析①：【日本の】配信者1人あたりの視聴者数 (VPC) ---
        if vpc_weight > 0 and streamer_count > 0:
            viewers_per_channel = total_viewers / streamer_count
            vpc_score = viewers_per_channel * vpc_weight
            final_scores["viewers_per_ch_score"] = min(vpc_score, 50) # 上限50点は維持
            final_flags.append(f"👥VPC(JP): {viewers_per_channel:.1f}") # タグに(JP)を追加

        # --- 分析②：【日本の】トップ配信者への人気集中度 (Top Share) ---
        if top_share_penalty and total_viewers > 0:
            threshold = top_share_penalty.get('threshold', 0.7)
            weight = top_share_penalty.get('weight', 80)
            
            # 視聴者数が最も多い配信者を取得 (streamsはソートされていないのでmax関数を使う)
            top_streamer = max(streams, key=lambda s: s.viewer_count)
            top_streamer_viewers = top_streamer.viewer_count
            
            top_share_ratio = top_streamer_viewers / total_viewers
            
            if top_share_ratio > threshold:
                final_scores["top_share_penalty"] = -weight
                final_flags.append(f"🎯人気集中(JP): {top_share_ratio:.0%}") # タグに(JP)を追加
        
        if final_scores:
            return {**final_scores, "source_hit_flags": final_flags}

    except Exception as e:
        print(f"⚠️ market_health.pyでのAPIエラー: {e}")
        return {}
            
    return {}