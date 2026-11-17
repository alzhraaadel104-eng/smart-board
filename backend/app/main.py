from io import BytesIO
import os
from pathlib import Path
import re

import numpy as np
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

from app.generator.html_generator import generate_html
from app.generator.css_generator import generate_css
from app.generator.javascript_generator import generate_javascript
from app.vision.detector import detect_rectangles
from app.vision.ocr import recognize_text
from app.vision.openai_analyzer import (
    OpenAIAnalyzerConfigError,
    OpenAIAnalyzerError,
    analyze_with_openai,
)

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP", "BMP"}

app = FastAPI(
    title="Smart Whiteboard API",
    description="Authenticated sketch analysis API that generates a live UI preview and HTML/CSS/JavaScript files.",
    version="3.0.0",
)
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
PROJECT_ROOT = FRONTEND_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")
from app.auth import COOKIE_NAME, SESSION_SECONDS, create_user, find_user, init_db, make_session, public_user, session_user, verify_password

init_db()


class RegisterPayload(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginPayload(BaseModel):
    username: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


def _current_user(request: Request):
    user = session_user(request.cookies.get(COOKIE_NAME))
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in to use the dashboard.")
    return user


def _set_session(response: Response, user_id: int):
    response.set_cookie(
        key=COOKIE_NAME,
        value=make_session(user_id),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").strip().lower() == "true",
        samesite="lax",
        path="/",
    )


@app.post("/api/auth/register", tags=["authentication"])
def register(payload: RegisterPayload, response: Response):
    username = payload.username.strip()
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        raise HTTPException(status_code=422, detail="Username must be 3–32 characters using letters, numbers, dot, underscore, or hyphen.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    user = create_user(username, email, payload.password)
    if not user:
        raise HTTPException(status_code=409, detail="That username or email is already registered.")
    _set_session(response, user["id"])
    return {"authenticated": True, "username": user["username"], "user": user}


@app.post("/api/auth/login", tags=["authentication"])
def login(payload: LoginPayload, response: Response):
    user = find_user(payload.username)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email/username or password is incorrect.")
    _set_session(response, user["id"])
    return {"authenticated": True, "username": user["username"], "user": public_user(user)}


@app.get("/api/auth/me", tags=["authentication"])
def auth_status(request: Request):
    user = _current_user(request)
    return {"authenticated": True, "username": user["username"], "user": public_user(user)}


@app.post("/api/auth/logout", tags=["authentication"])
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, httponly=True, samesite="lax", path="/")
    return {"authenticated": False}


@app.get("/", include_in_schema=False)
def home_page():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return HTMLResponse(index_file.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<h1>Frontend is not built</h1><p>Run <code>cd frontend; npm install; npm run dev</code>.</p>",
        status_code=503,
    )


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


def _merge_detections(boxes, text_items, image_width, image_height):
    """Attach OCR labels to enclosing shapes and keep free text as text elements."""
    elements = [
        {"id": f"element_{index + 1:03d}", "type": "container", "text": "",
         "bbox": [x, y, x + box_width, y + box_height], "confidence": None}
        for index, (x, y, box_width, box_height) in enumerate(boxes)
    ]
    action_words = {"login", "log in", "sign in", "submit", "register", "continue"}
    for text_index, item in enumerate(text_items):
        x1, y1, x2, y2 = item["bbox"]
        center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
        enclosing = [
            (i, element) for i, element in enumerate(elements)
            if (element["bbox"][2] - element["bbox"][0]) * (element["bbox"][3] - element["bbox"][1]) < image_width * image_height * 0.25
            and element["bbox"][0] <= center_x <= element["bbox"][2]
            and element["bbox"][1] <= center_y <= element["bbox"][3]
        ]
        if enclosing:
            i, element = min(
                enclosing,
                key=lambda pair: (pair[1]["bbox"][2] - pair[1]["bbox"][0])
                * (pair[1]["bbox"][3] - pair[1]["bbox"][1]),
            )
            label = item["text"]
            normalized = " ".join(label.lower().split())
            element["text"] = label
            element["confidence"] = item["confidence"]
            if normalized in action_words:
                element["type"] = "button"
            elif normalized in {"email", "e-mail"}:
                element["type"] = "input"
                element["input_type"] = "email"
            elif normalized in {"password", "passcode"}:
                element["type"] = "input"
                element["input_type"] = "password"
        else:
            normalized = " ".join(item["text"].lower().split())
            nearby_fields = []
            if normalized in {"email", "e-mail", "password", "passcode"}:
                for i, element in enumerate(elements):
                    x_left, y_top, x_right, y_bottom = element["bbox"]
                    vertical_gap = y_top - y2
                    if (element["type"] == "container" and vertical_gap >= -2
                            and vertical_gap <= max(30, (y2 - y1) * 1.5)
                            and x1 < x_right and x2 > x_left):
                        nearby_fields.append((vertical_gap, i, element))
            if nearby_fields:
                _, _, field = min(nearby_fields, key=lambda candidate: candidate[0])
                field["type"] = "input"
                field["text"] = item["text"]
                field["input_type"] = "password" if normalized in {"password", "passcode"} else "email"
                field["confidence"] = item["confidence"]
            else:
                elements.append({
                    "id": f"text_{text_index + 1:03d}", "type": "text",
                    "text": item["text"], "bbox": item["bbox"],
                    "confidence": item["confidence"],
                })
    return elements


def _decode_image(image_bytes):
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            if source.format not in ALLOWED_FORMATS:
                raise HTTPException(status_code=400, detail="Supported formats are PNG, JPEG, WEBP, and BMP.")
            width, height = source.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail="The image dimensions are too large.")
            source.verify()
        with Image.open(BytesIO(image_bytes)) as source:
            rgb = source.convert("RGB")
            return np.array(rgb), rgb.width, rgb.height, source.format
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid supported image.")


