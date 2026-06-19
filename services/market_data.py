import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# Global in-memory cache for profiles and history
MARKET_DATA_CACHE = {}
HISTORY_CACHE = {}
CACHE_EXPIRY = 300 # 5 minutes cache expiry

def get_clean_ticker(symbol: str) -> str:
    """Standardizes asset symbols (e.g. BTC to BTC-USD, AAPL to AAPL)."""
    symbol = symbol.strip().upper()
    crypto_mapping = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD",
        "ADA": "ADA-USD",
        "DOT": "DOT-USD",
        "XRP": "XRP-USD",
        "DOGE": "DOGE-USD"
    }
    return crypto_mapping.get(symbol, symbol)

def get_asset_logo_url(symbol: str) -> str:
    """Returns a high-quality brand logo URL for US stocks or major cryptos, with fallbacks."""
    symbol = symbol.upper().strip()
    mappings = {
        "AAPL": "https://logo.clearbit.com/apple.com",
        "TSLA": "https://logo.clearbit.com/tesla.com",
        "MSFT": "https://logo.clearbit.com/microsoft.com",
        "NVDA": "https://logo.clearbit.com/nvidia.com",
        "GOOGL": "https://logo.clearbit.com/google.com",
        "GOOG": "https://logo.clearbit.com/google.com",
        "AMZN": "https://logo.clearbit.com/amazon.com",
        "META": "https://logo.clearbit.com/meta.com",
        "NFLX": "https://logo.clearbit.com/netflix.com",
        "AMD": "https://logo.clearbit.com/amd.com",
        "INTC": "https://logo.clearbit.com/intel.com",
        "PYPL": "https://logo.clearbit.com/paypal.com",
        "COIN": "https://logo.clearbit.com/coinbase.com",
        "BTC-USD": "https://assets.coingecko.com/coins/images/1/small/bitcoin.png",
        "ETH-USD": "https://assets.coingecko.com/coins/images/279/small/ethereum.png",
        "SOL-USD": "https://assets.coingecko.com/coins/images/4128/small/solana.png",
        "ADA-USD": "https://assets.coingecko.com/coins/images/975/small/cardano.png",
        "DOT-USD": "https://assets.coingecko.com/coins/images/12171/small/polkadot.png",
        "XRP-USD": "https://assets.coingecko.com/coins/images/44/small/ripple.png",
        "DOGE-USD": "https://assets.coingecko.com/coins/images/325/small/dogecoin.png"
    }
    
    if symbol in mappings:
        return mappings[symbol]
        
    if "-" in symbol:
        base = symbol.split("-")[0]
        crypto_logos = {
            "BTC": "https://assets.coingecko.com/coins/images/1/small/bitcoin.png",
            "ETH": "https://assets.coingecko.com/coins/images/279/small/ethereum.png",
            "SOL": "https://assets.coingecko.com/coins/images/4128/small/solana.png",
            "ADA": "https://assets.coingecko.com/coins/images/975/small/cardano.png",
            "DOT": "https://assets.coingecko.com/coins/images/12171/small/polkadot.png",
            "XRP": "https://assets.coingecko.com/coins/images/44/small/ripple.png",
            "DOGE": "https://assets.coingecko.com/coins/images/325/small/dogecoin.png"
        }
        if base in crypto_logos:
            return crypto_logos[base]
            
    # Try guessing domain from ticker symbol
    clean_sym = symbol.lower()
    return f"https://logo.clearbit.com/{clean_sym}.com"

def fetch_asset_info(symbol: str) -> dict:
    """Fetches key profile statistics and metadata from Yahoo Finance (cached)."""
    ticker_symbol = get_clean_ticker(symbol)
    now = time.time()
    
    # Check cache
    if ticker_symbol in MARKET_DATA_CACHE:
        entry = MARKET_DATA_CACHE[ticker_symbol]
        if now - entry["timestamp"] < CACHE_EXPIRY:
            return entry["data"]
            
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # Determine asset class
        is_crypto = "-" in ticker_symbol or "USD" in ticker_symbol
        asset_class = "crypto" if is_crypto else "stock"
        
        # Extract fields with safe defaults
        name = info.get("longName") or info.get("shortName") or ticker_symbol
        market_cap = info.get("marketCap") or info.get("volume", 1) * info.get("regularMarketPrice", 1) if is_crypto else info.get("marketCap")
        pe_ratio = info.get("trailingPE") or None
        
        data = {
            "symbol": ticker_symbol,
            "name": name,
            "price": info.get("regularMarketPrice") or info.get("currentPrice") or info.get("navPrice") or 0.0,
            "change": info.get("regularMarketChangePercent") or 0.0,
            "volume": info.get("regularMarketVolume") or info.get("volume24Hr") or info.get("volume") or 0,
            "market_cap": market_cap or 0,
            "pe_ratio": pe_ratio,
            "high_52week": info.get("fiftyTwoWeekHigh") or 0.0,
            "low_52week": info.get("fiftyTwoWeekLow") or 0.0,
            "summary": info.get("longBusinessSummary") or f"No summary available for {name}.",
            "asset_class": asset_class,
            "status": "success"
        }
    except Exception as e:
        data = get_simulated_asset_info(ticker_symbol)
        
    # Append logo_url and societal_brief for all results (both real and simulated!)
    from .ai_service import get_societal_brief
    data["logo_url"] = get_asset_logo_url(ticker_symbol)
    data["societal_brief"] = get_societal_brief(ticker_symbol, data["name"], data["summary"])
    
    MARKET_DATA_CACHE[ticker_symbol] = {"timestamp": now, "data": data}
    return data

