"""Investor letters collector.

Checks major investment firms' websites for new publications, memos, and letters.
Stores as NewsItem entries with source="investor_letter".
"""

import time
from datetime import datetime

import requests
import feedparser
from bs4 import BeautifulSoup

from ix.collectors.base import BaseCollector
from ix.collectors.fulltext import fetch_full_text
from ix.db.conn import Session


class InvestorLettersCollector(BaseCollector):
    name = "investor_letters"
    display_name = "Investor Letters"
    schedule = "0 10 * * *"  # Daily 10 AM
    category = "research"

    SOURCES = [
        {
            "name": "Howard Marks (Oaktree)",
            "url": "https://www.oaktreecapital.com/insights/memos",
            "type": "scrape",
            "author": "Howard Marks",
            "fund": "Oaktree Capital",
        },
        {
            "name": "GMO Quarterly",
            "url": "https://www.gmo.com/americas/research-library/",
            "type": "scrape",
            "author": "GMO",
            "fund": "GMO",
        },
        {
            "name": "Hussman Weekly",
            "url": "https://www.hussmanfunds.com/category/comment/",
            "type": "scrape",
            "author": "John Hussman",
            "fund": "Hussman Funds",
        },
        {
            "name": "AQR Research",
            "url": "https://www.aqr.com/Insights/Research",
            "type": "scrape",
            "author": "AQR",
            "fund": "AQR Capital",
        },
        {
            "name": "Research Affiliates",
            "url": "https://www.researchaffiliates.com/publications",
            "type": "scrape",
            "author": "Research Affiliates",
            "fund": "Research Affiliates",
        },
        {
            "name": "Verdad Capital",
            "url": "https://verdadcap.com/archive",
            "type": "scrape",
            "author": "Verdad",
            "fund": "Verdad Capital",
        },
        {
            "name": "Epsilon Theory",
            "url": "https://www.epsilontheory.com/feed/",
            "type": "rss",
            "author": "Ben Hunt",
            "fund": "Epsilon Theory",
        },
        {
            "name": "Lyn Alden",
            "url": "https://www.lynalden.com/feed/",
            "type": "rss",
            "author": "Lyn Alden",
            "fund": "Lyn Alden Investment Strategy",
        },
        {
            "name": "Crescat Capital",
            "url": "https://www.crescat.net/feed/",
            "type": "rss",
            "author": "Crescat",
            "fund": "Crescat Capital",
        },
        # ── Substack Newsletters (P0 — Must Have) ──
        {
            "name": "The Macro Compass",
            "url": "https://themacrocompass.substack.com/feed",
            "type": "rss",
            "author": "Alfonso Peccatiello",
            "fund": "The Macro Compass",
        },
        {
            "name": "Net Interest",
            "url": "https://www.netinterest.co/feed",
            "type": "rss",
            "author": "Marc Rubinstein",
            "fund": "Net Interest",
        },
        {
            "name": "Apricitas Economics",
            "url": "https://www.apricitas.io/feed",
            "type": "rss",
            "author": "Joseph Politano",
            "fund": "Apricitas Economics",
        },
        {
            "name": "Chartbook",
            "url": "https://adamtooze.substack.com/feed",
            "type": "rss",
            "author": "Adam Tooze",
            "fund": "Chartbook",
        },
        {
            "name": "Kyla Scanlon",
            "url": "https://kylascanlon.substack.com/feed",
            "type": "rss",
            "author": "Kyla Scanlon",
            "fund": "Kyla Scanlon",
        },
        {
            "name": "Doomberg",
            "url": "https://doomberg.substack.com/feed",
            "type": "rss",
            "author": "Doomberg",
            "fund": "Doomberg",
        },
        {
            "name": "Capital Flows",
            "url": "https://capitalflows.substack.com/feed",
            "type": "rss",
            "author": "Michael Howell",
            "fund": "Capital Flows & Asset Markets",
        },
        {
            "name": "The Last Bear Standing",
            "url": "https://thelastbearstanding.substack.com/feed",
            "type": "rss",
            "author": "TLBS",
            "fund": "The Last Bear Standing",
        },
        # ── Substack Newsletters (P1 — High Value) ──
        {
            "name": "The Bear Traps Report",
            "url": "https://www.thebeartrapsreport.com/feed",
            "type": "rss",
            "author": "Larry McDonald",
            "fund": "The Bear Traps Report",
        },
        {
            "name": "Fidenza Macro",
            "url": "https://fidenzamacro.substack.com/feed",
            "type": "rss",
            "author": "Fidenza",
            "fund": "Fidenza Macro",
        },
        {
            "name": "Concoda",
            "url": "https://concoda.substack.com/feed",
            "type": "rss",
            "author": "Concoda",
            "fund": "Concoda",
        },
        {
            "name": "Prometheus Research",
            "url": "https://prometheusresearch.substack.com/feed",
            "type": "rss",
            "author": "Prometheus",
            "fund": "Prometheus Research",
        },
        {
            "name": "Luke Gromen (FFTT)",
            "url": "https://fftt-llc.com/feed",
            "type": "rss",
            "author": "Luke Gromen",
            "fund": "FFTT LLC",
        },
        {
            "name": "Macro Alf (Market Alpha)",
            "url": "https://alfsmarketalpha.substack.com/feed",
            "type": "rss",
            "author": "Alfonso Peccatiello",
            "fund": "Macro Alf",
        },
        {
            "name": "Noahpinion",
            "url": "https://noahpinion.substack.com/feed",
            "type": "rss",
            "author": "Noah Smith",
            "fund": "Noahpinion",
        },
        {
            "name": "The Diff",
            "url": "https://thediff.co/feed",
            "type": "rss",
            "author": "Byrne Hobart",
            "fund": "The Diff",
        },
        # ── Substack Newsletters (P2 — Nice to Have) ──
        {
            "name": "Construction Physics",
            "url": "https://constructionphysics.substack.com/feed",
            "type": "rss",
            "author": "Brian Potter",
            "fund": "Construction Physics",
        },
        {
            "name": "Bankless",
            "url": "https://newsletter.banklesshq.com/feed",
            "type": "rss",
            "author": "Bankless",
            "fund": "Bankless",
        },
        {
            "name": "Pomp Letters",
            "url": "https://pomp.substack.com/feed",
            "type": "rss",
            "author": "Anthony Pompliano",
            "fund": "Pomp Letters",
        },
        {
            "name": "Macro Hive",
            "url": "https://macrohive.substack.com/feed",
            "type": "rss",
            "author": "Bilal Hafeez",
            "fund": "Macro Hive",
        },
        # ── Individual Research Providers (P0 — Must Have, scrape) ──
        {
            "name": "Jim Bianco (Bianco Research)",
            "url": "https://www.biancoresearch.com/blog/",
            "type": "scrape",
            "author": "Jim Bianco",
            "fund": "Bianco Research",
        },
        {
            "name": "David Rosenberg",
            "url": "https://www.rosenbergresearch.com/research/",
            "type": "scrape",
            "author": "David Rosenberg",
            "fund": "Rosenberg Research",
        },
        {
            "name": "Lacy Hunt (Hoisington)",
            "url": "https://hfrg.net/insights/",
            "type": "scrape",
            "author": "Lacy Hunt",
            "fund": "Hoisington Investment Management",
        },
        {
            "name": "Russell Napier",
            "url": "https://www.eri-c.com/edinburgh-reading-list/",
            "type": "scrape",
            "author": "Russell Napier",
            "fund": "ERIC",
        },
        # ── Individual Research Providers (P1 — High Value, scrape) ──
        {
            "name": "Gavekal Research",
            "url": "https://research.gavekal.com/",
            "type": "scrape",
            "author": "Gavekal",
            "fund": "Gavekal Research",
        },
        {
            "name": "Variant Perception",
            "url": "https://blog.variantperception.com/",
            "type": "scrape",
            "author": "Variant Perception",
            "fund": "Variant Perception",
        },
        {
            "name": "Yardeni Research",
            "url": "https://yardeni.com/our-research/",
            "type": "scrape",
            "author": "Ed Yardeni",
            "fund": "Yardeni Research",
        },
        # ── Individual Research Providers (P2 — Nice to Have, scrape) ──
        {
            "name": "Fidelity Insights",
            "url": "https://institutional.fidelity.com/app/literature/list/702.html",
            "type": "scrape",
            "author": "Fidelity",
            "fund": "Fidelity Investments",
        },
        # ── New — Sell-side / Macro Strategy (scrape) ──
        {
            "name": "Apollo (Torsten Slok)",
            "url": "https://www.apolloacademy.com/the-daily-spark/",
            "type": "scrape",
            "author": "Torsten Slok",
            "fund": "Apollo Global",
        },
        {
            "name": "BCA Research",
            "url": "https://www.bcaresearch.com/marketing/insights",
            "type": "scrape",
            "author": "BCA Research",
            "fund": "BCA Research",
        },
        {
            "name": "CrossBorder Capital",
            "url": "https://www.crossbordercapital.com/blog",
            "type": "scrape",
            "author": "Michael Howell",
            "fund": "CrossBorder Capital",
        },
        # ── New — Hedge Funds / Asset Managers (scrape) ──
        {
            "name": "Bridgewater Research",
            "url": "https://www.bridgewater.com/research-and-insights",
            "type": "scrape",
            "author": "Bridgewater",
            "fund": "Bridgewater Associates",
        },
        {
            "name": "D.E. Shaw",
            "url": "https://www.deshaw.com/library",
            "type": "scrape",
            "author": "D.E. Shaw",
            "fund": "D.E. Shaw",
        },
        {
            "name": "Two Sigma",
            "url": "https://www.twosigma.com/insights/",
            "type": "scrape",
            "author": "Two Sigma",
            "fund": "Two Sigma",
        },
        {
            "name": "Citadel Insights",
            "url": "https://www.citadelsecurities.com/news-and-insights/",
            "type": "scrape",
            "author": "Citadel",
            "fund": "Citadel Securities",
        },
        {
            "name": "Marathon Asset Management",
            "url": "https://www.marathonfund.com/news",
            "type": "scrape",
            "author": "Marathon",
            "fund": "Marathon Asset Management",
        },
        {
            "name": "Pantera Capital",
            "url": "https://panteracapital.com/blockchain-letter/",
            "type": "scrape",
            "author": "Pantera",
            "fund": "Pantera Capital",
        },
        # ── New — Substack Newsletters ──
        {
            "name": "Lykeion",
            "url": "https://thelykeion.substack.com/feed",
            "type": "rss",
            "author": "Lykeion",
            "fund": "Lykeion",
        },
        {
            "name": "The Overshoot",
            "url": "https://theovershoot.co/feed",
            "type": "rss",
            "author": "Matt Klein",
            "fund": "The Overshoot",
        },
        {
            "name": "Employ America",
            "url": "https://employamerica.substack.com/feed",
            "type": "rss",
            "author": "Employ America",
            "fund": "Employ America",
        },
        {
            "name": "The Macro Trading Floor",
            "url": "https://themacrotradingfloor.substack.com/feed",
            "type": "rss",
            "author": "Macro Trading Floor",
            "fund": "The Macro Trading Floor",
        },
        {
            "name": "The Transcript",
            "url": "https://www.thetranscript.substack.com/feed",
            "type": "rss",
            "author": "The Transcript",
            "fund": "The Transcript",
        },
        # ── New — Korean Research (scrape) ──
        {
            "name": "BOK Economic Review",
            "url": "https://www.bok.or.kr/eng/bbs/B0000268/list.do?menuNo=400067",
            "type": "scrape",
            "author": "Bank of Korea",
            "fund": "Bank of Korea",
        },
        {
            "name": "Mirae Asset Research",
            "url": "https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1546",
            "type": "scrape",
            "author": "Mirae Asset",
            "fund": "Mirae Asset Securities",
        },
        # ── New — Academic / Policy ──
        {
            "name": "NBER New Working Papers",
            "url": "https://www.nber.org/papers?page=1&perPage=20&sortBy=public_date",
            "type": "scrape",
            "author": "NBER",
            "fund": "National Bureau of Economic Research",
        },
        {
            "name": "Brookings BPEA",
            "url": "https://www.brookings.edu/programs/economic-studies/",
            "type": "scrape",
            "author": "Brookings",
            "fund": "Brookings Institution",
        },
        {
            "name": "PIIE",
            "url": "https://www.piie.com/research",
            "type": "scrape",
            "author": "PIIE",
            "fund": "Peterson Institute",
        },
        {
            "name": "Seeking Alpha Transcripts",
            "url": "https://seekingalpha.com/earnings/earnings-call-transcripts",
            "type": "scrape",
            "author": "Seeking Alpha",
            "fund": "Seeking Alpha Transcripts",
        },
    ]

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0
        total = len(self.SOURCES)

        for i, src in enumerate(self.SOURCES):
            if progress_cb:
                progress_cb(i + 1, total, f"Checking {src['name']}")

            try:
                # Each source gets its own session to isolate failures
                with Session() as db:
                    if src["type"] == "rss":
                        count = self._fetch_rss(db, src)
                    else:
                        count = self._fetch_scrape(db, src)
                    inserted += count
            except Exception as e:
                self.logger.error(f"Error fetching {src['name']}: {e}")
                errors += 1

            time.sleep(2)  # Be polite

        self.update_state(last_data_date=str(datetime.now().date()))
        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"Investor Letters: {inserted} new items from {total} sources",
        }

    def _fetch_rss(self, db, src: dict) -> int:
        """Fetch articles from an RSS feed."""
        count = 0
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()

                # Strip HTML from summary
                if summary:
                    summary = BeautifulSoup(summary, "html.parser").get_text()[:500]

                published = None
                if entry.get("published_parsed"):
                    published = datetime(*entry.published_parsed[:6])

                if not title or not url:
                    continue

                body_text = fetch_full_text(url)
                if body_text:
                    time.sleep(1)  # Rate limit Firecrawl calls

                was_new = self._upsert_news_item(
                    db,
                    source="investor_letter",
                    source_name=src["name"],
                    title=title,
                    url=url,
                    body_text=body_text,
                    summary=summary,
                    meta={
                        "author": src.get("author"),
                        "fund": src.get("fund"),
                        "letter_type": "article",
                    },
                    published_at=published,
                )
                if was_new:
                    count += 1
        except Exception as e:
            self.logger.warning(f"RSS fetch failed for {src['name']}: {e}")

        return count

    def _fetch_scrape(self, db, src: dict) -> int:
        """Scrape a publications listing page for new entries."""
        count = 0
        try:
            resp = requests.get(src["url"], timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Investment-X Research)"
            })
            if resp.status_code != 200:
                self.logger.warning(f"HTTP {resp.status_code} from {src['url']}")
                return 0

            soup = BeautifulSoup(resp.text, "html.parser")
            articles = self._extract_articles(soup, src)

            for article in articles[:15]:
                article_url = article.get("url")
                body_text = fetch_full_text(article_url) if article_url else None
                if body_text:
                    time.sleep(1)  # Rate limit Firecrawl calls

                was_new = self._upsert_news_item(
                    db,
                    source="investor_letter",
                    source_name=src["name"],
                    title=article["title"],
                    url=article_url,
                    body_text=body_text,
                    summary=article.get("summary"),
                    meta={
                        "author": src.get("author"),
                        "fund": src.get("fund"),
                        "letter_type": article.get("type", "memo"),
                    },
                    published_at=article.get("date"),
                )
                if was_new:
                    count += 1
        except Exception as e:
            self.logger.warning(f"Scrape failed for {src['name']}: {e}")

        return count

    def _extract_articles(self, soup: BeautifulSoup, src: dict) -> list:
        """Generic article extraction from a listing page."""
        articles = []
        base_url = src["url"].rsplit("/", 1)[0]

        # Look for common patterns: article cards, list items with links
        for selector in ["article", ".post", ".entry", ".insight", ".memo", ".publication",
                         "li a[href]", ".card", ".list-item"]:
            elements = soup.select(selector)
            if elements and len(elements) >= 2:
                for el in elements[:20]:
                    title_el = el.find(["h2", "h3", "h4", "a"])
                    if not title_el:
                        continue

                    title = title_el.get_text().strip()
                    if not title or len(title) < 5:
                        continue

                    # Get URL
                    link = el.find("a") if el.name != "a" else el
                    url = None
                    if link and link.get("href"):
                        href = link["href"]
                        if href.startswith("http"):
                            url = href
                        elif href.startswith("/"):
                            from urllib.parse import urlparse
                            parsed = urlparse(src["url"])
                            url = f"{parsed.scheme}://{parsed.netloc}{href}"

                    # Get summary/description
                    summary = None
                    desc_el = el.find(["p", ".description", ".excerpt", ".summary"])
                    if desc_el:
                        summary = desc_el.get_text().strip()[:500]

                    # Get date
                    date = None
                    date_el = el.find(["time", ".date", ".published"])
                    if date_el:
                        date_text = date_el.get("datetime") or date_el.get_text().strip()
                        try:
                            date = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            pass

                    articles.append({
                        "title": title,
                        "url": url,
                        "summary": summary,
                        "date": date,
                        "type": "memo",
                    })

                if articles:
                    break

        return articles
