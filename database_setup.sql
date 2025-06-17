-- SQL commands to run in Supabase SQL editor
-- Create these tables after setting up your Supabase project

-- Table to cache stock data and reduce API calls
CREATE TABLE IF NOT EXISTS stock_cache (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    current_price DECIMAL(10,2) NOT NULL,
    week_52_low DECIMAL(10,2) NOT NULL,
    week_52_high DECIMAL(10,2) NOT NULL,
    company_name VARCHAR(200),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to store user watchlists
CREATE TABLE IF NOT EXISTS user_watchlists (
    id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL,
    watchlist TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_stock_cache_symbol ON stock_cache(symbol);
CREATE INDEX IF NOT EXISTS idx_stock_cache_updated_at ON stock_cache(updated_at);
CREATE INDEX IF NOT EXISTS idx_user_watchlists_user_id ON user_watchlists(user_id);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE stock_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_watchlists ENABLE ROW LEVEL SECURITY;

-- Allow public read access to stock_cache
CREATE POLICY "Allow public read access" ON stock_cache FOR SELECT USING (true);
CREATE POLICY "Allow public insert/update" ON stock_cache FOR ALL USING (true);

-- Allow users to manage their own watchlists
CREATE POLICY "Users can manage own watchlists" ON user_watchlists FOR ALL USING (true); 