# Warstwa 1: Unit + Integration (pytest)

## Srodowisko uruchomienia
- Data uruchomienia: `2026-02-18`
- Interpreter: `C:\Development\ContentSaaS\backend\.venv\Scripts\python.exe`
- Katalog roboczy: `C:\Development\ContentSaaS`

Komenda testowa (wynik 53/53 PASS):

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests --cov=backend --cov-report=html --cov-report=term
```

Komenda do policzenia coverage tylko dla modulow produkcyjnych:

```powershell
.\backend\.venv\Scripts\python.exe -m coverage report --include="backend/*.py" --omit="backend/tests/*,backend/test_*.py"
```

Artefakty:
- HTML coverage: `htmlcov/index.html`
- Screenshoty: `coverage-report.png`, `coverage-report-full.png`
- Kopie do pracy: `thesis/writing/thesis/rozdzialy_tresc_md2/coverage-report.png`, `thesis/writing/thesis/rozdzialy_tresc_md2/coverage-report-full.png`

## Wynik testow (Unit + Integration)

| Metryka | Wartosc |
|---|---:|
| Liczba testow (collected) | 53 |
| PASS | 53 |
| FAIL | 0 |
| ERROR | 0 |

## Coverage: wynik i interpretacja

- Coverage surowe (`--cov=backend`): **58%** (`TOTAL 3141 stmt, 1326 miss`).
- Coverage dla modulow produkcyjnych: **50%** (`TOTAL 2520 stmt, 1262 miss`).

Wyjasnienie roznicy 58% vs 50%:
- `58%` liczy wszystko pod `backend/`, w tym pliki testowe (`backend/tests/*`), ktore maja bardzo wysoki coverage i zawyzaja laczny wynik.
- `50%` usuwa pliki testowe z mianownika i zostawia tylko kod produkcyjny; to metryka bardziej adekwatna do oceny jakosci testowania systemu.

## Reprezentatywne testy (10)

| Test | Co sprawdza |
|---|---|
| `backend/tests/test_business_growth_strategy.py::test_extract_json_truncated` | Leczenie obcietego JSON (brakujace nawiasy) i poprawny parse wyniku. |
| `backend/tests/test_json_comma.py::test_extract_json_orphan_video_ideas` | Naprawa osieroconych obiektow JSON przez opakowanie ich w `video_ideas`. |
| `backend/tests/test_content_maximizer.py::test_analyze_transcript_respects_language_and_model` | Przekazanie poprawnego modelu i jezyka do promptu AI. |
| `backend/tests/test_content_maximizer.py::test_analyze_transcript_clamps_out_of_bounds_and_returns_six_clips` | Clamp czasow klipow do zakresu i zwrot 6 kategorii klipow. |
| `backend/tests/test_database.py::test_concurrent_script_writes_do_not_lose_entries` | Brak utraty rekordow przy wspolbieznych zapisach skryptow. |
| `backend/tests/test_database.py::test_update_and_delete_script` | Poprawna aktualizacja statusu/metadanych i usuwanie skryptu. |
| `backend/tests/test_server_api.py::test_process_prefers_header_ai_config` | Priorytet konfiguracji AI z naglowkow HTTP nad `ai_config` w payloadzie. |
| `backend/tests/test_server_api.py::test_process_stream_returns_progress_and_complete` | Poprawny format zdarzen streamu (`progress` -> `complete`). |
| `backend/tests/test_flow.py::test_generate_business_growth_strategy_stream_normalizes_invalid_language_to_polish` | Normalizacja nieobslugiwanego jezyka wejsciowego do `pl`. |
| `backend/tests/test_transcript_utils.py::test_extract_video_id_from_common_formats` | Poprawna ekstrakcja `video_id` z roznych formatow URL YouTube. |

## Tabela: modul -> coverage (Markdown)

| Modul | Coverage |
|---|---:|
| `backend/analyze_json.py` | 0% |
| `backend/benchmark_processing.py` | 0% |
| `backend/business_growth_strategy_processor.py` | 61% |
| `backend/content_processor.py` | 82% |
| `backend/database.py` | 80% |
| `backend/debug_resources.py` | 0% |
| `backend/download_clip.py` | 15% |
| `backend/generate_metrics_report.py` | 0% |
| `backend/reproduce_missing_brace.py` | 0% |
| `backend/run_tests.py` | 0% |
| `backend/schemas.py` | 100% |
| `backend/server.py` | 44% |
| `backend/transcript_fetcher.py` | 24% |
| `backend/website_scraper.py` | 8% |
| **TOTAL (moduly produkcyjne)** | **50%** |

## Tabela: modul -> coverage (LaTeX)

```latex
\begin{table}[htbp]
\centering
\caption{Pokrycie testami modulow produkcyjnych backendu}
\label{tab:backend_coverage_modules}
\begin{tabular}{lr}
\hline
Modul & Coverage [\%] \\
\hline
analyze\_json.py & 0 \\
benchmark\_processing.py & 0 \\
business\_growth\_strategy\_processor.py & 61 \\
content\_processor.py & 82 \\
database.py & 80 \\
debug\_resources.py & 0 \\
download\_clip.py & 15 \\
generate\_metrics\_report.py & 0 \\
reproduce\_missing\_brace.py & 0 \\
run\_tests.py & 0 \\
schemas.py & 100 \\
server.py & 44 \\
transcript\_fetcher.py & 24 \\
website\_scraper.py & 8 \\
\hline
\textbf{TOTAL (moduly produkcyjne)} & \textbf{50} \\
\hline
\end{tabular}
\end{table}
```

## Luki coverage i dlaczego

- `0%` w `analyze_json.py`, `benchmark_processing.py`, `debug_resources.py`, `generate_metrics_report.py`, `reproduce_missing_brace.py`, `run_tests.py`:
  - To pliki narzedziowe/diagnostyczne/benchmarkowe, poza glowna sciezka runtime API.
- Niskie coverage warstwy I/O i integracji zewnetrznej:
  - `download_clip.py` (15%), `transcript_fetcher.py` (24%), `website_scraper.py` (8%).
  - Powod: zaleznosc od sieci, plikow, procesow zewnetrznych i kosztowniejszych scenariuszy E2E.
- `server.py` (44%):
  - Pokryte sa glowne endpointy i przypadki bledow walidacyjnych, ale nie wszystkie galezie obslugi bledow i scenariusze poboczne.

## 58% vs 50%: co wpisujemy do pracy

Do pracy rekomendowane jest podanie **50%** jako glownej liczby coverage, bo dotyczy wylacznie kodu produkcyjnego.

Gotowe zdanie do wklejenia:

> Pokrycie testami modulow produkcyjnych backendu wynioslo **50\%**\footnote{Wartosc obliczona komenda \texttt{coverage report --include="backend/*.py" --omit="backend/tests/*,backend/test\_*.py"}. Surowy wynik \texttt{pytest --cov=backend} wyniosl 58\%, poniewaz uwzglednia rowniez pliki testowe.}.
