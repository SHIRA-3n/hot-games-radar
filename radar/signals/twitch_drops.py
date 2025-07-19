# 【この内容で radar/signals/twitch_drops.py を作成・保存してください】

def score(game, cfg, twitch_api, **_):
    """
    ゲームにDropsが有効になっているかをチェックし、スコアを加算する。
    """
    # この機能は、司令塔から渡されるゲーム情報に'game_data'オブジェクトが必要
    game_data = game.get('game_data')
    if not game_data or not hasattr(game_data, 'is_drops_enabled'):
        return {}

    if game_data.is_drops_enabled:
        # config.yamlから重みを取得
        weight = cfg.get('weights', {}).get('drops', 0)
        if weight > 0:
            return {"drops_score": weight, "source_hit_flags": ["💧Drops有効"]}
            
    return {}