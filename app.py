"""
00981A ETF 監控 — 雲端版（純靜態）
報價由前端直接透過 CORS proxy 抓取，後端只負責 serve HTML
"""
from flask import Flask, send_from_directory
import os

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)

@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/api/health')
def health():
    from flask import jsonify
    return jsonify({'ok': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    app.run(host='0.0.0.0', port=port)
