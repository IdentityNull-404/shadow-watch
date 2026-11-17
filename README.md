# Shadow Watch — Cyber Intelligence

Public dashboard: https://identitynull-404.github.io/shadow-watch/

## What updates automatically

* GitHub Actions workflow `Refresh cyber intelligence feed` runs at minute 17 each hour (subject to GitHub's scheduler).
* `scripts/update_feed.py` searches four public security RSS feeds for news from the past 14 days, removes duplicate URLs and matching titles, checks for overlap with the curated ledger, and writes up to 60 headlines to `data/feed.json`.
* Headlines are **DEVELOPING / UNVERIFIED LEADS**, not proof of compromise. The website lists the publishing organization and links the original article.
* If all external sources fail, the script stops with an error and preserves the prior successful snapshot, avoiding false freshness.
* `data/incidents.json` is the curated evidence ledger. It is not silently overwritten by RSS headlines.

## Promote an alert to a reviewed incident

GitHub > Actions > **Publish reviewed alert** > **Run workflow**.
Supply the title, organization, date (YYYY-MM-DD), original HTTPS source, factual summary, and suitable classification.
The script `scripts/publish_alert.py` checks for an existing record by source and by exact organization/date/title; it appends corroborating sources instead of duplicating those matches.
This is a reviewer-initiated action. **Do not classify as Confirmed cyberattack unless independent reporting or the victim confirms malicious activity.**

Alternatively, ask ChatGPT to add a sourced alert to Shadow Watch; if its connected GitHub access is available it can edit `data/incidents.json` directly.

## Setup / diagnostics

1. GitHub > Settings > Pages > Deploy from branch > `main` / `/ (root)`.
2. GitHub > Settings > Actions > General: permit GitHub Actions and make sure workflow permissions allow **Read and write permissions** for repository contents, if permitted by the account settings.
3. GitHub > Actions > **Refresh cyber intelligence feed** > **Run workflow** to populate the initial headline feed.
4. Inspect that run for a green check and verify `data/feed.json` contains a non-null `updated_at`.
5. For publication, inspect the Pages deployment workflow and verify the public URL.

GitHub cron execution may be delayed; the website displays the last successful update timestamp. GitHub Pages publication must be separately enabled.

## Editorial policy

Record the time an event happened and distinguish it from the disclosure date. Preserve source links, confidence levels and status changes. Do not equate unrelated service outages with attacks, infer common attribution from chronology, or publish private victim information. Extortion-site listings alone are ransomware **claims**, not verified breaches.

## Automation limitations

The ChatGPT hourly cyber watch and the GitHub scheduled headline collector are separate services. The ChatGPT watch has been instructed to attempt to write significant alerts to this repository if connected GitHub tools are available in its scheduled execution environment, but such access is not guaranteed. A successful alert notification alone does **not** prove the website was updated. Check the GitHub commit history or dashboard after the alert.
