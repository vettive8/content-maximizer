"""
Helpers for uploaded MP4 handling and Gemini-based transcription.
"""

import json
import os
import re
import time
from typing import Dict, List, Optional, Tuple

from google.genai import types

from transcript_fetcher import seconds_to_timestamp


UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

SUPPORTED_EXTENSIONS = {".mp4"}
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
DEFAULT_THINKING_LEVEL = os.environ.get("GEMINI_THINKING_LEVEL", "low")


def _safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sanitize_media_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", str(value or ""))


def is_supported_upload(filename: str) -> bool:
    ext = os.path.splitext(str(filename or ""))[1].lower()
    return ext in SUPPORTED_EXTENSIONS


def get_uploaded_media_path(media_id: str) -> Optional[str]:
    safe_id = _sanitize_media_id(media_id)
    if not safe_id:
        return None
    return os.path.join(UPLOADS_DIR, f"{safe_id}.mp4")


def save_uploaded_mp4(file_storage, media_id: str) -> Dict[str, str]:
    if file_storage is None:
        raise ValueError("Missing file")

    filename = file_storage.filename or ""
    if not is_supported_upload(filename):
        raise ValueError("Only .mp4 files are supported")

    path = get_uploaded_media_path(media_id)
    if not path:
        raise ValueError("Invalid media ID")

    file_storage.save(path)
    return {
        "media_id": _sanitize_media_id(media_id),
        "path": path,
        "filename": filename,
    }


def _strip_json_fence(text: str) -> str:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _first_json_slice(text: str) -> str:
    object_idx = text.find("{")
    array_idx = text.find("[")
    starts = [idx for idx in (object_idx, array_idx) if idx >= 0]
    if not starts:
        return text
    return text[min(starts):]


def _parse_json_text(raw_text: str):
    cleaned = _strip_json_fence(raw_text)
    candidates = [cleaned, _first_json_slice(cleaned)]
    seen = set()
    decoder = json.JSONDecoder()
    for candidate in candidates:
        value = (candidate or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Best-effort parse if JSON is followed by trailing commentary.
            try:
                parsed, _ = decoder.raw_decode(value)
                return parsed
            except json.JSONDecodeError:
                repaired = _repair_json_text(value)
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    continue
    raise ValueError("Model returned invalid JSON transcript response")


def _repair_json_text(text: str) -> str:
    """Best-effort JSON repair for malformed model output."""
    repaired = []
    stack = []
    in_string = False
    escape = False

    for char in str(text or ""):
        if in_string:
            if escape:
                repaired.append(char)
                escape = False
                continue
            if char == "\\":
                repaired.append(char)
                escape = True
                continue
            if char == '"':
                repaired.append(char)
                in_string = False
                continue
            if char == "\n":
                repaired.append("\\n")
                continue
            if char == "\r":
                continue
            if ord(char) < 32:
                repaired.append(f"\\u{ord(char):04x}")
                continue
            repaired.append(char)
            continue

        if char == '"':
            in_string = True
            repaired.append(char)
            continue

        repaired.append(char)
        if char == "{":
            stack.append("}")
        elif char == "[":
            stack.append("]")
        elif char in ("}", "]") and stack and stack[-1] == char:
            stack.pop()

    if in_string:
        repaired.append('"')

    candidate = "".join(repaired)
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    if stack:
        candidate += "".join(reversed(stack))
    return candidate


def _collect_response_text(response) -> str:
    chunks = []

    direct_text = getattr(response, "text", None)
    if isinstance(direct_text, str) and direct_text.strip():
        chunks.append(direct_text.strip())

    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                chunks.append(part_text.strip())

    return "\n".join(chunks).strip()


def _extract_response_payload(response):
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, (dict, list)):
        return parsed

    raw_text = _collect_response_text(response)
    if not raw_text:
        return None
    return _parse_json_text(raw_text)


def _generate_content_with_retry(
    client,
    model_name: str,
    contents,
    config: Dict,
    max_attempts: int = 3,
    base_backoff_seconds: float = 1.0,
):
    """Retry transient model failures (e.g. 429/503) to reduce flaky 500s."""
    last_error = None
    request_config = dict(config or {})
    if str(model_name or "").startswith("gemini-3") and "thinking_config" not in request_config:
        request_config["thinking_config"] = {"thinking_level": DEFAULT_THINKING_LEVEL}
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=request_config,
            )
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            time.sleep(base_backoff_seconds * (2 ** (attempt - 1)))
    raise last_error


def _timestamp_to_seconds(value):
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value or "").strip()
    if not raw:
        return None
    numeric = _safe_float(raw, None)
    if numeric is not None:
        return numeric
    if not re.match(r"^\d{1,2}:\d{2}(?::\d{2})?$", raw):
        return None
    parts = [int(p) for p in raw.split(":")]
    if len(parts) == 2:
        mm, ss = parts
        return float(mm * 60 + ss)
    hh, mm, ss = parts
    return float(hh * 3600 + mm * 60 + ss)


