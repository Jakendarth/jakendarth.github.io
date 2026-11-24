#!/usr/bin/env python3
"""Package the static homepage for GitHub Pages."""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def redirect_page(anchor):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="0;url=/{anchor}"><link rel="canonical" href="https://jakendarth.github.io/{anchor}"><title>Nikos Kougiatsos</title></head><body><p>Continue to <a href="/{anchor}">the homepage</a>.</p></body></html>
'''


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets/css").mkdir(parents=True)
    (DIST / "assets/img").mkdir(parents=True)
    for source, destination in (
        ("index.html", "index.html"),
        ("assets/css/renewed.css", "assets/css/renewed.css"),
        ("assets/img/tu-delft-portrait.jpg", "assets/img/tu-delft-portrait.jpg"),
        ("assets/img/guidance-framework-figure.png", "assets/img/guidance-framework-figure.png"),
        ("assets/img/mission-framework-figure.png", "assets/img/mission-framework-figure.png"),
        ("assets/img/nk-ship-mark.svg", "assets/img/nk-ship-mark.svg"),
        ("assets/img/icons8-water-transportation-80.png", "assets/img/icons8-water-transportation-80.png"),
    ):
        shutil.copy2(ROOT / source, DIST / destination)
    for route, anchor in (("projects", "#work"), ("publications", "#publications"), ("blog", "#publications")):
        target = DIST / route / "index.html"
        target.parent.mkdir(parents=True)
        target.write_text(redirect_page(anchor))
    (DIST / ".nojekyll").touch()
    (DIST / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: https://jakendarth.github.io/sitemap.xml\n")
    (DIST / "sitemap.xml").write_text('''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://jakendarth.github.io/</loc></url></urlset>
''')
    if (ROOT / "CNAME").exists():
        shutil.copy2(ROOT / "CNAME", DIST / "CNAME")
    print(f"Built {DIST}")


if __name__ == "__main__":
    main()
