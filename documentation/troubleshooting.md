# Rozwiązywanie problemów

## 1. Backend nie startuje

Objawy:

- `ModuleNotFoundError` (np. `bs4`),
- błąd importu modułów backendu,
- brak odpowiedzi na `/api/health`.

Kroki:

1. aktywuj właściwe `venv` (`backend/.venv`),
2. uruchom `pip install -r backend/requirements.txt`,
3. sprawdź `python backend/server.py`.

## 2. Frontend "wisi" na pobieraniu transkryptu

Objawy:

- pasek postępu stoi na etapie transkryptu,
- brak dalszych kroków generacji.

Kroki:

1. sprawdź, czy backend działa na `localhost:5000`,
2. otwórz `http://localhost:5000/api/health`,
3. sprawdź poprawność URL YouTube,
4. sprawdź log backendu (timeout transkryptu to 45 s).

## 3. Błędy generacji AI (`503`, parse JSON, limity)

Objawy:

- endpointy AI zwracają błąd,
- komunikaty o przeciążeniu dostawcy,
- błędy parsera JSON w odpowiedzi modelu.

Kroki:

1. ponów żądanie,
2. zmień model w `Silnik AI`,
3. sprawdź poprawność klucza i limity API,
4. dla Business Growth Strategy sprawdź log backendu (`[JSON ERROR]`).

## 4. Nie działa pobieranie klipów

Kroki:

1. sprawdź `ffmpeg -version`,
2. sprawdź czy `yt-dlp` może pobrać dany film,
3. monitoruj `GET /api/download_clip/status/<job_id>`.

Uwagi:

- pierwszy klip dla filmu bywa najwolniejszy,
- kolejne klipy są szybsze dzięki cache.

## 5. Eksport Google Docs

Aktualny mechanizm:

- aplikacja próbuje skopiować tekst do schowka,
- otwiera `https://docs.new`.

Jeśli nie działa:

1. sprawdź uprawnienia schowka w przeglądarce,
2. wyłącz blokery popupów,
3. skopiuj ręcznie treść i wklej do dokumentu.

## 6. PDF jest obcięty lub nieczytelny

Kroki:

1. przed eksportem odśwież sekcję i przewiń ją do końca,
2. spróbuj ponownie przy mniejszym zoomie przeglądarki,
3. użyj eksportu TXT jako formatu awaryjnego.

