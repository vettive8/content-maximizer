# Persistencja danych

## 1. Model zapisu

Aplikacja u¿ywa plików JSON i lokalnego systemu plików.

Œcie¿ki:

- `backend/data/projects.json` - indeks metadanych projektów.
- `backend/data/<project_id>.json` - pe³ny payload projektu.
- `backend/data/scripts.json` - wpisy zarz¹dzanie skryptami.
- `backend/data/transcripts.json` - indeks transkryptów.
- `backend/data/transcripts/<video_id>.json` - pe³ny snapshot transkryptu.
- `backend/downloads/` - cache Ÿróde³ i gotowych klipów.

## 2. Integralnoœæ zapisu

`backend/database.py` implementuje:

- globalny `threading.RLock` (`_DATA_LOCK`),
- zapis atomowy `_atomic_write_json(...)` (`tempfile + os.replace`).

To chroni przed czêœciowo zapisanym JSON w ramach jednego procesu backendu.

## 3. Semantyka `save_project`

- gdy payload zawiera `id`: aktualizacja istniej¹cego projektu,
- gdy brak `id`: utworzenie nowego UUID,
- `created_at` jest zachowywany przy update,
- `updated_at` jest odœwie¿any przy ka¿dym zapisie.

Czyli zapis jest czêœciowo idempotentny po `id`, ale bez wersjonowania historycznego.

## 4. Semantyka Script Management

Wpis skryptu zawiera m.in.:

- `id`
- `project_id`
- `title`
- `status` (`written`, `scheduled`, `published`)
- `scheduled_date`
- `chapters`
- `created_at`

Backend nie wymusza formalnego automatu stanów - aktualizacja statusu to zwyk³e pole.

## 5. Transkrypty

`save_transcript_independently(...)`:

- aktualizuje indeks `transcripts.json`,
- zapisuje pe³ny payload do `transcripts/<video_id>.json`.

Dziêki temu transkrypt jest snapshotem niezale¿nym od póŸniejszych zmian projektu.

## 6. Ograniczenia

- Brak bazy SQL/NoSQL i brak transakcji miêdzy wieloma plikami.
- Brak wersjonowania artefaktów.
- Brak mechanizmu wspó³dzielenia stanu miêdzy wieloma instancjami backendu.
