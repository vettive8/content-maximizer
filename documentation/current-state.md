# Aktualny stan projektu

## 1. Co dzia³a

System dzia³a jako lokalny prototyp end-to-end i zawiera:

- pe³ny workflow Content Maximizer,
- pe³ny workflow Business Growth Strategy,
- zarz¹dzanie skryptami z edycj¹ i zmian¹ statusu,
- konfiguracjê AI (klucz/model) z poziomu UI,
- ustawienia jêzyka i motywu.

## 2. Potwierdzone elementy techniczne

- stream NDJSON dla `/api/process_stream` i `/api/generate_business_growth_strategy`,
- priorytet konfiguracji AI: `header -> payload -> runtime -> env`,
- naprawa JSON i fallback modelowy w procesorach AI,
- zapis atomowy + `RLock` w warstwie danych,
- asynchroniczne joby pobierania klipów z pollingiem,
- automatyczny zapis projektów po zakoñczeniu workflow.

## 3. G³ówne ograniczenia

- brak auth/roles i brak multi-user,
- brak workflow engine po stronie backendu,
- brak wersjonowania artefaktów,
- brak automatycznych testów frontendu,
- brak natywnej integracji Google Docs API,
- zale¿noœæ od zewnêtrznej us³ugi Gemini,
- joby klipów trzymane w pamiêci procesu (restart backendu resetuje stan jobów).

## 4. Ograniczenia danych wejœciowych

- UI akceptuje upload `.txt/.pdf/.docx` dla transkryptów,
- backend odczytuje pliki jako UTF-8 text; najbardziej przewidywalny format to `.txt`.

## 5. Status repo

- dane runtime (`backend/data`, `backend/downloads`) s¹ wykluczone przez `.gitignore`,
- dokumentacja w tym katalogu opisuje stan „as-is” dla aktualnego kodu.


