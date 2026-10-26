# NOTERA

A calm, colourful notes app that runs on your own computer. One Flask server and one HTML file.

- Notion-style pages, sub-pages, tags, favourites, quick find (`Ctrl+P`), page outline and collapsible headings
- **Paste prompt** box: paste a whole ChatGPT / Claude / DeepSeek answer and it stays in one box, with tables,
  code, diagrams, step cards, quizzes and array visuals rebuilt
- Runnable Python blocks, image and SVG support, four-plus themes, choosable fonts
- Your notes sync between your own laptops through a private GitHub repo
- A tiny **sharing network**: pair with a friend using a 6-digit key and share chosen pages

## Run
```
start.bat
```
Needs Python 3.10+ and Git. It installs Flask and opens http://127.0.0.1:5151/.

## Your own laptops (private repo sync)
Put your private notes repo address in `sync_config.json`:
```
{"notes_remote": "https://github.com/YOU/notera-notes.git"}
```
On the second laptop: clone this repo, run `start.bat`, sign in to GitHub once. Notes merge page by page.

## Sharing with a friend (6-digit key)
Every install creates a small identity the first time it runs: a user id like `NTR-4F9A21`, a name and an avatar colour.
Open your profile (top of the sidebar):

1. **Pick a relay.** The relay is a tiny server that introduces two people and passes along only the pages they share.
   - Same Wi-Fi: one person clicks **Host it on this computer**. The other enters the address it shows
     (for example `http://192.168.1.20:5252`).
   - Anywhere: deploy `relay.py` free on Render, Railway or Fly (a `Procfile` is included; start command
     `gunicorn relay:app`), then put its address in `network_config.json` and commit it, so everyone who clones
     this repo joins the same network:
     ```
     {"relay": "https://your-relay.onrender.com"}
     ```
2. **Pair.** One person clicks **Create a share key** and sends the 6 digits. The other enters them under
   **Join**. A key works once and expires in 10 minutes.
3. **Share pages.** Click the people icon on a page in the sidebar. Edits sync both ways within seconds.
   Pages you don't share never leave your computer.
4. **Stop any time.** **Stop sharing** unlinks you. Your pages stay on your computer; they just stop syncing.

The relay stores only the pages people explicitly share. Anyone who has a room link can read that room, so treat
the 6-digit key like a short-lived invitation and share it only with the person you mean.

## Privacy
This repo contains only the app. `notes_data/`, `identity.json` and `net.json` are git-ignored.
