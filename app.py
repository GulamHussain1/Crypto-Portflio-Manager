from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import csv
import json
import data_manager
import urllib.request
import time
import math
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' 

DB_PATH = os.path.join('data', 'users.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH) 
    conn.row_factory = sqlite3.Row
    return conn

# --- AUTH & DASHBOARD ROUTES ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
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
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def load_dashboard_data():
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if not os.path.exists(filepath): return None
    
    chart_data = {}
    dates = []
    start_prices = {}
    current_prices = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            coin = row.get('crypto_name', '').strip().capitalize()
            date = row.get('date_time', '')
            try: price = float(row.get('close_price', 0))
            except: continue
            
            if coin not in chart_data:
                chart_data[coin] = []
                start_prices[coin] = price
                
            chart_data[coin].append(price)
            current_prices[coin] = price
            
            if coin == 'Bitcoin' and date not in dates:
                dates.append(date)

    if not chart_data: return None
    
    total_cryptos = len(chart_data.keys())
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
    if 'user_id' not in session: return redirect(url_for('login'))
    data = load_dashboard_data()
    risk_data = {'distribution': [40, 35, 25], 'mix_scatter': [{'x': 12, 'y': 8}, {'x': 18, 'y': 15}, {'x': 25, 'y': 22}, {'x': 8, 'y': 4}]}
    return render_template('dashboard.html', username=session['username'], dashboard_data=json.dumps(data) if data else None, risk_data=json.dumps(risk_data), raw_data=data)

# --- INVESTMENT MIX ---

def rule_based_allocation(amount, risk_profile):
    amount = float(amount)
    mix = {}
    percentages = {}
    
    if risk_profile == 'conservative':
        percentages = {'Bitcoin': 70, 'Ethereum': 20, 'Solana': 5, 'Ripple': 5}
        expected_return = "8% - 12%"
        risk_score = 3.2
    elif risk_profile == 'balanced':
        percentages = {'Bitcoin': 40, 'Ethereum': 30, 'Solana': 15, 'Ripple': 15}
        expected_return = "15% - 25%"
        risk_score = 5.5
    elif risk_profile == 'aggressive':
        percentages = {'Bitcoin': 20, 'Ethereum': 30, 'Solana': 25, 'Ripple': 25}
        expected_return = "30% - 50%"
        risk_score = 8.1
    else: return None

    for coin, pct in percentages.items():
        mix[coin] = amount * (pct / 100.0)

    return {"allocations": mix, "percentages": percentages, "total": amount, "expected_return": expected_return, "risk_score": risk_score, "profile": risk_profile.capitalize()}

@app.route('/investment-mix', methods=['GET', 'POST'])
def investment_mix():
    if 'user_id' not in session: return redirect(url_for('login'))
    calculated_plan = None
    if request.method == 'POST':
        investment_amount = request.form.get('amount')
        risk_level = request.form.get('risk_level')
        if investment_amount and risk_level:
            calculated_plan = rule_based_allocation(investment_amount, risk_level)
            session['last_plan'] = calculated_plan 
    return render_template('investment_mix.html', username=session['username'], plan=calculated_plan)

# --- PORTFOLIO SIMULATOR ---

def simulate_portfolio(amount, allocations):
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if not os.path.exists(filepath): return None
        
    history = {'Bitcoin': [], 'Ethereum': [], 'Solana': [], 'Ripple': []}
    dates = []
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Bulletproof dynamic column finder
            csv_coin, price, date = "", None, ""
            for k, v in row.items():
                if not k: continue
                k_clean = k.strip().lower()
                if k_clean in ['crypto_name', 'name', 'coin', 'id']: csv_coin = str(v).strip().lower()
                elif k_clean in ['close_price', 'price', 'latest_price', 'close']: 
                    try: price = float(v)
                    except: pass
                elif k_clean in ['date_time', 'date', 'time', 'timestamp']: date = str(v).strip()
            
            if price is None: continue
            
            # Map the coin securely
            if csv_coin == 'bitcoin': coin = 'Bitcoin'
            elif csv_coin == 'ethereum': coin = 'Ethereum'
            elif csv_coin == 'solana': coin = 'Solana'
            elif csv_coin in ['ripple', 'xrp']: coin = 'Ripple'
            else: continue
            
            history[coin].append(price)
            if coin == 'Bitcoin' and date: dates.append(date)
                    
    if not dates: return None

    amount = float(amount)
    coin_holdings = {} 
    for coin in history.keys():
        if len(history[coin]) > 0:
            day_1_price = history[coin][0]
            usd_allocated = amount * (float(allocations.get(coin, 0)) / 100.0)
            # Prevent crashes if price is exactly zero
            coin_holdings[coin] = (usd_allocated / day_1_price) if day_1_price > 0 else 0
        else: 
            coin_holdings[coin] = 0

    daily_portfolio_values = []
    for i in range(len(dates)):
        daily_total = 0
        for coin in history.keys():
            if i < len(history[coin]): daily_total += coin_holdings[coin] * history[coin][i]
        daily_portfolio_values.append(daily_total)

    final_value = daily_portfolio_values[-1]
    profit_loss = final_value - amount
    return {
        'dates': dates, 'values': daily_portfolio_values, 'initial': amount, 
        'final': final_value, 'pnl': profit_loss, 'roi': (profit_loss / amount) * 100 if amount > 0 else 0
    }

@app.route('/simulator', methods=['GET', 'POST'])
def simulator():
    if 'user_id' not in session: return redirect(url_for('login'))
    simulation_results = None
    if request.method == 'POST':
        amount = request.form.get('amount')
        if not amount: amount = 10000
        def safe_float(val):
            try: return float(val)
            except: return 0.0
        allocations = {
            'Bitcoin': safe_float(request.form.get('btc_pct')),
            'Ethereum': safe_float(request.form.get('eth_pct')),
            'Solana': safe_float(request.form.get('sol_pct')),
            'Ripple': safe_float(request.form.get('xrp_pct'))
        }
        if sum(allocations.values()) == 100: simulation_results = simulate_portfolio(amount, allocations)
        else: flash('Allocations must equal 100%.', 'error')
    return render_template('portfolio_simulator.html', username=session['username'], results=simulation_results)

# --- PRICE FORECAST (ML) ---

def predict_future_price(coin_name, days_ahead):
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if not os.path.exists(filepath): return None

    historical_prices = []
    historical_dates = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_coin = str(row.get('crypto_name', '')).strip().lower()
            target_coin = str(coin_name).strip().lower()
            if csv_coin == target_coin:
                try:
                    historical_prices.append(float(row['close_price']))
                    historical_dates.append(row['date_time'])
                except: continue

    if not historical_prices or len(historical_prices) < 2: return None

    n = len(historical_prices)
    x = list(range(1, n + 1)) 
    y = historical_prices

    sum_x, sum_y = sum(x), sum(y)
    sum_x_squared = sum([i**2 for i in x])
    sum_xy = sum([x[i] * y[i] for i in range(n)])

    denominator = (n * sum_x_squared) - (sum_x ** 2)
    slope = 0 if denominator == 0 else ((n * sum_xy) - (sum_x * sum_y)) / denominator
    intercept = (sum_y - (slope * sum_x)) / n

    target_day_x = n + int(days_ahead)
    predicted_price = max(0.0, (slope * target_day_x) + intercept)
    current_price = historical_prices[-1]
    expected_change = ((predicted_price - current_price) / current_price) * 100 if current_price > 0 else 0

    trendline = [(slope * i) + intercept for i in x]
    future_trendline = trendline.copy()
    for i in range(1, int(days_ahead) + 1): future_trendline.append((slope * (n + i)) + intercept)

    return {
        'coin': coin_name, 'days_ahead': days_ahead, 'current_price': current_price,
        'predicted_price': predicted_price, 'expected_change': expected_change,
        'historical_prices': historical_prices, 'trendline': future_trendline, 'dates': historical_dates 
    }

@app.route('/forecast', methods=['GET', 'POST'])
def forecast():
    if 'user_id' not in session: return redirect(url_for('login'))
    prediction = None
    if request.method == 'POST':
        selected_coin = request.form.get('coin')
        days_to_predict = request.form.get('days')
        if selected_coin and days_to_predict: prediction = predict_future_price(selected_coin, days_to_predict)
    return render_template('price_forecast.html', username=session['username'], prediction=prediction)

# --- RISK ANALYSIS ---

def calculate_risk_metrics(coin_name):
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if not os.path.exists(filepath): return None
        
    prices = []
    dates = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_coin = str(row.get('crypto_name', '')).strip().lower()
            target_coin = str(coin_name).strip().lower()
            if csv_coin == target_coin:
                try:
                    prices.append(float(row['close_price']))
                    dates.append(row['date_time'])
                except: continue
                
    if not prices or len(prices) < 2: return None

    daily_returns = [((prices[i] - prices[i-1]) / prices[i-1]) for i in range(1, len(prices))]
    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_return)**2 for r in daily_returns) / len(daily_returns)
    annual_volatility = math.sqrt(variance) * math.sqrt(365) * 100 
    
    running_max = prices[0]
    drawdowns = [0.0] 
    for i in range(1, len(prices)):
        if prices[i] > running_max: running_max = prices[i]
        drawdowns.append(((prices[i] - running_max) / running_max) * 100)
        
    max_drawdown = min(drawdowns) 
    grade = "Low Risk (Grade A)" if annual_volatility < 40 else "Moderate Risk (Grade B)" if annual_volatility < 65 else "High Risk (Grade C)" if annual_volatility < 90 else "Extreme Risk (Grade D)"

    return {'coin': coin_name, 'annual_volatility': annual_volatility, 'max_drawdown': max_drawdown, 'grade': grade, 'dates': dates, 'drawdowns': drawdowns}

