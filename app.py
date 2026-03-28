from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os # Add this import
import csv
import json
import data_manager # Imports the fetcher script we wrote earlier
import urllib.request
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os
import time
import math
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' 

# Point to the new database location
DB_PATH = os.path.join('data', 'users.db')

def get_db_connection():
    # Update the connection to use DB_PATH
    conn = sqlite3.connect(DB_PATH) 
    conn.row_factory = sqlite3.Row
    return conn

# ... (The rest of your routes remain exactly the same) ...

@app.route('/')
def index():
    """The default home route."""
    # If the user is already logged in, send them straight to the dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    # Otherwise, make the login page the default destination
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Hash the password for security
        hashed_pw = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                         (username, email, hashed_pw))
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists. Please use a different one.', 'error')
        finally:
            conn.close()
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        # Verify user exists and password matches the hash
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear the session to log the user out
    session.clear()
    return redirect(url_for('login'))

def load_dashboard_data():
    """Reads the CSV and calculates KPIs and Chart Data."""
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if not os.path.exists(filepath):
        return None
    
    chart_data = {}
    dates = []
    start_prices = {}
    current_prices = {}
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            coin = row['crypto_name']
            date = row['date_time']
            price = float(row['close_price'])
            
            if coin not in chart_data:
                chart_data[coin] = []
                start_prices[coin] = price # Store the first price we see
                
            chart_data[coin].append(price)
            current_prices[coin] = price # Constantly updates, leaving the latest price
            
            if coin == 'Bitcoin' and date not in dates:
                dates.append(date)

    # 1. Calculate KPI: Total Cryptos
    total_cryptos = len(chart_data.keys())

    # 2. Calculate KPI: Highest Return
    highest_return_coin = "None"
    highest_return_pct = 0
    for coin in chart_data.keys():
        pct_change = ((current_prices[coin] - start_prices[coin]) / start_prices[coin]) * 100
        if pct_change > highest_return_pct:
            highest_return_pct = pct_change
            highest_return_coin = coin

    return {
        'dates': dates, 
        'prices': chart_data,
        'kpi_total_cryptos': total_cryptos,
        'kpi_highest_return_coin': highest_return_coin,
        'kpi_highest_return_pct': round(highest_return_pct, 2)
    }

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    data = load_dashboard_data()
    
    # Mock data for the Risk modules we haven't built yet
    risk_data = {
        'distribution': [40, 35, 25], # Low, Medium, High Risk %
        'mix_scatter': [{'x': 12, 'y': 8}, {'x': 18, 'y': 15}, {'x': 25, 'y': 22}, {'x': 8, 'y': 4}] # Risk vs Return
    }
    
    return render_template('dashboard.html', 
                           username=session['username'],
                           dashboard_data=json.dumps(data) if data else None,
                           risk_data=json.dumps(risk_data),
                           raw_data=data) # Pass raw dict for easy HTML rendering

# --- Investment Mix Calculator Logic ---

# --- Investment Mix Calculator Logic ---

def rule_based_allocation(amount, risk_profile):
    """
    Pure Python math to calculate investment spreads based on risk rules.
    """
    amount = float(amount)
    mix = {}
    percentages = {} # NEW: We need to store the percentages for the UI
    
    # Rule Set 1: Conservative (Capital Preservation)
    if risk_profile == 'conservative':
        percentages = {'Bitcoin': 70, 'Ethereum': 20, 'Solana': 5, 'Ripple': 5}
        expected_return = "8% - 12%"
        risk_score = 3.2
        
    # Rule Set 2: Balanced (Growth with some protection)
    elif risk_profile == 'balanced':
        percentages = {'Bitcoin': 40, 'Ethereum': 30, 'Solana': 15, 'Ripple': 15}
        expected_return = "15% - 25%"
        risk_score = 5.5
        
    # Rule Set 3: Aggressive (Maximum Yield)
    elif risk_profile == 'aggressive':
        percentages = {'Bitcoin': 20, 'Ethereum': 30, 'Solana': 25, 'Ripple': 25}
        expected_return = "30% - 50%"
        risk_score = 8.1
        
    else:
        return None

    # Calculate exact dollar amounts based on the percentages
    for coin, pct in percentages.items():
        mix[coin] = amount * (pct / 100.0)

    return {
        "allocations": mix,
        "percentages": percentages, # <--- THIS IS WHAT WAS MISSING!
        "total": amount,
        "expected_return": expected_return,
        "risk_score": risk_score,
        "profile": risk_profile.capitalize()
    }

