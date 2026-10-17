# WarsawOpenDataHackathon – backend

Backend API oparte o FastAPI i SQLAlchemy (baza SQLite). Projekt udostępnia endpoint zdrowia aplikacji oraz uwierzytelnianie JWT (rejestracja, logowanie, wylogowanie, usuwanie konta).

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
   | `JWT_SECRET_KEY` | **wymagane**           | Klucz podpisu tokenów JWT (min. 32 znaki)    |
   | `JWT_ALGORITHM`  | `HS256`                | Algorytm podpisu JWT                         |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`      | Czas ważności tokenu JWT w minutach          |

   `JWT_SECRET_KEY` nie ma wartości domyślnej - bez niego aplikacja nie wystartuje. Losowy klucz wygenerujesz poleceniem:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Jeśli `.env` nie istnieje, używane są wartości domyślne (poza `JWT_SECRET_KEY`, który trzeba podać zawsze).

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

## Uwierzytelnianie

Endpointy kont znajdują się pod prefiksem `/api/v1/auth`:

| Metoda   | Ścieżka          | Opis                                                        |
| -------- | ---------------- | ----------------------------------------------------------- |
| `POST`   | `/register`      | Tworzy konto (body: `email`, `password`)                    |
| `POST`   | `/login`         | Zwraca token JWT (`access_token`, `token_type`, `expires_in`) |
| `POST`   | `/logout`        | Unieważnia bieżący token (usuwa sesję w bazie)              |
| `GET`    | `/me`            | Dane zalogowanego użytkownika (przykład chronionego endpointu) |
| `DELETE` | `/me`            | Usuwa konto (body: `password` - wymagane potwierdzenie)     |

Wymogi hasła: co najmniej 12 znaków, mała i wielka litera, cyfra oraz znak specjalny.
Hasła są hashowane algorytmem Argon2id i nigdy nie są zapisywane w postaci jawnej.

Chronione endpointy wymagają nagłówka `Authorization: Bearer <token>`. Token jest akceptowany tylko wtedy, gdy:
podpis jest poprawny, nie wygasł i sesja o jego identyfikatorze (`jti`) nadal istnieje w bazie.
Wylogowanie usuwa tę sesję, więc token przestaje działać natychmiast.

Aby zabezpieczyć nowy endpoint, dodaj zależność:

```python
from app.api.dependencies import get_current_user

@router.get("/moj-endpoint")
def moj_endpoint(user: User = Depends(get_current_user)) -> ...:
    ...
```

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

Plik `.env` nie jest kopiowany do obrazu (patrz `.dockerignore`). Konfigurację w kontenerze przekazuj przez flagę `-e`, np. `-e DEBUG=true`. Klucz `JWT_SECRET_KEY` jest wymagany, więc trzeba go podać przy każdym uruchomieniu: `-e JWT_SECRET_KEY=<losowy-klucz>`.
