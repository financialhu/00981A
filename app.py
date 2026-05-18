"""
00981A ETF 監控 — 雲端版
用 openapi.twse.com.tw 取得收盤價（每日更新，無地區限制）
盤中用昨收價+試算，或直接顯示最新收盤
"""
from flask import Flask, jsonify, send_from_directory, request
import urllib.request, urllib.parse, json, time, os, ssl

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def fetch_url(url, headers=None):
    h = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
        return json.loads(r.read())

# ── 方法1：openapi.twse.com.tw 當日收盤（無IP限制）──────────────
def get_twse_closing():
    """抓今日上市全部個股收盤價，回傳 {code: {price, prev}} dict"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = fetch_url(url)
    result = {}
    for row in data:
        code  = row.get("Code", "")
        close = float(row.get("ClosingPrice", 0) or 0)
        open_ = float(row.get("OpeningPrice", 0) or 0)
        if code and close:
            result[code] = {"price": close, "prev": open_ or close, "name": row.get("Name", code)}
    return result

# 快取，避免每次都重新抓（每5分鐘更新一次）
_cache = {"data": {}, "ts": 0}

def get_prices_cached():
    global _cache
    if time.time() - _cache["ts"] > 300:  # 5分鐘
        try:
            _cache["data"] = get_twse_closing()
            _cache["ts"]   = time.time()
        except Exception as e:
            print(f"更新失敗: {e}")
    return _cache["data"]


@app.route('/api/price')
def price():
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    if not codes:
        return jsonify({'error': 'no codes'}), 400

    try:
        all_prices = get_prices_cached()
        msg_array = []
        for c in codes:
            if c in all_prices:
                p = all_prices[c]
                msg_array.append({
                    "c": c,
                    "n": p["name"],
                    "z": str(p["price"]),
                    "y": str(p["prev"]),
                })
        return jsonify({"msgArray": msg_array})
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.route('/api/health')
def health():
    return jsonify({'ok': True})


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    app.run(host='0.0.0.0', port=port)
