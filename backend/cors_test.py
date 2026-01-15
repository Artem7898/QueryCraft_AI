import requests
import json

# Тест POST запроса
url = "http://localhost:8000/api/v1/generate"
headers = {"Content-Type": "application/json", "Origin": "http://localhost:3000"}
data = {
    "text": "тестовый запрос",
    "db_type": "postgresql",
    "complexity": "simple",
    "language": "ru",
}

try:
    # Сначала OPTIONS (preflight)
    print("Testing OPTIONS request...")
    resp = requests.options(url, headers=headers)
    print(f"OPTIONS Status: {resp.status_code}")
    print(f"OPTIONS Headers: {dict(resp.headers)}")

    # Затем POST
    print("\nTesting POST request...")
    resp = requests.post(url, headers=headers, json=data)
    print(f"POST Status: {resp.status_code}")
    print(f"POST Headers: {dict(resp.headers)}")
    print(f"POST Body: {resp.text}")

except Exception as e:
    print(f"Error: {e}")
