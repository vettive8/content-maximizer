# Testowanie

## 1. Jak uruchomiæ testy backendu

Z katalogu projektu:

```bash
python backend/run_tests.py
```

Alternatywa (unittest discover):

```bash
python -m unittest discover -s backend/tests -p "test_*.py"
```

## 2. Zakres obecnych testów

Pliki testowe:

- `backend/tests/test_content_maximizer.py`
- `backend/tests/test_database.py`
- `backend/tests/test_flow.py`
- `backend/tests/test_business_growth_strategy.py`
- `backend/tests/test_json_comma.py`
- `backend/tests/test_server_api.py`
- `backend/tests/test_transcript_utils.py`

Pokrywane obszary:

- kontrakty endpointów Flask,
- logika przetwarzania Content Maximizer,
- logika Business Growth Strategy i naprawa JSON,
- persistencja i semantyka zapisu,
- transkrypty i helpery formatuj¹ce.

## 3. Czego brakuje

- Brak automatycznych testów frontendu (UI/e2e).
- Brak testów obci¹¿eniowych i testów bezpieczeñstwa.

## 4. Minimalna walidacja po zmianach funkcjonalnych

1. uruchomiæ pe³ne testy backendu,
2. sprawdziæ `GET /api/health`,
3. wykonaæ 1 pe³ny przebieg Content Maximizer,
4. wykonaæ 1 pe³ny przebieg Business Growth Strategy,
5. zapisaæ i zaktualizowaæ skrypt w Script Management.

