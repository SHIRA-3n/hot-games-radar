import asyncio

async def score(game, cfg, twitch_api, **_):
    """
    グローバルと日本の両方の視点から日本語配信の割合を評価し、
    ペナルティとボーナスの両方を考慮する。
    """
    penalty_rule = cfg.get('penalties', {}).get('low_jp_ratio', {})
    threshold = penalty_rule.get('threshold', 0.05)
    penalty_weight = penalty_rule.get('weight', 50)
    
    # ★★★【改善②】ボーナス用の設定をconfig.yamlから読み込む★★★
    bonus_rule = cfg.get('weights', {}).get('high_jp_ratio_bonus', {})
    bonus_threshold = bonus_rule.get('threshold', 0.3) # 30%以上ならボーナス
    bonus_weight = bonus_rule.get('weight', 20)      # 20点加算

    if not game.get('id'):
        return {}

    try:
        # --- ★★★【改善①】2つの異なるサンプルを調査★★★ ---
        
        # 調査①：全世界の人気配信者100人
        global_streams = [s async for s in twitch_api.get_streams(game_id=[game['id']], first=100)]
        
        # 調査②：日本の人気配信者100人
        jp_streams_sample = [s async for s in twitch_api.get_streams(game_id=[game['id']], language='ja', first=100)]
        
        # --- 2つの調査結果を統合して分析 ---
        
        global_total = len(global_streams)
        global_jp_count = sum(1 for s in global_streams if s.language == 'ja')

        # グローバル市場での日本語比率を計算
        jp_ratio_in_global = global_jp_count / global_total if global_total > 0 else 0
        
        final_score = 0
        tags = []

        # ペナルティ判定：グローバル市場で、日本語比率が低すぎるか？
        if jp_ratio_in_global < threshold:
            final_score -= penalty_weight
            tags.append(f"🇯🇵JP比率低い({jp_ratio_in_global:.0%})")

        # ボーナス判定：日本の配信者コミュニティが、十分に大きいか？
        # (日本の配信者サンプルが50人以上いて、かつグローバル比率が30%以上)
        if len(jp_streams_sample) >= 50 and jp_ratio_in_global >= bonus_threshold:
             final_score += bonus_weight
             tags.append(f"🇯🇵JPコミュニティ活発✨")
        
        if final_score != 0:
            return {"jp_ratio_score": final_score, "source_hit_flags": tags}

    except Exception as e:
        print(f"⚠️ jp_ratio.pyでのAPIエラー: {e}")
        return {}
            
    return {}