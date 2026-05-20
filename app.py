"""
00981A ETF 監控 — 雲端版（Render）
報價來源：Yahoo Finance v8 chart API
"""
from flask import Flask, jsonify, send_from_directory, request
import urllib.request, urllib.parse, json, os
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)


def fetch_one(code):
    """Yahoo Finance v8，先試上市再試上櫃"""
    for suffix in ['.TW', '.TWO']:
        url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{code}{suffix}"
               f"?interval=1d&range=1d&lang=zh-TW")
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            })
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
            meta  = ((data.get('chart') or {}).get('result') or [{}])[0].get('meta') or {}
            price = meta.get('regularMarketPrice', 0)
            prev  = meta.get('previousClose') or meta.get('chartPreviousClose') or price
            name  = meta.get('shortName') or meta.get('symbol') or code
            if price:
                return code, {'price': price, 'prev': prev, 'name': name}
        except:
            continue
    return code, None


@app.route('/api/price')
def price():
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    if not codes:
        return jsonify({'error': 'no codes'}), 400

    result = {}
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(fetch_one, c): c for c in codes}
        for f in as_completed(futures):
            code, data = f.result()
            if data:
                result[code] = data

    msg_array = [
        {'c': c, 'z': str(v['price']), 'y': str(v['prev']), 'n': v.get('name', c)}
        for c, v in result.items()
    ]
    return jsonify({'msgArray': msg_array})


@app.route('/api/health')
def health():
    return jsonify({'ok': True})


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    app.run(host='0.0.0.0', port=port)
