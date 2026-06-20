/**
 * MarketPulse AI - Main Dashboard Javascript Client
 * Handles AJAX updates, dynamic UI actions, and Plotly.js chart rendering
 */

document.addEventListener("DOMContentLoaded", function () {
    // UI Global Handlers
    initSidebarAsset();
    initWatchlist();
    initAlerts();
    initClock();
    loadActivePageModule();
    
    // Watchlist Star click event
    const watchlistStarBtn = document.getElementById("add-watchlist-btn");
    if (watchlistStarBtn) {
        watchlistStarBtn.addEventListener("click", toggleWatchlist);
    }
});

// ==========================================================================
// 1. Sidebar & Global State
// ==========================================================================

function initSidebarAsset() {
    fetch(`/api/market-data/${ACTIVE_SYMBOL}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === "success" || data.status === "simulated") {
                // Update sidebar details
                document.getElementById("sidebar-name").textContent = data.name;
                document.getElementById("sidebar-price").textContent = `$${data.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                
                const changeEl = document.getElementById("sidebar-change");
                const changeSign = data.change >= 0 ? "+" : "";
                changeEl.textContent = `${changeSign}${data.change.toFixed(2)}%`;
                
                if (data.change >= 0) {
                    changeEl.className = "active-change trend-up";
                } else {
                    changeEl.className = "active-change trend-down";
                }
                
                document.getElementById("sidebar-asset-class").textContent = data.asset_class;
                
                // Update sidebar logo
                const logoContainer = document.getElementById("sidebar-logo-container");
                if (logoContainer && data.logo_url) {
                    logoContainer.innerHTML = `
                        <img src="${data.logo_url}" alt="${data.symbol} Logo" style="width:100%; height:100%; object-fit:contain; background:#ffffff; display:block;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                        <div style="display:none; width:100%; height:100%; background:linear-gradient(135deg, var(--accent-blue) 0%, #1e293b 100%); color:white; align-items:center; justify-content:center; font-family:'Outfit',sans-serif; font-weight:700; font-size:10px;">
                            ${data.symbol.substring(0, 2)}
                        </div>
                    `;
                }
                
                // Update engine API badges
                const engineBadge = document.getElementById("engine-badge");
                if (engineBadge) {
                    engineBadge.textContent = data.status === "simulated" ? "Local Mock" : "Real Feed";
                    engineBadge.className = data.status === "simulated" ? "engine-badge sentiment-neu" : "engine-badge sentiment-pos";
                }
                
                // Check if symbol is in watchlist, update star icon
                checkWatchlistStatus(data.symbol);
            }
        })
        .catch(err => console.error("Error loading sidebar asset:", err));
}

// ==========================================================================
// 2. Watchlist Logic
// ==========================================================================

function initWatchlist() {
    const watchlistBtn = document.getElementById("watchlist-dropdown-btn");
    const dropdown = document.getElementById("watchlist-dropdown-panel");
    const list = document.getElementById("dropdown-watchlist-list");
    const countBadge = document.getElementById("watchlist-count");
    
    if (!watchlistBtn) return;
    
    // Toggle dropdown
    watchlistBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
        
        // Close alerts dropdown if open
        const alertsDropdown = document.getElementById("alerts-dropdown-panel");
        if (alertsDropdown) alertsDropdown.style.display = "none";
    });
    
    document.addEventListener("click", function () {
        if (dropdown) dropdown.style.display = "none";
    });
    
    dropdown.addEventListener("click", function (e) {
        e.stopPropagation();
    });
    
    // Fetch watchlist items
    fetch("/api/watchlist")
        .then(res => res.json())
        .then(items => {
            countBadge.textContent = items.length;
            countBadge.style.display = items.length === 0 ? "none" : "flex";
            
            list.innerHTML = "";
            if (items.length === 0) {
                list.innerHTML = `<p class="empty-alerts">No assets watched.</p>`;
                return;
            }
            
            items.forEach(item => {
                const itemEl = document.createElement("a");
                itemEl.href = `/search?symbol=${item.symbol}`;
                itemEl.className = "watchlist-dropdown-item";
                itemEl.style.marginBottom = "8px";
                
                // Fetch quick price details
                fetch(`/api/market-data/${item.symbol}`)
                    .then(r => r.json())
                    .then(priceData => {
                        const changeSign = priceData.change >= 0 ? "+" : "";
                        const changeClass = priceData.change >= 0 ? "wl-change trend-up" : "wl-change trend-down";
                        
                        itemEl.innerHTML = `
                            <div class="wl-drop-left">
                                <span style="font-weight:700;">${item.symbol}</span>
                                <span style="font-size:10px; color:var(--text-muted);">${priceData.name}</span>
                            </div>
                            <div class="wl-drop-right">
                                <strong>$${priceData.price.toFixed(2)}</strong>
                                <span class="${changeClass}">${changeSign}${priceData.change.toFixed(2)}%</span>
                            </div>
                        `;
                    });
                    
                list.appendChild(itemEl);
            });
        })
        .catch(err => console.error("Error loading watchlist:", err));
}

