def test_basic_math():
    """Простой тест математики"""
    assert 1 + 1 == 2

def test_imports():
    """Тест импортов приложения"""
    try:
        import app.main
        import app.config
        import app.models.schemas
        assert True
    except ImportError as e:
        raise AssertionError(f"Import error: {e}")