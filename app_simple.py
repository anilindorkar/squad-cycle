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
    .processing-status {
        background-color: #f0f8ff;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #1976d2;
        margin: 10px 0;
    }
    .summary-table {
        margin-top: 30px;
    }
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    .status-processing {
        color: #ffc107;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# Title and description
st.title("📈 Stock Price Tracker")
st.markdown("Get real-time stock prices and 52-week high/low analysis - Processing one by one")

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

if 'processed_stocks' not in st.session_state:
    st.session_state.processed_stocks = []

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
                        'company_name': company_name,
                        'status': 'success'
                    }
                    
                    # Cache the data
                    cache_stock_data(supabase, ticker_symbol, stock_data)
                    
                    return stock_data
        
        return {'symbol': ticker_symbol, 'status': 'error', 'error': 'No data available'}
        
    except Exception as e:
        return {'symbol': ticker_symbol, 'status': 'error', 'error': str(e)}

def display_stock_info(stock_data):
    if stock_data and stock_data.get('status') == 'success':
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
    else:
        st.error(f"❌ Failed to fetch data for {stock_data['symbol']}: {stock_data.get('error', 'Unknown error')}")

def create_summary_list(processed_stocks):
    """Create a summary list of all processed stocks"""
    if not processed_stocks:
        return []
    
    summary_data = []
    for stock in processed_stocks:
        if stock.get('status') == 'success':
            diff_low_percent = ((stock['current_price'] - stock['52_week_low']) / stock['52_week_low']) * 100
            diff_high_percent = ((stock['current_price'] - stock['52_week_high']) / stock['52_week_high']) * 100
            
            summary_data.append({
                'Symbol': stock['symbol'],
                'Company': stock['company_name'],
                'Current Price': f"${stock['current_price']:.2f}",
                '52W Low': f"${stock['52_week_low']:.2f}",
                '52W High': f"${stock['52_week_high']:.2f}",
                'Above Low %': f"{diff_low_percent:.1f}%",
                'Below High %': f"{abs(diff_high_percent):.1f}%",
                'Status': '✅ Success'
            })
        else:
            summary_data.append({
                'Symbol': stock['symbol'],
                'Company': 'N/A',
                'Current Price': 'N/A',
                '52W Low': 'N/A',
                '52W High': 'N/A',
                'Above Low %': 'N/A',
                'Below High %': 'N/A',
                'Status': f"❌ {stock.get('error', 'Error')}"
            })
    
    return summary_data

def display_summary_table(summary_data):
    """Display summary data as a simple table"""
    if not summary_data:
        return
    
    # Create header
    st.markdown("### 📋 Summary Results")
    
    # Display as a simple table using markdown
    headers = ['Symbol', 'Company', 'Current Price', '52W Low', '52W High', 'Above Low %', 'Below High %', 'Status']
    
    # Create markdown table
    table_md = "| " + " | ".join(headers) + " |\n"
    table_md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    
    for row in summary_data:
        table_md += "| " + " | ".join([str(row[header]) for header in headers]) + " |\n"
    
    st.markdown(table_md)
    
    # Create CSV content for download
    csv_content = ",".join(headers) + "\n"
    for row in summary_data:
        csv_content += ",".join([f'"{str(row[header])}"' for header in headers]) + "\n"
    
    st.download_button(
        label="📥 Download Summary as CSV",
        data=csv_content,
        file_name=f"stock_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

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

# Processing controls
st.sidebar.title("⚙️ Processing Controls")
if st.sidebar.button("Clear Results"):
    st.session_state.processed_stocks = []
    st.rerun()

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
            st.rerun()
    
    # Add to watchlist
    new_symbol = st.sidebar.text_input("Add symbol to watchlist:").upper()
    if st.sidebar.button("Add to Watchlist") and new_symbol:
        if new_symbol not in current_watchlist:
            current_watchlist.append(new_symbol)
            if save_watchlist(supabase, st.session_state.user_id, current_watchlist):
                st.sidebar.success(f"Added {new_symbol}!")
                st.rerun()
    
    # Clear watchlist
    if current_watchlist and st.sidebar.button("Clear Watchlist"):
        save_watchlist(supabase, st.session_state.user_id, [])
        st.rerun()

# Popular stocks
if supabase:
    st.sidebar.title("🔥 Popular Stocks")
    popular = get_popular_stocks(supabase, 5)
    if popular:
        for stock in popular:
            if st.sidebar.button(f"{stock['symbol']} - {stock['name'][:20]}...", key=f"pop_{stock['symbol']}"):
                st.session_state.ticker_input = stock['symbol']
                st.rerun()

# Main input
ticker_input = st.text_input(
    "Enter stock symbols (comma-separated, e.g., AAPL, MSFT, GOOGL):", 
    value=getattr(st.session_state, 'ticker_input', 'AAPL, MSFT, GOOGL, AMZN, META, TSLA, NVDA'),
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
    
    # Clear previous results
    st.session_state.processed_stocks = []
    
    # Create progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Process each ticker one by one
    for i, ticker in enumerate(tickers):
        # Update progress
        progress = (i + 1) / len(tickers)
        progress_bar.progress(progress)
        status_text.markdown(f"<div class='processing-status'>🔄 Processing {ticker} ({i+1}/{len(tickers)})</div>", unsafe_allow_html=True)
        
        # Fetch stock data
        stock_data = get_stock_info(ticker)
        
        # Store result
        st.session_state.processed_stocks.append(stock_data)
        
        # Display individual result
        if stock_data:
            display_stock_info(stock_data)
        
        # Add delay between requests to respect API limits (only if not cached)
        if i < len(tickers) - 1:  # Don't delay after the last request
            time.sleep(12)  # 12-second delay between stocks to stay within rate limits
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.markdown("<div class='processing-status'>✅ Processing Complete!</div>", unsafe_allow_html=True)
    
    # Create and display summary table
    if st.session_state.processed_stocks:
        summary_data = create_summary_list(st.session_state.processed_stocks)
        
        if summary_data:
            display_summary_table(summary_data)
            
            # Show statistics
            successful_count = len([s for s in st.session_state.processed_stocks if s.get('status') == 'success'])
            failed_count = len(st.session_state.processed_stocks) - successful_count
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Processed", len(st.session_state.processed_stocks))
            with col2:
                st.metric("Successful", successful_count)
            with col3:
                st.metric("Failed", failed_count)
    
    # Add note about data freshness
    st.info("Note: Data is refreshed every minute during market hours. Cached data is used when available to reduce API calls.")

# Add footer
st.markdown("---")
st.markdown("Data provided by Alpha Vantage API | Database: Supabase") 