function checkWatchlistStatus(symbol) {
    const btn = document.getElementById("add-watchlist-btn");
    if (!btn) return;
    
    fetch("/api/watchlist")
        .then(res => res.json())
        .then(items => {
            const isWatched = items.some(item => item.symbol === symbol);
            const icon = btn.querySelector("i");
            if (isWatched) {
                icon.className = "fa-solid fa-star";
                btn.style.color = "var(--accent-gold)";
            } else {
                icon.className = "fa-regular fa-star";
                btn.style.color = "var(--text-secondary)";
            }
        });
}

function toggleWatchlist() {
    fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: ACTIVE_SYMBOL })
    })
    .then(res => res.json())
    .then(data => {
        checkWatchlistStatus(ACTIVE_SYMBOL);
        initWatchlist();
    })
    .catch(err => console.error("Error toggling watchlist:", err));
}

// ==========================================================================
// 3. Alert Logic
// ==========================================================================

let alertsInitialized = false;

function initAlerts() {
    const alertsBtn = document.getElementById("alert-bell-btn");
    const dropdown = document.getElementById("alerts-dropdown-panel");
    
    if (!alertsBtn) return;
    
    if (!alertsInitialized) {
        // Toggle dropdown
        alertsBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
            
            // Close watchlist dropdown if open
            const watchlistDropdown = document.getElementById("watchlist-dropdown-panel");
            if (watchlistDropdown) watchlistDropdown.style.display = "none";
        });
        
        document.addEventListener("click", function () {
            dropdown.style.display = "none";
        });
        
        dropdown.addEventListener("click", function (e) {
            e.stopPropagation();
        });
        
        // Modal controls
        const openModalBtn = document.getElementById("open-alert-modal-btn");
        const closeModalBtn = document.getElementById("close-alert-modal");
        const modal = document.getElementById("alert-modal");
        
        if (openModalBtn && modal) {
            openModalBtn.addEventListener("click", () => {
                dropdown.style.display = "none";
                modal.classList.add("open");
            });
        }
        
        if (closeModalBtn && modal) {
            closeModalBtn.addEventListener("click", () => {
                modal.classList.remove("open");
            });
        }
        
        // Toggle email input group visibility on checkbox change
        const emailCheckbox = document.getElementById("alert-email-notify");
        const emailInputGroup = document.getElementById("email-input-group");
        const emailAddressInput = document.getElementById("alert-email-address");
        if (emailCheckbox && emailInputGroup) {
            emailCheckbox.addEventListener("change", function() {
                emailInputGroup.style.display = this.checked ? "block" : "none";
                if (this.checked && emailAddressInput && !emailAddressInput.value) {
                    emailAddressInput.value = USER_EMAIL;
                }
            });
        }
        
        // Submit alert form
        const form = document.getElementById("create-alert-form");
        if (form) {
            form.onsubmit = function (e) {
                e.preventDefault();
                const alertType = document.getElementById("alert-type").value;
                const threshold = parseFloat(document.getElementById("alert-threshold").value);
                const emailNotify = document.getElementById("alert-email-notify") ? document.getElementById("alert-email-notify").checked : false;
                const targetEmail = emailNotify && document.getElementById("alert-email-address") ? document.getElementById("alert-email-address").value.trim() : null;
                
                fetch("/api/alerts", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        symbol: ACTIVE_SYMBOL,
                        alert_type: alertType,
                        threshold: threshold,
                        email_notify: emailNotify,
                        target_email: targetEmail
                    })
                })
                .then(res => res.json())
                .then(() => {
                    modal.classList.remove("open");
                    form.reset();
                    if (emailInputGroup) emailInputGroup.style.display = "none";
                    refreshAlertsList();
                });
            };
        }
        
        alertsInitialized = true;
    }
    
    // Fetch active alerts
    refreshAlertsList();
}

function refreshAlertsList() {
    const list = document.getElementById("dropdown-alerts-list");
    const countBadge = document.getElementById("alert-count");
    if (!list || !countBadge) return;
    
    fetch("/api/alerts")
        .then(res => res.json())
        .then(alerts => {
            countBadge.textContent = alerts.length;
            countBadge.style.display = alerts.length === 0 ? "none" : "flex";
            
            list.innerHTML = "";
            if (alerts.length === 0) {
                list.innerHTML = `<p class="empty-alerts">No alerts active.</p>`;
                return;
            }
            
            alerts.forEach(al => {
                const item = document.createElement("div");
                item.className = "alert-list-item";
                
                let desc = "";
                if (al.alert_type === "price_above") desc = `Price rises above $${al.threshold}`;
                else if (al.alert_type === "price_below") desc = `Price falls below $${al.threshold}`;
                else if (al.alert_type === "sentiment_below") desc = `Sentiment below ${al.threshold}`;
                
                if (al.email_notify) {
                    desc += al.target_email ? ` (📧 to: ${al.target_email})` : " (📧 Email Active)";
                }
                
                item.innerHTML = `
                    <strong>${al.symbol}</strong>: ${desc}
                    <button class="delete-alert-btn" onclick="deleteAlert(${al.id})">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                `;
                list.appendChild(item);
            });
        });
}

