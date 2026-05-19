"""
00981A ETF 監控 — 雲端版
上市：twse.com.tw MI_INDEX（每日盤後更新，無地區限制）
上櫃：tpex.org.tw openapi
"""
from flask import Flask, jsonify, send_from_directory, request
import urllib.request, urllib.parse, json, time, os, ssl, re

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    })
    with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
        return json.loads(r.read())

_cache = {"tse": {}, "otc": {}, "ts": 0}

def refresh_cache():
    global _cache
    if time.time() - _cache["ts"] < 300:
        return

    # ── 上市：用 twse MI_INDEX（當日全市場行情）────────────────
    try:
        today = time.strftime("%Y%m%d")
        url = (f"https://www.twse.com.tw/exchangeReport/MI_INDEX"
               f"?response=json&date={today}&type=ALL&_={int(time.time()*1000)}")
        data = fetch(url)
        # fields9 = ["證券代號","證券名稱","成交股數",...,"收盤價","漲跌","漲跌價差",...]
        fields = data.get("fields9", [])
        rows   = data.get("data9",   [])
        # 找欄位位置
        fi_code  = next((i for i,f in enumerate(fields) if "代號" in f), 0)
        fi_name  = next((i for i,f in enumerate(fields) if "名稱" in f), 1)
        fi_close = next((i for i,f in enumerate(fields) if "收盤" in f), 8)
        fi_open  = next((i for i,f in enumerate(fields) if "開盤" in f), 5)

        tse = {}
        for row in rows:
            code  = str(row[fi_code]).strip()
            name  = str(row[fi_name]).strip()
            close = str(row[fi_close]).replace(",","").strip()
            open_ = str(row[fi_open]).replace(",","").strip()
            if code and close and close not in ("--",""):
                try:
                    c = float(close)
                    o = float(open_) if open_ not in ("--","") else c
                    tse[code] = {"price": c, "prev": o, "name": name}
                except:
                    pass
        _cache["tse"] = tse
        print(f"上市更新：{len(tse)} 筆")
    except Exception as e:
        print(f"上市失敗: {e}")

    # ── 上櫃：tpex openapi ───────────────────────────────────────
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
        print(f"上櫃更新：{len(otc)} 筆")
    except Exception as e:
        print(f"上櫃失敗: {e}")

    _cache["ts"] = time.time()


@app.route('/api/price')
def price():
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    if not codes:
        return jsonify({'error': 'no codes'}), 400

    refresh_cache()

    msg_array = []
    for c in codes:
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
    refresh_cache()
    # 查幾個常見股票確認有沒有抓到
    test = {c: _cache["tse"].get(c) or _cache["otc"].get(c)
            for c in ["2330","2454","2303","6669"]}
    return jsonify({
        "tse_count": len(_cache["tse"]),
        "otc_count": len(_cache["otc"]),
        "test_stocks": test,
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
