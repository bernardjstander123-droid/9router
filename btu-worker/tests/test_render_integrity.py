"""Real-media integrity gates: malformed renders must never reach queue success."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import worker


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class RenderIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clip = self.root / "shot.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=128x224:r=24:d=2",
            "-c:v", "mpeg4", str(self.clip)
        ], check=True, timeout=30)

    def test_complete_clip_decodes_and_matches(self):
        self.assertAlmostEqual(
            worker.probe(self.clip, 2, width=128, height=224, fps=24), 2, delta=0.1)

    def test_wrong_size_rejected(self):
        with self.assertRaisesRegex(worker.Blocked, "width"):
            worker.probe(self.clip, 2, width=256, height=224, fps=24)
        with self.assertRaisesRegex(worker.Blocked, "height"):
            worker.probe(self.clip, 2, width=128, height=256, fps=24)

    def test_wrong_fps_rejected(self):
        with self.assertRaisesRegex(worker.Blocked, "frame rate"):
            worker.probe(self.clip, 2, width=128, height=224, fps=30)

    def test_short_clip_rejected(self):
        with self.assertRaisesRegex(worker.Blocked, "shorter"):
            worker.probe(self.clip, 3, width=128, height=224, fps=24)

    def test_corrupt_mp4_rejected(self):
        self.clip.write_bytes(b"not an mp4")
        with self.assertRaises(worker.Blocked):
            worker.probe(self.clip, 2, width=128, height=224, fps=24)

    def test_unsafe_record_id_rejected_before_file_access(self):
        dummy = SimpleNamespace(output=self.root)
        with self.assertRaisesRegex(worker.Blocked, "record ID"):
            worker.Worker.render(dummy, {"id": "../escape"}, {})


class QueueValidationTests(unittest.TestCase):
    def test_fractional_dimensions_and_fps_rejected(self):
        payload = {"render_status": "queued", "wings": 8,
                   "prompt": "Original Demon God rises from throne",
                   "character_reference": "local://projects/character_reference.png",
                   "width": 128, "height": 224, "fps": 24, "duration_seconds": 2}
        for key, bad in (("width", 128.5), ("height", 223), ("fps", 23.976)):
            with self.subTest(key=key):
                data = dict(payload, **{key: bad})
                with self.assertRaises(worker.Blocked):
                    worker.eligible({"status": "success", "payload": data})


if __name__ == "__main__":
    unittest.main()
