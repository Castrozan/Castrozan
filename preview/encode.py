import subprocess


def encode_recording(frames, output):
    manifest = frames[0][0].parent / "frames.ffconcat"
    entries = ["ffconcat version 1.0"]
    for index, (path, timestamp) in enumerate(frames):
        next_timestamp = frames[index + 1][1] if index + 1 < len(frames) else 20.0
        entries.extend(
            [
                f"file '{path.name}'",
                f"duration {max(0.01, next_timestamp - timestamp):.6f}",
            ]
        )
    entries.append(f"file '{frames[-1][0].name}'")
    manifest.write_text("\n".join(entries) + "\n")
    subprocess.run(
        [
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
            "-filter_complex",
            "fps=20,split[frames][palette_input];[palette_input]palettegen=stats_mode=diff[palette];"
            "[frames][palette]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
            "-t",
            "20",
            "-loop",
            "0",
            str(output),
        ],
        check=True,
    )
    if output.stat().st_size > 8 * 1024 * 1024:
        raise RuntimeError("The GIF exceeds the 8 MiB preview budget")
