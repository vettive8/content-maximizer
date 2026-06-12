import json
import os
import re
import uuid
import tempfile
import threading
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'projects.json')
TRANSCRIPTS_INDEX = os.path.join(os.path.dirname(__file__), 'data', 'transcripts.json')
TRANSCRIPTS_DIR = os.path.join(os.path.dirname(__file__), 'data', 'transcripts')

SCRIPTS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'scripts.json')
METRICS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'metrics.json')
_DATA_LOCK = threading.RLock()
SCRIPT_STATUS_TRANSITIONS = {
    'written': {'written', 'scheduled', 'published'},
    'scheduled': {'written', 'scheduled', 'published'},
    'published': {'published'},
}
STORAGE_ID_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')


class InvalidIdentifierError(ValueError):
    """Raised when an identifier is unsafe for filesystem-backed storage."""


def _validate_storage_id(value, field_name='id'):
    if not isinstance(value, str) or not STORAGE_ID_PATTERN.fullmatch(value):
        raise InvalidIdentifierError(f'Invalid {field_name}')
    return value


def _project_file_path(project_id):
    safe_project_id = _validate_storage_id(project_id, 'project_id')
    data_dir = os.path.abspath(os.path.dirname(DATA_FILE))
    project_file = os.path.abspath(os.path.join(data_dir, f"{safe_project_id}.json"))

    if os.path.commonpath([data_dir, project_file]) != data_dir:
        raise InvalidIdentifierError('Invalid project_id')

    return project_file


def _count_chapter_edits(before_chapters, after_chapters):
    """Return how many chapter entries changed between two chapter arrays."""
    before = before_chapters if isinstance(before_chapters, list) else []
    after = after_chapters if isinstance(after_chapters, list) else []
    max_len = max(len(before), len(after))
    edits = 0
    for idx in range(max_len):
        b = before[idx] if idx < len(before) else None
        a = after[idx] if idx < len(after) else None
        if b is None or a is None:
            edits += 1
            continue
        b_title = str((b or {}).get('title', '')).strip() if isinstance(b, dict) else str(b)
        a_title = str((a or {}).get('title', '')).strip() if isinstance(a, dict) else str(a)
        b_script = str((b or {}).get('script', '')).strip() if isinstance(b, dict) else ''
        a_script = str((a or {}).get('script', '')).strip() if isinstance(a, dict) else ''
        if (b_title != a_title) or (b_script != a_script):
            edits += 1
    return edits


