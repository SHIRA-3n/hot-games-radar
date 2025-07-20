# 【この内容で radar/signals/google_trends.py を作成・保存してください】

from pytrends.request import TrendReq
import pandas as pd

# Googleトレンドに接続するためのオブジェクトを準備
# hl='ja-JP'で日本語、tz=540で日本時間を指定
pytrends = TrendReq(hl='ja-JP', tz=540)

def score(game, cfg, **_):
    """
    Googleトレンドを使い、日本でのゲーム名の検索インタレストが
    直近で急上昇しているかを評価する。
    """
    # config.yamlから重みを読み込む
    weight = cfg.get('weights', {}).get('trends_jp_spike', 0)
    if weight == 0:
        return {}

    # 検索キーワードを設定 (例: "原神 ゲーム")
    # "ゲーム"と付けることで、無関係な検索結果を排除しやすくなる
    keyword = f"{game['name']} ゲーム"
    
    try:
        # 過去7日間の日別トレンドデータを取得
        pytrends.build_payload([keyword], cat=0, timeframe='today 7-d', geo='JP')
        # interest_over_time()はDataFrameを返す
        df = pytrends.interest_over_time()
        
        # データが十分にない場合は、分析不能なので終了
        if df.empty or len(df) < 3:
            return {}

        # トレンドの急上昇を検知するロジック
        # (これは一例です。より高度な分析も可能)
        
        # 過去5日間の平均値と、直近2日間の平均値を比較
        past_avg = df[keyword].head(5).mean()
        recent_avg = df[keyword].tail(2).mean()

        # ノイズ（普段から検索数が0に近い）を避けるため、過去の平均が低すぎる場合は無視
        if past_avg < 5: # 基準値。0~100の相対値なので5はかなり低い
             return {}
        
        # 直近の平均が、過去の平均の2倍以上になっていたら「急上昇」と判断
        if recent_avg > past_avg * 2:
            spike_ratio = recent_avg / past_avg
            # スコアは、急上昇の比率に応じて少し変動させる
            final_score = weight * (spike_ratio / 2) # 2倍で満点、3倍なら1.5倍のスコア

            return {"trends_jp_spike": final_score, "source_hit_flags": [f"🔍Gトレンド急上昇({spike_ratio:.1f}倍)"]}

    except Exception as e:
        # pytrendsは時々エラーを返すことがあるので、静かに処理を終了
        # print(f"⚠️ google_trends.pyでエラー: {e}")
        return {}
            
    return {}