import streamlit as st
import requests
from datetime import datetime
import time
from database import init_supabase, cache_stock_data, get_cached_stock_data, save_watchlist, get_watchlist, get_popular_stocks
import uuid

st.set_page_config(page_title="Stock Price Tracker", page_icon="📈", layout="wide")

# Add custom CSS
st.markdown("""
    <style>
    .main {
        padding: 20px;
    }
    .metric-row {
        margin-bottom: 20px;
    }
    .stock-divider {
        margin: 30px 0;
        border-bottom: 2px solid #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)

# Title and description
st.title("📈 Stock Price Tracker")
st.markdown("Get real-time stock prices and 52-week high/low analysis for multiple stocks")

# Initialize database connection
supabase = init_supabase()

# Initialize session state
if 'api_key' not in st.session_state:
    # Try to get API key from secrets first
    try:
        st.session_state.api_key = st.secrets["ALPHA_VANTAGE_API_KEY"]
    except:
        st.session_state.api_key = None

if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

def get_stock_info(ticker_symbol):
    if not st.session_state.api_key:
        st.error("""
        Please enter your Alpha Vantage API key. You can get a free API key at:
        https://www.alphavantage.co/support/#api-key
        
        It's free and takes just a minute to register!
        """)
        return None
    
    # Try to get cached data first
    cached_data = get_cached_stock_data(supabase, ticker_symbol)
    if cached_data:
        st.info(f"📊 Using cached data for {ticker_symbol} (updated within last 15 minutes)")
        return cached_data
        
    try:
        # Get Global Quote
        quote_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker_symbol}&apikey={st.session_state.api_key}"
        quote_response = requests.get(quote_url)
        quote_data = quote_response.json()
        
        if "Global Quote" in quote_data and quote_data["Global Quote"]:
            current_price = float(quote_data["Global Quote"]["05. price"])
            
            # Get Company Overview for the name
            overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker_symbol}&apikey={st.session_state.api_key}"
            overview_response = requests.get(overview_url)
            overview_data = overview_response.json()
            
            company_name = overview_data.get("Name", ticker_symbol)
            
            # Get Weekly Adjusted Time Series for 52-week high/low
            weekly_url = f"https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol={ticker_symbol}&apikey={st.session_state.api_key}"
            weekly_response = requests.get(weekly_url)
            weekly_data = weekly_response.json()
            
            if "Weekly Adjusted Time Series" in weekly_data:
                # Get data from the last 52 weeks
                highs = []
                lows = []
                count = 0
                for date in sorted(weekly_data["Weekly Adjusted Time Series"].keys(), reverse=True):
                    if count < 52:  # Only look at last 52 weeks
                        lows.append(float(weekly_data["Weekly Adjusted Time Series"][date]["3. low"]))
                        highs.append(float(weekly_data["Weekly Adjusted Time Series"][date]["2. high"]))
                        count += 1
                    else:
                        break
                
                fifty_two_week_low = min(lows) if lows else None
                fifty_two_week_high = max(highs) if highs else None
                
                if fifty_two_week_low and fifty_two_week_high:
                    stock_data = {
                        'symbol': ticker_symbol,
                        'current_price': current_price,
                        '52_week_low': fifty_two_week_low,
                        '52_week_high': fifty_two_week_high,
                        'company_name': company_name
                    }
                    
                    # Cache the data
                    cache_stock_data(supabase, ticker_symbol, stock_data)
                    
                    return stock_data
        
        return None
        
    except Exception as e:
        st.error(f"Error details for {ticker_symbol}: {str(e)}")
        return None

def display_stock_info(stock_data):
    if stock_data:
        # Display company name in a header
        st.subheader(f"📊 {stock_data['company_name']} ({stock_data['symbol']})")
        
        # First row: Current Price
        st.metric("Current Price", f"${stock_data['current_price']:.2f}")
        
        # Second row: 52 Week Range
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("52 Week Low", f"${stock_data['52_week_low']:.2f}")
        with col2:
            st.metric("52 Week High", f"${stock_data['52_week_high']:.2f}")
        
        # Third row: Performance Metrics
        col1, col2 = st.columns(2)
        
        with col1:
            # Calculate how far above 52-week low
            diff_low = stock_data['current_price'] - stock_data['52_week_low']
            diff_low_percent = (diff_low / stock_data['52_week_low']) * 100
            st.metric(
                "Above 52W Low", 
                f"{diff_low_percent:.1f}%",
                delta=f"${diff_low:.2f}"
            )
        
        with col2:
            # Calculate how far below 52-week high
            diff_high = stock_data['current_price'] - stock_data['52_week_high']
            diff_high_percent = (diff_high / stock_data['52_week_high']) * 100
            st.metric(
                "Below 52W High", 
                f"{abs(diff_high_percent):.1f}%",
                delta=f"-${abs(diff_high):.2f}",
                delta_color="inverse"
            )
        
        # Add analysis section
        st.markdown("### 📈 Price Analysis")
        st.markdown(f"""
        - Current price is **${stock_data['current_price']:.2f}**
        - **{diff_low_percent:.1f}%** above 52-week low of ${stock_data['52_week_low']:.2f}
        - **{abs(diff_high_percent):.1f}%** below 52-week high of ${stock_data['52_week_high']:.2f}
        """)
        
        # Add divider
        st.markdown("<div class='stock-divider'></div>", unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🔧 Configuration")

# API Key configuration
if not st.session_state.api_key:
    api_key = st.sidebar.text_input("Enter Alpha Vantage API Key:", type="password")
    if api_key:
        st.session_state.api_key = api_key
else:
    st.sidebar.success("API Key configured! ✅")

# Database status
if supabase:
    st.sidebar.success("Database connected! ✅")
else:
    st.sidebar.warning("Database not connected (optional)")

# Watchlist management
st.sidebar.title("📝 Watchlist")
if supabase:
    current_watchlist = get_watchlist(supabase, st.session_state.user_id)
    
    if current_watchlist:
        st.sidebar.subheader("Your Watchlist:")
        watchlist_str = ", ".join(current_watchlist)
        st.sidebar.write(watchlist_str)
        
        if st.sidebar.button("Load Watchlist"):
            st.session_state.ticker_input = watchlist_str
            st.experimental_rerun()
    
    # Add to watchlist
    new_symbol = st.sidebar.text_input("Add symbol to watchlist:").upper()
    if st.sidebar.button("Add to Watchlist") and new_symbol:
        if new_symbol not in current_watchlist:
            current_watchlist.append(new_symbol)
            if save_watchlist(supabase, st.session_state.user_id, current_watchlist):
                st.sidebar.success(f"Added {new_symbol}!")
                st.experimental_rerun()
    
    # Clear watchlist
    if current_watchlist and st.sidebar.button("Clear Watchlist"):
        save_watchlist(supabase, st.session_state.user_id, [])
        st.experimental_rerun()

# Popular stocks
if supabase:
    st.sidebar.title("🔥 Popular Stocks")
    popular = get_popular_stocks(supabase, 5)
    if popular:
        for stock in popular:
            if st.sidebar.button(f"{stock['symbol']} - {stock['name'][:20]}...", key=f"pop_{stock['symbol']}"):
                st.session_state.ticker_input = stock['symbol']
                st.experimental_rerun()

# Main input
ticker_input = st.text_input(
    "Enter stock symbols (comma-separated, e.g., AAPL, MSFT, GOOGL):", 
    value=getattr(st.session_state, 'ticker_input', ''),
    key='main_input'
).upper().strip()

# Update session state when input changes
if ticker_input != getattr(st.session_state, 'ticker_input', ''):
    st.session_state.ticker_input = ticker_input

# Add some example stocks with their full names
st.markdown("""
#### Example input:
AAPL, MSFT, GOOGL

#### Available symbols:
- AAPL (Apple Inc.)
- MSFT (Microsoft Corporation)
- GOOGL (Alphabet Inc.)
- AMZN (Amazon.com Inc.)
- META (Meta Platforms Inc.)
- TSLA (Tesla Inc.)
- NVDA (NVIDIA Corporation)
- JPM (JPMorgan Chase & Co.)
""")

if ticker_input and st.session_state.api_key:
    # Split and clean the input
    tickers = [t.strip() for t in ticker_input.split(',') if t.strip()]
    
    if len(tickers) > 5:
        st.warning("⚠️ Due to API limits, please enter 5 or fewer symbols at a time.")
        tickers = tickers[:5]
    
    # Process each ticker
    for i, ticker in enumerate(tickers):
        # Show a spinner while loading data
        with st.spinner(f'Fetching data for {ticker} ({i+1}/{len(tickers)})...'):
            stock_data = get_stock_info(ticker)
            
            if stock_data:
                display_stock_info(stock_data)
            else:
                st.error(f"""Could not fetch data for {ticker}. Please verify that:
1. The stock symbol is correct (e.g., 'AAPL' for Apple Inc.)
2. You have entered a valid API key
3. You haven't exceeded the API rate limit (5 calls per minute for free tier)""")
            
            # Add delay between requests to respect API limits (only if not cached)
            if i < len(tickers) - 1:  # Don't delay after the last request
                time.sleep(12)  # 12-second delay between stocks to stay within rate limits
    
    # Add note about data freshness
    st.info("Note: Data is refreshed every minute during market hours. Cached data is used when available to reduce API calls.")

# Add footer
st.markdown("---")
st.markdown("Data provided by Alpha Vantage API | Database: Supabase") 