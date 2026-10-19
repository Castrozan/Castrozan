import base64
import hashlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image, ImageDraw

from encode import encode_recording
from media import decode_gif
from render import frame_timestamps
from timing import TIMING


class AnimationTests(unittest.TestCase):
    def test_static_colors_survive_animation_palette_changes(self):
        static_colors = [
            (column * 37 % 256, column * 91 % 256, column * 19 % 256)
            for column in range(64)
        ]
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            frames = []
            for index, animated_color in enumerate(
                [(255, 0, 255), (0, 0, 255), (0, 255, 255)]
            ):
                frame = Image.new("RGB", (128, 64))
                frame.putdata((static_colors + [animated_color] * 64) * 64)
                path = destination / f"frame-{index}.png"
                frame.save(path)
                frames.append((path, index * 8))
            expected = frame.crop((0, 0, 64, 64)).tobytes()
            output = destination / "recording.gif"
            encode_recording(frames, output)
            with Image.open(output) as animation:
                for number in range(animation.n_frames):
                    animation.seek(number)
                    self.assertEqual(
                        animation.convert("RGB").crop((0, 0, 64, 64)).tobytes(),
                        expected,
                    )

    def test_transparent_canvas_survives_gif_encoding_and_optimization(self):
        colors = ["red", "blue", "green"]
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            frames = []
            for index, color in enumerate(colors):
                frame = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
                ImageDraw.Draw(frame).rectangle((16, 16, 48, 48), fill=color)
                path = destination / f"frame-{index}.png"
                frame.save(path)
                frames.append((path, index * 8))
            output = destination / "recording.gif"
            encode_recording(frames, output)
            with Image.open(output) as animation:
                for index, color in enumerate(colors):
                    animation.seek(index)
                    frame = animation.convert("RGBA")
                    self.assertEqual(frame.getpixel((0, 0))[3], 0)
                    self.assertEqual(
                        frame.getpixel((32, 32)),
                        Image.new("RGB", (1, 1), color).getpixel((0, 0)) + (255,),
                    )

    def test_reverse_face_motion_continues_during_the_reading_hold(self):
        for theme in ["light", "dark"]:
            with self.subTest(theme=theme):
                path = Path(__file__).resolve().parents[1] / f"readme-flip-{theme}.gif"
                elapsed = 0
                samples = []
                with Image.open(path) as animation:
                    for frame_number in range(animation.n_frames):
                        animation.seek(frame_number)
                        duration = animation.info["duration"]
                        if 13000 <= elapsed < 22000:
                            samples.append(
                                (
                                    duration,
                                    hashlib.sha256(
                                        animation.convert("RGB").tobytes()
                                    ).digest(),
                                )
                            )
                        elapsed += duration
                self.assertGreaterEqual(len(samples), 150)
                self.assertTrue(all(duration <= 60 for duration, _ in samples))
                self.assertGreaterEqual(len({digest for _, digest in samples}), 100)

    def test_recorded_animations_keep_the_canvas_corners_transparent(self):
        for theme in ["light", "dark"]:
            with self.subTest(theme=theme):
                path = Path(__file__).resolve().parents[1] / f"readme-flip-{theme}.gif"
                with Image.open(path) as animation:
                    frame_numbers = [0, animation.n_frames // 2, animation.n_frames - 1]
                    for frame_number in frame_numbers:
                        animation.seek(frame_number)
                        frame = animation.convert("RGBA")
                        self.assertEqual(
                            frame.getpixel((frame.width - 1, frame.height - 1))[3],
                            0,
                        )
                        self.assertEqual(frame.getchannel("A").getextrema()[1], 255)
                        for background_color in [
                            (255, 0, 255, 255),
                            (0, 255, 255, 255),
                        ]:
                            background = Image.new("RGBA", frame.size, background_color)
                            background.alpha_composite(frame)
                            self.assertEqual(
                                background.getpixel(
                                    (frame.width - 1, frame.height - 1)
                                ),
                                background_color,
                            )

    def test_embedded_gif_preserves_frames_and_durations(self):
        images = [Image.new("RGB", (2, 2), color) for color in ["red", "green", "blue"]]
        source = io.BytesIO()
        images[0].save(
            source,
            format="GIF",
            save_all=True,
            append_images=images[1:],
            duration=[40, 70, 110],
            loop=0,
        )
        animation = decode_gif(source.getvalue())
        self.assertEqual(animation["duration"], 220)
        self.assertEqual(
            [frame["end"] for frame in animation["frames"]], [40, 110, 220]
        )
        for expected, frame in zip(images, animation["frames"]):
            with Image.open(
                io.BytesIO(base64.b64decode(frame["source"].split(",")[1]))
            ) as actual:
                self.assertEqual(actual.convert("RGB").tobytes(), expected.tobytes())

    def test_both_turns_animate_at_fifty_frames_per_second(self):
        for theme in ["light", "dark"]:
            with self.subTest(theme=theme):
                path = Path(__file__).resolve().parents[1] / f"readme-flip-{theme}.gif"
                self.assertLessEqual(path.stat().st_size, 100 * 1024 * 1024)
                intervals = [(11500, 12500), (22700, 23700)]
                samples = {interval: [] for interval in intervals}
                elapsed = 0
                with Image.open(path) as animation:
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
                self.assertEqual(elapsed, 24000)
                for interval, frames in samples.items():
                    with self.subTest(interval=interval):
                        self.assertEqual(len(frames), 50)
                        self.assertTrue(all(duration == 20 for duration, _ in frames))
                        self.assertGreaterEqual(
                            len({digest for _, digest in frames}), 48
                        )


class RecordingTimelineTests(unittest.TestCase):
    def test_reverse_face_keeps_animating_through_the_reading_hold(self):
        timestamps = frame_timestamps()
        reverse_start = TIMING["outgoingStart"] + TIMING["turnDuration"]
        samples = [
            timestamp
            for timestamp in timestamps
            if reverse_start <= timestamp <= TIMING["returnStart"]
        ]
        self.assertEqual(samples[0], reverse_start)
        self.assertEqual(samples[-1], TIMING["returnStart"])
        self.assertLessEqual(
            max(end - start for start, end in zip(samples, samples[1:])), 50
        )


if __name__ == "__main__":
    unittest.main()
