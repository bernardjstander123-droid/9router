#!/usr/bin/env python3
"""RealmForge local-only video queue to a self-hosted ComfyUI API workflow.

Uses no Runway or third-party queue. Requires a real ComfyUI server and weights.
Only trusted locally exported API-format workflows may be configured.
"""

import argparse
import copy
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen
import uuid

MAX_BODY = 16_384
MAX_IMAGE = 32 * 1024 * 1024
MAX_VIDEO = 1024 * 1024 * 1024


class RenderError(Exception):
    pass


def config():
    root = Path(os.environ.get('RF_LOCAL_ROOT', str(Path(__file__).resolve().parent / 'runtime'))).resolve()
    endpoint = os.environ.get('RF_COMFY_URL', 'http://127.0.0.1:8188').rstrip('/')
    parsed = urlsplit(endpoint)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise RenderError('ComfyUI must be on loopback HTTP; use an SSH tunnel for remote GPUs')
    return {
        'root': root,
        'assets': root / 'assets',
        'output': root / 'output',
        'database': root / 'jobs.sqlite3',
        'workflow': Path(os.environ.get('RF_WORKFLOW', str(root / 'workflow_api.json'))).resolve(),
        'bindings': Path(os.environ.get('RF_BINDINGS', str(root / 'bindings.json'))).resolve(),
        'comfy': endpoint,
        'token': os.environ.get('RF_LOCAL_TOKEN', ''),
    }


def connection(c):
    db = sqlite3.connect(c['database'], timeout=10)
    db.row_factory = sqlite3.Row
    return db


