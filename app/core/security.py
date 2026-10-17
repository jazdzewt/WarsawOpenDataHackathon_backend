"""Narzędzia bezpieczeństwa: hashowanie haseł (Argon2id) oraz tworzenie i odczyt tokenów JWT."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

# Argon2id jest odporny na ataki GPU/ASIC. Parametry domyślne biblioteki są zgodne
# z zalecaniami OWASP. Hasło nigdy nie jest przechowywane w postaci jawnej.
_password_hasher = PasswordHasher()

# Hash bez odpowiadającego mu hasła. Służy do wyrównania czasu odpowiedzi logowania,
# gdy e-mail nie istnieje, żeby nie dało się po czasie odpowiedzi zgadywać kont.
DUMMY_PASSWORD_HASH = _password_hasher.hash("dummy-password-for-timing-only")


def hash_password(password: str) -> str:
    """Zwraca hash hasła (Argon2id, z automatyczną solą)."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Sprawdza, czy podane hasło pasuje do zapisanego hasha. Nigdy nie rzuca wyjątku."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int) -> tuple[str, str]:
    """Tworzy podpisany token JWT dla użytkownika.

    Zwraca krotkę (token, jti). Identyfikator `jti` jest zapisywany po stronie serwera
    w tabeli sesji, dzięki czemu wylogowanie może unieważnić konkretny token.
    """
    jti = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),  # identyfikator użytkownika
        "jti": jti,  # unikalny identyfikator tokenu (do unieważniania)
        "iat": now,  # czas wystawienia
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),  # czas wygaśnięcia
    }
    token = jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def decode_access_token(token: str) -> dict:
    """Weryfikuje podpis i termin ważności tokenu, zwraca jego claimy.

    Rzuca `jwt.InvalidTokenError` (lub podklasę), jeśli token jest nieprawidłowy,
    sfałszowany albo wygasły. Algorytm jest jawnie ograniczony do jednego, co chroni
    przed atakiem z podmianą algorytmu (np. na "none").
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub", "jti"]},
    )
