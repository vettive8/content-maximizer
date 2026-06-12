# DAST: OWASP ZAP (localhost)

## Wykryte URL i scope

- Frontend: `http://localhost:5173/`
- Backend API: `http://localhost:5000/` (endpointy pod `/api/*`)
- Scope ograniczony do localhost (context regex):
  - `^http://localhost:5173.*`
  - `^http://127\.0\.0\.1:5173.*`
  - `^http://localhost:5000.*`
  - `^http://127\.0\.0\.1:5000.*`

## Metodologia

- Narzedzie: `OWASP ZAP 2.17.0` (daemon/headless).
- Etap 1: `Passive scan`
  - seed URL + spider (frontend i backend), oczekiwanie az `pscan recordsToScan == 0`.
- Etap 2: `Active scan` (tylko localhost, in-scope-only)
  - active scan frontend (`http://localhost:5173/`)
  - active scan backend (`http://localhost:5000/api/health`)
- Raportowanie:
  - `docs/testing/reports/zap-report.html`
  - `docs/testing/reports/zap-report.json`

## Procedura krok-po-kroku (odtwarzalna)

### A. Uruchom aplikacje lokalnie

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe server.py
```

Frontend (drugi terminal):

```powershell
cd C:\Development\ContentSaaS
npm run dev -- --host 0.0.0.0 --port 5173
```

Weryfikacja:
- `http://localhost:5000/api/health` -> HTTP 200
- `http://localhost:5173/` -> HTTP 200

### B. Uruchom ZAP (headless)

```powershell
C:\Program Files\ojdkbuild\java-17-openjdk-17.0.3.0.6-1\bin\java.exe `
  -Xmx1024m `
  -jar C:\Development\ContentSaaS\tools\zap\ZAP_2.17.0\ZAP_2.17.0\zap-2.17.0.jar `
  -daemon -host 127.0.0.1 -port 8090 `
  -config api.disablekey=true `
  -config api.addrs.addr.name=127.0.0.1 `
  -config api.addrs.addr.regex=true
```

Sprawdzenie API ZAP:

```powershell
Invoke-RestMethod http://127.0.0.1:8090/JSON/core/view/version/
```

### C. Passive + Active scan + raport (automatycznie)

```powershell
python docs/testing/reports/run_zap_scan.py
```

Skrypt:
- tworzy nowa sesje ZAP,
- ustawia context i scope tylko na localhost,
- wykonuje spider + passive scan,
- wykonuje active scan in-scope-only,
- eksportuje HTML i JSON report.

## Podsumowanie alertow

Wynik 1 (alerty pogrupowane, z `zap-report.json`):

| Poziom | Liczba |
|---|---:|
| High | 0 |
| Medium | 6 |
| Low | 3 |
| Info | 2 |

Wynik 2 (instancje alertow, z `core/view/alerts`):

| Poziom | Liczba |
|---|---:|
| High | 0 |
| Medium | 42 |
| Low | 28 |
| Info | 7 |

## Top 3 alerty i rekomendacje

1. `Content Security Policy (CSP) Header Not Set` (Medium)
- Dotyczy frontendu i backendu.
- Rekomendacja: ustawic naglowek `Content-Security-Policy` (co najmniej `default-src 'self'` + jawne whitelisty dla skryptow, stylow i fontow).

2. `Cross-Domain Misconfiguration` (Medium)
- Dotyczy API (`Access-Control-Allow-Origin: *`).
- Rekomendacja: zawezic CORS do zaufanych originow frontendu (np. `http://localhost:5173` w dev; konkretna lista domen w prod), ograniczyc metody i naglowki.

3. `Missing Anti-clickjacking Header` (Medium)
- Dotyczy frontendu.
- Rekomendacja: ustawic `X-Frame-Options: DENY` lub CSP z `frame-ancestors 'none'`/`'self'`.

Dodatkowe obserwacje:
- `X-Content-Type-Options Header Missing` (Low): dodac `X-Content-Type-Options: nosniff`.
- `Server Leaks Version Information` (Low): ukryc/znormalizowac `Server` header.
- `HTTP Only Site` (Medium): w lokalnym dev expected; dla produkcji wymagane HTTPS + HSTS.

## Procedura GUI (jesli chcesz powtorzyc recznie)

1. Otworz ZAP (GUI), wybierz `File -> New Session`.
2. `Contexts` (lewy panel) -> `New Context...` -> nazwa `ContentSaaS_Localhost`.
3. W kontekscie dodaj `Include in Context`:
   - `^http://localhost:5173.*`
   - `^http://127\.0\.0\.1:5173.*`
   - `^http://localhost:5000.*`
   - `^http://127\.0\.0\.1:5000.*`
4. W `Quick Start -> Manual Explore` odwiedz:
   - `http://localhost:5173/`
   - `http://localhost:5000/api/health`
   - `http://localhost:5000/api/categories`
5. PPM na `http://localhost:5173` -> `Attack -> Spider...` (zaznacz context/scope).
6. Poczekaj az pasek Passive Scan zejdzie do `0`.
7. PPM na `http://localhost:5173` -> `Attack -> Active Scan...` -> `In Scope Only`.
8. PPM na `http://localhost:5000/api/health` -> `Attack -> Active Scan...` -> `In Scope Only`.
9. `Report -> Generate Report...`:
   - format HTML -> zapisz jako `docs/testing/reports/zap-report.html`
   - format JSON -> zapisz jako `docs/testing/reports/zap-report.json`

## Artefakty

- `docs/testing/reports/zap-report.html`
- `docs/testing/reports/zap-report.json`
- `docs/testing/reports/zap-alert-summary.json`
- `docs/testing/reports/run_zap_scan.py`
