from app.layout.layout_engine import prepare_elements

BASE_CSS = """\
* { box-sizing: border-box; }

body {
    margin: 0;
    padding: clamp(8px, 3vw, 24px);
    background: #f0f0f0;
    font-family: Arial, Helvetica, sans-serif;
}

.sketch-canvas {
    position: relative;
    width: 100%;
    max-width: 900px;
    margin: 0 auto;
    aspect-ratio: {ratio};
    background: white;
    border: 1px solid #ddd;
    container-type: inline-size;
}

.sketch-element {
    position: absolute;
    overflow-wrap: anywhere;
    font-size: var(--fs, 16px);
}

.sketch-button {
    border: 1px solid #555;
    border-radius: 4px;
    background: #f5f5f5;
    cursor: pointer;
}

.sketch-input {
    border: 1px solid #888;
    border-radius: 4px;
    padding: 0 8px;
    background: white;
}

.sketch-text {
    margin: 0;
    display: flex;
    align-items: center;
}

.sketch-image {
    border: 1px dashed #999;
    background: #eee;
    color: #777;
    display: flex;
    align-items: center;
    justify-content: center;
}

.sketch-container {
    border: 1px solid #bbb;
    border-radius: 6px;
}

.interaction-status {
    position: absolute;
    inset: auto 2% 2%;
    z-index: 10;
    width: auto;
    margin: 0;
    padding: 10px 12px;
    border: 1px solid #c9c3ed;
    border-radius: 8px;
    background: #f7f5ff;
    color: #403574;
    font: 13px/1.4 Arial, Helvetica, sans-serif;
}

.sketch-input[aria-invalid="true"] {
    outline: 2px solid #d45f69;
}
"""


def generate_css(data):
    elements = prepare_elements(data)
    ratio = f"{data['image_width']} / {data['image_height']}"
    css = BASE_CSS.replace("{ratio}", ratio)

    rules = []
    for el in elements:
        b = el["box"]
        rules.append(
            f"#{el['id']} {{\n"
            f"    left: {b['left']}%;\n"
            f"    top: {b['top']}%;\n"
            f"    width: {b['width']}%;\n"
            f"    height: {b['height']}%;\n"
            f"    --fs: {el['font_size']}cqw;\n"
            f"}}\n"
        )
    return css + "\n" + "\n".join(rules)