def _normalize_segments(raw_segments) -> List[Dict]:
    normalized = []
    last_end = 0.0

    for item in raw_segments or []:
        if isinstance(item, str):
            text_line = item.strip()
            if not text_line:
                continue
            stamp_match = re.match(r"^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?(?:\([^)]+\))?\s*(.+)$", text_line)
            if stamp_match:
                start = _timestamp_to_seconds(stamp_match.group(1))
                text = stamp_match.group(2).strip()
            else:
                start = last_end
                text = text_line
            if not text:
                continue
            start = max(last_end, _safe_float(start, last_end))
            end = start + 2.5
        elif isinstance(item, dict):
            text = str(
                item.get("text")
                or item.get("content")
                or item.get("transcript")
                or ""
            ).strip()
            if not text:
                continue

            start = _timestamp_to_seconds(
                item.get("start")
                if item.get("start") is not None
                else item.get("start_time")
            )
            if start is None:
                start = _timestamp_to_seconds(item.get("timestamp"))
            if start is None:
                start = last_end

            end = _timestamp_to_seconds(
                item.get("end")
                if item.get("end") is not None
                else item.get("end_time")
            )
            duration = _timestamp_to_seconds(item.get("duration"))
            if end is None and duration is not None:
                end = start + duration
            if end is None or end <= start:
                end = start + max(1.0, duration if duration and duration > 0 else 2.5)

            start = max(0.0, _safe_float(start, 0.0))
            end = max(start + 0.5, _safe_float(end, start + 0.5))
            if start < last_end:
                shift = last_end - start
                start += shift
                end += shift
        else:
            continue

        duration = max(0.5, end - start)
        segment = {
            "start": round(start, 2),
            "duration": round(duration, 2),
            "text": text,
        }
        normalized.append(segment)
        last_end = segment["start"] + segment["duration"]

    return normalized


