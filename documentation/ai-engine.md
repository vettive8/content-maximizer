# Silnik AI: konfiguracja klucza i modelu

## 1. Cel modu³u

`Silnik AI` pozwala ustawiæ klucz Gemini API i model bez edycji backendu.
Konfiguracja jest zapisywana lokalnie i synchronizowana do runtime backendu.

## 2. Przechowywanie po stronie frontendu

`src/utils/storage.js` zapisuje wartoœci w `localStorage`:

- `meos_gemini_api_key`
- `meos_selected_model`

Domyœlny model: `gemini-3.1-flash-lite-preview`.

## 3. Synchronizacja do backendu

Frontend wywo³uje:

- `POST /api/ai/config`

Wywo³anie nastêpuje:

- na starcie aplikacji (`syncAIConfigToBackend`),
- po zapisie klucza,
- po zmianie modelu.

Backend aktualizuje `_runtime_ai_config` oraz czyœci cache procesorów (`_processor_cache`).

## 4. Priorytet Ÿróde³ konfiguracji (backend)

Dla requestów generuj¹cych backend stosuje kolejnoœæ:

1. Nag³ówki `X-Gemini-Api-Key` / `X-Gemini-Model`
2. `ai_config` w body
3. runtime config (`/api/ai/config`)
4. env (`GEMINI_API_KEY`, `GEMINI_MODEL`)

Dodatkowo `get_processor(...)` ma fallback do env, gdy runtime jest pusty.

## 5. Katalog modeli w UI

Modele zdefiniowane w `src/data/models.js`:

- `gemini-3.1-flash-lite-preview` (recommended)
- `gemini-3-flash-preview`
- `gemini-3.1-pro-preview`
- `gemini-3.1-pro-preview-customtools`
- `gemini-3-pro-preview` (deprecated, shutdown 9 marca 2026)

Uwaga: katalog modeli UI jest niezale¿ny od dostêpnoœci modeli po stronie dostawcy API.

## 6. Znane ograniczenia

- Klucz API jest przechowywany w `localStorage` (wygodne, ale s³absze bezpieczeñstwo).
- Brak centralnego mened¿era sekretów i brak auth u¿ytkowników.
- Gdy klucz jest b³êdny/brak limitu, endpointy generowania zwracaj¹ b³êdy runtime.

