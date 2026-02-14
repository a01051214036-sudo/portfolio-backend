import os
import json
import requests
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- 환경 변수 설정 (Render에서 입력) ---
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")

# --- 구글 시트 인증 함수 ---
def get_google_sheet():
    if not GOOGLE_CREDENTIALS_JSON or not GOOGLE_SHEET_ID:
        print("구글 시트 설정이 누락되었습니다.")
        return None
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(GOOGLE_SHEET_ID).sheet1
    except Exception as e:
        print(f"Google Sheet Auth Error: {e}")
        return None

# --- 티커 매핑 ---
TICKER_MAP = {
    "SOXL": "SOXL", "BTC": "BTC-USD", "AAPL": "AAPL", "ASML": "ASML",
    "GOOGL": "GOOGL", "MU": "MU", "NVDA": "NVDA", "SLV": "SLV",
    "ACE_KRX_GOLD": "411060.KS", "ACE_US_30Y": "453850.KS",
}

def get_exchange_rate():
    try:
        data = yf.Ticker("KRW=X").history(period="1d")
        return data['Close'].iloc[-1]
    except:
        return 1450.0

@app.route('/')
def home():
    return "Portfolio Backend (Google Sheets Only) is Running!"

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

# 1. 가격 조회 API
@app.route('/api/prices', methods=['POST'])
def get_prices():
    data = request.json
    raw_tickers = data.get('tickers', [])
    usd_krw = get_exchange_rate()
    prices = {}
    
    for t in raw_tickers:
        yahoo_ticker = TICKER_MAP.get(t, t)
        try:
            ticker_obj = yf.Ticker(yahoo_ticker)
            todays_data = ticker_obj.history(period="1d")
            if not todays_data.empty:
                current_price = todays_data['Close'].iloc[-1]
                if ".KS" in yahoo_ticker or ".KQ" in yahoo_ticker:
                    prices[t] = round(current_price)
                else:
                    prices[t] = round(current_price * usd_krw)
        except: pass
    return jsonify(prices)

# 2. 구글 시트 불러오기
@app.route('/api/sheets/load', methods=['GET'])
def load_from_sheets():
    sheet = get_google_sheet()
    if not sheet:
        return jsonify({"status": "error", "message": "Google Sheet connection failed"}), 500
    
    try:
        records = sheet.get_all_records()
        portfolio_list = []
        
        for i, row in enumerate(records):
            try:
                qty = float(str(row.get('수량', 0)).replace(',', ''))
            except: qty = 0
            
            try:
                avg = float(str(row.get('매수단가', 0)).replace(',', ''))
            except: avg = 0
            
            item = {
                "id": i + 1,
                "name": str(row.get('종목명', '')),
                "ticker": str(row.get('티커', '')),
                "qty": qty,
                "avgPrice": avg,
                "currentPrice": avg, # 초기값
                "account": str(row.get('계좌', '공통')),
                "assetClass": str(row.get('자산군', '기타')),
                "risk": str(row.get('위험등급', '미분류')),
                "role": str(row.get('역할', '미분류')),
                "category": "일반"
            }
            portfolio_list.append(item)
            
        return jsonify(portfolio_list)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 3. 구글 시트 저장하기
@app.route('/api/sheets/sync', methods=['POST'])
def sync_to_sheets():
    sheet = get_google_sheet()
    if not sheet:
        return jsonify({"status": "error", "message": "Google Sheet connection failed"}), 500

    data_list = request.json
    try:
        headers = ["계좌", "자산군", "위험등급", "역할", "종목명", "티커", "수량", "매수단가", "평가금액", "수익률"]
        rows = [headers]
        
        for item in data_list:
            current_val = item.get('currentPrice', 0) * item.get('qty', 0)
            invested_val = item.get('avgPrice', 0) * item.get('qty', 0)
            roi = ((current_val - invested_val) / invested_val) * 100 if invested_val > 0 else 0

            row = [
                item.get('account'), item.get('assetClass'), item.get('risk'), item.get('role'),
                item.get('name'), item.get('ticker'), item.get('qty'), item.get('avgPrice'),
                int(current_val), f"{roi:.2f}%"
            ]
            rows.append(row)
            
        sheet.clear()
        sheet.update('A1', rows)
        return jsonify({"status": "success", "count": len(data_list)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)