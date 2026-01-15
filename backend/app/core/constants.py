from enum import Enum


class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class Complexity(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    ADVANCED = "advanced"


SUPPORTED_LANGUAGES = ["ru", "en"]
