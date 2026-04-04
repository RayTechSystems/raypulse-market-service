import os
import sys

from flask import Flask, jsonify
import logging
from flask_cors import CORS
from SmartApi import SmartConnect
import pyotp
import time
import threading

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

# 3. Validation: Stop the app immediately if secrets are missing
# This prevents confusing "NoneType" errors later in your logic.
required_secrets = {
    "ANGEL_API_KEY": ANGEL_API_KEY,
    "ANGEL_CLIENT_ID": ANGEL_CLIENT_ID,
    "ANGEL_PASSWORD": ANGEL_PASSWORD,
    "ANGEL_TOTP_SECRET": ANGEL_TOTP_SECRET
}

# GLOBAL STATE
latest_data = {}
smart_api = None

# SYMBOLS MAP (For SmartAPI, we need Exchange and Token ID)
# You can find these in the Angel One JSON master file
SYMBOLS = {
    "NIFTY":     {"exchange": "NSE", "tradingsymbol": "NIFTY",     "symboltoken": "99926000"},
    "BANKNIFTY": {"exchange": "NSE", "tradingsymbol": "BANKNIFTY", "symboltoken": "99926009"},
    "RELIANCE":  {"exchange": "NSE", "tradingsymbol": "RELIANCE-EQ", "symboltoken": "2885"},
    "SBIN":      {"exchange": "NSE", "tradingsymbol": "SBIN-EQ",     "symboltoken": "3045"}
}

def login_to_angel():
    "Handles the full login flow including TOTP"
    global smart_api
    # Connect Flask's logger to Gunicorn's error handlers
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

    try:
        app.logger.info("Starting AngelOne APP")
        print("--- RAYPULSE STARTING --- " + time.strftime("%Y-%m-%d %H:%M:%S"),file=sys.stderr, flush=True)
        print("Attempting Login...", file=sys.stderr, flush=True)
        smart_api = SmartConnect(api_key=API_KEY)
        
        # Generate TOTP
        totp = pyotp.TOTP(TOTP_SECRET).now()
        
        # Generate Session
        data = smart_api.generateSession(CLIENT_ID, PASSWORD, totp)
        
        if data['status']:
            print("Login Successful!",file=sys.stderr, flush=True)
            return True
        else:
            print(f"Login Failed: {data['message']}", file=sys.stderr, flush=True)
            return False
    except Exception as e:
        print(f"Login Exception: {e}", file=sys.stderr, flush=True)
        return False

def fetch_market():
    """Background thread to poll LTP (Last Traded Price)"""
    global latest_data, smart_api
    
    # Ensure we are logged in before starting
    while not login_to_angel():
        app.logger.info("Starting AngelOne Login...")
        print("Retrying login in 10 seconds...", file=sys.stderr, flush=True)
        time.sleep(10)

    while True:
        try:
            result = {}
            for name, details in SYMBOLS.items():
                # Fetch LTP from SmartAPI
                response = smart_api.ltpData(
                    details['exchange'], 
                    details['tradingsymbol'], 
                    details['symboltoken']
                )
                
                if response['status'] and response['data']:
                    data = response['data']
                    result[name] = {
                        "symbol":    details['tradingsymbol'],
                        "price":     data.get('ltp', 0),
                        "high":      data.get('high', 0),
                        "low":       data.get('low', 0),
                        "close":     data.get('close', 0),
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    print(f"{name}: {result[name]['price']}")
                else:
                    print(f"Error fetching {name}: {response.get('message')}")
            
            latest_data = result
            print("--- All SmartAPI data fetched ---", file=sys.stderr, flush=True)

        except Exception as e:
            print(f"Global Fetch Error: {e}")
            # If session expires, re-login
            if "Invalid Token" in str(e) or "Session Expired" in str(e):
                login_to_angel()

        time.sleep(5) # Poll every 5 seconds

@app.route("/market")
def get_market():
    return jsonify(latest_data)

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "logged_in": smart_api is not None,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == "__main__":
    # Start the data thread
    threading.Thread(target=fetch_market, daemon=True).start()
    
    # Run Flask
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
