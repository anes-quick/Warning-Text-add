ok# Warning Text Web App — Build Roadmap

Living context for implementation. **Active codebase:** `tool-template/` (FastAPI + static `index.html`, same Vercel + Railway pattern as the template).

---

## Product (MVP)

- **Input:** User drags/drops a **portrait (9:16)** video file.
- **Action:** User enters **one text string**, clicks **Process**.
- **Output:** Video normalized to **1080×1920** with **one text overlay** near the bottom (full duration), downloadable as MP4.
- **Constraint:** Source videos may differ in resolution but keep **the same aspect ratio** as 1080×1920.

Non-goals for v1: accounts, cloud storage, queues, multi-line editor, timeline keyframes, batch jobs.

---

## Architecture

| Layer        | Host    | Role |
|-------------|---------|------|
| Frontend    | Vercel  | `tool-template/index.html` — drop zone, text, process, download |
| API + FFmpeg | Railway | `tool-template/backend/` FastAPI — `POST /api/process`, FFmpeg in Docker |

**Why not FFmpeg on Vercel:** Serverless timeouts, payload limits, no dependable encode environment.

---

## Repository layout (current)

```
Warning Text Web App/
├── ROADMAP.md
└── tool-template/
    ├── index.html              ← frontend (Vercel)
    ├── assets/overlays/        ← Bottom.png, Top.png
    ├── vercel.json
    ├── Dockerfile              ← Railway: Python + FFmpeg
    └── backend/
        ├── requirements.txt
        └── app/
            ├── main.py         ← CORS, app factory
            └── api/
                ├── __init__.py ← routes: /health, /process
                └── process_route.py
```

---

## Technical decisions

- **Frontend:** Single static page (template style); `BACKEND_URL` in script (localhost:8000 vs Railway URL).
- **Backend:** FastAPI + `python-multipart`; FFmpeg via `subprocess`.
- **Overlay assets:** `tool-template/assets/overlays/Bottom.png` and `Top.png` (copied from repo root). Optional env **`OVERLAY_ASSETS_DIR`** to point at another folder. **`placement`** form field: `bottom` (default) or `top`.
- **FFmpeg pipeline:** `scale2ref` scales PNG to video **width** (aspect preserved), then `overlay` centered horizontally, **bottom** (`H-h`) or **top** (`0`). Video resolution unchanged.

---

## API

- **`GET /api/health`** → `{ "status": "ok" }`
- **`POST /api/process`** — `multipart/form-data`: `video` (file), `placement` (`bottom` | `top`, default `bottom`). Success: `video/mp4` bytes; errors: JSON `detail`.

---

## Build phases

### Phase 1 — API + FFmpeg
- [x] Docker image: Python + FFmpeg + DejaVu (`tool-template/Dockerfile`).
- [x] Upload endpoint, temp dir, background cleanup after response.
- [x] FFmpeg filter chain: scale → pad → PNG overlay (top/bottom).
- [ ] Manual / Docker smoke test with a real clip (local machine had no `ffmpeg` in PATH when last checked — use Docker or `brew install ffmpeg`).

### Phase 2 — Frontend
- [x] Drop zone, text input, process, loading/error, blob download link.
- [x] CORS includes localhost ports + `*.vercel.app` regex in `main.py`.

### Phase 3 — Deploy
- [ ] Railway: deploy from `tool-template` with Dockerfile; set public URL in `index.html` (`YOUR-RAILWAY-APP...`).
- [ ] Vercel: project root = `tool-template` (or monorepo subdir), same as template.
- [ ] End-to-end test on production URLs.

### Phase 4 — Polish (optional)
- [ ] Encode progress / timeouts tuning for long files.
- [ ] Client max-size hint vs Railway limits.
- [ ] Optional: `README.md` in `tool-template` with local dev + overlay asset paths.

---

## Local dev (quick)

```bash
cd tool-template/backend
python3 -m pip install -r requirements.txt
# Install ffmpeg (e.g. brew install ffmpeg) and optional:
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open **`http://127.0.0.1:8000`** or **`http://localhost:8000`** in the browser — FastAPI serves **`index.html` on `GET /`**, so the UI and **`/api/*`** share one origin (no CORS issues). Optional: still works from `python -m http.server` on another port if CORS allows it.

Logs: uvicorn default logging + `warning_text` logger lines for each request and for `/api/process` / ffmpeg failures.

---

## Open choices

- Default text: none required (empty rejected).
- Overlay: bottom-centered, boxed, fontsize 54 (see `process_route.py`).
- Max upload: not capped in code yet — align with Railway.

---

## Changelog

| Date       | Note |
|------------|------|
| 2026-04-04 | Roadmap created |
| 2026-04-04 | Built on `tool-template`: `/api/process`, UI, Docker FFmpeg |
