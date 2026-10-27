# NOTERA

A personal technical knowledge workspace: a rich document editor, a freeform canvas, a programming notebook and a
LeetCode and revision tracker. It runs on your own computer (one small Flask server and one HTML file) on
**Windows and Mac**.

## Start it

| System | What to do |
| --- | --- |
| Windows | Double-click **`start.bat`** |
| Mac / Linux | Double-click **`start.command`** (first time: right-click, Open) or run `./start.command` |

Needs [Python 3.10+](https://www.python.org/downloads/) and, for syncing, [Git](https://git-scm.com/downloads).
The first run creates a private `.venv`, installs Flask and opens http://127.0.0.1:5151/.

First run asks how to begin: start fresh, fetch your notes from a private GitHub repo, join a friend with a 6-digit key,
or share your notes.

## Capture: rich paste

Paste an answer from ChatGPT, Claude, Gemini or a web page and it keeps its structure instead of becoming plain text.
Order of preference: Notera's own block format, then HTML, then Markdown, then plain text.

Kept: headings, bold, italic, links, nested lists, checklists (clickable), tables (copy, CSV, Markdown from the hover bar),
code with language label, indentation, blank lines, Unicode and syntax highlighting (copy button on hover),
collapsible `<details>`, callouts (Note, Tip, Warning), LaTeX (`$..$`, `$$..$$`, KaTeX output), SVG (sanitised, stays a vector),
images, Mermaid fences (rendered in a sandbox), spreadsheet (TSV) data as a table, step cards, quizzes and array widgets rebuilt.
Pasted content is sanitised: scripts, event handlers and unsafe links are removed. Pasted code is never run automatically.

Use the **Paste prompt** block (`/prompt`) to keep a whole answer together in one box.

## Layout: document or canvas

Every page can switch between **Document** and **Canvas** (toggle next to the tags).

**Flow** (on by default): blocks never overlap and gaps close by themselves. Move or resize a block and the others rearrange around it; type in a text box and the blocks below make room. Turn Flow off in the canvas toolbar for fully free placement. **Tidy** lays everything into 1, 2 or 3 columns, and the width button in a block's top bar snaps it to a quarter, third, half, two thirds or full width. Grab a block by its top bar, by its image, or Alt+drag anywhere.

Canvas: drag blocks by their top handle, resize from any corner or edge, rotate images and diagrams, multi-select with
Shift or a marquee, group (`Ctrl G`), duplicate (`Ctrl D`), lock (`L`), bring forward or back (`]`, `[`), nudge with the arrows
(Shift for 10 px), align and distribute, snap to other blocks and an optional grid, zoom (`Ctrl` + wheel), pan (`Space` + drag),
fit (`Ctrl 0`) and a layers panel. Text stays editable: only the handle bar moves a block. Switching back to Document keeps your
blocks and their canvas positions.

Document mode also has columns: drop a block on another block's left or right edge.

## Interactive components

`/component` or **Component** in the add bar: paste HTML or SVG, import a `.html`, `.svg`, `.md`, `.txt` or image file
(or drop files on the page), add Mermaid, or use ready-made native components: **algorithm stepper**, **quiz**, **tabs**.
HTML components run in a sandboxed iframe with no access to your notes, no network, no storage and no popups.
Scripts are off by default for anything that did not come from you inserting it. External libraries cannot load; use inline
code. Mermaid needs an internet connection the first time to fetch its library.

## Coding workspace

- **LeetCode problem** (template or `/lc`): platform, number, link, difficulty, seven statuses, attempts, confidence,
  dates, related problems, plus the 15-section solution notebook. Several solutions can sit side by side (`/solution`).
- **Review**: log how a review went (solved alone, hint, explained only, forgot, again). Intervals default to 1, 3, 7, 14, 30 days
  and are editable. Nothing is marked Mastered automatically.
- **Coding dashboard** on Home: recorded, solved on my own, with hints, studied, attempted, needs revision, difficulty,
  topics, weak topics, weekly activity, 8-week progress, revision queue.
- **DSA pattern library**: 37 patterns with idea, clues, a tested Python template, explanation, example problems, mistakes,
  complexity and related patterns. Install from Home.
- **Templates**: LeetCode, interview question, SQL problem, CS topic, AI/ML concept (12 sections), project documentation,
  concept notes, bug log. **Collections** (Inbox, Programming, DSA and LeetCode...) and **Quick capture** on Home.
- **Code blocks**: Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, SQL, Bash, HTML, CSS, JSON, YAML, Markdown,
  Mermaid. Label, copy, indent guides, smart backspace, saved **snippets** (`/snippet`), custom input for `input()` and run time.
- **Flashcards** (`/flashcard`) with spaced repetition, a review session (`Review`), and a Today note.
- **Links**: type `[[` or `/link` to link notes; backlinks appear under each page. **Search** (`Ctrl P`) covers titles, headings,
  text, code, flashcards, problems and snippets with filters: `code:`, `lang:python`, `card:`, `problem:`, `tag:dp`, `is:due`.

## AI assistant (optional)

Open the `...` menu, **AI settings**, and paste an Anthropic API key (or set `ANTHROPIC_API_KEY`). The key is stored on this
computer by the server and never sent to the browser. Select text and press **AI** for Explain, Simplify, Expand, Summarize,
Example, Mistakes, Takeaways, Compare, Flashcards, Quiz, Interview questions or Diagram. **Explain** on any code block offers
beginner, line by line, syntax, algorithm, time, space, edge cases, mistakes and interview modes. `Alt A` opens a chat that
sees the open note. Results always arrive as new blocks. Nothing is overwritten and tag or folder suggestions apply only when you click.

## Sync and sharing

Your own laptops sync through a **private** GitHub repo (the app refuses to push notes to a public one). Friends can pair with a
6-digit key through a small relay (`relay.py`; host it from the app on the same Wi-Fi, or deploy it and put the address in
`network_config.json`). Pages you share sync both ways. Pages you do not share never leave your computer.

## Tests

```
python tests/run_all.py
```
Covers merge logic, first-run sync, two-laptop sync, friend pairing and sharing, the hosted relay, the AI backend (against a mock
provider) and the pattern templates. UI behaviour (rich paste, canvas, sandbox) was checked in a browser; see
`tests/MANUAL_BROWSER_CHECKS.md`.

## Known limitations

- The AI features have been tested against a mock provider only, not against a live key.
- Pasted tables can be edited, copied and exported, but only the native Table block has add and remove row and column buttons.
  Column resizing is not built.
- Canvas: images cannot be cropped, rotation is for images and diagrams, and there is no virtualisation. A 400-block page
  rerenders in about 1.2 s. Printing a canvas is not laid out for pages; switch to Document to print or save as PDF.
- Code blocks do not have line numbers, line highlighting, collapse, wrapping options or light and dark code themes.
- The **Run** button runs Python on your own computer with a 15 second limit. It is not a security sandbox.
- Interview, computer science and AI/ML areas are templates and tags, not separate databases. There are no CSV or image exports.
- Mermaid inside a Paste prompt box stays as code. It renders when pasted as separate blocks.
- Collections can be renamed, added and deleted, but not manually reordered.
- This is a single-user local app: it has no login. Do not expose port 5151 to a network.

## Privacy
This repo contains only the app. `notes_data/`, `identity.json`, `net.json`, `sync_config.json`, `ai_config.json` and `.venv/`
are git-ignored.
