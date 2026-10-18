import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from render import read_recording


class AnimationTests(unittest.TestCase):
    def test_recording_frames_use_opaque_rgb(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.gif"
            image = Image.new("P", (2, 2), 1)
            image.putpalette([0, 255, 0, 13, 17, 23] + [0] * 762)
            image.save(source, transparency=0, duration=50, optimize=False)
            frames = read_recording(source, root)
            with Image.open(frames[0][0]) as frame:
                self.assertEqual(frame.mode, "RGB")
                self.assertNotIn("transparency", frame.info)

    def test_both_turns_animate_at_fifty_frames_per_second(self):
        intervals = [(9500, 10500), (18700, 19700)]
        samples = {interval: [] for interval in intervals}
        elapsed = 0
        with Image.open(Path(__file__).with_name("readme-flip.gif")) as animation:
            for frame_number in range(animation.n_frames):
                animation.seek(frame_number)
                duration = animation.info["duration"]
                for interval, frames in samples.items():
                    if interval[0] <= elapsed < interval[1]:
                        digest = hashlib.sha256(
                            animation.convert("RGB").tobytes()
                        ).digest()
                        frames.append((duration, digest))
                elapsed += duration
        self.assertEqual(elapsed, 20000)
        for interval, frames in samples.items():
            with self.subTest(interval=interval):
                self.assertEqual(len(frames), 50)
                self.assertTrue(all(duration == 20 for duration, _ in frames))
                self.assertGreaterEqual(len({digest for _, digest in frames}), 48)


if __name__ == "__main__":
    unittest.main()
