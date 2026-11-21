"""Check CORS against the running local API."""

import httpx


def main() -> None:
    """Validate the expected local preflight and offline generation response."""
    origin = "http://localhost:3000"
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=5.0) as client:
        preflight = client.options(
            "/api/v1/generate",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        preflight.raise_for_status()
        assert preflight.headers["access-control-allow-origin"] == origin

        response = client.post(
            "/api/v1/generate",
            headers={"Origin": origin},
            json={"text": "Show active users", "language": "en"},
        )
        response.raise_for_status()
        assert response.headers["access-control-allow-origin"] == origin
        result = response.json()
        assert result["source"] == "demo"
        assert "FROM users" in result["query"]
        print("CORS and offline generation passed")


if __name__ == "__main__":
    main()
