from html import escape
from pathlib import Path

from app.layout.layout_engine import prepare_elements
from app.generator.css_generator import generate_css
from app.generator.javascript_generator import generate_javascript


def render_element(element):
    el_type = element["type"]
    el_id = escape(element["id"], quote=True)
    text = escape(element["text"])
    cls = f"sketch-element sketch-{escape(el_type, quote=True)}"

    if el_type == "button":
        return f'<button id="{el_id}" class="{cls}" type="button">{text or "Button"}</button>'
    if el_type == "input":
        input_type = escape(element["input_type"], quote=True)
        return f'<input id="{el_id}" class="{cls}" type="{input_type}" placeholder="{text}">'
    if el_type == "text":
        return f'<p id="{el_id}" class="{cls}">{text}</p>'
    if el_type == "image":
        return f'<div id="{el_id}" class="{cls}" role="img" aria-label="image placeholder">{text or "Image"}</div>'
    return f'<div id="{el_id}" class="{cls}">{text}</div>'


def generate_html(data, css_href="style.css", js_src="script.js"):
    if not isinstance(css_href, str) or any(char in css_href for char in "\r\n\"'"):
        raise ValueError("css_href must be a safe single-line path.")
    if not isinstance(js_src, str) or any(char in js_src for char in "\r\n\"'"):
        raise ValueError("js_src must be a safe single-line path.")
    elements = prepare_elements(data)
    body = "\n    ".join(render_element(el) for el in elements)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '    <meta charset="UTF-8">\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "    <title>Generated Page</title>\n"
        f'    <link rel="stylesheet" href="{escape(css_href)}">\n'
        "</head>\n"
        "<body>\n"
        '<div class="sketch-canvas">\n'
        f"    {body}\n"
        "</div>\n"
        f'<script src="{escape(js_src)}" defer></script>\n'
        "</body>\n"
        "</html>\n"
    )


def write_site(data, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(generate_html(data), encoding="utf-8")
    (out / "style.css").write_text(generate_css(data), encoding="utf-8")
    (out / "script.js").write_text(generate_javascript(data), encoding="utf-8")
    return out
