# Bezpieczeństwo: stan faktyczny

## 1. Co jest zaimplementowane

### 1.1 Sanitizacja treści w frontendzie

Plik: `src/utils/sanitize.js`

Używane mechanizmy:

- `escapeHtml(...)`
- `escapeAttribute(...)`
- `decodeHtmlEntities(...)`
- `sanitizeDeep(...)` dla struktur zagnieżdżonych

To ogranicza ryzyko XSS przy renderowaniu treści z modelu/transkryptu.

### 1.2 Normalizacja danych wejściowych

- normalizacja języka (`pl/en`) po stronie backendu,
- walidacja i normalizacja zakresów czasowych klipów,
- sanitizacja nazwy pliku klipu (`download_clip.py`).

### 1.3 Integralność danych

- zapis atomowy JSON (`tempfile + os.replace`),
- blokada `RLock` w persistencji.

### 1.4 Ograniczenie ekspozycji klucza

- `GET /api/ai/config` zwraca tylko `configured` + `model` (bez pełnego klucza),
- backend akceptuje klucz z nagłówka/payload/runtime/env.

## 2. Luki bezpieczeństwa (istotne)

- Brak logowania, autoryzacji i ról.
- Klucz API przechowywany w `localStorage`.
- Brak CSRF/session modelu.
- Brak rate limitingu.
- `CORS(app)` bez ograniczenia originów (tryb deweloperski).
- Brak pełnej walidacji schematów JSON na wejściu.

## 3. Ograniczenia publikacyjne i eksportowe

- Eksport PDF w Planie Gry działa po stronie przeglądarki (`html2pdf` z CDN).
- Eksport do Google Docs to workflow `kopiuj + docs.new`, bez OAuth i API Google.

## 4. Rekomendacje na produkcję

1. Wdrożyć auth + role + izolację tenantów.
2. Przenieść sekrety do backend secret store, usunąć `localStorage` dla klucza.
3. Ograniczyć CORS do zaufanych domen.
4. Dodać rate limiting i monitoring błędów.
5. Wprowadzić walidację schematów request/response (np. JSON Schema/Pydantic).
6. Zastąpić pliki JSON bazą danych i kolejką zadań.
