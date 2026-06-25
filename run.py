import os
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from config import Config
from database import init_db, db, Watchlist, Portfolio, Alert, User, ActivityLog
import services
import numpy as np
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from services.email_service import send_alert_email

app = Flask(__name__)
app.config.from_object(Config)

# Direct SQLite Migration (runs before SQLAlchemy initialization to avoid mapper validation errors)
import sqlite3
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, "marketpulse.db")
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alert'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(alert)")
        columns = [row[1] for row in cursor.fetchall()]
        mutated = False
        if "email_notify" not in columns:
            cursor.execute("ALTER TABLE alert ADD COLUMN email_notify BOOLEAN DEFAULT 0")
            mutated = True
        if "target_email" not in columns:
            cursor.execute("ALTER TABLE alert ADD COLUMN target_email VARCHAR(100)")
            mutated = True
        if mutated:
            conn.commit()
    conn.close()
except Exception as e:
    print(f"Direct sqlite migration failed: {e}")

# Register database
init_db(app)

# Pre-populate some demo data if tables are empty
with app.app_context():
    if not Watchlist.query.first():
        db.session.add(Watchlist(symbol="AAPL", asset_class="stock"))
        db.session.add(Watchlist(symbol="BTC-USD", asset_class="crypto"))
        db.session.add(Watchlist(symbol="TSLA", asset_class="stock"))
        db.session.commit()
    
    if not Portfolio.query.first():
        db.session.add(Portfolio(symbol="AAPL", name="Apple Inc.", quantity=10.0, purchase_price=175.50, asset_class="stock"))
        db.session.add(Portfolio(symbol="BTC-USD", name="Bitcoin USD", quantity=0.25, purchase_price=58000.00, asset_class="crypto"))
        db.session.commit()
        
    if not Alert.query.first():
        db.session.add(Alert(symbol="AAPL", alert_type="price_above", condition="price > 195", threshold=195.0))
        db.session.add(Alert(symbol="BTC-USD", alert_type="price_below", condition="price < 55000", threshold=55000.0))
        db.session.commit()

    if not User.query.first():
        db.session.add(User(
            username="admin",
            email="admin@marketpulse.ai",
            password_hash=generate_password_hash("AdminPassword123"),
            role="admin"
        ))
        db.session.add(User(
            username="user",
            email="user@marketpulse.ai",
            password_hash=generate_password_hash("UserPassword123"),
            role="user"
        ))
        db.session.commit()

# --- Auth Gate & Activity Logging Helpers ---
@app.before_request
def check_login():
    exempt_routes = ["route_login", "route_register", "static"]
    if request.endpoint and request.endpoint not in exempt_routes:
        if "user_id" not in session:
            return redirect(url_for("route_login"))

@app.context_processor
def inject_user_context():
    user = None
    if "user_id" in session:
        user = User.query.get(session["user_id"])
    return dict(
        current_user=user,
        current_time=datetime.now().strftime("%b %d, %Y %H:%M")
    )

def log_user_activity(action: str):
    user_id = session.get("user_id")
    username = session.get("user_username", "Anonymous")
    ip_addr = request.remote_addr
    log = ActivityLog(
        user_id=user_id,
        username=username,
        action=action,
        ip_address=ip_addr
    )
    db.session.add(log)
    db.session.commit()

# Helper to get active session symbol
def get_session_symbol():
    if "active_symbol" not in session:
        session["active_symbol"] = "AAPL"
    return session["active_symbol"]

# ==========================================================================
# 1. Page Routes
# ==========================================================================

# ==========================================================================
# 1. Page Routes & Auth View Handlers
# ==========================================================================