window.deleteAlert = function (id) {
    fetch(`/api/alerts/${id}`, { method: "DELETE" })
        .then(res => res.json())
        .then(() => {
            refreshAlertsList();
        });
};

// ==========================================================================
// Clock & Quick Alert Actions
// ==========================================================================

function initClock() {
    const clockEl = document.getElementById("header-time");
    if (!clockEl) return;
    
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    
    function updateClock() {
        const now = new Date();
        const month = months[now.getMonth()];
        const day = String(now.getDate()).padStart(2, '0');
        const year = now.getFullYear();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        
        clockEl.textContent = `${month} ${day}, ${year} ${hours}:${minutes}:${seconds}`;
    }
    
    updateClock();
    setInterval(updateClock, 1000);
}

window.quickAddAlert = function(symbol, alertType, threshold, btnId) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    
    // Prompt the user for an email address to dispatch the alert to.
    // Pre-fill with USER_EMAIL, allowing custom override.
    const emailInput = prompt(`Enter email address to receive notification when this alert triggers for ${symbol} (leave blank to disable email notifications):`, USER_EMAIL);
    
    // If they click Cancel, abort the alert creation
    if (emailInput === null) return;
    
    const emailNotify = emailInput.trim() !== "";
    const targetEmail = emailNotify ? emailInput.trim() : null;
    
    btn.disabled = true;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Adding...`;
    
    fetch("/api/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            symbol: symbol,
            alert_type: alertType,
            threshold: parseFloat(threshold),
            email_notify: emailNotify,
            target_email: targetEmail
        })
    })
    .then(res => {
        if (!res.ok) throw new Error("Failed to add alert");
        return res.json();
    })
    .then(data => {
        btn.innerHTML = `<i class="fa-solid fa-check"></i> Added!`;
        btn.classList.add("added-alert");
        refreshAlertsList();
        
        // Reset after 3 seconds
        setTimeout(() => {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
            btn.classList.remove("added-alert");
        }, 3000);
    })
    .catch(err => {
        console.error("Error setting quick alert:", err);
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Fail`;
        setTimeout(() => {
            btn.innerHTML = originalHTML;
        }, 3000);
    });
};

// ==========================================================================
// 4. Module Loaders (Page Specific Chart Renders)
// ==========================================================================

function loadActivePageModule() {
    const containers = {
        overview: loadOverviewPage,
        news: loadNewsPage,
        investors: loadInvestorsPage,
        sentiment: loadSentimentPage,
        network: loadNetworkPage,
        predictions: loadPredictionsPage,
        portfolio: loadPortfolioPage
    };
    
    const loader = containers[ACTIVE_PAGE];
    if (loader) {
        loader();
    }
}

// -------------------- Page 1: Overview --------------------
let overviewListenersBound = false;

