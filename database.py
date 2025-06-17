import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import json

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_ANON_KEY"]
        supabase: Client = create_client(supabase_url, supabase_key)
        return supabase
    except:
        return None

# Cache stock data to reduce API calls
def cache_stock_data(supabase, symbol, stock_data):
    if not supabase:
        return
    
    try:
        data = {
            "symbol": symbol,
            "current_price": stock_data['current_price'],
            "week_52_low": stock_data['52_week_low'],
            "week_52_high": stock_data['52_week_high'],
            "company_name": stock_data['company_name'],
            "updated_at": datetime.now().isoformat()
        }
        
        # Insert or update stock data
        result = supabase.table("stock_cache").upsert(data, on_conflict="symbol").execute()
        return result
    except Exception as e:
        st.error(f"Error caching data: {e}")

# Get cached stock data (if recent)
def get_cached_stock_data(supabase, symbol, max_age_minutes=15):
    if not supabase:
        return None
    
    try:
        # Get data updated within the last 15 minutes
        cutoff_time = (datetime.now() - timedelta(minutes=max_age_minutes)).isoformat()
        
        result = supabase.table("stock_cache").select("*").eq("symbol", symbol).gte("updated_at", cutoff_time).execute()
        
        if result.data:
            data = result.data[0]
            return {
                'symbol': data['symbol'],
                'current_price': data['current_price'],
                '52_week_low': data['week_52_low'],
                '52_week_high': data['week_52_high'],
                'company_name': data['company_name']
            }
        return None
    except Exception as e:
        st.error(f"Error retrieving cached data: {e}")
        return None

# Save user watchlist
def save_watchlist(supabase, user_id, watchlist):
    if not supabase:
        return False
    
    try:
        data = {
            "user_id": user_id,
            "watchlist": json.dumps(watchlist),
            "updated_at": datetime.now().isoformat()
        }
        
        result = supabase.table("user_watchlists").upsert(data, on_conflict="user_id").execute()
        return True
    except Exception as e:
        st.error(f"Error saving watchlist: {e}")
        return False

# Get user watchlist
def get_watchlist(supabase, user_id):
    if not supabase:
        return []
    
    try:
        result = supabase.table("user_watchlists").select("watchlist").eq("user_id", user_id).execute()
        
        if result.data:
            return json.loads(result.data[0]['watchlist'])
        return []
    except Exception as e:
        st.error(f"Error retrieving watchlist: {e}")
        return []

# Get popular stocks (most queried)
def get_popular_stocks(supabase, limit=10):
    if not supabase:
        return []
    
    try:
        result = supabase.table("stock_cache").select("symbol, company_name").order("updated_at", desc=True).limit(limit).execute()
        return [{"symbol": item["symbol"], "name": item["company_name"]} for item in result.data]
    except Exception as e:
        return [] 