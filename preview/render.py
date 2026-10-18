import base64
import json

from PIL import Image


def read_recording(source, destination):
    frames = []
    elapsed = 0.0
    with Image.open(source) as recording:
        for frame_number in range(recording.n_frames):
            recording.seek(frame_number)
            path = destination / f"source-{frame_number:05d}.png"
            frame = recording.convert("RGB")
            frame.info.clear()
            frame.save(path, compress_level=1)
            if elapsed <= 12 < elapsed + recording.info["duration"] / 1000:
                frame.save(destination / "back.png")
            frames.append((path, elapsed))
            elapsed += recording.info["duration"] / 1000
    return frames


def image_source(path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def render_turns(chrome, frames, destination, width, height):
    turn_intervals = [(9.2, 10.8), (18.4, 20.0)]
    reverse_source = image_source(destination / "back.png")
    rendered_frames = [
        frame
        for frame in frames
        if not any(start <= frame[1] < end for start, end in turn_intervals)
    ]
    for turn_number, (start, end) in enumerate(turn_intervals):
        front_path = (
            max(
                (frame for frame in frames if frame[1] < start),
                key=lambda frame: frame[1],
            )[0]
            if turn_number == 0
            else frames[0][0]
        )
        sources = json.dumps([image_source(front_path), reverse_source])
        chrome.evaluate(f"window.profileReadmeCard.showRecordedFaces(...{sources})")
        for frame_number in range(round((end - start) * 50)):
            timestamp = start + frame_number / 50
            chrome.evaluate(
                f"window.profileReadmeCard.animation.currentTime = {timestamp * 1000}"
            )
            path = destination / f"turn-{turn_number}-{frame_number:03d}.png"
            chrome.screenshot(path, width, height)
            rendered_frames.append((path, timestamp))
        print(f"Rendered turn {turn_number + 1}: 80 frames at 50 fps", flush=True)
    return sorted(rendered_frames, key=lambda frame: frame[1])
