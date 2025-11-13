import streamlit as st
import yfinance as yf
import requests
from io import BytesIO
from PIL import Image
import datetime
import time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Streamlit page setup ---
st.set_page_config(page_title="Cyberpunk Stock Tracker", page_icon="💹", layout="wide")

# --- Sidebar Controls ---
st.sidebar.header("⚙️ Controls")
tickers_input = st.sidebar.text_input("Enter stock tickers (comma-separated):", "AAPL, TSLA, NVDA")
period = st.sidebar.selectbox("Select time range:", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"])
refresh_rate = st.sidebar.slider("Auto-refresh interval (seconds):", 10, 300, 60)
theme_choice = st.sidebar.radio("Theme:", ["Cyberpunk Glow", "Classic Trading Chart"])

# --- Finnhub API key input (user-provided) ---
st.sidebar.subheader("🔑 API Keys")
finnhub_api = st.sidebar.text_input(
    "Finnhub API key",
    value="",
    type="password",
    help="Enter your Finnhub API key to enable company news (keeps hidden)."
)

# --- Background Image Controls ---
st.sidebar.subheader("🌅 Chart Background")
bg_choice = st.sidebar.selectbox(
    "Select Background Image:",
    ["Beach 1", "Beach 2", "Classic", "Upload Your Own"]
)
uploaded_bg = None
if bg_choice == "Upload Your Own":
    uploaded_bg = st.sidebar.file_uploader("Upload a background image", type=["jpg", "jpeg", "png"])

# --- Load Selected Background Image ---
if uploaded_bg is not None:
    bg_image = Image.open(uploaded_bg)
else:
    try:
        if bg_choice == "Beach 1":
            bg_image = Image.open("images/1.jpg")
        elif bg_choice == "Beach 2":
            bg_image = Image.open("images/2.jpg")
        else:
            bg_image = None
    except Exception:
        bg_image = None

# --- Apply Cyberpunk CSS ---
with open("cyberpunk_style_embedded.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- Title + GitHub Avatar ---
# --- Title + GitHub Avatar (Centered) ---
st.markdown("""
<div style='display:flex;justify-content:center;align-items:center;gap:15px;'>
    <img src='https://avatars.githubusercontent.com/u/34708224?s=96&v=4' width='60' style='border-radius:50%;border:2px solid #00ffff;box-shadow:0 0 10px #00ffff;'>
    <h1 class='cyberpunk-title'>CYBERPUNK QUOTES</h1>
</div>
""", unsafe_allow_html=True)
# --- Parse tickers ---
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# --- Auto-refresh setup ---
if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = time.time()
else:
    if time.time() - st.session_state["last_refresh"] > refresh_rate:
        st.session_state["last_refresh"] = time.time()
        st.rerun()

# --- Cached data functions ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker, period):
    return yf.Ticker(ticker).history(period=period)

@st.cache_data(ttl=3600)
def get_info_cached(ticker):
    return yf.Ticker(ticker).get_info()

@st.cache_data(ttl=1800)
def get_company_news(symbol, api_key):
    if not api_key:
        return []
    FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/company-news"
    today = datetime.date.today()
    past = today - datetime.timedelta(days=30)
    params = {"symbol": symbol, "from": past.isoformat(), "to": today.isoformat(), "token": api_key}
    try:
        response = requests.get(FINNHUB_NEWS_URL, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [item for item in data if item.get("headline") and item.get("url")]
        return []
    except Exception:
        return []

# --- Main Dashboard ---
for ticker in tickers:
    try:
        info = get_info_cached(ticker)
        hist = get_stock_data(ticker, period)

        if hist.empty:
            st.warning(f"No data available for {ticker}")
            continue

        # Company Header
        logo_url = info.get("logo_url")
        if not logo_url:
            domain = info.get("website", "").replace("https://", "").replace("http://", "").split("/")[0]
            if domain:
                logo_url = f"https://logo.clearbit.com/{domain}"

        col1, col2 = st.columns([1, 4])
        with col1:
            if logo_url:
                try:
                    r = requests.get(logo_url, timeout=5)
                    if r.status_code == 200:
                        st.image(Image.open(BytesIO(r.content)), width=100)
                except:
                    pass
        with col2:
            st.markdown(f"### {info.get('shortName', ticker)}")
            st.caption(f"{info.get('sector', 'N/A')} | {info.get('industry', 'N/A')}")

        # Chart Rendering
        if theme_choice == "Cyberpunk Glow":
            import matplotlib.pyplot as plt
            import mplcyberpunk
            plt.style.use("cyberpunk")
            fig, ax = plt.subplots(figsize=(10,5))
            if bg_image is not None:
                ax.imshow(bg_image, extent=[
                    hist.index.min(), hist.index.max(),
                    hist["Close"].min(), hist["Close"].max()
                ], aspect='auto', alpha=0.25, zorder=0)
            ax.plot(hist.index, hist["Close"], label=ticker, linewidth=2, zorder=2)
            ax.set_title(f"{ticker} Stock Price ({period})", fontsize=14)
            ax.set_xlabel("Date")
            ax.set_ylabel("Price ($)")
            plt.legend()
            mplcyberpunk.add_glow_effects()
            st.pyplot(fig)
        else:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7,0.3])
            fig.add_trace(go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name='Price',
                increasing_line_color='green',
                decreasing_line_color='red'
            ), row=1, col=1)
            fig.add_trace(go.Bar(
                x=hist.index,
                y=hist['Volume'],
                name='Volume',
                marker_color='blue',
                opacity=0.3
            ), row=2, col=1)
            fig.update_layout(
                template='plotly_white',
                title=f"{ticker} Classic Trading Chart",
                xaxis=dict(rangeslider_visible=False),
                height=700,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig, use_container_width=True)

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        price = info.get("currentPrice")
        cap = info.get("marketCap")
        high = info.get("fiftyTwoWeekHigh")
        low = info.get("fiftyTwoWeekLow")
        with col1: st.metric("Current Price", f"${price:,.2f}" if price else "N/A")
        with col2: st.metric("Market Cap", f"${cap:,.0f}" if cap else "N/A")
        with col3: st.metric("52w High / Low", f"${high} / ${low}")
        with col4:
            hist_5d = get_stock_data(ticker, "5d")
            if len(hist_5d) >= 2:
                change = hist_5d["Close"].iloc[-1] - hist_5d["Close"].iloc[-2]
                pct = (change / hist_5d["Close"].iloc[-2]) * 100
                st.metric("Daily Change", f"${change:.2f}", f"{pct:.2f}%")

        # --- Collapsible Company Info (Cyberpunk Glow) ---
        summary = info.get("longBusinessSummary", "No company description available.")
        if summary and summary.strip():
            st.markdown("""
                <style>
                /* Cyberpunk Glow Expander */
                div[data-testid="stExpander"] {
                    border: 1px solid #00ffff !important;
                    border-radius: 10px !important;
                    box-shadow: 0 0 15px #00ffff80;
                    background-color: rgba(0, 20, 30, 0.6) !important;
                }
                div[data-testid="stExpander"] > div:first-child {
                    color: #00f5ff !important;
                    font-weight: bold !important;
                    font-size: 1rem !important;
                    text-shadow: 0 0 8px #00ffff;
                }
                </style>
            """, unsafe_allow_html=True)

            with st.expander("📘 Company Info (click to expand)"):
                st.write(summary)
        else:
            st.info("No company description available.")

        st.markdown("---")

        # News
        st.subheader(f"📰 {ticker} Recent News")
        if not finnhub_api:
            st.info("Enter your Finnhub API key in the sidebar to enable company news.")
            news = []
        else:
            news = get_company_news(ticker, finnhub_api)
        if news:
            for article in news[:5]:
                dt = datetime.datetime.fromtimestamp(article.get("datetime", 0))
                t_str = dt.strftime("%b %d, %Y")
                st.markdown(
                    f"<div class='news-card'><a href='{article.get('url')}' target='_blank'><b>{article.get('headline')}</b></a><br><small>{article.get('source', 'Unknown')} | {t_str}</small></div>",
                    unsafe_allow_html=True
                )
        else:
            if finnhub_api:
                st.info("No recent news available.")

        st.markdown("<hr style='border: 1px solid #00f5ff; opacity: 0.3;'>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Could not load info for {ticker}: {e}")