function loadOverviewPage() {
    const chartDiv = document.getElementById("overview-chart-canvas");
    if (!chartDiv) return;
    
    // Bind listeners once
    if (!overviewListenersBound) {
        overviewListenersBound = true;
        const typeSel = document.getElementById("chart-type-selector");
        const durSel = document.getElementById("chart-duration-selector");
        const refreshBtn = document.getElementById("chart-refresh-btn");
        
        if (typeSel) typeSel.addEventListener("change", loadOverviewPage);
        if (durSel) durSel.addEventListener("change", loadOverviewPage);
        if (refreshBtn) refreshBtn.addEventListener("click", function() {
            const icon = document.getElementById("chart-refresh-icon");
            if (icon) {
                icon.style.transform = "rotate(360deg)";
                setTimeout(() => { icon.style.transform = "rotate(0deg)"; }, 600);
            }
            loadOverviewPage();
        });
    }
    
    // Read selector values
    const chartType = document.getElementById("chart-type-selector")?.value || "candlestick";
    const durVal = document.getElementById("chart-duration-selector")?.value || "3mo_1d";
    const [period, interval] = durVal.split("_");
    
    // Show spinner while fetching
    chartDiv.innerHTML = `
        <div class="spinner-wrapper">
            <div class="spinner"></div>
            <div class="loading-text">Fetching pricing history...</div>
        </div>
    `;
    
    // 1. Load Chart Data
    fetch(`/api/market-data/${ACTIVE_SYMBOL}/history?period=${period}&interval=${interval}`)
        .then(res => res.json())
        .then(history => {
            if (history.status === "error" || !history.dates || history.dates.length === 0) {
                chartDiv.innerHTML = `<div class="empty-alerts">No historical price action found for this selection.</div>`;
                return;
            }
            
            let trace = {};
            if (chartType === "candlestick") {
                trace = {
                    x: history.dates,
                    open: history.open,
                    high: history.high,
                    low: history.low,
                    close: history.close,
                    type: 'candlestick',
                    name: ACTIVE_SYMBOL,
                    increasing: { line: { color: '#10b981', width: 1.5 } },
                    decreasing: { line: { color: '#ef4444', width: 1.5 } }
                };
            } else if (chartType === "line") {
                trace = {
                    x: history.dates,
                    y: history.close,
                    type: 'scatter',
                    mode: 'lines',
                    name: ACTIVE_SYMBOL,
                    line: { color: '#3b82f6', width: 2 }
                };
            } else if (chartType === "area") {
                trace = {
                    x: history.dates,
                    y: history.close,
                    type: 'scatter',
                    mode: 'lines',
                    name: ACTIVE_SYMBOL,
                    fill: 'tozeroy',
                    fillcolor: 'rgba(59, 130, 246, 0.08)',
                    line: { color: '#3b82f6', width: 2 }
                };
            }
            
            const layout = {
                dragmode: 'zoom',
                hovermode: 'x unified',
                showlegend: false,
                margin: { t: 15, b: 35, l: 15, r: 60 },
                xaxis: {
                    rangeslider: { visible: false },
                    gridcolor: 'rgba(255,255,255,0.06)',
                    gridwidth: 1,
                    showline: true,
                    linecolor: 'rgba(255,255,255,0.1)',
                    tickcolor: 'rgba(255,255,255,0.1)',
                    font: { color: '#94a3b8', size: 10, family: 'Inter, sans-serif' },
                    showspikes: true,
                    spikemode: 'across',
                    spikesnap: 'cursor',
                    spikedash: 'dash',
                    spikethickness: 1,
                    spikecolor: 'rgba(255,255,255,0.3)'
                },
                yaxis: {
                    side: 'right',
                    gridcolor: 'rgba(255,255,255,0.06)',
                    gridwidth: 1,
                    showline: true,
                    linecolor: 'rgba(255,255,255,0.1)',
                    tickcolor: 'rgba(255,255,255,0.1)',
                    font: { color: '#94a3b8', size: 10, family: 'Inter, sans-serif' },
                    showspikes: true,
                    spikemode: 'across',
                    spikesnap: 'cursor',
                    spikedash: 'dash',
                    spikethickness: 1,
                    spikecolor: 'rgba(255,255,255,0.3)'
                },
                plot_bgcolor: 'rgba(10, 15, 30, 0.4)',
                paper_bgcolor: 'transparent',
                hoverlabel: {
                    bgcolor: '#1e293b',
                    bordercolor: 'rgba(255,255,255,0.15)',
                    font: { color: '#f8fafc', size: 12, family: 'Inter, sans-serif' }
                }
            };
            
            // Clear spinner before drawing
            chartDiv.innerHTML = "";
            Plotly.newPlot(chartDiv, [trace], layout, { responsive: true, scrollZoom: true, displayModeBar: 'hover' });
        })
        .catch(err => {
            chartDiv.innerHTML = `<div class="empty-alerts">Error rendering Plotly chart context.</div>`;
            console.error(err);
        });
        
    // 2. Load Trade Recommendations
    loadTradeSignal();
}

function loadTradeSignal() {
    const panel = document.getElementById("trade-recommendation-panel");
    const badge = document.getElementById("trade-signal-badge");
    const desc = document.getElementById("trade-signal-desc");
    const entry = document.getElementById("trade-entry");
    const target = document.getElementById("trade-target");
    const stop = document.getElementById("trade-stop");
    
    if (!panel) return;
    
    fetch(`/api/trade-signal/${ACTIVE_SYMBOL}`)
        .then(res => res.json())
        .then(data => {
            badge.textContent = `${data.signal} SIGNAL`;
            desc.textContent = data.description;
            entry.textContent = data.entry_range;
            target.textContent = `$${data.target.toFixed(2)}`;
            stop.textContent = `$${data.stop_loss.toFixed(2)}`;
            
            // Update panel border glows & badge classes
            panel.className = "glass-panel trade-rec-card";
            if (data.signal === "BUY") {
                panel.classList.add("buy-signal");
                badge.className = "badge sentiment-pos";
            } else if (data.signal === "SHORT") {
                panel.classList.add("short-signal");
                badge.className = "badge sentiment-neg";
            } else {
                panel.classList.add("hold-signal");
                badge.className = "badge sentiment-neu";
                target.style.color = "var(--text-secondary)";
                stop.style.color = "var(--text-secondary)";
            }
        })
        .catch(err => console.error("Error loading trade signal:", err));
}

