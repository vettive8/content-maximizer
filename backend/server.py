"""
Content Maximizer Backend - Flask API Server
Provides REST endpoints for transcript fetching and AI content processing.
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from transcript_fetcher import fetch_transcript, extract_video_id, seconds_to_timestamp
from content_processor import create_processor, SEGMENT_CATEGORIES
from website_scraper import scrape_website_text
from business_growth_strategy_processor import BusinessGrowthStrategyProcessor
from video_transcriber import (
    get_uploaded_media_path,
    is_supported_upload,
    save_uploaded_mp4,
    transcribe_uploaded_video,
)
from database import (
    save_project, get_all_projects, get_project_details, delete_project, 
    delete_all_projects, save_transcript_independently,
    get_all_scripts, save_script, update_script, delete_script, append_metric,
    InvalidIdentifierError
)
from dotenv import load_dotenv
import os
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

DEFAULT_MAX_UPLOAD_MB = 500


def _parse_positive_int(value):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def _parse_positive_float(value):
    try:
        parsed = float(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def _configured_max_content_length():
    explicit_bytes = _parse_positive_int(os.environ.get('MAX_CONTENT_LENGTH'))
    if explicit_bytes:
        return explicit_bytes

    max_upload_mb = _parse_positive_float(os.environ.get('MAX_UPLOAD_MB'))
    if max_upload_mb:
        return int(max_upload_mb * 1024 * 1024)

    return DEFAULT_MAX_UPLOAD_MB * 1024 * 1024


def _format_size_limit(byte_count):
    if not byte_count:
        return 'configured limit'

    mb = byte_count / (1024 * 1024)
    if mb >= 1:
        return f"{mb:g} MB"

    kb = byte_count / 1024
    if kb >= 1:
        return f"{kb:g} KB"

    return f"{byte_count} bytes"


app.config['MAX_CONTENT_LENGTH'] = _configured_max_content_length()


@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(_error):
    limit = app.config.get('MAX_CONTENT_LENGTH')
    return jsonify({
        'success': False,
        'error': f"Request payload too large. Maximum allowed size is {_format_size_limit(limit)}."
    }), 413

# Runtime AI configuration and processor cache.
_processor_cache = {}
_processor_lock = threading.Lock()
_runtime_ai_config = {
    'api_key': os.environ.get('GEMINI_API_KEY'),
    'model': os.environ.get('GEMINI_MODEL', 'gemini-3-flash-preview')
}

# Async clip download jobs
_clip_download_jobs = {}
_clip_download_lock = threading.Lock()
_clip_perf = {
    'source_download_avg_seconds': 45.0,
    'slice_seconds_per_second': 1.15,
    'slice_overhead_seconds': 8.0,
}
_transcript_executor = ThreadPoolExecutor(max_workers=4)


def _record_metric(record):
    try:
        append_metric(record)
    except Exception as exc:
        print(f"[METRICS] Failed to append metric: {exc}")


def _normalize_language(value, default='pl'):
    normalized = str(value or default).strip().lower()
    return normalized if normalized in ('pl', 'en') else default

def _extract_ai_config(payload=None):
    """Resolve AI config from request payload/headers with runtime fallback."""
    payload = payload or {}
    ai_config = payload.get('ai_config', {}) if isinstance(payload, dict) else {}

    header_api_key = request.headers.get('X-Gemini-Api-Key')
    header_model = request.headers.get('X-Gemini-Model')

    api_key = header_api_key or ai_config.get('api_key') or _runtime_ai_config.get('api_key')
    model_name = header_model or ai_config.get('model') or _runtime_ai_config.get('model')

    return {
        'api_key': api_key,
        'model': model_name
    }

def get_processor(api_key=None, model_name=None):
    resolved_key = api_key or _runtime_ai_config.get('api_key') or os.environ.get('GEMINI_API_KEY')
    resolved_model = model_name or _runtime_ai_config.get('model') or os.environ.get('GEMINI_MODEL', 'gemini-3-flash-preview')

    if not resolved_key:
        raise ValueError("Gemini API key not configured")

    cache_key = (resolved_key, resolved_model)
    with _processor_lock:
        if cache_key not in _processor_cache:
            _processor_cache[cache_key] = create_processor(resolved_key, model_name=resolved_model)
        return _processor_cache[cache_key]


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clip_duration_seconds(start, end):
    return max(1.0, _safe_float(end, 0.0) - _safe_float(start, 0.0))


def _estimate_clip_download_seconds(source_cached: bool, clip_cached: bool, clip_duration: float):
    if clip_cached:
        return 1, 0, 1

    source_eta = 0.0 if source_cached else float(_clip_perf.get('source_download_avg_seconds', 45.0))
    slice_factor = float(_clip_perf.get('slice_seconds_per_second', 1.15))
    slice_overhead = float(_clip_perf.get('slice_overhead_seconds', 8.0))
    slice_eta = max(3.0, clip_duration * slice_factor + slice_overhead)
    total = max(1.0, source_eta + slice_eta)
    return int(round(total)), int(round(source_eta)), int(round(slice_eta))


def _serialize_clip_job(job):
    now = time.time()
    started_at = job.get('started_at') or now
    elapsed = max(0.0, now - started_at)
    estimated = float(job.get('estimated_seconds') or 1.0)
    remaining = max(0.0, estimated - elapsed)

    # If we have a stage-specific eta from yt-dlp/ffmpeg, prefer it.
    dynamic_eta = job.get('stage_eta_seconds')
    if dynamic_eta is not None:
        if job.get('stage') == 'downloading_source':
            remaining = max(0.0, float(dynamic_eta) + float(job.get('slice_estimate_seconds') or 0.0))
        elif job.get('stage') == 'slicing_clip':
            remaining = max(0.0, float(dynamic_eta))
        else:
            remaining = max(0.0, float(dynamic_eta))

    progress = float(job.get('progress_percent') or 0.0)
    if job.get('status') in ('queued', 'running'):
        if progress <= 0:
            progress = min(95.0, (elapsed / max(estimated, 1.0)) * 100.0)
        else:
            progress = max(progress, min(95.0, (elapsed / max(estimated, 1.0)) * 100.0))
    if job.get('status') == 'completed':
        progress = 100.0

    return {
        'job_id': job['job_id'],
        'source_type': job.get('source_type', 'youtube'),
        'source_id': job.get('source_id') or job.get('video_id'),
        'status': job.get('status', 'queued'),
        'stage': job.get('stage', 'queued'),
        'message': job.get('message', ''),
        'progress_percent': round(progress, 1),
        'elapsed_seconds': round(elapsed, 1),
        'estimated_seconds': int(round(estimated)),
        'remaining_seconds': int(round(max(0.0, remaining))),
        'first_download_for_video': bool(job.get('first_download_for_video', False)),
        'source_cached': bool(job.get('source_cached', False)),
        'clip_cached': bool(job.get('clip_cached', False)),
        'error': job.get('error'),
    }


def _update_clip_perf(meta, clip_duration):
    if not isinstance(meta, dict):
        return

    source_cached = bool(meta.get('source_cached'))
    clip_cached = bool(meta.get('clip_cached'))
    source_elapsed = _safe_float(meta.get('source_elapsed_seconds'), 0.0)
    slice_elapsed = _safe_float(meta.get('slice_elapsed_seconds'), 0.0)

    # EMA update for smoother estimates.
    alpha = 0.30
    if (not source_cached) and source_elapsed > 0:
        current = float(_clip_perf.get('source_download_avg_seconds', 45.0))
        _clip_perf['source_download_avg_seconds'] = current * (1.0 - alpha) + source_elapsed * alpha

    if (not clip_cached) and slice_elapsed > 0 and clip_duration > 0:
        observed = slice_elapsed / clip_duration
        factor_current = float(_clip_perf.get('slice_seconds_per_second', 1.15))
        overhead_current = float(_clip_perf.get('slice_overhead_seconds', 8.0))
        observed_factor = max(0.05, (slice_elapsed - overhead_current) / clip_duration)
        observed_overhead = max(0.0, slice_elapsed - factor_current * clip_duration)

        _clip_perf['slice_seconds_per_second'] = factor_current * (1.0 - alpha) + observed_factor * alpha
        _clip_perf['slice_overhead_seconds'] = overhead_current * (1.0 - alpha) + observed_overhead * alpha


def _launch_clip_download_job(job_id, source_type, source_id, start, end, title):
    from download_clip import prepare_clip, prepare_upload_clip

    clip_duration = _clip_duration_seconds(start, end)

    def _run():
        with _clip_download_lock:
            job = _clip_download_jobs.get(job_id)
            if not job:
                return
            job['status'] = 'running'
            job['stage'] = 'preparing'
            job['message'] = 'Preparing download'
            job['started_at'] = time.time()

        source_cached = source_type == 'upload'

        def _progress_cb(event):
            nonlocal source_cached
            stage = event.get('stage') or 'running'
            stage_percent = event.get('percent')
            eta_seconds = event.get('eta_seconds')

            with _clip_download_lock:
                current = _clip_download_jobs.get(job_id)
                if not current:
                    return

                if stage == 'source_cached':
                    source_cached = True
                    current['source_cached'] = True
                    current['stage'] = 'slicing_clip'
                    current['message'] = 'Source already cached'
                    current['progress_percent'] = max(current.get('progress_percent', 0.0), 20.0)
                    current['stage_eta_seconds'] = 0
                    return

                if stage == 'clip_cached':
                    current['clip_cached'] = True
                    current['stage'] = 'completed'
                    current['status'] = 'completed'
                    current['message'] = 'Clip already cached'
                    current['progress_percent'] = 100.0
                    current['stage_eta_seconds'] = 0
                    return

                if stage == 'downloading_source':
                    current['stage'] = stage
                    current['message'] = 'Downloading source video'
                    if stage_percent is not None:
                        current['progress_percent'] = max(1.0, min(70.0, float(stage_percent) * 0.7))
                    if eta_seconds is not None:
                        current['stage_eta_seconds'] = max(0.0, _safe_float(eta_seconds, 0.0))
                    return

                if stage == 'slicing_clip':
                    current['stage'] = stage
                    current['message'] = 'Slicing clip'
                    base = 70.0 if not source_cached else 20.0
                    span = 28.0 if not source_cached else 78.0
                    pct = _safe_float(stage_percent, 0.0)
                    current['progress_percent'] = max(base, min(98.0, base + (pct / 100.0) * span))
                    if eta_seconds is not None:
                        current['stage_eta_seconds'] = max(0.0, _safe_float(eta_seconds, 0.0))
                    return

                current['stage'] = stage
                current['message'] = event.get('message') or current.get('message') or 'Processing'

        if source_type == 'upload':
            clip_path, error, meta = prepare_upload_clip(source_id, start, end, title, progress_callback=_progress_cb)
        else:
            clip_path, error, meta = prepare_clip(source_id, start, end, title, progress_callback=_progress_cb)
        with _clip_download_lock:
            current = _clip_download_jobs.get(job_id)
            if not current:
                return

            if error:
                current['status'] = 'error'
                current['stage'] = 'error'
                current['error'] = error
                current['message'] = error
                current['progress_percent'] = max(current.get('progress_percent', 0.0), 1.0)
                _record_metric({
                    'type': 'job',
                    'job_id': job_id,
                    'workflow': 'clip-download',
                    'status': 'error',
                    'source_type': source_type,
                    'source_id': source_id,
                    'total_seconds': round(time.time() - (current.get('started_at') or time.time()), 3),
                    'error': error,
                })
                return

            current['status'] = 'completed'
            current['stage'] = 'completed'
            current['message'] = 'Clip ready'
            current['progress_percent'] = 100.0
            current['clip_path'] = clip_path
            current['download_name'] = os.path.basename(clip_path)
            current['completed_at'] = time.time()
            if isinstance(meta, dict):
                current['source_cached'] = bool(meta.get('source_cached', current.get('source_cached')))
                current['clip_cached'] = bool(meta.get('clip_cached', False))
                _update_clip_perf(meta, clip_duration)
            _record_metric({
                'type': 'job',
                'job_id': job_id,
                'workflow': 'clip-download',
                'status': 'completed',
                'source_type': source_type,
                'source_id': source_id,
                'source_cached': bool(current.get('source_cached')),
                'clip_cached': bool(current.get('clip_cached')),
                'clip_duration_seconds': round(clip_duration, 3),
                'total_seconds': round(time.time() - (current.get('started_at') or time.time()), 3),
                'stage_seconds': {
                    'source_download': float((meta or {}).get('source_elapsed_seconds', 0.0)),
                    'slice_clip': float((meta or {}).get('slice_elapsed_seconds', 0.0)),
                },
            })

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok', 
        'message': 'Content Maximizer API is running',
        'gemini': bool(_runtime_ai_config.get('api_key') or os.environ.get('GEMINI_API_KEY'))
    })


@app.route('/api/ai/config', methods=['GET'])
def get_ai_config():
    """Return current backend AI runtime configuration (without exposing full key)."""
    api_key = _runtime_ai_config.get('api_key')
    return jsonify({
        'success': True,
        'configured': bool(api_key),
        'model': _runtime_ai_config.get('model')
    })


@app.route('/api/ai/config', methods=['POST'])
def set_ai_config():
    """Set runtime AI configuration used by backend processors."""
    global _processor_cache

    data = request.get_json() or {}
    api_key = data.get('api_key')
    model_name = data.get('model')

    if api_key is not None:
        _runtime_ai_config['api_key'] = api_key.strip() if isinstance(api_key, str) else api_key
    if model_name:
        _runtime_ai_config['model'] = model_name

    # Clear cache so subsequent calls use the new config.
    with _processor_lock:
        _processor_cache = {}

    return jsonify({
        'success': True,
        'configured': bool(_runtime_ai_config.get('api_key')),
        'model': _runtime_ai_config.get('model')
    })


@app.route('/api/transcript', methods=['POST'])
def get_transcript():
    """
    Fetch transcript from YouTube video.
    
    Request body:
        {
            "url": "https://www.youtube.com/watch?v=VIDEO_ID",
            "language": "pl"  // optional, defaults to 'pl'
        }
    """
    job_id = str(uuid.uuid4())
    job_started = time.time()
    data = request.get_json()

    if not data or 'url' not in data:
        _record_metric({
            'type': 'job',
            'job_id': job_id,
            'workflow': 'transcript-fetch',
            'status': 'error',
            'total_seconds': round(time.time() - job_started, 3),
            'error': 'Missing required field: url',
        })
        return jsonify({
            'success': False,
            'error': 'Missing required field: url'
        }), 400

    url = data['url']
    language = _normalize_language(data.get('language'))

    # Validate URL
    video_id = extract_video_id(url)
    if not video_id:
        _record_metric({
            'type': 'job',
            'job_id': job_id,
            'workflow': 'transcript-fetch',
            'status': 'error',
            'total_seconds': round(time.time() - job_started, 3),
            'error': 'Invalid YouTube URL',
        })
        return jsonify({
            'success': False,
            'error': 'Invalid YouTube URL'
        }), 400

    print(f"[TRANSCRIPT] Request received: video_id={video_id}, language={language}", flush=True)

    # Fetch transcript with timeout so frontend does not hang forever
    future = _transcript_executor.submit(fetch_transcript, url, language)
    try:
        result = future.result(timeout=45)
    except FuturesTimeoutError:
        future.cancel()
        print(f"[TRANSCRIPT] Timeout: video_id={video_id}", flush=True)
        _record_metric({
            'type': 'job',
            'job_id': job_id,
            'workflow': 'transcript-fetch',
            'status': 'error',
            'video_id': video_id,
            'language': language,
            'total_seconds': round(time.time() - job_started, 3),
            'error': 'timeout',
        })
        return jsonify({
            'success': False,
            'error': 'Przekroczono limit czasu pobierania transkryptu (45s). Sprobuj ponownie lub uzyj innego filmu.'
        }), 504
    except Exception as exc:
        print(f"[TRANSCRIPT] Internal error: {exc}", flush=True)
        _record_metric({
            'type': 'job',
            'job_id': job_id,
            'workflow': 'transcript-fetch',
            'status': 'error',
            'video_id': video_id,
            'language': language,
            'total_seconds': round(time.time() - job_started, 3),
            'error': str(exc),
        })
        return jsonify({
            'success': False,
            'error': str(exc)
        }), 500

    if result['success']:
        print(f"[TRANSCRIPT] Success: video_id={result['video_id']}, lines={result['line_count']}, lang={result['language']}", flush=True)
        response_data = {
            'success': True,
            'video_id': result['video_id'],
            'language': result['language'],
            'is_generated': result['is_generated'],
            'line_count': result['line_count'],
            'transcript': result['transcript'],
            'segments': result['raw_data']
        }
        
        # Save independent copy of transcript
        save_transcript_independently(response_data)
        _record_metric({
            'type': 'job',
            'job_id': job_id,
            'workflow': 'transcript-fetch',
            'status': 'completed',
            'video_id': result['video_id'],
            'language': result['language'],
            'line_count': result['line_count'],
            'total_seconds': round(time.time() - job_started, 3),
        })
        return jsonify(response_data)

    print(f"[TRANSCRIPT] Failed: video_id={video_id}, error={result.get('error')}", flush=True)
    _record_metric({
        'type': 'job',
        'job_id': job_id,
        'workflow': 'transcript-fetch',
        'status': 'error',
        'video_id': video_id,
        'language': language,
        'total_seconds': round(time.time() - job_started, 3),
        'error': result.get('error'),
    })
    return jsonify({
        'success': False,
        'error': result['error']
    }), 404


@app.route('/api/transcript/upload', methods=['POST'])
def upload_transcript():
    """Transcribe an uploaded MP4 video via Gemini."""
    job_id = str(uuid.uuid4())
    job_started = time.time()
    uploaded_file = request.files.get('video')
    language = _normalize_language(request.form.get('language'))

    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({
            'success': False,
            'error': 'Missing required file field: video'
        }), 400

    if not is_supported_upload(uploaded_file.filename):
        return jsonify({
            'success': False,
            'error': 'Only .mp4 files are supported'
        }), 400

    ai_config = _extract_ai_config()
    media_id = str(uuid.uuid4())
    saved_path = None
    try:
        processor = get_processor(
            api_key=ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )
        save_result = save_uploaded_mp4(uploaded_file, media_id)
        saved_path = save_result['path']

        transcript_result = transcribe_uploaded_video(
            processor.client,
            saved_path,
            language=language,
            model_name=ai_config.get('model') or _runtime_ai_config.get('model') or 'gemini-3-flash-preview'
        )
        if not transcript_result.get('success'):
            if saved_path and os.path.exists(saved_path):
                os.remove(saved_path)
            raise ValueError(transcript_result.get('error') or 'Failed to transcribe uploaded video')

        source_filename = save_result.get('filename') or f'{media_id}.mp4'
        response_data = {
            'success': True,
            'video_id': media_id,
            'source_type': 'upload',
            'source_id': media_id,
            'source_filename': source_filename,
            'title': os.path.splitext(source_filename)[0],
            'media_url': f'/api/media/{media_id}',
            'language': transcript_result.get('language', language),
            'is_generated': bool(transcript_result.get('is_generated', True)),
            'line_count': transcript_result.get('line_count', 0),
            'transcript': transcript_result.get('transcript', ''),
            'segments': transcript_result.get('raw_data', []),
        }

        save_transcript_independently(response_data)
        _record_metric({
            'type': 'job',
            'job_id': job_id,
            'workflow': 'transcript-upload',
            'status': 'completed',
            'source_type': 'upload',
            'source_id': media_id,
            'language': response_data['language'],
            'line_count': response_data['line_count'],
            'total_seconds': round(time.time() - job_started, 3),
        })
        return jsonify(response_data)
    except Exception as exc:
        error_text = str(exc)
        upper_error = error_text.upper()
        status_code = 503 if ('503' in error_text or 'UNAVAILABLE' in upper_error or 'RESOURCE_EXHAUSTED' in upper_error) else 500
        _record_metric({
            'type': 'job',
            'job_id': job_id,
            'workflow': 'transcript-upload',
            'status': 'error',
            'source_type': 'upload',
            'source_id': media_id,
            'language': language,
            'total_seconds': round(time.time() - job_started, 3),
            'error': error_text,
        })
        return jsonify({
            'success': False,
            'error': error_text
        }), status_code


@app.route('/api/media/<media_id>', methods=['GET'])
def serve_uploaded_media(media_id):
    """Serve uploaded MP4 source for local preview playback."""
    media_path = get_uploaded_media_path(media_id)
    if not media_path or not os.path.exists(media_path):
        return jsonify({'success': False, 'error': 'Media not found'}), 404

    return send_file(
        media_path,
        mimetype='video/mp4',
        conditional=True
    )


@app.route('/api/transcript/<video_id>', methods=['GET'])
def get_transcript_by_id(video_id):
    """Fetch transcript by video ID directly."""
    language = _normalize_language(request.args.get('language'))
    result = fetch_transcript(video_id, language)
    
    if result['success']:
        return jsonify({
            'success': True,
            'video_id': result['video_id'],
            'language': result['language'],
            'is_generated': result['is_generated'],
            'line_count': result['line_count'],
            'transcript': result['transcript'],
            'segments': result['raw_data']
        })
    else:
        return jsonify({
            'success': False,
            'error': result['error']
        }), 404


@app.route('/api/process', methods=['POST'])
def process_content():
    """
    Full content processing with Gemini AI.
    """
    data = request.get_json()
    job_id = str(uuid.uuid4())
    job_started = time.time()

    if not data or 'transcript' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing required field: transcript'
        }), 400

    transcript = data['transcript']
    segments = data.get('segments', [])
    language = _normalize_language(data.get('language'))
    generate = data.get('generate', ['clips', 'blog', 'social'])
    ai_config = _extract_ai_config(data)

    try:
        processor = get_processor(
            api_key=ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )

        results = {
            'success': True,
            'clips': [],
            'clip_candidates': [],
            'blog': None,
            'social': None,
            'errors': [],
            'meta': {'gemini_retries': 0, 'stage_seconds': {}}
        }

        if 'clips' in generate:
            t_stage = time.time()
            clips_result = processor.analyze_transcript(
                transcript,
                segments,
                language=language,
                model_name=ai_config.get('model')
            )
            results['meta']['stage_seconds']['clips'] = round(time.time() - t_stage, 3)
            if clips_result['success']:
                results['clips'] = clips_result['clips']
                results['clip_candidates'] = clips_result.get('intermediate_candidates', [])
                results['meta']['gemini_retries'] += int(clips_result.get('meta', {}).get('gemini_retries', 0))
            else:
                results['errors'].append(f"Clips: {clips_result['error']}")

        if 'blog' in generate:
            t_stage = time.time()
            blog_result = processor.generate_blog_post(
                transcript,
                language,
                model_name=ai_config.get('model')
            )
            results['meta']['stage_seconds']['blog'] = round(time.time() - t_stage, 3)
            if blog_result['success']:
                results['blog'] = blog_result['blog']
                results['meta']['gemini_retries'] += int(blog_result.get('meta', {}).get('gemini_retries', 0))
            else:
                results['errors'].append(f"Blog: {blog_result['error']}")

        if 'social' in generate:
            t_stage = time.time()
            social_result = processor.generate_social_posts(
                transcript,
                language,
                model_name=ai_config.get('model')
            )
            results['meta']['stage_seconds']['social'] = round(time.time() - t_stage, 3)
            if social_result['success']:
                results['social'] = social_result['posts']
                results['meta']['gemini_retries'] += int(social_result.get('meta', {}).get('gemini_retries', 0))
            else:
                results['errors'].append(f"Social: {social_result['error']}")

        if results['errors']:
            results['success'] = False

        if results['clips']:
            avg_score = sum(float(c.get('adjusted_selection_score', 0.0)) for c in results['clips']) / max(1, len(results['clips']))
            avg_overlap = sum(float(c.get('max_overlap_ratio', 0.0)) for c in results['clips']) / max(1, len(results['clips']))
        else:
            avg_score = 0.0
            avg_overlap = 0.0

        _record_metric({
            'type': 'job',
            'job_id': job_id,
            'workflow': 'content-maximizer-sync',
            'status': 'completed' if results['success'] else 'error',
            'total_seconds': round(time.time() - job_started, 3),
            'stage_seconds': results['meta']['stage_seconds'],
            'gemini_retries': results['meta']['gemini_retries'],
            'h2_clip_quality_score_avg': round(avg_score, 3),
            'h2_clip_overlap_avg': round(avg_overlap, 3),
            'error': '; '.join(results['errors']) if results['errors'] else None,
        })

        return jsonify(results)

    except Exception as e:
        _record_metric({
            'type': 'job',
            'job_id': job_id,
            'workflow': 'content-maximizer-sync',
            'status': 'error',
            'total_seconds': round(time.time() - job_started, 3),
            'error': str(e),
        })
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/process_stream', methods=['POST'])
def process_content_stream():
    """
    Streaming version of full content processing.
    Yields NDJSON events: progress, complete, error.
    """
    try:
        print(f"[STREAM] Request received")
        data = request.get_json()
        if not data or 'transcript' not in data:
             return jsonify({'success': False, 'error': 'Missing required field: transcript'}), 400

        transcript = data['transcript']
        segments = data.get('segments', [])
        language = _normalize_language(data.get('language'))
        generate_list = data.get('generate', ['clips', 'blog', 'social'])
        ai_config = _extract_ai_config(data)

        print(f"[STREAM] Processing {len(transcript)} chars, generating: {generate_list}")

        processor = get_processor(
            api_key=ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )

        from flask import Response, stream_with_context
        import json
        import time
        import datetime

        job_id = str(uuid.uuid4())

        def generate():
            start_ts = time.time()
            stage_seconds = {}
            gemini_retries = 0

            def logv(msg):
                print(f"[STREAM {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

            logv("Starting generator...")
            yield json.dumps({"type": "progress", "stage": "init", "percent": 5, "message": "Initializing AI...", "time_remaining": "~2 mins"}) + "\n"

            results = {
                'success': True,
                'clips': [],
                'clip_candidates': [],
                'blog': None,
                'social': None,
                'errors': []
            }

            if 'clips' in generate_list:
                logv("Starting CLIPS generation")
                yield json.dumps({"type": "progress", "stage": "clips", "percent": 10, "message": "Analyzing for Viral Clips...", "time_remaining": "~60s"}) + "\n"
                try:
                    t0 = time.time()
                    clips_result = processor.analyze_transcript(
                        transcript,
                        segments,
                        language=language,
                        model_name=ai_config.get('model')
                    )
                    stage_seconds['clips'] = round(time.time() - t0, 3)
                    gemini_retries += int(clips_result.get('meta', {}).get('gemini_retries', 0))
                    logv(f"Clips finished in {time.time()-t0:.2f}s. Success: {clips_result.get('success')}")

                    if clips_result['success']:
                        results['clips'] = clips_result['clips']
                        results['clip_candidates'] = clips_result.get('intermediate_candidates', [])
                    else:
                        results['errors'].append(f"Clips: {clips_result['error']}")
                except Exception as e:
                    logv(f"Clips ERROR: {e}")
                    results['errors'].append(f"Clips Exception: {str(e)}")

            if 'blog' in generate_list:
                logv("Starting BLOG generation")
                yield json.dumps({"type": "progress", "stage": "blog", "percent": 50, "message": "Writing SEO Blog Post...", "time_remaining": "~40s"}) + "\n"
                try:
                    t0 = time.time()
                    blog_result = processor.generate_blog_post(
                        transcript,
                        language,
                        model_name=ai_config.get('model')
                    )
                    stage_seconds['blog'] = round(time.time() - t0, 3)
                    gemini_retries += int(blog_result.get('meta', {}).get('gemini_retries', 0))
                    logv(f"Blog finished in {time.time()-t0:.2f}s. Success: {blog_result.get('success')}")

                    if blog_result['success']:
                        results['blog'] = blog_result['blog']
                    else:
                        results['errors'].append(f"Blog: {blog_result['error']}")
                except Exception as e:
                    logv(f"Blog ERROR: {e}")
                    results['errors'].append(f"Blog Exception: {str(e)}")

            if 'social' in generate_list:
                logv("Starting SOCIAL generation")
                yield json.dumps({"type": "progress", "stage": "social", "percent": 85, "message": "Drafting Social Posts...", "time_remaining": "~15s"}) + "\n"
                try:
                    t0 = time.time()
                    social_result = processor.generate_social_posts(
                        transcript,
                        language,
                        model_name=ai_config.get('model')
                    )
                    stage_seconds['social'] = round(time.time() - t0, 3)
                    gemini_retries += int(social_result.get('meta', {}).get('gemini_retries', 0))
                    logv(f"Social finished in {time.time()-t0:.2f}s. Success: {social_result.get('success')}")

                    if social_result['success']:
                        results['social'] = social_result['posts']
                    else:
                        results['errors'].append(f"Social: {social_result['error']}")
                except Exception as e:
                    logv(f"Social ERROR: {e}")
                    results['errors'].append(f"Social Exception: {str(e)}")

            if results['errors']:
                results['success'] = False
                logv(f"Finished with errors: {results['errors']}")
            else:
                logv("Finished SUCCESS")

            if results['clips']:
                avg_score = sum(float(c.get('adjusted_selection_score', 0.0)) for c in results['clips']) / max(1, len(results['clips']))
                avg_overlap = sum(float(c.get('max_overlap_ratio', 0.0)) for c in results['clips']) / max(1, len(results['clips']))
            else:
                avg_score = 0.0
                avg_overlap = 0.0

            total_elapsed = round(time.time() - start_ts, 3)
            _record_metric({
                'type': 'job',
                'job_id': job_id,
                'workflow': 'content-maximizer-stream',
                'status': 'completed' if results['success'] else 'error',
                'total_seconds': total_elapsed,
                'stage_seconds': stage_seconds,
                'gemini_retries': gemini_retries,
                'h2_clip_quality_score_avg': round(avg_score, 3),
                'h2_clip_overlap_avg': round(avg_overlap, 3),
                'error': '; '.join(results['errors']) if results['errors'] else None,
            })

            yield json.dumps({"type": "complete", "result": results}) + "\n"
            logv(f"Total time: {time.time()-start_ts:.2f}s")

        return Response(stream_with_context(generate()), mimetype='application/x-ndjson')

    except Exception as e:
        print(f"[PROCESSOR] Error: {e}")
        _record_metric({
            'type': 'job',
            'job_id': str(uuid.uuid4()),
            'workflow': 'content-maximizer-stream',
            'status': 'error',
            'error': str(e),
        })
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clips', methods=['POST'])
def generate_clips():
    """Generate viral clips using Gemini AI."""
    data = request.get_json()
    
    if not data or 'transcript' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing required field: transcript'
        }), 400
    
    try:
        ai_config = _extract_ai_config(data)
        processor = get_processor(
            api_key=ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )
        result = processor.analyze_transcript(
            data['transcript'], 
            data.get('segments', []),
            language=_normalize_language(data.get('language')),
            model_name=ai_config.get('model')
        )
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/blog', methods=['POST'])
def generate_blog():
    """Generate SEO blog post using Gemini AI."""
    data = request.get_json()
    
    if not data or 'transcript' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing required field: transcript'
        }), 400
    
    try:
        ai_config = _extract_ai_config(data)
        processor = get_processor(
            api_key=ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )
        result = processor.generate_blog_post(
            data['transcript'],
            _normalize_language(data.get('language')),
            model_name=ai_config.get('model')
        )
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/social', methods=['POST'])
def generate_social():
    """Generate social media posts using Gemini AI."""
    data = request.get_json()
    
    if not data or 'transcript' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing required field: transcript'
        }), 400
    
    try:
        ai_config = _extract_ai_config(data)
        processor = get_processor(
            api_key=ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )
        result = processor.generate_social_posts(
            data['transcript'],
            _normalize_language(data.get('language')),
            model_name=ai_config.get('model')
        )
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Return available clip categories and their durations."""
    return jsonify({
        'success': True,
        'categories': SEGMENT_CATEGORIES
    })


