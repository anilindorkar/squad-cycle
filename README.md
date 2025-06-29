# Stock Price Tracker

A Streamlit web application that tracks stock prices and shows 52-week high/low analysis for multiple stocks with database integration.

## Features
- Real-time stock price tracking
- Multiple stock symbol support (comma-separated)
- 52-week high and low analysis
- Percentage calculations from highs and lows
- User watchlists with persistence
- Data caching to reduce API calls
- Popular stocks tracking
- Support for major US stocks

## Demo
You can access the live demo at: [https://us-stock-insights.streamlit.app/]

## Database Integration
This app uses Supabase (PostgreSQL) for:
- **Stock Data Caching**: Reduces API calls by caching recent data
- **User Watchlists**: Save and manage your favorite stocks
- **Popular Stocks**: Track most-viewed stocks

## Setup Instructions

### 1. Local Development

1. Clone the repository:
```bash
git clone [your-repo-url]
cd [your-repo-name]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
   - Get Alpha Vantage API key: [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
   - Set up Supabase project: [Supabase](https://supabase.com)
   - Create `.streamlit/secrets.toml` with your credentials

4. Set up database tables:
   - Run the SQL commands from `database_setup.sql` in your Supabase SQL editor

5. Run the app:
```bash
1. Basic
streamlit run app.py
2. Advanced
python -m streamlit run app_simple.py
```

### 2. Free Database Setup (Supabase)

1. **Create Supabase Account**:
   - Go to [supabase.com](https://supabase.com)
   - Sign up for free (500MB storage, 2GB bandwidth/month)

2. **Create a New Project**:
   - Create new project
   - Wait for database setup (2-3 minutes)

3. **Set Up Database Tables**:
   - Go to SQL Editor in your Supabase dashboard
   - Copy and run the commands from `database_setup.sql`

4. **Get Credentials**:
   - Go to Settings → API
   - Copy your `URL` and `anon` key

5. **Add to Secrets**:
   ```toml
   ALPHA_VANTAGE_API_KEY = "your_alpha_vantage_key"
   SUPABASE_URL = "your_supabase_url"
   SUPABASE_ANON_KEY = "your_supabase_anon_key"
   ```

### 3. Alternative Free Database Options

#### MongoDB Atlas (NoSQL)
- **Free tier**: 512MB storage
- **Setup**: [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- **Use case**: Document-based storage

#### Neon (PostgreSQL)
- **Free tier**: 3GB storage
- **Setup**: [Neon](https://neon.tech)
- **Use case**: Modern PostgreSQL with branching

#### PlanetScale (MySQL)
- **Free tier**: 5GB storage
- **Setup**: [PlanetScale](https://planetscale.com)
- **Use case**: Serverless MySQL

## Deployment on Streamlit Cloud

1. **Push to GitHub**:
```bash
git add .
git commit -m "Deploy to Streamlit"
git push origin main
```

2. **Deploy on Streamlit**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Add secrets in the app settings

3. **Add Secrets**:
   - In Streamlit Cloud app settings
   - Add your API keys and database credentials

## App Features

### Stock Analysis
- Current price
- 52-week high/low range
- Percentage above 52-week low
- Percentage below 52-week high
- Price analysis summary

### Watchlist Management
- Add stocks to personal watchlist
- Quick load watchlist symbols
- Persistent storage across sessions

### Performance Optimization
- Data caching (15-minute refresh)
- Reduced API calls
- Popular stocks tracking

## API Limits
- Alpha Vantage free tier: 5 calls/minute, 500 calls/day
- App automatically caches data to minimize API usage
- Supports up to 5 stocks per query

## Contributing
Feel free to open issues or submit pull requests.

## License
MIT License
