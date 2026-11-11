import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from host_preflight import model_file_status, comfy_status, workflow_status, check


class PreflightTests(unittest.TestCase):
    def test_missing_model(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(model_file_status(Path(tmp) / 'missing.safetensors')['reason'], 'missing')

    def test_lfs_pointer_not_treated_as_weights(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / 'model.safetensors'
            p.write_bytes(b'version https://git-lfs.github.com/spec/v1\n' + b'x' * (1024 * 1024))
            self.assertFalse(model_file_status(p)['ok'])

    def test_remote_comfy_url_denied(self):
        self.assertFalse(comfy_status('http://example.org:8188')['ok'])

    def test_workflow_binding_verified_not_inference(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'workflow_api.json').write_text(json.dumps({'6': {'inputs': {'text': 'prompt'}}}))
            (root / 'bindings.json').write_text(json.dumps({'positive_prompt': {'node': '6', 'input': 'text'}}))
            self.assertTrue(workflow_status(root)['ok'])

    def test_failed_cuda_prevents_false_ready(self):
        with TemporaryDirectory() as tmp, patch('host_preflight.gpu_status', return_value={'ok': False, 'reason': 'no gpu'}), patch('host_preflight.comfy_status', return_value={'ok': True, 'reason': 'yes'}), patch('host_preflight.workflow_status', return_value={'ok': True, 'reason': 'yes'}), patch('host_preflight.model_file_status', return_value={'ok': True, 'reason': 'yes'}), patch('host_preflight.shutil.which', return_value='/usr/bin/ffprobe'):
            report = check(Path(tmp), Path(tmp), 'http://localhost:8188')
            self.assertFalse(report['preflight_passed'])
            self.assertFalse(report['inference_verified'])

if __name__ == '__main__':
    unittest.main()
