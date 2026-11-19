import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import queue_manifest as queue


def sample():
    return {"project": "Demon God Awakening", "width": 640, "height": 360,
            "fps": 24, "protagonist_wings": 8,
            "original_character_reference": "local://projects/character_reference.png",
            "estimated_duration_seconds": 3,
            "shots": [{"id": 1, "file": "renders/shot_01.mp4",
                       "prompt": "An ash storm over the ancient citadel", "duration_seconds": 3}]}


class QueueManifestTests(unittest.TestCase):
    def test_offline_plan_matches_worker_contract(self):
        jobs = queue.make_jobs(sample())
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["wings"], 8)
        self.assertEqual(jobs[0]["scene_id"], "shot_01")
        self.assertEqual(jobs[0]["render_status"], "queued")
        self.assertEqual(jobs[0]["character_reference"], sample()["original_character_reference"])
        self.assertEqual(jobs[0]["duration_seconds"], 3)

    def test_rejects_continuity_and_duration_mismatch(self):
        for mutation in [lambda m: m.update(protagonist_wings=6),
                         lambda m: m.update(estimated_duration_seconds=4),
                         lambda m: m["shots"][0].update(character_reference="local://wrong.png"),
                         lambda m: m["shots"][0].update(file="../secret.mp4"),
                         lambda m: m["shots"][0].update(duration_seconds=31)]:
            m = sample()
            mutation(m)
            with self.subTest(m=m), self.assertRaises(ValueError):
                queue.make_jobs(m)

    def test_original_reference_contained(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "projects").mkdir()
            path = root / "projects" / "character_reference.png"
            path.write_bytes(b"placeholder")
            self.assertEqual(queue.safe_reference(root, "local://projects/character_reference.png"), path)
            for uri in ["local://../secret.png", "local:///etc/passwd", "local://projects/../secret.png", "https://example.com/a.png"]:
                with self.subTest(uri=uri), self.assertRaises((ValueError, FileNotFoundError)):
                    queue.safe_reference(root, uri)

    def test_submission_is_idempotent_with_receipt(self):
        class Response:
            status = 202
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"data":{"id":"record-123"}}'
        with tempfile.TemporaryDirectory() as td:
            receipt = Path(td) / "receipts.json"
            jobs = queue.make_jobs(sample())
            with patch.object(queue.urllib.request, "urlopen", return_value=Response()) as send:
                queue.submit_jobs(jobs, api=queue.DEFAULT_API, token="tm_test_fake", receipt_file=receipt)
                queue.submit_jobs(jobs, api=queue.DEFAULT_API, token="tm_test_fake", receipt_file=receipt)
                send.assert_called_once()
            self.assertEqual(json.loads(receipt.read_text())["shot_01"]["record_id"], "record-123")
            altered = [dict(jobs[0], prompt="changed prompt")]
            with self.assertRaises(ValueError):
                queue.submit_jobs(altered, api=queue.DEFAULT_API, token="tm_test_fake", receipt_file=receipt)

    def test_refuses_production_token_and_other_endpoint(self):
        jobs = queue.make_jobs(sample())
        with tempfile.TemporaryDirectory() as td:
            receipt = Path(td) / "receipts.json"
            with self.assertRaises(ValueError):
                queue.submit_jobs(jobs, api=queue.DEFAULT_API, token="tm_live_secret", receipt_file=receipt)
            with self.assertRaises(ValueError):
                queue.submit_jobs(jobs, api="https://example.com", token="tm_test_fake", receipt_file=receipt)


if __name__ == "__main__":
    unittest.main()