// -------------------- Page 2: News Intelligence --------------------
function loadNewsPage() {
    const list = document.getElementById("news-feed-list");
    const aiSummary = document.getElementById("ai-summary-bullets");
    
    if (!list) return;
    
    fetch(`/api/news/${ACTIVE_SYMBOL}`)
        .then(res => res.json())
        .then(data => {
            // Summary update
            aiSummary.innerHTML = "";
            const bullets = data.summary.split("- ").filter(b => b.trim().length > 0);
            bullets.forEach(b => {
                const li = document.createElement("li");
                li.innerHTML = b.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                aiSummary.appendChild(li);
            });
            
            // News list update
            list.innerHTML = "";
            if (data.news.length === 0) {
                list.innerHTML = `<div class="empty-alerts">No recent news available.</div>`;
                return;
            }
            
            data.news.forEach(n => {
                const item = document.createElement("div");
                const sentimentClass = n.sentiment_label === "Positive" ? "pos" : (n.sentiment_label === "Negative" ? "neg" : "neu");
                
                item.className = `news-brief-card glass-panel ${sentimentClass}`;
                item.innerHTML = `
                    <div class="news-header">
                        <span class="news-source-date">${n.source} • ${n.date}</span>
                        <span class="badge ${n.sentiment_class}">${n.sentiment_label}</span>
                    </div>
                    <h3 class="news-title">
                        <a href="${n.url}" target="_blank">${n.title}</a>
                    </h3>
                    <p class="news-desc">${n.summary}</p>
                `;
                list.appendChild(item);
            });
        });
}

// -------------------- Page 3: Investor Analysis --------------------
function loadInvestorsPage() {
    const pieCanvas = document.getElementById("holder-pie-canvas");
    if (!pieCanvas) return;
    
    // Clear spinner before drawing chart
    pieCanvas.innerHTML = "";
    
    const assetClass = document.getElementById("investors-dashboard")?.getAttribute("data-asset-class") || "stock";
    
    let values = [35, 25, 15, 12, 13];
    let labels = ['Vanguard Group Inc.', 'BlackRock Inc.', 'State Street Corp', 'Fidelity Management', 'Retail / Others'];
    
    if (assetClass === "crypto") {
        values = [34.5, 20.0, 18.0, 15.0, 12.5];
        labels = ['Staking Rewards / Retail', 'Smart Contract Reserves', 'Exchange Reserves', 'Whales / Seed Investors', 'Protocol Founders'];
    }
    
    // Draw a pie chart of top holders using mock/scraped ratios
    const data = [{
        values: values,
        labels: labels,
        type: 'pie',
        hole: 0.4,
        marker: {
            colors: ['#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe', '#1e293b']
        },
        textinfo: 'percent',
        textposition: 'outside',
        automargin: true
    }];
    
    const layout = {
        showlegend: true,
        legend: {
            font: { color: '#94a3b8', size: 11 },
            orientation: 'h',
            y: -0.1
        },
        margin: { t: 10, b: 40, l: 10, r: 10 },
        plot_bgcolor: 'transparent',
        paper_bgcolor: 'transparent',
        font: { color: '#f8fafc' }
    };
    
    Plotly.newPlot(pieCanvas, data, layout, { responsive: true, displayModeBar: false });
}