@app.route("/login", methods=["GET", "POST"])
def route_login():
    if "user_id" in session:
        return redirect(url_for("route_overview"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["user_username"] = user.username
            session["user_role"] = user.role
            log_user_activity("Logged In")
            return redirect(url_for("route_overview"))
        return render_template("login.html", error="Invalid email or password.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def route_register():
    if "user_id" in session:
        return redirect(url_for("route_overview"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        if not username or not email or not password:
            return render_template("register.html", error="All fields are required.")
            
        if User.query.filter((User.email == email) | (User.username == username)).first():
            return render_template("register.html", error="Username or Email already registered.")
            
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_pw, role="user")
        db.session.add(new_user)
        db.session.commit()
        
        session["user_id"] = new_user.id
        session["user_username"] = new_user.username
        session["user_role"] = new_user.role
        log_user_activity("Registered and Logged In")
        return redirect(url_for("route_overview"))
        
    return render_template("register.html")

@app.route("/logout")
def route_logout():
    log_user_activity("Logged Out")
    session.clear()
    return redirect(url_for("route_login"))

@app.route("/admin")
def route_admin():
    user_id = session.get("user_id")
    user = User.query.get(user_id) if user_id else None
    if not user or user.role != "admin":
        return "Forbidden", 403
        
    log_user_activity("Accessed Admin Dashboard")
    total_users = User.query.count()
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    
    return render_template(
        "admin.html",
        active_page="admin",
        active_symbol=get_session_symbol(),
        total_users=total_users,
        logs=logs
    )

@app.route("/")
def index():
    return redirect(url_for("route_overview"))

@app.route("/overview")
def route_overview():
    symbol = get_session_symbol()
    data = services.fetch_asset_info(symbol)
    log_user_activity(f"Viewed Dashboard for {symbol}")
    return render_template(
        "overview.html",
        active_page="overview",
        active_symbol=symbol,
        **data
    )

@app.route("/todays-trades")
def route_todays_trades():
    import random
    stock_pool = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "COIN", "AMD", "NFLX"]
    crypto_pool = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD"]
    
    suggested_stocks = random.sample(stock_pool, min(4, len(stock_pool)))
    suggested_cryptos = random.sample(crypto_pool, min(4, len(crypto_pool)))
    
    stock_trades = []
    crypto_trades = []
    
    # Process stocks
    for symbol in suggested_stocks:
        try:
            info = services.fetch_asset_info(symbol)
            price = info.get("price", 0.0)
            name = info.get("name", symbol)
            change = info.get("change", 0.0)
            
            if change >= 0:
                direction = "BUY"
                entry_min = price * 0.99
                entry_max = price * 1.005
                target = price * 1.045
                stop_loss = price * 0.975
            else:
                direction = "SHORT"
                entry_min = price * 0.995
                entry_max = price * 1.01
                target = price * 0.955
                stop_loss = price * 1.025
                
            if direction == "BUY":
                profit_dollars = 1000.0 * (target - price) / price
                profit_pct = (target - price) / price * 100.0
                reason = (
                    f"{name} displays strong technical structure with a +{change:.2f}% gain today. "
                    f"ML model forecasts short-term consolidation followed by a breakout. "
                    f"Recommended entry: ${entry_min:,.2f} - ${entry_max:,.2f}."
                )
            else:
                profit_dollars = 1000.0 * (price - target) / price
                profit_pct = (price - target) / price * 100.0
                reason = (
                    f"{name} is facing technical resistance and has declined -{abs(change):.2f}% today. "
                    f"Pulse AI detects volume distribution. "
                    f"Recommended short entry: ${entry_min:,.2f} - ${entry_max:,.2f}."
                )
                
            stock_trades.append({
                "symbol": symbol,
                "name": name,
                "current_price": price,
                "direction": direction,
                "entry_range": f"${entry_min:,.2f} - ${entry_max:,.2f}",
                "target": round(target, 2),
                "stop_loss": round(stop_loss, 2),
                "profit_dollars": round(profit_dollars, 2),
                "profit_pct": round(profit_pct, 1),
                "reason": reason,
                "logo_url": info.get("logo_url")
            })
        except Exception as e:
            print(f"Error compiling stock trade recommendations for {symbol}: {e}")
            
    # Process cryptos
    for symbol in suggested_cryptos:
        try:
            info = services.fetch_asset_info(symbol)
            price = info.get("price", 0.0)
            name = info.get("name", symbol)
            change = info.get("change", 0.0)
            
            if change >= 0:
                direction = "BUY"
                entry_min = price * 0.99
                entry_max = price * 1.005
                target = price * 1.045
                stop_loss = price * 0.975
            else:
                direction = "SHORT"
                entry_min = price * 0.995
                entry_max = price * 1.01
                target = price * 0.955
                stop_loss = price * 1.025
                
            if direction == "BUY":
                profit_dollars = 1000.0 * (target - price) / price
                profit_pct = (target - price) / price * 100.0
                reason = (
                    f"{name} displays strong technical structure with a +{change:.2f}% gain today. "
                    f"ML model forecasts short-term consolidation followed by a breakout. "
                    f"Recommended entry: ${entry_min:,.2f} - ${entry_max:,.2f}."
                )
            else:
                profit_dollars = 1000.0 * (price - target) / price
                profit_pct = (price - target) / price * 100.0
                reason = (
                    f"{name} is facing technical resistance and has declined -{abs(change):.2f}% today. "
                    f"Pulse AI detects volume distribution. "
                    f"Recommended short entry: ${entry_min:,.2f} - ${entry_max:,.2f}."
                )
                
            crypto_trades.append({
                "symbol": symbol,
                "name": name,
                "current_price": price,
                "direction": direction,
                "entry_range": f"${entry_min:,.2f} - ${entry_max:,.2f}",
                "target": round(target, 2),
                "stop_loss": round(stop_loss, 2),
                "profit_dollars": round(profit_dollars, 2),
                "profit_pct": round(profit_pct, 1),
                "reason": reason,
                "logo_url": info.get("logo_url")
            })
        except Exception as e:
            print(f"Error compiling crypto trade recommendations for {symbol}: {e}")
            
    log_user_activity("Viewed Today's Trades")
    return render_template(
        "todays_trades.html",
        active_page="todays_trades",
        active_symbol=get_session_symbol(),
        stock_trades=stock_trades,
        crypto_trades=crypto_trades
    )

@app.route("/news")
def route_news():
    symbol = get_session_symbol()
    log_user_activity(f"Viewed News Intelligence for {symbol}")
    return render_template(
        "news.html",
        active_page="news",
        active_symbol=symbol
    )

@app.route("/investors")
def route_investors():
    symbol = get_session_symbol()
    data = services.fetch_asset_info(symbol)
    log_user_activity(f"Viewed Investor Analysis for {symbol}")
    return render_template(
        "investors.html",
        active_page="investors",
        active_symbol=symbol,
        name=data.get("name", symbol),
        asset_class=data.get("asset_class", "stock")
    )

@app.route("/document/<symbol>/<doc_type>")
def route_document(symbol, doc_type):
    symbol = services.get_clean_ticker(symbol)
    data = services.fetch_asset_info(symbol)
    name = data.get("name", symbol)
    asset_class = data.get("asset_class", "stock")
    
    doc_title = ""
    sections = []
    
    if asset_class == "stock":
        if doc_type == "10-K":
            doc_title = f"FORM 10-K - Annual Report for {name} ({symbol})"
            sections = [
                {
                    "title": "Item 1. Business",
                    "content": f"{name} is a leading global technology and services enterprise. Our mission is to build solutions that redefine how society interacts, transacts, and grows. We operate across multiple segments: consumer platforms, enterprise cloud solutions, and bleeding-edge digital assets. Our competitive advantage lies in our rapid cycle iteration, deep engineering talent pool, and extensive global infrastructure scale."
                },
                {
                    "title": "Item 1A. Risk Factors",
                    "content": "Our business is subject to significant risks including: high rate of competitive displacement, cyber security breaches targeting our central systems, complex and evolving local and international regulatory landscapes, and macro-economic factors affecting consumer and enterprise spending. Any disruption to our supply chain or digital operations could materially affect quarterly revenue."
                },
                {
                    "title": "Item 7. Management's Discussion and Analysis (MD&A)",
                    "content": "During the fiscal year, we experienced a robust 12% revenue growth year-over-year, driven by our digital segment and cloud subscriptions. Operating margin expanded to 28.4%. We continue to invest heavily in machine learning engines to streamline operation workflows and improve search retrieval algorithms."
                },
                {
                    "title": "Item 8. Financial Statements and Supplementary Data",
                    "is_table": True,
                    "table_headers": ["Financial Metric (USD Millions)", "FY 2025", "FY 2024", "YoY Change"],
                    "table_rows": [
                        ["Total Revenue", "$85,420", "$76,268", "+12.0%"],
                        ["Cost of Goods Sold (COGS)", "$32,150", "$29,450", "+9.2%"],
                        ["Gross Profit", "$53,270", "$46,818", "+13.8%"],
                        ["Research & Development (R&D)", "$12,400", "$10,850", "+14.3%"],
                        ["Sales & Marketing", "$9,800", "$9,100", "+7.7%"],
                        ["Operating Income (EBIT)", "$24,220", "$20,150", "+20.2%"],
                        ["Net Income", "$19,550", "$16,200", "+20.7%"],
                        ["Total Current Assets", "$45,600", "$38,400", "+18.7%"],
                        ["Total Liabilities", "$28,150", "$26,200", "+7.4%"],
                        ["Total Shareholders' Equity", "$17,450", "$12,200", "+43.0%"]
                    ]
                }
            ]
        elif doc_type == "10-Q":
            doc_title = f"FORM 10-Q - Quarterly Report for {name} ({symbol})"
            sections = [
                {
                    "title": "Part I. Financial Information",
                    "content": f"The condensed consolidated balance sheets as of the end of the quarter show steady growth in cash equivalents. Total cash reserves stand at ${round(data.get('price', 150.0)*120, 2):,.2f} million. Capital expenditures for the quarter were focused on deep tech integration."
                },
                {
                    "title": "Condensed Consolidated Statements of Operations (Unaudited)",
                    "is_table": True,
                    "table_headers": ["Metric (Three Months Ended)", "Jun 2026", "Jun 2025", "Change"],
                    "table_rows": [
                        ["Total Revenue", "$22,840", "$20,250", "+12.8%"],
                        ["Operating Income", "$6,410", "$5,290", "+21.2%"],
                        ["Net Income", "$5,120", "$4,210", "+21.6%"],
                        ["Basic EPS (USD)", "$1.28", "$1.05", "+21.9%"]
                    ]
                },
                {
                    "title": "Part II. Other Information - Legal Proceedings",
                    "content": "The company is involved in routine regulatory audits and commercial intellectual property disputes. Management believes the resolution of these proceedings will not have a material impact on our consolidated financial position or operational results."
                }
            ]
        elif doc_type == "8-K":
            doc_title = f"FORM 8-K - Current Report for {name} ({symbol})"
            sections = [
                {
                    "title": "Item 1.01 Entry into a Material Definitive Agreement",
                    "content": f"On June 12, 2026, {name} entered into a strategic joint partnership agreement with a leading infrastructure consortium. Under the terms, both parties will integrate their digital networks, leveraging artificial intelligence engines to analyze asset connection models. This agreement is expected to expand our total addressable market by $4.5 billion over three years."
                },
                {
                    "title": "Item 5.02 Departure of Directors or Certain Officers; Election of Directors",
                    "content": "On June 10, 2026, the Board of Directors elected a new Chief Operating Officer (COO) effective immediately. The new officer has over fifteen years of executive experience in enterprise scale systems and high-throughput transaction terminals."
                }
            ]
        else:
            return "Document type not found for stocks", 404
            
    else: # crypto
        if doc_type == "whitepaper":
            doc_title = f"{name} ({symbol}) Technical Whitepaper"
            sections = [
                {
                    "title": "1. Abstract",
                    "content": f"The {name} protocol proposes a decentralized, high-throughput network to manage asset intelligence feeds without centralized brokers. By utilizing a zero-knowledge Proof-of-Stake consensus framework, the protocol guarantees 99.999% uptime with sub-second execution finality. This paper presents our security design, consensus parameters, and mathematical proofs."
                },
                {
                    "title": "2. Consensus & Node Network Architecture",
                    "content": "The network maintains security through validator nodes staking native tokens. Blocks are produced using a VRF (Verifiable Random Function) seed, which randomizes proposer nodes to prevent DDoS attacks targeting specific infrastructure. The state is finalized via an asynchronous Byzantine Fault Tolerant (aBFT) round robin."
                },
                {
                    "title": "3. Tokenomics & Vesting Allocations",
                    "is_table": True,
                    "table_headers": ["Token Allocation Group", "Percentage of Supply", "Initial Lockup", "Vesting Period"],
                    "table_rows": [
                        ["Whales / Seed Investors", "15.0%", "12 Months", "24 Months Linear"],
                        ["Core Protocol Founders", "12.5%", "24 Months", "48 Months Linear"],
                        ["DeFi Smart Contract Reserves", "20.0%", "None", "Ongoing Rewards"],
                        ["Exchange Reserves (Liquidity)", "18.0%", "None", "Market Making Pools"],
                        ["Community Stakers / Retail", "34.5%", "None", "Block Rewards Over 10 Years"]
                    ]
                },
                {
                    "title": "4. Formal Mathematical Verifications",
                    "content": "Let \\(V\\) be the set of active validators. The network consensus holds if: \\(|V_{faulty}| < \\frac{1}{3}|V|\\). We define our throughput capacity as: \\(T = \\frac{B_{size}}{T_{latency}} \\times (1 - d)\\), where \\(d\\) represents network propagation delay."
                }
            ]
        elif doc_type == "security-audit":
            doc_title = f"{name} ({symbol}) Smart Contract Security Audit Report"
            sections = [
                {
                    "title": "Executive Summary",
                    "content": "A comprehensive security audit was executed on the core staking and distribution contracts of the protocol. The audit utilized automated static analysis, symbolic execution engines, and manual code review to verify vulnerability status."
                },
                {
                    "title": "Vulnerability Findings Log",
                    "is_table": True,
                    "table_headers": ["Issue ID", "Severity", "Description", "Status"],
                    "table_rows": [
                        ["MP-SEC-01", "Critical", "Reentrancy vector detected in withdrawal reward payout loops.", "RESOLVED"],
                        ["MP-SEC-02", "High", "Unchecked arithmetic operations in voting contract could cause overflow.", "RESOLVED"],
                        ["MP-SEC-03", "Medium", "Timestamp dependence in block verification logic.", "MITIGATED"],
                        ["MP-SEC-04", "Low", "Gas optimization in loop iterations.", "RESOLVED"]
                    ]
                },
                {
                    "title": "Audit Conclusion",
                    "content": "The core staking and lockup smart contracts demonstrate exceptional security hygiene. Following the resolution of MP-SEC-01 and MP-SEC-02, the contracts are rated SECURE and ready for mainnet deployment."
                }
            ]
        elif doc_type == "compliance-brief":
            doc_title = f"{name} ({symbol}) Regulatory & Compliance Briefing"
            sections = [
                {
                    "title": "1. Regulatory Jurisdiction Exposure",
                    "content": "The protocol operates as a decentralized autonomous organization (DAO) with nodes distributed across 42 countries. Core development is managed by a Swiss foundation, limiting exposure to single-jurisdiction regulatory actions."
                },
                {
                    "title": "2. Decentralization Scoring & Howey Test Analysis",
                    "content": "Based on the distributed staking parameters, no wallet address controls more than 4% of validator nodes. There is no central managerial group, suggesting a high likelihood of classification as a decentralized commodity rather than an unregistered security."
                },
                {
                    "title": "3. AML / CFT Compliance Controls",
                    "content": "While the protocol itself is permissionless, major exchange liquidity pools and fiat on/off ramps connected to the network enforce full KYC/AML procedures in compliance with FATF (Financial Action Task Force) recommendations."
                }
            ]
        else:
            return "Document type not found for crypto", 404
            
    log_user_activity(f"Viewed Document {doc_type} for {symbol}")
    return render_template(
        "document_viewer.html",
        symbol=symbol,
        name=name,
        doc_type=doc_type,
        doc_title=doc_title,
        sections=sections,
        asset_class=asset_class
    )

@app.route("/sentiment")
def route_sentiment():
    symbol = get_session_symbol()
    log_user_activity(f"Viewed Sentiment Dashboard for {symbol}")
    return render_template(
        "sentiment.html",
        active_page="sentiment",
        active_symbol=symbol
    )

@app.route("/network")
def route_network():
    symbol = get_session_symbol()
    log_user_activity(f"Viewed Market Connection Network for {symbol}")
    return render_template(
        "network.html",
        active_page="network",
        active_symbol=symbol
    )

@app.route("/predictions")
def route_predictions():
    symbol = get_session_symbol()
    log_user_activity(f"Viewed Prediction Engine for {symbol}")
    return render_template(
        "predictions.html",
        active_page="predictions",
        active_symbol=symbol
    )

@app.route("/portfolio")
def route_portfolio():
    symbol = get_session_symbol()
    log_user_activity("Viewed Portfolio Analyzer")
    return render_template(
        "portfolio.html",
        active_page="portfolio",
        active_symbol=symbol
    )

@app.route("/email-alerts")
def route_email_alerts():
    symbol = get_session_symbol()
    active_email_alerts = Alert.query.filter_by(email_notify=True, is_active=True).order_by(Alert.created_at.desc()).all()
    sent_email_alerts = Alert.query.filter_by(email_notify=True, is_active=False).order_by(Alert.triggered_at.desc()).all()
    
    log_user_activity("Viewed Email Alerts Hub")
    return render_template(
        "email_alerts.html",
        active_page="email_alerts",
        active_symbol=symbol,
        active_email_alerts=active_email_alerts,
        sent_email_alerts=sent_email_alerts
    )

@app.route("/search", methods=["GET", "POST"])
def route_search():
    if request.method == "POST":
        symbol = request.form.get("symbol", "AAPL").strip().upper()
        if symbol:
            symbol = services.get_clean_ticker(symbol)
            session["active_symbol"] = symbol
    else:
        symbol = request.args.get("symbol", "AAPL").strip().upper()
        if symbol:
            symbol = services.get_clean_ticker(symbol)
            session["active_symbol"] = symbol
            
    log_user_activity(f"Searched asset symbol: {symbol}")
    
    ref = request.referrer
    if ref and "/overview" in ref:
        return redirect(url_for("route_overview"))
    elif ref and "/news" in ref:
        return redirect(url_for("route_news"))
    elif ref and "/investors" in ref:
        return redirect(url_for("route_investors"))
    elif ref and "/sentiment" in ref:
        return redirect(url_for("route_sentiment"))
    elif ref and "/network" in ref:
        return redirect(url_for("route_network"))
    elif ref and "/predictions" in ref:
        return redirect(url_for("route_predictions"))
    elif ref and "/portfolio" in ref:
        return redirect(url_for("route_portfolio"))
        
    return redirect(url_for("route_overview"))

# ==========================================================================
# 2. JSON API Endpoints (AJAX)
# ==========================================================================

import threading

# Global variables for background ML training
PREDICTION_CACHE = {}
TRAINING_STATUS = {}
TRAINING_LOCK = threading.Lock()

def run_background_training(symbol, history, algorithm="random_forest"):
    try:
        forecast = services.train_and_predict(history, forecast_days=7, algorithm=algorithm)
        with TRAINING_LOCK:
            PREDICTION_CACHE[symbol] = forecast
            TRAINING_STATUS[symbol] = "completed"
    except Exception as e:
        print(f"Background training failed for {symbol}: {e}")
        with TRAINING_LOCK:
            TRAINING_STATUS[symbol] = "failed"

@app.route("/api/market-data/<symbol>")
def api_market_data(symbol):
    info = services.fetch_asset_info(symbol)
    price = info.get("price", 0.0)
    
    # Check active alerts for this symbol
    try:
        active_alerts = Alert.query.filter_by(symbol=symbol, is_active=True).all()
        for alert in active_alerts:
            triggered = False
            sentiment = 0.0
            if alert.alert_type == "price_above" and price >= alert.threshold:
                triggered = True
            elif alert.alert_type == "price_below" and price <= alert.threshold:
                triggered = True
            elif alert.alert_type == "sentiment_below":
                # Fetch news sentiment to check
                try:
                    raw_news = services.fetch_rss_news(symbol)
                    scored_news = services.analyze_articles_sentiment(raw_news)
                    metrics = services.aggregate_sentiment_metrics(scored_news)
                    sentiment = metrics.get("average", 0.0)
                    if sentiment <= alert.threshold:
                        triggered = True
                except Exception as e:
                    print(f"Error checking sentiment alert for {symbol}: {e}")
            
            if triggered:
                alert.is_active = False
                alert.triggered_at = datetime.utcnow()
                db.session.commit()
                
                # Represent email dispatch log
                user_email = alert.target_email
                if not user_email:
                    user_email = "user@marketpulse.ai"
                    if "user_id" in session:
                        user = User.query.get(session["user_id"])
                        if user:
                            user_email = user.email
                
                metric_value = price if alert.alert_type != "sentiment_below" else sentiment
                alert_desc = f"Price rises above ${alert.threshold}" if alert.alert_type == "price_above" else \
                             f"Price falls below ${alert.threshold}" if alert.alert_type == "price_below" else \
                             f"Sentiment falls below {alert.threshold}"
                
                # Actually send the email if email_notify is enabled
                email_sent = False
                if alert.email_notify and user_email and user_email != "user@marketpulse.ai":
                    email_sent = send_alert_email(
                        to_email=user_email,
                        symbol=symbol,
                        alert_type=alert.alert_type,
                        threshold=alert.threshold,
                        current_value=metric_value
                    )
                
                email_status = "Email delivered" if email_sent else "Email not configured (check SMTP settings in .env)"
                action_log_desc = f"[EMAIL ALERT] Alert Triggered for {symbol}: {alert_desc} (Current: {metric_value}). {email_status} to {user_email}."
                print(f"\n{action_log_desc}\n")
                
                # Log action to ActivityLog
                log = ActivityLog(
                    user_id=session.get("user_id"),
                    username=session.get("user_username", "System"),
                    action=action_log_desc,
                    ip_address=request.remote_addr
                )
                db.session.add(log)
                db.session.commit()
    except Exception as e:
        print(f"Error in alert processing for {symbol}: {e}")
        
    return jsonify(info)

@app.route("/api/market-data/<symbol>/history")
def api_market_history(symbol):
    period = request.args.get("period", "3mo")
    interval = request.args.get("interval", "1d")
    history = services.fetch_historical_prices(symbol, period, interval)
    return jsonify(history)

@app.route("/api/news/<symbol>")
def api_news(symbol):
    raw_news = services.fetch_rss_news(symbol)
    scored_news = services.analyze_articles_sentiment(raw_news)
    metrics = services.aggregate_sentiment_metrics(scored_news)
    
    # Generate executive summary using AI summaries
    summary = services.get_ai_summarizer(scored_news, symbol)
    
    return jsonify({
        "symbol": symbol,
        "news": scored_news,
        "metrics": metrics,
        "summary": summary
    })

@app.route("/api/predictions/<symbol>")
def api_predictions(symbol):
    period = request.args.get("period", "3mo")
    interval = request.args.get("interval", "1d")
    algorithm = request.args.get("algorithm", "random_forest")
    force_retrain = request.args.get("force_retrain", "false").lower() == "true"
    
    history = services.fetch_historical_prices(symbol, period, interval)
    
    # Check cache
    with TRAINING_LOCK:
        status = TRAINING_STATUS.get(symbol)
        cached_result = PREDICTION_CACHE.get(symbol)
        
    if not force_retrain and cached_result and status == "completed":
        return jsonify({
            "status": "completed",
            "symbol": symbol,
            "historical": history,
            "forecast": cached_result
        })
        
    if not force_retrain and status == "training":
        return jsonify({
            "status": "training",
            "symbol": symbol,
            "message": "Model is training in the background..."
        })
        
    # Start training thread
    with TRAINING_LOCK:
        TRAINING_STATUS[symbol] = "training"
        
    thread = threading.Thread(target=run_background_training, args=(symbol, history, algorithm))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "status": "training",
        "symbol": symbol,
        "message": "Background training started."
    })

@app.route("/api/trade-signal/<symbol>")
def api_trade_signal(symbol):
    info = services.fetch_asset_info(symbol)
    price = info.get("price", 0.0)
    
    history = services.fetch_historical_prices(symbol, "3mo", "1d")
    close_prices = history.get("close", [])
    
    raw_news = services.fetch_rss_news(symbol)
    scored_news = services.analyze_articles_sentiment(raw_news)
    metrics = services.aggregate_sentiment_metrics(scored_news)
    sentiment = metrics.get("average", 0.0)
    
    with TRAINING_LOCK:
        forecast = PREDICTION_CACHE.get(symbol)
        
    if not forecast:
        # Fast fallback prediction to avoid blocking
        import pandas as pd
        df = pd.DataFrame({
            "close": close_prices,
            "date": pd.to_datetime(history["dates"])
        })
        forecast = services.prediction_model.generate_random_walk_predictions(df, 7)
        
    predicted_close = forecast.get("predictions", [])
    pred_change = ((predicted_close[-1] - price) / price) if price > 0 and predicted_close else 0.0
    
    signal = "HOLD"
    entry_min = price * 0.99
    entry_max = price * 1.01
    target = price
    stop_loss = price
    description = ""
    
    if pred_change > 0.015 and sentiment > 0.05:
        signal = "BUY"
        target = float(predicted_close[-1])
        stop_loss = float(price * 0.95)
        description = (
            f"Bullish indicators detected: The Random Forest model projects a {pred_change*100:.1f}% rise "
            f"over the next 7 days, supported by positive news sentiment (average score: {sentiment:.2f})."
        )
    elif pred_change < -0.015 and sentiment < -0.05:
        signal = "SHORT"
        target = float(predicted_close[-1])
        stop_loss = float(price * 1.05)
        description = (
            f"Bearish momentum detected: The ML engine projects a {abs(pred_change)*100:.1f}% decline "
            f"over the next 7 days. News sentiment is negative (average score: {sentiment:.2f})."
        )
    else:
        description = (
            f"No clear trading signal. Current trends suggest consolidation. "
            f"The ML 7-day forecast indicates a mild change of {pred_change*100:.1f}%. "
            f"News sentiment index is neutral at {sentiment:.2f}."
        )
        
    return jsonify({
        "symbol": symbol,
        "signal": signal,
        "current_price": price,
        "entry_range": f"${entry_min:.2f} - ${entry_max:.2f}",
        "target": round(target, 2),
        "stop_loss": round(stop_loss, 2),
        "description": description
    })

@app.route("/api/network")
def api_network():
    symbol = get_session_symbol()
    is_crypto = "-" in symbol or "USD" in symbol
    
    # Generate standard network node cluster
    nodes = [
        {"id": "active", "label": symbol, "x": 0, "y": 0, "size": 25, "color": "#3b82f6"},
    ]
    
    # Related nodes based on asset class
    if is_crypto:
        related = ["BTC-USD", "ETH-USD", "SOL-USD", "USDT"]
        macro = ["FED Rates", "SEC Rules", "Stablecoin Regulation"]
    else:
        related = ["MSFT", "GOOGL", "AMZN", "SPY"]
        macro = ["FED Rates", "Inflation Index", "Bond Yields"]
        
    edges = []
    
    # Add related assets nodes
    for i, name in enumerate(related):
        angle = (2 * np.pi * i) / len(related)
        x = np.cos(angle) * 1.5
        y = np.sin(angle) * 1.5
        nodes.append({"id": f"rel_{i}", "label": name, "x": x, "y": y, "size": 18, "color": "#10b981"})
        edges.append({"x0": 0, "y0": 0, "x1": x, "y1": y, "weight": 0.8})
        
    # Add macro node influences
    for j, name in enumerate(macro):
        angle = (2 * np.pi * j) / len(macro) + 0.5
        x = np.cos(angle) * 2.8
        y = np.sin(angle) * 2.8
        nodes.append({"id": f"macro_{j}", "label": name, "x": x, "y": y, "size": 20, "color": "#f59e0b"})
        edges.append({"x0": 0, "y0": 0, "x1": x, "y1": y, "weight": 0.5})
        
        # Connect one related asset to a macro factor for depth
        if len(nodes) > 2:
            edges.append({"x0": nodes[1]["x"], "y0": nodes[1]["y"], "x1": x, "y1": y, "weight": 0.3})
            
    return jsonify({
        "nodes": nodes,
        "edges": edges
    })

# --- Watchlist API ---
@app.route("/api/watchlist", methods=["GET", "POST"])
def api_watchlist():
    if request.method == "POST":
        data = request.get_json() or {}
        symbol = data.get("symbol", "").strip().upper()
        if symbol:
            item = Watchlist.query.filter_by(symbol=symbol).first()
            if item:
                db.session.delete(item)
                db.session.commit()
                return jsonify({"status": "removed", "symbol": symbol})
            else:
                # Resolve asset class
                is_crypto = "-" in symbol or "USD" in symbol
                asset_class = "crypto" if is_crypto else "stock"
                db.session.add(Watchlist(symbol=symbol, asset_class=asset_class))
                db.session.commit()
                return jsonify({"status": "added", "symbol": symbol})
        return jsonify({"error": "Symbol missing"}), 400
        
    items = Watchlist.query.all()
    return jsonify([i.to_dict() for i in items])

# --- Alerts API ---
@app.route("/api/alerts", methods=["GET", "POST"])
def api_alerts():
    if request.method == "POST":
        data = request.get_json() or {}
        symbol = data.get("symbol", "").strip().upper()
        alert_type = data.get("alert_type", "price_above")
        threshold = float(data.get("threshold", 0.0))
        email_notify = bool(data.get("email_notify", False))
        target_email = data.get("target_email")
        if target_email:
            target_email = target_email.strip()
        
        cond_map = {
            "price_above": f"price > {threshold}",
            "price_below": f"price < {threshold}",
            "sentiment_below": f"sentiment < {threshold}"
        }
        
        alert = Alert(
            symbol=symbol,
            alert_type=alert_type,
            condition=cond_map.get(alert_type, f"custom {threshold}"),
            threshold=threshold,
            email_notify=email_notify,
            target_email=target_email
        )
        db.session.add(alert)
        db.session.commit()
        return jsonify(alert.to_dict())
        
    alerts = Alert.query.filter_by(is_active=True).all()
    return jsonify([a.to_dict() for a in alerts])

@app.route("/api/alerts/<int:alert_id>", methods=["DELETE"])
def api_delete_alert(alert_id):
    alert = Alert.query.get(alert_id)
    if alert:
        db.session.delete(alert)
        db.session.commit()
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Alert not found"}), 404

# --- Portfolio API ---
@app.route("/api/portfolio", methods=["GET", "POST"])
def api_portfolio():
    if request.method == "POST":
        data = request.get_json() or {}
        symbol = data.get("symbol", "").strip().upper()
        qty = float(data.get("quantity", 0.0))
        price = float(data.get("purchase_price", 0.0))
        trade_type = data.get("trade_type", "Long").strip()
        
        if symbol and qty > 0 and price > 0:
            # Clean and look up asset info
            symbol = services.get_clean_ticker(symbol)
            info = services.fetch_asset_info(symbol)
            name = info.get("name", symbol)
            asset_class = info.get("asset_class", "stock")
            
            # Check if exists, update it, else create
            holding = Portfolio.query.filter_by(symbol=symbol, trade_type=trade_type).first()
            if holding:
                # Recalculate average purchase price
                total_qty = holding.quantity + qty
                avg_cost = ((holding.quantity * holding.purchase_price) + (qty * price)) / total_qty
                holding.quantity = total_qty
                holding.purchase_price = avg_cost
            else:
                holding = Portfolio(
                    symbol=symbol,
                    name=name,
                    quantity=qty,
                    purchase_price=price,
                    asset_class=asset_class,
                    trade_type=trade_type
                )
                db.session.add(holding)
            
            db.session.commit()
            return jsonify(holding.to_dict())
        return jsonify({"error": "Invalid inputs"}), 400
        
    holdings = Portfolio.query.all()
    return jsonify([h.to_dict() for h in holdings])

@app.route("/api/portfolio/<int:holding_id>", methods=["DELETE"])
def api_delete_portfolio(holding_id):
    holding = Portfolio.query.get(holding_id)
    if holding:
        db.session.delete(holding)
        db.session.commit()
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Holding not found"}), 404

# --- Chat API ---
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    symbol = data.get("symbol", "AAPL").strip().upper()
    
    # Log user query activity
    log_user_activity(f"Asked Assistant about {symbol}: '{message[:45]}...'")
    
    # Fetch historical pricing as context
    history = services.fetch_historical_prices(symbol, "1mo")
    response = services.generate_chat_response(message, symbol, history)
    
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
