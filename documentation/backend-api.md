# Backend API (Flask)

Bazowy adres: `http://localhost:5000`

## 1. Health I Konfiguracja AI

| Metoda | Endpoint | Opis |
|---|---|---|
| GET | `/api/health` | Status API i informacja, czy dostępny jest klucz Gemini. |
| GET | `/api/ai/config` | Zwraca, czy runtime ma ustawiony klucz + aktualny model. |
| POST | `/api/ai/config` | Ustawia runtime `api_key` i/lub `model`; czyści cache procesorów. |

## 2. Transkrypty

| Metoda | Endpoint | Opis |
|---|---|---|
| POST | `/api/transcript` | Pobiera transkrypt po URL YouTube. Wymagane: `url`. Opcjonalnie: `language` (`pl`/`en`). |
| GET | `/api/transcript/<video_id>` | Pobiera transkrypt po ID filmu. Opcjonalnie query `language`. |

Uwagi:

- Backend ma timeout 45 s dla `POST /api/transcript`.
- Przy sukcesie transkrypt jest zapisywany niezależnie do `backend/data/transcripts`.

## 3. Content Maximizer

| Metoda | Endpoint | Opis |
|---|---|---|
| POST | `/api/process` | Generacja bez streamu (`clips/blog/social`). |
| POST | `/api/process_stream` | Generacja streamowana NDJSON (`clips -> blog -> social`). |
| POST | `/api/clips` | Tylko klipy. |
| POST | `/api/blog` | Tylko blog. |
| POST | `/api/social` | Tylko social media. |
| GET | `/api/categories` | Zwraca mapę kategorii klipów i zakresy czasu. |

### Kontrakt `/api/process_stream`

Request (przykład):

```json
{
  "transcript": "...",
  "segments": [],
  "language": "pl",
  "generate": ["clips", "blog", "social"],
  "ai_config": {
    "api_key": "...",
    "model": "gemini-3.5-flash"
  }
}
```

Stream events (NDJSON):

- `{"type":"progress","stage":"init|clips|blog|social","percent":...,"message":"...","time_remaining":"..."}`
- `{"type":"complete","result":{...}}`

Uwaga: błędy etapów są agregowane w `result.errors`; endpoint zwykle domyka się eventem `complete`.

## 4. Pobieranie Klipów

| Metoda | Endpoint | Opis |
|---|---|---|
| GET | `/api/download_clip` | Tryb synchroniczny (kompatybilność). |
| POST | `/api/download_clip/start` | Start asynchronicznego joba pobierania/wycinania klipu. |
| GET | `/api/download_clip/status/<job_id>` | Status joba (`queued/running/completed/error`) + ETA i progres. |
| GET | `/api/download_clip/file/<job_id>` | Pobranie pliku po statusie `completed`. |

`/api/download_clip/start` zwraca m.in.:

- `job_id`
- `status`
- `stage`
- `progress_percent`
- `estimated_seconds`
- `remaining_seconds`
- `first_download_for_video`
- `source_cached`
- `clip_cached`

## 5. Projekty

| Metoda | Endpoint | Opis |
|---|---|---|
| POST | `/api/save_project` | Zapis projektu. Gdy payload zawiera `id`, następuje aktualizacja istniejącego rekordu. |
| GET | `/api/list_projects` | Lista metadanych projektów. |
| GET | `/api/get_project/<project_id>` | Szczegóły projektu. |
| POST | `/api/delete_project` | Usunięcie projektu po `project_id` (w body). |
| POST | `/api/delete_all_projects` | Usunięcie wszystkich projektów. |

## 6. Business Growth Strategy

| Metoda | Endpoint | Opis |
|---|---|---|
| POST | `/api/generate_business_growth_strategy` | Streamowany workflow: scraping + market research + psychoanalysis + creative brief. |
| POST | `/api/bgs/generate_titles` | Generuje 5 tytułów long-form. |
| POST | `/api/bgs/generate_similar_title` | Generuje 1 podobny tytuł. |
| POST | `/api/bgs/generate_similar_titles` | Generuje wiele podobnych tytułów. |
| POST | `/api/bgs/generate_chapters` | Generuje strukturę rozdziałów. |
| POST | `/api/bgs/generate_script` | Generuje skrypt rozdziału (opcja A/B), z opcjonalną ciągłością `previous_chapter_script`. |

`/api/generate_business_growth_strategy` przyjmuje `multipart/form-data`:

- `website` (opcjonalny URL)
- `context` (opcjonalny tekst)
- `language` (`pl`/`en`)
- `transcripts` (0..n plików)

Uwaga praktyczna: backend odczytuje pliki transkryptów jako UTF-8 (`decode(..., errors='ignore')`).
Najpewniejszy format wejściowy to `.txt`.

## 7. Script Management

| Metoda | Endpoint | Opis |
|---|---|---|
| GET | `/api/scripts/list` | Lista skryptów. |
| POST | `/api/scripts/save` | Zapis nowego skryptu. |
| PUT | `/api/scripts/<script_id>` | Aktualizacja (`status`, `scheduled_date`, `chapters`, `title`). |
| DELETE | `/api/scripts/<script_id>` | Usunięcie skryptu. |

## 8. Nadpisanie Konfiguracji AI Per Request

Backend rozpoznaje konfigurację w nagłówkach i payloadzie.

Nagłówki:

- `X-Gemini-Api-Key`
- `X-Gemini-Model`

Payload:

```json
{
  "ai_config": {
    "api_key": "...",
    "model": "gemini-3.5-flash"
  }
}
```
