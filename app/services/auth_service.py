from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.user import UserDelete, UserRegister


class EmailAlreadyRegisteredError(Exception):
    """Konto z podanym adresem e-mail już istnieje."""


class InvalidCredentialsError(Exception):
    """Nieprawidłowy e-mail lub hasło. Celowo jeden komunikat dla obu przypadków,
    żeby nie ujawniać, które adresy mają konto."""


class InvalidPasswordError(Exception):
    """Podane hasło przy usuwaniu konta jest nieprawidłowe."""


class AuthService:
    """Logika rejestracji, logowania, wylogowania i usuwania kont.

    Wszystkie zapytania idą przez ORM SQLAlchemy, który przekazuje wartości jako
    parametry zapytania. Dane od użytkownika nigdy nie są sklejane z SQL-em,
    więc nie ma możliwości SQL injection.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def register(self, payload: UserRegister) -> User:
        """Tworzy konto. Hasło jest hashowane przed zapisem do bazy."""
        user = User(email=payload.email, password_hash=hash_password(payload.password))
        self._db.add(user)
        try:
            self._db.commit()
        except IntegrityError as exc:
            # Unikalność e-maila jest pilnowana przez bazę. Obsługuje to także
            # sytuację, gdy dwa żądania rejestrują ten sam adres równocześnie.
            self._db.rollback()
            raise EmailAlreadyRegisteredError from exc
        self._db.refresh(user)
        return user

    def login(self, email: str, password: str) -> tuple[str, int]:
        """Weryfikuje dane logowania i tworzy sesję.

        Zwraca krotkę (token JWT, czas ważności w sekundach).
        """
        user = self._db.scalar(select(User).where(User.email == email))
        if user is None:
            # Weryfikujemy hasło także przy nieistniejącym koncie, żeby czas odpowiedzi
            # był podobny i nie dało się sprawdzić, czy e-mail jest zarejestrowany.
            verify_password(password, DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError

        token, jti = create_access_token(user.id)
        # Zapisujemy sesję po stronie serwera - dopiero to pozwala później unieważnić token.
        self._db.add(UserSession(jti=jti, user_id=user.id))
        self._db.commit()
        return token, settings.access_token_expire_minutes * 60

    def logout(self, jti: str) -> None:
        """Usuwa sesję powiązaną z tokenem. Od tej chwili token jest odrzucany."""
        self._db.execute(delete(UserSession).where(UserSession.jti == jti))
        self._db.commit()

    def is_session_active(self, user_id: int, jti: str) -> bool:
        """Sprawdza, czy sesja o podanym `jti` istnieje i należy do użytkownika."""
        session = self._db.scalar(
            select(UserSession).where(
                UserSession.jti == jti,
                UserSession.user_id == user_id,
            )
        )
        return session is not None

    def delete_account(self, user: User, payload: UserDelete) -> None:
        """Usuwa konto po ponownym potwierdzeniu hasłem.

        Sesje użytkownika są usuwane razem z kontem (ON DELETE CASCADE), a jawne
        usunięcie poniżej działa także tam, gdzie klucze obce nie są egzekwowane (SQLite).
        """
        if not verify_password(payload.password, user.password_hash):
            raise InvalidPasswordError

        self._db.execute(delete(UserSession).where(UserSession.user_id == user.id))
        self._db.delete(user)
        self._db.commit()
