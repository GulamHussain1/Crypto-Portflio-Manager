# Crypto Investment Portfolio Manager

**Author:** Gulam Hussain
**Institution:** University Institute of Technology, Barkatullah University, Bhopal
**Status:** Version 1.0 (Completed)

## 🎯 Product Vision
A comprehensive, full-stack web application designed to help institutional and retail investors track, analyze, and simulate cryptocurrency portfolios. The system utilizes pure Python for heavy data processing, machine learning forecasting, and mathematical risk analysis, completely avoiding bloated third-party analytical libraries.

## 🛠️ Tech Stack
* **Backend:** Python, Flask
* **Database:** SQLite
* **Frontend:** HTML5, CSS3 (Custom Grid/Flexbox), JavaScript
* **Data Visualization:** Chart.js
* **Data Pipeline:** Parallel HTTP requests (`urllib`), standard CSV modules

---

## 📋 Agile User Stories (Completed Epics)

### Epic 1: Authentication & Security
* **User Story:** As a user, I want to securely sign up and log in so that my portfolio data remains private.
* **Acceptance Criteria:** Passwords must be hashed using Werkzeug. Sessions must be managed securely via Flask.

### Epic 2: Data Aggregation & Dashboard
* **User Story:** As an analyst, I want to sync 365 days of historical market data and view it on a dashboard so I can identify macro trends.
* **Acceptance Criteria:** Implement a parallel-processing data fetcher. Display live KPIs and a multi-line Chart.js EDA graph.

### Epic 3: Live Market Tracking
* **User Story:** As a trader, I want to see real-time price updates so I can monitor daily market volatility.
* **Acceptance Criteria:** Implement an asynchronous JavaScript fetch loop that pings a custom Flask API endpoint every 3 seconds for Binance ticker data.

### Epic 4: Strategy & Simulation Engine
* **User Story:** As an investor, I want to generate rule-based asset allocations and backtest custom mixes against historical data.
* **Acceptance Criteria:** Build a pure Python math engine for calculating spreads based on risk profiles. Build a backtesting loop that calculates daily ROI over a 365-day period.

### Epic 5: Advanced Analytics (Machine Learning & Risk)
* **User Story:** As a risk manager, I want to forecast future prices and calculate maximum drawdowns so I can avoid volatile assets.
* **Acceptance Criteria:** Implement a custom Linear Regression model (Least Squares) in pure Python. Calculate annualized volatility and generate "Underwater" drawdown charts.

### Epic 6: Reporting & Automation
* **User Story:** As an administrator, I want to export my data and receive automated alerts for critical market crashes.
* **Acceptance Criteria:** Generate dynamic CSV and print-optimized PDF reports. Implement a standard `smtplib` email engine that accepts dynamic SMTP credentials to send HTML warning alerts.