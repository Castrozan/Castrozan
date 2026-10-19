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
            "fps=50,split[frames][palette_input];"
            "[palette_input]palettegen=max_colors=256:reserve_transparent=1:"
            "stats_mode=single[palette];"
            "[frames][palette]paletteuse=new=1:dither=none:alpha_threshold=128",
            "-t",
            str(TIMING["duration"] / 1000),
            "-loop",
            "0",
            str(output),
        ],
        check=True,
    )
    optimized = manifest.with_name("optimized.gif")
    subprocess.run(
        [
            "gifsicle",
            "--optimize=3",
            str(output),
            "--output",
            str(optimized),
        ],
        check=True,
    )
    if optimized.stat().st_size > 100 * 1024 * 1024:
        raise RuntimeError("The GIF exceeds GitHub's 100 MiB ordinary Git file limit")
    optimized.replace(output)