@app.route('/risk-analysis', methods=['GET', 'POST'])
def risk_analysis():
    if 'user_id' not in session: return redirect(url_for('login'))
    analysis = None
    if request.method == 'POST':
        selected_coin = request.form.get('coin')
        if selected_coin: analysis = calculate_risk_metrics(selected_coin)
    return render_template('risk_analysis.html', username=session['username'], analysis=analysis)

# --- LIVE MARKET & DATA SYNC ---

@app.route('/fetch-data', methods=['POST'])
def fetch_data():
    if 'user_id' not in session: return redirect(url_for('login'))
    dataset = data_manager.gather_all_data_in_parallel()
    if dataset:
        data_manager.save_to_csv(dataset)
        flash('Market data successfully updated!', 'success')
    else: flash('Error fetching data. Check your connection.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/live-market')
def live_market():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('live_market.html', username=session['username'])

@app.route('/api/live-prices')
def api_live_prices():
    symbols = '["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT"]'
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbols={symbols}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response: raw_data = json.loads(response.read().decode())
        name_map = {"BTCUSDT": "Bitcoin", "ETHUSDT": "Ethereum", "SOLUSDT": "Solana", "XRPUSDT": "Ripple"}
        live_data = [{"name": name_map[item['symbol']], "symbol": item['symbol'].replace('USDT', ''), "price": float(item['lastPrice']), "change_pct": float(item['priceChangePercent']), "high": float(item['highPrice']), "low": float(item['lowPrice']), "volume": float(item['volume'])} for item in raw_data]
        return {"status": "success", "data": live_data}
    except Exception as e: return {"status": "error", "message": str(e)}

