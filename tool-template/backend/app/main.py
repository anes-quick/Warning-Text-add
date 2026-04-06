import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .api import router as api_router

logger = logging.getLogger("warning_text.app")


def _setup_logging() -> None:
    # Ensure app-level INFO logs are visible in local uvicorn runs.
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    logging.getLogger("warning_text").setLevel(logging.INFO)


def _index_html_path() -> Path:
    env = os.environ.get("FRONTEND_INDEX", "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p
    app_dir = Path(__file__).resolve().parent
    # Local: tool-template/backend/app/main.py → tool-template/index.html
    repo = app_dir.parent.parent / "index.html"
    if repo.is_file():
        return repo
    # Docker: COPY index.html /app/index.html next to backend package
    bundled = app_dir.parent / "index.html"
    if bundled.is_file():
        return bundled
    raise FileNotFoundError(
        "index.html not found. Set FRONTEND_INDEX or ensure index.html is copied into the image."
    )


def create_app() -> FastAPI:
    _setup_logging()
    app = FastAPI(title="Warning Text Tool API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:8001",
            "http://127.0.0.1:8001",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_origin_regex=r"https://.*\.vercel\.app|http://(localhost|127\.0\.0\.1):\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("%s %s", request.method, request.url.path)
            raise
        elapsed = time.perf_counter() - start
        logger.info(
            "%s %s -> %s in %.2fs",
            request.method,
            request.url.path,
            getattr(response, "status_code", "?"),
            elapsed,
        )
        return response

    @app.get("/")
    async def serve_ui() -> FileResponse:
        path = _index_html_path()
        return FileResponse(path, media_type="text/html; charset=utf-8")

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
