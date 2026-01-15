import httpx
import json
import time
from typing import Dict, Any, Optional
from app.config import settings
from app.models.schemas import DatabaseType, Complexity
import logging
import re

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.api_key = settings.BYTEZ_API_KEY
        self.model = settings.MODEL_NAME
        self.api_url = settings.BYTEZ_API_URL
        self.timeout = settings.API_TIMEOUT
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def generate_sql(
        self,
        text: str,
        db_type: DatabaseType,
        complexity: Complexity,
        language: str = "ru",
    ) -> Dict[str, Any]:
        """Генерация SQL запроса через BYTEZ API"""

        # Если API ключ не установлен, возвращаем тестовые данные
        if not self.api_key or self.api_key == "B72c830aee09a35f763208e26c948eef":
            return self._generate_mock_response(text, db_type, complexity, language)

        # Формируем промпт в зависимости от языка
        if language == "ru":
            prompt = self._build_russian_prompt(text, db_type, complexity)
        else:
            prompt = self._build_english_prompt(text, db_type, complexity)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Параметры для генерации
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt(db_type, complexity, language),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 500,
            "temperature": 0.1,
            "top_p": 0.95,
        }

        start_time = time.time()

        try:
            response = await self.client.post(
                f"{self.api_url}/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()

            result = response.json()
            generated_text = result["choices"][0]["message"]["content"].strip()
            tokens_used = result.get("usage", {}).get("total_tokens", 0)

            # Извлекаем SQL запрос и объяснение
            sql_query, explanation = self._parse_response(generated_text, language)

            execution_time = time.time() - start_time

            return {
                "query": sql_query,
                "explanation": explanation,
                "executed_in": round(execution_time, 2),
                "tokens_used": tokens_used,
                "model": self.model,
            }

        except httpx.HTTPStatusError as e:
            return {
                "query": f"Ошибка API: {e.response.status_code}",
                "explanation": "Произошла ошибка при обращении к API",
                "executed_in": time.time() - start_time,
                "error": str(e),
            }
        except Exception as e:
            return {
                "query": f"Ошибка: {str(e)}",
                "explanation": "Произошла непредвиденная ошибка",
                "executed_in": time.time() - start_time,
                "error": str(e),
            }

    def _generate_mock_response(
        self, text: str, db_type: DatabaseType, complexity: Complexity, language: str
    ) -> Dict[str, Any]:
        """Генерация тестового ответа"""
        time.sleep(1)  # Имитация задержки

        if "users" in text.lower() or "пользовател" in text.lower():
            sql = f"""-- Запрос для {db_type.value}
SELECT 
    id,
    name,
    email,
    age,
    status,
    created_at
FROM users
WHERE status = 'active'
ORDER BY created_at DESC
LIMIT 50;"""
        elif "orders" in text.lower() or "заказ" in text.lower():
            sql = f"""-- Статистика заказов для {db_type.value}
SELECT 
    DATE(created_at) as order_date,
    COUNT(*) as total_orders,
    SUM(amount) as total_amount,
    AVG(amount) as average_order
FROM orders
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY order_date DESC;"""
        else:
            sql = f"""-- Общий запрос для {db_type.value}
SELECT *
FROM your_table
WHERE condition = 'value'
LIMIT 100;"""

        explanation_ru = f"Сгенерирован {complexity.value} запрос для {db_type.value.upper()} на основе описания"
        explanation_en = f"Generated {complexity.value} query for {db_type.value.upper()} based on description"

        return {
            "query": sql,
            "explanation": explanation_ru if language == "ru" else explanation_en,
            "executed_in": 1.2,
            "tokens_used": 150,
            "model": f"{self.model} (тестовый режим)",
        }

    def _get_system_prompt(
        self, db_type: DatabaseType, complexity: Complexity, language: str
    ) -> str:
        """Системный промпт для модели"""

        if language == "ru":
            return f"""Вы опытный разработчик баз данных. Генерируйте {complexity.value} {db_type.value.upper()} запросы.
Правила:
1. Возвращайте ТОЛЬКО SQL запрос без дополнительного текста
2. Затем, после пустой строки, дайте краткое объяснение
3. Используйте правильный синтаксис для {db_type.value.upper()}
4. Добавьте комментарии к сложным частям запроса
5. Учитывайте лучшие практики для {db_type.value.upper()}"""
        else:
            return f"""You are an experienced database developer. Generate {complexity.value} {db_type.value.upper()} queries.
Rules:
1. Return ONLY the SQL query without additional text
2. Then, after an empty line, give a brief explanation
3. Use proper syntax for {db_type.value.upper()}
4. Add comments to complex parts of the query
5. Consider best practices for {db_type.value.upper()}"""

    def _build_russian_prompt(
        self, text: str, db_type: DatabaseType, complexity: Complexity
    ) -> str:
        """Формируем промпт на русском"""

        db_instructions = {
            "postgresql": "Используй синтаксис PostgreSQL. Поддерживай современные функции как оконные функции, CTE.",
            "mysql": "Используй синтаксис MySQL. Учитывай особенности движков InnoDB/MyISAM.",
            "sqlite": "Используй синтаксис SQLite. Учитывай ограничения SQLite (нет полной поддержки оконных функций).",
            "mongodb": "Генерируй MongoDB запрос (используй JavaScript синтаксис для оболочки MongoDB).",
        }

        complexity_instructions = {
            "simple": "Простой запрос с базовыми операциями SELECT, WHERE.",
            "medium": "Запрос средней сложности с JOIN, GROUP BY, агрегатными функциями.",
            "advanced": "Сложный запрос с подзапросами, оконными функциями, CTE.",
        }

        return f"""{db_instructions.get(db_type.value, "")}
{complexity_instructions.get(complexity.value, "")}

Описание запроса: {text}

Сгенерируй {db_type.value.upper()} запрос {complexity.value} сложности:"""

    def _build_english_prompt(
        self, text: str, db_type: DatabaseType, complexity: Complexity
    ) -> str:
        """Формируем промпт на английском"""

        db_instructions = {
            "postgresql": "Use PostgreSQL syntax. Support modern features like window functions, CTE.",
            "mysql": "Use MySQL syntax. Consider InnoDB/MyISAM engine specifics.",
            "sqlite": "Use SQLite syntax. Consider SQLite limitations (no full window functions support).",
            "mongodb": "Generate MongoDB query (use JavaScript syntax for MongoDB shell).",
        }

        complexity_instructions = {
            "simple": "Simple query with basic SELECT, WHERE operations.",
            "medium": "Medium complexity query with JOIN, GROUP BY, aggregate functions.",
            "advanced": "Advanced query with subqueries, window functions, CTE.",
        }

        return f"""{db_instructions.get(db_type.value, "")}
{complexity_instructions.get(complexity.value, "")}

Query description: {text}

Generate {db_type.value.upper()} {complexity.value} complexity query:"""

    def _parse_response(self, response: str, language: str) -> tuple[str, str]:
        """Парсим ответ от модели, извлекая SQL и объяснение"""

        lines = response.split("\n")
        sql_lines = []
        explanation_lines = []

        in_sql = True

        for line in lines:
            # Если находим пустую строку, переключаемся на объяснение
            if line.strip() == "" and in_sql:
                in_sql = False
                continue

            if in_sql:
                sql_lines.append(line)
            else:
                explanation_lines.append(line)

        sql_query = "\n".join(sql_lines).strip()
        explanation = "\n".join(explanation_lines).strip()

        # Если объяснение пустое, создаем базовое
        if not explanation:
            explanation = (
                "Сгенерированный SQL запрос"
                if language == "ru"
                else "Generated SQL query"
            )

        return sql_query, explanation

    async def close(self):
        """Закрываем клиент"""
        await self.client.aclose()


# Создаем экземпляр сервиса
ai_service = AIService()