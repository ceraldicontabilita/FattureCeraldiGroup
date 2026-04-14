#!/usr/bin/env python3
"""
Proxy locale Ceraldi Fatture
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Legge fatture passive da MongoDB Atlas e le serve all'HTML senza CORS.

SETUP (una volta sola):
  pip install pymongo dnspython

AVVIO:
  python proxy_ceraldi.py

BROWSER:
  http://localhost:8080
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json, os, ssl, urllib.request, urllib.parse

MONGO_URI  = "mongodb+srv://Ceraldidatabase:Ceraldi1974.@cluster0.vofh7iz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MONGO_DB   = "Gestionale"
MONGO_COLL = "fatture_passive"
GITHUB_RAW = "https://raw.githubusercontent.com/ceraldicontabilita/FattureCeraldiGroup/main/fatture_finale.html"

def aggiorna_html():
    fname = "fatture_finale.html"
    try:
        req = urllib.request.Request(GITHUB_RAW)
        req.add_header("Cache-Control", "no-cache")
        with urllib.request.urlopen(req, timeout=10, context=ssl.create_default_context()) as r:
            data = r.read()
        with open(fname, "wb") as f:
            f.write(data)
        print(f"[setup] HTML aggiornato da GitHub ({len(data):,} bytes)")
    except Exception as e:
        if os.path.exists(fname):
            print(f"[setup] Uso HTML locale (GitHub non raggiungibile: {e})")
        else:
            print(f"[ATTENZIONE] HTML non trovato: {e}")

def mongo_fatture(anno, mese=None, limit=500):
    import pymongo
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client[MONGO_DB]
    colls = db.list_collection_names()
    coll  = next((c for c in [MONGO_COLL, "invoices", "fatture"] if c in colls), MONGO_COLL)
    filt  = {"anno": int(anno)}
    if mese:
        filt["invoice_date"] = {"$regex": f"^{anno}-{str(mese).zfill(2)}"}
    docs = list(db[coll].find(filt, {"_id": 0}).sort("invoice_date", -1).limit(int(limit)))
    client.close()
    print(f"[mongo] {len(docs)} docs da {coll} — anno={anno} mese={mese or '*'}")
    return docs

class Handler(SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        qs   = dict(urllib.parse.parse_qsl(self.path.split("?",1)[1])) if "?" in self.path else {}

        if path == "/api/fatture-passive":
            try:
                docs = mongo_fatture(qs.get("anno", 2026), qs.get("mese","") or None, qs.get("limit",500))
                self._json(docs)
            except Exception as e:
                print(f"[mongo] ERRORE: {e}")
                self._json({"error": str(e)}, 502)

        elif path == "/proxy/invoices":
            # Fallback impresasemplice.online
            qstr = self.path.split("?",1)[1] if "?" in self.path else ""
            url  = f"https://impresasemplice.online/api/invoices?{qstr}"
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "Mozilla/5.0")
                with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as r:
                    body = r.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._cors(); self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self._json({"error": str(e)}, 502)

        elif path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/fatture_finale.html")
            self.end_headers()
        else:
            super().do_GET()

    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors(); self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

    def log_message(self, fmt, *args):
        print(f"[http] {fmt % args}")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    aggiorna_html()
    print(f"\n{'━'*50}")
    print(f"  ✅  Proxy Ceraldi avviato su http://localhost:8080")
    print(f"  📦  MongoDB: Gestionale.fatture_passive")
    print(f"  🔄  Fallback: impresasemplice.online")
    print(f"{'━'*50}\n")
    HTTPServer(("localhost", 8080), Handler).serve_forever()