def _atomic_write_json(path, data, indent=2):
    """Write JSON atomically to avoid partial/corrupted files."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(prefix='tmp_', suffix='.json', dir=os.path.dirname(path))
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _read_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception:
        return default


def normalize_project_title(raw_title, project_type=None):
    title = str(raw_title or '').strip()
    if not title:
        return title

    replacements = (
        ('MT - ', 'CM - '),
        ('SWB - ', 'BGS - '),
        ('GM - ', 'BGS - '),
        ('Game Plan - ', 'BGS - '),
        ('Strategia Wzrostu Biznesu - ', 'BGS - '),
        ('Content Maximizer - ', 'CM - '),
        ('Maksymalizator Tresci - ', 'CM - '),
        ('Maksymalizator Tre\u015bci - ', 'CM - '),
    )
    for old, new in replacements:
        if title.lower().startswith(old.lower()):
            title = f"{new}{title[len(old):]}"
            break

    title = title.replace('Game Plan', 'Business Growth Strategy')
    title = title.replace('Strategia Wzrostu Biznesu', 'Business Growth Strategy')
    title = title.replace('Maksymalizator Tresci', 'Content Maximizer')
    title = title.replace('Maksymalizator Tre\u015bci', 'Content Maximizer')

    normalized_type = str(project_type or '').strip().lower()
    if normalized_type in ('business-growth-strategy', 'game-plan') and not title.lower().startswith('bgs - '):
        title = f'BGS - {title}'
    if normalized_type == 'content-maximizer' and not title.lower().startswith('cm - '):
        title = f'CM - {title}'

    return title

def ensure_data_dir():
    with _DATA_LOCK:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

        if not os.path.exists(DATA_FILE):
            _atomic_write_json(DATA_FILE, [], indent=2)

        if not os.path.exists(TRANSCRIPTS_INDEX):
            _atomic_write_json(TRANSCRIPTS_INDEX, [], indent=2)

        if not os.path.exists(SCRIPTS_FILE):
            _atomic_write_json(SCRIPTS_FILE, [], indent=2)
        if not os.path.exists(METRICS_FILE):
            _atomic_write_json(METRICS_FILE, [], indent=2)

def append_metric(record):
    """Append a single telemetry record to metrics.json."""
    with _DATA_LOCK:
        ensure_data_dir()
        metrics = _read_json(METRICS_FILE, [])
        metric = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            **(record or {}),
        }
        metrics.append(metric)
        _atomic_write_json(METRICS_FILE, metrics, indent=2)
        return metric

def get_metrics():
    with _DATA_LOCK:
        ensure_data_dir()
        return _read_json(METRICS_FILE, [])

def get_all_projects():
    with _DATA_LOCK:
        ensure_data_dir()
        return _read_json(DATA_FILE, [])

def get_all_scripts():
    with _DATA_LOCK:
        ensure_data_dir()
        return _read_json(SCRIPTS_FILE, [])

def save_script(data):
    with _DATA_LOCK:
        ensure_data_dir()
        scripts = _read_json(SCRIPTS_FILE, [])

        script = {
            'id': str(uuid.uuid4()),
            'created_at': datetime.now().isoformat(),
            'project_id': data.get('project_id'),
            'title': data.get('title', 'Untitled Script'),
            'status': data.get('status', 'written'),
            'scheduled_date': data.get('scheduled_date'),
            'chapters': data.get('chapters', [])
        }

        scripts.insert(0, script)
        _atomic_write_json(SCRIPTS_FILE, scripts, indent=2)
        append_metric({
            'type': 'event',
            'event_name': 'script_created',
            'script_id': script['id'],
            'project_id': script.get('project_id'),
            'status': script.get('status'),
            'chapter_count': len(script.get('chapters', [])),
        })
        return script

def update_script(script_id, update_data):
    with _DATA_LOCK:
        ensure_data_dir()
        scripts = _read_json(SCRIPTS_FILE, [])

        found = False
        for script in scripts:
            if script['id'] == script_id:
                if 'status' in update_data:
                    current_status = str(script.get('status') or 'written')
                    next_status = str(update_data['status'] or current_status)
                    allowed = SCRIPT_STATUS_TRANSITIONS.get(current_status, {current_status})
                    if next_status not in allowed:
                        append_metric({
                            'type': 'event',
                            'event_name': 'script_status_transition',
                            'script_id': script_id,
                            'from_status': current_status,
                            'to_status': next_status,
                            'valid': False,
                        })
                        return False
                    script['status'] = next_status
                    append_metric({
                        'type': 'event',
                        'event_name': 'script_status_transition',
                        'script_id': script_id,
                        'from_status': current_status,
                        'to_status': next_status,
                        'valid': True,
                    })
                if 'scheduled_date' in update_data:
                    script['scheduled_date'] = update_data['scheduled_date']
                if 'chapters' in update_data:
                    previous_chapters = list(script.get('chapters') or [])
                    next_chapters = update_data['chapters'] if isinstance(update_data.get('chapters'), list) else []
                    edit_count = _count_chapter_edits(previous_chapters, next_chapters)
                    script['chapters'] = next_chapters
                    append_metric({
                        'type': 'event',
                        'event_name': 'script_chapters_updated',
                        'script_id': script_id,
                        'chapter_count': len(script.get('chapters', [])),
                    })
                    append_metric({
                        'type': 'event',
                        'event_name': 'post_generation_edit_count',
                        'script_id': script_id,
                        'project_id': script.get('project_id'),
                        'edit_count': int(edit_count),
                        'chapter_count_before': len(previous_chapters),
                        'chapter_count_after': len(next_chapters),
                    })
                if 'title' in update_data:
                    script['title'] = update_data['title']
                found = True
                break

        if found:
            _atomic_write_json(SCRIPTS_FILE, scripts, indent=2)
            return True
        return False

def delete_script(script_id):
    with _DATA_LOCK:
        ensure_data_dir()
        scripts = _read_json(SCRIPTS_FILE, [])

        initial_len = len(scripts)
        scripts = [s for s in scripts if s['id'] != script_id]

        if len(scripts) < initial_len:
            _atomic_write_json(SCRIPTS_FILE, scripts, indent=2)
            return True
        return False

def save_project(data):
    with _DATA_LOCK:
        ensure_data_dir()
        projects = _read_json(DATA_FILE, [])
        data = dict(data or {})
        data['title'] = normalize_project_title(data.get('title', 'Unknown Video'), data.get('type'))

        now = datetime.now().isoformat()
        requested_id = data.get('id')
        has_requested_id = 'id' in data and requested_id is not None
        project_id = _validate_storage_id(requested_id, 'project_id') if has_requested_id else str(uuid.uuid4())
        data['id'] = project_id
        project_file = _project_file_path(project_id)

        # Persist the full blob in a dedicated file.
        _atomic_write_json(project_file, data, indent=2)

        # Preserve original created_at when updating.
        existing_meta = next((p for p in projects if p.get('id') == project_id), None)
        created_at = existing_meta.get('created_at') if existing_meta else now

        meta = {
            'id': project_id,
            'created_at': created_at,
            'updated_at': now,
            'video_id': data.get('video_id'),
            'title': data.get('title', 'Unknown Video'),
            'type': data.get('type')
        }

        # Replace existing metadata or prepend new one.
        projects = [p for p in projects if p.get('id') != project_id]
        projects.insert(0, meta)
        _atomic_write_json(DATA_FILE, projects, indent=2)
        return meta

def get_project_details(project_id):
    with _DATA_LOCK:
        ensure_data_dir()
        project_file = _project_file_path(project_id)
        if os.path.exists(project_file):
            return _read_json(project_file, None)
        return None

def delete_project(project_id):
    with _DATA_LOCK:
        ensure_data_dir()
        safe_project_id = _validate_storage_id(project_id, 'project_id')
        projects = _read_json(DATA_FILE, [])
        new_projects = [p for p in projects if p['id'] != safe_project_id]
        _atomic_write_json(DATA_FILE, new_projects, indent=2)

        project_file = _project_file_path(safe_project_id)
        if os.path.exists(project_file):
            os.remove(project_file)
            return True
        return False

def delete_all_projects():
    with _DATA_LOCK:
        ensure_data_dir()
        projects = _read_json(DATA_FILE, [])
        for p in projects:
            try:
                project_file = _project_file_path(p['id'])
            except InvalidIdentifierError:
                continue
            if os.path.exists(project_file):
                os.remove(project_file)

        _atomic_write_json(DATA_FILE, [], indent=2)
        return True

def save_transcript_independently(data):
    """Save transcript to a separate persistent store."""
    with _DATA_LOCK:
        ensure_data_dir()

        video_id = data.get('video_id')
        if not video_id:
            return False

        try:
            transcripts = _read_json(TRANSCRIPTS_INDEX, [])
            exists = any(t['video_id'] == video_id for t in transcripts)

            if not exists:
                meta = {
                    'video_id': video_id,
                    'saved_at': datetime.now().isoformat(),
                    'line_count': data.get('line_count', 0),
                    'language': data.get('language', 'en')
                }
                transcripts.insert(0, meta)
                _atomic_write_json(TRANSCRIPTS_INDEX, transcripts, indent=2)

            file_path = os.path.join(TRANSCRIPTS_DIR, f"{video_id}.json")
            _atomic_write_json(file_path, data, indent=2)
            return True
        except Exception as e:
            print(f"Error saving transcript: {e}")
            return False
