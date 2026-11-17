# Smart Sketch to Code Dashboard

Turn a hand-drawn interface into a live page and separate HTML, CSS, and JavaScript files. The project combines OpenCV rectangle detection, English OCR with EasyOCR, optional OpenAI Vision, a FastAPI backend, and a React + Vite dashboard with a server-validated sign-in screen.

## Requirements

- Python 3.11 (recommended for Docker parity; Python 3.12 may also work)
- Node.js 22 (Vite requires a current Node.js release)
- EasyOCR downloads its English recognition model the first time analysis runs; allow an internet connection for that first request.
- OpenAI API key if you want the higher-level vision classification option. OpenAI API usage is billed separately.

## Accounts and saved user data

The opening page offers **Sign in** and **Create an account**. Register with a username, email, and password of at least 8 characters. Registration signs you in immediately. Later, enter your email or username and password. User accounts are stored in `data/users.db`; passwords are saved only as PBKDF2-SHA256 hashes. A local session secret is generated automatically in `data/session.secret` unless `SESSION_SECRET` is set in `.env`.

For cloud hosting, set `DATABASE_PATH` to a persistent disk location, configure a private `SESSION_SECRET` with at least 32 characters, and use `COOKIE_SECURE=true` over HTTPS. Without a mounted persistent disk, a hosting service may discard the SQLite database during redeployment.

## Run in development

Open two PowerShell windows in the project root. In the first, start the backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

The app does not need a preconfigured admin account. If you want a stable session secret, generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set the generated value as `SESSION_SECRET` in `.env` if desired. Keep `COOKIE_SECURE=false` for localhost, and set it to `true` when serving over HTTPS. Accounts created through the signup page use a signed, HTTP-only session cookie.

To use OpenAI Vision, put your API key in `OPENAI_API_KEY`. The key stays on the server: the browser sends the image to FastAPI, which calls OpenAI. Never put the key in a `VITE_` variable or a frontend file. Set `ANALYSIS_PROVIDER=auto` to use OpenAI when configured and EasyOCR otherwise, or choose the engine in the dashboard.

After configuring `.env`, start the backend:

```powershell
python -m uvicorn main:app --reload --reload-dir backend
```

In the second window, start Vite:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). The Vite development server forwards `/api` and `/health` requests to FastAPI at port 8000. The backend API documentation is at `http://127.0.0.1:8000/docs`.

If Python 3.11 is not installed, use `python` instead of `py -3.11` and check its version with `python --version`. The virtual environment is created only after Python has been found; activate it only after the `venv` command succeeds.

The first local analysis may take longer while EasyOCR downloads and initializes its model. Later requests reuse the loaded reader. OpenAI Vision sends the image to the Responses API and asks for schema-constrained labels and shape classifications; OpenCV supplies the rectangle candidate coordinates. The API accepts PNG, JPEG, WEBP, and BMP images up to 12 MB and 20 megapixels.

## API

- `GET /health` checks that the API is running.
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, and `POST /api/auth/logout` manage user accounts and sessions.
- `POST /api/analyze` requires a valid sign-in session, accepts a multipart upload field named `file`, and returns detected elements, recognized text, and generated `html`, `css`, and `javascript` strings.

The vision pipeline identifies English labels and attaches text found inside detected shapes. Email and Password labels map to basic inputs; Login and Sign in map to buttons when placed inside a detected shape. Coordinates and type inference can still be imperfect on ambiguous handwriting, so review the result before using the generated files.

Use the **HTML**, **CSS**, and **JS** buttons in the result panel to download the generated files. Keep the three matching files in the same folder. The JavaScript adds basic field validation and button feedback as a starter; connect actions such as login or form submission to your own application/backend before production use. An example OCR sketch is included at `dataset/ocr_samples/login_form.png`.

## Production build and run

```powershell
cd frontend
npm install
npm run build
cd ..
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

After the Vite build exists in `frontend/dist`, FastAPI serves the React application at `/` along with the API. For Docker hosting, build from the project root:

```bash
docker build -t smart-sketch-to-code .
docker run --rm -p 8000:8000 smart-sketch-to-code
```

The container builds the React frontend and includes it with the FastAPI service. It uses the hosting platform's `PORT` environment variable. Configure `SESSION_SECRET`, `DATABASE_PATH` on a persistent disk, `COOKIE_SECURE=true`, `OPENAI_API_KEY`, `OPENAI_MODEL`, and optionally `ANALYSIS_PROVIDER` as hosting secrets/environment variables; do not commit credentials. GitHub hosts the source and runs CI; GitHub Pages cannot run this Python API.

## Generator demo

Generate a sample page from the included JSON data without uploading an image:

```powershell
python backend/run_demo.py
```

By default, this writes `demo_output/index.html`, `demo_output/style.css`, and `demo_output/script.js` from `dataset/sample_login.json`.

## Tests and CI

```powershell
python -m pip install -r backend\requirements.txt
python -m pytest -c backend\pytest.ini
```

GitHub Actions builds the Vite frontend and runs the Python suite on pushes and pull requests. The API test stubs OCR, so it does not download model weights.

## Project structure

```text
backend/app/main.py                 FastAPI API and production static serving
backend/app/vision/detector.py      OpenCV rectangle detection
backend/app/vision/ocr.py           Lazy EasyOCR reader and text coordinates
backend/app/layout/layout_engine.py Element validation and positioning
backend/app/generator/              HTML, CSS, and JavaScript generation
backend/tests/                      API and generator tests
frontend/src/                       React dashboard and styles
frontend/package-lock.json          Reproducible npm dependencies
frontend/vite.config.js             Local API proxy
dataset/                            Example layouts, OCR sample image, and evaluation cases
demo_output/                        Generated sample page
Task_1.ipynb                        Original Colab computer-vision prototype
Dockerfile                          Frontend build and API deployment
.github/workflows/ci.yml            GitHub Actions build and checks
```

