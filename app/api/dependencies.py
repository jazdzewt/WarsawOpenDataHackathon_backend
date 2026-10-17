from typing import NamedTuple

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService

# Odczytuje nagłówek `Authorization: Bearer <token>`. `auto_error=False` pozwala
# samodzielnie zwrócić 401 zamiast domyślnego 403, gdy nagłówka brakuje.
bearer_scheme = HTTPBearer(auto_error=False)


class CurrentSession(NamedTuple):
    """Zalogowany użytkownik wraz z identyfikatorem jego bieżącego tokenu."""

    user: User
    jti: str


def _unauthorized(detail: str) -> HTTPException:
    # Nagłówek WWW-Authenticate jest wymagany przez standard HTTP przy odpowiedzi 401.
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentSession:
    """Dependency weryfikujące dostęp do endpointu.

    Token musi spełniać trzy warunki:
      1. nagłówek Authorization z typem Bearer,
      2. poprawny podpis i nieupłynięty termin ważności (JWT),
      3. aktywna sesja w bazie (token nie został unieważniony przez wylogowanie).
    W przeciwnym razie zwracany jest 401.

    Użycie w endpoincie: `current: CurrentSession = Depends(get_current_session)`
    albo, gdy potrzebny jest tylko użytkownik: `Depends(get_current_user)`.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Brak tokenu uwierzytelniającego")

    try:
        claims = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("Token jest nieprawidłowy lub wygasł") from exc

    try:
        user_id = int(claims["sub"])
    except (TypeError, ValueError) as exc:
        raise _unauthorized("Token jest nieprawidłowy") from exc
    jti = claims["jti"]

    service = AuthService(db)
    if not service.is_session_active(user_id, jti):
        # Token jest poprawny kryptograficznie, ale sesja została usunięta (wylogowanie).
        raise _unauthorized("Sesja wygasła. Zaloguj się ponownie")

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("Konto nie istnieje")

    return CurrentSession(user=user, jti=jti)


def get_current_user(current: CurrentSession = Depends(get_current_session)) -> User:
    """Skrót dla endpointów, które potrzebują tylko zalogowanego użytkownika."""
    return current.user
