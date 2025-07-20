# 【この内容で radar/signals/market_health.py を作成・保存してください】

import asyncio

# このセンサーは非同期で動作する必要があります
async def score(game, cfg, twitch_api, **_):
    """
    Twitch APIを使い、配信者1人あたりの視聴者数と、
    トップ配信者への人気集中度を分析する。
    """
    # config.yamlから、このアナリストが使う2つのルールを読み込む
    vpc_weight = cfg.get('weights', {}).get('viewers_per_ch', 0)
    top_share_penalty = cfg.get('penalties', {}).get('top_share', {})
    
    # ルールが何も設定されていなければ、何もしない
    if vpc_weight == 0 and not top_share_penalty:
        return {}

    streams = []
    total_viewers = 0
    
    try:
        # このゲームの配信を最大100件まで取得
        # 全世界の配信者を対象に分析するため、languageフィルターはかけない
        async for stream in twitch_api.get_streams(game_id=[game['id']], first=100):
            streams.append(stream)
            total_viewers += stream.viewer_count
        
        # 配信が全くない場合は、分析不能なので終了
        if not streams:
            return {}
        
        streamer_count = len(streams)
        final_scores = {}
        final_flags = []

        # --- 分析①：配信者1人あたりの視聴者数 (Viewers Per Channel) ---
        if vpc_weight > 0:
            viewers_per_channel = total_viewers / streamer_count
            # このスコアは単純な加算ではなく、指標そのものをスコアとする
            # 例: 1人あたり50人見ていれば、スコアに50が加わるイメージ
            # 重み(weight)は、その影響度を調整する「倍率」として使う
            vpc_score = viewers_per_channel * vpc_weight
            final_scores["viewers_per_ch_score"] = min(vpc_score, 50)
            final_flags.append(f"👥VPC: {viewers_per_channel:.1f}")

        # --- 分析②：トップ配信者への人気集中度 (Top Share) ---
        if top_share_penalty:
            threshold = top_share_penalty.get('threshold', 0.8) # デフォルト80%
            weight = top_share_penalty.get('weight', 0)
            
            # 視聴者数が多い順に配信を並び替え
            streams.sort(key=lambda s: s.viewer_count, reverse=True)
            
            # 1位の配信者の視聴者数を取得
            top_streamer_viewers = streams[0].viewer_count
            
            # 1位の配信者が、全体の視聴者数の何%を占めているか計算
            top_share_ratio = top_streamer_viewers / total_viewers
            
            # 集中度がしきい値(threshold)を超えていたら、ペナルティ
            if top_share_ratio > threshold:
                final_scores["top_share_penalty"] = -weight
                final_flags.append(f"🎯人気集中({top_share_ratio:.0%})")
        
        if final_scores:
            return {**final_scores, "source_hit_flags": final_flags}

    except Exception as e:
        print(f"⚠️ market_health.pyでのAPIエラー: {e}")
        return {}
            
    return {}