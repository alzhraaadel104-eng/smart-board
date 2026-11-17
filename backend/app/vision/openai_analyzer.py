"""Image understanding and UI element classification through OpenAI Responses API."""

import asyncio
import base64
from io import BytesIO
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image


class OpenAIAnalyzerError(RuntimeError):
    """Safe-to-display configuration or upstream API error."""


class OpenAIAnalyzerConfigError(OpenAIAnalyzerError):
    """Missing local configuration for the optional provider."""


_COMPONENT_TYPES = ["button", "input", "text", "image", "container"]
_INPUT_TYPES = ["", "text", "email", "password", "search", "number", "tel", "url"]
_SCHEMA = {
    "type": "object",
    "properties": {
        "recognized_text": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "bbox": {"type": "array", "items": {"type": "integer"}},
                    "confidence": {"type": "number"},
                },
                "required": ["text", "bbox", "confidence"],
                "additionalProperties": False,
            },
        },
        "shapes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "shape_index": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                    "bbox": {"type": "array", "items": {"type": "integer"}},
                    "type": {"type": "string", "enum": _COMPONENT_TYPES},
                    "text": {"type": "string"},
                    "input_type": {"type": "string", "enum": _INPUT_TYPES},
                },
                "required": ["shape_index", "bbox", "type", "text", "input_type"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["recognized_text", "shapes"],
    "additionalProperties": False,
}


def _image_data_url(image_bytes, image_format):
    media_type = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}.get(image_format)
    if media_type:
        payload = image_bytes
    else:
        with Image.open(BytesIO(image_bytes)) as source:
            converted = source.convert("RGB")
            stream = BytesIO()
            converted.save(stream, format="PNG")
            payload = stream.getvalue()
        media_type = "image/png"
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _send_request(payload, api_key):
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise OpenAIAnalyzerConfigError(
            f"OpenAI API returned HTTP {exc.code}. Check API key, model access, and account billing."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise OpenAIAnalyzerError("Could not reach OpenAI API. Check internet access and try again.") from exc


def _response_text(response_data):
    if isinstance(response_data.get("output_text"), str):
        return response_data["output_text"]
    for output_item in response_data.get("output", []):
        if output_item.get("type") != "message":
            continue
        for content_item in output_item.get("content", []):
            if content_item.get("type") == "output_text":
                return content_item.get("text", "")
    raise OpenAIAnalyzerError("OpenAI returned no structured analysis. Try another image.")


def _clean_result(result, image_width, image_height, candidate_count):
    words = []
    for word in result.get("recognized_text", []):
        text = str(word.get("text", "")).strip()
        bbox = word.get("bbox")
        if not text or not isinstance(bbox, list) or len(bbox) != 4:
            continue
        try:
            x1, y1, x2, y2 = [int(value) for value in bbox]
            confidence = float(word.get("confidence", 0.5))
        except (TypeError, ValueError, OverflowError):
            continue
        x1, x2 = max(0, min(x1, image_width)), max(0, min(x2, image_width))
        y1, y2 = max(0, min(y1, image_height)), max(0, min(y2, image_height))
        if x2 <= x1 or y2 <= y1:
            continue
        words.append({
            "text": text,
            "bbox": [x1, y1, x2, y2],
            "confidence": round(max(0.0, min(confidence, 1.0)), 4),
        })

    shapes = []
    for shape in result.get("shapes", []):
        index = shape.get("shape_index")
        if index is not None and (
            not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < candidate_count
        ):
            continue
        component_type = shape.get("type")
        if component_type not in _COMPONENT_TYPES:
            continue
        bbox = shape.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        try:
            x1, y1, x2, y2 = [int(value) for value in bbox]
        except (TypeError, ValueError, OverflowError):
            continue
        x1, x2 = max(0, min(x1, image_width)), max(0, min(x2, image_width))
        y1, y2 = max(0, min(y1, image_height)), max(0, min(y2, image_height))
        if x2 <= x1 or y2 <= y1:
            continue
        input_type = shape.get("input_type", "")
        if input_type not in _INPUT_TYPES:
            input_type = ""
        shapes.append({
            "shape_index": index,
            "bbox": [x1, y1, x2, y2],
            "type": component_type,
            "text": str(shape.get("text", "")).strip(),
            "input_type": input_type,
        })
    return {"recognized_text": words, "shapes": shapes}


async def analyze_with_openai(image_bytes, image_format, image_width, image_height, candidate_boxes):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise OpenAIAnalyzerConfigError(
            "OPENAI_API_KEY is missing. Add it to the project .env file, then restart the backend."
        )

    model = os.getenv("OPENAI_MODEL", "gpt-6.1-sol").strip() or "gpt-6.1-sol"
    prompt = (
        f"Canvas size: {image_width} by {image_height} pixels.\n"
        "Read all clearly visible English labels exactly as written. For every text item, return its tight pixel bounding box "
        "[x1,y1,x2,y2] on this original canvas and an estimated confidence from 0 to 1. Do not invent unreadable text.\n"
        "Identify every clear UI component in the image, including rectangles missed by the supplied candidates. Return one "
        "shape record per supplied candidate, using its candidate index as shape_index, and add any other visible UI components "
        "with shape_index null. Include each component's tight pixel bbox [x1,y1,x2,y2]. Choose button, input, image, text, or "
        "container. Use the nearest associated label as text; "
        "classify common email/password fields correctly. If uncertain, use container and an empty input_type.\n"
        f"Rectangle candidates (pixel x,y,width,height): {json.dumps(candidate_boxes, separators=(',', ':'))}"
    )
    payload = {
        "model": model,
        "reasoning": {"effort": "low"},
        "input": [
            {"role": "system", "content": "Analyze UI sketches. Return only the requested structured data. Coordinates must be integer pixels on the original image canvas."},
            {"role": "user", "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": _image_data_url(image_bytes, image_format), "detail": "high"},
            ]},
        ],
        "text": {"format": {
            "type": "json_schema",
            "name": "sketch_analysis",
            "strict": True,
            "schema": _SCHEMA,
        }},
        "max_output_tokens": 6000,
    }
    response_data = await asyncio.to_thread(_send_request, payload, api_key)
    try:
        parsed = json.loads(_response_text(response_data))
    except json.JSONDecodeError as exc:
        raise OpenAIAnalyzerError("OpenAI returned invalid structured data. Try again.") from exc
    return _clean_result(parsed, image_width, image_height, len(candidate_boxes))
