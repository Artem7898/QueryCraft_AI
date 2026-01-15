import re
from typing import List


class SecurityError(Exception):
    pass


class SQLInjectionError(SecurityError):
    pass


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Расширенная санитизация ввода"""

    # Проверка длины
    if len(text) > max_length:
        raise ValueError(f"Текст превышает максимальную длину {max_length}")

    # Список опасных паттернов
    dangerous_patterns = [
        # SQL injection
        r"(?i)(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE)",
        r"(?i)(UNION\s+SELECT|UNION\s+ALL\s+SELECT)",
        r"(?i)(INSERT\s+INTO|UPDATE\s+.+\s+SET)",
        r"(?i)(CREATE\s+TABLE|ALTER\s+TABLE)",
        r"(?i)(EXEC\s*\(|EXECUTE\s*\(|xp_cmdshell)",
        r"(?i)(--|#|/\*|\*/)",
        r"(?i)(OR\s+['\"]?['\"]?\s*=\s*['\"]?['\"]?)",
        r"(?i)(WAITFOR\s+DELAY|SLEEP\s*\()",

        # NoSQL injection
        r"(?i)(\$where|\$ne|\$gt|\$lt)",
        r"(?i)(\{\s*\"\$",

        # Path traversal
        r"(\.\./|\.\.\\|~/|/etc/|/bin/)",

        # XSS
        r"(<script|javascript:|onload=|onerror=)",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, text):
            raise SQLInjectionError(
                f"Обнаружен потенциально опасный запрос: {pattern}"
            )

    # Удаление лишних пробелов и обрезка
    cleaned = ' '.join(text.split())
    return cleaned[:max_length]


def validate_db_type(db_type: str) -> str:
    """Валидация типа базы данных"""
    allowed_types = {"postgresql", "mysql", "mongodb"}
    if db_type.lower() not in allowed_types:
        raise ValueError(f"Неподдерживаемый тип БД: {db_type}")
    return db_type.lower()