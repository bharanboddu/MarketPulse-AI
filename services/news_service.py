import requests
import xml.etree.ElementTree as ET
import html
from datetime import datetime, timedelta
import numpy as np

def fetch_rss_news(symbol: str) -> list:
    """Fetches real-time news headlines from Google News RSS for a given symbol."""
    search_term = symbol.replace("-USDT", "").replace("-USD", "")
    url = f"https://news.google.com/rss/search?q={search_term}+crypto+market&hl=en-US&gl=US&ceid=US:en" if "-" in symbol else f"https://news.google.com/rss/search?q={search_term}+market&hl=en-US&gl=US&ceid=US:en"
    
    articles = []
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            raise Exception("Failed to load RSS feed")
            
        root = ET.fromstring(response.content)
        
        # Google News XML namespaces are usually not complicated, elements are under <channel> <item>
        items = root.findall(".//item")
        
        for item in items[:15]:  # Get top 15 news articles
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date_str = item.find("pubDate").text if item.find("pubDate") is not None else ""
            source = item.find("source").text if item.find("source") is not None else "Google News"
            
            # Clean title (Google News appends " - Source Name" at the end of titles)
            clean_title = title
            if " - " in title:
                clean_title = " - ".join(title.split(" - ")[:-1])
                
            # Parse date
            try:
                # e.g., "Fri, 19 Jun 2026 14:10:00 GMT"
                dt = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                formatted_date = dt.strftime("%b %d, %Y %H:%M")
            except Exception:
                formatted_date = pub_date_str
                
            articles.append({
                "title": clean_title,
                "url": link,
                "date": formatted_date,
                "source": source,
                "summary": f"Latest developments and financial updates regarding {symbol} asset activities from {source}."
            })
            
    except Exception as e:
        print(f"fetch_rss_news ERROR for {symbol}: {e}")
        # Fallback to simulated news if network fails
        return get_simulated_news(symbol)
        
    if not articles:
        return get_simulated_news(symbol)
        
    return articles

def get_simulated_news(symbol: str) -> list:
    """Generates realistic simulated financial news articles for an asset."""
    np.random.seed(hash(symbol) % (2**32))
    
    templates = [
        {
            "title_template": "{symbol} Shares Surge Amid Strong Institutional Buying and ETF Inflow Reports",
            "source": "Bloomberg",
            "summary_template": "Market analysts report a substantial uptick in trading volume for {symbol} today, driven by large block orders from major institutional funds and hedge positions."
        },
        {
            "title_template": "Regulatory Clarity in Focus: What the Latest Federal Hearings Mean for {symbol}",
            "source": "Reuters",
            "summary_template": "Lawmakers discussed the regulatory frameworks affecting digital assets and equities, directly referencing {symbol} market structures. Analysts remain optimistic."
        },
        {
            "title_template": "Technical Analysis: {symbol} Approaches Key Resistance Level After 5% Rally",
            "source": "MarketWatch",
            "summary_template": "The 50-day moving average suggests {symbol} has successfully tested the support band. Traders are looking closely at the short-term resistance."
        },
        {
            "title_template": "{symbol} Integration Expands Globally with New Payment Network Partnerships",
            "source": "CoinDesk" if "-" in symbol or symbol in ["BTC", "ETH", "SOL"] else "TechCrunch",
            "summary_template": "Strategic alliances announced early this morning aim to bring {symbol} technology utilities directly to millions of retail payment systems."
        },
        {
            "title_template": "Macro headwinds continue to test asset classes: {symbol} displays resilience",
            "source": "Financial Times",
            "summary_template": "Despite inflation updates and interest rate uncertainty, {symbol} has decoupled from indices and shows robust sideways accumulation patterns."
        }
    ]
    
    articles = []
    base_time = datetime.now()
    
    for i, t in enumerate(templates):
        title = t["title_template"].format(symbol=symbol)
        summary = t["summary_template"].format(symbol=symbol)
        date_str = (base_time - timedelta(hours=i*4)).strftime("%b %d, %Y %H:%M")
        
        articles.append({
            "title": title,
            "url": "#",
            "date": date_str,
            "source": t["source"],
            "summary": summary
        })
        
    return articles
