#!/usr/bin/env python3
"""Refresh updates, publications, and substantive GitHub projects on the homepage."""

from datetime import date, datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import sys
from urllib.error import URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "index.html"
FEATURED = ROOT / "assets/data/featured_updates.json"
ORCID = "https://orcid.org/0000-0001-9518-9114"
GITHUB_OWNER = "Jakendarth"
OPENALEX_URL = "https://api.openalex.org/works?" + urlencode({
    "filter": "authorships.author.orcid:0000-0001-9518-9114",
    "sort": "publication_date:desc",
    "per-page": "20",
})
GITHUB_REPOS_URL = f"https://api.github.com/users/{GITHUB_OWNER}/repos?per_page=100&sort=updated"
PROJECT_DESCRIPTIONS = {
    "GNC_simulator": "Open source guidance, navigation, and control simulation for autonomous surface vessels.",
    "MAR-AI-Platform": "AI tools for explainability and accountability in maritime operations.",
}
PROJECT_TITLES = {"GNC_simulator": "GNC Simulator", "MAR-AI-Platform": "MAR(AI) Platform"}
RELEVANT_TERMS = ("maritime", "marine", "vessel", "ship", "navigation", "propulsion", "gnc", "autonomy", "mar-ai")


def fetch_json(url):
    request = Request(url, headers={"User-Agent": "nikos-kougiatsos-website/1.0", "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def valid_date(value):
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed <= datetime.now(timezone.utc).date() else None
    except (TypeError, ValueError):
        return None


def valid_url(value, host=None):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and (host is None or parsed.hostname == host)


def research_items(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("OpenAlex response did not contain works")
    items = []
    for work in payload["results"]:
        if work.get("type") not in {"article", "conference-paper"}:
            continue
        if not any((entry.get("author") or {}).get("orcid") == ORCID for entry in work.get("authorships", [])):
            continue
        published = valid_date(work.get("publication_date"))
        title, url = work.get("title"), work.get("doi")
        if not published or not isinstance(title, str) or not title.strip() or not valid_url(url, "doi.org"):
            continue
        venue = ((work.get("primary_location") or {}).get("source") or {}).get("display_name") or "Research publication"
        kind = "Conference paper" if work["type"] == "conference-paper" else "Research article"
        items.append({"date": published.isoformat(), "title": title.strip(),
                      "description": f"{kind} in {venue}.", "source": venue, "url": url})
    seen, unique = set(), []
    for item in sorted(items, key=lambda row: row["date"], reverse=True):
        doi = item["url"].lower()
        if doi not in seen:
            seen.add(doi)
            unique.append(item)
    return unique


def selected_repositories(payload):
    if not isinstance(payload, list):
        raise ValueError("GitHub repositories response was not a list")
    selected = []
    for repo in payload:
        name = repo.get("name") or ""
        searchable = f'{name} {repo.get("description") or ""}'.lower()
        pushed = valid_date((repo.get("pushed_at") or "")[:10])
        if repo.get("fork") or repo.get("archived") or (repo.get("size") or 0) < 10:
            continue
        if not pushed or pushed.year < 2024 or name.lower() in {"jakendarth", "nikosk", "jakendarth.github.io"}:
            continue
        if not any(term in searchable for term in RELEVANT_TERMS):
            continue
        if not valid_url(repo.get("html_url"), "github.com") or repo.get("owner", {}).get("login", "").lower() != GITHUB_OWNER.lower():
            continue
        selected.append(repo)
    return sorted(selected, key=lambda repo: repo["pushed_at"], reverse=True)[:3]


def project_details(repo):
    name = repo["name"]
    api_base = f"https://api.github.com/repos/{GITHUB_OWNER}/{quote(name)}"
    releases = fetch_json(api_base + "/releases?per_page=5")
    if not isinstance(releases, list):
        raise ValueError(f"Could not read releases for {name}")
    release = next((entry for entry in releases if not entry.get("draft") and not entry.get("prerelease")
                    and isinstance(entry.get("tag_name"), str)), None)
    if release:
        version = release["tag_name"]
    else:
        tags = fetch_json(api_base + "/tags?per_page=1")
        if not isinstance(tags, list):
            raise ValueError(f"Could not read tags for {name}")
        if tags:
            version = tags[0]["name"]
        else:
            commits = fetch_json(api_base + "/commits?per_page=1")
            if not isinstance(commits, list) or not commits:
                raise ValueError(f"Could not read revision for {name}")
            version = "revision " + commits[0]["sha"][:7]
    pushed = valid_date((repo.get("pushed_at") or "")[:10])
    return {
        "name": name, "title": PROJECT_TITLES.get(name, name.replace("_", " ").replace("-", " ")),
        "description": PROJECT_DESCRIPTIONS.get(name, repo.get("description") or "Open source maritime research software."),
        "url": repo["html_url"], "version": version, "date": pushed.isoformat(),
        "release": release,
    }


def release_update(project):
    release = project["release"]
    if not release:
        return None
    published = valid_date((release.get("published_at") or "")[:10])
    url = release.get("html_url")
    if not published or not valid_url(url, "github.com"):
        return None
    return {"date": published.isoformat(), "title": f'{project["title"]} {project["version"]} released',
            "description": "A new version of the open source maritime research software.",
            "source": "GitHub", "url": url}


def featured_items():
    items = json.loads(FEATURED.read_text())
    for item in items:
        if not valid_date(item.get("date")) or not valid_url(item.get("url")):
            raise ValueError("Invalid featured update")
        for field in ("title", "description", "source"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"Invalid featured update {field}")
    return items


def render_updates(items):
    rows = []
    for item in items:
        published = date.fromisoformat(item["date"])
        rows.append(
            '        <a href="{url}" target="_blank" rel="noopener noreferrer">'
            '<time datetime="{iso}">{date}</time><span><strong>{title}</strong>'
            '<small>{description}</small></span><span class="update-source">{source} '
            '<span aria-hidden="true">↗</span></span></a>'.format(
                url=escape(item["url"], quote=True), iso=item["date"],
                date=published.strftime("%d %b %Y"), title=escape(item["title"]),
                description=escape(item["description"]), source=escape(item["source"])))
    return "\n".join(rows)


def render_writing(items):
    rows = []
    for item in items:
        rows.append(
            '        <a href="{url}" target="_blank" rel="noopener noreferrer">'
            '<span class="publication-year">{year}</span><span class="publication-title">{title}'
            '<small>{source}</small></span><span class="publication-arrow" aria-hidden="true">↗</span></a>'.format(
                url=escape(item["url"], quote=True), year=item["date"][:4],
                title=escape(item["title"]), source=escape(item["source"])))
    return "\n".join(rows)


def render_projects(projects):
    rows = []
    for project in projects:
        updated = date.fromisoformat(project["date"]).strftime("%b %Y")
        rows.append(
            '        <a class="work-card" href="{url}" target="_blank" rel="noopener noreferrer">'
            '<div class="card-art card-art-project" aria-hidden="true"><span class="project-art-overline">OPEN SOURCE / MARITIME</span>'
            '<span class="project-art-title">{art_title}</span><span class="project-art-orbit"></span></div>'
            '<div class="card-meta"><span>GitHub · {version}</span><span>Updated {updated} ↗</span></div>'
            '<h3>{title}</h3><p>{description}</p></a>'.format(
                url=escape(project["url"], quote=True), version=escape(project["version"]),
                updated=updated, title=escape(project["title"]), art_title=escape(project["title"]),
                description=escape(project["description"])))
    return "\n".join(rows)


def replace_between(page, start, end, content):
    if page.count(start) != 1 or page.count(end) != 1:
        raise ValueError(f"Expected one {start} / {end} marker pair")
    prefix, rest = page.split(start, 1)
    _, suffix = rest.split(end, 1)
    return prefix + start + "\n" + content + "\n      " + end + suffix


def main():
    try:
        research = research_items(fetch_json(OPENALEX_URL))
        repos = selected_repositories(fetch_json(GITHUB_REPOS_URL))
        if not research or not repos:
            raise ValueError("A public source returned no verified research or substantive projects")
        projects = [project_details(repo) for repo in repos]
        updates = research + [item for project in projects if (item := release_update(project))] + featured_items()
        updates.sort(key=lambda row: row["date"], reverse=True)
        seen, selected_updates = set(), []
        for item in updates:
            if item["url"].lower() not in seen:
                seen.add(item["url"].lower())
                selected_updates.append(item)
            if len(selected_updates) == 4:
                break
        page = PAGE.read_text()
        page = replace_between(page, "<!-- updates:generated:start -->", "<!-- updates:generated:end -->", render_updates(selected_updates))
        page = replace_between(page, "<!-- writing:generated:start -->", "<!-- writing:generated:end -->", render_writing(research[:4]))
        page = replace_between(page, "<!-- work:generated:start -->", "<!-- work:generated:end -->", render_projects(projects))
        checked = datetime.now(timezone.utc).date()
        checked_text = f'Checked <time datetime="{checked.isoformat()}">{checked.strftime("%d %b %Y")}</time>.'
        page = replace_between(page, "<!-- updates:checked:start -->", "<!-- updates:checked:end -->", checked_text)
        PAGE.write_text(page)
        project_label = "project" if len(projects) == 1 else "projects"
        print(f"Refreshed {len(selected_updates)} updates, {min(4, len(research))} papers, and {len(projects)} {project_label}")
    except (URLError, TimeoutError) as error:
        print(f"Public source unavailable; keeping existing homepage: {error}", file=sys.stderr)
        return 0
    except Exception as error:
        print(f"Content refresh failed; keeping existing homepage: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
