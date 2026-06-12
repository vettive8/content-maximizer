# Ewaluacja Hipotez H1-H5 (na podstawie telemetryki)

## 1) Zrodla metryk i pipeline raportowania

Zidentyfikowane zrodla:
- `backend/data/metrics.json` - glowne repozytorium zdarzen telemetrycznych (`job` + `event`).
- `backend/generate_metrics_report.py` - generator raportow CSV/JSON do `backend/data/reports/`.
- `backend/server.py` - emituje metryki jobowe przez `_record_metric(...)`.
- `backend/database.py` - emituje metryki eventowe (`script_created`, `script_status_transition`, `script_chapters_updated`) oraz dopisana metryka H5 `post_generation_edit_count`.

Uruchomione raportowanie:

```powershell
.\backend\.venv\Scripts\python.exe backend\generate_metrics_report.py
.\backend\.venv\Scripts\python.exe docs\testing\reports\generate_hypothesis_artifacts.py
```

Artefakty:
- `docs/testing/reports/metrics-report.csv`
- `docs/testing/reports/metrics-summary.json`
- `docs/testing/reports/metrics-h1-times.csv`
- `docs/testing/reports/metrics-h2-quality.csv`
- `docs/testing/reports/metrics-h3-process-errors.csv`
- `docs/testing/reports/metrics-h4-ai-share.csv`
- `docs/testing/reports/metrics-h5-post-generation-edits.csv`
- `docs/testing/figures/h1_total_seconds_per_workflow.png`
- `docs/testing/figures/h4_ai_share_distribution.png`
- `docs/testing/figures/retries_errors_per_workflow.png`

## 2) H1 - czas przygotowania (median / p90 / p95)

Metryki policzone z `metrics.json` (workflow-level):

| Workflow | Runs (total/completed/error) | Median [s] | p90 [s] | p95 [s] |
|---|---:|---:|---:|---:|
| `business-growth-strategy-stream` | 20 / 14 / 6 | 0.021 (all), 0.013 (completed) | 94.671 (all), 68.774 (completed) | 106.097 (all), 153.309 (completed) |
| `content-maximizer-stream` | 11 / 8 / 3 | 0.002 (all), 0.002 (completed) | 323.659 (all), 326.537 (completed) | 328.456 (all), 329.894 (completed) |
| `transcript-fetch` | 22 / 13 / 9 | 0.002 (all), 1.687 (completed) | 1.770 (all), 1.785 (completed) | 1.786 (all), 1.847 (completed) |
| `clip-download` | 3 / 3 / 0 | 38.633 | 62.029 | 64.954 |
| `content-maximizer-sync` | 17 / 17 / 0 | 0.000 | 0.000 | 0.001 |

Interpretacja:
- Rozklady sa silnie mieszane (bardzo szybkie przebiegi testowe + dluzsze przebiegi realne), dlatego sam median bywa bliski 0 dla niektorych workflow.
- Dla oceny operacyjnej bardziej informatywne sa ogony (`p90`, `p95`) i wykres `h1_total_seconds_per_workflow.png`.
- Najdluzsze zadania sa w warstwie AI stream (`content-maximizer-stream`, `business-growth-strategy-stream`), co wspiera teze o dominacji inference w calkowitym czasie.

## 3) H2 - proxy jakosci (score / valid_schema / repair_count)

Poniewaz nie ma bezposredniej etykiety eksperckiej w telemetryce, uzyto proxy:
- `score`: `h2_clip_quality_score_avg`
- `valid_schema_proxy`: brak bledow typu `schema`/`parse` w job error (proxy techniczne)
- `repair_count_proxy`: `gemini_retries`

Wyniki (`content-maximizer-*`, N=28 jobow):
- `score_median`: `0.0`
- `score_p90`: `0.0`
- `score_p95`: `5.233`
- `score_max`: `8.531`
- `quality_nonzero_rows`: `2 / 28`
- `valid_schema_proxy_rate`: `100.0%` (brak errorow `schema`/`parse`)
- `repair_count_proxy_total`: `0`

Interpretacja:
- Sygnal jakosci jest niejednorodny; wiekszosc rekordow ma score = 0 (czesto szybkie przebiegi testowe lub sciezki bez realnej analizy klipow).
- Proxy `valid_schema` jest dodatni, ale to miara techniczna, nie semantyczna.
- Telemetria nie zawiera jeszcze bezposredniej oceny trafnosci merytorycznej (np. eksperckiej oceny 1-5), wiec H2 nalezy interpretowac ostroznie.

## 4) H3 - ograniczenie bledow procesowych (invalid transitions)

Wyniki z eventow `script_status_transition`:
- `transitions_total`: `8`
- `invalid_transitions`: `1`
- `invalid_transition_rate_percent`: `12.5%`
- Jedyna para niepoprawna: `published -> written` (count = 1)

Opis testu negatywnego:
- Wykonany zewnetrznie test black-box (Postman/Newman): niedozwolone przejscie statusu `published -> written` przez `PUT /api/scripts/<id>` zwrocilo `success=false` (PASS scenariusza negatywnego).

Interpretacja:
- Maszyna stanow blokuje niedozwolone przejscia, co potwierdza H3 na poziomie technicznym.

## 5) H4 - udzial czasu AI (`ai_share`) i ograniczenia metryk czasu

Wyniki:
- `rows_total`: `34`
- `ai_share_median`: `0.0%`
- `ai_share_p90`: `98.803%`
- `ai_share_p95`: `125.455%`
- `ai_share_max`: `223.75%`
- `over_100_count`: `2` przypadki

Interpretacja przypadkow `>100%`:
- To nie jest fizycznie "za duzo AI", tylko artefakt sposobu pomiaru:
  - `stage_seconds` sa mierzone na roznych granicach czasowych w endpointach stream,
  - czesc etapow ma nakladajace sie okna czasowe (start/stop nie sa symetryczne),
  - suma etapow AI bywa wiec wieksza od `total_seconds`.

Ograniczenie metody:
- `stage_seconds` i `total_seconds` nie sa idealnie zgodne semantycznie w kazdym workflow.
- Wnioski H4 nalezy opierac na trendzie (AI dominuje ogon czasu), nie na bezwzglednym procentowaniu kazdego pojedynczego joba.

## 6) H5 - metryka edycji po generacji (instrumentacja + probka N>=5)

Brakujaca metryka zostala dopisana minimalnie:
- Plik: `backend/database.py`
- Nowy event: `post_generation_edit_count`
- Emisja przy `update_script(..., chapters=...)`
- Pola: `script_id`, `project_id`, `edit_count`, `chapter_count_before`, `chapter_count_after`

Zebrana probka:
- Sztuczny mini re-run przez API (`/api/scripts/save` + `/api/scripts/<id>` update chapters) dla `N=5`.
- Wynik w telemetryce:
  - `sample_size`: `5`
  - `edit_count_median`: `3`
  - `edit_count_p90`: `3.0`
  - `edit_count_p95`: `3.0`
  - `edit_count_max`: `3`

Wniosek:
- Telemetria H5 jest juz gotowa do dalszej obserwacji produkcyjnej; obecna probka ma charakter kalibracyjny (kontrolowany re-run), ale spelnia wymog minimalnego zbioru i odblokowuje dalsza analize edycji post-generacyjnych.
