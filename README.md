# NOTERA

A calm, colourful notes app for coding notes, LeetCode solutions and revision. It runs on your own computer
(one small Python server and one HTML file) on **Windows and Mac**.

## Start it

| System | What to do |
| --- | --- |
| Windows | Double-click **`start.bat`** |
| Mac / Linux | Double-click **`start.command`** (first time: right-click, Open) or run `./start.command` |

You need [Python 3.10+](https://www.python.org/downloads/) and, for syncing, [Git](https://git-scm.com/downloads).
The first run sets itself up in a private `.venv` folder and opens http://127.0.0.1:5151/ in your browser.

### First run: pick how to begin
- **Start fresh** with a clean notebook.
- **Fetch my notes** from your own *private* GitHub repo (paste its address, sign in to GitHub once).
- **Join a friend** by entering their 6-digit share key.
- **Share my notes** by creating a 6-digit key for a friend.

## Made for coding notes
- **Library**: click *Pages* in the sidebar (or *Library*) for a full-screen organiser. Drag pages onto folders, tick several and press *Move*, rename folders in place.
- **Folder first**: *New page* asks which folder it belongs in (type to search or create one; Shift-click skips). *New folder* is created right in the sidebar, name it and press Enter.
- **Flashcards**: type `/flashcard`, write a question and an answer. *Review* in the sidebar runs a spaced-repetition session (Again, Hard, Good, Easy).
- **Practice tracker** on Home: easy, medium and hard counts from your tags, a day streak, and a *Today* button for a daily note.
- **Code input**: the *Input* button on a code block feeds `input()`, like LeetCode's testcase box, and shows the run time. Press `?` for all shortcuts; *Print or save as PDF* is in the `...` menu.
- **Columns and layouts**: drag any block by its handle and drop it on another block's left or right edge to put them side by side
  (up to four columns). Drag the divider to resize; it snaps to 1/4, 1/3, 1/2, 2/3 and 3/4 with a live percentage. *Layout* on a row
  offers presets, and columns stack on narrow windows. Image beside text just works.
- **Python editor**: indent guides that follow each block to its last line, Backspace removes a full indent step, `else:` snaps to its
  `if`, and Enter after `return` or `pass` steps back out.
- **Folders and subfolders** in the sidebar (New folder, or the folder icon on any folder). Drag pages onto a folder.
- **Templates** (From template): *LeetCode problem* (problem, hint, approach, solution, complexity, edge cases,
  mistakes, key idea), *Concept notes* and *Bug and fix log*. In any page type `/leetcode`.
- **Code blocks** for Python (runnable), JavaScript, TypeScript, Java, C++, C, Go, SQL and Shell, each with a label such as
  *Brute force* or *Optimal*.
- **Callouts** for `/hint`, `/pitfall`, `/idea` and `/complexity`, and colour-coded tags: `easy`, `medium`, `hard`,
  `solved`, `unsolved`, `revise`.
- **Revision**: press *Revise* on a page and pick a day. Due pages appear on Home and in the sidebar.
- **Paste prompt**: paste a whole ChatGPT / Claude / DeepSeek answer into one box. Tables, code, diagrams, step cards,
  quizzes and array visuals are rebuilt.
- Quick find (`Ctrl+P`), page outline (`Alt+O`), collapsible headings, six themes, choosable fonts.

## Your own laptops (private repo sync)
Create an empty **private** repo on GitHub, then on first run choose *Fetch my notes* and paste its address (or later
from the profile area). Notera refuses to sync notes to a repo that is public. Every save is committed and pushed in the
background, and the second laptop pulls and merges page by page.

## Sharing with a friend (6-digit key)
Each install creates an identity on first run: a user id like `NTR-4F9A21`, a name and a colour.

1. **Pick a relay**, the tiny server that introduces two people and passes along only the pages they share.
   - Same Wi-Fi: one person clicks *Host it on this computer*. The other enters the address it shows
     (for example `http://192.168.1.20:5252`).
   - Anywhere: deploy `relay.py` (a `Procfile` is included; start command `gunicorn relay:app`) on Render, Railway or
     Fly, then put its address in `network_config.json` and commit it so every clone uses the same relay:
     `{"relay": "https://your-relay.onrender.com"}`
2. **Pair.** One person creates a key; the other enters the 6 digits. A key works once and expires in 10 minutes.
3. **Share pages** with the people icon on a page. Edits sync both ways. Unshared pages never leave your computer.
4. **Stop sharing** any time. Your pages stay on your computer.

## Privacy
This repo contains only the app. `notes_data/`, `identity.json`, `net.json`, `sync_config.json` and `.venv/` are
git-ignored, so your notes are never published with the code.
