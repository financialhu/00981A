"""
00981A ETF 監控 — 雲端版
報價來源：Google Finance（無地區限制）
台股格式：TSE:2330（上市）、TPE:2330（上櫃）
"""
from flask import Flask, jsonify, send_from_directory, request
import urllib.request, urllib.parse, json, time, os, ssl, re

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

def fetch_google_price(code):
    """
    從 Google Finance 頁面抓單一股票現價與昨收。
    先試上市(TSE)，再試上櫃(TPE)。
    回傳 {"price": float, "prev": float, "name": str} 或 None
    """
    for exchange in ["TSE", "TPE"]:
        url = f"https://www.google.com/finance/quote/{code}:{exchange}"
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,*/*",
            })
            with urllib.request.urlopen(req, timeout=10, context=CTX) as r:
                html = r.read().decode("utf-8", errors="replace")

            # 現價：data-last-price 或 class="YMlKec fxKbKc"
            price = None
            m = re.search(r'data-last-price="([\d\.]+)"', html)
            if not m:
                m = re.search(r'class="YMlKec fxKbKc"[^>]*>([\d,\.]+)', html)
            if m:
                price = float(m.group(1).replace(",",""))

            # 昨收：data-prev-close
            prev = price
            m2 = re.search(r'data-prev-close="([\d\.]+)"', html)
            if not m2:
                # 備用：找「前收盤價」附近數字
                m2 = re.search(r'(?:前收盤價|Previous close)[^\d]+([\d,\.]+)', html)
            if m2:
                prev = float(m2.group(1).replace(",",""))

            # 公司名稱
            name = code
            m3 = re.search(r'<title>([^(（<]+)', html)
            if m3:
                name = m3.group(1).strip().split(" - ")[0].strip()

            if price:
                return {"price": price, "prev": prev, "name": name, "exchange": exchange}

        except Exception as e:
            print(f"  Google {exchange}:{code} 失敗: {e}")
            continue

    return None


# ── 快取（每支股票個別快取 5 分鐘）─────────────────────────────
_cache = {}   # { code: {"price", "prev", "name", "ts"} }

def get_price(code):
    now = time.time()
    if code in _cache and now - _cache[code]["ts"] < 300:
        return _cache[code]
    result = fetch_google_price(code)
    if result:
        result["ts"] = now
        _cache[code] = result
    return result


@app.route('/api/price')
def price():
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    if not codes:
        return jsonify({'error': 'no codes'}), 400

    msg_array = []
    for c in codes:
        p = get_price(c)
        if p:
            msg_array.append({
                "c": c,
                "n": p.get("name", c),
                "z": str(p["price"]),
                "y": str(p["prev"]),
            })

    return jsonify({"msgArray": msg_array})


@app.route('/api/debug')
def debug():
    """測試單一股票"""
    code = request.args.get('code', '2330')
    result = fetch_google_price(code)
    return jsonify({"code": code, "result": result})


@app.route('/api/health')
def health():
    return jsonify({'ok': True})


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    app.run(host='0.0.0.0', port=port)
