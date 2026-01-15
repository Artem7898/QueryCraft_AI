import pytest
from fastapi.testclient import TestClient
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Отложенный импорт, чтобы избежать ошибок
@pytest.fixture
def client():
    # Импортируем только здесь
    from app.main import app
    return TestClient(app)