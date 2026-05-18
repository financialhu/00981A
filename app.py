"""
00981A ETF 監控 — 雲端版
報價來源：openapi.twse.com.tw + tpex.org.tw（無地區限制，每日更新）
"""
from flask import Flask, jsonify, send_from_directory, request
import urllib.request, urllib.parse, json, time, os, ssl

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
        return json.loads(r.read())

# ── 快取 ─────────────────────────────────────────────────────────
_cache = {"tse": {}, "otc": {}, "ts": 0}

def refresh_cache():
    """每5分鐘重抓一次上市+上櫃全部股票收盤資料"""
    global _cache
    now = time.time()
    if now - _cache["ts"] < 300:
        return

    # 上市
    try:
        rows = fetch("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL")
        tse = {}
        for r in rows:
            code  = str(r.get("Code","")).strip()
            close = str(r.get("ClosingPrice","")).replace(",","").strip()
            open_ = str(r.get("OpeningPrice","")).replace(",","").strip()
            name  = str(r.get("Name","")).strip()
            if code and close and close != "--":
                try:
                    c = float(close)
                    o = float(open_) if open_ and open_ != "--" else c
                    tse[code] = {"price": c, "prev": o, "name": name}
                except:
                    pass
        _cache["tse"] = tse
    except Exception as e:
        print(f"上市資料失敗: {e}")

    # 上櫃
    try:
        rows = fetch("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes")
        otc = {}
        for r in rows:
            code  = str(r.get("SecuritiesCompanyCode","")).strip()
            close = str(r.get("Close","")).replace(",","").strip()
            open_ = str(r.get("Open","")).replace(",","").strip()
            name  = str(r.get("CompanyName","")).strip()
            if code and close and close != "--":
                try:
                    c = float(close)
                    o = float(open_) if open_ and open_ != "--" else c
                    otc[code] = {"price": c, "prev": o, "name": name}
                except:
                    pass
        _cache["otc"] = otc
    except Exception as e:
        print(f"上櫃資料失敗: {e}")

    _cache["ts"] = now
    print(f"快取更新：上市 {len(_cache['tse'])} 筆，上櫃 {len(_cache['otc'])} 筆")


@app.route('/api/price')
def price():
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    if not codes:
        return jsonify({'error': 'no codes'}), 400

    refresh_cache()

    msg_array = []
    for c in codes:
        # 先找上市，再找上櫃
        p = _cache["tse"].get(c) or _cache["otc"].get(c)
        if p:
            msg_array.append({
                "c": c,
                "n": p["name"],
                "z": str(p["price"]),
                "y": str(p["prev"]),
            })

    return jsonify({"msgArray": msg_array})


@app.route('/api/debug')
def debug():
    """查看快取狀態"""
    refresh_cache()
    sample_tse = dict(list(_cache["tse"].items())[:3])
    sample_otc = dict(list(_cache["otc"].items())[:3])
    return jsonify({
        "tse_count": len(_cache["tse"]),
        "otc_count": len(_cache["otc"]),
        "sample_tse": sample_tse,
        "sample_otc": sample_otc,
        "age_sec": int(time.time() - _cache["ts"]),
    })


@app.route('/api/health')
def health():
    return jsonify({'ok': True})


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    app.run(host='0.0.0.0', port=port)