// -------------------- Page 4: Sentiment Dashboard --------------------
function loadSentimentPage() {
    const gaugeCanvas = document.getElementById("sentiment-gauge");
    const trendCanvas = document.getElementById("sentiment-trend-chart");
    if (!gaugeCanvas) return;
    
    fetch(`/api/news/${ACTIVE_SYMBOL}`)
        .then(res => res.json())
        .then(data => {
            const score = data.metrics.average; // -1 to 1
            const gaugeValue = (score + 1) * 50; // map to 0 to 100
            
            // 1. Gauge chart
            const gaugeData = [
                {
                    domain: { x: [0, 1], y: [0, 1] },
                    value: gaugeValue,
                    title: { text: "Weighted Sentiment Gauge", font: { size: 14, color: '#94a3b8' } },
                    type: "indicator",
                    mode: "gauge+number",
                    number: { font: { color: '#f8fafc' }, suffix: "%" },
                    gauge: {
                        axis: { range: [0, 100], tickwidth: 1, tickcolor: "#94a3b8" },
                        bar: { color: "#3b82f6" },
                        bgcolor: "rgba(255, 255, 255, 0.05)",
                        borderwidth: 1,
                        bordercolor: "rgba(255, 255, 255, 0.1)",
                        steps: [
                            { range: [0, 40], color: "rgba(239, 68, 68, 0.2)" },
                            { range: [40, 60], color: "rgba(100, 116, 139, 0.2)" },
                            { range: [60, 100], color: "rgba(16, 185, 129, 0.2)" }
                        ]
                    }
                }
            ];
            
            const gaugeLayout = {
                margin: { t: 40, b: 20, l: 30, r: 30 },
                plot_bgcolor: 'transparent',
                paper_bgcolor: 'transparent',
                font: { color: '#f8fafc' }
            };
            
            Plotly.newPlot(gaugeCanvas, gaugeData, gaugeLayout, { responsive: true, displayModeBar: false });
            
            // 2. Trend line chart (dummy historical comparison)
            const dates = [];
            const sentimentTrend = [];
            const priceTrend = [];
            
            const start = new Date();
            for (let i = 15; i >= 0; i--) {
                const d = new Date();
                d.setDate(start.getDate() - i);
                dates.push(d.toISOString().split("T")[0]);
                sentimentTrend.push(Math.sin(i / 2) * 0.4 + (score * 0.5));
                priceTrend.push(100 + (i * 1.5) + Math.cos(i) * 3);
            }
            
            const traceSent = {
                x: dates,
                y: sentimentTrend,
                name: 'Sentiment Score',
                type: 'scatter',
                line: { color: '#3b82f6', width: 2 }
            };
            
            const tracePrice = {
                x: dates,
                y: priceTrend,
                name: 'Asset Price ($)',
                yaxis: 'y2',
                type: 'scatter',
                line: { color: '#10b981', width: 2, dash: 'dot' }
            };
            
            const trendLayout = {
                margin: { t: 20, b: 40, l: 40, r: 40 },
                xaxis: { gridcolor: 'rgba(255,255,255,0.05)', font: { color: '#94a3b8' } },
                yaxis: { title: 'Sentiment', gridcolor: 'rgba(255,255,255,0.05)', font: { color: '#94a3b8' } },
                yaxis2: {
                    title: 'Price ($)',
                    overlaying: 'y',
                    side: 'right',
                    gridcolor: 'transparent',
                    font: { color: '#94a3b8' }
                },
                plot_bgcolor: 'transparent',
                paper_bgcolor: 'transparent',
                legend: { font: { color: '#f8fafc' }, orientation: 'h', y: -0.2 }
            };
            
            Plotly.newPlot(trendCanvas, [traceSent, tracePrice], trendLayout, { responsive: true, displayModeBar: false });
        });
}

// -------------------- Page 5: Market Network Graph --------------------
function loadNetworkPage() {
    const canvas = document.getElementById("network-canvas");
    if (!canvas) return;
    
    fetch("/api/network")
        .then(res => res.json())
        .then(data => {
            // Draw scatter correlation nodes
            const nodeX = data.nodes.map(n => n.x);
            const nodeY = data.nodes.map(n => n.y);
            const nodeLabels = data.nodes.map(n => n.label);
            const nodeSizes = data.nodes.map(n => n.size);
            const nodeColors = data.nodes.map(n => n.color);
            
            const edgeTraces = [];
            data.edges.forEach(edge => {
                edgeTraces.push({
                    x: [edge.x0, edge.x1],
                    y: [edge.y0, edge.y1],
                    mode: 'lines',
                    line: {
                        color: 'rgba(255, 255, 255, 0.08)',
                        width: edge.weight * 2
                    },
                    hoverinfo: 'none',
                    showlegend: false
                });
            });
            
            const nodeTrace = {
                x: nodeX,
                y: nodeY,
                mode: 'markers+text',
                text: nodeLabels,
                textposition: 'top center',
                hoverinfo: 'text',
                hovertext: nodeLabels.map((l, i) => `${l} Connection`),
                marker: {
                    size: nodeSizes,
                    color: nodeColors,
                    line: { color: 'rgba(255,255,255,0.2)', width: 1 }
                },
                textfont: {
                    color: '#f8fafc',
                    size: 11
                },
                name: 'Assets & Macro Factors'
            };
            
            const layout = {
                showlegend: false,
                xaxis: { showgrid: false, zeroline: false, showticklabels: false },
                yaxis: { showgrid: false, zeroline: false, showticklabels: false },
                margin: { t: 20, b: 20, l: 20, r: 20 },
                plot_bgcolor: 'transparent',
                paper_bgcolor: 'transparent'
            };
            
            Plotly.newPlot(canvas, [...edgeTraces, nodeTrace], layout, { responsive: true, displayModeBar: false });
        });
}

