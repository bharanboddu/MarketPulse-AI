import google.generativeai as genai
import openai
from flask import current_app
import random

def get_ai_summarizer(articles: list, symbol: str) -> str:
    """Generates a cohesive executive briefing from multiple news articles using LLMs (Gemini/OpenAI) or local fallback."""
    if not articles:
        return "No articles available to summarize."
        
    # Format articles for the prompt
    bulletins = []
    for idx, art in enumerate(articles):
        bulletins.append(f"Article [{idx+1}]: {art['title']} (Source: {art['source']})\nContent: {art['summary']}")
    
    combined_articles = "\n\n".join(bulletins)
    prompt = (
        f"You are a Senior Financial Analyst. Review the following news articles about {symbol} and construct "
        f"a concise, professional executive briefing (2-3 short bullet points). "
        f"Focus on the market sentiment, key catalysts, and what this means for investors. "
        f"Do not invent any facts outside the provided articles.\n\n"
        f"Articles:\n{combined_articles}\n\n"
        f"Executive Briefing (as markdown bullet points):"
    )
    
    # 1. Attempt Gemini
    gemini_key = current_app.config.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            # Use 'gemini-1.5-flash' as it is standard, fast, and highly capable
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API Error: {e}")
            
    # 2. Attempt OpenAI
    openai_key = current_app.config.get("OPENAI_API_KEY")
    if openai_key:
        try:
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional financial intelligence bot."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.5
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            
    # 3. Local Rule-based template fallback (Offline Mode)
    return get_simulated_ai_summary(articles, symbol)

def generate_chat_response(message: str, symbol: str, price_history: dict = None) -> str:
    """Handles chatbot conversations and answers questions about an asset."""
    price_info = ""
    if price_history and "close" in price_history and price_history["close"]:
        last_price = price_history["close"][-1]
        price_info = f" The last known trading price for {symbol} is ${last_price:.2f}."
        
    prompt = (
        f"You are a helpful MarketPulse AI assistant. The user is asking about {symbol}.{price_info} "
        f"Answer their question in a professional, objective financial analyst tone. Keep it concise (under 150 words). "
        f"If you do not know the answer, recommend them to verify via official filings.\n\n"
        f"User Message: {message}\n\n"
        f"Assistant Response:"
    )
    
    # 1. Attempt Gemini
    gemini_key = current_app.config.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API Error: {e}")
            
    # 2. Attempt OpenAI
    openai_key = current_app.config.get("OPENAI_API_KEY")
    if openai_key:
        try:
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional market intelligence agent."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            
    # 3. Fallback simulated chatbot responses
    return get_simulated_chat_response(message, symbol)

def get_simulated_ai_summary(articles: list, symbol: str) -> str:
    """Generates structured summaries when no API key is provided."""
    bullets = []
    
    # Analyze sentiment
    titles = [a["title"] for a in articles]
    has_positive = any(w in " ".join(titles).lower() for w in ["surge", "gain", "rally", "buy", "upbeat"])
    has_negative = any(w in " ".join(titles).lower() for w in ["plunge", "drop", "concern", "sell", "decline"])
    
    if has_positive:
        bullets.append(f"**Bullish Catalyst**: Broad consensus suggests that institutional buy-ins and news flow regarding partnership expansion are stabilizing {symbol}'s support boundaries.")
    if has_negative:
        bullets.append(f"**Bearish Risk Factors**: Regulatory compliance reviews and global macroeconomic headwinds continue to pose minor technical risks for {symbol}.")
    if not bullets:
        bullets.append(f"**Consolidation phase**: {symbol} shows balanced news sentiment. Technical metrics point to a sideways accumulation range with volume testing immediate moving averages.")
        
    bullets.append(f"**Key Focus**: Investors are monitoring upcoming interest rate revisions and direct sector volume inflows to gauge the sustainability of {symbol}'s current trading price.")
    
    return "\n".join([f"- {b}" for b in bullets])