@app.route('/investment-mix', methods=['GET', 'POST'])
def investment_mix():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    calculated_plan = None
    
    if request.method == 'POST':
        investment_amount = request.form.get('amount')
        risk_level = request.form.get('risk_level')
        
        if investment_amount and risk_level:
            calculated_plan = rule_based_allocation(investment_amount, risk_level)
            # NEW: Save the generated plan to the user's session
            session['last_plan'] = calculated_plan 
            
    return render_template('investment_mix.html', 
                           username=session['username'],
                           plan=calculated_plan)


# --- Portfolio Simulator Logic ---

def simulate_portfolio(amount, allocations):
    """
    Backtests a portfolio mix using the 365-day historical CSV data.
    allocations is a dict: e.g., {'Bitcoin': 40, 'Ethereum': 30, 'Solana': 20, 'Ripple': 10}
    """
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if not os.path.exists(filepath):
        return None
        
    history = {'Bitcoin': [], 'Ethereum': [], 'Solana': [], 'Ripple': []}
    dates = []
    
    # 1. Load the historical data
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            coin = row['crypto_name']
            if coin in history:
                history[coin].append(float(row['close_price']))
                # Use Bitcoin's timeline as our master date list
                if coin == 'Bitcoin':
                    dates.append(row['date_time'])
                    
    # Ensure we have data
    if not dates: return None

    # 2. "Buy" the assets on Day 0
    amount = float(amount)
    coin_holdings = {} # How many actual coins we own
    
    for coin in history.keys():
        if len(history[coin]) > 0:
            day_1_price = history[coin][0]
            # Calculate dollar amount allocated to this coin
            usd_allocated = amount * (float(allocations.get(coin, 0)) / 100.0)
            # Calculate how many coins that buys
            coin_holdings[coin] = usd_allocated / day_1_price
        else:
            coin_holdings[coin] = 0

    # 3. Track the portfolio value day-by-day
    daily_portfolio_values = []
    
    for i in range(len(dates)):
        daily_total = 0
        for coin in history.keys():
            # Multiply the coins we own by that day's specific price
            if i < len(history[coin]):
                daily_total += coin_holdings[coin] * history[coin][i]
        
        daily_portfolio_values.append(daily_total)

    final_value = daily_portfolio_values[-1]
    profit_loss = final_value - amount
    roi_percent = (profit_loss / amount) * 100

    return {
        'dates': dates,
        'values': daily_portfolio_values,
        'initial': amount,
        'final': final_value,
        'pnl': profit_loss,
        'roi': roi_percent
    }

@app.route('/simulator', methods=['GET', 'POST'])
def simulator():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    simulation_results = None
    
    if request.method == 'POST':
        # Safely grab amount, default to 10000 if empty
        amount = request.form.get('amount')
        if not amount: amount = 10000
        
        # Helper function to prevent crashes if a box is left empty
        def safe_float(val):
            try: return float(val)
            except (ValueError, TypeError): return 0.0

        # Grab the percentages safely
        allocations = {
            'Bitcoin': safe_float(request.form.get('btc_pct')),
            'Ethereum': safe_float(request.form.get('eth_pct')),
            'Solana': safe_float(request.form.get('sol_pct')),
            'Ripple': safe_float(request.form.get('xrp_pct'))
        }
        
        total_pct = sum(allocations.values())
        
        if total_pct == 100:
            simulation_results = simulate_portfolio(amount, allocations)
        else:
            flash(f'Error: Allocations must equal exactly 100%. Yours equaled {total_pct}%.', 'error')
            
    return render_template('portfolio_simulator.html', 
                           username=session['username'],
                           results=simulation_results)


#--------- price forecast



# --- Machine Learning Price Forecast Logic ---

