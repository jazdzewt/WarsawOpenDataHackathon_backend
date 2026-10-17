# WarsawOpenDataHackathon – backend

Backend API oparte o FastAPI i SQLAlchemy (baza SQLite). Projekt udostępnia endpointy zdrowia aplikacji oraz CRUD dla zasobu `items`.

## Wymagania

- Python 3.12 (zgodnie z obrazem Dockera)
- Opcjonalnie: Docker

## Uruchomienie lokalne

1. Utwórz i aktywuj wirtualne środowisko w katalogu projektu:

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

   Na Linux/macOS:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Zainstaluj zależności:

   ```bash
   pip install -r requirements.txt
   ```

3. (Opcjonalnie) Utwórz plik `.env` na podstawie `.env.example` i dostosuj wartości:

   ```powershell
   copy .env.example .env
   ```

   Dostępne zmienne:

   | Zmienna          | Domyślnie              | Opis                                         |
   | ---------------- | ---------------------- | -------------------------------------------- |
   | `APP_NAME`       | `FastAPI Template`     | Nazwa aplikacji widoczna w dokumentacji      |
   | `APP_VERSION`    | `0.1.0`                | Wersja aplikacji                             |
   | `DEBUG`          | `false`                | Tryb debugowania FastAPI                     |
   | `API_PREFIX`     | `/api/v1`              | Prefiks wszystkich endpointów API            |
   | `CORS_ORIGINS`   | `["*"]`                | Dozwolone originy (lista w formacie JSON)    |
   | `DATABASE_URL`   | `sqlite:///./app.db`   | Adres bazy danych SQLAlchemy                 |

   Jeśli `.env` nie istnieje, używane są wartości domyślne.

4. Uruchom serwer deweloperski:

   ```bash
   uvicorn app.main:app --reload
   ```

   Aplikacja będzie dostępna pod adresem `http://127.0.0.1:8000`.

   Tabele bazy danych tworzą się automatycznie przy starcie aplikacji.

## Dokumentacja API

Po uruchomieniu serwera:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health check: http://127.0.0.1:8000/health

Endpointy zasobu `items` znajdują się pod prefiksem `/api/v1/items`.

## Testy

```bash
pytest
```

Testy używają osobnej, tymczasowej bazy SQLite w pamięci.

## Uruchomienie w Dockerze

1. Zbuduj obraz:

   ```bash
   docker build -t warsaw-backend .
   ```

2. Uruchom kontener, montując wolumen na bazę danych:

   ```bash
   docker run --rm -p 8000:8000 -v warsaw-data:/data warsaw-backend
   ```

   API będzie dostępne pod `http://localhost:8000`. Baza danych jest zapisywana w `/data/app.db` wewnątrz kontenera, dzięki czemu dane przetrwają restart, o ile wolumen `warsaw-data` istnieje.

Plik `.env` nie jest kopiowany do obrazu (patrz `.dockerignore`). Konfigurację w kontenerze przekazuj przez flagę `-e`, np. `-e DEBUG=true`.