def get_simulated_chat_response(message: str, symbol: str) -> str:
    """Generates smart template answers for the chatbot."""
    msg = message.lower()
    
    responses = [
        "Based on technical signals, {symbol} is currently accumulating with balanced RSI and volume indicators. Support levels are firm.",
        "News sentiment for {symbol} is currently neutral-to-positive. The main catalysts to look out for are regulatory announcements and next week's macro reports.",
        "If you are looking to hedge, analysts suggest watching the correlations shown in the Market Impact Network tab to see how {symbol} responds to macro index movements."
    ]
    
    if "buy" in msg or "invest" in msg or "should i" in msg:
        return f"Regarding investing in {symbol}, market trends show steady accumulation, but it remains sensitive to macro sentiment. It's recommended to set support price alerts in the Overview tab to manage entry points."
    elif "price" in msg or "chart" in msg or "value" in msg:
        return f"The {symbol} price chart shows recent short-term consolidation. You can view the full predictive boundary bounds under the Prediction Engine tab to see our machine learning model's forecasted direction."
    elif "risk" in msg or "danger" in msg or "bearish" in msg:
        return f"Primary risks for {symbol} include regulatory scrutiny and sudden macro liquidity drains. Diversifying and monitoring institutional holdings (see the Investor Analysis tab) is advised."
        
    return random.choice(responses).format(symbol=symbol)

def get_societal_brief(symbol: str, name: str, business_summary: str) -> str:
    """Generates a professional brief on what the asset is, what it does, and how it affects society."""
    prompt = (
        f"You are a Senior ESG and Financial Analyst. Write a concise, professional paragraph (3-4 sentences, max 100 words) "
        f"summarizing what {name} ({symbol}) does, and its broader impact on society (both positive technological/financial "
        f"contributions and potential environmental or social concerns).\n\n"
        f"Business Description:\n{business_summary}\n\n"
        f"Societal Impact Brief:"
    )
    
    # 1. Attempt Gemini
    gemini_key = current_app.config.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API Error: {e}")
            
    # 2. Attempt OpenAI
    openai_key = current_app.config.get("OPENAI_API_KEY")
    if openai_key:
        try:
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional ESG intelligence agent."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.6
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            
    # 3. Local Rule-based fallback
    return get_simulated_societal_brief(symbol, name, business_summary)

def get_simulated_societal_brief(symbol: str, name: str, business_summary: str) -> str:
    symbol = symbol.upper().strip()
    
    precomputed = {
        "AAPL": (
            "Apple Inc. designs and manufactures consumer electronics, software, and services. Apple has revolutionized "
            "global communication, productivity, and mobile computing. Society benefits from its focus on user privacy, "
            "accessibility, and carbon-neutral corporate goals, though it faces scrutiny regarding supply chain labor "
            "conditions and mineral sourcing for hardware."
        ),
        "TSLA": (
            "Tesla Inc. designs and manufactures electric vehicles, battery energy storage systems, and solar panels. Tesla "
            "accelerates the global transition to sustainable energy, directly reducing carbon emissions from transport. "
            "However, its societal footprint includes debates over battery raw material mining (lithium/cobalt), "
            "autopilot safety concerns, and labor relations."
        ),
        "NVDA": (
            "NVIDIA Corporation designs graphics processing units (GPUs) and AI computing systems. NVIDIA is the primary "
            "catalyst for the global Artificial Intelligence revolution, powering scientific discoveries, medical diagnostics, "
            "and advanced automation. Societal challenges include the massive energy consumption of GPU data centers and "
            "ethical concerns over deepfakes and autonomous military tech."
        ),
        "MSFT": (
            "Microsoft Corporation develops software, cloud services, and hardware. Microsoft democratizes computing "
            "globally, enhancing productivity and educational access. It leads corporate investments in generative AI (OpenAI) "
            "and aims to be carbon negative, while facing ongoing concerns regarding cybersecurity vulnerabilities "
            "and digital monopolization."
        ),
        "BTC-USD": (
            "Bitcoin is a decentralized peer-to-peer cryptocurrency operating on a proof-of-work blockchain. It offers "
            "financial inclusion to unbanked global populations and provides a hedge against inflation. However, its high "
            "mining energy consumption poses environmental challenges, and its anonymity has occasionally facilitated "
            "undocumented transactions."
        )
    }
    
    if symbol in precomputed:
        return precomputed[symbol]
        
    # Generic template fallback
    return (
        f"{name} operates in the financial and technology markets. It contributes to economic productivity, job creation, "
        f"and industrial innovation. Its societal footprint is driven by standard corporate governance, consumer safety compliance, "
        f"and its contribution to industry-wide technological standards."
    )