// -------------------- Page 6: Predictions --------------------
function loadPredictionsPage(forceRetrain = false) {
    const canvas = document.getElementById("prediction-chart-canvas");
    if (!canvas) return;
    
    // Check if we are currently on the predictions page before starting/polling
    if (ACTIVE_PAGE !== "predictions") return;

    const algorithm = document.getElementById("ml-algorithm") ? document.getElementById("ml-algorithm").value : "random_forest";
    const period = document.getElementById("train-period") ? document.getElementById("train-period").value : "3mo";
    
    let url = `/api/predictions/${ACTIVE_SYMBOL}?algorithm=${algorithm}&period=${period}`;
    if (forceRetrain) {
        url += `&force_retrain=true`;
    }

    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.status === "training") {
                canvas.innerHTML = `
                    <div class="spinner-wrapper">
                        <div class="spinner"></div>
                        <div class="loading-text">Model training has started in the background. Polling for results...</div>
                    </div>
                `;
                // Poll again in 2 seconds
                setTimeout(() => loadPredictionsPage(false), 2000);
                return;
            }
            
            canvas.innerHTML = "";
            
            const histDates = data.historical.dates;
            const histClose = data.historical.close;
            
            const futDates = data.forecast.dates;
            const futClose = data.forecast.predictions;
            const futUpper = data.forecast.upper_band;
            const futLower = data.forecast.lower_band;
            
            // Update metric fields in UI
            document.getElementById("model-accuracy").textContent = data.forecast.metrics.r2_percentage;
            document.getElementById("model-mae").textContent = `$${data.forecast.metrics.mae.toFixed(2)}`;
            
            const featureList = document.getElementById("feature-importance-list");
            featureList.innerHTML = "";
            data.forecast.feature_importances.forEach(f => {
                const li = document.createElement("li");
                li.style.display = "flex";
                li.style.justifyContent = "space-between";
                li.style.fontSize = "13px";
                li.style.marginBottom = "8px";
                li.innerHTML = `
                    <span style="color:var(--text-secondary)">${f.feature}</span>
                    <strong style="color:var(--accent-blue)">${(f.importance * 100).toFixed(1)}%</strong>
                `;
                featureList.appendChild(li);
            });
            
            // Render Prediction Chart
            const traceHist = {
                x: histDates.slice(-30), // show last 30 days
                y: histClose.slice(-30),
                name: 'Historical Price',
                type: 'scatter',
                line: { color: '#94a3b8', width: 2 }
            };
            
            const tracePred = {
                x: [histDates[histDates.length - 1], ...futDates],
                y: [histClose[histClose.length - 1], ...futClose],
                name: 'Forecast Model',
                type: 'scatter',
                line: { color: '#3b82f6', width: 2, dash: 'solid' }
            };
            
            const traceUpper = {
                x: [histDates[histDates.length - 1], ...futDates],
                y: [histClose[histClose.length - 1], ...futUpper],
                fill: null,
                type: 'scatter',
                line: { color: 'rgba(59, 130, 246, 0.1)', width: 0 },
                showlegend: false
            };
            
            const traceLower = {
                x: [histDates[histDates.length - 1], ...futDates],
                y: [histClose[histClose.length - 1], ...futLower],
                fill: 'tonexty',
                fillcolor: 'rgba(59, 130, 246, 0.08)',
                type: 'scatter',
                line: { color: 'rgba(59, 130, 246, 0.1)', width: 0 },
                name: 'Confidence Bounds'
            };
            
            const layout = {
                hovermode: 'x unified',
                margin: { t: 20, b: 40, l: 15, r: 60 },
                xaxis: { 
                    gridcolor: 'rgba(255,255,255,0.06)', 
                    gridwidth: 1,
                    showline: true,
                    linecolor: 'rgba(255,255,255,0.1)',
                    font: { color: '#94a3b8', family: 'Inter, sans-serif' },
                    showspikes: true,
                    spikemode: 'across',
                    spikesnap: 'cursor',
                    spikedash: 'dash',
                    spikethickness: 1,
                    spikecolor: 'rgba(255,255,255,0.3)'
                },
                yaxis: { 
                    side: 'right',
                    gridcolor: 'rgba(255,255,255,0.06)', 
                    gridwidth: 1,
                    showline: true,
                    linecolor: 'rgba(255,255,255,0.1)',
                    font: { color: '#94a3b8', family: 'Inter, sans-serif' },
                    showspikes: true,
                    spikemode: 'across',
                    spikesnap: 'cursor',
                    spikedash: 'dash',
                    spikethickness: 1,
                    spikecolor: 'rgba(255,255,255,0.3)'
                },
                plot_bgcolor: 'rgba(10, 15, 30, 0.4)',
                paper_bgcolor: 'transparent',
                legend: { font: { color: '#f8fafc', family: 'Inter, sans-serif' }, orientation: 'h', y: -0.2 },
                hoverlabel: {
                    bgcolor: '#1e293b',
                    bordercolor: 'rgba(255,255,255,0.15)',
                    font: { color: '#f8fafc', size: 12, family: 'Inter, sans-serif' }
                }
            };
            
            Plotly.newPlot(canvas, [traceHist, traceUpper, traceLower, tracePred], layout, { responsive: true, scrollZoom: true, displayModeBar: 'hover' });
        });
}

