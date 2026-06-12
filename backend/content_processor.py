"""
Content Maximizer - Gemini Content Processor
Uses Google Gemini API to analyze transcripts and generate content.
"""

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from jsonschema import ValidationError, validate
from schemas import CM_BLOG_SCHEMA, CM_CLIPS_SCHEMA, CM_SOCIAL_SCHEMA


DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
DEFAULT_THINKING_LEVEL = os.environ.get("GEMINI_THINKING_LEVEL", "low")


# Segment categories with duration ranges (in seconds).
SEGMENT_CATEGORIES = {
    "Micro Hooks": {"min": 15, "max": 30, "type": "shorts", "description": "Quick attention-grabbing hooks"},
    "Viral Shorts": {"min": 60, "max": 75, "type": "shorts", "description": "Short-form clips with stronger context"},
    "Extended Shorts": {"min": 110, "max": 120, "type": "shorts", "description": "Near-2-minute story clips"},
    "Golden Nuggets": {"min": 180, "max": 240, "type": "medium", "description": "3-4 minute key insights"},
    "Deep Dives": {"min": 300, "max": 359, "type": "long", "description": "5:00-5:59 minute deep analysis"},
    "Full Segments": {"min": 600, "max": 659, "type": "long", "description": "10:00-10:59 minute full segments"},
}

BASE_CLIP_BLUEPRINTS = [
    {"category": "Micro Hooks", "min": 15, "max": 30, "best_platform": "Instagram"},
    {"category": "Viral Shorts", "min": 60, "max": 75, "best_platform": "Tiktok"},
    {"category": "Extended Shorts", "min": 110, "max": 120, "best_platform": "YT Shorts"},
    {"category": "Golden Nuggets", "min": 180, "max": 240, "best_platform": "LinkedIn"},
    {"category": "Deep Dives", "min": 300, "max": 359, "best_platform": "LinkedIn"},
]

FULL_SEGMENT_BLUEPRINT = {"category": "Full Segments", "min": 600, "max": 659, "best_platform": "X/Twitter"}
CANDIDATES_PER_CATEGORY = 3

# Explicit rubric used to make clip quality scoring less opaque.
# Weights must sum to 1.0.
CLIP_QUALITY_WEIGHTS = {
    "hook_strength": 0.20,
    "standalone_clarity": 0.15,
    "insight_density": 0.15,
    "specificity_proof": 0.12,
    "emotional_pull": 0.10,
    "shareability": 0.10,
    "actionability": 0.08,
    "platform_fit": 0.10,
}

# Criteria descriptions used in prompts and backend evidence expectations.
CRITERIA_DESCRIPTIONS = {
    "hook_strength": "How strongly the opening creates curiosity/tension in the first moments",
    "standalone_clarity": "How understandable the clip is without full-video context",
    "insight_density": "How much valuable insight is delivered per second",
    "specificity_proof": "Use of specifics: numbers, examples, concrete claims",
    "emotional_pull": "Emotional resonance: pain, aspiration, surprise, controversy",
    "shareability": "Likelihood viewers want to send/repost it",
    "actionability": "Presence of clear takeaway or next action",
    "platform_fit": "Fit to the assigned platform format and audience behavior",
}

# Backend-controlled final score blend.
FINAL_VIRAL_WEIGHTS = {
    "semantic": 0.60,
    "length": 0.25,
    "technical": 0.15,
}

# Penalize near-duplicate windows across selected categories.
# Ordered from strongest to weakest overlap thresholds.
OVERLAP_PENALTIES = (
    (0.85, 2.00),
    (0.65, 1.25),
    (0.45, 0.75),
)


