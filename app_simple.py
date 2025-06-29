import streamlit as st
import requests
from datetime import datetime
import time
from database import init_supabase, cache_stock_data, get_cached_stock_data, save_watchlist, get_watchlist, get_popular_stocks
import uuid

st.set_page_config(page_title="Stock Price Tracker", page_icon="📈", layout="wide")

# Initialize session state first (before any other code that uses it)
if 'api_key' not in st.session_state:
    # Don't try to get API key from secrets if it's a placeholder
    try:
        secret_key = st.secrets.get("ALPHA_VANTAGE_API_KEY", "")
        if secret_key and secret_key != "your_api_key_here":
            st.session_state.api_key = secret_key
        else:
            st.session_state.api_key = None
    except:
        st.session_state.api_key = None

if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if 'processed_stocks' not in st.session_state:
    st.session_state.processed_stocks = []

if 'download_counter' not in st.session_state:
    st.session_state.download_counter = 0

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
    .rate-limit-warning {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #ffc107;
        margin: 15px 0;
    }
    .countdown-timer {
        background-color: #f8d7da;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #dc3545;
        margin: 20px 0;
        text-align: center;
        font-size: 1.2em;
        font-weight: bold;
    }
    .batch-info {
        background-color: #d1ecf1;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #17a2b8;
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
st.markdown("Get real-time stock prices and 52-week high/low analysis - Smart Rate Limiting")

# Show API key warning prominently if not configured
if not st.session_state.api_key:
    st.error("""
    🔑 **Alpha Vantage API Key Required**
    
    To use this app, you need a free Alpha Vantage API key:
    
    1. **Get your free API key**: [Click here to register](https://www.alphavantage.co/support/#api-key)
    2. **Enter the key** in the sidebar under "🔧 Configuration"
    3. **Start tracking stocks** for free!
    
    The free tier includes 25 requests per day and 5 requests per minute.
    """)
    
    st.info("💡 **Tip**: Registration takes less than 1 minute and gives you instant access to real-time stock data!")

# Initialize database connection
supabase = init_supabase()

def get_stock_info(ticker_symbol):
    if not st.session_state.api_key:
        return {'symbol': ticker_symbol, 'status': 'error', 'error': 'API key not configured'}
    
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
        
        # Check for API errors first
        if "Error Message" in quote_data:
            return {'symbol': ticker_symbol, 'status': 'error', 'error': quote_data['Error Message']}
        
        if "Note" in quote_data:
            return {'symbol': ticker_symbol, 'status': 'rate_limit', 'error': f"Rate limit: {quote_data['Note']}"}
            
        if "Information" in quote_data:
            return {'symbol': ticker_symbol, 'status': 'rate_limit', 'error': f"API Info: {quote_data['Information']}"}
        
        if "Global Quote" in quote_data and quote_data["Global Quote"]:
            global_quote = quote_data["Global Quote"]
            
            # Check if price data exists
            price_key = "05. price"
            if price_key not in global_quote:
                return {'symbol': ticker_symbol, 'status': 'error', 'error': 'Price data not available'}
            
            current_price = float(global_quote[price_key])
            
            # Get Company Overview for the name
            overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker_symbol}&apikey={st.session_state.api_key}"
            overview_response = requests.get(overview_url)
            overview_data = overview_response.json()
            
            if "Error Message" in overview_data:
                company_name = ticker_symbol
            else:
                company_name = overview_data.get("Name", ticker_symbol)
            
            # Get Weekly Adjusted Time Series for 52-week high/low
            weekly_url = f"https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol={ticker_symbol}&apikey={st.session_state.api_key}"
            weekly_response = requests.get(weekly_url)
            weekly_data = weekly_response.json()
            
            if "Error Message" in weekly_data:
                return {'symbol': ticker_symbol, 'status': 'error', 'error': weekly_data['Error Message']}
            
            if "Note" in weekly_data:
                return {'symbol': ticker_symbol, 'status': 'rate_limit', 'error': f"Rate limit: {weekly_data['Note']}"}
                
            if "Information" in weekly_data:
                return {'symbol': ticker_symbol, 'status': 'rate_limit', 'error': f"API Info: {weekly_data['Information']}"}
            
            if "Weekly Adjusted Time Series" in weekly_data:
                time_series = weekly_data["Weekly Adjusted Time Series"]
                
                # Get data from the last 52 weeks
                highs = []
                lows = []
                count = 0
                for date in sorted(time_series.keys(), reverse=True):
                    if count < 52:  # Only look at last 52 weeks
                        lows.append(float(time_series[date]["3. low"]))
                        highs.append(float(time_series[date]["2. high"]))
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
                else:
                    return {'symbol': ticker_symbol, 'status': 'error', 'error': 'Could not calculate 52-week range'}
            else:
                return {'symbol': ticker_symbol, 'status': 'error', 'error': 'No historical data available'}
        else:
            return {'symbol': ticker_symbol, 'status': 'error', 'error': 'No quote data available'}
        
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
        if stock_data.get('status') == 'rate_limit':
            st.error(f"🛑 Rate limit reached for {stock_data['symbol']}: {stock_data.get('error', 'Rate limit exceeded')}")
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
            status_icon = "🛑" if stock.get('status') == 'rate_limit' else "❌"
            summary_data.append({
                'Symbol': stock['symbol'],
                'Company': 'N/A',
                'Current Price': 'N/A',
                '52W Low': 'N/A',
                '52W High': 'N/A',
                'Above Low %': 'N/A',
                'Below High %': 'N/A',
                'Status': f"{status_icon} {stock.get('error', 'Error')}"
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
    
    # Increment download counter for unique key
    st.session_state.download_counter += 1
    
    st.download_button(
        label="📥 Download Summary as CSV",
        data=csv_content,
        file_name=f"stock_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        key=f"download_csv_{st.session_state.download_counter}"
    )

def countdown_timer(seconds, message):
    """Display a countdown timer"""
    countdown_placeholder = st.empty()
    
    for remaining in range(seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        countdown_placeholder.markdown(f"""
        <div class='countdown-timer'>
            ⏳ {message}<br/>
            <span style='font-size: 2em; color: #dc3545;'>{mins:02d}:{secs:02d}</span><br/>
            <small>Waiting for API rate limit reset...</small>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(1)
    
    countdown_placeholder.empty()

def process_stocks_with_rate_limiting(tickers):
    """Process stocks in batches respecting API rate limits"""
    BATCH_SIZE = 5
    WAIT_TIME = 60  # 1 minute between batches
    
    # Clear previous results
    st.session_state.processed_stocks = []
    
    # Check daily limit warning
    if len(tickers) > 25:
        st.warning(f"""
        ⚠️ **Daily Limit Warning**
        
        You're requesting {len(tickers)} symbols, but Alpha Vantage free tier only allows **25 requests per day**.
        
        **Recommendation**: 
        - Process only your most important 25 stocks today
        - Consider upgrading to a paid plan for higher limits
        - Or spread your requests across multiple days
        """)
    
    # Split tickers into batches
    batches = [tickers[i:i + BATCH_SIZE] for i in range(0, len(tickers), BATCH_SIZE)]
    
    # Display batch information
    if len(batches) > 1:
        st.markdown(f"""
        <div class='rate-limit-warning'>
            ⚠️ <strong>Rate Limit Management</strong><br/>
            Processing {len(tickers)} symbols in {len(batches)} batch(es) of {BATCH_SIZE} stocks each.<br/>
            There will be a 1-minute wait between batches to respect Alpha Vantage's 5 calls/minute limit.<br/>
            <strong>Daily limit: {len(tickers)} of 25 requests will be used today.</strong>
        </div>
        """, unsafe_allow_html=True)
    
    total_processed = 0
    
    for batch_num, batch_tickers in enumerate(batches, 1):
        # Display batch info
        st.markdown(f"""
        <div class='batch-info'>
            📦 <strong>Processing Batch {batch_num} of {len(batches)}</strong><br/>
            Symbols: {', '.join(batch_tickers)}
        </div>
        """, unsafe_allow_html=True)
        
        # Create progress tracking for this batch
        batch_progress = st.progress(0)
        batch_status = st.empty()
        
        # Process each stock in the current batch
        for i, ticker in enumerate(batch_tickers):
            # Update progress
            progress = (i + 1) / len(batch_tickers)
            batch_progress.progress(progress)
            batch_status.markdown(f"<div class='processing-status'>🔄 Processing {ticker} ({i+1}/{len(batch_tickers)} in batch {batch_num})</div>", unsafe_allow_html=True)
            
            # Fetch stock data
            stock_data = get_stock_info(ticker)
            
            # Check for rate limit error and stop processing immediately
            if stock_data and stock_data.get('status') == 'rate_limit':
                st.session_state.processed_stocks.append(stock_data)
                batch_progress.empty()
                batch_status.empty()
                
                st.error(f"""
                🛑 **Processing Stopped - API Rate Limit Reached**
                
                **Error on symbol**: {ticker}
                **Error message**: {stock_data.get('error', 'Rate limit exceeded')}
                
                **What happened**: Alpha Vantage API rate limit has been exceeded.
                
                **Next steps**:
                1. Wait for the rate limit to reset (usually 1 minute)
                2. Try again with fewer symbols
                3. Consider upgrading to a paid Alpha Vantage plan for higher limits
                
                **Processed so far**: {total_processed} out of {len(tickers)} symbols
                """)
                
                # Display summary of what was processed so far
                if st.session_state.processed_stocks:
                    st.markdown("### 📊 Partial Results (Before Rate Limit)")
                    summary_data = create_summary_list(st.session_state.processed_stocks)
                    if summary_data:
                        display_summary_table(summary_data)
                
                return  # Stop all processing immediately
            
            # Store result
            st.session_state.processed_stocks.append(stock_data)
            total_processed += 1
            
            # Display individual result
            if stock_data:
                display_stock_info(stock_data)
            
            # Add delay between requests within batch (12 seconds to be safe)
            if i < len(batch_tickers) - 1:
                time.sleep(12)
        
        # Clear batch progress
        batch_progress.empty()
        batch_status.markdown(f"<div class='processing-status'>✅ Batch {batch_num} Complete! ({len(batch_tickers)} stocks processed)</div>", unsafe_allow_html=True)
        
        # Wait between batches (except for the last batch)
        if batch_num < len(batches):
            st.markdown(f"""
            <div class='rate-limit-warning'>
                🕐 <strong>Rate Limit Break</strong><br/>
                Completed batch {batch_num} of {len(batches)}. Waiting 1 minute before processing next batch...
            </div>
            """, unsafe_allow_html=True)
            
            countdown_timer(WAIT_TIME, f"Next batch ({batch_num + 1}/{len(batches)}) starts in:")
    
    # Final completion message
    st.markdown(f"""
    <div class='processing-status'>
        🎉 <strong>All Processing Complete!</strong><br/>
        Successfully processed {total_processed} stocks across {len(batches)} batch(es).
    </div>
    """, unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🔧 Configuration")

# API Key configuration - make it prominent
st.sidebar.markdown("### 🔑 Alpha Vantage API Key")
if not st.session_state.api_key:
    st.sidebar.error("⚠️ API Key Required")
    st.sidebar.markdown("""
    **Get your free API key:**
    1. [Register here](https://www.alphavantage.co/support/#api-key)
    2. Copy your API key
    3. Paste it below
    """)
    api_key = st.sidebar.text_input(
        "Enter your API key:", 
        type="password",
        placeholder="Paste your Alpha Vantage API key here"
    )
    if api_key:
        st.session_state.api_key = api_key
        st.sidebar.success("✅ API Key saved!")
        st.rerun()
else:
    st.sidebar.success("✅ API Key configured!")
    if st.sidebar.button("🔄 Change API Key"):
        st.session_state.api_key = None
        st.rerun()

# Database status
if supabase:
    st.sidebar.success("Database connected! ✅")
else:
    st.sidebar.warning("Database not connected (optional)")

# Rate limit info
st.sidebar.title("⏱️ Rate Limit Info")
st.sidebar.info("""
**Alpha Vantage Free Tier:**
- 5 calls per minute
- 25 calls per day

**Smart Processing:**
- Batches of 5 stocks
- 1-minute wait between batches
- 12-second delay between stocks
- **Auto-stops on rate limit errors**
""")

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
col1, col2 = st.columns([4, 1])

with col1:
    ticker_input = st.text_input(
        "Enter stock symbols (comma-separated, e.g., AAPL, MSFT, GOOGL):", 
        value=getattr(st.session_state, 'ticker_input', 'AAPL, MSFT, GOOGL, AMZN, META'),
        key='main_input'
    ).upper().strip()

with col2:
    st.markdown("<br/>", unsafe_allow_html=True)  # Add spacing to align with input
    fetch_button = st.button("📊 Fetch Data", type="primary", use_container_width=True)

# Update session state when input changes
if ticker_input != getattr(st.session_state, 'ticker_input', ''):
    st.session_state.ticker_input = ticker_input

# Add some example stocks with their full names
st.markdown("""
#### Example input (5 stocks - conservative for daily limit):
AAPL, MSFT, GOOGL, AMZN, META

#### ⚠️ Daily Limit: 25 requests per day (Free tier)

#### Popular symbols:
- AAPL (Apple Inc.)
- MSFT (Microsoft Corporation)
- GOOGL (Alphabet Inc.)
- AMZN (Amazon.com Inc.)
- META (Meta Platforms Inc.)
- TSLA (Tesla Inc.)
- NVDA (NVIDIA Corporation)
- JPM (JPMorgan Chase & Co.)
- NFLX (Netflix Inc.)
- DIS (The Walt Disney Company)

💡 **Tip**: With 25 daily requests, focus on your most important stocks!
""")

# Only process when the fetch button is clicked
if fetch_button and ticker_input and st.session_state.api_key:
    # Split and clean the input
    tickers = [t.strip() for t in ticker_input.split(',') if t.strip()]
    
    if len(tickers) > 0:
        # Display processing plan
        batch_count = (len(tickers) + 4) // 5  # Ceiling division
        estimated_time = (batch_count - 1) * 60 + len(tickers) * 12  # Wait time + processing time
        
        st.markdown(f"""
        ### 📊 Processing Plan
        - **Total Symbols**: {len(tickers)}
        - **Batches**: {batch_count} (max 5 symbols per batch)
        - **Estimated Time**: ~{estimated_time // 60} minutes {estimated_time % 60} seconds
        """)
        
        # Process stocks with intelligent rate limiting
        process_stocks_with_rate_limiting(tickers)
        
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

elif fetch_button and not st.session_state.api_key:
    st.error("⚠️ Please enter your Alpha Vantage API key in the sidebar before fetching data.")

elif fetch_button and not ticker_input:
    st.warning("⚠️ Please enter at least one stock symbol before fetching data.")

# Display previous results if they exist (without the fetch button being clicked)
elif st.session_state.processed_stocks and not fetch_button:
    st.markdown("### 📋 Previous Results")
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
    
    st.info("💡 Click 'Fetch Data' button to update with current symbols or get fresh data.")

# Add footer
st.markdown("---")
st.markdown("Data provided by Alpha Vantage API | Database: Supabase") 