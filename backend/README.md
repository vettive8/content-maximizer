# Marketing Engine OS - Backend (Flask)

Ten README ma przede wszystkim pomóc w uruchomieniu projektu.

## Jak Uruchomić Aplikację

## A) Pierwsze uruchomienie (jednorazowo)

1. Zainstaluj wymagania systemowe:
- Python `3.10+`
- Node.js `18+` + `npm`
- `ffmpeg` w `PATH` (`ffmpeg -version`)

2. Przygotuj backend:

```bash
cd c:\Development\ContentSaaS\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

3. Przygotuj frontend (z katalogu głównego projektu):

```bash
cd c:\Development\ContentSaaS
npm install
```

4. Opcjonalnie utwórz `backend/.env`:

```env
PORT=5000
GEMINI_MODEL=gemini-3.5-flash
```

`GEMINI_API_KEY` możesz ustawić później z UI w zakładce `Silnik AI`.

## B) Każde kolejne uruchomienie (codzienny start)

Uruchom 2 terminale.

Terminal 1 - backend:

```bash
cd c:\Development\ContentSaaS\backend
.\.venv\Scripts\activate
python server.py
```

Terminal 2 - frontend:

```bash
cd c:\Development\ContentSaaS
npm run dev
```

## C) Konfiguracja klucza Gemini

Po uruchomieniu aplikacji:

1. Wejdź na `http://localhost:5173`.
2. Otwórz zakładkę `Silnik AI`.
3. Wklej klucz API Gemini i wybierz model.
4. Zapisz konfigurację.

Frontend wyśle ustawienia do backendu przez `POST /api/ai/config`.

## D) Sprawdzenie, czy działa

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:5000/api/health`

Przykładowy test:

1. W `Maksymalizatorze Treści` wklej URL YouTube.
2. Uruchom generowanie.
3. Pobierz 1 klip (sprawdza `yt-dlp` + `ffmpeg`).

## Najczęstsze problemy

- `ModuleNotFoundError`:
Sprawdź, czy aktywne jest `backend/.venv` i czy był wykonany `pip install -r requirements.txt`.

- `ffmpeg not found`:
Dodaj `ffmpeg` do `PATH` i uruchom terminal ponownie.

- Frontend działa, backend "milczy":
Sprawdź `GET /api/health` i port `5000`.

- Błędy Gemini (`503`, quota, invalid key):
Zmień model w `Silnik AI`, sprawdź klucz i limity API.

## Co Robi Backend

Backend odpowiada za:

- transkrypty YouTube,
- generowanie AI (`clips`, `blog`, `social`, `business growth strategy`),
- asynchroniczne pobieranie klipów,
- zapis danych projektów/skryptów/transkryptów do JSON.

Kluczowe pliki:

- `server.py`
- `transcript_fetcher.py`
- `content_processor.py`
- `business_growth_strategy_processor.py`
- `download_clip.py`
- `database.py`

## Dalsza Dokumentacja

- Kontrakty API: `backend/docs/backend_api.md`
- Przewodnik frontendu: `backend/docs/frontend_guide.md`
- Szczegółowy setup: `backend/docs/setup_guide.md`
