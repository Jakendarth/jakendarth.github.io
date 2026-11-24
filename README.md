# Nikos Kougiatsos — personal website

Source for [jakendarth.github.io](https://jakendarth.github.io). The homepage is static HTML and CSS. The weekly workflow refreshes three sections: Updates, Selected work, and Recent writing.

## Preview

Run `python3 -m http.server 8000` in this directory and open `http://localhost:8000`.

## Weekly refresh

`.github/workflows/deploy.yml` refreshes and deploys the site every Monday at 07:37 UTC. It also runs on pushes to `master` or `main`, and can be started manually with **Run workflow** in GitHub Actions. The scheduled run commits its checked snapshot to the default branch. In **Settings → Pages**, select **GitHub Actions** as the publishing source when activating the workflow.

`scripts/refresh_content.py` reads OpenAlex works filtered by ORCID `0000-0001-9518-9114` and shows the latest four verified papers in Recent writing. It selects recent, substantive, maritime-related public repositories owned by `Jakendarth` for Selected work. Each project displays its latest release tag, tag, or a clearly labeled commit revision. Empty repositories and forks are excluded, so MAR(AI) will appear only after code is published there. Updates combine recent papers, releases, and editorial features in `assets/data/featured_updates.json`.

If a public feed is unavailable, the existing content and checked date remain in place. News features outside the structured feeds need to be added to `assets/data/featured_updates.json`. GitHub may disable scheduled workflows after 60 days without repository activity, for example if weekly runs fail to commit for an extended period.

Run `python3 scripts/refresh_content.py` for a local refresh, then `python3 scripts/build_site.py` to build the deployment artifact in `dist/`. The build also creates redirects from `/projects/`, `/publications/`, and `/blog/` to the homepage.

## Edit content

Edit `index.html` for the biography and contact links, and `assets/css/renewed.css` for the design. The portrait is `assets/img/tu-delft-portrait.jpg`. The two scheme images are credited in the page and come from open-access [2026](https://research.tudelft.nl/en/publications/integrating-rule-awareness-and-semantic-reasoning-in-collision-fr/) and [2025](https://research.tudelft.nl/en/publications/an-intelligent-agent-based-resilient-framework-for-marine-vessel-/) papers.
