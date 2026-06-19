# MarketPulse AI

A premium financial intelligence dashboard built with Flask, featuring:

- 📊 **Live Market Data** — Real-time stock & crypto prices via yfinance
- 🤖 **AI Predictions** — ML-powered trade signals (XGBoost + scikit-learn)
- 📰 **News Feed** — Sentiment-analyzed financial news
- 🔔 **Smart Alerts** — Price alerts with email notifications
- 💬 **AI Chat Assistant** — Ask questions about any ticker
- 📈 **Portfolio Analyzer** — Track and analyze your holdings
- 📧 **Email Alerts Hub** — Monitor all email notification activity

## Quick Start (Local Development)

```bash
# Clone the repo
git clone <your-repo-url>
cd marketpulse-ai

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.template .env
# Edit .env with your API keys

# Run the app
python run.py
```

Visit `http://localhost:5000`

## Deploy to Render (Free Tier)

See [DEPLOY.md](DEPLOY.md) for step-by-step deployment instructions.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | ✅ | Session encryption key |
| `GEMINI_API_KEY` | Optional | Google Gemini for AI summaries |
| `OPENAI_API_KEY` | Optional | OpenAI fallback for AI features |
| `NEWS_API_KEY` | Optional | NewsAPI key (RSS used as default) |

## Tech Stack

- **Backend**: Flask + SQLAlchemy
- **Frontend**: HTML/CSS/JS + Plotly.js
- **ML**: scikit-learn + XGBoost
- **Data**: yfinance + Google News RSS
- **Production**: Gunicorn

## License

MIT