# --- REPORTS ---

@app.route('/reports')
def reports():
    if 'user_id' not in session: return redirect(url_for('login'))
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    file_exists = os.path.exists(filepath)
    last_updated = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(filepath))) if file_exists else "N/A"
    file_size_kb = round(os.path.getsize(filepath) / 1024, 1) if file_exists else 0
    return render_template('reports.html', username=session['username'], file_exists=file_exists, last_updated=last_updated, file_size=file_size_kb)

@app.route('/download/market-data')
def download_market_data():
    if 'user_id' not in session: return redirect(url_for('login'))
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if os.path.exists(filepath): return send_file(filepath, as_attachment=True, download_name='crypto_market_history_365d.csv')
    flash('Report not found. Please sync data first.', 'error')
    return redirect(url_for('reports'))

@app.route('/download/forecast-summary')
def download_forecast_summary():
    if 'user_id' not in session: return redirect(url_for('login'))
    filepath = os.path.join('data', 'crypto_365d_history.csv')
    if not os.path.exists(filepath): return redirect(url_for('reports'))

    coin_data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            coin = row.get('crypto_name', '').strip()
            if coin not in coin_data: coin_data[coin] = []
            try: coin_data[coin].append(float(row['close_price']))
            except: continue

    report_data = []
    for coin, prices in coin_data.items():
        if len(prices) < 2: continue
        daily_change_pct = ((prices[-1] - prices[-2]) / prices[-2]) * 100
        prediction = predict_future_price(coin, 1)
        pred_decimal = (prediction['expected_change'] / 100.0) if prediction else 0.0
        report_data.append({'crypto_name': coin.lower(), 'latest_price': round(prices[-1], 2), 'predicted': round(pred_decimal, 5), 'latest_daily_change_%': round(daily_change_pct, 6)})

    out_filepath = os.path.join('data', 'forecast_summary.csv')
    with open(out_filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['crypto_name', 'latest_price', 'predicted', 'latest_daily_change_%'])
        writer.writeheader()
        writer.writerows(report_data)
    return send_file(out_filepath, as_attachment=True, download_name='ml_forecast_summary.csv')    

