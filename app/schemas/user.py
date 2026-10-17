import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Minimalna długość i maksymalna długość hasła. Maksimum chroni przed nadużyciem
# (bardzo długie hasło zużywa dużo CPU podczas hashowania Argon2).
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


def validate_password_strength(password: str) -> str:
    """Sprawdza wymogi bezpieczeństwa hasła i zwraca je bez zmian.

    Hasło musi mieć co najmniej 12 znaków i zawierać małą literę, wielką literę,
    cyfrę oraz znak specjalny. Walidacja działa po stronie serwera, więc nie da się
    jej obejść od strony klienta.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Hasło musi mieć co najmniej {PASSWORD_MIN_LENGTH} znaków")
    if not re.search(r"[a-z]", password):
        raise ValueError("Hasło musi zawierać małą literę")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Hasło musi zawierać wielką literę")
    if not re.search(r"\d", password):
        raise ValueError("Hasło musi zawierać cyfrę")
    if not re.search(r"[^\w\s]", password):
        raise ValueError("Hasło musi zawierać znak specjalny")
    return password


class UserRegister(BaseModel):
    """Dane potrzebne do utworzenia konta: wyłącznie e-mail i hasło."""

    email: EmailStr
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        # Adresy e-mail porównujemy bez względu na wielkość liter.
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserLogin(BaseModel):
    """Dane logowania. Hasło sprawdzamy tylko pod kątem długości, nie siły,
    bo siła była wymuszona przy rejestracji."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserDelete(BaseModel):
    """Potwierdzenie usunięcia konta hasłem - zabezpiecza przed usunięciem konta
    przez osobę, która przejęła tylko aktywny token."""

    password: str = Field(..., min_length=1, max_length=PASSWORD_MAX_LENGTH)


class UserRead(BaseModel):
    """Publiczne dane konta. Hash hasła nigdy nie jest zwracany."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class TokenResponse(BaseModel):
    """Odpowiedź po zalogowaniu."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # czas ważności tokenu w sekundach
