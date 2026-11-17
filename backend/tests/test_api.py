from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app

client = TestClient(app)


def _sketch_png():
    image = Image.new("RGB", (240, 180), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 35, 180, 90), outline="black", width=3)
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _sign_in(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-that-is-at-least-32-characters")
    suffix = uuid4().hex[:12]
    response = client.post("/api/auth/register", json={
        "username": f"test_{suffix}",
        "email": f"{suffix}@example.com",
        "password": "test-password-123",
    })
    assert response.status_code == 200


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_homepage_serves_the_frontend():
    response = client.get("/")
    assert response.status_code in (200, 503)
    assert "text/html" in response.headers["content-type"]
    if response.status_code == 200:
        assert "Sketchflow" in response.text


def test_analyze_image_returns_detected_elements_and_preview(monkeypatch):
    _sign_in(monkeypatch)
    monkeypatch.setattr("app.main.recognize_text", lambda image: [])
    response = client.post(
        "/api/analyze",
        files={"file": ("sketch.png", _sketch_png(), "image/png")},
        data={"provider": "local"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["image"] == {"width": 240, "height": 180}
    assert result["elements"]
    assert all(element["type"] == "container" for element in result["elements"])
    assert "<!DOCTYPE html>" in result["html"]
    assert ".sketch-canvas" in result["css"]
    assert "addEventListener" in result["javascript"]
    assert 'src="script.js"' in result["html"]


def test_analyze_image_rejects_non_image_content_type(monkeypatch):
    _sign_in(monkeypatch)
    response = client.post(
        "/api/analyze",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_analyze_image_rejects_invalid_image_bytes(monkeypatch):
    _sign_in(monkeypatch)
    response = client.post(
        "/api/analyze",
        files={"file": ("bad.png", b"not an image", "image/png")},
    )
    assert response.status_code == 400
