"""
Telegram channel configuration for the macro research pipeline.

Provides channel list and API credentials used by scripts/research/macro_research.py
for direct Telegram scraping via telethon.
"""

import os
from pathlib import Path

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = str(Path(__file__).parent / "ix_session")

CHANNELS_TO_SCRAPE = [
    # ── Korean Broker Research ──
    "t.me/HANAchina",
    "t.me/EMchina",
    "t.me/hanaglobalbottomup",
    "t.me/hanabondview",
    "t.me/HanaResearch",
    "t.me/shinhanresearch",
    "t.me/KISemicon",
    "t.me/strategy_kis",
    "t.me/kiwoom_semibat",
    "t.me/merITz_tech",
    "t.me/meritz_research",
    "t.me/growthresearch",
    "t.me/eugene2team",
    "t.me/Brain_And_Body_Research",
    "t.me/daishinstrategy",
    "t.me/yuantaresearch",
    "t.me/companyreport",
    "t.me/repostory123",
    # ── Korean Analysts & Strategists ──
    "t.me/hermitcrab41",
    "t.me/Yeouido_Lab",
    "t.me/EarlyStock1",
    "t.me/globaletfi",
    "t.me/Inhwan_Ha",
    "t.me/jkc123",
    "t.me/sskimfi",
    "t.me/globalequity1",
    "t.me/sypark_strategy",
    "t.me/bottomupquantapproach",
    "t.me/TNBfolio",
    "t.me/globalbobo",
    "t.me/lim_econ",
    "t.me/Jstockclass",
    "t.me/awake_schedule",
    "t.me/KoreaIB",
    "t.me/buffettlab",
    "t.me/YeouidoStory2",
    "t.me/sejongdata2013",
    "t.me/tRadarnewsdesk",
    # ── Japan / Asia Research ──
    "t.me/aetherjapanresearch",
    # ── Wire Services & Major Media ──
    "t.me/ReutersWorldChannel",
    "t.me/bloomberg",
    "t.me/FinancialNews",
    "t.me/BloombergQ",
    "t.me/wall_street_journal_news",
    "t.me/cnaborsenews",
    "t.me/naborsenews",
    # ── English Macro / Research (P0) ──
    "t.me/MarketEar",
    "t.me/unusual_whales",
    "t.me/CryptoMacroNews",
    "t.me/zaborskychannel",
    "t.me/biancoresearch",
    "t.me/WatcherGuru",
    "t.me/financialjuice",
    # ── English Macro / Research (P1) ──
    "t.me/MacroAlf",
    "t.me/TheTerminal",
    "t.me/BISgram",
    "t.me/FedWatch",
    "t.me/IIF_GlobalDebt",
    "t.me/IMFNews",
    "t.me/WorldBankLive",
    # ── English Macro / Research (P2) ──
    "t.me/realvisionchannel",
    "t.me/GoldTelegraph",
    "t.me/MacroScope",
    "t.me/ZeroHedge",
    "t.me/ForexFactory",
    "t.me/TradingView",
]
