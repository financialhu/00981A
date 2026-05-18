"""
00981A ETF 監控 — 雲端版
報價來源改為 Yahoo Finance（全球可連，無地區限制）
"""
from flask import Flask, jsonify, send_from_directory, request
import urllib.request, urllib.parse, json, os

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)


def yahoo_quote(symbols):
    """
    從 Yahoo Finance v7 quote API 批次取得現價與昨收。
    symbols: list of str，例如 ['2330.TW', '2454.TW']
    回傳 list of dict: [{c, n, z, y}, ...]  (與 mis.twse 格式相容)
    """
    joined = ','.join(symbols)
    url = (f"https://query1.finance.yahoo.com/v7/finance/quote"
           f"?symbols={urllib.parse.quote(joined)}"
           f"&fields=regularMarketPrice,previousClose,shortName,symbol"
           f"&lang=zh-TW&region=TW")

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())

    results = []
    for q in data.get("quoteResponse", {}).get("result", []):
        sym   = q.get("symbol", "")                        # e.g. "2330.TW"
        code  = sym.replace(".TW", "").replace(".TWO", "") # e.g. "2330"
        price = q.get("regularMarketPrice", 0)
        prev  = q.get("previousClose", price)
        name  = q.get("shortName", code)
        results.append({
            "c": code,
            "n": name,
            "z": str(price),   # 現價
            "y": str(prev),    # 昨收
        })
    return results


@app.route('/api/price')
def price():
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    if not codes:
        return jsonify({'error': 'no codes'}), 400

    # 轉成 Yahoo 格式：上市加 .TW，上櫃（6開頭4碼）加 .TWO
    symbols = []
    for c in codes:
        suffix = ".TWO" if (len(c) == 4 and c.startswith("6")) else ".TW"
        symbols.append(c + suffix)

    try:
        results = yahoo_quote(symbols)
        # 回傳與舊版相容的格式，讓前端不用改
        return jsonify({"msgArray": results})
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