def predict_future_price(coin_name, days_ahead):
    """
    Pure Python Linear Regression (Least Squares Method).
    Predicts the future price based on the last 365 days of trend data.
    """
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if not os.path.exists(filepath):
        return None

    # 1. Gather historical prices for the specific coin
    historical_prices = []
    historical_dates = []
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['crypto_name'] == coin_name:
                historical_prices.append(float(row['close_price']))
                historical_dates.append(row['date_time'])

    if not historical_prices:
        return None

    # 2. Prepare the X (Days) and Y (Prices) variables
    n = len(historical_prices)
    # X will just be day 1, 2, 3... 365
    x = list(range(1, n + 1)) 
    y = historical_prices

    # 3. Calculate the core components for Linear Regression math
    sum_x = sum(x)
    sum_y = sum(y)
    sum_x_squared = sum([i**2 for i in x])
    sum_xy = sum([x[i] * y[i] for i in range(n)])

    # 4. Calculate Slope (m) and Y-Intercept (b) 
    # Formula: m = (n*Σ(xy) - Σx*Σy) / (n*Σ(x^2) - (Σx)^2)
    denominator = (n * sum_x_squared) - (sum_x ** 2)
    
    # Safety check to avoid division by zero if data is perfectly flat
    if denominator == 0: 
        slope = 0
    else:
        slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator
        
    intercept = (sum_y - (slope * sum_x)) / n

    # 5. Make the Prediction
    # We want to predict the price 'days_ahead' from now
    target_day_x = n + int(days_ahead)
    predicted_price = (slope * target_day_x) + intercept
    
    # Ensure prediction doesn't go below $0 (crypto can't have a negative price)
    if predicted_price < 0:
        predicted_price = 0.0

    current_price = historical_prices[-1]
    expected_change = ((predicted_price - current_price) / current_price) * 100

    # Generate data points for the trendline so Chart.js can draw it
    trendline = [(slope * i) + intercept for i in x]
    
    # Add the future predicted points to the line
    future_trendline = trendline.copy()
    for i in range(1, int(days_ahead) + 1):
        future_trendline.append((slope * (n + i)) + intercept)

    return {
        'coin': coin_name,
        'days_ahead': days_ahead,
        'current_price': current_price,
        'predicted_price': predicted_price,
        'expected_change': expected_change,
        'historical_prices': historical_prices,
        'trendline': future_trendline, # Includes past trend + future prediction
        'dates': historical_dates # We'll let JS handle adding the future dates for simplicity
    }

@app.route('/forecast', methods=['GET', 'POST'])
def forecast():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    prediction = None
    
    if request.method == 'POST':
        selected_coin = request.form.get('coin')
        days_to_predict = request.form.get('days')
        
        if selected_coin and days_to_predict:
            prediction = predict_future_price(selected_coin, days_to_predict)
            
    return render_template('price_forecast.html', 
                           username=session['username'],
                           prediction=prediction)








@app.route('/fetch-data', methods=['POST'])
def fetch_data():
    """Triggered by the 'Sync Data' button."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Run the parallel fetcher
    dataset = data_manager.gather_all_data_in_parallel()
    if dataset:
        data_manager.save_to_csv(dataset)
        flash('Market data successfully updated!', 'success')
    else:
        flash('Error fetching data. Check your connection.', 'error')
        
    return redirect(url_for('dashboard'))


@app.route('/live-market')
def live_market():
    """Serves the Live Market HTML page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    return render_template('live_market.html', username=session['username'])

@app.route('/api/live-prices')
def api_live_prices():
    """Hidden route that fetches real-time data from Binance."""
    # Binance allows us to fetch multiple specific symbols at once to save time
    symbols = '["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT"]'
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbols={symbols}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            raw_data = json.loads(response.read().decode())
            
        # Format the data cleanly for our frontend
        name_map = {"BTCUSDT": "Bitcoin", "ETHUSDT": "Ethereum", "SOLUSDT": "Solana", "XRPUSDT": "Ripple"}
        live_data = []
        
        for item in raw_data:
            live_data.append({
                "name": name_map[item['symbol']],
                "symbol": item['symbol'].replace('USDT', ''), # Show 'BTC' instead of 'BTCUSDT'
                "price": float(item['lastPrice']),
                "change_pct": float(item['priceChangePercent']),
                "high": float(item['highPrice']),
                "low": float(item['lowPrice']),
                "volume": float(item['volume'])
            })
            
        return {"status": "success", "data": live_data}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
# --- Reports & Data Export Logic ---

@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Check if our database CSV exists and get its stats
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    file_exists = os.path.exists(filepath)
    
    if file_exists:
        # Get the time the file was last updated and format it cleanly
        raw_time = os.path.getmtime(filepath)
        last_updated = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(raw_time))
        # Calculate file size in Kilobytes
        file_size_kb = round(os.path.getsize(filepath) / 1024, 1)
    else:
        last_updated = "N/A"
        file_size_kb = 0

    return render_template('reports.html', 
                           username=session['username'],
                           file_exists=file_exists,
                           last_updated=last_updated,
                           file_size=file_size_kb)

