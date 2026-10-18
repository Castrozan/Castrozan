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
        "warning",
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
            "[palette_input]palettegen=max_colors=64:stats_mode=diff,setpts=0[palette];"
            "[frames][palette]paletteuse=dither=none:diff_mode=rectangle",
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
    if optimized.stat().st_size > 10_000_000:
        raise RuntimeError("The GIF exceeds the 10 MB inline image budget")
    optimized.replace(output)
