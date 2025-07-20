# 【この内容で radar/signals/jp_ratio.py を作成・保存してください】

import asyncio

# このセンサーは非同期で動作する必要があります
async def score(game, cfg, twitch_api, **_):
    """
    Twitch APIを使い、特定のゲームの配信における
    日本語配信の割合を計算し、低すぎる場合にペナルティを課す。
    """
    # config.yamlからペナルティのルールを読み込む
    penalty_rule = cfg.get('penalties', {}).get('low_jp_ratio', {})
    threshold = penalty_rule.get('threshold') # 日本語比率の最低ライン
    weight = penalty_rule.get('weight')      # ペナルティの重み

    # ルールが設定されていなければ、何もしない
    if threshold is None or weight is None:
        return {}

    total_streams = 0
    jp_streams = 0
    
    try:
        # このゲームの配信を最大100件まで取得
        async for stream in twitch_api.get_streams(game_id=[game['id']], first=100):
            total_streams += 1
            # 配信言語が'ja'（日本語）だったらカウント
            if stream.language == 'ja':
                jp_streams += 1
        
        # 配信が全くない場合は、分析不能なので終了
        if total_streams == 0:
            return {}

        # 日本語配信の割合を計算
        jp_ratio = jp_streams / total_streams
        
        # 割合が設定した最低ライン(threshold)を下回っていたら、ペナルティを課す
        if jp_ratio < threshold:
            # スコアはマイナス値で返す
            return {"jp_ratio_penalty": -weight, "source_hit_flags": [f"🇯🇵日本語比率: {jp_ratio:.0%}"]}
            
    except Exception as e:
        print(f"⚠️ jp_ratio.pyでのAPIエラー: {e}")
        return {}
            
    return {}