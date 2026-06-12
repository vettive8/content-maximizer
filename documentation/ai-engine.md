# Silnik AI: konfiguracja klucza i modelu

## 1. Cel Modułu

`Silnik AI` pozwala ustawić klucz Gemini API i model bez edycji backendu.
Konfiguracja jest zapisywana lokalnie i synchronizowana do runtime backendu.

## 2. Przechowywanie Po Stronie Frontendu

`src/utils/storage.js` zapisuje wartości w `localStorage`:

- `meos_gemini_api_key`
- `meos_selected_model`

Domyślny model: `gemini-3.5-flash`.

## 3. Synchronizacja Do Backendu

Frontend wywołuje:

- `POST /api/ai/config`

Wywołanie następuje:

- na starcie aplikacji (`syncAIConfigToBackend`),
- po zapisie klucza,
- po zmianie modelu.

Backend aktualizuje `_runtime_ai_config` oraz czyści cache procesorów (`_processor_cache`).

## 4. Priorytet Źródeł Konfiguracji (backend)

Dla requestów generujących backend stosuje kolejność:

1. Nagłówki `X-Gemini-Api-Key` / `X-Gemini-Model`
2. `ai_config` w body
3. runtime config (`/api/ai/config`)
4. env (`GEMINI_API_KEY`, `GEMINI_MODEL`)

Dodatkowo `get_processor(...)` ma fallback do env, gdy runtime jest pusty.

## 5. Katalog Modeli W UI

Modele zdefiniowane w `src/data/models.js`:

- `gemini-3.5-flash` (recommended, stable)
- `gemini-3.1-flash-lite` (efficient, stable)
- `gemini-3.1-pro-preview`
- `gemini-3-flash-preview` (preview / compatibility option)

Uwaga: katalog modeli UI jest niezależny od dostępności modeli po stronie dostawcy API. Warto sprawdzać oficjalną stronę modeli Gemini przed produkcyjnym wdrożeniem, bo preview IDs mogą być wycofywane.

## 6. Znane Ograniczenia

- Klucz API jest przechowywany w `localStorage` (wygodne, ale słabsze bezpieczeństwo).
- Brak centralnego menedżera sekretów i brak auth użytkowników.
- Gdy klucz jest błędny albo brakuje limitu, endpointy generowania zwracają błędy runtime.
