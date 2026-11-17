"""Lazy, CPU-friendly English OCR using EasyOCR."""

from functools import lru_cache

import numpy as np


@lru_cache(maxsize=1)
def _reader():
    try:
        import easyocr
    except ImportError as exc:
        raise RuntimeError(
            "EasyOCR is not installed. Install backend/requirements.txt and retry."
        ) from exc
    return easyocr.Reader(["en"], gpu=False)


def recognize_text(image_rgb, minimum_confidence=0.2):
    """Return recognized text with pixel-space axis-aligned boxes and confidence."""
    reader = _reader()
    detections = reader.readtext(image_rgb, detail=1, paragraph=False)
    items = []
    for polygon, text, confidence in detections:
        text = str(text).strip()
        confidence = float(confidence)
        if not text or confidence < minimum_confidence:
            continue
        points = np.asarray(polygon, dtype=float)
        items.append({
            "text": text,
            "bbox": [
                int(np.floor(points[:, 0].min())),
                int(np.floor(points[:, 1].min())),
                int(np.ceil(points[:, 0].max())),
                int(np.ceil(points[:, 1].max())),
            ],
            "confidence": round(confidence, 4),
        })
    return items
