# Szybki Start (lokalnie)

## 1. Wymagania

- Python `3.10+` (zalecane 3.11/3.12)
- Node.js `18+` oraz `npm`
- `ffmpeg` w `PATH` (wymagane do wycinania klipów)

Sprawdzenie:

```bash
python --version
node --version
npm --version
ffmpeg -version
```

## 2. Backend - Instalacja

### Windows (PowerShell / CMD)

```bash
cd c:\Development\ContentSaaS\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Linux / macOS

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Frontend - Instalacja

W katalogu głównym projektu:

```bash
cd c:\Development\ContentSaaS
npm install
```

## 4. Uruchomienie

### Terminal A (backend)

```bash
cd c:\Development\ContentSaaS\backend
.\.venv\Scripts\activate
python server.py
```

### Terminal B (frontend)

```bash
cd c:\Development\ContentSaaS
npm run dev
```

## 5. Weryfikacja

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:5000/api/health`

Oczekiwany wynik health:

```json
{
  "status": "ok",
  "message": "Content Maximizer API is running",
  "gemini": true
}
```

`gemini: false` oznacza, że backend działa, ale nie ma aktywnego klucza API.

## 6. Konfiguracja Klucza Gemini

Projekt wspiera 2 tryby konfiguracji:

1. `Silnik AI` w frontendzie (zalecane):
- otwórz zakładkę `Silnik AI`,
- wpisz klucz API,
- wybierz model,
- kliknij zapis.

2. `backend/.env` (opcjonalnie):

```env
GEMINI_API_KEY=twoj_klucz
GEMINI_MODEL=gemini-3.5-flash
PORT=5000
```

Uwaga: frontend i tak może nadpisać model/klucz runtime przez `/api/ai/config`.

## 7. Pierwszy Test End-To-End

1. W `Maksymalizatorze Treści` wklej URL YouTube i uruchom generowanie.
2. Poczekaj na zakończenie streamu `/api/process_stream`.
3. Pobierz przynajmniej 1 klip (sprawdza `yt-dlp` + `ffmpeg`).
4. W `Planie Gry` uruchom workflow i wygeneruj tytuły + rozdziały + skrypt.
5. Zapisz skrypt do `Zarządzanie skryptami` i sprawdź zmianę statusu.
