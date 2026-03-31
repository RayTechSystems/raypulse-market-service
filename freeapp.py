from flask import Flask, jsonify
from flask_cors import CORS
import yfinance, time, threading

app = Flask(__name__)
CORS(app, resources={
    r"/*":{
        "origins":[
            "https://yellow-pond-0463cf400.6.azurestaticapps.net",
            "http://localhost",
            "http://localhost:3000",
            "http://127.0.0.1",
            "http://144.24.117.46",
            "*"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "ngrok-skip-browser-warning"]
    }
})
latest_data = {}

SYMBOLS = {
    "NIFTY50":   "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX":    "^BSESN",
    "AAPL":      "AAPL",
    "MSFT":      "MSFT",
    "GOLD":      "GC=F",
    "CRUDE_OIL": "CL=F"
}

def safe_round(val, digits=2):
    try:
        if val is None:
            return 0
        return round(float(val), digits)
    except:
        return 0

def safe_int(val):
    try:
        if val is None:
            return 0
        return int(val)
    except:
        return 0

def fetch_market():
    global latest_data
    while True:
        try:
            result = {}
            for name, symbol in SYMBOLS.items():
                try:
                    ticker = yfinance.Ticker(symbol)
                    info = ticker.fast_info
                    result[name] = {
                        "symbol":    symbol,
                        "price":     safe_round(info.last_price),
                        "high":      safe_round(info.day_high),
                        "low":       safe_round(info.day_low),
                        "volume":    safe_int(info.last_volume),
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    print(f"{name}: {result[name]['price']}")
                except Exception as e:
                    print(f"ERROR fetching {name}: {e}")
                    result[name] = {
                        "symbol":    symbol,
                        "price":     0,
                        "high":      0,
                        "low":       0,
                        "volume":    0,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }

            latest_data = result
            print("--- All data fetched ---")

        except Exception as e:
            print(f"GLOBAL ERROR: {e}")

        time.sleep(5)

@app.route("/market")
def market():
    return jsonify(latest_data)

@app.route("/quote/<symbol>")
def quote(symbol):
    symbol = symbol.upper()
    if symbol in latest_data:
        return jsonify(latest_data[symbol])
    return jsonify({"error": "symbol not found"}), 404

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "symbols": list(SYMBOLS.keys()),
        "last_updated": latest_data.get(
            "NIFTY50", {}
        ).get("timestamp", "not yet")
    })

threading.Thread(target=fetch_market, daemon=True).start()
app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