def _split_transcript_lines(raw_text: str) -> List[str]:
    normalized = str(raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    if "\n" not in normalized and "\\n" in normalized:
        normalized = normalized.replace("\\n", "\n")
    return [line for line in normalized.split("\n") if str(line).strip()]


def _build_transcript_text(segments: List[Dict]) -> str:
    lines = []
    for segment in segments:
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        timestamp = seconds_to_timestamp(float(segment.get("start", 0.0)))
        lines.append(f"[{timestamp}] {text}")
    return "\n".join(lines)


def _normalize_language_code(value: str) -> str:
    return "pl" if str(value or "").strip().lower() == "pl" else "en"


def _segments_from_payload(
    payload,
    fallback_language: str,
    raw_response_text: str = "",
) -> Tuple[List[Dict], str]:
    detected_language = _normalize_language_code(fallback_language)
    raw_segments = []

    if isinstance(payload, list):
        raw_segments = payload
    elif isinstance(payload, dict):
        raw_segments = (
            payload.get("segments")
            or payload.get("transcript_segments")
            or payload.get("items")
            or []
        )
        detected_language = _normalize_language_code(payload.get("language") or fallback_language)

    segments = _normalize_segments(raw_segments)
    if not segments and isinstance(payload, dict):
        transcript_text = str(payload.get("transcript") or "").strip()
        if transcript_text:
            segments = _normalize_segments(_split_transcript_lines(transcript_text))

    if not segments and raw_response_text:
        segments = _normalize_segments(_split_transcript_lines(raw_response_text))

    return segments, detected_language


def _clean_segment_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _looks_like_timestamp_only_text(text: str) -> bool:
    cleaned = _clean_segment_text(text).strip("\"'").strip(",.;: ")
    if not cleaned:
        return True
    return bool(re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", cleaned))


def _looks_like_json_snippet_text(text: str) -> bool:
    cleaned = _clean_segment_text(text)
    if not cleaned:
        return True
    if cleaned in {"{", "}", "[", "]"}:
        return True
    if cleaned.startswith('{"start"') or cleaned.startswith('"segments"') or cleaned.startswith('"language"'):
        return True
    markers = ('"start"', '"end"', '"text"', '"segments"', '"language"')
    marker_hits = sum(1 for marker in markers if marker in cleaned)
    return marker_hits >= 2


def _is_low_quality_transcript(segments: List[Dict]) -> bool:
    if not segments:
        return True

    texts = [_clean_segment_text(seg.get("text")) for seg in segments]
    texts = [text for text in texts if text]
    if not texts:
        return True

    total = len(texts)
    timestamp_only = sum(1 for text in texts if _looks_like_timestamp_only_text(text))
    jsonish = sum(1 for text in texts if _looks_like_json_snippet_text(text))
    alpha_like = sum(1 for text in texts if re.search(r"[A-Za-z]", text))

    parsed_times = []
    for text in texts:
        parsed = _timestamp_to_seconds(text.strip("\"'").strip(",.;: "))
        if parsed is not None:
            parsed_times.append(parsed)

    monotonic_ratio = 0.0
    if len(parsed_times) >= 12:
        non_decreasing = sum(1 for idx in range(1, len(parsed_times)) if parsed_times[idx] >= parsed_times[idx - 1])
        monotonic_ratio = non_decreasing / max(1, len(parsed_times) - 1)

    if total >= 25 and timestamp_only / total >= 0.45:
        return True
    if total >= 25 and jsonish / total >= 0.22:
        return True
    if total >= 50 and (timestamp_only + jsonish) / total >= 0.55:
        return True
    if alpha_like / total < 0.30:
        return True
    if monotonic_ratio > 0.9 and timestamp_only / total >= 0.2:
        return True
    return False


def _build_plaintext_fallback_prompt(language_name: str) -> str:
    return f"""Transcribe all spoken words from this video in {language_name}.

Return plain text only with one line per timestamp using this format:
[mm:ss] spoken words

Rules:
- Include the full spoken transcript from start to end.
- Every line must contain real spoken words after the timestamp.
- Never output standalone timestamps like "00:01" as transcript text.
- Do not output JSON, markdown, code fences, or explanations.
"""


def _resolve_file_state(file_obj) -> str:
    state = getattr(file_obj, "state", None)
    if state is None:
        return ""
    value = getattr(state, "value", None)
    if value:
        return str(value)
    return str(state)


def transcribe_uploaded_video(
    client,
    video_path: str,
    language: str = "pl",
    model_name: str = DEFAULT_GEMINI_MODEL,
    poll_seconds: float = 2.0,
    timeout_seconds: float = 180.0,
) -> Dict:
    if not client:
        return {"success": False, "error": "Gemini client is not configured"}
    if not video_path or not os.path.exists(video_path):
        return {"success": False, "error": "Uploaded video file is missing"}

    language = "pl" if str(language or "").lower() == "pl" else "en"
    language_name = "Polish" if language == "pl" else "English"

    uploaded = None
    try:
        uploaded = client.files.upload(
            file=video_path,
            config={
                "mime_type": "video/mp4",
                "display_name": os.path.basename(video_path),
            },
        )

        wait_started = time.time()
        while _resolve_file_state(uploaded) == types.FileState.PROCESSING.value:
            if (time.time() - wait_started) > timeout_seconds:
                return {"success": False, "error": "Timed out while preparing uploaded video"}
            time.sleep(max(0.1, poll_seconds))
            uploaded = client.files.get(name=uploaded.name)

        final_state = _resolve_file_state(uploaded)
        if final_state == types.FileState.FAILED.value:
            error_message = getattr(getattr(uploaded, "error", None), "message", None)
            return {"success": False, "error": error_message or "Uploaded video processing failed"}

        prompt = f"""Transcribe all spoken words from this video in {language_name}.

Return STRICT JSON only using this exact structure:
{{
  "language": "{language}",
  "segments": [
    {{"start": 0.0, "end": 3.2, "text": "spoken text"}}
  ]
}}

Rules:
- Include the full spoken transcript from start to end.
- `start` and `end` are seconds from video start (numbers, not strings).
- Keep segments in chronological order and non-overlapping.
- Keep each segment concise (roughly 2-8 seconds when possible).
- `text` must contain spoken words only, never timestamps.
- Never return values like "00:01" as segment text.
- Do not include any markdown or explanations outside JSON.
"""

        response = _generate_content_with_retry(
            client,
            model_name=model_name,
            contents=[uploaded, prompt],
            config={
                "response_mime_type": "application/json",
            },
            max_attempts=3,
            base_backoff_seconds=1.0,
        )

        response_text = _collect_response_text(response)
        payload = None
        payload_error = None
        try:
            payload = _extract_response_payload(response)
        except Exception as exc:
            payload_error = exc

        if payload is None and response_text:
            payload = {"language": language, "transcript": response_text}

        segments, detected_language = _segments_from_payload(payload, language, response_text)

        if not segments or _is_low_quality_transcript(segments):
            fallback_response = _generate_content_with_retry(
                client,
                model_name=model_name,
                contents=[uploaded, _build_plaintext_fallback_prompt(language_name)],
                config={
                    "response_mime_type": "text/plain",
                },
                max_attempts=2,
                base_backoff_seconds=1.0,
            )
            fallback_text = _collect_response_text(fallback_response)
            fallback_payload = None
            if fallback_text:
                try:
                    fallback_payload = _extract_response_payload(fallback_response)
                except Exception:
                    fallback_payload = {"language": language, "transcript": fallback_text}

            fallback_segments, fallback_language = _segments_from_payload(
                fallback_payload,
                language,
                fallback_text,
            )

            if fallback_segments and not _is_low_quality_transcript(fallback_segments):
                segments = fallback_segments
                detected_language = fallback_language

        if not segments:
            if payload_error is not None:
                raise payload_error
            return {"success": False, "error": "Failed to extract transcript segments from uploaded video"}

        if _is_low_quality_transcript(segments):
            return {"success": False, "error": "Failed to produce readable transcript from uploaded video"}

        transcript = _build_transcript_text(segments)
        return {
            "success": True,
            "transcript": transcript,
            "raw_data": segments,
            "language": detected_language,
            "is_generated": True,
            "line_count": len(segments),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    finally:
        try:
            if uploaded and getattr(uploaded, "name", None):
                client.files.delete(name=uploaded.name)
        except Exception:
            pass
