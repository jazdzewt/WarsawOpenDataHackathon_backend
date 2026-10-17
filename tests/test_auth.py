import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import get_db
from app.main import app
from app.models.user import User

# Silne hasło spełniające wszystkie wymogi (długość, małe/wielkie litery, cyfra, znak specjalny).
STRONG_PASSWORD = "Tajne-Haslo-123"
EMAIL = "jan.kowalski@example.com"


def register(client: TestClient, email: str = EMAIL, password: str = STRONG_PASSWORD):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def login(client: TestClient, email: str = EMAIL, password: str = STRONG_PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- Rejestracja ---


def test_register_creates_account_without_exposing_password(client: TestClient) -> None:
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == EMAIL
    # Hash ani hasło nie mogą wrócić w odpowiedzi.
    assert "password" not in body
    assert "password_hash" not in body


def test_register_normalizes_email_case(client: TestClient) -> None:
    response = register(client, email="  Jan.Kowalski@EXAMPLE.com ")
    assert response.status_code == 201
    assert response.json()["email"] == EMAIL


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    register(client)
    response = register(client, email="JAN.KOWALSKI@example.com")
    assert response.status_code == 409


def test_register_rejects_invalid_email(client: TestClient) -> None:
    assert register(client, email="nie-email").status_code == 422


def test_register_rejects_weak_passwords(client: TestClient) -> None:
    weak_passwords = [
        "Krotkie1!",  # za krótkie (poniżej 12 znaków)
        "tajne-haslo-123!",  # brak wielkiej litery
        "TAJNE-HASLO-123!",  # brak małej litery
        "Tajne-Haslo-abc!",  # brak cyfry
        "TajneHasloAbc123",  # brak znaku specjalnego
    ]
    for password in weak_passwords:
        response = register(client, email=f"user{len(password)}@example.com", password=password)
        assert response.status_code == 422, password


def test_register_accepts_only_email_and_password(client: TestClient) -> None:
    # Dodatkowe pola (np. imię) są ignorowane - przyjmujemy wyłącznie e-mail i hasło.
    response = client.post(
        "/api/v1/auth/register",
        json={"email": EMAIL, "password": STRONG_PASSWORD, "name": "Jan"},
    )
    assert response.status_code == 201
    assert "name" not in response.json()


# --- Logowanie ---


def test_login_returns_jwt(client: TestClient) -> None:
    register(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2  # format JWT: header.payload.signature
    assert body["expires_in"] > 0


def test_login_rejects_wrong_password_and_unknown_email_the_same_way(client: TestClient) -> None:
    register(client)
    wrong_password = login(client, password="Inne-Haslo-123!")
    unknown_email = login(client, email="nikt@example.com")
    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_login_is_case_insensitive_for_email(client: TestClient) -> None:
    register(client)
    assert login(client, email="JAN.KOWALSKI@example.com").status_code == 200


def test_password_is_stored_as_hash(client: TestClient) -> None:
    register(client)
    # Sięgamy do bazy przez tę samą sesję, której używa aplikacja w testach.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        user = db.scalar(select(User).where(User.email == EMAIL))
        assert user is not None
        assert user.password_hash != STRONG_PASSWORD
        # Identyfikator algorytmu Argon2id - potwierdza, że hash nie jest jawnym hasłem.
        assert user.password_hash.startswith("$argon2id$")
    finally:
        db.close()


# --- Ochrona endpointów (weryfikacja JWT) ---


def test_protected_endpoint_requires_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_protected_endpoint_rejects_malformed_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_header("to-nie-jest-jwt"))
    assert response.status_code == 401


def test_protected_endpoint_accepts_valid_token(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]
    response = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_token_with_forged_signature_is_rejected(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    # Token podpisany innym kluczem nie może być zaakceptowany.
    forged = jwt.encode(claims, "inny-sekret-ktory-nie-jest-prawdziwy-32", algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers=auth_header(forged)).status_code == 401


def test_token_with_none_algorithm_is_rejected(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    unsigned = jwt.encode(claims, key=None, algorithm="none")
    assert client.get("/api/v1/auth/me", headers=auth_header(unsigned)).status_code == 401


# --- Wylogowanie ---


def test_logout_invalidates_token(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 200

    assert client.post("/api/v1/auth/logout", headers=auth_header(token)).status_code == 204

    # Token jest nadal kryptograficznie poprawny, ale sesja została usunięta.
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 401


def test_logout_only_affects_the_token_used(client: TestClient) -> None:
    register(client)
    first = login(client).json()["access_token"]
    second = login(client).json()["access_token"]

    client.post("/api/v1/auth/logout", headers=auth_header(first))

    assert client.get("/api/v1/auth/me", headers=auth_header(first)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=auth_header(second)).status_code == 200


def test_logout_requires_token(client: TestClient) -> None:
    assert client.post("/api/v1/auth/logout").status_code == 401


# --- Usuwanie konta ---


def test_delete_account_requires_correct_password(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]

    response = client.request(
        "DELETE",
        "/api/v1/auth/me",
        headers=auth_header(token),
        json={"password": "Zle-Haslo-123!"},
    )
    assert response.status_code == 403
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 200


def test_delete_account_removes_user_and_sessions(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]

    response = client.request(
        "DELETE",
        "/api/v1/auth/me",
        headers=auth_header(token),
        json={"password": STRONG_PASSWORD},
    )
    assert response.status_code == 204

    # Token nie działa już po usunięciu konta.
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 401
    # Konto nie może się ponownie zalogować.
    assert login(client).status_code == 401


def test_delete_account_requires_token(client: TestClient) -> None:
    response = client.request("DELETE", "/api/v1/auth/me", json={"password": STRONG_PASSWORD})
    assert response.status_code == 401


# --- SQL injection ---


def test_sql_injection_in_login_is_not_possible(client: TestClient) -> None:
    register(client)
    payloads = ["' OR '1'='1", "admin'--", "' OR 1=1 --"]
    for payload in payloads:
        response = login(client, email=payload, password=payload)
        # Adres e-mail z payloadem nie przechodzi walidacji (422) albo nie znajduje konta (401).
        assert response.status_code in (401, 422), payload
