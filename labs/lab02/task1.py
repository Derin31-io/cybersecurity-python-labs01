import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

PASSWORD_HASH_ALGORITHM = "sha256"
PASSWORD_HASH_ITERATIONS = 600_000
SALT_SIZE = 16
SESSION_TIMEOUT_SEC = 900

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9_]{2,63}@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)


class User:
    """Користувач системи."""

    def __init__(
        self,
        username: str,
        email: str,
        role: str,
        active: bool = True,
        password: str | None = None,
    ) -> None:
        self.username = username
        self._email = ""
        self.email = email
        self.role = role
        self.active = active

        self.__password_hash = b""
        self.__password_salt = b""

        if password is not None:
            self.set_password(password)

    @property
    def email(self) -> str:
        """Повертає email користувача."""
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        """Встановлює email з перевіркою формату."""
        if not isinstance(value, str):
            raise TypeError("Email must be a string")

        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Invalid email format")

        self._email = value

    def set_password(self, password: str) -> None:
        """Встановлює пароль у вигляді захищеного хешу."""
        if not isinstance(password, str):
            raise TypeError("Password must be a string")

        if not password:
            raise ValueError("Password cannot be empty")

        salt = os.urandom(SALT_SIZE)

        password_hash = hashlib.pbkdf2_hmac(
            PASSWORD_HASH_ALGORITHM,
            password.encode("utf-8"),
            salt,
            PASSWORD_HASH_ITERATIONS,
        )

        self.__password_salt = salt
        self.__password_hash = password_hash

    def check_password(self, password: str) -> bool:
        """Перевіряє пароль без розкриття хешу."""
        if not isinstance(password, str):
            return False

        if not self.__password_hash or not self.__password_salt:
            return False

        candidate_hash = hashlib.pbkdf2_hmac(
            PASSWORD_HASH_ALGORITHM,
            password.encode("utf-8"),
            self.__password_salt,
            PASSWORD_HASH_ITERATIONS,
        )

        return hmac.compare_digest(
            self.__password_hash,
            candidate_hash,
        )

    def deactivate(self) -> None:
        """Деактивує користувача."""
        self.active = False

    def __str__(self) -> str:
        """Текстове представлення користувача."""
        status = "active" if self.active else "inactive"

        return (
            f"User(username={self.username}, "
            f"email={self.email}, "
            f"role={self.role}, "
            f"status={status})"
        )


class Admin(User):
    """Адміністратор із набором дозволів."""

    def __init__(
        self,
        username: str,
        email: str,
        role: str = "admin",
        active: bool = True,
        password: str | None = None,
        permissions: set[str] | None = None,
    ) -> None:
        super().__init__(
            username=username,
            email=email,
            role=role,
            active=active,
            password=password,
        )

        self.permissions = set(permissions) if permissions is not None else set()

    def grant_permission(self, permission: str) -> None:
        """Додає дозвіл."""
        if not isinstance(permission, str):
            raise TypeError("Permission must be a string")

        if not permission:
            raise ValueError("Permission cannot be empty")

        self.permissions.add(permission)

    def revoke_permission(self, permission: str) -> None:
        """Видаляє дозвіл."""
        self.permissions.discard(permission)

    def has_permission(self, permission: str) -> bool:
        """Перевіряє наявність дозволу."""
        return permission in self.permissions

    def __str__(self) -> str:
        """Текстове представлення адміністратора."""
        status = "active" if self.active else "inactive"
        permissions = ", ".join(sorted(self.permissions))

        return (
            f"Admin(username={self.username}, "
            f"email={self.email}, "
            f"role={self.role}, "
            f"status={status}, "
            f"permissions=[{permissions}])"
        )


