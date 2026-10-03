#!/usr/bin/env python3
"""Generate a small weekly GitHub activity SVG from public events."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

EVENT_TYPES = {
    "PushEvent",
    "PullRequestEvent",
    "PullRequestReviewEvent",
    "IssuesEvent",
    "IssueCommentEvent",
    "CreateEvent",
    "ReleaseEvent",
}


def github_events(username: str) -> list[dict]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "kaimir-profile",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    events: list[dict] = []
    for page in range(1, 4):
        url = f"https://api.github.com/users/{quote(username)}/events/public?per_page=100&page={page}"
        request = Request(url, headers=headers)
        with urlopen(request, timeout=20) as response:
            batch = json.load(response)
        if not batch:
            break
        events.extend(batch)
        if len(batch) < 100:
            break
    return events


def build_svg(username: str, output: Path) -> None:
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    cutoff = datetime.combine(days[0], datetime.min.time(), tzinfo=timezone.utc)

    counts: Counter[str] = Counter()
    for event in github_events(username):
        if event.get("type") not in EVENT_TYPES:
            continue
        created = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        if created < cutoff:
            continue
        counts[created.date().isoformat()] += 1

    values = [counts[d.isoformat()] for d in days]
    total = sum(values)
    max_value = max(values, default=0)

    width, height = 900, 310
    left, top, chart_w, chart_h = 64, 92, 772, 145
    gap = 18
    bar_w = (chart_w - gap * 6) / 7

    bars: list[str] = []
    for i, (day, value) in enumerate(zip(days, values)):
        x = left + i * (bar_w + gap)
        h = 0 if max_value == 0 else value / max_value * chart_h
        y = top + chart_h - h
        label_y = top + chart_h + 28
        bars.append(
            f'<rect x="{x:.1f}" y="{top + chart_h:.1f}" width="{bar_w:.1f}" height="0" rx="6" fill="#7DD3FC">'
            f'<animate attributeName="height" from="0" to="{h:.1f}" dur="0.6s" begin="{i * 0.07:.2f}s" fill="freeze"/>'
            f'<animate attributeName="y" from="{top + chart_h:.1f}" to="{y:.1f}" dur="0.6s" begin="{i * 0.07:.2f}s" fill="freeze"/>'
            f'</rect>'
            f'<text x="{x + bar_w/2:.1f}" y="{label_y}" text-anchor="middle" class="mono muted" font-size="15">{day.strftime("%a")}</text>'
            f'<text x="{x + bar_w/2:.1f}" y="{max(82, y - 8):.1f}" text-anchor="middle" class="mono bright" font-size="14">{value}</text>'
        )

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">Weekly GitHub Activity for {escape(username)}</title>
  <desc id="desc">Public GitHub development events over the last seven days.</desc>
  <style>
    .mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace}}
    .bright{{fill:#E7EEF8}}.muted{{fill:#7E8BA0}}
  </style>
  <rect x="0" y="0" width="{width}" height="{height}" rx="18" fill="#0D1117" stroke="#263142" stroke-width="2"/>
  <text x="30" y="42" class="mono bright" font-size="22" font-weight="700">Weekly GitHub Activity</text>
  <text x="30" y="67" class="mono muted" font-size="14">$ window = last 7 days · public development events · total = {total}</text>
  <line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#344154" stroke-width="2"/>
  {''.join(bars)}
  <text x="30" y="286" class="mono muted" font-size="13">generated {generated}</text>
</svg>
'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build_svg(args.username, Path(args.output))


if __name__ == "__main__":
    main()
