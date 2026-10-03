#!/usr/bin/env python3
"""Generate a terminal-style weekly GitHub activity SVG from public events."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

DEVELOPMENT_EVENTS = {
    "PushEvent",
    "PullRequestEvent",
    "PullRequestReviewEvent",
    "IssuesEvent",
    "IssueCommentEvent",
    "CreateEvent",
    "ReleaseEvent",
}


def github_get(url: str, token: str | None) -> list[dict]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "kaimir-profile-readme",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def fetch_recent_events(username: str, token: str | None) -> list[dict]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    events: list[dict] = []

    for page in range(1, 4):
        query = urllib.parse.urlencode({"per_page": 100, "page": page})
        url = f"https://api.github.com/users/{urllib.parse.quote(username)}/events/public?{query}"
        batch = github_get(url, token)
        if not batch:
            break
        events.extend(batch)
        oldest = min(datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")) for item in batch)
        if oldest < cutoff:
            break

    return [
        event
        for event in events
        if event.get("type") in DEVELOPMENT_EVENTS
        and datetime.fromisoformat(event["created_at"].replace("Z", "+00:00")) >= cutoff
    ]


def render_svg(username: str, counts: Counter[str], output: Path) -> None:
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    values = [counts[d.isoformat()] for d in days]
    max_value = max(values) if values else 0

    width, height = 900, 320
    chart_left, chart_top = 80, 92
    chart_w, chart_h = 760, 150
    gap = 20
    bar_w = (chart_w - gap * 6) / 7

    bars: list[str] = []
    for idx, (day, value) in enumerate(zip(days, values)):
        x = chart_left + idx * (bar_w + gap)
        bar_h = 0 if max_value == 0 else (value / max_value) * chart_h
        y = chart_top + chart_h - bar_h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="5" fill="#7dd3fc">'
            f'<animate attributeName="height" from="0" to="{bar_h:.1f}" dur="0.7s" begin="{0.15 + idx*0.08:.2f}s" fill="freeze"/>'
            f'<animate attributeName="y" from="{chart_top + chart_h:.1f}" to="{y:.1f}" dur="0.7s" begin="{0.15 + idx*0.08:.2f}s" fill="freeze"/>'
            f'</rect>'
            f'<text x="{x + bar_w/2:.1f}" y="{chart_top + chart_h + 28}" text-anchor="middle" class="mono muted" font-size="16">{day.strftime("%a")}</text>'
            f'<text x="{x + bar_w/2:.1f}" y="{max(82, y - 8):.1f}" text-anchor="middle" class="mono bright" font-size="15">{value}</text>'
        )

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = sum(values)
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">Weekly GitHub Activity for {escape(username)}</title>
  <desc id="desc">Public GitHub development events over the last seven days.</desc>
  <style>
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
    .bright {{ fill: #e7eef8; }}
    .muted {{ fill: #7e8ba0; }}
    .accent {{ fill: #7dd3fc; }}
  </style>
  <rect x="0" y="0" width="{width}" height="{height}" rx="18" fill="#0d1117" stroke="#263142" stroke-width="2"/>
  <text x="30" y="44" class="mono bright" font-size="22" font-weight="700">Weekly GitHub Activity</text>
  <text x="30" y="69" class="mono muted" font-size="14">$ window = last 7 days · public development events · total = {total}</text>
  <line x1="{chart_left}" y1="{chart_top + chart_h}" x2="{chart_left + chart_w}" y2="{chart_top + chart_h}" stroke="#344154" stroke-width="2"/>
  {''.join(bars)}
  <text x="30" y="292" class="mono muted" font-size="13">generated {generated}</text>
</svg>
'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    token = __import__("os").environ.get("GITHUB_TOKEN")
    events = fetch_recent_events(args.username, token)
    counts: Counter[str] = Counter()
    for event in events:
        date = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00")).date().isoformat()
        counts[date] += 1

    render_svg(args.username, counts, Path(args.output))
    print(f"Generated {args.output} from {len(events)} public development events.")


if __name__ == "__main__":
    main()