class GeminiContentProcessor:
    """Processes transcripts using Gemini AI to generate clips and content."""

    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """Initialize with Gemini API key and default model."""
        self.api_key = api_key
        self.default_model = model_name or DEFAULT_GEMINI_MODEL
        self.client = None

        # Unit tests can initialize the class with "test_key" and inject mocks.
        if api_key and api_key != "test_key":
            self.client = genai.Client(api_key=api_key)
        self._runtime_stats = {"gemini_retries": 0, "gemini_calls": 0}

    def _require_client(self):
        if self.client is None:
            raise RuntimeError(
                "Gemini client is not initialized. Provide a valid API key before generating content."
            )

    def _resolve_model(self, model_name: Optional[str] = None) -> str:
        return model_name or self.default_model or DEFAULT_GEMINI_MODEL

    @staticmethod
    def _is_gemini_3_model(model_name: str) -> bool:
        return str(model_name or "").startswith("gemini-3")

    def _build_generation_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        if not self._is_gemini_3_model(model_name):
            return None
        return {
            "thinking_config": {
                "thinking_level": DEFAULT_THINKING_LEVEL,
            }
        }

    def _reset_runtime_stats(self):
        self._runtime_stats = {"gemini_retries": 0, "gemini_calls": 0}

    @staticmethod
    def _validate_with_schema(payload: Any, schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        try:
            validate(instance=payload, schema=schema)
            return True, None
        except ValidationError as exc:
            return False, str(exc)

    def _generate_content_with_retry(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        max_attempts: int = 3,
        base_backoff_seconds: float = 0.7,
    ):
        self._require_client()
        last_error = None
        for attempt in range(1, max_attempts + 1):
            self._runtime_stats["gemini_calls"] += 1
            try:
                resolved_model = self._resolve_model(model_name)
                request_kwargs = {
                    "model": resolved_model,
                    "contents": prompt,
                }
                generation_config = self._build_generation_config(resolved_model)
                if generation_config is not None:
                    request_kwargs["config"] = generation_config
                return self.client.models.generate_content(**request_kwargs)
            except Exception as exc:
                last_error = exc
                if attempt >= max_attempts:
                    break
                self._runtime_stats["gemini_retries"] += 1
                time.sleep(base_backoff_seconds * (2 ** (attempt - 1)))
        raise last_error

    @staticmethod
    def _strip_markdown_json_fence(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) > 1:
                cleaned = parts[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return cleaned.strip()

    @staticmethod
    def _slice_to_first_json(text: str) -> str:
        object_idx = text.find("{")
        array_idx = text.find("[")
        starts = [idx for idx in (object_idx, array_idx) if idx >= 0]
        if not starts:
            return text
        return text[min(starts):]

    @staticmethod
    def _repair_json_text(text: str) -> str:
        """Best-effort repair for malformed model JSON."""
        repaired = []
        stack = []
        in_string = False
        escape = False

        for char in text:
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

    def _parse_json_response(self, response_text: str):
        cleaned = self._strip_markdown_json_fence(response_text or "")
        first_slice = self._slice_to_first_json(cleaned)

        candidates = []
        for candidate in (
            cleaned,
            first_slice,
            self._repair_json_text(cleaned),
            self._repair_json_text(first_slice),
        ):
            normalized = (candidate or "").strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        last_error = None
        decoder = json.JSONDecoder()
        for candidate in candidates:
            try:
                return json.loads(candidate), candidate
            except json.JSONDecodeError as exc:
                last_error = exc
                try:
                    parsed, _ = decoder.raw_decode(candidate)
                    return parsed, candidate
                except json.JSONDecodeError:
                    continue

        if last_error is not None:
            raise last_error
        raise json.JSONDecodeError("Empty response", cleaned, 0)

    def _repair_json_with_model(self, raw_text: str, model_name: Optional[str] = None):
        """Ask the model to return strictly valid JSON when first parse fails."""
        prompt = f"""You are a JSON repair assistant.
Convert the text below into valid JSON only.
Do not include markdown, commentary, or explanations.
Keep all original fields if possible.

TEXT TO REPAIR:
{raw_text[:25000]}
"""
        response = self._generate_content_with_retry(prompt, model_name=model_name)
        return self._parse_json_response(response.text or "")

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            parsed = float(value)
            if parsed != parsed:  # NaN guard
                return default
            return parsed
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_int(value: Any, default: int = 7) -> int:
        try:
            parsed = int(float(value))
        except (TypeError, ValueError):
            return default
        return max(1, min(10, parsed))

    def _extract_video_duration(self, transcript: str, segments: list) -> Optional[float]:
        max_end = 0.0
        if isinstance(segments, list):
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                start = self._to_float(segment.get("start"), 0.0)
                end = segment.get("end")
                if end is None:
                    duration = self._to_float(segment.get("duration"), 0.0)
                    end = start + duration
                end = self._to_float(end, start)
                if end > max_end:
                    max_end = end

        if max_end > 0:
            return max_end

        if not transcript:
            return None

        # Fallback for markdown transcript lines like [MM:SS] or [H:MM:SS].
        for h_str, m_str, s_str in re.findall(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]", transcript):
            if s_str:
                hours = int(h_str)
                minutes = int(m_str)
                seconds = int(s_str)
                total = hours * 3600 + minutes * 60 + seconds
            else:
                minutes = int(h_str)
                seconds = int(m_str)
                total = minutes * 60 + seconds
            if total > max_end:
                max_end = float(total)

        return max_end if max_end > 0 else None

    def _build_clip_blueprints(self, video_duration: Optional[float]) -> List[Dict[str, Any]]:
        blueprints = [dict(item) for item in BASE_CLIP_BLUEPRINTS]
        blueprints.append(dict(FULL_SEGMENT_BLUEPRINT))
        return blueprints

    @staticmethod
    def _fit_clip_to_bounds(
        start: float,
        end: float,
        min_duration: float,
        max_duration: float,
        video_duration: Optional[float],
    ) -> (float, float):
        min_duration = max(1.0, float(min_duration))
        max_duration = max(min_duration, float(max_duration))

        if video_duration is None or video_duration <= 0:
            if end <= start:
                end = start + min_duration
            duration = end - start
            if duration < min_duration:
                end = start + min_duration
            elif duration > max_duration:
                end = start + max_duration
            return round(start, 2), round(end, 2)

        total = max(1.0, float(video_duration))
        target_duration = end - start
        if target_duration <= 0:
            target_duration = min_duration
        target_duration = max(min_duration, min(max_duration, target_duration))

        if total < target_duration:
            target_duration = total

        latest_valid_start = max(0.0, total - target_duration)
        start = max(0.0, min(start, latest_valid_start))
        end = start + target_duration

        if end > total:
            end = total
            start = max(0.0, end - target_duration)

        duration = end - start
        if duration < min_duration and total >= min_duration:
            start = max(0.0, min(start, total - min_duration))
            end = start + min_duration
        elif duration < 1.0:
            start = max(0.0, total - 1.0)
            end = total

        if end - start > max_duration:
            end = start + max_duration
        if end > total:
            end = total

        if end <= start:
            end = min(total, start + 1.0)
            if end <= start:
                start = max(0.0, total - 1.0)
                end = total

        return round(start, 2), round(end, 2)

    def _normalize_platform_content(self, raw_content: Any, fallback_title: str, language: str) -> Dict[str, Any]:
        content = raw_content if isinstance(raw_content, dict) else {}
        default_desc = "Najwazniejsze wnioski z materialu." if language == "pl" else "Key takeaways from the video."
        default_cta = "Obejrzyj pelne wideo." if language == "pl" else "Watch the full video."

        yt = content.get("yt_shorts")
        if not isinstance(yt, dict):
            yt = {}
        yt.setdefault("title", fallback_title)
        yt.setdefault("description", default_desc)

        instagram = content.get("instagram")
        if not isinstance(instagram, dict):
            instagram = {}
        instagram.setdefault("caption", "")
        instagram.setdefault("hashtags", [])

        linkedin = content.get("linkedin")
        if not isinstance(linkedin, dict):
            linkedin = {}
        linkedin.setdefault("post", "")

        twitter = content.get("twitter")
        if not isinstance(twitter, dict):
            twitter = {}
        twitter.setdefault("tweet", "")

        facebook = content.get("facebook")
        if not isinstance(facebook, dict):
            facebook = {}
        facebook.setdefault("post", "")

        tiktok = content.get("tiktok")
        if not isinstance(tiktok, dict):
            tiktok = {}
        tiktok.setdefault("caption", "")
        tiktok.setdefault("hashtags", [])

        cta = content.get("cta")
        if not isinstance(cta, str):
            cta = default_cta

        return {
            "yt_shorts": yt,
            "instagram": instagram,
            "linkedin": linkedin,
            "twitter": twitter,
            "facebook": facebook,
            "tiktok": tiktok,
            "cta": cta,
        }

    @staticmethod
    def _normalize_category_name(value: Any) -> str:
        text = str(value or "").strip().lower()
        return re.sub(r"\s+", " ", text)

    def _resolve_candidate_category(
        self,
        raw_category: Any,
        blueprints: List[Dict[str, Any]],
    ) -> Optional[str]:
        normalized = self._normalize_category_name(raw_category)
        if not normalized:
            return None

        for spec in blueprints:
            if normalized == self._normalize_category_name(spec["category"]):
                return spec["category"]

        aliases = {
            "micro hook": "Micro Hooks",
            "viral short": "Viral Shorts",
            "extended short": "Extended Shorts",
            "golden nugget": "Golden Nuggets",
            "deep dive": "Deep Dives",
            "full segment": "Full Segments",
        }
        return aliases.get(normalized)

    @staticmethod
    def _length_fit_score(duration: float, min_duration: float, max_duration: float) -> int:
        """
        Scores how close the selected clip duration is to category sweet spot.
        10 = center of range, ~6 = edge of range, lower outside range.
        """
        min_duration = max(1.0, float(min_duration))
        max_duration = max(min_duration, float(max_duration))
        center = (min_duration + max_duration) / 2.0
        half_span = max((max_duration - min_duration) / 2.0, 1.0)
        distance_ratio = abs(float(duration) - center) / half_span
        score = int(round(10 - (distance_ratio * 4)))
        return max(1, min(10, score))

    @staticmethod
    def _clamp_score(value: float, min_score: float = 1.0, max_score: float = 10.0) -> float:
        return max(min_score, min(max_score, float(value)))

    def _extract_quality_scores(self, source: Dict[str, Any], fallback_score: int) -> Tuple[Dict[str, int], float]:
        raw_scores = source.get("criteria_scores")
        if not isinstance(raw_scores, dict):
            raw_scores = source.get("quality_scores")
        if not isinstance(raw_scores, dict):
            raw_scores = {}

        criteria_scores: Dict[str, int] = {}
        for key in CLIP_QUALITY_WEIGHTS.keys():
            criteria_scores[key] = self._to_int(raw_scores.get(key), fallback_score)

        weighted = 0.0
        for key, weight in CLIP_QUALITY_WEIGHTS.items():
            weighted += criteria_scores[key] * weight
        return criteria_scores, round(self._clamp_score(weighted), 2)

    @staticmethod
    def _normalize_evidence_text(value: Any, max_len: int = 260) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        if len(text) > max_len:
            return text[: max_len - 1].rstrip() + "..."
        return text

    def _extract_quality_evidence(self, source: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        raw_evidence = source.get("criteria_evidence")
        if not isinstance(raw_evidence, dict):
            raw_evidence = source.get("quality_evidence")
        if not isinstance(raw_evidence, dict):
            raw_evidence = {}

        normalized: Dict[str, Dict[str, str]] = {}
        for key in CLIP_QUALITY_WEIGHTS.keys():
            item = raw_evidence.get(key)
            evidence_text = ""
            why_text = ""
            if isinstance(item, dict):
                evidence_text = self._normalize_evidence_text(
                    item.get("transcript_evidence") or item.get("quote") or item.get("evidence")
                )
                why_text = self._normalize_evidence_text(
                    item.get("why") or item.get("reason") or item.get("rationale")
                )
            elif isinstance(item, str):
                evidence_text = self._normalize_evidence_text(item)

            normalized[key] = {
                "transcript_evidence": evidence_text,
                "why": why_text,
            }
        return normalized

    def _evidence_quality_score(
        self,
        criteria_scores: Dict[str, int],
        criteria_evidence: Dict[str, Dict[str, str]],
    ) -> float:
        total = max(1, len(CLIP_QUALITY_WEIGHTS))
        with_quote = 0
        with_reason = 0
        strong_evidence = 0
        unsupported_high_scores = 0

        for key in CLIP_QUALITY_WEIGHTS.keys():
            evidence = criteria_evidence.get(key, {})
            quote = self._normalize_evidence_text(evidence.get("transcript_evidence"))
            reason = self._normalize_evidence_text(evidence.get("why"))
            score = self._to_int(criteria_scores.get(key), 7)

            has_quote = len(quote) >= 8
            has_reason = len(reason) >= 14
            if has_quote:
                with_quote += 1
            if has_reason:
                with_reason += 1
            if has_quote and has_reason:
                strong_evidence += 1
            if score >= 8 and not has_quote:
                unsupported_high_scores += 1

        base = (
            3.0
            + (with_quote / total) * 3.0
            + (with_reason / total) * 2.0
            + (strong_evidence / total) * 2.0
        )
        penalty = min(2.5, unsupported_high_scores * 0.5)
        return round(self._clamp_score(base - penalty), 2)

    def _technical_quality_score(
        self,
        source: Dict[str, Any],
        raw_start: float,
        raw_end: float,
        start_time: float,
        end_time: float,
        max_duration: float,
    ) -> float:
        score = 10.0
        duration = max(1.0, end_time - start_time)

        # Penalize invalid timestamps from model output.
        if raw_end <= raw_start:
            score -= 2.5

        # Penalize heavy timestamp correction (low confidence candidate).
        correction = abs(raw_start - start_time) + abs(raw_end - end_time)
        correction_ratio = correction / max(duration, 1.0)
        score -= min(2.5, correction_ratio * 1.5)

        title = source.get("title")
        if not isinstance(title, str) or not title.strip():
            score -= 0.5

        content = source.get("content")
        required_platform_fields = ("yt_shorts", "instagram", "linkedin", "twitter", "facebook", "tiktok", "cta")
        if not isinstance(content, dict):
            score -= 1.75
        else:
            missing = sum(1 for field in required_platform_fields if field not in content)
            score -= min(2.0, missing * 0.25)

        # Very long clips in a short category are harder to use cleanly.
        if duration > max_duration:
            score -= 0.5

        return round(self._clamp_score(score), 2)

    @staticmethod
    def _overlap_ratio(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
        intersection = max(0.0, min(a_end, b_end) - max(a_start, b_start))
        if intersection <= 0:
            return 0.0
        shortest = max(1.0, min(a_end - a_start, b_end - b_start))
        return intersection / shortest

    def _calculate_overlap_penalty(self, candidate: Dict[str, Any], selected: List[Dict[str, Any]]) -> Tuple[float, float]:
        if not selected:
            return 0.0, 0.0

        start = float(candidate.get("start_time", 0.0))
        end = float(candidate.get("end_time", 0.0))
        max_overlap = 0.0
        for picked in selected:
            overlap = self._overlap_ratio(
                start,
                end,
                float(picked.get("start_time", 0.0)),
                float(picked.get("end_time", 0.0)),
            )
            if overlap > max_overlap:
                max_overlap = overlap

        penalty = 0.0
        for threshold, threshold_penalty in OVERLAP_PENALTIES:
            if max_overlap >= threshold:
                penalty = threshold_penalty
                break
        return penalty, round(max_overlap, 3)

    def _score_candidate(
        self,
        source: Dict[str, Any],
        blueprint: Dict[str, Any],
        video_duration: Optional[float],
    ) -> Dict[str, Any]:
        min_duration = blueprint["min"]
        max_duration = blueprint["max"]
        raw_start = self._to_float(source.get("start_time", source.get("start", 0.0)), 0.0)
        raw_end = self._to_float(
            source.get("end_time", source.get("end", raw_start + min_duration)),
            raw_start + min_duration,
        )
        start_time, end_time = self._fit_clip_to_bounds(
            raw_start,
            raw_end,
            min_duration,
            max_duration,
            video_duration,
        )
        duration = max(0.0, end_time - start_time)

        model_viral_score = self._to_int(source.get("viral_score"), 7)
        criteria_scores, semantic_score_raw = self._extract_quality_scores(
            source,
            fallback_score=model_viral_score,
        )
        criteria_evidence = self._extract_quality_evidence(source)
        evidence_quality_score = self._evidence_quality_score(criteria_scores, criteria_evidence)
        semantic_score = self._clamp_score((semantic_score_raw * 0.8) + (evidence_quality_score * 0.2))
        length_score = self._length_fit_score(duration, min_duration, max_duration)
        technical_score = self._technical_quality_score(
            source=source,
            raw_start=raw_start,
            raw_end=raw_end,
            start_time=start_time,
            end_time=end_time,
            max_duration=max_duration,
        )
        selection_score = (
            semantic_score * FINAL_VIRAL_WEIGHTS["semantic"]
            + float(length_score) * FINAL_VIRAL_WEIGHTS["length"]
            + technical_score * FINAL_VIRAL_WEIGHTS["technical"]
        )
        virality_score = self._to_int(round(selection_score), default=length_score)

        return {
            "source": source,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "model_viral_score": model_viral_score,
            "criteria_scores": criteria_scores,
            "criteria_evidence": criteria_evidence,
            "semantic_score_raw": round(semantic_score_raw, 2),
            "evidence_quality_score": evidence_quality_score,
            "semantic_score": round(float(semantic_score), 2),
            "length_score": length_score,
            "technical_score": technical_score,
            "selection_score": round(self._clamp_score(selection_score), 3),
            "virality_score": virality_score,
        }

    def _normalize_clips(
        self,
        parsed_payload: Any,
        blueprints: List[Dict[str, Any]],
        video_duration: Optional[float],
        language: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        clips = parsed_payload
        if isinstance(clips, dict):
            clips = clips.get("clips") or clips.get("items") or clips.get("data") or []
        if not isinstance(clips, list):
            clips = []

        categorized_candidates: Dict[str, List[Dict[str, Any]]] = {
            spec["category"]: [] for spec in blueprints
        }
        uncategorized_candidates: List[Dict[str, Any]] = []

        for item in clips:
            if not isinstance(item, dict):
                continue
            resolved_category = self._resolve_candidate_category(item.get("category"), blueprints)
            if resolved_category:
                categorized_candidates[resolved_category].append(item)
            else:
                uncategorized_candidates.append(item)

        normalized: List[Dict[str, Any]] = []
        intermediate_candidates: List[Dict[str, Any]] = []
        for idx, blueprint in enumerate(blueprints):
            category = blueprint["category"]
            candidates = list(categorized_candidates.get(category, []))
            if not candidates and uncategorized_candidates:
                candidates = [uncategorized_candidates.pop(0)]
            if not candidates:
                candidates = [{}]

            scored_candidates = [
                self._score_candidate(
                    source=candidate if isinstance(candidate, dict) else {},
                    blueprint=blueprint,
                    video_duration=video_duration,
                )
                for candidate in candidates
            ]
            for scored in scored_candidates:
                overlap_penalty, max_overlap_ratio = self._calculate_overlap_penalty(scored, normalized)
                adjusted_score = self._clamp_score(scored["selection_score"] - overlap_penalty)
                scored["overlap_penalty"] = overlap_penalty
                scored["max_overlap_ratio"] = max_overlap_ratio
                scored["adjusted_selection_score"] = round(adjusted_score, 3)
                scored["adjusted_virality_score"] = self._to_int(
                    round(adjusted_score),
                    default=scored["virality_score"],
                )
                source = scored.get("source") or {}
                intermediate_candidates.append(
                    {
                        "category": category,
                        "title": source.get("title") or f"{category} Candidate",
                        "start_time": scored["start_time"],
                        "end_time": scored["end_time"],
                        "model_viral_score": scored["model_viral_score"],
                        "selection_score": scored["selection_score"],
                        "adjusted_selection_score": scored["adjusted_selection_score"],
                        "overlap_penalty": scored["overlap_penalty"],
                        "max_overlap_ratio": scored["max_overlap_ratio"],
                    }
                )

            best_candidate = max(
                scored_candidates,
                key=lambda item: (
                    item["adjusted_selection_score"],
                    item["selection_score"],
                    item["length_score"],
                    item["semantic_score"],
                    item["model_viral_score"],
                ),
            )
            source = best_candidate["source"]
            title = source.get("title")
            if not isinstance(title, str) or not title.strip():
                title = f"{category} Clip {idx + 1}"

            normalized.append(
                {
                    "id": idx + 1,
                    "title": title.strip(),
                    "category": category,
                    "start_time": best_candidate["start_time"],
                    "end_time": best_candidate["end_time"],
                    "viral_score": best_candidate["adjusted_virality_score"],
                    "model_viral_score": best_candidate["model_viral_score"],
                    "criteria_scores": best_candidate["criteria_scores"],
                    "criteria_evidence": best_candidate["criteria_evidence"],
                    "semantic_score_raw": best_candidate["semantic_score_raw"],
                    "evidence_quality_score": best_candidate["evidence_quality_score"],
                    "semantic_score": best_candidate["semantic_score"],
                    "length_score": best_candidate["length_score"],
                    "technical_score": best_candidate["technical_score"],
                    "selection_score": best_candidate["selection_score"],
                    "adjusted_selection_score": best_candidate["adjusted_selection_score"],
                    "overlap_penalty": best_candidate["overlap_penalty"],
                    "max_overlap_ratio": best_candidate["max_overlap_ratio"],
                    "candidate_count": len(scored_candidates),
                    "best_platform": blueprint["best_platform"],
                    "selection_reason": source.get("selection_reason", ""),
                    "content": self._normalize_platform_content(source.get("content"), title.strip(), language),
                }
            )

        if normalized:
            ranking = sorted(
                range(len(normalized)),
                key=lambda clip_idx: (
                    normalized[clip_idx]["adjusted_selection_score"],
                    normalized[clip_idx]["viral_score"],
                    normalized[clip_idx]["length_score"],
                    normalized[clip_idx]["semantic_score"],
                    normalized[clip_idx]["model_viral_score"],
                ),
                reverse=True,
            )
            for rank, clip_idx in enumerate(ranking, start=1):
                normalized[clip_idx]["viral_rank"] = rank
                normalized[clip_idx]["is_best_clip"] = rank == 1

        return normalized, intermediate_candidates

    def analyze_transcript(
        self,
        transcript: str,
        segments: list,
        language: str = "pl",
        model_name: Optional[str] = None,
    ) -> dict:
        """Analyze transcript to find best moments for each clip category."""
        self._reset_runtime_stats()
        language = "pl" if language == "pl" else "en"
        language_name = "Polish" if language == "pl" else "English"
        video_duration = self._extract_video_duration(transcript, segments)
        clip_blueprints = self._build_clip_blueprints(video_duration)
        total_candidates = len(clip_blueprints) * CANDIDATES_PER_CATEGORY

        categories_prompt = "\n".join(
            f"{idx + 1}. {spec['category']} ({spec['min']}-{spec['max']}s) -> Best Platform: {spec['best_platform']}"
            for idx, spec in enumerate(clip_blueprints)
        )
        allowed_categories = ", ".join(spec["category"] for spec in clip_blueprints)
        duration_guard = (
            f"- All timestamps MUST stay within 0 and {int(video_duration)} seconds."
            if video_duration
            else "- Keep timestamps realistic and grounded in the transcript timeline."
        )
        criteria_rubric = "\n".join(
            f"- {key}: {description}"
            for key, description in CRITERIA_DESCRIPTIONS.items()
        )
        criteria_evidence_json = "\n".join(
            f'    "{key}": {{ "transcript_evidence": "...", "why": "..." }}'
            for key in CLIP_QUALITY_WEIGHTS.keys()
        )

        prompt = f"""Analyze this {language_name} video transcript and identify the best clip candidates for EACH category below.
The video discusses business/marketing topics.

TRANSCRIPT:
{transcript[:30000]}

CATEGORIES, DURATION CONSTRAINTS & BEST PLATFORMS:
{categories_prompt}

TASK:
Identify exactly {CANDIDATES_PER_CATEGORY} candidate clips for EACH category above ({total_candidates} clips total).
Strictly adhere to the duration ranges and assigned Best Platforms.
Candidates for the same category should be meaningfully different moments.

For EACH clip, return JSON with:
- title: Catchy title for the clip
- category: MUST be one of [{allowed_categories}]
- start_time: start in seconds
- end_time: end in seconds
- viral_score: 1-10
- criteria_scores: {{
    "hook_strength": 1-10,
    "standalone_clarity": 1-10,
    "insight_density": 1-10,
    "specificity_proof": 1-10,
    "emotional_pull": 1-10,
    "shareability": 1-10,
    "actionability": 1-10,
    "platform_fit": 1-10
}}
- criteria_evidence: {{
{criteria_evidence_json}
}}
- selection_reason: 1 short sentence explaining why this clip can perform well.
- best_platform: The platform assigned to this category above (e.g. YT Shorts, Instagram, Tiktok)
- content: {{
    "yt_shorts": {{ "title": "...", "description": "..." }},
    "instagram": {{ "caption": "...", "hashtags": [...] }},
    "linkedin": {{ "post": "..." }},
    "twitter": {{ "tweet": "..." }},
    "facebook": {{ "post": "..." }},
    "tiktok": {{ "caption": "...", "hashtags": [...] }},
    "cta": "..."
}}

IMPORTANT:
- Score using this rubric:
{criteria_rubric}
- Treat `criteria_scores` as your primary scoring mechanism; `viral_score` should be the overall summary.
- For EACH criterion in `criteria_evidence`, include:
  - `transcript_evidence`: short exact quote/snippet from transcript supporting the score.
  - `why`: one concise sentence connecting quote to the score.
- If direct transcript evidence is weak/missing for a criterion, do NOT give a high score (>7).
- You MUST generate content for ALL 6 platforms for EVERY clip.
- Use "yt_shorts" instead of "youtube" in the content object.
- Ensure the 'end_time' - 'start_time' matches the specific duration range for the category.
- Keep `viral_score` consistent with `criteria_scores` (high only if most criteria are high).
- Return EXACTLY {total_candidates} clips in a JSON array.
- Each category must appear exactly {CANDIDATES_PER_CATEGORY} times.
- {duration_guard}
- CRITICAL LANGUAGE RULE: ALL text fields MUST be written in {language_name}.
- The fields `title`, `content.yt_shorts.title`, `content.yt_shorts.description`, `content.instagram.caption`,
  `content.linkedin.post`, `content.twitter.tweet`, `content.facebook.post`, `content.tiktok.caption`, and `content.cta`
  MUST be in {language_name}.
- If {language_name} is Polish, do not output English phrasing except unavoidable product names/acronyms.

Return ONLY valid JSON array with exactly {total_candidates} items."""

        result_text = ""
        try:
            response = self._generate_content_with_retry(prompt, model_name=model_name)
            raw_response = response.text or ""
            result_text = self._strip_markdown_json_fence(raw_response)
            parsed_payload, _ = self._parse_json_response(raw_response)
            clips, intermediate_candidates = self._normalize_clips(
                parsed_payload,
                clip_blueprints,
                video_duration=video_duration,
                language=language,
            )
            schema_ok, schema_error = self._validate_with_schema(clips, CM_CLIPS_SCHEMA)
            if not schema_ok:
                return {
                    "success": False,
                    "error": f"Clip schema validation failed: {schema_error}",
                    "raw": result_text,
                    "meta": dict(self._runtime_stats),
                }
            return {
                "success": True,
                "clips": clips,
                "intermediate_candidates": intermediate_candidates,
                "meta": dict(self._runtime_stats),
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse AI response: {str(e)}",
                "raw": result_text,
                "meta": dict(self._runtime_stats),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "meta": dict(self._runtime_stats)}

    def generate_blog_post(
        self,
        transcript: str,
        language: str = "pl",
        model_name: Optional[str] = None,
    ) -> dict:
        """Generate SEO-optimized blog post from transcript."""
        self._reset_runtime_stats()
        lang_instruction = "in Polish" if language == "pl" else "in English"
        prompt = f"""Based on this video transcript, write a COMPREHENSIVE, LONG-FORM SEO Blog Post {lang_instruction}.
The post should be a deep dive into the specific topics discussed, formatted for easy reading but covering every detail.
Target length: 1500+ words.

TRANSCRIPT:
{transcript[:30000]}

Generate a LONG, detailed blog post structure:
1. SEO Title (H1 equivalent)
2. Compelling Meta Description
3. Engaging Introduction (hook the reader)
4. 5-8 Detailed Sections (H2). Each section must be substantial (300+ words each). Use markdown for headers.
5. Key Takeaways (Bullet points)
6. Comprehensive Conclusion
7. 5-8 SEO Keywords

Return ONLY valid JSON:
{{
    "title": "...",
    "meta_description": "...",
    "intro": "...",
    "sections": [
        {{"title": "...", "content": "Markdown content here..."}},
        {{"title": "...", "content": "..."}}
    ],
    "keywords": ["..."]
}}
"""
        raw_response = ""
        try:
            response = self._generate_content_with_retry(prompt, model_name=model_name)
            raw_response = response.text or ""
            blog, _ = self._parse_json_response(raw_response)
            schema_ok, schema_error = self._validate_with_schema(blog, CM_BLOG_SCHEMA)
            if not schema_ok:
                return {
                    "success": False,
                    "error": f"Blog schema validation failed: {schema_error}",
                    "meta": dict(self._runtime_stats),
                }
            return {"success": True, "blog": blog, "meta": dict(self._runtime_stats)}
        except json.JSONDecodeError as e:
            if raw_response:
                try:
                    repaired_blog, _ = self._repair_json_with_model(raw_response, model_name=model_name)
                    schema_ok, schema_error = self._validate_with_schema(repaired_blog, CM_BLOG_SCHEMA)
                    if not schema_ok:
                        return {
                            "success": False,
                            "error": f"Blog schema validation failed: {schema_error}",
                            "meta": dict(self._runtime_stats),
                        }
                    return {"success": True, "blog": repaired_blog, "meta": dict(self._runtime_stats)}
                except Exception:
                    pass
            return {
                "success": False,
                "error": f"Failed to parse AI response: {str(e)}",
                "meta": dict(self._runtime_stats),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "meta": dict(self._runtime_stats)}

    def generate_social_posts(
        self,
        transcript: str,
        language: str = "pl",
        model_name: Optional[str] = None,
    ) -> dict:
        """Generate social media posts for all platforms."""
        self._reset_runtime_stats()
        lang_instruction = "in Polish" if language == "pl" else "in English"
        prompt = f"""Based on this transcript, create social media posts {lang_instruction}.

TRANSCRIPT:
{transcript[:20000]}

Return ONLY valid JSON:
{{
    "linkedin": {{ "content": "...", "hashtags": ["..."] }},
    "twitter": {{ "tweets": [{{ "number": "1/10", "content": "..." }}] }},
    "facebook": {{ "content": "...", "hashtags": ["..."] }}
}}
"""
        try:
            response = self._generate_content_with_retry(prompt, model_name=model_name)
            posts, _ = self._parse_json_response(response.text or "")
            schema_ok, schema_error = self._validate_with_schema(posts, CM_SOCIAL_SCHEMA)
            if not schema_ok:
                return {
                    "success": False,
                    "error": f"Social schema validation failed: {schema_error}",
                    "meta": dict(self._runtime_stats),
                }
            return {"success": True, "posts": posts, "meta": dict(self._runtime_stats)}
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse AI response: {str(e)}",
                "meta": dict(self._runtime_stats),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "meta": dict(self._runtime_stats)}

    def process_full_content(
        self,
        transcript: str,
        segments: list,
        language: str = "pl",
        model_name: Optional[str] = None,
    ) -> dict:
        """
        Process transcript and generate all content types.
        Returns complete content package: clips, blog, social posts.
        """
        results = {
            "success": True,
            "clips": [],
            "blog": None,
            "social": None,
            "errors": [],
        }

        clips_result = self.analyze_transcript(transcript, segments, language=language, model_name=model_name)
        if clips_result["success"]:
            results["clips"] = clips_result["clips"]
        else:
            results["errors"].append(f"Clips: {clips_result['error']}")

        blog_result = self.generate_blog_post(transcript, language=language, model_name=model_name)
        if blog_result["success"]:
            results["blog"] = blog_result["blog"]
        else:
            results["errors"].append(f"Blog: {blog_result['error']}")

        social_result = self.generate_social_posts(transcript, language=language, model_name=model_name)
        if social_result["success"]:
            results["social"] = social_result["posts"]
        else:
            results["errors"].append(f"Social: {social_result['error']}")

        results["success"] = len(results["errors"]) == 0
        return results


def create_processor(
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> GeminiContentProcessor:
    """Factory function to create processor with API key and model."""
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("Gemini API key required. Set GEMINI_API_KEY env var or pass api_key.")
    return GeminiContentProcessor(key, model_name=model_name)
