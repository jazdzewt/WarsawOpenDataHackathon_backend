from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_item_crud(client: TestClient) -> None:
    created = client.post("/api/v1/items", json={"name": "Widget"})
    assert created.status_code == 201
    item_id = created.json()["id"]

    assert client.get(f"/api/v1/items/{item_id}").json()["name"] == "Widget"

    updated = client.patch(f"/api/v1/items/{item_id}", json={"description": "Blue"})
    assert updated.json()["description"] == "Blue"

    assert client.delete(f"/api/v1/items/{item_id}").status_code == 204
    assert client.get(f"/api/v1/items/{item_id}").status_code == 404


def test_list_returns_created_items(client: TestClient) -> None:
    client.post("/api/v1/items", json={"name": "A"})
    client.post("/api/v1/items", json={"name": "B"})

    names = [item["name"] for item in client.get("/api/v1/items").json()]
    assert names == ["A", "B"]


def test_create_rejects_empty_name(client: TestClient) -> None:
    response = client.post("/api/v1/items", json={"name": ""})
    assert response.status_code == 422


def test_sql_injection_payload_is_stored_as_plain_text(client: TestClient) -> None:
    payload = "x'); DROP TABLE items; --"

    created = client.post("/api/v1/items", json={"name": payload})
    assert created.status_code == 201
    assert created.json()["name"] == payload

    assert client.get("/api/v1/items").json()[0]["name"] == payload


def test_sql_injection_in_path_is_rejected_by_validation(client: TestClient) -> None:
    response = client.get("/api/v1/items/1 OR 1=1")
    assert response.status_code == 422
