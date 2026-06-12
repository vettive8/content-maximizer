import os
import subprocess
import time
from typing import Callable, Dict, Optional, Tuple

import yt_dlp
from video_transcriber import get_uploaded_media_path

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ProgressCallback = Callable[[Dict], None]


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _sanitize_title(title: str) -> str:
    cleaned = "".join([c for c in str(title or "") if c.isalnum() or c in (" ", "-", "_")]).strip()
    return cleaned or "clip"


def get_source_video_path(video_id: str) -> Optional[str]:
    """Return cached source path if present."""
    for ext in ("mp4", "webm", "mkv"):
        candidate = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


def get_upload_source_video_path(source_id: str) -> Optional[str]:
    """Return uploaded source path if present."""
    path = get_uploaded_media_path(source_id)
    if path and os.path.exists(path):
        return path
    return None


def build_clip_filename(video_id: str, start_time: float, end_time: float, title: str) -> str:
    safe_title = _sanitize_title(title)
    start_int = int(round(_safe_float(start_time, 0.0)))
    end_int = int(round(_safe_float(end_time, start_int + 1)))
    return f"{safe_title}_{start_int}_{end_int}.mp4"


def get_clip_output_path(video_id: str, start_time: float, end_time: float, title: str) -> str:
    return os.path.join(DOWNLOAD_DIR, build_clip_filename(video_id, start_time, end_time, title))


def get_upload_clip_output_path(source_id: str, start_time: float, end_time: float, title: str) -> str:
    safe_source = _sanitize_title(f"upload_{source_id}").replace(" ", "_")
    base = build_clip_filename(source_id, start_time, end_time, title)
    return os.path.join(DOWNLOAD_DIR, f"{safe_source}_{base}")


def download_video(video_id: str, progress_callback: Optional[ProgressCallback] = None) -> Tuple[Optional[str], bool]:
    """
    Download full source video if needed.
    Returns (video_path, source_cached).
    """
    cached = get_source_video_path(video_id)
    if cached:
        if progress_callback:
            progress_callback({
                "stage": "source_cached",
                "percent": 100,
                "message": "Source already cached",
                "eta_seconds": 0,
            })
        return cached, True

    url = f"https://www.youtube.com/watch?v={video_id}"
    output_template = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")

    def _progress_hook(data):
        if not progress_callback:
            return
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            percent = (downloaded / total * 100.0) if total else None
            progress_callback({
                "stage": "downloading_source",
                "percent": percent,
                "eta_seconds": data.get("eta"),
                "speed_bytes_per_sec": data.get("speed"),
                "message": "Downloading source video",
            })
        elif status == "finished":
            progress_callback({
                "stage": "downloading_source",
                "percent": 100,
                "eta_seconds": 0,
                "message": "Source download completed",
            })

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:
        print(f"Error downloading video: {exc}")
        return None, False

    resolved = get_source_video_path(video_id)
    return resolved, False


def slice_clip(
    video_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> bool:
    """Slice a clip using ffmpeg and emit progress by parsing `-progress pipe:1`."""
    duration = max(1.0, _safe_float(end_time, 0.0) - _safe_float(start_time, 0.0))
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_time),
        "-i",
        video_path,
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "aac",
        "-progress",
        "pipe:1",
        "-nostats",
        output_path,
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as exc:
        print(f"Error starting ffmpeg: {exc}")
        return False

    try:
        slice_wall_start = time.time()
        if progress_callback:
            progress_callback({
                "stage": "slicing_clip",
                "percent": 0,
                "message": "Slicing clip",
                "eta_seconds": duration,
            })

        for line in process.stdout or []:
            line = line.strip()
            if not line:
                continue
            if line.startswith("out_time_ms="):
                out_time_ms = _safe_float(line.split("=", 1)[1], 0.0)
                processed_seconds = out_time_ms / 1_000_000.0
                percent = max(0.0, min(100.0, (processed_seconds / duration) * 100.0))
                if progress_callback:
                    remaining_media = max(0.0, duration - processed_seconds)
                    elapsed_wall = max(0.001, time.time() - slice_wall_start)
                    speed_ratio = max(0.05, processed_seconds / elapsed_wall)
                    eta_wall = remaining_media / speed_ratio
                    progress_callback({
                        "stage": "slicing_clip",
                        "percent": percent,
                        "eta_seconds": eta_wall,
                        "message": "Slicing clip",
                    })
            elif line == "progress=end":
                if progress_callback:
                    progress_callback({
                        "stage": "slicing_clip",
                        "percent": 100,
                        "eta_seconds": 0,
                        "message": "Clip slice completed",
                    })

        return process.wait() == 0
    except Exception as exc:
        print(f"Error slicing clip: {exc}")
        return False