@app.route('/download/market-data')
def download_market_data():
    """Forces the browser to download the CSV file."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    
    if os.path.exists(filepath):
        # as_attachment=True tells the browser to download it, not open it
        return send_file(filepath, as_attachment=True, download_name='crypto_market_history_365d.csv')
    else:
        flash('Report not found. Please go to the Dashboard and Sync Data first.', 'error')
        return redirect(url_for('reports'))

@app.route('/download/forecast-summary')
def download_forecast_summary():
    """Generates a real-time CSV report combining current prices and AI predictions."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if not os.path.exists(filepath):
        flash('No market data available. Sync first.', 'error')
        return redirect(url_for('reports'))

    # 1. Gather historical prices to find the latest daily change
    coin_data = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            coin = row['crypto_name']
            if coin not in coin_data:
                coin_data[coin] = []
            coin_data[coin].append(float(row['close_price']))

    report_data = []

    # 2. Loop through every coin and calculate the exact metrics from the screenshot
    for coin, prices in coin_data.items():
        if len(prices) < 2:
            continue
            
        latest_price = prices[-1]
        prev_price = prices[-2]
        
        # Calculate standard 24h daily change %
        daily_change_pct = ((latest_price - prev_price) / prev_price) * 100
        
        # Run our ML model to predict 1 day into the future
        prediction = predict_future_price(coin, 1)
        
        # The screenshot shows the prediction formatted as a raw decimal (e.g., -0.02443 instead of -2.44%)
        pred_decimal = (prediction['expected_change'] / 100.0) if prediction else 0.0

        # Format it exactly like the Excel screenshot
        report_data.append({
            'crypto_name': coin.lower(),
            'latest_price': round(latest_price, 2),
            'predicted': round(pred_decimal, 5),
            'latest_daily_change_%': round(daily_change_pct, 6)
        })

    # 3. Write the calculated data to a new CSV file
    out_filepath = os.path.join('data', 'forecast_summary.csv')
    with open(out_filepath, 'w', newline='') as f:
        fieldnames = ['crypto_name', 'latest_price', 'predicted', 'latest_daily_change_%']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_data)

    # Force the browser to download the freshly made file
    return send_file(out_filepath, as_attachment=True, download_name='ml_forecast_summary.csv')    



# --- Risk Analysis Logic ---

def calculate_risk_metrics(coin_name):
    """
    Pure Python calculator for Volatility and Maximum Drawdown.
    """
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if not os.path.exists(filepath):
        return None
        
    prices = []
    dates = []
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['crypto_name'] == coin_name:
                prices.append(float(row['close_price']))
                dates.append(row['date_time'])
                
    if not prices or len(prices) < 2:
        return None

    # 1. Calculate Daily Returns
    daily_returns = []
    for i in range(1, len(prices)):
        pct_change = (prices[i] - prices[i-1]) / prices[i-1]
        daily_returns.append(pct_change)
        
    # 2. Calculate Volatility (Standard Deviation of returns)
    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_return)**2 for r in daily_returns) / len(daily_returns)
    daily_volatility = math.sqrt(variance)
    
    # Annualize the volatility (Standard math is daily * sqrt(365))
    annual_volatility = daily_volatility * math.sqrt(365) * 100 
    
    # 3. Calculate Maximum Drawdown (How far it fell from its All-Time High)
    running_max = prices[0]
    drawdowns = [0.0] # Day 1 has 0 drawdown
    
    for i in range(1, len(prices)):
        price = prices[i]
        if price > running_max:
            running_max = price
            
        # Calculate percentage drop from the highest peak seen so far
        drawdown_pct = ((price - running_max) / running_max) * 100
        drawdowns.append(drawdown_pct)
        
    max_drawdown = min(drawdowns) # This will be a negative number

    # 4. Assign a Risk Grade
    if annual_volatility < 40: grade = "Low Risk (Grade A)"
    elif annual_volatility < 65: grade = "Moderate Risk (Grade B)"
    elif annual_volatility < 90: grade = "High Risk (Grade C)"
    else: grade = "Extreme Risk (Grade D)"

    return {
        'coin': coin_name,
        'annual_volatility': annual_volatility,
        'max_drawdown': max_drawdown,
        'grade': grade,
        'dates': dates,
        'drawdowns': drawdowns # We send this list to JS to draw the chart
    }

