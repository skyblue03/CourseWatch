# CourseWatch

Monitors **publicly available** course/timetable pages and notifies you when a seat appears available.

This project is designed to be **free** and run without leaving software running on your PC:
it uses **GitHub Actions** on a schedule and sends notifications via **GitHub Issues**
(you receive an email from GitHub when an Issue is created).

## What it does
- Fetches a public webpage URL
- Extracts an availability number (e.g., `Availability no: 1`)
- Triggers **only** on transition from not available -> available
- Default: **notify once** and auto-disables that watch to avoid repeats

## What it does NOT do
- No student system login
- No Allocate+ / authenticated scraping
- No auto-enrolment
- No bypassing protections

## Quick start
1. Upload these files to a GitHub repo (or use it as a template).
2. Edit `watchlist.yml`:
   - set `url` to the public Flinders course page
   - keep keyword `Availability no` (or adjust if the page uses different wording)
   - set `label` to something meaningful
3. Enable Actions: Repo → **Actions** tab → enable workflows.
4. Test once: Actions → **CourseWatch check** → **Run workflow**.

## Deactivate / Pause
- Edit `watchlist.yml` and set `enabled: false` for that watch
- Or disable Actions in your repo settings

## Re-arm after a notification
If `mode: once`, the tool auto-sets `enabled: false` after it alerts.
Set it back to `true` to watch again.

## Responsible polling
Default schedule runs every 15 minutes.
Please keep intervals reasonable and follow `docs/ETHICS.md`.
