from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """Konto użytkownika. Logowanie odbywa się przez e-mail i hasło."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Unikalny, znormalizowany (małe litery) adres e-mail - zapobiega duplikatom kont.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Wyłącznie hash hasła (Argon2id). Hasło w postaci jawnej nigdy nie trafia do bazy.
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
