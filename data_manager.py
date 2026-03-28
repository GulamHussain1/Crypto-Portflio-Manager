import urllib.request
import json
import csv
from datetime import datetime
import concurrent.futures
import time
import os # Add this import

HEADERS = [
    'crypto_name', 'symbol', 'date_time', 
    'open_price', 'high_price', 'low_price', 
    'close_price', 'volume', 'market_cap'
]

# Create the data directory if it doesn't exist
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# Point the CSV filename to the data folder
CSV_FILENAME = os.path.join(DATA_DIR, 'crypto_365d_history.csv')

# ... (The rest of your fetching logic remains exactly the same) ...
# Added "cg_id" to automate the CoinGecko API fetch
TARGET_COINS = [
    {"name": "Bitcoin", "symbol": "BTCUSDT", "cg_id": "bitcoin"},
    {"name": "Ethereum", "symbol": "ETHUSDT", "cg_id": "ethereum"},
    {"name": "Solana", "symbol": "SOLUSDT", "cg_id": "solana"},
    {"name": "Ripple", "symbol": "XRPUSDT", "cg_id": "ripple"}
]

def fetch_historical_data(coin):
    """
    Fetches OHLCV from Binance and Market Cap from CoinGecko, 
    then merges them perfectly by Date.
    """
    crypto_name = coin["name"]
    symbol_pair = coin["symbol"]
    cg_id = coin["cg_id"]
    
    print(f"Starting automated data merge for {crypto_name}...")
    
    # The two API endpoints
    binance_url = f"https://api.binance.com/api/v3/klines?symbol={symbol_pair}&interval=1d&limit=365"
    cg_url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart?vs_currency=usd&days=365&interval=daily"
    
    try:
        # --- 1. Fetch Market Cap from CoinGecko ---
        req_cg = urllib.request.Request(cg_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_cg) as response:
            cg_data = json.loads(response.read().decode())
            
        # Create a dictionary to easily look up market cap by date (YYYY-MM-DD)
        market_cap_dict = {}
        for item in cg_data['market_caps']:
            date_str = datetime.fromtimestamp(item[0] / 1000.0).strftime('%Y-%m-%d')
            market_cap_dict[date_str] = item[1]

        # --- 2. Fetch OHLCV from Binance ---
        req_binance = urllib.request.Request(binance_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_binance) as response:
            binance_data = json.loads(response.read().decode())
            
        csv_rows = []
        
        # --- 3. Merge the Data ---
        for day in binance_data:
            timestamp_ms = day[0]
            date_time = datetime.fromtimestamp(timestamp_ms / 1000.0).strftime('%Y-%m-%d')
            
            open_price = float(day[1])
            high_price = float(day[2])
            low_price = float(day[3])
            close_price = float(day[4])
            volume = float(day[5])
            
            # Look up the exact market cap for this specific date
            # If for some reason CoinGecko missed a day, default to 0
            market_cap = market_cap_dict.get(date_time, 0)
            
            csv_rows.append([
                crypto_name, symbol_pair, date_time, 
                open_price, high_price, low_price, 
                close_price, volume, market_cap
            ])
            
        print(f"✓ Successfully merged and processed {crypto_name}")
        
        # Small sleep to prevent hitting CoinGecko's free tier rate limits
        time.sleep(1) 
        return csv_rows

    except Exception as e:
        print(f"Error fetching {crypto_name}: {e}")
        return []

def gather_all_data_in_parallel():
    all_data_rows = []
    # We use max_workers=2 here to be gentle on CoinGecko's free public API
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = executor.map(fetch_historical_data, TARGET_COINS)
        for result_rows in results:
            all_data_rows.extend(result_rows)
    return all_data_rows

def save_to_csv(data_rows):
    with open(CSV_FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerows(data_rows)
    print(f"\nSaved {len(data_rows)} fully automated rows to {CSV_FILENAME}")

if __name__ == "__main__":
    master_dataset = gather_all_data_in_parallel()
    if master_dataset:
        save_to_csv(master_dataset)