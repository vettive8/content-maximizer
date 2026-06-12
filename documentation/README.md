# Dokumentacja projektu Marketing Engine OS

Ten katalog opisuje **aktualny stan implementacji** na podstawie kodu w tym repozytorium.
Dokumentacja zosta³a zsynchronizowana z kodem backendu (`backend/`) i frontendu (`src/`).

## Zakres aplikacji

Aplikacja dzia³a lokalnie jako prototyp typu SPA + API i obejmuje:

- `Maksymalizator Treœci` (YouTube -> transkrypt -> klipy/blog/social).
- `Strategia Wzrostu Biznesu` (analiza rynku, psychoanaliza, creative brief, generowanie skryptów).
- `Zarz¹dzanie skryptami` (statusy `written/scheduled/published`, edycja, link do projektu).
- `Silnik AI` (klucz API i model Gemini).
- `Ustawienia` (jêzyk `pl/en`, motyw `dark/light`).

## Mapa plików

- `quick-start.md` - uruchomienie krok po kroku.
- `architecture.md` - architektura i odpowiedzialnoœci modu³ów.
- `backend-api.md` - kontrakty endpointów Flask.
- `workflows.md` - przep³ywy u¿ytkownika i danych end-to-end.
- `ai-engine.md` - konfiguracja modeli i klucza API.
- `data-persistence.md` - model zapisu JSON i semantyka aktualizacji.
- `security.md` - realnie zaimplementowane zabezpieczenia i luki.
- `testing.md` - testy backendu i sposób uruchamiania.
- `troubleshooting.md` - typowe problemy i diagnostyka.
- `current-state.md` - zwiêz³e podsumowanie stanu projektu i ograniczeñ.

## Wa¿ne za³o¿enia

- Backend domyœlnie dzia³a na `http://localhost:5000`.
- Frontend (Vite) domyœlnie dzia³a na `http://localhost:5173`.
- Aplikacja jest projektowana jako **single-user, local-first prototype**.
- Persistencja to pliki JSON (`backend/data`) oraz pliki wideo (`backend/downloads`).

