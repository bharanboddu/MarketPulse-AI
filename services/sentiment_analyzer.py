from textblob import TextBlob
import numpy as np

def calculate_sentiment(text: str) -> float:
    """Calculates a sentiment polarity score between -1 (negative) and 1 (positive) using TextBlob."""
    if not text:
        return 0.0
    try:
        blob = TextBlob(text)
        return float(blob.sentiment.polarity)
    except Exception:
        # Simple rule-based fallback if TextBlob has issues
        text_lower = text.lower()
        pos_words = ["surge", "rally", "gain", "growth", "high", "positive", "bullish", "profit", "buy", "upbeat", "expand"]
        neg_words = ["drop", "fall", "loss", "plunge", "negative", "bearish", "sell", "concern", "decline", "warn", "slump"]
        
        pos_count = sum(1 for w in pos_words if w in text_lower)
        neg_count = sum(1 for w in neg_words if w in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        return float((pos_count - neg_count) / total)

def analyze_articles_sentiment(articles: list) -> list:
    """Attaches sentiment scores, labels, and classes to a list of articles."""
    scored_articles = []
    for art in articles:
        # Score title + summary
        text_to_score = f"{art['title']}. {art['summary']}"
        score = calculate_sentiment(text_to_score)
        
        # Categorize
        if score > 0.05:
            label = "Positive"
            css_class = "sentiment-pos"
        elif score < -0.05:
            label = "Negative"
            css_class = "sentiment-neg"
        else:
            label = "Neutral"
            css_class = "sentiment-neu"
            
        scored_articles.append({
            **art,
            "sentiment_score": score,
            "sentiment_label": label,
            "sentiment_class": css_class
        })
    return scored_articles

def aggregate_sentiment_metrics(scored_articles: list) -> dict:
    """Aggregates article list sentiments into stats."""
    if not scored_articles:
        return {"average": 0.0, "label": "Neutral", "positive_count": 0, "neutral_count": 0, "negative_count": 0}
        
    scores = [art["sentiment_score"] for art in scored_articles]
    avg_score = float(np.mean(scores))
    
    pos_count = sum(1 for art in scored_articles if art["sentiment_label"] == "Positive")
    neu_count = sum(1 for art in scored_articles if art["sentiment_label"] == "Neutral")
    neg_count = sum(1 for art in scored_articles if art["sentiment_label"] == "Negative")
    
    if avg_score > 0.05:
        avg_label = "Positive"
    elif avg_score < -0.05:
        avg_label = "Negative"
    else:
        avg_label = "Neutral"
        
    return {
        "average": round(avg_score, 2),
        "label": avg_label,
        "positive_count": pos_count,
        "neutral_count": neu_count,
        "negative_count": neg_count,
        "total": len(scored_articles)
    }
