from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserSession(Base):
    """Aktywna sesja powiązana z tokenem JWT.

    Token JWT jest ważny tylko wtedy, gdy jego `jti` istnieje w tej tabeli.
    Wylogowanie usuwa wiersz, dzięki czemu token przestaje działać natychmiast,
    mimo że jego termin ważności jeszcze nie minął.
    """

    __tablename__ = "user_sessions"

    # Identyfikator tokenu (claim `jti`) jest kluczem głównym sesji.
    jti: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
