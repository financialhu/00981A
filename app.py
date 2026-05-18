"""
00981A ETF 監控 — 雲端版
報價來源：mis.twse.com.tw（從伺服器端打，無 CORS 限制）
"""
from flask import Flask, jsonify, send_from_directory, request
import urllib.request, urllib.parse, json, time, os

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)


@app.route('/api/price')
def price():
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    if not codes:
        return jsonify({'error': 'no codes'}), 400

    # 上市 tse_，上櫃（6開頭4碼）otc_
    parts = []
    for c in codes:
        otc = len(c) == 4 and c.startswith('6')
        parts.append(f"{'otc' if otc else 'tse'}_{c}.tw")

    ex_ch = '|'.join(parts)
    url = (
        f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
        f"?ex_ch={urllib.parse.quote(ex_ch)}&json=1&delay=0&_={int(time.time()*1000)}"
    )

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer":  "https://mis.twse.com.tw/stock/index.jsp",
            "Accept":   "application/json, text/plain, */*",
            "Accept-Language": "zh-TW,zh;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())

        # 確認有拿到資料
        msg = data.get("msgArray", [])
        if not msg:
            return jsonify({"error": "empty msgArray", "raw": data}), 502

        return jsonify(data)

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
