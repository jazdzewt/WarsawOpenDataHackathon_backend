# Instrukcje dla Claude'a – WarsawOpenDataHackathon backend

Ten plik opisuje zasady pracy w tym repozytorium. Claude ma się do nich stosować przy każdej zmianie.

## Struktura projektu

Warstwy są rozdzielone. Nowa funkcjonalność trafia do odpowiednich katalogów, a nie do jednego pliku:

```
app/
  main.py              # tworzenie aplikacji FastAPI, lifespan, rejestracja routera
  api/
    router.py          # główny router: tylko include_router, bez logiki
    dependencies.py    # zależności (np. get_current_user) do ochrony endpointów
    routes/            # jeden plik na zasób, np. auth.py, health.py, report.py
  core/
    config.py          # ustawienia (pydantic-settings), jedyne miejsce czytania env
    security.py        # hashowanie haseł i obsługa JWT
  db/
    base.py            # DeclarativeBase
    session.py         # engine, SessionLocal, init_db, get_db
  models/              # modele SQLAlchemy, jeden plik na tabelę
  schemas/             # modele Pydantic (wejście/wyjście API), jeden plik na zasób
  services/            # logika biznesowa i zapytania do bazy, jeden plik na zasób
tests/
  conftest.py          # wspólne fixtures (klient testowy, baza w pamięci)
  test_<zasób>.py      # testy jednego zasobu/funkcjonalności
```

Zasady podziału:
- Routes tylko przyjmują żądanie, wołają serwis i zwracają odpowiedź. Zapytań do bazy nie piszemy w routes.
- Serwisy dostają sesję SQLAlchemy w konstruktorze i nie wiedzą nic o HTTP (wyjątki domenowe, np. `InvalidCredentialsError`, są mapowane na kody HTTP w routes).
- Konfiguracja tylko przez `app/core/config.py`. Nie wolno wołać `os.environ` ani czytać `.env` w innych miejscach.
- Nowy zasób = nowy plik w `models/`, `schemas/`, `services/`, `api/routes/` plus wpis w `api/router.py`.

## Zasady kodu

- Komentarze w kodzie piszemy po polsku. Każdy nowo dodany kod ma mieć komentarze wyjaśniające, co i dlaczego się dzieje (zwłaszcza w kodzie bezpieczeństwa).
- Docstringi w serwisach i modułach też po polsku. Nazwy zmiennych, funkcji i klas po angielsku.
- Dopasowujemy się do stylu istniejącego kodu: type hints wszędzie, `Mapped[...]` w modelach, `Depends(...)` w routes.
- Zapytania wyłącznie przez ORM SQLAlchemy (`select`, `delete`, `scalar`). Nigdy nie sklejamy SQL-a z danymi od użytkownika (`text()` z f-stringiem jest zakazane).
- Hasła: wyłącznie hash Argon2id (`app/core/security.py`). Hasło w postaci jawnej nie trafia do bazy, logów ani odpowiedzi API.
- Błędy logowania zwracają jeden, ogólny komunikat (brak wycieku informacji o istnieniu konta).
- Nowe sekrety i ustawienia dodajemy do `Settings` oraz `.env.example`, a README aktualizujemy, jeśli zmienia się sposób uruchamiania.

## Testy – obowiązkowe przy każdej nowej funkcjonalności

Każda nowa funkcjonalność (endpoint, serwis, zmiana zachowania) musi mieć testy zanim zmiana zostanie uznana za gotową:

1. Testy idą do `tests/test_<zasób>.py` (np. `test_auth.py`, `test_report.py`), a nie do `conftest.py` ani do jednego wspólnego pliku.
2. Testy używają fixture `client` z `conftest.py`. Baza testowa jest w pamięci, więc testy nie dotykają `app.db`.
3. Każdy endpoint ma co najmniej: przypadek poprawny, przypadek błędu walidacji (422) lub braku autoryzacji (401/403) oraz przypadek nieistniejącego zasobu (404), jeśli dotyczy.
4. Zmiany bezpieczeństwa mają test negatywny (np. zły token, podrobiony podpis, payload SQL injection).
5. Przed zakończeniem pracy uruchamiamy `pytest` i podajemy wynik. Jeśli testy nie przechodzą, mówimy to wprost, a nie zgłaszamy zadania jako skończonego.

Uruchamianie: `.venv\Scripts\python.exe -m pytest -q` (zależności z `requirements.txt`).

## Porządek w repozytorium

- Nie zostawiamy plików tymczasowych, skryptów testowych ani notatek w katalogu projektu. Tymczasowe pliki idą do katalogu scratchpad, a nie do repo.
- Nie dodajemy dużych plików danych (JSON, CSV) do korzenia repo bez zgody użytkownika. Pliki `boiska.json`, `zajecia.json`, `powietrze.json`, `pogoda.json` i `script.py` należą do zmian innego autora i nie wolno ich modyfikować ani usuwać bez pytania.
- Sekrety (klucze API, JWT) nigdy nie trafiają do plików śledzonych przez git. Dozwolone są tylko placeholdery w `.env.example`.
- Nie tworzymy plików dokumentacji poza README, chyba że użytkownik o to poprosi.

## Git

- Commity i push wykonujemy tylko na wyraźne polecenie użytkownika.
- Nie używamy `--force` na gałęziach zdalnych bez wyraźnej zgody.
- Nie zmieniamy historii `main` (bez `rebase` i `reset` na commitach już wypchniętych).
- Commit message: krótki tytuł po polsku, na końcu linia `Co-Authored-By` zgodnie z aktualnymi wytycznymi.

## Przed zakończeniem zadania – checklista

- [ ] Kod ma polskie komentarze tam, gdzie wyjaśniają logikę lub bezpieczeństwo.
- [ ] Nowa funkcjonalność ma testy w `tests/test_<zasób>.py`, a `pytest` przechodzi.
- [ ] Nie ma nieużywanych importów ani martwego kodu (np. po usunięciu zasobu).
- [ ] Router nie importuje modułów, które nie istnieją.
- [ ] Nowe ustawienia są w `Settings` i `.env.example`.
- [ ] Brak plików tymczasowych w repo i brak sekretów w kodzie.
