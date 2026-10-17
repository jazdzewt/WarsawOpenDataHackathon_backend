from fastapi.testclient import TestClient

from app.main import app
from app.services.item_service import item_service

client = TestClient(app)


def setup_function() -> None:
    item_service._items.clear()
    item_service._next_id = 1


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_item_crud() -> None:
    created = client.post("/api/v1/items", json={"name": "Widget"})
    assert created.status_code == 201
    item_id = created.json()["id"]

    assert client.get(f"/api/v1/items/{item_id}").json()["name"] == "Widget"

    updated = client.patch(f"/api/v1/items/{item_id}", json={"description": "Blue"})
    assert updated.json()["description"] == "Blue"

    assert client.delete(f"/api/v1/items/{item_id}").status_code == 204
    assert client.get(f"/api/v1/items/{item_id}").status_code == 404


def test_create_rejects_empty_name() -> None:
    response = client.post("/api/v1/items", json={"name": ""})
    assert response.status_code == 422