@app.route('/download/strategy-pdf')
def download_strategy_pdf():
    if 'user_id' not in session: return redirect(url_for('login'))
    plan = session.get('last_plan')
    if not plan: return redirect(url_for('reports'))
    return render_template('strategy_pdf.html', username=session['username'], plan=plan, date=time.strftime('%B %d, %Y'))

# --- SETTINGS & EMAIL ---

def send_risk_alert_email(sender_email, sender_password, recipient_email, coin, drop_pct, grade):
    if not sender_email or not sender_password: return False 
    message = MIMEMultipart("alternative")
    message["Subject"] = f"⚠️ SYSTEM ALERT: {coin} Risk Threshold Breached"
    message["From"] = sender_email
    message["To"] = recipient_email
    html = f"<html><body><h2>{coin} Alert</h2><p>Drawdown: {drop_pct}% | Grade: {grade}</p></body></html>"
    message.attach(MIMEText(html, "html"))
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        return True
    except: return False

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    if 'risk_threshold' not in session:
        session['risk_threshold'] = 20.0 
        session['alerts_enabled'] = True
        session['sender_email'] = ""
        session['sender_password'] = ""

    if request.method == 'POST':
        if 'update_settings' in request.form:
            session['risk_threshold'] = float(request.form.get('threshold', 20.0))
            session['alerts_enabled'] = request.form.get('alerts_enabled') == 'on'
            session['sender_email'] = request.form.get('sender_email', '')
            session['sender_password'] = request.form.get('sender_password', '')
            flash('System preferences updated.', 'success')
        elif 'test_alert' in request.form:
            conn = get_db_connection()
            user = conn.execute('SELECT email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            conn.close()
            success = send_risk_alert_email(session['sender_email'], session['sender_password'], user['email'], "Bitcoin", -25.5, "High Risk")
            if success: flash('Test alert sent.', 'success')
            else: flash('Failed to send email. Check App Password.', 'error')

    return render_template('settings.html', username=session['username'], threshold=session['risk_threshold'], alerts_enabled=session['alerts_enabled'], sender_email=session.get('sender_email', ''), sender_password=session.get('sender_password', ''))

if __name__ == '__main__':
    app.run(debug=True, port=8900)