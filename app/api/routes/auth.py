from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentSession, get_current_session, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserDelete, UserLogin, UserRead, UserRegister
from app.services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidPasswordError,
)

router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create account",
)
def register(payload: UserRegister, service: AuthService = Depends(get_auth_service)) -> User:
    # Walidacja e-maila i siły hasła odbywa się już w schemacie (UserRegister).
    try:
        return service.register(payload)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Konto z tym adresem e-mail już istnieje",
        )


@router.post("/login", response_model=TokenResponse, summary="Log in and get JWT")
def login(payload: UserLogin, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    try:
        token, expires_in = service.login(payload.email, payload.password)
    except InvalidCredentialsError:
        # Ten sam komunikat dla złego e-maila i złego hasła - brak wycieku informacji o kontach.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy e-mail lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out (invalidate current JWT)",
)
def logout(
    current: CurrentSession = Depends(get_current_session),
    service: AuthService = Depends(get_auth_service),
) -> None:
    # Usuwamy sesję powiązaną z tokenem, którym wykonano żądanie.
    service.logout(current.jti)


@router.get("/me", response_model=UserRead, summary="Current user (requires JWT)")
def me(user: User = Depends(get_current_user)) -> User:
    # Przykład chronionego endpointu: dostęp tylko z ważnym, aktywnym tokenem.
    return user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete current account (requires password)",
)
def delete_me(
    payload: UserDelete,
    user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> None:
    try:
        service.delete_account(user, payload)
    except InvalidPasswordError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nieprawidłowe hasło",
        )
