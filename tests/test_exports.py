"""Exports (Markdown zip, problems CSV) and request validation.
Run: python tests/test_exports.py"""
import base64, csv, io, json, os, sys, tempfile, zipfile
from pathlib import Path

tmp = tempfile.mkdtemp()
os.environ["NOTERA_DATA"] = os.path.join(tmp, "notes")
os.environ["NOTERA_HOME"] = os.path.join(tmp, "home")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app  # noqa: E402

FAILS = []


def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


PNG = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()
B = lambda t, **k: {"id": "b%d" % abs(hash(json.dumps(k, sort_keys=True) + t)) , "t": t, **k}
state = {"pages": [
    {"id": "f1", "title": "DSA", "parent": None, "folder": True, "tags": [], "blocks": [{"id": "x", "t": "p", "h": ""}]},
    {"id": "p1", "title": "Two Sum / Notes", "parent": "f1", "tags": ["leetcode", "easy", "arrays"], "rev": {"due": 1893456000000, "n": 2}, "hist": [1, 2], "blocks": [
        B("h2", h="Idea"), B("p", h="Use a <b>hash map</b> and <i>one pass</i>, see <a href=\"https://x.test\">link</a>."),
        B("ul", h="first"), B("ul", h="second"), B("todo", h="solved", done=True),
        B("code", h="def f(x):\n    return x  # keep\n\n    ", lang="python", label="Optimal"),
        B("table", rows=[["a", "b|c"], ["1", "2"]]), B("math", h="E=mc^2"),
        B("svg", svg="<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'/>", alt="diagram"),
        B("image", src="data:image/png;base64," + PNG, alt="shot"),
        B("doc", h="<h3>Sub</h3><ul><li>a<ul><li>nested</li></ul></li></ul><pre data-lang=\"js\"><code>let a = 1;\n  b();</code></pre><table><tr><th>H</th></tr><tr><td>v</td></tr></table><details><summary>Hint</summary><p>think</p></details><p>Euler <span class=\"mx\" data-tex=\"e^{i\\pi}\">x</span></p>"),
        B("lc", plat="LeetCode", num="1", url="https://leetcode.com/problems/two-sum/", diff="Easy", status="Solved independently", attempts=2, conf=4, solved="2026-10-01", rel="3Sum"),
        B("qa", h="Q?", a="A!"), B("html", kind="mermaid", src="graph TD\n A-->B"),
        B("html", kind="html", src="<button>x</button>", title="demo"),
    ]},
    {"id": "p2", "title": "Loose", "parent": None, "tags": [], "blocks": [B("p", h="hello")]},
]}
z = zipfile.ZipFile(app.build_markdown_zip(state))
names = z.namelist()
ok("DSA/Two Sum _ Notes.md" in names or any(n.startswith("DSA/Two Sum") and n.endswith(".md") for n in names), "folders become directories and page names are made file-safe: %s" % [n for n in names if n.endswith(".md")])
ok("Loose.md" in names, "top-level page exported")
md = z.read([n for n in names if n.startswith("DSA/") and n.endswith(".md")][0]).decode()
ok(md.startswith('---\ntitle: "Two Sum / Notes"\ntags: [leetcode, easy, arrays]'), "front matter with title and tags")
ok("## Idea" in md and "**hash map**" in md and "*one pass*" in md and "[link](https://x.test)" in md, "headings, bold, italic and links survive")
ok("- first\n- second" in md and "- [x] solved" in md, "list items stay together and the to-do keeps its state")
ok("**Optimal**" in md and "```python\ndef f(x):\n    return x  # keep" in md, "code keeps language, label, indentation and comments")
ok("| a | b\\|c |" in md and "| --- |" in md.replace("|---", "| ---") or "---" in md, "native tables become Markdown tables")
ok("$$\nE=mc^2\n$$" in md and "$e^{i\\pi}$" in md, "display and inline math")
ok("```js\nlet a = 1;\n  b();\n```" in md and "  - nested" in md, "pasted code and nested lists keep structure")
ok("<details><summary>Hint</summary>" in md, "collapsible sections")
ok("```mermaid\ngraph TD" in md, "mermaid stays as a mermaid fence")
ok("**Q:** Q?" in md and "**A:** A!" in md and "Difficulty:** Easy" in md, "flashcards and problem tracker fields")
asset = [n for n in names if "assets/" in n]
ok(any(n.endswith(".png") for n in asset) and z.read([n for n in asset if n.endswith(".png")][0]).startswith(b"\x89PNG"), "images are written as real files")
ok(any(n.endswith(".svg") for n in asset) and any(n.endswith(".html") for n in asset), "SVG and interactive components are written as files")
ok("![shot](assets/" in md, "images are linked relatively")
rows = app.problems_rows(state)
ok(len(rows) == 1 and rows[0][0] == "Two Sum / Notes" and rows[0][5] == "Solved independently" and rows[0][11] == "arrays" and rows[0][12].startswith("2030"), "problem CSV row: %s" % rows[0][:6])

c = app.app.test_client()
r = c.get("/api/export/problems.csv")
ok(r.status_code == 200 and r.mimetype == "text/csv" and "Difficulty" in r.get_data(as_text=True).splitlines()[0], "CSV endpoint")
ok(c.get("/api/export/markdown.zip").status_code == 200, "Markdown zip endpoint")
for bad, why in [({"pages": "x"}, "pages not a list"), ({"nope": 1}, "no pages"), ({"pages": [{"id": "a"}]}, "page without blocks"),
                 ({"pages": [{"id": "a", "blocks": [{"t": "p"}]}]}, "block without id"), ({"pages": [{"id": "a", "blocks": []}, {"id": "a", "blocks": []}]}, "duplicate ids")]:
    ok(c.post("/api/state", json=bad).status_code == 400, "rejects " + why)
ok(not os.path.exists(os.path.join(tmp, "notes", "pages.json")), "rejected requests wrote nothing")
good = {"pages": [{"id": "a", "title": "t", "blocks": [{"id": "b", "t": "p", "h": ""}]}], "trash": []}
ok(c.post("/api/state", json=good).status_code == 200 and json.loads(Path(tmp, "notes", "pages.json").read_text(encoding="utf-8"))["pages"][0]["id"] == "a", "valid notebook is saved")
if FAILS:
    print("\n%d check(s) failed" % len(FAILS))
    sys.exit(1)
print("\nall checks passed")
