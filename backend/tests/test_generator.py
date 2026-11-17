import json
from pathlib import Path

import pytest

from app.layout.layout_engine import normalize_bbox, prepare_elements
from app.generator.html_generator import generate_html, write_site
from app.generator.css_generator import generate_css

DATASET = Path(__file__).resolve().parents[2] / "dataset"


def load(name):
    return json.loads((DATASET / name).read_text(encoding="utf-8"))


def test_normalize_bbox_basic():
    box = normalize_bbox([100, 200, 350, 250], 1000, 800)
    assert box == {"left": 10.0, "top": 25.0, "width": 25.0, "height": 6.25}


def test_normalize_bbox_clamps_outside_image():
    box = normalize_bbox([800, 600, 1200, 900], 1000, 800)
    assert box["left"] + box["width"] <= 100
    assert box["top"] + box["height"] <= 100


@pytest.mark.parametrize("bad", [
    [300, 300, 100, 100],
    [1, 2, 3],
    "abc",
    None,
    [1, 2, "x", 4],
])
def test_normalize_bbox_invalid(bad):
    with pytest.raises(ValueError):
        normalize_bbox(bad, 1000, 800)


@pytest.mark.parametrize("w,h", [(0, 800), (1000, 0), (-5, 800), (None, 800)])
def test_normalize_bbox_invalid_image_size(w, h):
    with pytest.raises(ValueError):
        normalize_bbox([0, 0, 10, 10], w, h)


def test_html_contains_all_elements():
    html = generate_html(load("sample_login.json"))
    assert "<button" in html
    assert html.count("<input") == 2
    assert 'placeholder="Email"' in html
    assert 'type="password" placeholder="Password"' in html
    assert 'href="style.css"' in html


def test_html_escapes_script():
    html = generate_html(load("sample_hard_cases.json"))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_unknown_type_becomes_container():
    elements = prepare_elements(load("sample_hard_cases.json"))
    unknown = [e for e in elements if e["text"] == "Unknown type"][0]
    assert unknown["type"] == "container"


def test_bad_elements_are_skipped_not_crash():
    elements = prepare_elements(load("sample_hard_cases.json"))
    assert all(e["text"] != "Broken bbox" for e in elements)


def test_unsafe_id_is_replaced():
    html = generate_html(load("sample_hard_cases.json"))
    assert "bad id" not in html


def test_ids_are_unique():
    elements = prepare_elements(load("sample_hard_cases.json"))
    ids = [e["id"] for e in elements]
    assert len(ids) == len(set(ids))


def test_duplicate_ids_do_not_collide_with_fallback_ids():
    data = {
        "image_width": 100,
        "image_height": 100,
        "elements": [
            {"id": "bad id", "type": "text", "bbox": [0, 0, 10, 10]},
            {"id": "element_001", "type": "text", "bbox": [10, 10, 20, 20]},
        ],
    }
    ids = [element["id"] for element in prepare_elements(data)]
    assert len(ids) == len(set(ids))


def test_missing_image_size_raises():
    with pytest.raises(ValueError):
        generate_html({"elements": [{"type": "button", "bbox": [0, 0, 10, 10]}]})


def test_empty_elements_ok():
    html = generate_html({"image_width": 100, "image_height": 100, "elements": []})
    assert "sketch-canvas" in html


def test_css_has_rule_per_element():
    data = load("sample_login.json")
    css = generate_css(data)
    for el in data["elements"]:
        assert f"#{el['id']}" in css
    assert "position: absolute" in css
    assert "aspect-ratio: 1000 / 800" in css


def test_css_has_no_garbage_values():
    css = generate_css(load("sample_hard_cases.json"))
    assert "NaN" not in css and "None" not in css


def test_write_site_creates_files(tmp_path):
    write_site(load("sample_login.json"), tmp_path)
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "style.css").exists()
