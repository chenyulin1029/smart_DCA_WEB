# smart_dca_app.py

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

# 1. Load tickers
@st.cache_data
def load_valid_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    table = pd.read_html(url)[0]
    return set(table['Symbol'].tolist() + ['QQQ', 'NVDA'])

valid_tickers = load_valid_tickers()

# 2. Utility functions (same as in your code)
def fetch_price(ticker, date):
    df = yf.download(ticker, start=date - datetime.timedelta(days=200),
                     end=date + datetime.timedelta(days=1),
                     progress=False, auto_adjust=False)
    col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    return float(df[col].loc[:pd.to_datetime(date)].iloc[-1])

def validate_tickers(input_str):
    tickers = [t.strip().upper() for t in input_str.split(',') if t.strip()]
    invalid = [t for t in tickers if t not in valid_tickers]
    if invalid:
        raise ValueError(f"Invalid tickers: {invalid}")
    return tickers

def get_last_trade_and_buy_dates():
    today = datetime.date.today()
    offset = 1 if today.weekday() >= 5 else 0
    last_trade = today - datetime.timedelta(days=offset)
    tentative = datetime.date(today.year, today.month, 15)
    while tentative.weekday() >= 5:
        tentative += datetime.timedelta(days=1)
    return today, last_trade, tentative

# 3. Smart DCA logic
def run_dca(tickers, init_counts, cutoff_date, buy_date, invest_amt):
    prices = {t: fetch_price(t, cutoff_date) for t in tickers}
    raw = {}
    for t in tickers:
        p0 = prices[t]
        p1 = fetch_price(t, cutoff_date - datetime.timedelta(days=30))
        p3 = fetch_price(t, cutoff_date - datetime.timedelta(days=90))
        p6 = fetch_price(t, cutoff_date - datetime.timedelta(days=180))
        r1, r3, r6 = p0 / p1 - 1, p0 / p3 - 1, p0 / p6 - 1
        raw[t] = 0.2*r1 + 0.3*r3 + 0.5*r6

    rotation = init_counts.copy()
    sorted_raw = sorted(raw.items(), key=lambda x: x[1], reverse=True)

    for t, score in sorted_raw:
        if rotation.get(t, 0) < 3:
            candidate = t
            break
    else:
        candidate = sorted_raw[0][0]
        for t in rotation:
            rotation[t] = 0

    rotation[candidate] += 1
    for t in rotation:
        if t != candidate:
            rotation[t] = 0

    price = prices[candidate]
    shares = np.floor(invest_amt / price * 1000) / 1000
    cost = shares * price

    return {
        "Buy Ticker": candidate,
        "Price": price,
        "Shares": shares,
        "Cost": cost,
        "New Rotation": rotation
    }

# 4. UI Layout
st.title("📊 Smart DCA Investment Engine")

ticker_str = st.text_input("Enter Tickers (comma-separated)", value="QQQ,AAPL,NVDA")
preset = st.radio("Choose Investment Preset", ['$450 (Default)', '$600 (Future)'])
custom_amt = st.number_input("Or enter custom amount", min_value=0.0, max_value=5000.0, step=10.0, value=0.0)
amount = 450 if (custom_amt == 0 and preset == '$450 (Default)') else (600 if custom_amt == 0 else custom_amt)

cutoff_date = st.date_input("Cutoff Date", value=get_last_trade_and_buy_dates()[1])
buy_date = st.date_input("Buy Date", value=get_last_trade_and_buy_dates()[2])

st.markdown("### Rotation Counts")
col1, col2, col3 = st.columns(3)
count_qqq = col1.number_input("QQQ", min_value=0, max_value=3, value=0)
count_aapl = col2.number_input("AAPL", min_value=0, max_value=3, value=0)
count_nvda = col3.number_input("NVDA", min_value=0, max_value=3, value=3)

if st.button("Run Smart DCA"):
    try:
        tickers = validate_tickers(ticker_str)
        init_counts = {'QQQ': count_qqq, 'AAPL': count_aapl, 'NVDA': count_nvda}
        result = run_dca(tickers, init_counts, cutoff_date, buy_date, amount)
        st.success("✅ Smart DCA Suggestion:")
        st.write(result)
    except Exception as e:
        st.error(f"❌ {e}")