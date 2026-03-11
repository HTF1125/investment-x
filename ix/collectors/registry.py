"""Collector registry — maps collector names to instances and provides scheduler helpers."""

from ix.collectors.cftc import CFTCCollector
from ix.collectors.aaii import AAIISentimentCollector
from ix.collectors.cboe import CBOECollector
from ix.collectors.google_trends import GoogleTrendsCollector
from ix.collectors.sec_13f import SEC13FCollector
from ix.collectors.insider_tx import InsiderTransactionCollector
from ix.collectors.finra_darkpool import FINRADarkPoolCollector
from ix.collectors.investor_letters import InvestorLettersCollector
from ix.collectors.academic import AcademicPapersCollector
from ix.collectors.reddit_sentiment import RedditSentimentCollector

ALL_COLLECTORS = [
    CFTCCollector(),
    AAIISentimentCollector(),
    CBOECollector(),
    GoogleTrendsCollector(),
    SEC13FCollector(),
    InsiderTransactionCollector(),
    FINRADarkPoolCollector(),
    InvestorLettersCollector(),
    AcademicPapersCollector(),
    RedditSentimentCollector(),
]

COLLECTOR_MAP = {c.name: c for c in ALL_COLLECTORS}


def get_collector(name: str):
    """Get a collector instance by name."""
    return COLLECTOR_MAP.get(name)


def get_all_collectors():
    """Get all registered collectors."""
    return ALL_COLLECTORS