@app.route('/risk-analysis', methods=['GET', 'POST'])
def risk_analysis():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    analysis = None
    
    if request.method == 'POST':
        selected_coin = request.form.get('coin')
        if selected_coin:
            analysis = calculate_risk_metrics(selected_coin)
            
    return render_template('risk_analysis.html', 
                           username=session['username'],
                           analysis=analysis)


@app.route('/download/strategy-pdf')
def download_strategy_pdf():
    """Generates a print-optimized PDF view of the strategy."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    plan = session.get('last_plan')
    
    if not plan:
        flash('Please calculate an Investment Mix first to generate a Strategy PDF.', 'error')
        return redirect(url_for('reports'))
        
    return render_template('strategy_pdf.html', 
                           username=session['username'], 
                           plan=plan, 
                           date=time.strftime('%B %d, %Y'))



# --- Settings & Email Alert Logic ---

def send_risk_alert_email(sender_email, sender_password, recipient_email, coin, drop_pct, grade):
    """
    Pure Python Email Engine using smtplib.
    Now uses dynamic credentials passed from the Settings UI.
    """
    # Safety check to ensure credentials exist
    if not sender_email or not sender_password:
        return False 

    message = MIMEMultipart("alternative")
    message["Subject"] = f"⚠️ SYSTEM ALERT: {coin} Risk Threshold Breached"
    message["From"] = sender_email
    message["To"] = recipient_email

    # Create the HTML version of your message
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f5; padding: 20px;">
        <div style="background-color: #ffffff; padding: 20px; border-radius: 8px; border-top: 4px solid #ef4444;">
            <h2 style="color: #111827;">Crypto Manager Risk Alert</h2>
            <p style="color: #4b5563;">Your automated system has detected a critical market movement.</p>
            
            <div style="background-color: #fee2e2; padding: 15px; border-radius: 6px; margin: 20px 0;">
                <h3 style="color: #b91c1c; margin-top: 0;">{coin} Alert</h3>
                <ul style="color: #991b1b; font-weight: bold;">
                    <li>Maximum Drawdown: {drop_pct}%</li>
                    <li>Current Risk Grade: {grade}</li>
                </ul>
            </div>
            
            <p style="color: #4b5563; font-size: 14px;">Log in to your dashboard immediately to review your portfolio strategy and adjust your allocations.</p>
        </div>
      </body>
    </html>
    """
    
    message.attach(MIMEText(html, "html"))

    try:
        # Securely connect to Gmail's SMTP server
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Default settings (Now including email fields)
    if 'risk_threshold' not in session:
        session['risk_threshold'] = 20.0 
        session['alerts_enabled'] = True
        session['sender_email'] = ""
        session['sender_password'] = ""

    if request.method == 'POST':
        # Handle the form update
        if 'update_settings' in request.form:
            session['risk_threshold'] = float(request.form.get('threshold', 20.0))
            session['alerts_enabled'] = request.form.get('alerts_enabled') == 'on'
            session['sender_email'] = request.form.get('sender_email', '')
            session['sender_password'] = request.form.get('sender_password', '')
            flash('System preferences updated successfully.', 'success')
            
        # Handle the "Test Alert" button
        elif 'test_alert' in request.form:
            if not session['alerts_enabled']:
                flash('Please enable alerts before testing.', 'error')
            elif not session.get('sender_email') or not session.get('sender_password'):
                flash('Please configure your Sender Email and App Password first.', 'error')
            else:
                # Get the user's email from the database
                conn = get_db_connection()
                user = conn.execute('SELECT email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
                conn.close()
                
                user_email = user['email']
                
                test_coin = "Bitcoin"
                test_drop = -25.5
                test_grade = "High Risk"
                
                # Pass the dynamic session credentials into the email function
                success = send_risk_alert_email(
                    session['sender_email'], 
                    session['sender_password'], 
                    user_email, test_coin, test_drop, test_grade
                )
                
                if success:
                    flash(f'Test alert dispatched to {user_email}.', 'success')
                else:
                    flash('Failed to send email. Check your App Password or terminal for SMTP errors.', 'error')

    return render_template('settings.html', 
                           username=session['username'],
                           threshold=session['risk_threshold'],
                           alerts_enabled=session['alerts_enabled'],
                           sender_email=session.get('sender_email', ''),
                           sender_password=session.get('sender_password', ''))
if __name__ == '__main__':
    app.run(debug=True,port=8900)