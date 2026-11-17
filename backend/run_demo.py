import argparse
import json
from pathlib import Path

from app.generator.html_generator import write_site

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Generate a demo HTML/CSS page from sketch element JSON.")
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=PROJECT_ROOT / "dataset" / "sample_login.json",
        help="Input JSON file (defaults to the sample login sketch).",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=PROJECT_ROOT / "demo_output",
        help="Output directory (defaults to demo_output at the project root).",
    )
    args = parser.parse_args()

    input_path = args.input.resolve()
    output_path = args.output.resolve()
    data = json.loads(input_path.read_text(encoding="utf-8"))
    write_site(data, output_path)
    print(f"Generated: {output_path / 'index.html'}")


if __name__ == "__main__":
    main()
