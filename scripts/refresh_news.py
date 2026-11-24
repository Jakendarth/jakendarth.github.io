#!/usr/bin/env python3
"""Refresh a small daily reading list from public maritime publisher RSS feeds."""

from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "index.html"
FEEDS = (
    ("Smart Maritime Network", "https://smartmaritimenetwork.com/feed/", "smartmaritimenetwork.com", False),
    ("Offshore Energy", "https://www.offshore-energy.biz/feed/", "offshore-energy.biz", True),
)
THEMES = (
    ("Autonomy", re.compile(r"autonom|uncrewed|unmanned|self.driving|remote.control|collision.avoidance|navigation", re.I)),
    ("Maritime AI", re.compile(r"\bAI\b|artificial intelligence|machine learning|digital twin|sensor|monitoring", re.I)),
    ("Clean propulsion", re.compile(r"methanol|hydrogen|ammonia|battery|electric|decarbon|emission|fuel cell|propulsion", re.I)),
    ("Safety", re.compile(r"safety|cyber|accident|collision|incident|fault|risk", re.I)),
)
MARITIME_CONTEXT = re.compile(r"ship|vessel|maritim|marine|ferry|tanker|port|csov|usv|seafar", re.I)
EXCLUDE = re.compile(r"\bnaval\b|\bnavy\b|military|defen[cs]e|weapon|warship", re.I)


def replace_between(page, start, end, content):
    if page.count(start) != 1 or page.count(end) != 1:
        raise ValueError(f"Expected one {start} / {end} marker pair")
    prefix, rest = page.split(start, 1)
    _, suffix = rest.split(end, 1)
    return prefix + start + content + end + suffix


def feed_items(source, feed_url, host, needs_context, now):
    request = Request(feed_url, headers={"User-Agent": "nikos-kougiatsos-website/1.0"})
    with urlopen(request, timeout=15) as response:
        root = ElementTree.parse(response).getroot()
    items = []
    for entry in root.findall(".//item"):
        title = (entry.findtext("title") or "").strip()
        url = (entry.findtext("link") or "").strip()
        published_text = entry.findtext("pubDate")
        if not title or not published_text or EXCLUDE.search(title):
            continue
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {host, "www." + host}:
            continue
        if needs_context and not MARITIME_CONTEXT.search(title):
            continue
        theme = next((label for label, pattern in THEMES if pattern.search(title)), None)
        if not theme:
            continue
        try:
            published = parsedate_to_datetime(published_text).astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        if not now - timedelta(days=14) <= published <= now + timedelta(minutes=5):
            continue
        items.append({"title": title, "url": url, "source": source, "theme": theme, "published": published})
    return items


def select_items(items):
    selected, seen, sources, themes = [], set(), Counter(), Counter()
    recent = sorted(items, key=lambda row: row["published"], reverse=True)
    for diverse_only in (True, False):
        for item in recent:
            key = item["title"].casefold()
            if key in seen or sources[item["source"]] >= 2 or (diverse_only and themes[item["theme"]]):
                continue
            selected.append(item)
            seen.add(key)
            sources[item["source"]] += 1
            themes[item["theme"]] += 1
            if len(selected) == 3:
                return sorted(selected, key=lambda row: row["published"], reverse=True)
    return sorted(selected, key=lambda row: row["published"], reverse=True)


def render(items):
    rows = []
    for item in items:
        date = item["published"]
        rows.append(
            '\n          <a class="reading-item" href="{url}" target="_blank" rel="noopener noreferrer">'
            '<span class="reading-topic">{theme}</span><span class="reading-copy"><strong>{title}</strong>'
            '<small>{source} · <time datetime="{iso}">{date}</time></small></span>'
            '<span class="reading-arrow" aria-hidden="true">↗</span></a>'.format(
                url=escape(item["url"], quote=True), theme=escape(item["theme"]),
                title=escape(item["title"]), source=escape(item["source"]),
                iso=date.date().isoformat(), date=date.strftime("%d %b %Y")))
    return "".join(rows) + "\n          "


def main():
    now = datetime.now(timezone.utc)
    found, errors = [], []
    for source, url, host, needs_context in FEEDS:
        try:
            found.extend(feed_items(source, url, host, needs_context, now))
        except (OSError, ElementTree.ParseError) as error:
            errors.append(f"{source}: {error}")
    selected = select_items(found)
    if not selected:
        print("No current matching news; keeping existing reading list. " + "; ".join(errors), file=sys.stderr)
        return 0
    page = PAGE.read_text()
    page = replace_between(page, "<!-- reading:generated:start -->", "<!-- reading:generated:end -->", render(selected))
    checked = f'Checked <time datetime="{now.date().isoformat()}">{now.strftime("%d %b %Y")}</time>'
    page = replace_between(page, "<!-- reading:checked:start -->", "<!-- reading:checked:end -->", checked)
    PAGE.write_text(page)
    print(f"Refreshed {len(selected)} suggested articles" + (f"; unavailable feeds: {', '.join(errors)}" if errors else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
