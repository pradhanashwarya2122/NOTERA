# Browser checks (run by hand in a real browser, results recorded here)

These cover UI behaviour that the Python tests cannot reach. Each was run against a test instance (separate data folder) with
simulated clipboard, pointer and keyboard events, and the sandbox button was clicked with a real mouse.

## Rich paste
- Pasted one LLM-style response (heading, bold/italic, inline code, link, Python code block with language class, table,
  3-level nested list, checklist, details, "Note:" blockquote, KaTeX math, SVG with `onload` and `<script>`, Mermaid fence): the
  blocks came out in the original order, code kept indentation, blank lines, comments and Unicode (`日本語`, `< & >`).
- Edited the pasted text, toggled a checkbox, saved, reloaded: the edit, the checked state, highlighting, rendered math and the
  collapsible section were all intact. The saved HTML contained no rendered-KaTeX debris.
- The SVG was stored without `script` or `onload`.

## Canvas
- Converted a document to canvas: positions matched the document layout. Clicking in text selected the block without moving it.
- Handle-bar drag, east and south-east resize, fixed height, double-click to restore auto height, marquee select, align left,
  group and group-select, lock, duplicate, delete, undo and redo, zoom and fit all worked.
- Saved, reloaded: positions, sizes and zoom were restored. Switched to document and back: all blocks and layouts kept.
- 400 blocks: ~1.2 s full canvas render, 0.3 ms per drag step, <1 ms search.

## Interactive components and security
- A hostile component tried to read `parent.document`, `localStorage`, `top.location`, `fetch` to the local API and to
  example.com, and load an external image. Every attempt was blocked (reported through `postMessage`). A real mouse click on its
  button still ran the component's own script (counter went to 2).
- Native stepper, quiz and tabs worked and could be edited. Imported: clean SVG (kept as vector), SVG with script (kept in the
  sandbox, scripts off), HTML file, Markdown file with a Mermaid fence and task list.
- Inside the canvas: dragging the handle moved an HTML component, iframe pointer capture was paused during the drag and restored
  afterwards, the sandbox attribute was unchanged, the stepper's Next button did not drag the block, duplicate made an
  independent copy.
- Mermaid rendered a diagram in the sandbox (internet available).

## Learning workspace and AI
- Installed the 37 patterns (idempotent), set up the 10 collections, quick-captured a LeetCode page with 15 sections.
- Status changes set dates and tags; review outcomes moved the next interval; custom intervals respected; three independent
  reviews did not auto-master.
- Dashboard separated recorded, solved alone, solved with hints, studied, attempted and needs revision; an older page tagged
  `solved` was not counted as solved.
- Search filters, `[[`-style links, backlinks and link navigation worked.
- AI (mock provider): setup dialog opens without a key; explain, flashcards, quiz, diagram and explain-code all inserted new
  blocks and left the original untouched; chat inserted a code-fenced answer as a real code block; suggestions applied only
  after a click.

## Flow layout (canvas)
- Dragging a text box beside a diagram placed it level with the diagram, closed the gap below, and left zero overlaps.
- Growing a diagram pushed blocks below it down. Typing 12 lines into a text box pushed the block beneath it from y=179 to y=454.
- Dragging an image moved its block; dragging inside text did not. Tidy made two non-overlapping columns. Flow off left a block at y=2000 untouched.
- A 247-block real page showed 16 overlaps right after load (images still loading) and 0 after the settle pass.
- A background sync poll that swaps in an unchanged copy no longer detaches the open page: edits after it still reach the saved data.
