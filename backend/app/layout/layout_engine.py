import math
import re

ALLOWED_TYPES = {"button", "input", "text", "image", "container"}
ALLOWED_INPUT_TYPES = {"text", "email", "password", "search", "number", "tel", "url"}
DEFAULT_TYPE = "container"


def _is_number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return math.isfinite(value)


def _valid_size(width, height):
    return _is_number(width) and _is_number(height) and width > 0 and height > 0


def normalize_bbox(bbox, image_width, image_height):
    if not _valid_size(image_width, image_height):
        raise ValueError("image_width and image_height must be positive finite numbers.")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise ValueError("bbox must be a list of 4 numbers.")
    if not all(_is_number(value) for value in bbox):
        raise ValueError("bbox values must be finite numbers.")

    x1, y1, x2, y2 = bbox
    x1 = max(0, min(x1, image_width))
    x2 = max(0, min(x2, image_width))
    y1 = max(0, min(y1, image_height))
    y2 = max(0, min(y2, image_height))

    if x2 <= x1 or y2 <= y1:
        raise ValueError("bbox must have positive width and height inside the image.")

    return {
        "left": round(x1 / image_width * 100, 2),
        "top": round(y1 / image_height * 100, 2),
        "width": round((x2 - x1) / image_width * 100, 2),
        "height": round((y2 - y1) / image_height * 100, 2),
    }


def safe_element_id(raw_id, index):
    if isinstance(raw_id, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", raw_id):
        return raw_id
    return f"element_{index + 1:03d}"


def _unique_id(raw_id, index, used_ids):
    candidate = safe_element_id(raw_id, index)
    if candidate not in used_ids:
        return candidate

    suffix = 1
    base = f"element_{index + 1:03d}"
    candidate = base
    while candidate in used_ids:
        suffix += 1
        candidate = f"{base}_{suffix}"
    return candidate


def prepare_elements(data):
    if not isinstance(data, dict):
        raise ValueError("data must be a dict with image_width, image_height, elements.")

    width = data.get("image_width")
    height = data.get("image_height")
    elements = data.get("elements")
    if not _valid_size(width, height):
        raise ValueError("image_width and image_height are required and must be positive finite numbers.")
    if not isinstance(elements, list):
        raise ValueError("'elements' must be a list.")

    prepared = []
    used_ids = set()
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            continue
        try:
            box = normalize_bbox(element.get("bbox"), width, height)
        except ValueError:
            continue

        element_type = element.get("type")
        if element_type not in ALLOWED_TYPES:
            element_type = DEFAULT_TYPE

        element_id = _unique_id(element.get("id"), index, used_ids)
        used_ids.add(element_id)

        text = element.get("text")
        if text is None:
            text = ""
        elif not isinstance(text, str):
            text = str(text)

        input_type = element.get("input_type", "text")
        if input_type not in ALLOWED_INPUT_TYPES:
            input_type = "text"

        font_size = round(box["height"] * height / width * 0.45, 2)
        prepared.append({
            "id": element_id,
            "type": element_type,
            "text": text,
            "input_type": input_type,
            "box": box,
            "font_size": font_size,
        })

    prepared.sort(key=lambda item: 0 if item["type"] == "container" else 1)
    return prepared
