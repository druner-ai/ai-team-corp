"""
Тесты для endpoint'а GET /health.
"""
from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    """
    Проверяет, что endpoint возвращает статус 200.
    """
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_schema(client: TestClient) -> None:
    """
    Проверяет структуру JSON-ответа.
    """
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert isinstance(data["uptime_seconds"], float)
    assert isinstance(data["version"], str)


def test_health_uptime_increases(client: TestClient) -> None:
    """
    Проверяет, что uptime увеличивается между запросами.
    """
    r1 = client.get("/health").json()
    r2 = client.get("/health").json()
    assert r2["uptime_seconds"] >= r1["uptime_seconds"]


def test_root_redirects_to_docs(client: TestClient) -> None:
    """
    Проверяет, что корневой путь редиректит на /docs (в dev-окружении).
    """
    response = client.get("/", follow_redirects=False)
    # В тестовом окружении ENVIRONMENT=development, поэтому docs включены
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_security_headers(client: TestClient) -> None:
    """
    Проверяет наличие заголовков безопасности.
    """
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