@app.post("/api/analyze", tags=["analysis"])
async def analyze_image(
    file: UploadFile = File(...),
    provider: str = Form("auto"),
    current_user: dict = Depends(_current_user),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    image_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The upload exceeds the 12 MB limit.")

    provider = provider.strip().lower()
    if provider not in {"auto", "openai", "local"}:
        raise HTTPException(status_code=400, detail="provider must be auto, openai, or local.")

    image_rgb, width, height, image_format = _decode_image(image_bytes)
    boxes = detect_rectangles(image_rgb)
    selected_provider = provider
    if selected_provider == "auto":
        configured_default = os.getenv("ANALYSIS_PROVIDER", "auto").strip().lower()
        if configured_default in {"openai", "local"}:
            selected_provider = configured_default
        else:
            selected_provider = "openai" if os.getenv("OPENAI_API_KEY", "").strip() else "local"

    try:
        if selected_provider == "openai":
            ai_result = await analyze_with_openai(
                image_bytes, image_format, width, height, boxes
            )
            text_items = ai_result["recognized_text"]
            elements = _merge_detections(boxes, text_items, width, height)
            for shape in ai_result["shapes"]:
                index = shape["shape_index"]
                if index is None:
                    element = {
                        "id": f"vision_{len(elements) + 1:03d}",
                        "bbox": shape["bbox"],
                        "confidence": None,
                    }
                    elements.append(element)
                elif index < len(boxes):
                    element = elements[index]
                else:
                    continue
                element["type"] = shape["type"]
                element["bbox"] = shape["bbox"]
                if shape["text"]:
                    element["text"] = shape["text"]
                if shape["type"] == "input" and shape["input_type"]:
                    element["input_type"] = shape["input_type"]
        else:
            text_items = recognize_text(image_rgb)
            elements = _merge_detections(boxes, text_items, width, height)
    except OpenAIAnalyzerConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OpenAIAnalyzerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    result = {"image_width": width, "image_height": height, "elements": elements}

    return {
        "status": "success",
        "image": {"width": width, "height": height},
        "elements": elements,
        "recognized_text": text_items,
        "analysis_provider": selected_provider,
        "html": generate_html(result),
        "css": generate_css(result),
        "javascript": generate_javascript(result),
        "message": "Sketch analyzed. Review estimated text confidence and generated controls before using the code.",
    }


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