def prepare_clip(
    video_id: str,
    start_time: float,
    end_time: float,
    title: str,
    progress_callback: Optional[ProgressCallback] = None,
):
    """
    Full orchestration for source download + clipping.
    Returns (clip_path, error, meta).
    """
    overall_start = time.time()
    clip_path = get_clip_output_path(video_id, start_time, end_time, title)

    source_start = time.time()
    video_path, source_cached = download_video(video_id, progress_callback=progress_callback)
    source_elapsed = 0.0 if source_cached else (time.time() - source_start)
    if not video_path:
        return None, "Failed to download source video", {
            "source_cached": source_cached,
            "clip_cached": False,
            "source_elapsed_seconds": round(source_elapsed, 2),
            "slice_elapsed_seconds": 0.0,
            "total_elapsed_seconds": round(time.time() - overall_start, 2),
        }

    if os.path.exists(clip_path):
        if progress_callback:
            progress_callback({
                "stage": "clip_cached",
                "percent": 100,
                "eta_seconds": 0,
                "message": "Clip already cached",
            })
        return clip_path, None, {
            "source_cached": source_cached,
            "clip_cached": True,
            "source_elapsed_seconds": round(source_elapsed, 2),
            "slice_elapsed_seconds": 0.0,
            "total_elapsed_seconds": round(time.time() - overall_start, 2),
        }

    slice_start = time.time()
    success = slice_clip(video_path, start_time, end_time, clip_path, progress_callback=progress_callback)
    slice_elapsed = time.time() - slice_start
    total_elapsed = time.time() - overall_start
    if success:
        return clip_path, None, {
            "source_cached": source_cached,
            "clip_cached": False,
            "source_elapsed_seconds": round(source_elapsed, 2),
            "slice_elapsed_seconds": round(slice_elapsed, 2),
            "total_elapsed_seconds": round(total_elapsed, 2),
        }

    return None, "Failed to slice clip", {
        "source_cached": source_cached,
        "clip_cached": False,
        "source_elapsed_seconds": round(source_elapsed, 2),
        "slice_elapsed_seconds": round(slice_elapsed, 2),
        "total_elapsed_seconds": round(total_elapsed, 2),
    }


def prepare_upload_clip(
    source_id: str,
    start_time: float,
    end_time: float,
    title: str,
    progress_callback: Optional[ProgressCallback] = None,
):
    """
    Slice a clip from a locally uploaded source video.
    Returns (clip_path, error, meta).
    """
    overall_start = time.time()
    source_path = get_upload_source_video_path(source_id)
    if not source_path:
        return None, "Uploaded source video not found", {
            "source_cached": True,
            "clip_cached": False,
            "source_elapsed_seconds": 0.0,
            "slice_elapsed_seconds": 0.0,
            "total_elapsed_seconds": round(time.time() - overall_start, 2),
        }

    clip_path = get_upload_clip_output_path(source_id, start_time, end_time, title)
    if os.path.exists(clip_path):
        if progress_callback:
            progress_callback({
                "stage": "clip_cached",
                "percent": 100,
                "eta_seconds": 0,
                "message": "Clip already cached",
            })
        return clip_path, None, {
            "source_cached": True,
            "clip_cached": True,
            "source_elapsed_seconds": 0.0,
            "slice_elapsed_seconds": 0.0,
            "total_elapsed_seconds": round(time.time() - overall_start, 2),
        }

    slice_start = time.time()
    success = slice_clip(source_path, start_time, end_time, clip_path, progress_callback=progress_callback)
    slice_elapsed = time.time() - slice_start
    total_elapsed = time.time() - overall_start
    if success:
        return clip_path, None, {
            "source_cached": True,
            "clip_cached": False,
            "source_elapsed_seconds": 0.0,
            "slice_elapsed_seconds": round(slice_elapsed, 2),
            "total_elapsed_seconds": round(total_elapsed, 2),
        }

    return None, "Failed to slice clip", {
        "source_cached": True,
        "clip_cached": False,
        "source_elapsed_seconds": 0.0,
        "slice_elapsed_seconds": round(slice_elapsed, 2),
        "total_elapsed_seconds": round(total_elapsed, 2),
    }


def get_clip_path(video_id, start, end, title):
    """
    Backward-compatible API used by the existing synchronous endpoint.
    Returns (clip_path, error).
    """
    clip_path, error, _ = prepare_clip(video_id, start, end, title, progress_callback=None)
    return clip_path, error
