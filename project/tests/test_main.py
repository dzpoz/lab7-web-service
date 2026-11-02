from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_user():
    response = client.post("/api/v1/users/", json={"username": "testuser", "password": "testpass"})
    assert response.status_code == 201
    assert response.json()["username"] == "testuser"

def test_get_user():
    response = client.get("/api/v1/users/1")
    assert response.status_code in [200, 404]

def test_login():
    response = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass"})
    assert response.status_code == 200
    assert "session_token" in response.json()

def test_login_invalid_password():
    response = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "wrongpass"})
    assert response.status_code == 400