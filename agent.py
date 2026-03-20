import yfinance as yf
import pandas as pd
import requests
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# S&P 500
sp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
stocks = sp500['Symbol'].tolist()

# קריפטו
crypto = ["BTC-USD", "ETH-USD", "SOL-USD"]

symbols = stocks + crypto


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

        if len(df) < 50:
            continue

        df['RSI'] = get_rsi(df)
        df['High_20'] = df['High'].rolling(20).max()
        df['Low_20'] = df['Low'].rolling(20).min()
        df['Volume_avg'] = df['Volume'].rolling(20).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        score = 0

        # פריצה איכותית
        if last['Close'] > prev['High_20']:
            score += 1
        if last['RSI'] > 55:
            score += 1
        if last['Volume'] > last['Volume_avg']:
            score += 1

        if score >= 3:
            messages.append(
                f"🚀 {symbol}\nפריצה חזקה\nמחיר: {last['Close']:.2f}\nRSI: {last['RSI']:.1f}"
            )

        # תמיכה איכותית
        support_score = 0

        if last['Close'] <= prev['Low_20'] * 1.02:
            support_score += 1
        if last['RSI'] < 35:
            support_score += 1
        if last['Close'] > prev['Low_20']:
            support_score += 1

        if support_score >= 3:
            messages.append(
                f"📉 {symbol}\nאזור תמיכה חזק\nמחיר: {last['Close']:.2f}\nRSI: {last['RSI']:.1f}"
            )

    except:
        continue

# שליחה לטלגרם
if messages:
    text = "\n\n".join(messages[:10])
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

print("Scan done")
