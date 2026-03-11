"""Reddit sentiment collector for r/wallstreetbets and r/investing.

Aggregates daily sentiment scores and captures notable posts.
Stores numeric sentiment as Timeseries, top posts as NewsItem.
"""

import time
from datetime import datetime
from collections import Counter

import pandas as pd
import requests

from ix.collectors.base import BaseCollector
from ix.db.conn import Session


class RedditSentimentCollector(BaseCollector):
    name = "reddit_sentiment"
    display_name = "Reddit Sentiment"
    schedule = "0 8,14,20 * * *"  # 3x daily
    category = "sentiment"

    SUBREDDITS = ["wallstreetbets", "investing", "stocks"]

    # Simple keyword-based sentiment scoring
    BULLISH_KEYWORDS = [
        "bull", "calls", "moon", "rocket", "buy", "long", "breakout",
        "undervalued", "squeeze", "tendies", "yolo", "diamond hands",
        "green", "rip", "ath", "all time high", "pump",
    ]
    BEARISH_KEYWORDS = [
        "bear", "puts", "crash", "dump", "sell", "short", "overvalued",
        "bubble", "recession", "red", "drill", "rug pull", "bag holder",
        "loss porn", "guh", "dead cat", "capitulation",
    ]

    HEADERS = {
        "User-Agent": "Investment-X:v1.0 (by /u/investment_x_research)"
    }

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0

        total = len(self.SUBREDDITS) * 2  # fetch + process for each
        current = 0

        all_posts = []
        ticker_mentions = Counter()
        sentiment_scores = {"bullish": 0, "bearish": 0, "neutral": 0}

        with Session() as db:
            for sub in self.SUBREDDITS:
                current += 1
                if progress_cb:
                    progress_cb(current, total, f"Fetching r/{sub}")

                try:
                    posts = self._fetch_subreddit(sub)
                    all_posts.extend(posts)

                    for post in posts:
                        text = f"{post.get('title', '')} {post.get('selftext', '')}".lower()

                        # Score sentiment
                        bull_score = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text)
                        bear_score = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text)

                        if bull_score > bear_score:
                            sentiment_scores["bullish"] += 1
                        elif bear_score > bull_score:
                            sentiment_scores["bearish"] += 1
                        else:
                            sentiment_scores["neutral"] += 1

                        # Extract ticker mentions ($AAPL, $TSLA, etc.)
                        import re
                        tickers = re.findall(r'\$([A-Z]{1,5})\b', post.get("title", ""))
                        for t in tickers:
                            ticker_mentions[t] += 1

                except Exception as e:
                    self.logger.error(f"Error fetching r/{sub}: {e}")
                    errors += 1

                time.sleep(2)

            # Store aggregate sentiment as timeseries
            current += 1
            if progress_cb:
                progress_cb(current + len(self.SUBREDDITS), total, "Storing sentiment data")

            total_scored = sum(sentiment_scores.values())
            if total_scored > 0:
                today = pd.Timestamp.now().normalize()

                # Net sentiment score: (bullish - bearish) / total
                net_score = (sentiment_scores["bullish"] - sentiment_scores["bearish"]) / total_scored
                sentiment_series = pd.Series({today: net_score})

                self._upsert_timeseries(
                    db,
                    source="Reddit",
                    code="REDDIT_WSB_SENTIMENT",
                    source_code="Reddit:WSB_SENTIMENT",
                    name="Reddit Aggregate Sentiment Score",
                    category="Sentiment",
                    data=sentiment_series,
                    unit="score",
                )
                inserted += 1

                # Total mention count
                total_mentions = sum(ticker_mentions.values())
                mentions_series = pd.Series({today: float(total_mentions)})

                self._upsert_timeseries(
                    db,
                    source="Reddit",
                    code="REDDIT_WSB_MENTIONS_TOTAL",
                    source_code="Reddit:WSB_MENTIONS",
                    name="Reddit Total Ticker Mentions",
                    category="Sentiment",
                    data=mentions_series,
                    unit="count",
                )
                inserted += 1

            # Store top posts as NewsItems
            top_posts = sorted(all_posts, key=lambda p: p.get("score", 0), reverse=True)[:20]
            for post in top_posts:
                try:
                    selftext = post.get("selftext", "")
                    was_new = self._upsert_news_item(
                        db,
                        source="reddit",
                        source_name=f"Reddit r/{post.get('subreddit', 'unknown')}",
                        title=post.get("title", ""),
                        url=f"https://reddit.com{post.get('permalink', '')}",
                        body_text=selftext if selftext else None,
                        summary=selftext[:500] if selftext else None,
                        symbols=self._extract_tickers(post.get("title", "")),
                        meta={
                            "subreddit": post.get("subreddit"),
                            "score": post.get("score"),
                            "num_comments": post.get("num_comments"),
                            "author": post.get("author"),
                        },
                        published_at=datetime.utcfromtimestamp(post["created_utc"]) if post.get("created_utc") else None,
                    )
                    if was_new:
                        inserted += 1
                except Exception as e:
                    self.logger.warning(f"Failed to insert Reddit post: {e}")

        self.update_state(
            last_data_date=str(datetime.now().date()),
            extra_state={
                "ticker_mentions": dict(ticker_mentions.most_common(20)),
                "sentiment": sentiment_scores,
            },
        )

        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"Reddit: {inserted} items, sentiment {sentiment_scores}",
        }

    def _fetch_subreddit(self, subreddit: str, limit: int = 50) -> list:
        """Fetch hot posts from a subreddit using Reddit JSON API."""
        posts = []
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
            resp = requests.get(url, headers=self.HEADERS, timeout=30)

            if resp.status_code == 429:
                self.logger.warning(f"Reddit rate limited for r/{subreddit}")
                time.sleep(10)
                return []

            if resp.status_code != 200:
                self.logger.warning(f"Reddit returned {resp.status_code} for r/{subreddit}")
                return []

            data = resp.json()
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                posts.append({
                    "title": post.get("title", ""),
                    "selftext": post.get("selftext", ""),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "author": post.get("author", ""),
                    "permalink": post.get("permalink", ""),
                    "created_utc": post.get("created_utc"),
                    "subreddit": subreddit,
                })

        except Exception as e:
            self.logger.error(f"Failed to fetch r/{subreddit}: {e}")

        return posts

    def _extract_tickers(self, text: str) -> list:
        """Extract ticker symbols from text ($AAPL, $TSLA, etc.)."""
        import re
        tickers = re.findall(r'\$([A-Z]{1,5})\b', text)
        return list(set(tickers))