def initialize(c):
    c['root'].mkdir(parents=True, exist_ok=True)
    c['output'].mkdir(parents=True, exist_ok=True)
    c['assets'].mkdir(parents=True, exist_ok=True)
    with connection(c) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, status TEXT NOT NULL,
            prompt TEXT NOT NULL, reference TEXT,
            video_path TEXT, duration REAL, width INTEGER, height INTEGER,
            error TEXT, created INTEGER NOT NULL, updated INTEGER NOT NULL)''')


def image_path(c, reference):
    if not isinstance(reference, str) or not reference or len(reference) > 256:
        raise RenderError('reference_image must be a relative local image path')
    if '\\' in reference or reference.startswith('/') or any(p in ('', '.', '..') for p in reference.split('/')):
        raise RenderError('Unsafe reference image path')
    base = c['assets'].resolve()
    path = (base / reference).resolve()
    if base not in path.parents or not path.is_file() or path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
        raise RenderError('Reference image is missing, invalid, or outside asset root')
    if path.stat().st_size > MAX_IMAGE:
        raise RenderError('Reference image exceeds 32 MiB')
    return path


def validate_submission(c, body):
    if not isinstance(body, dict) or set(body) - {'prompt', 'reference_image'}:
        raise RenderError('Only prompt and reference_image fields are accepted')
    prompt = body.get('prompt')
    if not isinstance(prompt, str) or not 5 <= len(prompt.strip()) <= 2000:
        raise RenderError('prompt must contain 5 to 2000 characters')
    reference = body.get('reference_image')
    if reference is not None:
        image_path(c, reference)
    return prompt.strip(), reference


def enqueue(c, body):
    prompt, reference = validate_submission(c, body)
    job_id = uuid.uuid4().hex
    now = int(time.time())
    with connection(c) as db:
        db.execute('INSERT INTO jobs (id,status,prompt,reference,created,updated) VALUES (?,?,?,?,?,?)',
                   (job_id, 'queued', prompt, reference, now, now))
    return job_id


def get_job(c, job_id):
    if not isinstance(job_id, str) or len(job_id) != 32 or not all(x in '0123456789abcdef' for x in job_id):
        return None
    with connection(c) as db:
        row = db.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    return dict(row) if row else None


def claim(c):
    db = connection(c)
    try:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute("SELECT * FROM jobs WHERE status = 'queued' ORDER BY created, rowid LIMIT 1").fetchone()
        if row:
            db.execute("UPDATE jobs SET status = 'running', updated = ? WHERE id = ?", (int(time.time()), row['id']))
        db.commit()
        return dict(row) if row else None
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def record_result(c, job_id, *, path=None, meta=None, error=None):
    with connection(c) as db:
        if path:
            db.execute("UPDATE jobs SET status='completed', video_path=?, duration=?, width=?, height=?, error=NULL, updated=? WHERE id=? AND status='running'",
                       (str(path), meta['duration'], meta['width'], meta['height'], int(time.time()), job_id))
        else:
            db.execute("UPDATE jobs SET status='failed', error=?, updated=? WHERE id=? AND status='running'",
                       (str(error)[:300], int(time.time()), job_id))


def read_json(url, *, body=None, timeout=30):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    headers = {'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    with urlopen(Request(url, data=data, headers=headers, method='POST' if data is not None else 'GET'), timeout=timeout) as response:
        return json.load(response)


def readiness(c):
    issues = []
    if not c['workflow'].is_file():
        issues.append('workflow_api.json not installed')
    if not c['bindings'].is_file():
        issues.append('bindings.json not installed')
    if not shutil.which('ffprobe'):
        issues.append('ffprobe not installed')
    if len(c['token']) < 24:
        issues.append('RF_LOCAL_TOKEN must have at least 24 characters')
    try:
        stats = read_json(c['comfy'] + '/system_stats', timeout=2)
        if not isinstance(stats, dict):
            raise RenderError('Invalid ComfyUI system stats')
    except (OSError, TimeoutError, ValueError, RenderError):
        issues.append('ComfyUI not reachable on loopback')
    return {'ready_for_submission': not issues, 'issues': issues,
            'note': 'Readiness does not prove model weights, GPU inference, or MP4 generation'}


def graph(c, prompt, reference_name, job_id):
    template = json.loads(c['workflow'].read_text(encoding='utf-8'))
    bindings = json.loads(c['bindings'].read_text(encoding='utf-8'))
    if not isinstance(template, dict) or not isinstance(bindings, dict):
        raise RenderError('Workflow and bindings must be JSON objects')
    result = copy.deepcopy(template)
    for key, value in (('positive_prompt', prompt), ('reference_image', reference_name), ('filename_prefix', 'realmforge_' + job_id)):
        binding = bindings.get(key)
        if binding is None:
            if key == 'positive_prompt' or (key == 'reference_image' and reference_name is not None):
                raise RenderError('Missing workflow binding: ' + key)
            continue
        if key == 'reference_image' and reference_name is None:
            raise RenderError('This workflow requires reference_image')
        if not isinstance(binding, dict) or not isinstance(binding.get('node'), str) or not isinstance(binding.get('input'), str):
            raise RenderError('Invalid workflow binding: ' + key)
        node = result.get(binding['node'])
        if not isinstance(node, dict) or not isinstance(node.get('inputs'), dict) or binding['input'] not in node['inputs']:
            raise RenderError('Missing workflow node/input for: ' + key)
        node['inputs'][binding['input']] = value
    if reference_name is not None and 'reference_image' not in bindings:
        raise RenderError('Image supplied but not bound to the workflow')
    return result


def upload_image(c, path):
    boundary = 'rf' + uuid.uuid4().hex
    filename = path.name.replace('"', '_').replace('\r', '_').replace('\n', '_')
    mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}[path.suffix.lower()]
    head = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n').encode()
    payload = head + path.read_bytes() + (f'\r\n--{boundary}--\r\n').encode()
    req = Request(c['comfy'] + '/upload/image', data=payload, method='POST',
                  headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with urlopen(req, timeout=90) as res:
        obj = json.load(res)
    name = obj.get('name')
    if not isinstance(name, str) or not name:
        raise RenderError('ComfyUI failed to accept reference image')
    return name


def video_descriptor(history):
    outputs = history.get('outputs', {})
    if not isinstance(outputs, dict):
        raise RenderError('ComfyUI history missing outputs')
    for node in outputs.values():
        if not isinstance(node, dict):
            continue
        for key in ('videos', 'gifs', 'video'):
            values = node.get(key, [])
            if isinstance(values, dict):
                values = [values]
            if not isinstance(values, list):
                continue
            for v in values:
                if not isinstance(v, dict):
                    continue
                name, sub = v.get('filename'), v.get('subfolder', '')
                if (isinstance(name, str) and name.lower().endswith('.mp4') and Path(name).name == name
                    and isinstance(sub, str) and not sub.startswith(('/', '\\'))
                    and all(p not in ('.', '..') for p in sub.replace('\\', '/').split('/'))
                    and v.get('type', 'output') == 'output'):
                    return {'filename': name, 'subfolder': sub, 'type': 'output'}
    raise RenderError('Completed ComfyUI workflow has no saved MP4')


def download_video(c, desc, destination):
    tmp = destination.with_suffix('.partial')
    total = 0
    try:
        with urlopen(c['comfy'] + '/view?' + urlencode(desc), timeout=180) as res, tmp.open('wb') as out:
            while True:
                chunk = res.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_VIDEO:
                    raise RenderError('Video exceeds 1 GiB cap')
                out.write(chunk)
        if total < 1024:
            raise RenderError('Downloaded MP4 is empty')
        tmp.replace(destination)
    finally:
        tmp.unlink(missing_ok=True)


def probe_video(path):
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                 'format=duration:stream=codec_type,width,height', '-of', 'json', str(path)],
                                capture_output=True, text=True, timeout=30, check=True)
        info = json.loads(result.stdout)
        stream = next((s for s in info.get('streams', []) if s.get('codec_type') == 'video'), None)
        duration = float(info.get('format', {}).get('duration', 0))
        if not stream or duration < .3 or not int(stream.get('width', 0)) or not int(stream.get('height', 0)):
            raise RenderError('MP4 missing valid video stream or duration')
        return {'duration': duration, 'width': int(stream['width']), 'height': int(stream['height'])}
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError, StopIteration) as ex:
        raise RenderError('FFprobe could not validate MP4') from ex


def render(c, job, *, timeout=3600):
    reference = image_path(c, job['reference']) if job['reference'] else None
    uploaded = upload_image(c, reference) if reference else None
    workflow = graph(c, job['prompt'], uploaded, job['id'])
    submission = read_json(c['comfy'] + '/prompt', body={'prompt': workflow, 'client_id': 'realmforge-' + job['id']})
    prompt_id = submission.get('prompt_id')
    if not isinstance(prompt_id, str) or not prompt_id:
        raise RenderError('ComfyUI rejected API workflow')
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        history = read_json(c['comfy'] + '/history/' + quote(prompt_id, safe=''))
        item = history.get(prompt_id)
        if item:
            status = item.get('status', {})
            if status.get('status_str') == 'error':
                raise RenderError('ComfyUI reported a generation error')
            if status.get('completed') or status.get('status_str') == 'success':
                desc = video_descriptor(item)
                destination = c['output'] / (job['id'] + '.mp4')
                download_video(c, desc, destination)
                try:
                    return destination, probe_video(destination)
                except Exception:
                    destination.unlink(missing_ok=True)
                    raise
        time.sleep(2)
    raise RenderError('ComfyUI inference timeout; inspect history before resubmitting')


def work_once(c):
    job = claim(c)
    if job is None:
        return False
    try:
        path, meta = render(c, job)
        record_result(c, job['id'], path=path, meta=meta)
        print('Verified MP4:', path, flush=True)
    except Exception as exc:
        record_result(c, job['id'], error=type(exc).__name__ + ': ' + str(exc))
        print('Render failed:', job['id'], type(exc).__name__, str(exc)[:180], file=sys.stderr, flush=True)
    return True


def make_handler(c):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, code, obj):
            data = json.dumps(obj).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def authenticated(self):
            authorization = self.headers.get('Authorization', '')
            expected = 'Bearer ' + c['token']
            return len(c['token']) >= 24 and hmac.compare_digest(authorization, expected)

        def do_GET(self):
            if self.path == '/health':
                return self.send_json(200, {'service': 'realmforge-local-video', 'status': 'online'})
            if not self.authenticated():
                return self.send_json(401, {'error': 'unauthorized'})
            if self.path == '/ready':
                return self.send_json(200, readiness(c))
            parts = self.path.split('/')
            if len(parts) in (4, 5) and parts[:3] == ['', 'v1', 'jobs']:
                row = get_job(c, parts[3])
                if not row:
                    return self.send_json(404, {'error': 'not_found'})
                if len(parts) == 4:
                    return self.send_json(200, {key: row[key] for key in ('id', 'status', 'error', 'duration', 'width', 'height', 'created', 'updated')})
                if parts[4] == 'video' and row['status'] == 'completed':
                    path = (c['output'] / (row['id'] + '.mp4')).resolve()
                    if path.parent != c['output'].resolve() or not path.is_file():
                        return self.send_json(404, {'error': 'video_missing'})
                    self.send_response(200)
                    self.send_header('Content-Type', 'video/mp4')
                    self.send_header('Content-Length', str(path.stat().st_size))
                    self.send_header('Content-Disposition', 'attachment; filename="' + row['id'] + '.mp4"')
                    self.send_header('Cache-Control', 'private, no-store')
                    self.end_headers()
                    with path.open('rb') as fp:
                        shutil.copyfileobj(fp, self.wfile, length=1024 * 1024)
                    return
            return self.send_json(404, {'error': 'not_found'})

        def do_POST(self):
            if not self.authenticated():
                return self.send_json(401, {'error': 'unauthorized'})
            if self.path != '/v1/jobs':
                return self.send_json(404, {'error': 'not_found'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length < 2 or length > MAX_BODY:
                    return self.send_json(413, {'error': 'invalid_body_size'})
                data = json.loads(self.rfile.read(length))
                job_id = enqueue(c, data)
                return self.send_json(202, {'id': job_id, 'status': 'queued', 'status_url': '/v1/jobs/' + job_id})
            except (ValueError, UnicodeError, RenderError) as ex:
                return self.send_json(400, {'error': str(ex)[:200]})

        def log_message(self, fmt, *args):
            # Avoid logging authenticated requests containing user project data.
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['serve', 'worker', 'check'])
    parser.add_argument('--port', type=int, default=5678)
    parser.add_argument('--interval', type=int, default=5)
    args = parser.parse_args()
    c = config()
    if args.mode == 'check':
        print(json.dumps(readiness(c), indent=2))
        return
    if len(c['token']) < 24:
        parser.error('RF_LOCAL_TOKEN must contain at least 24 characters')
    initialize(c)
    if args.mode == 'serve':
        print('RealmForge local video API on http://127.0.0.1:' + str(args.port), flush=True)
        ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(c)).serve_forever()
    else:
        if args.interval < 1:
            parser.error('--interval must be positive')
        print('RealmForge local video worker started; waiting for jobs', flush=True)
        while True:
            if not work_once(c):
                time.sleep(args.interval)


if __name__ == '__main__':
    main()
