# API External Integration Tests (Postman/Newman)

## Narzedzie i artefakty

- Narzedzie zewnetrzne: **Postman Collection v2.1** uruchamiana przez **Newman (CLI)**.
- Kolekcja: `docs/testing/reports/postman-collection.json`
- Environment: `docs/testing/reports/postman-environment.json`
- Trace run: `docs/testing/reports/postman-run.txt`
- Raport maszynowy: `docs/testing/reports/postman-run.json`

Komenda uruchomieniowa:

```powershell
npx --yes newman run docs/testing/reports/postman-collection.json `
  -e docs/testing/reports/postman-environment.json `
  --reporters cli,json `
  --reporter-json-export docs/testing/reports/postman-run.json `
  > docs/testing/reports/postman-run.txt
```

Wynik wykonania (run z dnia `2026-02-18`):
- Requests: `12/12` wykonane
- Assertions: `29`, failed: `0`
- Test scripts failed: `0`

## Tabela wynikow (endpoint -> przypadek -> expected -> wynik)

| Endpoint | Przypadek testowy | Expected | Wynik |
|---|---|---|---|
| `POST /api/ai/config` + `GET /api/ai/config` | Ustawienie i odczyt runtime AI config | `200`, `success=true`, `configured=true` | `PASS` |
| `POST /api/transcript` | Brak pola `url` (walidacja) | `400`, `success=false` | `PASS` |
| `POST /api/transcript` | Scenariusz timeout `504` | `504` po przekroczeniu 45s | `MANUAL/OPTIONAL` (w tym run: `expect_transcript_timeout_504=false`, endpoint zwrocil `200`) |
| `POST /api/process_stream` (NDJSON) | Minimalny stream, weryfikacja pierwszego eventu | `200`, `application/x-ndjson`, pierwszy event `progress/init`, czas < 3s | `PASS` (response time: `97ms`) |
| `POST /api/generate_business_growth_strategy` (NDJSON) | Minimalny stream multipart | `200`, `application/x-ndjson`, pierwszy event `progress/init` | `PASS` |
| `POST /api/save_project` | Zapis projektu | `200`, `success=true`, `project_id` obecne | `PASS` |
| `GET /api/list_projects` | Widocznosc zapisanego projektu | `200`, lista zawiera nowy `project_id` | `PASS` |
| `PUT /api/scripts/<script_id>` | Test negatywny status transition (`published -> written`) | Odrzucenie przejscia (`success=false`) | `PASS` |
| `POST /api/download_clip/start` | Start joba pobierania klipu | `200`, `success=true`, `job_id` obecne | `PASS` |
| `GET /api/download_clip/status/<job_id>` | Odczyt statusu joba | `200`, `success=true`, zgodny `job_id` | `PASS` |

## Trace / dowod wykonania

Dowod wykonania znajduje sie w:
- `docs/testing/reports/postman-run.txt` (pelny log CLI)
- `docs/testing/reports/postman-run.json` (wynik per request/assertion)

Fragment podsumowania z trace:

```text
requests: 12 executed, 0 failed
assertions: 29 executed, 0 failed
total run duration: ~4.3s
```

## Black-box verification FR (krotkie podsumowanie)

Testy wykonane przez zewnetrzne narzedzie (Postman/Newman), bez odwolania do test runnera backendu, potwierdzily:
- poprawna walidacje i kontrakty HTTP dla krytycznych endpointow,
- poprawna obsluge streamingu NDJSON (`process_stream`, `generate_business_growth_strategy`),
- poprawna persystencje i odczyt danych (`save_project` + `list_projects`),
- poprawne wymuszenie maszyny stanow dla skryptow (niedozwolone przejscie odrzucone),
- poprawny lifecycle jobow asynchronicznych (`download_clip/start` + `status`).

Uwaga o `504`:
- scenariusz timeout transkryptu jest w kolekcji jako test kontrolowany (`expect_transcript_timeout_504`),
- aby go wymusic, nalezy wlaczyc `expect_transcript_timeout_504=true` i uruchomic run w warunkach powodujacych przekroczenie 45s po stronie `fetch_transcript`.