// -------------------- Page 7: Portfolio Analyzer --------------------
function loadPortfolioPage() {
    const listBody = document.getElementById("portfolio-list-body");
    const chartCanvas = document.getElementById("portfolio-pie-canvas");
    
    if (!listBody) return;
    
    // Load holdings
    fetch("/api/portfolio")
        .then(res => res.json())
        .then(data => {
            listBody.innerHTML = "";
            
            if (data.length === 0) {
                listBody.innerHTML = `<tr><td colspan="5" class="empty-alerts">No assets in portfolio. Add one below.</td></tr>`;
                chartCanvas.innerHTML = `<div class="empty-alerts">Add assets to view weighting.</div>`;
                updatePortfolioMetrics([]);
                return;
            }
            
            const chartData = {
                values: [],
                labels: [],
                type: 'pie',
                marker: { colors: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'] }
            };
            
            let totalValue = 0;
            let loadedCount = 0;
            const fullItems = [];
            
            data.forEach(item => {
                // Fetch current price
                fetch(`/api/market-data/${item.symbol}`)
                    .then(r => r.json())
                    .then(priceData => {
                        const currentVal = item.quantity * priceData.price;
                        totalValue += currentVal;
                        
                        const profit = (priceData.price - item.purchase_price) * item.quantity;
                        const profitPct = ((priceData.price - item.purchase_price) / item.purchase_price) * 100;
                        const profitClass = profit >= 0 ? "text-success" : "text-danger";
                        const sign = profit >= 0 ? "+" : "";
                        
                        fullItems.push({
                            ...item,
                            currentPrice: priceData.price,
                            currentVal: currentVal
                        });
                        
                        const row = document.createElement("tr");
                        row.innerHTML = `
                            <td><strong>${item.symbol}</strong><br><span style="font-size:11px;color:var(--text-muted)">${item.name}</span></td>
                            <td>${item.quantity}</td>
                            <td>$${item.purchase_price.toFixed(2)}</td>
                            <td>$${priceData.price.toFixed(2)}</td>
                            <td class="${profitClass}">${sign}$${profit.toFixed(2)} (${sign}${profitPct.toFixed(2)}%)</td>
                            <td>
                                <button class="control-btn btn-sm" onclick="removeHolding(${item.id})">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                            </td>
                        `;
                        listBody.appendChild(row);
                        
                        // Add to pie chart lists
                        chartData.values.push(currentVal);
                        chartData.labels.push(item.symbol);
                        
                        loadedCount++;
                        if (loadedCount === data.length) {
                            renderPortfolioPie(chartCanvas, chartData);
                            updatePortfolioMetrics(fullItems, totalValue);
                        }
                    });
            });
        });
        
    // Add holding form
    const form = document.getElementById("add-holding-form");
    if (form) {
        form.onsubmit = function (e) {
            e.preventDefault();
            const symbol = document.getElementById("port-symbol").value.toUpperCase();
            const qty = parseFloat(document.getElementById("port-qty").value);
            const price = parseFloat(document.getElementById("port-price").value);
            
            fetch("/api/portfolio", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ symbol: symbol, quantity: qty, purchase_price: price })
            })
            .then(res => res.json())
            .then(() => {
                form.reset();
                loadPortfolioPage();
            });
        };
    }
}

function renderPortfolioPie(canvas, chartData) {
    const layout = {
        showlegend: true,
        legend: { font: { color: '#94a3b8' } },
        margin: { t: 20, b: 20, l: 20, r: 20 },
        plot_bgcolor: 'transparent',
        paper_bgcolor: 'transparent',
        font: { color: '#f8fafc' }
    };
    Plotly.newPlot(canvas, [chartData], layout, { responsive: true, displayModeBar: false });
}

function updatePortfolioMetrics(items, totalValue) {
    const totalValEl = document.getElementById("portfolio-total-value");
    const riskEl = document.getElementById("portfolio-risk-profile");
    
    if (!totalValEl) return;
    
    if (items.length === 0) {
        totalValEl.textContent = "$0.00";
        riskEl.textContent = "N/A";
        return;
    }
    
    totalValEl.textContent = `$${totalValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    
    // Estimate portfolio beta based on asset classes
    let weightedBeta = 0;
    items.forEach(item => {
        const weight = item.currentVal / totalValue;
        const beta = item.asset_class === "crypto" ? 2.5 : 1.1; // stock beta average vs high crypto beta
        weightedBeta += weight * beta;
    });
    
    let riskLabel = "Low Risk";
    if (weightedBeta > 1.8) riskLabel = "High Speculative Risk";
    else if (weightedBeta > 1.2) riskLabel = "Moderate / Aggressive Growth";
    
    riskEl.textContent = `${riskLabel} (Beta: ${weightedBeta.toFixed(2)})`;
}

window.removeHolding = function (id) {
    fetch(`/api/portfolio/${id}`, { method: "DELETE" })
        .then(res => res.json())
        .then(() => {
            loadPortfolioPage();
        });
};
