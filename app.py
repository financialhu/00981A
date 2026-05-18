"""
00981A ETF 監控 — 雲端版
部署在 Render，不需要本機 proxy
"""
from flask import Flask, jsonify, send_from_directory, request
import urllib.request, urllib.parse, json, time, os

app = Flask(__name__, static_folder='static')

# ── 報價 API（轉發 mis.twse.com.tw）─────────────────────────────
@app.route('/api/price')
def price():
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    if not codes:
        return jsonify({'error': 'no codes'}), 400

    parts = []
    for c in codes:
        otc = len(c) == 4 and c.startswith('6')
        parts.append(f"{'otc' if otc else 'tse'}_{c}.tw")

    ex_ch = '|'.join(parts)
    url = (f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
           f"?ex_ch={urllib.parse.quote(ex_ch)}&json=1&delay=0&_={int(time.time()*1000)}")
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'https://mis.twse.com.tw/',
        })
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 502

# ── 健康檢查 ─────────────────────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({'ok': True})

# ── 前端（所有其他路徑都回傳 index.html）────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    app.run(host='0.0.0.0', port=port)
