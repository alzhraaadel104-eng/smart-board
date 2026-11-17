# Original project work areas

This project follows the five work areas in the original team plan:

1. **Computer Vision** — `backend/app/vision/detector.py` detects rectangular regions and returns pixel coordinates. The original Colab prototype remains in `Task_1.ipynb`. Known weak cases include faint strokes, nested/overlapping shapes, skewed photos, and non-rectangular controls.
2. **OCR and Dataset** — `backend/app/vision/ocr.py` recognizes English text locally; `backend/app/vision/openai_analyzer.py` uses OpenAI Vision for schema-structured labels and shape classification. `dataset/ocr_evaluation_cases.json` is a starter checklist for Login, Email, Password, and Sign in. Add labeled example images and record expected text, actual text, and confidence when expanding evaluation; the checklist is not a claim of measured accuracy.
3. **Code Generation** — `backend/app/layout/layout_engine.py` validates the shared element data; `backend/app/generator/` generates separate HTML and CSS. The API uses pixel-space boxes and normalizes them to percentages for responsive output.
4. **Backend and Integration** — `backend/app/main.py` exposes `/health` and `/api/analyze`, validates uploads, joins CV/OCR results, and returns generated code.
5. **Frontend and Coordination** — `frontend/src/` contains the React + Vite dashboard, upload flow, code tabs, and generated-page preview. GitHub Actions builds the frontend and runs the backend checks. GitHub issues can track additions to OCR samples and hard CV cases.

OCR role mapping is intentionally simple: Email/E-mail becomes an email input, Password/Passcode a password input, and common action labels such as Login/Sign in become buttons when the label is inside a detected shape. Other recognized words are emitted as text elements. Review generated results because handwriting and geometry can be ambiguous.
