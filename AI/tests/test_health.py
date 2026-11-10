from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    res = TestClient(app).get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_unknown_route_is_404() -> None:
    assert TestClient(app).get("/nope").status_code == 404
