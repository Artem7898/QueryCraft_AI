from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.models.schemas import QueryRequest, QueryResponse
from app.services.ai_service import ai_service
import logging
import time

router = APIRouter()
logger = logging.getLogger(__name__)


# Явный обработчик OPTIONS для всех методов
@router.options("/generate")
async def options_generate():
    """Явная обработка CORS preflight запроса"""
    return JSONResponse(
        content={"message": "CORS preflight OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept, Authorization",
            "Access-Control-Max-Age": "86400",  # 24 часа
        },
    )


@router.post("/generate", response_model=QueryResponse)
async def generate_query(request: QueryRequest):
    """
    Генерация SQL/NoSQL запроса по описанию на естественном языке
    """
    start_time = time.time()

    try:
        logger.info(f"🔧 Generating query: {request.text[:100]}...")
        logger.info(
            f"📊 Params: db_type={request.db_type}, complexity={request.complexity}, language={request.language}"
        )

        # Если API ключ не установлен, работаем в тестовом режиме
        if not ai_service.api_key or ai_service.api_key == "your_api_key_here":
            logger.info("🧪 Working in test mode (no API key)")

            # Тестовые данные в зависимости от запроса
            if "users" in request.text.lower() or "пользовател" in request.text.lower():
                sql_query = """-- Запрос для выборки пользователей
SELECT 
    id,
    username,
    email,
    age,
    status,
    created_at
FROM users
WHERE status = 'active'
  AND age > 25
ORDER BY created_at DESC
LIMIT 100;"""
                explanation = "Выбирает активных пользователей старше 25 лет"
            elif "orders" in request.text.lower() or "заказ" in request.text.lower():
                sql_query = """-- Статистика заказов
SELECT 
    DATE(created_at) as order_date,
    COUNT(*) as total_orders,
    SUM(amount) as total_amount,
    AVG(amount) as average_order
FROM orders
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY order_date DESC;"""
                explanation = "Статистика заказов за последние 30 дней"
            else:
                # Используем безопасное имя таблицы
                safe_table_name = "example_table"
                sql_query = f"""-- {request.db_type.value.upper()} запрос
SELECT *
FROM {safe_table_name}
WHERE condition = 'value'
ORDER BY id
LIMIT 50;"""
                explanation = f"Пример {request.db_type.value.upper()} запроса"

            execution_time = time.time() - start_time

            return QueryResponse(
                query=sql_query,
                explanation=explanation,
                executed_in=round(execution_time, 2),
                tokens_used=150,
                model=f"{ai_service.model} (тестовый режим)",
            )

        # Реальный запрос к API
        result = await ai_service.generate_sql(
            text=request.text,
            db_type=request.db_type,
            complexity=request.complexity,
            language=request.language,
        )

        if "error" in result:
            logger.error(f"❌ Error generating query: {result['error']}")
            raise HTTPException(
                status_code=500, detail=f"Ошибка генерации запроса: {result['error']}"
            )

        return QueryResponse(
            query=result["query"],
            explanation=result["explanation"],
            executed_in=result["executed_in"],
            tokens_used=result.get("tokens_used"),
            model=result["model"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"💥 Unexpected error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "model": ai_service.model,
        "api_key_set": bool(
            ai_service.api_key
            and ai_service.api_key != "B72c830aee09a35f763208e26c948eef"
        ),
        "service": "QueryCraft AI",
        "timestamp": time.time(),
    }


@router.get("/test")
async def test_endpoint():
    """Тестовый эндпоинт для проверки CORS"""
    return {
        "message": "✅ CORS тест пройден",
        "timestamp": time.time(),
        "cors": "enabled",
        "status": "success",
    }


@router.get("/cors-test")
async def cors_test():
    """Специальный тест CORS"""
    return JSONResponse(
        content={"message": "CORS тест успешен"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "*",
        },
    )