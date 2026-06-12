# SCA Dependencies (Rozdzial 5)

## Zakres i wykryte pliki zaleznosci

Data skanu: `2026-02-18`

Backend (Python):
- Wykryty manifest: `backend/requirements.txt`
- Brak lockfile Python (`poetry.lock`, `Pipfile.lock`) w repozytorium.

Frontend (Node):
- Manifest: `package.json`
- Lockfile: `package-lock.json` (`lockfileVersion: 3`)
- Bezposrednia zaleznosc dev: `vite@5.4.14`

## Komendy i artefakty raportow

Backend (uruchomione z interpretera `backend/.venv`):

```powershell
.\backend\.venv\Scripts\pip-audit.exe -f json -o docs\testing\reports\pip-audit.json
.\backend\.venv\Scripts\pip-audit.exe > docs\testing\reports\pip-audit.txt
```

Frontend (katalog projektu):

```powershell
npm audit --json > docs\testing\reports\npm-audit.json
npm audit > docs\testing\reports\npm-audit.txt
```

Wygenerowane pliki:
- `docs/testing/reports/pip-audit.json`
- `docs/testing/reports/pip-audit.txt`
- `docs/testing/reports/npm-audit.json`
- `docs/testing/reports/npm-audit.txt`

Uwaga: `pip-audit` zwracal kod wyjscia `1` (wykryte podatnosci) oraz ostrzezenie o braku zapisu do cache lokalnego. Raporty zostaly wygenerowane poprawnie.

## Podsumowanie wynikow

| Narzedzie | Zakres | Critical | High | Medium | Low | Unknown | Wynik |
|---|---|---:|---:|---:|---:|---:|---|
| `pip-audit 2.10.0` | Pakiety zainstalowane w `backend/.venv` | 0 | 0 | 0 | 0 | 2 | `FAIL` (2 podatnosci w pakiecie `pip`) |
| `npm audit` (npm 10.8.2) | Zaleznosci z `package-lock.json` | 0 | 0 | 2 | 0 | 0 | `FAIL` (2 podatnosci: `vite`, `esbuild`) |

Wyjasnienie kolumny `Unknown`:
- `pip-audit` w formacie JSON nie zwraca poziomu severity dla kazdej CVE, wiec klasyfikacja C/H/M/L nie jest bezposrednio dostepna w tym raporcie.

## Top podatnosci i rekomendacje

| Priorytet | Podatnosc | Gdzie | Rekomendacja |
|---|---|---|---|
| 1 | `CVE-2026-1703` (path traversal przy instalacji wheel) | `pip 25.0.1` | `update`: podniesc `pip` do `>=26.0` w `backend/.venv` i obrazach CI. |
| 2 | `CVE-2025-8869` (problem ekstrakcji tar/symlink) | `pip 25.0.1` | `update`: minimalnie `pip>=25.3`; preferowane `26.0` (zamyka obie CVE). |
| 3 | `GHSA-67mh-4wv8-2f99` + pozostale advisories dla `vite` | `vite 5.4.14` / transytywnie `esbuild` | `update`: podniesc `vite` do `5.4.21` (non-breaking wg audit) i odswiezyc lockfile; `pin`: zablokowac wersje `vite>=5.4.21`. |

Dodatkowa decyzja tymczasowa (jesli update nie moze byc wdrozony od razu):
- `ignore` warunkowy tylko dla srodowiska lokalnego dev, z ograniczeniem dostepu do dev servera (brak ekspozycji publicznej) i terminem wygasniecia akceptacji ryzyka.

## Wnioski do Rozdzialu 5

- W warstwie zaleznosci wykryto podatnosci i wynik SCA jest negatywny (`FAIL`) do czasu aktualizacji `pip` i `vite`.
- Najwazniejsze ryzyka dotycza narzedzi deweloperskich/runtime tooling, nie logiki domenowej backendu.
- Na tym etapie **nie wykonano automatycznej aktualizacji pakietow**; raport zawiera wylacznie stan zastany oraz rekomendacje remediacji.

