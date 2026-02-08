
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from ix.misc.terminal import get_logger

logger = get_logger(__name__)

def get_gurufocus_news(limit: int = 20) -> pd.DataFrame:
    """
    Scrapes the latest news from GuruFocus.
    
    Args:
        limit (int): Maximum number of articles to retrieve.
        
    Returns:
        pd.DataFrame: DataFrame containing news articles with columns:
                      ['title', 'url', 'description', 'author', 'time', 'source']
    """
    url = "https://www.gurufocus.com/news"
    # Use a browser-like User-Agent to avoid 403 Forbidden
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        logger.info(f"Fetching news from {url}...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []
        
        # Select all article items
        # The class 'article-item' was observed in inspection
        items = soup.select("div.article-item")
        
        for item in items:
            try:
                # Title and Link
                # Found structure: <a class="link" ...> <div class="title-section">...</div> </a>
                link_tag = item.select_one("a.link")
                if not link_tag:
                    continue
                    
                href = link_tag.get('href')
                full_url = f"https://www.gurufocus.com{href}" if href.startswith("/") else href
                
                title_div = link_tag.select_one("div.title-section")
                title = title_div.get_text(strip=True) if title_div else link_tag.get_text(strip=True)
                
                # Description/Subtitle
                subtitle_tag = item.select_one("span.subtitle")
                description = subtitle_tag.get_text(strip=True) if subtitle_tag else ""
                
                # Author
                # Structure: <a href="/user/..." ...> <span>Name</span> </a>
                # Usually inside a col-17 div or similar
                author_tag = item.select_one("a[href^='/user/'] span")
                author = author_tag.get_text(strip=True) if author_tag else "GuruFocus"
                
                # Time/Date
                # Structure seen: <div class="date ..."> ... <span ...> Jan 29, 2026 </span> ... </div>
                # The date is usually the last span in the date div or text node
                # Let's try to grab text from 'div.date' and clean it
                time_str = ""
                date_div = item.select_one("div.date")
                if date_div:
                    # Remove "Stocks:" and other known labels if present
                    # This is a bit heuristic
                    # Searching for text that looks like a date/time
                    # or getting the text of the entire div
                    date_text = date_div.get_text(" ", strip=True)
                    # Simple heuristic: store the raw text for now, or cleaner if possible
                    # Often the date is just there e.g. "Jan 29, 2026 • 2 min read"
                    time_str = date_text
                
                articles.append({
                    "title": title,
                    "url": full_url,
                    "description": description,
                    "author": author,
                    "time": time_str,
                    "source": "GuruFocus"
                })
                
                if len(articles) >= limit:
                    break
                    
            except Exception as e:
                logger.warning(f"Error parsing article item: {e}")
                continue
        
        logger.info(f"Successfully scraped {len(articles)} articles.")
        return pd.DataFrame(articles)
        
    except Exception as e:
        logger.error(f"Failed to scrape GuruFocus news: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Test execution
    df = get_gurufocus_news()
    print(df.head())
    print("\nColumns:", df.columns)