def fetch_historical_prices(symbol: str, period: str = "3mo", interval: str = "1d") -> dict:
    """Fetches historical price data for charts (cached)."""
    ticker_symbol = get_clean_ticker(symbol)
    cache_key = f"{ticker_symbol}_{period}_{interval}"
    now = time.time()
    
    # Check cache
    if cache_key in HISTORY_CACHE:
        entry = HISTORY_CACHE[cache_key]
        if now - entry["timestamp"] < CACHE_EXPIRY:
            return entry["data"]
            
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            raise ValueError("No historical data found.")
            
        df = df.reset_index()
        # Rename Datetime column if present (occurs with intraday data)
        if "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "Date"})
            
        # Convert Datetime objects to formatted string
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d %H:%M")
        
        data = {
            "dates": df["Date"].tolist(),
            "open": df["Open"].tolist(),
            "high": df["High"].tolist(),
            "low": df["Low"].tolist(),
            "close": df["Close"].tolist(),
            "volume": df["Volume"].tolist(),
            "status": "success"
        }
    except Exception as e:
        data = get_simulated_historical_prices(ticker_symbol, period)
        
    HISTORY_CACHE[cache_key] = {"timestamp": now, "data": data}
    return data

def get_simulated_asset_info(symbol: str) -> dict:
    """Generates a high-quality mock data dict when offline or ticker fails."""
    is_crypto = "-" in symbol or "USD" in symbol or symbol in ["BTC", "ETH", "SOL"]
    name = f"{symbol} Asset Corp" if not is_crypto else f"{symbol} Protocol"
    
    np.random.seed(hash(symbol) % (2**32))
    base_price = np.random.uniform(10, 500) if not is_crypto else np.random.uniform(0.5, 60000)
    
    return {
        "symbol": symbol,
        "name": name,
        "price": round(base_price, 2),
        "change": round(np.random.uniform(-5.0, 5.0), 2),
        "volume": int(np.random.uniform(500000, 50000000)),
        "market_cap": int(np.random.uniform(1000000000, 500000000000)),
        "pe_ratio": round(np.random.uniform(10.0, 45.0), 1) if not is_crypto else None,
        "high_52week": round(base_price * 1.25, 2),
        "low_52week": round(base_price * 0.75, 2),
        "summary": f"This is a simulated asset profile for {symbol}. In a production environment with valid ticker configurations, this would represent the real-time aggregated profile details for {name}.",
        "asset_class": "crypto" if is_crypto else "stock",
        "status": "simulated"
    }

def get_simulated_historical_prices(symbol: str, period: str = "1mo") -> dict:
    """Generates synthetic historical pricing for charts."""
    np.random.seed(hash(symbol) % (2**32))
    days_map = {"1wk": 7, "1mo": 30, "3mo": 90, "1y": 365}
    days = days_map.get(period, 30)
    
    is_crypto = "-" in symbol or "USD" in symbol
    base_price = np.random.uniform(10, 500) if not is_crypto else np.random.uniform(10, 60000)
    
    dates = []
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []
    volumes = []
    
    current_price = base_price
    start_date = datetime.now() - timedelta(days=days)
    
    for i in range(days):
        date_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        dates.append(date_str)
        
        daily_return = np.random.normal(0.0005, 0.02)
        open_price = current_price
        close_price = current_price * (1 + daily_return)
        
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0.005, 0.008)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0.005, 0.008)))
        
        open_prices.append(round(open_price, 2))
        close_prices.append(round(close_price, 2))
        high_prices.append(round(high_price, 2))
        low_prices.append(round(low_price, 2))
        volumes.append(int(np.random.uniform(100000, 10000000)))
        
        current_price = close_price
        
    return {
        "dates": dates,
        "open": open_prices,
        "high": high_prices,
        "low": low_prices,
        "close": close_prices,
        "volume": volumes,
        "status": "simulated"
    }
