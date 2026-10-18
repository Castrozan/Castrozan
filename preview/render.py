from timing import TIMING


def frame_timestamps():
    outgoing_end = TIMING["outgoingStart"] + TIMING["turnDuration"]
    return [
        *range(0, TIMING["outgoingStart"], 50),
        *range(TIMING["outgoingStart"], outgoing_end, 20),
        outgoing_end,
        *range(TIMING["returnStart"], TIMING["duration"], 20),
    ]


def render_frames(chrome, destination, width, height):
    frames = []
    timestamps = frame_timestamps()
    for frame_number, milliseconds in enumerate(timestamps):
        chrome.evaluate(
            f"(async () => {{ await window.profileReadmeMedia.seek({milliseconds}); "
            f"window.profileReadmeCard.animation.currentTime = {milliseconds}; }})()"
        )
        path = destination / f"frame-{frame_number:05d}.png"
        chrome.screenshot(path, width, height)
        frames.append((path, milliseconds / 1000))
        if frame_number % 50 == 0:
            print(f"Rendered {frame_number + 1}/{len(timestamps)} frames", flush=True)
    return frames