@app.route('/api/download_clip', methods=['GET'])
def download_clip_endpoint():
    """
    Download a specific clip from a YouTube or uploaded source.
    
    Query params:
        source_type: youtube|upload (optional, default youtube)
        source_id/video_id: source identifier
        start: Start time in seconds
        end: End time in seconds
        title: Clip title for filename
    """
    source_type = str(request.args.get('source_type') or 'youtube').strip().lower()
    source_id = str(request.args.get('source_id') or request.args.get('video_id') or '').strip()
    start = request.args.get('start')
    end = request.args.get('end')
    title = request.args.get('title', 'clip')
    
    if not all([source_id, start, end]):
        return jsonify({'error': 'Missing required parameters'}), 400
    if source_type not in ('youtube', 'upload'):
        return jsonify({'error': 'Invalid source_type'}), 400
        
    try:
        start = float(start)
        end = float(end)
        if source_type == 'upload':
            from download_clip import prepare_upload_clip
            clip_path, error, _ = prepare_upload_clip(source_id, start, end, title, progress_callback=None)
        else:
            from download_clip import get_clip_path
            clip_path, error = get_clip_path(source_id, start, end, title)

        if error:
            return jsonify({'error': error}), 500

        return send_file(
            clip_path,
            as_attachment=True,
            download_name=os.path.basename(clip_path)
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download_clip/start', methods=['POST'])
def download_clip_start():
    """Start async clip download job and return job metadata."""
    data = request.get_json() or {}
    source_type = str(data.get('source_type') or 'youtube').strip().lower()
    source_id = str(data.get('source_id') or data.get('video_id') or '').strip()
    title = str(data.get('title') or 'clip')
    start = data.get('start')
    end = data.get('end')

    if not all([source_id, start is not None, end is not None]):
        return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
    if source_type not in ('youtube', 'upload'):
        return jsonify({'success': False, 'error': 'Invalid source_type'}), 400

    start = _safe_float(start, 0.0)
    end = _safe_float(end, 0.0)
    if end <= start:
        return jsonify({'success': False, 'error': 'Invalid clip range'}), 400

    if source_type == 'upload':
        from download_clip import get_upload_source_video_path, get_upload_clip_output_path
        source_path = get_upload_source_video_path(source_id)
        if not source_path:
            return jsonify({'success': False, 'error': 'Uploaded source video not found'}), 404
        clip_path = get_upload_clip_output_path(source_id, start, end, title)
        source_cached = True
    else:
        from download_clip import get_source_video_path, get_clip_output_path
        clip_path = get_clip_output_path(source_id, start, end, title)
        source_cached = bool(get_source_video_path(source_id))

    clip_cached = os.path.exists(clip_path)
    clip_duration = _clip_duration_seconds(start, end)
    estimated, source_eta, slice_eta = _estimate_clip_download_seconds(source_cached, clip_cached, clip_duration)

    job_id = str(uuid.uuid4())
    now = time.time()
    with _clip_download_lock:
        _clip_download_jobs[job_id] = {
            'job_id': job_id,
            'source_type': source_type,
            'source_id': source_id,
            'video_id': source_id,
            'title': title,
            'start': start,
            'end': end,
            'status': 'queued',
            'stage': 'queued',
            'message': 'Queued',
            'progress_percent': 1.0,
            'stage_eta_seconds': None,
            'created_at': now,
            'started_at': now,
            'estimated_seconds': estimated,
            'source_estimate_seconds': source_eta,
            'slice_estimate_seconds': slice_eta,
            'source_cached': source_cached,
            'clip_cached': clip_cached,
            'first_download_for_video': source_type == 'youtube' and (not source_cached),
            'clip_path': clip_path if clip_cached else None,
            'download_name': os.path.basename(clip_path),
            'error': None,
        }

    if clip_cached:
        with _clip_download_lock:
            _clip_download_jobs[job_id]['status'] = 'completed'
            _clip_download_jobs[job_id]['stage'] = 'completed'
            _clip_download_jobs[job_id]['message'] = 'Clip ready'
            _clip_download_jobs[job_id]['progress_percent'] = 100.0
            _clip_download_jobs[job_id]['completed_at'] = time.time()
    else:
        _launch_clip_download_job(job_id, source_type, source_id, start, end, title)

    with _clip_download_lock:
        payload = _serialize_clip_job(_clip_download_jobs[job_id])

    return jsonify({
        'success': True,
        **payload
    })


@app.route('/api/download_clip/status/<job_id>', methods=['GET'])
def download_clip_status(job_id):
    with _clip_download_lock:
        job = _clip_download_jobs.get(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        payload = _serialize_clip_job(job)

    return jsonify({
        'success': True,
        **payload
    })


@app.route('/api/download_clip/file/<job_id>', methods=['GET'])
def download_clip_file(job_id):
    with _clip_download_lock:
        job = _clip_download_jobs.get(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        if job.get('status') != 'completed':
            return jsonify({'success': False, 'error': 'Clip is not ready yet'}), 409
        clip_path = job.get('clip_path')
        download_name = job.get('download_name') or os.path.basename(clip_path or '')

    if not clip_path or not os.path.exists(clip_path):
        return jsonify({'success': False, 'error': 'Clip file missing'}), 404

    return send_file(
        clip_path,
        as_attachment=True,
        download_name=download_name
    )



@app.route('/api/save_project', methods=['POST'])
def api_save_project():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        result = save_project(data)
        return jsonify({'success': True, 'project_id': result['id']})
    except InvalidIdentifierError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/list_projects', methods=['GET'])
def list_projects_route():
    try:
        projects = get_all_projects()
        return jsonify({
            'success': True,
            'projects': projects
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_project/<project_id>', methods=['GET'])
def get_project_route(project_id):
    try:
        project = get_project_details(project_id)
        if project:
            return jsonify({'success': True, 'data': project})
        return jsonify({'success': False, 'error': 'Project not found'}), 404
    except InvalidIdentifierError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete_project', methods=['POST'])
def delete_project_route():
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        
        if not project_id:
            return jsonify({'success': False, 'error': 'Missing project_id'}), 400
            
        if delete_project(project_id):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
    except InvalidIdentifierError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete_all_projects', methods=['POST'])
def delete_all_projects_route():
    try:
        if delete_all_projects():
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete projects'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate_business_growth_strategy', methods=['POST'])
@app.route('/api/generate_game_plan', methods=['POST'])  # Legacy alias
def generate_business_growth_strategy():
    """
    Orchestrates the Business Growth Strategy creation with 3 sections:
    1. Market Research (uses all data sources)
    2. Psychoanalysis (focuses on sales transcripts)
    3. Creative Brief (combines everything + 30 video ideas)
    """
    job_id = str(uuid.uuid4())
    job_started = time.time()
    try:
        # Get form data and files
        manual_context = request.form.get('context', '')
        website_url = request.form.get('website', '')
        language = _normalize_language(request.form.get('language'))
        uploaded_files = request.files.getlist('transcripts')
        ai_config = _extract_ai_config()
        
        print(f"[BUSINESS GROWTH STRATEGY] Starting generation...")
        print(f"[BUSINESS GROWTH STRATEGY] Website: {website_url}")
        print(f"[BUSINESS GROWTH STRATEGY] Transcripts: {len(uploaded_files)} files")
        print(f"[BUSINESS GROWTH STRATEGY] Language: {language}")
        
        # Prepare data containers
        uploaded_files_data = []
        for file in uploaded_files:
             # Read file content into memory immediately to avoid context issues, 
             # but we will process/decode them inside the stream to report progress if needed.
             # Actually, simpler to read text here, it's fast. 
             # But if website scraping hangs, we want to yield first.
             # So we will pass the raw URL to the generator and let it scrape.
             try:
                 file_content = file.read().decode('utf-8', errors='ignore')
                 uploaded_files_data.append(f"\n--- {file.filename} ---\n{file_content}\n")
             except Exception as e:
                 print(f"[BUSINESS GROWTH STRATEGY] Error reading file {file.filename}: {e}")

        # Stream the response using NDJSON
        from flask import Response, stream_with_context
        
        def generate():
            stage_started = {'init': time.time()}
            stage_seconds = {}
            gemini_retries = 0
            errors = []
            # Initial Yield to establish connection
            yield json.dumps({"type": "progress", "stage": "init", "percent": 1, "message": "Starting job...", "time_remaining": "Calculating..."}) + "\n"
            
            # 1. Scrape Website (Inside stream)
            website_content = ""
            if website_url:
                stage_started['scraping'] = time.time()
                yield json.dumps({"type": "progress", "stage": "scraping", "percent": 5, "message": f"Scraping {website_url}...", "time_remaining": "~3 mins"}) + "\n"
                try:
                    website_content = scrape_website_text(website_url)
                    stage_seconds['scraping'] = round(time.time() - stage_started['scraping'], 3)
                    yield json.dumps({"type": "progress", "stage": "scraping_done", "percent": 10, "message": f"Scraped {len(website_content)} chars", "time_remaining": "~3 mins"}) + "\n"
                except Exception as e:
                    print(f"[BUSINESS GROWTH STRATEGY] Scraping error: {e}")
                    errors.append(str(e))
                    # Non-fatal, continue

            # 2. Process Transcripts
            sales_transcripts = "".join(uploaded_files_data)
            
            # Initialize Processor
            try:
                processor = BusinessGrowthStrategyProcessor(
                    ai_config.get('api_key'),
                    model_name=ai_config.get('model')
                )
                
                for event in processor.run_full_pipeline_stream(
                    manual_context=manual_context,
                    website_content=website_content,
                    sales_transcripts=sales_transcripts,
                    language=language
                ):
                    try:
                        parsed = json.loads(event)
                        if parsed.get('type') == 'progress':
                            stage = str(parsed.get('stage') or '')
                            if stage and stage not in stage_started:
                                stage_started[stage] = time.time()
                        elif parsed.get('type') == 'complete':
                            m = parsed.get('metrics') or {}
                            gemini_retries = int(m.get('gemini_retries', gemini_retries))
                        elif parsed.get('type') == 'error':
                            errors.append(str(parsed.get('message') or 'unknown'))
                    except Exception:
                        pass
                    yield event
                for stage, started in stage_started.items():
                    if stage not in stage_seconds:
                        stage_seconds[stage] = round(max(0.0, time.time() - started), 3)
                _record_metric({
                    'type': 'job',
                    'job_id': job_id,
                    'workflow': 'business-growth-strategy-stream',
                    'status': 'completed' if not errors else 'error',
                    'total_seconds': round(time.time() - job_started, 3),
                    'stage_seconds': stage_seconds,
                    'gemini_retries': gemini_retries,
                    'error': '; '.join(errors) if errors else None,
                    'input_transcript_files': len(uploaded_files),
                    'input_website_provided': bool(website_url),
                })
            except Exception as e:
                print(f"[BUSINESS GROWTH STRATEGY] Processor error: {e}")
                _record_metric({
                    'type': 'job',
                    'job_id': job_id,
                    'workflow': 'business-growth-strategy-stream',
                    'status': 'error',
                    'total_seconds': round(time.time() - job_started, 3),
                    'error': str(e),
                    'input_transcript_files': len(uploaded_files),
                    'input_website_provided': bool(website_url),
                })
                yield json.dumps({"type": "error", "message": str(e)}) + "\n"

        return Response(stream_with_context(generate()), mimetype='application/x-ndjson')

    except Exception as e:
        print(f"[BUSINESS GROWTH STRATEGY] Error: {e}")
        _record_metric({
            'type': 'job',
            'job_id': job_id,
            'workflow': 'business-growth-strategy-stream',
            'status': 'error',
            'total_seconds': round(time.time() - job_started, 3),
            'error': str(e),
        })
        return jsonify({'success': False, 'error': str(e)}), 500


# =========================================================================
# CONTENT IDEAS ENDPOINTS (Tab 4)
# =========================================================================

@app.route('/api/bgs/generate_titles', methods=['POST'])
@app.route('/api/gp/generate_titles', methods=['POST'])  # Legacy alias
def generate_content_titles():
    """Generate 5 video titles based on Business Growth Strategy context."""
    try:
        data = request.get_json()
        context_data = data.get('context', {})
        language = _normalize_language(data.get('language'))
        ai_config = _extract_ai_config(data)
        
        processor = BusinessGrowthStrategyProcessor(
            ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )
        
        result = processor.generate_video_titles(context_data, language)
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f"[CONTENT IDEAS] Error generating titles: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bgs/generate_similar_title', methods=['POST'])
@app.route('/api/gp/generate_similar_title', methods=['POST'])  # Legacy alias
def generate_similar_title():
    """Generate a variation of an existing title."""
    try:
        data = request.get_json()
        original_title = data.get('original_title', '')
        context_data = data.get('context', {})
        language = _normalize_language(data.get('language'))
        ai_config = _extract_ai_config(data)
        
        processor = BusinessGrowthStrategyProcessor(
            ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )
        
        result = processor.generate_similar_title(original_title, context_data, language, count=1)
        # Return first item for backwards compatibility
        return jsonify({'success': True, 'data': result[0] if result else {}})
        
    except Exception as e:
        print(f"[CONTENT IDEAS] Error generating similar title: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bgs/generate_similar_titles', methods=['POST'])
@app.route('/api/gp/generate_similar_titles', methods=['POST'])  # Legacy alias
def generate_similar_titles():
    """Generate multiple variations of an existing title."""
    try:
        data = request.get_json()
        original_title = data.get('original_title', '')
        context_data = data.get('context', {})
        language = _normalize_language(data.get('language'))
        count = data.get('count', 4)
        ai_config = _extract_ai_config(data)
        
        processor = BusinessGrowthStrategyProcessor(
            ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )
        
        result = processor.generate_similar_title(original_title, context_data, language, count=count)
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f"[CONTENT IDEAS] Error generating similar titles: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bgs/generate_chapters', methods=['POST'])
@app.route('/api/gp/generate_chapters', methods=['POST'])  # Legacy alias
def generate_chapter_structure():
    """Generate chapter structure for a video title."""
    try:
        data = request.get_json()
        title = data.get('title', '')
        context_data = data.get('context', {})
        language = _normalize_language(data.get('language'))
        ai_config = _extract_ai_config(data)
        
        processor = BusinessGrowthStrategyProcessor(
            ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )
        
        result = processor.generate_chapter_structure(title, context_data, language)
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f"[CONTENT IDEAS] Error generating chapters: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bgs/generate_script', methods=['POST'])
@app.route('/api/gp/generate_script', methods=['POST'])  # Legacy alias
def generate_chapter_script():
    """Generate script for a single chapter with Option A/B."""
    try:
        data = request.get_json()
        title = data.get('title', '')
        chapter = data.get('chapter', {})
        context_data = data.get('context', {})
        language = _normalize_language(data.get('language'))
        previous_chapter_script = data.get('previous_chapter_script', None)
        ai_config = _extract_ai_config(data)
        
        processor = BusinessGrowthStrategyProcessor(
            ai_config.get('api_key'),
            model_name=ai_config.get('model')
        )
        
        result = processor.generate_script_chapter(title, chapter, context_data, language, previous_chapter_script)
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f"[CONTENT IDEAS] Error generating script: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scripts/list', methods=['GET'])
def list_scripts():
    """List all scripts in Script Management."""
    try:
        scripts = get_all_scripts()
        return jsonify({'success': True, 'data': scripts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scripts/save', methods=['POST'])
def api_save_script():
    """Save a script to Script Management."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        script = save_script(data)
        return jsonify({'success': True, 'data': script})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scripts/<script_id>', methods=['PUT'])
def api_update_script(script_id):
    """Update an existing script."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        success = update_script(script_id, data)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scripts/<script_id>', methods=['DELETE'])
def api_delete_script(script_id):
    """Delete a script from Script Management."""
    try:
        success = delete_script(script_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Content Maximizer API on port {port}...")
    print(f"Gemini API: {'Configured' if os.environ.get('GEMINI_API_KEY') else 'NOT CONFIGURED'}")
    print(f"Max request size: {_format_size_limit(app.config.get('MAX_CONTENT_LENGTH'))}")
    print(f"Endpoints:")
    print(f"  GET  /api/health     - Health check")
    print(f"  POST /api/transcript - Fetch YouTube transcript")
    print(f"  POST /api/transcript/upload - Transcribe uploaded MP4")
    print(f"  POST /api/process    - Full AI content processing")
    print(f"  POST /api/clips      - Generate viral clips")
    print(f"  POST /api/blog       - Generate SEO blog post")
    print(f"  POST /api/social     - Generate social posts")
    print(f"  GET  /api/categories - List clip categories")
    print(f"  POST /api/bgs/generate_titles  - Content Ideas: Generate 5 titles")
    print(f"  POST /api/bgs/generate_chapters - Content Ideas: Generate chapters")
    print(f"  POST /api/bgs/generate_script   - Content Ideas: Generate script")
    app.run(host='0.0.0.0', port=port, debug=True)





