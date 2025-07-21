import os
import tweepy
from datetime import datetime, timedelta, timezone

bearer_token = os.environ.get("X_BEARER")
client = tweepy.Client(bearer_token) if bearer_token else None

def score(game, cfg, **_):
    """
    X (Twitter) APIを使い、直近の日本語ツイートの「量」と「質（エンゲージメント）」
    の両面から、ゲームの話題性を評価する。
    """
    if not client:
        if not bearer_token:
            print("⚠️ twitter.py: X_BEARERが設定されていません。")
        return {}

    weight = cfg.get('weights', {}).get('twitter_jp_spike', 0)
    if weight == 0:
        return {}
        
    query = f'"{game["name"]}" OR #{game["name"]} -is:retweet lang:ja'
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    
    try:
        # --- ★★★【改善①】ツイートの「質」も取得できるように、拡張フィールドを指定★★★ ---
        response = client.search_recent_tweets(
            query=query,
            start_time=one_hour_ago,
            max_results=10, # 質を見るので、サンプルは10件で十分
            expansions=['author_id'],
            tweet_fields=['public_metrics'] # いいね、リツイート数などを取得
        )
        
        tweets = response.data
        if not tweets:
            return {}

        # --- ★★★【改善②】「量」と「質」を組み合わせたスコアリング★★★ ---
        
        # 1. 量のスコア：1時間あたりのツイート数
        #    (APIの仕様上、取得したツイート数(最大10)と、全体のツイート数(meta)を考慮)
        tweet_count = response.meta.get('result_count', 0)
        quantity_score_ratio = min(tweet_count / 100, 1.0) # 100件で満点

        # 2. 質のスコア：平均エンゲージメント（いいね+リツイート）
        total_engagement = 0
        for tweet in tweets:
            # public_metricsが存在し、辞書であることを確認
            if tweet.public_metrics and isinstance(tweet.public_metrics, dict):
                total_engagement += tweet.public_metrics.get('like_count', 0)
                total_engagement += tweet.public_metrics.get('retweet_count', 0)
        
        avg_engagement = total_engagement / len(tweets) if tweets else 0
        # 平均10エンゲージメントで満点とする（ハードルは低め）
        quality_score_ratio = min(avg_engagement / 10, 1.0)
        
        # 最終的なスコアは、量(70%)と質(30%)を組み合わせて算出
        final_score_ratio = (quantity_score_ratio * 0.7) + (quality_score_ratio * 0.3)
        final_score = weight * final_score_ratio

        if final_score > 0:
            return {"twitter_jp_spike_score": final_score, "source_hit_flags": [f"💬Xで話題({tweet_count}+)"]}

    except tweepy.errors.TweepyException:
        return {}
    except Exception as e:
        print(f"⚠️ twitter.pyで予期せぬエラー: {e}")
        return {}
            
    return {}