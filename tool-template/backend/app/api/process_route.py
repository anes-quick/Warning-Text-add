import asyncio
import logging
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from tempfile import mkdtemp

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

router = APIRouter(tags=["video"])
logger = logging.getLogger("warning_text.process")

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v", ".mkv"}
OUT_NAME = "warning-text-output.mp4"


def _overlays_dir() -> Path:
    override = os.environ.get("OVERLAY_ASSETS_DIR", "").strip()
    if override:
        p = Path(override)
        if (p / "Bottom.png").is_file():
            return p
    here = Path(__file__).resolve().parent
    candidates = [
        Path("/app/assets/overlays"),
        Path.cwd() / "assets" / "overlays",
        here.parent.parent.parent.parent / "assets" / "overlays",
        here.parent.parent.parent / "assets" / "overlays",
    ]
    for c in candidates:
        if (c / "Bottom.png").is_file():
            return c
    logger.error("Overlay assets not found. Checked: %s", ", ".join(str(c) for c in candidates))
    # Return the primary container path so the error message is predictable.
    return Path("/app/assets/overlays")


def _overlay_png(placement: str) -> Path:
    name = "Bottom.png" if placement == "bottom" else "Top.png"
    p = _overlays_dir() / name
    if not p.is_file():
        raise FileNotFoundError(f"Missing overlay asset: {p}")
    return p


def _suffix(name: str) -> str:
    return Path(name).suffix.lower()


def _save_upload_sync(upload: UploadFile, dest: Path) -> None:
    with dest.open("wb") as out:
        shutil.copyfileobj(upload.file, out)


def _build_filter_complex_legacy() -> str:
    # Ported from the Windows .bat POC: fixed 1080x1920 output and full-frame PNG overlay.
    return (
        "[0:v]scale=1080:1920,setsar=1[bg];"
        "[1:v]scale=1080:1920,setsar=1[overlay];"
        "[bg][overlay]overlay=0:0:shortest=1,format=yuv420p[v]"
    )


def _video_encode_args() -> list[str]:
    if os.environ.get("NO_HW_ENCODE", "").strip() in ("1", "true", "yes"):
        return [
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
        ]
    # macOS: hardware H.264 is much faster for this use case.
    if platform.system() == "Darwin":
        return [
            "-c:v",
            "h264_videotoolbox",
            "-b:v",
            "12M",
            "-pix_fmt",
            "yuv420p",
        ]
    return [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
    ]


def _run_ffmpeg(
    input_path: Path,
    overlay_path: Path,
    output_path: Path,
) -> None:
    fc = _build_filter_complex_legacy()
    cmd: list[str] = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-loop",
        "1",
        "-i",
        str(overlay_path),
    ]
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "0:a?"]
    cmd += [
        "-c:a",
        "copy",
        "-shortest",
        *_video_encode_args(),
        str(output_path),
    ]
    logger.info("ffmpeg command: %s", " ".join(cmd))

    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    logger.info("ffmpeg finished rc=%s elapsed=%.2fs", proc.returncode, elapsed)
    if proc.returncode != 0:
        tail = (proc.stderr or "")[-8000:]
        logger.error("ffmpeg failed rc=%s stderr=%s", proc.returncode, tail)
        raise RuntimeError(tail or "ffmpeg failed")


def _cleanup_dir(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)


@router.post("/process")
async def process_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    placement: str = Form("bottom"),
) -> FileResponse:
    req_started = time.perf_counter()
    p = (placement or "bottom").strip().lower()
    if p not in ("bottom", "top"):
        raise HTTPException(status_code=400, detail='placement must be "bottom" or "top"')

    if not video.filename:
        raise HTTPException(status_code=400, detail="Video filename missing")
    ext = _suffix(video.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported type {ext or '(none)'}. Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    try:
        overlay_src = _overlay_png(p)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    logger.info(
        "process start file=%r placement=%r overlay=%s (%s bytes)",
        video.filename,
        p,
        overlay_src,
        overlay_src.stat().st_size,
    )

    work = mkdtemp(prefix="warnvid-")
    try:
        stage = time.perf_counter()
        input_path = Path(work) / f"input{ext}"
        overlay_copy = Path(work) / "overlay.png"
        output_path = Path(work) / OUT_NAME

        shutil.copy2(overlay_src, overlay_copy)
        logger.info("copied overlay in %.2fs", time.perf_counter() - stage)
        stage = time.perf_counter()
        await asyncio.to_thread(_save_upload_sync, video, input_path)
        logger.info("saved upload in %.2fs size=%s", time.perf_counter() - stage, input_path.stat().st_size)
        stage = time.perf_counter()
        await asyncio.to_thread(
            _run_ffmpeg,
            input_path,
            overlay_copy,
            output_path,
        )
        logger.info("ffmpeg stage done in %.2fs", time.perf_counter() - stage)
        logger.info("process done output_bytes=%s", output_path.stat().st_size)
    except RuntimeError as e:
        _cleanup_dir(work)
        raise HTTPException(status_code=422, detail="Could not process video. Try another file or format.") from e
    except Exception as e:
        _cleanup_dir(work)
        raise HTTPException(status_code=500, detail="Processing failed") from e

    background_tasks.add_task(_cleanup_dir, work)
    logger.info("process total elapsed %.2fs", time.perf_counter() - req_started)
    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=OUT_NAME,
    )
