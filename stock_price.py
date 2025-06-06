import yfinance as yf
import pandas as pd
from datetime import datetime

def get_stock_info(ticker_symbol):
    try:
        # Create a Ticker object
        stock = yf.Ticker(ticker_symbol)
        
        # Get the stock info
        info = stock.info
        
        # Get current price
        current_price = info.get('currentPrice', 'N/A')
        
        # Get 52 week low
        fifty_two_week_low = info.get('fiftyTwoWeekLow', 'N/A')
        
        return {
            'symbol': ticker_symbol,
            'current_price': current_price,
            '52_week_low': fifty_two_week_low,
            'company_name': info.get('longName', 'N/A')
        }
    except Exception as e:
        return f"Error fetching data for {ticker_symbol}: {str(e)}"

def main():
    while True:
        # Get stock symbol from user
        ticker = input("\nEnter stock symbol (e.g., AAPL, MSFT) or 'quit' to exit: ").upper()
        
        if ticker == 'QUIT':
            print("Goodbye!")
            break
            
        # Get stock information
        stock_data = get_stock_info(ticker)
        
        if isinstance(stock_data, dict):
            print(f"\nCompany: {stock_data['company_name']}")
            print(f"Current Price: ${stock_data['current_price']:.2f}")
            print(f"52 Week Low: ${stock_data['52_week_low']:.2f}")
        else:
            print(stock_data)

if __name__ == "__main__":
    main() 