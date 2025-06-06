# Stock Price Tracker

A Streamlit web application that tracks stock prices and shows 52-week high/low analysis for multiple stocks.

## Features
- Real-time stock price tracking
- Multiple stock symbol support (comma-separated)
- 52-week high and low analysis
- Percentage calculations from highs and lows
- Support for major US stocks

## Demo
You can access the live demo at: [https://us-stock-insights.streamlit.app/]

## Local Development

1. Clone the repository:
```bash
git clone [your-repo-url]
cd [your-repo-name]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the app:
```bash
streamlit run app.py
```

## Deployment
This app is deployed on Streamlit Community Cloud. To deploy your own version:

1. Fork this repository
2. Sign up at [share.streamlit.io](https://share.streamlit.io)
3. Deploy your forked repository
4. Add your Alpha Vantage API key in the Streamlit secrets

## Environment Variables
The app requires an Alpha Vantage API key. You can get one for free at [Alpha Vantage](https://www.alphavantage.co/support/#api-key).

## Contributing
Feel free to open issues or submit pull requests.

## License
MIT License
