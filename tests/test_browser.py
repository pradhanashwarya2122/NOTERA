"""Real-browser checks of the core flows (needs: pip install playwright && playwright install chromium).
Starts its own Notera on a temporary data folder, so your notes are never touched.
Run: python tests/test_browser.py"""
import json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP playwright is not installed")
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
PORT = 5183
URL = "http://127.0.0.1:%d" % PORT
tmp = tempfile.mkdtemp()
env = dict(os.environ, NOTERA_DATA=os.path.join(tmp, "n"), NOTERA_HOME=os.path.join(tmp, "h"), NOTERA_PORT=str(PORT), NOTERA_DISC_PORT="5395")
srv = subprocess.Popen([sys.executable, str(ROOT / "app.py")], cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
FAILS = []


def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


for _ in range(60):
    try:
        urllib.request.urlopen(URL + "/api/net", timeout=1)
        break
    except Exception:
        time.sleep(0.25)

B = lambda i, t, h="", **k: {"id": i, "t": t, "h": h, **k}
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZAAAADICAIAAABJdyC1AAAAUElEQVR4nO3BAQ0AAADCoPdPbQ8HFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPwZ0pgAAdqW2lYAAAAASUVORK5CYII="
state = {"pages": [
    {"id": "f1", "title": "DSA", "parent": None, "folder": True, "tags": [], "open": True, "blocks": [B("fb", "p")]},
    {"id": "p1", "title": "Two Sum", "parent": "f1", "tags": ["leetcode"], "mt": 1, "blocks": [B("a1", "h2", "Idea"), B("a2", "p", "Use a hash map"), B("a3", "p", "Second paragraph"), B("a4", "code", "print(1)", lang="python")]},
    {"id": "p2", "title": "Long page", "parent": None, "tags": [], "mt": 2, "blocks": [B("l%d" % i, "p", "line %d" % i) for i in range(80)]},
    {"id": "p3", "title": "With image", "parent": None, "tags": [], "mt": 3, "blocks": [B("im", "image", "", src=PNG, sz="s")]},
], "trash": []}
req = urllib.request.Request(URL + "/api/state", data=json.dumps(state).encode(), headers={"content-type": "application/json"}, method="POST")
urllib.request.urlopen(req)

try:
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        ctx = br.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True)
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(URL)
        pg.wait_for_selector("#tree")
        pg.wait_for_timeout(600)

        ok(pg.evaluate("homeOn") is True and pg.locator(".home").count() == 1, "a fresh launch opens Home")
        ok(pg.locator("#hlib").count() == 1, "Home offers the Library")

        pg.evaluate("homeOn=false;cur='p1';render()")
        ok(pg.locator("#bl .blk").count() == 4, "a page shows its blocks")
        pg.reload()
        pg.wait_for_selector("#bl")
        ok(pg.evaluate("page().id") == "p1" and pg.evaluate("homeOn") is False, "refresh returns to the same page")

        pg.evaluate("homeOn=false;cur='p2';render()")
        pg.wait_for_timeout(300)
        pg.evaluate("document.querySelector('#main').scrollTop=600")
        pg.wait_for_timeout(500)
        pg.reload()
        pg.wait_for_selector("#bl")
        pg.wait_for_timeout(1500)
        ok(abs(pg.evaluate("document.querySelector('#main').scrollTop") - 600) < 40, "refresh resumes the scroll position")

        # typing and the slash menu
        pg.evaluate("homeOn=false;cur='p1';render()")
        pg.locator("#bl .blk .ce").nth(1).click()
        pg.keyboard.press("End")
        pg.keyboard.type(" and one pass")
        pg.wait_for_timeout(700)
        ok("one pass" in pg.evaluate("page().blocks[1].h"), "typing is saved into the page")
        pg.keyboard.press("Enter")
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(400)
        pg.keyboard.type("/head", delay=40)
        pg.wait_for_timeout(300)
        ok(pg.evaluate("getComputedStyle(document.querySelector('#sl')).display!=='none'"), "the / menu opens")
        pg.keyboard.press("Escape")

        # drag a block with a real mouse
        pg.evaluate("homeOn=false;cur='p1';render()")
        first = pg.locator("#bl .blk").nth(0)
        first.hover()
        h = pg.locator("#bl .blk").nth(0).locator(".dh")
        hb = h.bounding_box()
        tb = pg.locator("#bl .blk").nth(3).bounding_box()
        pg.mouse.move(hb["x"] + 6, hb["y"] + 6)
        pg.mouse.down()
        pg.mouse.move(hb["x"] + 8, hb["y"] + 40, steps=4)
        pg.mouse.move(tb["x"] + 80, tb["y"] + tb["height"] - 4, steps=8)
        pg.wait_for_timeout(150)
        ok(pg.locator(".dgh").count() == 1 and pg.evaluate("document.querySelector('#dind').classList.contains('on')"), "dragging shows a ghost and a drop line")
        pg.mouse.up()
        pg.wait_for_timeout(500)
        order = pg.evaluate("page().blocks.map(b=>b.id).join(',')")
        ok(order.split(",")[0] != "a1" and pg.locator(".dgh").count() == 0, "drop reorders the blocks and cleans up: " + order)
        pg.keyboard.press("Control+z")
        pg.evaluate("homeOn=false;cur='p1';render()")

        # alt+arrow keyboard move
        pg.wait_for_timeout(500)
        pg.locator("#bl .blk .ce").nth(0).click()
        pg.wait_for_timeout(200)
        before = pg.evaluate("page().blocks.map(b=>b.id).join(',')")
        pg.keyboard.press("Alt+ArrowDown")
        pg.wait_for_timeout(500)
        ok(pg.evaluate("page().blocks.map(b=>b.id).join(',')") != before, "Alt+Down moves the focused block")

        # text box beside a small image
        pg.evaluate("homeOn=false;cur='p3';render()")
        pg.wait_for_timeout(500)
        ib = pg.locator("#bl .blk .im").bounding_box()
        pg.mouse.move(ib["x"] + ib["width"] + 120, ib["y"] + 40)
        pg.mouse.click(ib["x"] + ib["width"] + 120, ib["y"] + 40)
        pg.wait_for_timeout(500)
        ok(pg.evaluate("page().blocks.length") == 2 and pg.evaluate("!!page().blocks[1].rg"), "clicking beside an image adds a text box in the same row")

        # templates and library preview
        pg.evaluate("openTplSettings()")
        pg.wait_for_selector("#tset.show")
        pg.locator('#tset input[data-k="sqlq"]:not([data-s])').uncheck()
        ok(pg.evaluate("!tplVisible().some(([k])=>k==='sqlq')"), "unticking a template hides it from the New menu")
        pg.locator("#tsr").click()
        pg.locator("#tsd").click()
        pg.evaluate("openLibrary()")
        pg.wait_for_selector(".lr")
        pg.locator(".lr:not(.lf)").first.hover()
        pg.wait_for_timeout(700)
        ok(pg.evaluate("document.querySelector('#lpv').classList.contains('show')"), "hovering a page in the Library shows a preview")

        # recover dialog
        pg.evaluate("openRecover('trash')")
        pg.wait_for_selector("#rec.show")
        ok(pg.locator("#rec .rctabs button").count() == 2, "the recovery dialog opens")
        pg.keyboard.press("Escape")

        # delete then restore from the trash
        pg.evaluate("homeOn=false;cur='p2';render();delPage('p2',true)")
        ok(pg.evaluate("!P('p2')&&S.trash.length===1"), "deleting moves a page to the trash")
        pg.evaluate("openRecover('trash')")
        pg.wait_for_selector("#rec [data-r]")
        pg.locator("#rec [data-r]").first.click()
        ok(pg.evaluate("!!P('p2')&&S.trash.length===0"), "restoring brings it back")
        pg.evaluate("document.querySelector('#rec').classList.remove('show')")

        # exports
        pg.evaluate("document.querySelector('#mmenu').classList.add('show')")
        with pg.expect_download() as d:
            pg.locator("#exmd").click()
        ok(d.value.suggested_filename.endswith(".zip"), "Markdown export downloads a zip")

        # import validation
        pg.evaluate("window.__n=S.pages.length")
        res = pg.evaluate("""()=>{const bad=cleanImportedPage({id:'x'});const evil=cleanImportedPage({id:'e1',title:'t',blocks:[{id:'b1',t:'p',h:'<img src=x onerror=alert(1)><b>ok</b><script>1</script><a href="javascript:alert(1)">l</a>'},{id:'b2',t:'html',src:'<b>x</b>',run:true}]});
          return{bad,h:evil.blocks[0].h,run:evil.blocks[1].run}}""")
        ok(res["bad"] is None and "onerror" not in res["h"] and "<script" not in res["h"] and "javascript:" not in res["h"] and "<b>ok</b>" in res["h"] and res["run"] is False, "import strips scripts and handlers and switches components off: %s" % res["h"])

        # find and replace
        pg.evaluate("homeOn=false;cur='p1';render()")
        pg.keyboard.press("Control+h")
        pg.wait_for_selector("#frb.show")
        pg.fill("#frq", "hash")
        pg.fill("#frr", "dict")
        ok("1 match" in pg.inner_text("#frn"), "find counts matches: " + pg.inner_text("#frn"))
        pg.click("#frall")
        pg.wait_for_timeout(300)
        ok(pg.evaluate("page().blocks.some(b=>/dict map/.test(b.h))") and not pg.evaluate("page().blocks.some(b=>/hash map/.test(b.h))"), "replace all rewrites the text")
        pg.keyboard.press("Escape")

        # home progress
        pg.evaluate("homeOn=true;homeMode='home';homeCur=cur;render()")
        ok("day streak" in pg.inner_text(".hstats"), "Home shows the streak")

        # LeetCode chip and section choice
        pg.evaluate("homeOn=false;cur='p1';render()")
        pg.locator('.add .b[data-a="leetcode"]').click()
        pg.wait_for_timeout(300)
        ok(pg.locator(".lc").count() == 1 and "Dry run" not in pg.evaluate("page().blocks.filter(b=>b.t==='h2').map(b=>b.h).join('|')"), "the LeetCode chip adds the lean template")

        # narrow screen
        pg.set_viewport_size({"width": 390, "height": 800})
        pg.evaluate("homeOn=true;homeMode='home';homeCur=cur;render()")
        pg.wait_for_timeout(300)
        ok(pg.evaluate("document.documentElement.scrollWidth") <= 392, "no sideways scrolling on a phone-width screen")

        ok(not errors, "no page errors: %s" % errors[:3])
        br.close()
finally:
    srv.terminate()

if FAILS:
    print("\n%d check(s) failed" % len(FAILS))
    sys.exit(1)
print("\nall checks passed")
