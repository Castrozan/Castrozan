import subprocess

from timing import TIMING


def encode_recording(frames, output):
    manifest = frames[0][0].parent / "frames.ffconcat"
    entries = ["ffconcat version 1.0"]
    for index, (path, timestamp) in enumerate(frames):
        next_timestamp = (
            frames[index + 1][1]
            if index + 1 < len(frames)
            else TIMING["duration"] / 1000
        )
        entries.extend(
            [
                f"file '{path.name}'",
                "option framerate 50",
                f"duration {max(0.001, next_timestamp - timestamp):.6f}",
            ]
        )
    entries.extend([f"file '{frames[-1][0].name}'", "option framerate 50"])
    manifest.write_text("\n".join(entries) + "\n")
    input_command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(manifest),
    ]
    subprocess.run(
        [
            *input_command,
            "-filter_complex",
            "fps=50,format=yuva444p,split[color][alpha];"
            "[color]format=yuv420p[color];[alpha]alphaextract[alpha]",
            "-map",
            "[color]",
            "-map",
            "[alpha]",
            "-c:v",
            "libaom-av1",
            "-crf",
            "38",
            "-cpu-used",
            "6",
            "-row-mt",
            "1",
            "-t",
            str(TIMING["duration"] / 1000),
            "-loop",
            "0",
            "-f",
            "avif",
            str(output),
        ],
        check=True,
    )
