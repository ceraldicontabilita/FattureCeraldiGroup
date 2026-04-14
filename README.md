# Fatture Ceraldi Group

Registro fatture mobile per Ceraldi Group SRL.

## File

| File | Descrizione |
|------|-------------|
| `fatture_finale.html` | App principale — apri nel browser |
| `proxy_ceraldi.py` | Proxy locale Python (risolve CORS + legge MongoDB) |

## Come usare

### Con proxy MongoDB (consigliato)

```bash
# 1. Installa dipendenze (una volta sola)
pip install pymongo dnspython

# 2. Avvia il proxy
python proxy_ceraldi.py

# 3. Apri nel browser
# http://localhost:8080/fatture_finale.html
```

Il proxy legge le fatture passive direttamente da **MongoDB Atlas** (DB: Gestionale)
e le serve all'app HTML senza problemi CORS.

### Senza proxy (solo locale)

Apri `fatture_finale.html` direttamente nel browser.
Le funzioni di scansione e gestione manuale funzionano normalmente.
La sezione "Importa da Gestionale" richiede il proxy attivo.

## Architettura

- **Database**: Supabase (registro fatture mobile)
- **Sorgente SDI**: MongoDB Atlas `Gestionale.fatture_passive`
- **Proxy**: Python HTTP server su porta 8080
