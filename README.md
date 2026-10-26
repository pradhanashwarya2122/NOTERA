# Notera

A fast, minimal note-taking app that runs locally (Flask + one HTML file) with runnable Python blocks,
rich paste from ChatGPT / Claude / DeepSeek (headings, tables, code, SVG diagrams, images) and automatic
sync between laptops through a **private** GitHub repo.

## Run
```
start.bat
```
Needs Python 3.10+ and Git. It installs Flask, pulls your notes, and opens http://127.0.0.1:5151/.

## Second laptop in 3 steps
1. Install Python and Git.
2. `git clone <this repo>` then double-click `start.bat`.
3. Sign in to GitHub when the window asks (first time only). Your notes appear and keep syncing.

## How sync works
- Notes live in `notes_data/`, which is its own git repo pointing at your private notes repo (see `sync_config.json`).
- Every save is committed and pushed in the background a few seconds later; the other laptop pulls every ~20 seconds
  and the open page updates itself without interrupting typing.
- Both laptops can be edited at once: notes are merged page by page, newest edit wins per page, deletions go to Trash.
- Click the status text at the bottom of the sidebar ("Synced") to sync immediately.
- Offline? Keep writing. It syncs when you are back online.

## Privacy
This repo contains only the app. `notes_data/` is git-ignored here and is never published with the code.
