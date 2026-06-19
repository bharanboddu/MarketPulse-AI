# 🚀 Deploying MarketPulse AI to Render

This guide walks you through deploying MarketPulse AI to **Render** (free tier).

---

## Prerequisites

1. A **GitHub** account — [github.com](https://github.com)
2. A **Render** account — [render.com](https://render.com) (sign up free with GitHub)
3. **Git** installed on your machine — [git-scm.com](https://git-scm.com)

---

## Step 1: Push Your Code to GitHub

### 1.1 Create a GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Name it `marketpulse-ai` (or anything you like)
3. Set it to **Private** (recommended, since you have API keys)
4. Do **NOT** add a README or .gitignore (we already have them)
5. Click **Create repository**

### 1.2 Initialize Git and Push

Open a terminal in your project folder and run:

```bash
cd C:\Users\bhara\.gemini\antigravity\scratch\marketpulse-ai

git init
git add .
git commit -m "Initial commit - MarketPulse AI"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/marketpulse-ai.git
git push -u origin main
```

> ⚠️ Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 2: Deploy on Render

### Option A: One-Click Blueprint Deploy (Recommended)

1. Go to [render.com/dashboard](https://dashboard.render.com)
2. Click **New** → **Blueprint**
3. Connect your GitHub account if not already connected
4. Select your `marketpulse-ai` repository
5. Render will detect the `render.yaml` and auto-configure everything
6. You'll be prompted to enter values for:
   - `GEMINI_API_KEY` — Your Google Gemini API key (optional but recommended)
   - `OPENAI_API_KEY` — OpenAI key (optional)
   - `NEWS_API_KEY` — NewsAPI key (optional)
7. Click **Apply** to start the deployment

### Option B: Manual Web Service

1. Go to [render.com/dashboard](https://dashboard.render.com)
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `marketpulse-ai`
   - **Region**: Oregon (US West)
   - **Branch**: `main`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Plan**: Free
5. Add environment variables:
   | Key | Value |
   |---|---|
   | `FLASK_SECRET_KEY` | Click "Generate" or type a random string |
   | `FLASK_ENV` | `production` |
   | `GEMINI_API_KEY` | Your key (optional) |
   | `OPENAI_API_KEY` | Your key (optional) |
   | `NEWS_API_KEY` | Your key (optional) |
   | `PYTHON_VERSION` | `3.11.9` |
6. Click **Create Web Service**

---

## Step 3: Wait for Build

- Render will install dependencies and start Gunicorn
- Build usually takes **2-5 minutes**
- Once deployed, you'll see a URL like:
  ```
  https://marketpulse-ai.onrender.com
  ```

---

## Step 4: Verify

1. Open your Render URL in a browser
2. Check that the dashboard loads with live market data
3. Test the watchlist, alerts, and trade recommendations

---

## Important Notes

### 📦 SQLite on Render
Render's free tier uses **ephemeral storage** — your SQLite database will reset on each deploy/restart. This is fine for a demo or personal use. For persistent data, upgrade to a **Render PostgreSQL** database:

1. Go to Render Dashboard → **New** → **PostgreSQL**
2. Create a free PostgreSQL instance
3. Copy the **Internal Database URL**
4. Add it as the `DATABASE_URL` environment variable in your web service

The app already supports PostgreSQL via the `DATABASE_URL` env var — no code changes needed!

### 🔑 API Keys
- The app works without API keys (uses simulated AI responses and RSS feeds)
- For full AI features, add your `GEMINI_API_KEY`
- Get a free Gemini key at [aistudio.google.com](https://aistudio.google.com)

### 🕐 Cold Starts
- Render's free tier **sleeps after 15 minutes of inactivity**
- First request after sleep takes ~30 seconds to wake up
- This is normal for the free tier

### 🔄 Auto-Deploy
- Render auto-deploys when you push to the `main` branch
- To disable, go to Service Settings → Auto-Deploy → Off

---

## Troubleshooting

| Issue | Solution |
|---|---|
| Build fails | Check Render build logs for missing dependencies |
| App crashes on start | Ensure `wsgi.py` exists and `gunicorn` is in requirements.txt |
| Database errors | SQLite resets on redeploy; use PostgreSQL for persistence |
| Slow first load | Normal on free tier (cold start), wait ~30s |
| yfinance rate limited | The app handles this gracefully with fallback data |

---

## Updating Your App

After making local changes:

```bash
git add .
git commit -m "Your change description"
git push origin main
```

Render will automatically rebuild and redeploy! 🎉
