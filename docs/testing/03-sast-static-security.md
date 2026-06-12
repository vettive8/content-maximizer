# SAST Static Security (Rozdzial 5)

## Zakres i uruchomione narzedzia

Data skanu: `2026-02-18`

Backend:
- Narzedzie: `bandit 1.9.3`
- Komendy:

```powershell
.\backend\.venv\Scripts\bandit.exe -r backend -f json -o docs\testing\reports\bandit.json
.\backend\.venv\Scripts\bandit.exe -r backend > docs\testing\reports\bandit.txt
```

Uwaga techniczna:
- Druga komenda (TXT) wymagala ustawienia `PYTHONIOENCODING=utf-8` z powodu bledu kodowania konsoli Windows (cp1250). Raport koncowy zostal wygenerowany poprawnie w `docs/testing/reports/bandit.txt`.

Frontend (opcjonalnie):
- `semgrep` nie byl dostepny w srodowisku (`command not found`), wiec nie wygenerowano `semgrep.json/txt`.

## Wyniki Bandit: liczba findings wg severity

### Wynik surowy (dokladnie `bandit -r backend`)
- `HIGH`: 80
- `MEDIUM`: 302
- `LOW`: 5233
- `TOTAL`: 5615

### Wynik first-party (filtrowanie interpretacyjne, bez `backend/.venv/*`)
- `HIGH`: 1
- `MEDIUM`: 1
- `LOW`: 6
- `TOTAL`: 8

Dlaczego dwa widoki:
- Skan surowy obejmuje takze `backend/.venv` (biblioteki zewnetrzne), co dominuje liczbe findings.
- Dla oceny bezpieczenstwa kodu projektu kluczowy jest widok first-party.

## Top findings (max 5) i interpretacja

| Priorytet | Finding | Lokalizacja | Klasyfikacja | Interpretacja |
|---|---|---|---|---|
| 1 | `B201` Flask `debug=True` | `backend/server.py:1419` | `realne ryzyko` | Przy uruchomieniu produkcyjnym z debug moze dojsc do ekspozycji debuggera Werkzeug i RCE. W obecnym MVP to tryb developerski, ale wymaga twardej separacji od produkcji. |
| 2 | `B104` bind na `0.0.0.0` | `backend/server.py:1419` | `MVP limitation` | Otwiera nasluch na wszystkich interfejsach. W lokalnym dev akceptowalne, ale w produkcji powinno byc ograniczone przez reverse proxy/firewall i konfiguracje hosta. |
| 3 | `B603` `subprocess.Popen(...)` | `backend/download_clip.py:138` | `false positive (czesciowy)` | Wywolanie jest listowe (bez `shell=True`), a nazwy plikow sa sanitizowane (`_sanitize_title`), wiec ryzyko command injection jest ograniczone. Pozostaje ryzyko operacyjne (niezaufane sciezki/parametry), ale niskie. |
| 4 | `B110` `try/except/pass` (4 wystapienia) | `backend/business_growth_strategy_processor.py:396`, `backend/content_processor.py:1034`, `backend/server.py:1186`, `backend/transcript_fetcher.py:102` | `MVP limitation` | Ciche tlumienie wyjatkow utrudnia detekcje problemow i audyt incydentow. To nie jest bezposrednia podatnosc RCE, ale oslabia obserwowalnosc i reakcje na bledy. |
| 5 | Wysokie findings w `backend/.venv` (`B324`, `B411`, `B613` itd.) | np. `backend/.venv/Lib/site-packages/...` | `false positive` (dla kodu projektu) | Dotyczy kodu zaleznosci i samego narzedzia, nie first-party backendu. Ten szum nalezy adresowac przez SCA/aktualizacje zaleznosci oraz skan z wykluczeniem venv przy analizie kodu aplikacyjnego. |

## Known MVP constraints (swiadome ograniczenia NFR)

1. `localStorage` dla klucza API w frontendzie:
   - `src/utils/storage.js:5`
   - `src/utils/storage.js:12`
   - `src/utils/storage.js:16`
2. Brak warstwy auth/autoryzacji API (brak JWT/session/login middleware):
   - publiczne endpointy Flask widoczne w `backend/server.py` (np. `@app.route(...)`)
   - brak dopasowan dla auth w kodzie Python (`rg ... -g "*.py"` -> brak wynikow)
3. Brak dedykowanego secrets managera:
   - klucz AI pochodzi z env/runtime config: `backend/server.py:35`, `backend/server.py:69`, `backend/server.py:78`
   - brak integracji z vault/key manager w kodzie backendu/frontendu.

## Wniosek do Rozdzialu 5

- SAST backendu wykazal pojedyncze ryzyka first-party o niskiej i sredniej skali oraz jedno ryzyko wysokie zwiazane z trybem uruchomienia developerskiego.
- Najwieksza liczba findings w skanie surowym pochodzi z bibliotek w `backend/.venv`; nie nalezy interpretowac jej jako liczby bledow implementacji first-party.
