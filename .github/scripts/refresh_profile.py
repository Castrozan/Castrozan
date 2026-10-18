import argparse
from html import escape
import json
from pathlib import Path
import re
from urllib.request import urlopen
from xml.etree import ElementTree


def language_chart(statistics):
    chart = re.search(r"```text\n(.*?)\n```", statistics, re.DOTALL)
    if chart is None:
        raise ValueError("Language statistics contain no text chart")
    if chart[1] == "No commit activity found in the given period.":
        return chart[1]
    rows = []
    for line in chart[1].splitlines():
        match = re.fullmatch(r"(.+?)\s+[▓░]+\s+(\d+(?:\.\d+)?)\s*%", line)
        if match is None or not 0 <= float(match[2]) <= 100:
            raise ValueError(f"Invalid language statistic: {line}")
        name, percentage = match[1], float(match[2])
        filled = round(percentage * 17 / 100)
        rows.append(
            f"{name:<10} {'▓' * filled}{'░' * (17 - filled)} {percentage:5.2f} %"
        )
    if not rows:
        raise ValueError("Language statistics are empty")
    return escape("\n".join(rows))


def contribution_table(repositories):
    rows = ["| Project | PR | Description |", "| --- | --- | --- |"]
    for repository in repositories:
        for index, pull_request in enumerate(repository["prs"]):
            project = (
                f"[{repository['repo']}]({repository['repo_url']})"
                if index == 0
                else ""
            )
            title = escape(pull_request["title"]).replace("|", r"\|")
            title = " ".join(title.splitlines())
            rows.append(
                f"| {project} | [#{pull_request['number']}]({pull_request['url']}) | {title} |"
            )
    return "\n".join(rows)


def update_front(markdown, statistics, repositories):
    chart = language_chart(statistics)
    updated, count = re.subn(
        r"<pre>.*?</pre>",
        lambda _: f"<pre>{chart}</pre>",
        markdown,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Native Markdown has no language block")
    start = "<!-- OSS_CONTRIBUTIONS:START -->"
    end = "<!-- OSS_CONTRIBUTIONS:END -->"
    before, remainder = updated.split(start, 1)
    _, after = remainder.split(end, 1)
    return f"{before}{start}\n\n{contribution_table(repositories)}\n\n{end}{after}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("statistics", type=Path)
    parser.add_argument("contributions", type=Path)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    front = root / "preview/scene/front.md"
    updated = update_front(
        front.read_text(),
        arguments.statistics.read_text(),
        json.loads(arguments.contributions.read_text()),
    )
    calendars = {}
    for theme, name in [("light", "gitlab-snk-light.svg"), ("dark", "gitlab-snk.svg")]:
        with urlopen(
            f"https://raw.githubusercontent.com/Castrozan/private-gitlab-heatmap-exporter/master/{name}",
            timeout=30,
        ) as response:
            calendar = response.read()
        if ElementTree.fromstring(calendar).tag != "{http://www.w3.org/2000/svg}svg":
            raise ValueError(f"Invalid {theme} calendar SVG")
        calendars[theme] = calendar
    front.write_text(updated)
    for theme, calendar in calendars.items():
        (root / f"preview/scene/assets/gitlab-calendar-{theme}.svg").write_bytes(
            calendar
        )


if __name__ == "__main__":
    main()
