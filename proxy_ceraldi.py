#!/usr/bin/env python3
"""
Proxy locale Ceraldi - Fatture v9
Legge le fatture passive direttamente da MongoDB Atlas (Gestionale)
e le serve al file HTML senza problemi CORS.

Avvia con:  python proxy_ceraldi.py
Poi apri:   http://localhost:8080/fatture_finale_fixed.html
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json, os, ssl, urllib.request, urllib.parse

# ── MONGODB ATLAS ──
MONGO_URI   = "mongodb+srv://Ceraldidatabase:Ceraldi1974.@cluster0.vofh7iz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MONGO_DB    = "Gestionale"
MONGO_COLL  = "fatture_passive"   # collection fatture ricevute via SDI

# ── ATLAS DATA API (alternativa REST senza driver) ──
# Se hai abilitato la Data API su Atlas, metti qui il tuo App ID
ATLAS_APP_ID = ""   # es. "data-abcde"
ATLAS_KEY    = "al-Zh8hn1ZPvZwN0liT5FlhETPCuiCcafPIibG0nu5xXLC"

def atlas_find(anno, mese=None, limit=500):
    """Chiama MongoDB Atlas Data API e ritorna lista fatture."""
    if not ATLAS_APP_ID:
        raise RuntimeError("ATLAS_APP_ID non configurato")
    url = f"https://data.mongodb-api.com/app/{ATLAS_APP_ID}/endpoint/data/v1/action/find"
    filt = {"anno": anno}
    if mese:
        filt["$expr"] = {"$eq": [{"$month": "$invoice_date"}, int(mese)]}
    payload = json.dumps({
        "dataSource": "Cluster0",
        "database":   MONGO_DB,
        "collection": MONGO_COLL,
        "filter":     filt,
        "limit":      limit,
        "sort":       {"invoice_date": -1}
    }).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("api-key", ATLAS_KEY)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return json.loads(r.read())["documents"]

def mongo_find_pymongo(anno, mese=None, limit=500):
    """Usa pymongo (se installato) per leggere direttamente."""
    import pymongo
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    db = client[MONGO_DB]
    
    # Determina collection giusta
    colls = db.list_collection_names()
    coll_name = MONGO_COLL if MONGO_COLL in colls else ("invoices" if "invoices" in colls else MONGO_COLL)
    
    filt = {"anno": anno}
    if mese:
        filt["invoice_date"] = {"$regex": f"^{anno}-{mese.zfill(2)}"}
    
    docs = list(db[coll_name].find(filt, {"_id": 0}).sort("invoice_date", -1).limit(limit))
    client.close()
    return docs

class ProxyHandler(SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/fatture-passive"):
            self._handle_fatture()
        elif self.path.startswith("/proxy/invoices"):
            # Fallback: chiama impresasemplice.online
            self._handle_proxy_invoices()
        else:
            super().do_GET()

    def _handle_fatture(self):
        """Legge fatture da MongoDB Atlas e le restituisce."""
        qs = {}
        if "?" in self.path:
            qs = dict(urllib.parse.parse_qsl(self.path.split("?", 1)[1]))
        anno = int(qs.get("anno", 2026))
        mese = qs.get("mese", "")

        try:
            # Prova prima pymongo
            try:
                docs = mongo_find_pymongo(anno, mese or None)
                source = "pymongo"
            except Exception as e1:
                print(f"[pymongo] {e1} — provo Data API")
                docs = atlas_find(anno, mese or None)
                source = "data_api"

            print(f"[fatture] {len(docs)} docs anno={anno} mese={mese or '*'} via {source}")
            self._json(docs)

        except Exception as e:
            print(f"[fatture] ERRORE: {e}")
            self._json({"error": str(e)}, 502)

    def _handle_proxy_invoices(self):
        """Proxy verso impresasemplice.online (fallback)."""
        qs = self.path.split("?", 1)[1] if "?" in self.path else ""
        url = f"https://impresasemplice.online/api/invoices?{qs}"
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                data = r.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self._json({"error": str(e)}, 502)

    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

    def log_message(self, fmt, *args):
        print(f"[proxy] {fmt % args}")

if __name__ == "__main__":
    port = 8080
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"\n{'='*50}")
    print(f"  Proxy Ceraldi Fatture")
    print(f"  http://localhost:{port}/fatture_finale_fixed.html")
    print(f"{'='*50}\n")
    print("Installa dipendenze se mancanti:")
    print("  pip install pymongo dnspython\n")
    HTTPServer(("localhost", port), ProxyHandler).serve_forever()