class Session:
    """Сесія користувача."""

    def __init__(
        self,
        ip: str,
        login_time: datetime | None = None,
        last_activity: datetime | None = None,
    ) -> None:
        self.ip = ip

        now = datetime.now(timezone.utc)

        self.login_time = login_time if login_time is not None else now

        self.last_activity = (
            last_activity if last_activity is not None else self.login_time
        )

        self._validate_datetime(self.login_time)
        self._validate_datetime(self.last_activity)

    @staticmethod
    def _validate_datetime(value: datetime) -> None:
        """Перевіряє, що datetime має UTC timezone."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Session timestamps must be timezone-aware")

    def touch(self) -> None:
        """Оновлює час останньої активності."""
        self.last_activity = datetime.now(timezone.utc)

    def is_active(self, timeout_sec: int) -> bool:
        """Перевіряє, чи не закінчився таймаут сесії."""
        if timeout_sec <= 0:
            raise ValueError("timeout_sec must be greater than zero")

        now = datetime.now(timezone.utc)
        elapsed = now - self.last_activity

        return elapsed <= timedelta(seconds=timeout_sec)


@dataclass
class AuditRecord:
    """Окремий запис аудиту."""

    timestamp: datetime
    username: str
    action: str


class AuditLog:
    """Журнал аудиту."""

    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def add_log(self, username: str, action: str) -> None:
        """Додає подію до журналу."""
        record = AuditRecord(
            timestamp=datetime.now(timezone.utc),
            username=username,
            action=action,
        )

        self.records.append(record)

    def show_all(self) -> None:
        """Виводить усі записи аудиту."""
        if not self.records:
            print("Audit log is empty.")
            return

        for record in self.records:
            print(
                f"{record.timestamp.isoformat()} | {record.username} | {record.action}"
            )


class UserAccount:
    """Обліковий запис, що композиційно об'єднує User, Session і AuditLog."""

    SESSION_TIMEOUT_SEC = SESSION_TIMEOUT_SEC

    def __init__(
        self,
        user: User,
        session: Session | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        if not isinstance(user, User):
            raise TypeError("user must be an instance of User")

        if session is not None and not isinstance(session, Session):
            raise TypeError("session must be an instance of Session or None")

        if audit_log is not None and not isinstance(audit_log, AuditLog):
            raise TypeError("audit_log must be an instance of AuditLog or None")

        self.user = user
        self.session = session
        self.audit_log = audit_log if audit_log is not None else AuditLog()

    def login(
        self,
        username: str,
        password: str,
        ip: str,
    ) -> bool:
        """Виконує вхід користувача."""
        if username != self.user.username:
            self.audit_log.add_log(
                username,
                "login_failure",
            )
            return False

        if not self.user.active:
            self.audit_log.add_log(
                username,
                "login_failure",
            )
            return False

        if not self.user.check_password(password):
            self.audit_log.add_log(
                username,
                "login_failure",
            )
            return False

        self.session = Session(ip=ip)
        self.session.touch()

        self.audit_log.add_log(
            username,
            "login_success",
        )

        return True

    def is_authenticated(self) -> bool:
        """Перевіряє автентифікацію та термін дії сесії."""
        if self.session is None:
            return False

        return self.session.is_active(self.SESSION_TIMEOUT_SEC)

    def logout(self) -> None:
        """Завершує поточну сесію."""
        if self.session is None:
            return

        self.audit_log.add_log(
            self.user.username,
            "logout",
        )

        self.session = None

    def __getitem__(self, key: str):
        """Дозволяє отримувати дозволені атрибути через []."""
        allowed = {
            "user": self.user,
            "session": self.session,
            "audit_log": self.audit_log,
        }

        if key not in allowed:
            raise KeyError(key)

        return allowed[key]

    def __setitem__(self, key: str, value) -> None:
        """Дозволяє змінювати дозволені атрибути через []."""
        if key == "user":
            if not isinstance(value, User):
                raise TypeError("user must be an instance of User")

            self.user = value
            return

        if key == "session":
            if value is not None and not isinstance(
                value,
                Session,
            ):
                raise TypeError("session must be Session or None")

            self.session = value
            return

        if key == "audit_log":
            if not isinstance(value, AuditLog):
                raise TypeError("audit_log must be an instance of AuditLog")

            self.audit_log = value
            return

        raise KeyError(key)
