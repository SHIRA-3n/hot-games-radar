# 【この内容で radar/signals/twitter.py を作成・保存してください】

import os
import tweepy
from datetime import datetime, timedelta, timezone

# X API v2を利用するためのクライアントを初期化
# GitHub Actionsの環境変数からBearer Tokenを安全に読み込む
bearer_token = os.environ.get("X_BEARER")
client = tweepy.Client(bearer_token) if bearer_token else None

def score(game, cfg, **_):
    """
    X (Twitter) APIを使い、直近の日本語ツイート数から
    ゲームの話題性を評価する。
    """
    # APIクライアントが初期化できなければ、何もしない
    if not client:
        if not bearer_token:
            print("⚠️ twitter.py: X_BEARERが設定されていません。")
        return {}

    # config.yamlから重みを読み込む
    weight = cfg.get('weights', {}).get('twitter_jp_spike', 0)
    if weight == 0:
        return {}
        
    # 検索クエリを作成
    # 例: 「"原神" OR #原神 -is:retweet lang:ja」
    # (リツイートを除外し、日本語に限定)
    query = f'"{game["name"]}" OR #{game["name"]} -is:retweet lang:ja'
    
    # 過去1時間以内のツイートを検索
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    
    try:
        # X API v2のツイート検索機能を利用
        response = client.search_recent_tweets(
            query=query,
            start_time=one_hour_ago,
            max_results=100 # 話題性を測るには100件で十分
        )
        
        # ツイート数を取得
        tweet_count = response.meta.get('result_count', 0)

        # ツイート数に基づいてスコアを計算（これは一例です）
        # 1時間で100件以上のツイートがあれば、最大のスコアを与える
        score_ratio = min(tweet_count / 100, 1.0)
        final_score = weight * score_ratio

        if final_score > 0:
            return {"twitter_jp_spike": final_score, "source_hit_flags": [f"💬Xで話題({tweet_count}+)"]}

    except tweepy.errors.TweepyException as e:
        # APIエラー（レートリミットなど）の場合は静かに処理を終了
        # print(f"⚠️ twitter.pyでのAPIエラー: {e}")
        return {}
    except Exception as e:
        print(f"⚠️ twitter.pyで予期せぬエラー: {e}")
        return {}
            
    return {}