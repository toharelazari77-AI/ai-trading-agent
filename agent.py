import yfinance as yf
import pandas as pd
import requests
import os
import json

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# S&P 500
sp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
stocks = sp500['Symbol'].tolist()

crypto = ["BTC-USD", "ETH-USD", "SOL-USD"]
symbols = stocks + crypto

STATE_FILE = "sent_alerts.json"

# טעינת התראות קודמות
try:
    with open(STATE_FILE, "r") as f:
        sent_alerts = json.load(f)
except:
    sent_alerts = {}

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(sent_alerts, f)

def get_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

messages = []

for symbol in symbols:
    try:
        df = yf.download(symbol, period="3mo", interval="1d")

        if len(df) < 60:
            continue

        df['RSI'] = get_rsi(df)
        df['High_20'] = df['High'].rolling(20).max()
        df['Low_20'] = df['Low'].rolling(20).min()
        df['Volume_avg'] = df['Volume'].rolling(20).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        signal = None
        score = 0

        # 🚀 פריצה אמיתית
        if last['Close'] > prev['High_20']:
            score += 1
        if last['Volume'] > last['Volume_avg'] * 1.5:
            score += 1
        if last['RSI'] > 55:
            score += 1

        if score >= 2:
            signal = "Breakout"

        # 🎯 Pullback
        if (
            prev['Close'] > prev['High_20'] and
            abs(last['Close'] - prev['High_20']) / prev['High_20'] < 0.02
        ):
            signal = "Pullback"
            score += 1

        # 📉 תמיכה
        if last['Close'] <= prev['Low_20'] * 1.03 and last['RSI'] < 40:
            signal = "Support"

        # 🧠 תבנית בסיסית
        lows = df['Low'].tail(15).values
        if len(lows) >= 5 and lows[7] < lows[3] and lows[7] < lows[11]:
            signal = "Pattern"
            score += 1

        if not signal:
            continue

        # דירוג
        if score >= 3:
            grade = "A🔥"
        elif score == 2:
            grade = "B"
        else:
            grade = "C"

        # מניעת כפילויות
        key = f"{symbol}_{signal}"
        if key in sent_alerts:
            continue

        sent_alerts[key] = True

        entry = last['Close']
        stop = entry * 0.97
        target = entry * 1.05

        messages.append(
            f"{grade} | {symbol}\n"
            f"Signal: {signal}\n"
            f"Entry: {entry:.2f}\n"
            f"Target: {target:.2f}\n"
            f"Stop: {stop:.2f}"
        )

    except:
        continue

# שליחה
if messages:
    text = "\n\n".join(messages[:15])
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

save_state()
messages.append("✅ הבוט עובד בהצלחה 🔥")
print("Pro Scan done")
