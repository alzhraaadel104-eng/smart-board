"""Detect rectangular regions in a sketch image with OpenCV.

This intentionally detects geometry only. It does not recognize text or infer
whether a rectangle is a button, input, or another kind of UI component.
"""

import cv2
import numpy as np


def _intersection_over_union(first, second):
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    left = max(ax, bx)
    top = max(ay, by)
    right = min(ax + aw, bx + bw)
    bottom = min(ay + ah, by + bh)
    intersection = max(0, right - left) * max(0, bottom - top)
    union = aw * ah + bw * bh - intersection
    return intersection / union if union else 0.0


def _suppress_duplicates(boxes, threshold=0.88):
    kept = []
    for box in sorted(boxes, key=lambda item: item[2] * item[3], reverse=True):
        if all(_intersection_over_union(box, existing) < threshold for existing in kept):
            kept.append(box)
    return kept


def detect_rectangles(image_rgb):
    """Return detected rectangles as ``(x, y, width, height)`` pixel boxes."""
    if not isinstance(image_rgb, np.ndarray) or image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("image_rgb must be an RGB image array.")
    if image_rgb.size == 0:
        raise ValueError("image_rgb cannot be empty.")

    height, width = image_rgb.shape[:2]
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 100)
    threshold_value, binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    del threshold_value
    combined = cv2.bitwise_or(edges, binary)
    kernel = np.ones((3, 3), dtype=np.uint8)
    closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    image_area = width * height
    minimum_area = max(64, image_area * 0.0002)
    maximum_area = image_area * 0.96
    candidates = []
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue
        polygon = cv2.approxPolyDP(contour, 0.025 * perimeter, True)
        if len(polygon) != 4 or not cv2.isContourConvex(polygon):
            continue

        x, y, box_width, box_height = cv2.boundingRect(polygon)
        area = box_width * box_height
        aspect_ratio = box_width / box_height if box_height else 0
        if area < minimum_area or area > maximum_area:
            continue
        if not 0.12 <= aspect_ratio <= 8.0:
            continue
        candidates.append((int(x), int(y), int(box_width), int(box_height)))

    boxes = _suppress_duplicates(candidates)
    boxes.sort(key=lambda box: (box[1], box[0], -(box[2] * box[3])))
    return boxes
