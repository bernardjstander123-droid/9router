"""Tests use a fake ComfyUI transport and synthetic FFmpeg MP4, NOT AI inference."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import local_video as lv


class FakeComfy(BaseHTTPRequestHandler):
    mp4 = None
    def do_GET(self):
        if self.path == '/system_stats':
            data = json.dumps({'system': {'comfyui_version': 'mock'}}).encode()
        elif self.path == '/history/mock-prompt':
            data = json.dumps({'mock-prompt': {'status': {'completed': True, 'status_str': 'success'},
                'outputs': {'3': {'videos': [{'filename': 'test.mp4', 'subfolder': '', 'type': 'output'}]}}}}).encode()
        elif self.path.startswith('/view?'):
            data = self.mp4
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body_size = int(self.headers.get('Content-Length', '0'))
        self.rfile.read(body_size)
        if self.path == '/prompt':
            data = json.dumps({'prompt_id': 'mock-prompt'}).encode()
        elif self.path == '/upload/image':
            data = json.dumps({'name': 'uploaded.png'}).encode()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass


class LocalVideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.c = dict(root=self.root, assets=self.root/'assets', output=self.root/'output',
                      database=self.root/'jobs.sqlite3', workflow=self.root/'workflow.json',
                      bindings=self.root/'bindings.json', comfy='', token='secure-test-token-over-24-chars-long')
        lv.initialize(self.c)
        self.c['workflow'].write_text(json.dumps({'6': {'inputs': {'text': ''}},
                                                   '10': {'inputs': {'image': ''}},
                                                   '22': {'inputs': {'filename_prefix': ''}}}))
        self.c['bindings'].write_text(json.dumps({'positive_prompt': {'node': '6', 'input': 'text'},
                'reference_image': {'node': '10', 'input': 'image'},
                'filename_prefix': {'node': '22', 'input': 'filename_prefix'}}))
        (self.c['assets']/'character.png').write_bytes(b'fake image for mocked network transport')

    def tearDown(self):
        self.tmp.cleanup()

    def test_validation_and_containment(self):
        for reference in ['../secrets.png', '/etc/passwd', 'x\\..\\secrets.png', 'missing.png', 'a//b.png']:
            with self.assertRaises(lv.RenderError):
                lv.validate_submission(self.c, {'prompt': 'Demon God awakens', 'reference_image': reference})
        with self.assertRaises(lv.RenderError):
            lv.validate_submission(self.c, {'prompt': 'Demon God awakens', 'premium_override': True})
        self.assertEqual(lv.image_path(self.c, 'character.png').name, 'character.png')

    def test_graph_mapping(self):
        graph = lv.graph(self.c, 'Eight wings, dramatic storm', 'uploaded.png', 'a'*32)
        self.assertEqual(graph['10']['inputs']['image'], 'uploaded.png')
        self.assertEqual(graph['6']['inputs']['text'], 'Eight wings, dramatic storm')
        self.assertTrue(graph['22']['inputs']['filename_prefix'].startswith('realmforge_'))
        with self.assertRaises(lv.RenderError):
            lv.graph(self.c, 'Demon God awakens', None, 'a'*32)

    def test_no_fake_mp4_from_bad_history(self):
        with self.assertRaises(lv.RenderError):
            lv.video_descriptor({'outputs': {'0': {'images': [{'filename': 'x.png'}]}}})
        with self.assertRaises(lv.RenderError):
            lv.video_descriptor({'outputs': {'0': {'videos': [{'filename': '../x.mp4'}]}}})
        with self.assertRaises(lv.RenderError):
            lv.probe_video(self.c['output']/'missing.mp4')

    def test_queue_claim_atomic(self):
        job_id = lv.enqueue(self.c, {'prompt': 'A new original cinematic scene', 'reference_image': 'character.png'})
        first = lv.claim(self.c)
        self.assertEqual(first['id'], job_id)
        self.assertIsNone(lv.claim(self.c))
        lv.record_result(self.c, job_id, error='test failure')
        self.assertEqual(lv.get_job(self.c, job_id)['status'], 'failed')

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Requires FFmpeg binaries')
    def test_authenticated_end_to_end_mp4_transport_only(self):
        mp4 = self.root/'fixture.mp4'
        subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y',
                        '-f', 'lavfi', '-i', 'color=c=black:s=128x72:d=1:r=8',
                        '-c:v', 'mpeg4', '-pix_fmt', 'yuv420p', str(mp4)],
                       check=True, capture_output=True, timeout=30)
        FakeComfy.mp4 = mp4.read_bytes()
        comfy = ThreadingHTTPServer(('127.0.0.1', 0), FakeComfy)
        app = ThreadingHTTPServer(('127.0.0.1', 0), lv.make_handler(self.c))
        t1 = Thread(target=comfy.serve_forever, daemon=True)
        t2 = Thread(target=app.serve_forever, daemon=True)
        self.c['comfy'] = f'http://127.0.0.1:{comfy.server_port}'
        t1.start(); t2.start()
        base = f'http://127.0.0.1:{app.server_port}'
        token = {'Authorization': 'Bearer ' + self.c['token']}
        try:
            req = Request(base+'/v1/jobs', data=b'{}', headers={'Content-Type': 'application/json'}, method='POST')
            with self.assertRaises(HTTPError) as ex:
                urlopen(req, timeout=3)
            self.assertEqual(ex.exception.code, 401)
            req = Request(base+'/v1/jobs', data=json.dumps({'prompt': 'Demon God with eight wings in the clouds',
                               'reference_image': 'character.png'}).encode(),
                          headers={**token, 'Content-Type': 'application/json'}, method='POST')
            with urlopen(req, timeout=3) as res:
                self.assertEqual(res.status, 202)
                job_id = json.load(res)['id']
            self.assertTrue(lv.work_once(self.c))
            req = Request(base+'/v1/jobs/'+job_id, headers=token)
            with urlopen(req, timeout=3) as res:
                data = json.load(res)
            self.assertEqual(data['status'], 'completed')
            self.assertEqual(data['width'], 128)
            req = Request(base+'/v1/jobs/'+job_id+'/video', headers=token)
            with urlopen(req, timeout=3) as res:
                self.assertEqual(res.headers['Content-Type'], 'video/mp4')
                self.assertEqual(res.read(), FakeComfy.mp4)
        finally:
            app.shutdown(); comfy.shutdown()
            app.server_close(); comfy.server_close()
            t1.join(timeout=3); t2.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
