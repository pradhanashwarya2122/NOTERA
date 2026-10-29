"""Phone / standalone mode: notes in the browser, Python in the browser, GitHub sync from the browser, installable app files.
GitHub is replaced by an in-memory fake, so nothing leaves your machine except the one Python download (skipped if offline).
Run: python tests/test_standalone.py   (needs playwright + chromium)"""
import base64, json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP playwright is not installed")
    sys.exit(0)

ROOT = Path(__file__).resolve().parent.parent
PORT = 5189
URL = "http://127.0.0.1:%d" % PORT
tmp = tempfile.mkdtemp()
env = dict(os.environ, NOTERA_DATA=os.path.join(tmp, "n"), NOTERA_HOME=os.path.join(tmp, "h"), NOTERA_PORT=str(PORT), NOTERA_DISC_PORT="5401")
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

LAPTOP = {"pages": [{"id": "laptop-only", "title": "Laptop page", "parent": None, "tags": [], "mt": 1, "blocks": [{"id": "x", "t": "p", "h": "hi"}]}], "trash": []}
urllib.request.urlopen(urllib.request.Request(URL + "/api/state", data=json.dumps(LAPTOP).encode(), headers={"content-type": "application/json"}, method="POST"))

# a fake GitHub: one file, pages.json
FAKE = {"content": json.dumps({"pages": [
    {"id": "remote1", "title": "From the laptop", "parent": None, "tags": [], "mt": 5, "blocks": [{"id": "r", "t": "p", "h": "remote"}]},
    {"id": "shared", "title": "Old title", "parent": None, "tags": [], "mt": 1, "blocks": [{"id": "s", "t": "p", "h": "old"}]}], "trash": []}), "sha": "sha1", "puts": 0}


def github(route):
    req = route.request
    path = req.url.split("api.github.com", 1)[1].split("?")[0]
    if path == "/repos/me/notes" and req.method == "GET":
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"default_branch": "main"}))
    if path == "/repos/me/notes/contents/pages.json":
        if req.method == "PUT":
            data = json.loads(req.post_data)
            FAKE["content"] = base64.b64decode(data["content"]).decode("utf-8")
            FAKE["sha"] = "sha%d" % (FAKE["puts"] + 2)
            FAKE["puts"] += 1
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"content": {"sha": FAKE["sha"]}}))
        if "raw" in req.headers.get("accept", ""):
            return route.fulfill(status=200, content_type="application/json", body=FAKE["content"])
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"sha": FAKE["sha"]}))
    return route.fulfill(status=404, body="{}")


try:
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        # 1. on the laptop the shim stays out of the way
        ctx = br.new_context(accept_downloads=True)
        pg = ctx.new_page()
        pg.goto(URL)
        pg.wait_for_selector("#tree")
        pg.wait_for_timeout(500)
        ok(pg.evaluate("window.NOTERA_STANDALONE") is False, "on the laptop the app talks to app.py, not to the browser store")
        ok(pg.evaluate("S.pages.some(p=>p.id==='laptop-only')"), "laptop notes load normally")
        ctx.close()

        # 2. phone mode
        ctx = br.new_context(accept_downloads=True)
        ctx.add_init_script("try{localStorage.setItem('nt.local','1')}catch(e){}")
        ctx.route("https://api.github.com/**", github)
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(URL)
        pg.wait_for_selector("#tree")
        pg.wait_for_timeout(800)
        ok(pg.evaluate("window.NOTERA_STANDALONE") is True, "phone mode switches on")
        ok(pg.evaluate("S.pages.length===1&&S.pages[0].title==='Welcome to Notera'"), "a fresh phone starts with its own welcome page, not the laptop's notes")
        pg.evaluate("document.querySelector('#wel')&&document.querySelector('#wel').classList.remove('show')")

        pg.evaluate("S.pages.push({id:'phone1',title:'Phone note',parent:null,tags:[],mt:Date.now(),blocks:[{id:'pb',t:'p',h:'typed on the phone'}]});S.pages.find(p=>p.id==='shared')||0;save(1)")
        pg.wait_for_timeout(600)
        pg.reload()
        pg.wait_for_selector("#tree")
        pg.wait_for_timeout(800)
        ok(pg.evaluate("S.pages.some(p=>p.id==='phone1')"), "notes saved on the phone survive a reload")
        srv_state = json.loads(urllib.request.urlopen(URL + "/api/state").read())
        ok(not any(p["id"] == "phone1" for p in srv_state["pages"]), "phone notes never touch the laptop server")

        # export for the laptop
        pg.evaluate("document.querySelector('#mmenu').classList.add('show')")
        with pg.expect_download() as d:
            pg.locator("#ex").click()
        saved = Path(tmp, "export.json")
        d.value.save_as(str(saved))
        exported = json.loads(saved.read_text(encoding="utf-8"))
        ok(d.value.suggested_filename.endswith(".json") and any(p["id"] == "phone1" for p in exported["pages"]), "Export gives a backup file the laptop can import")

        # sync both ways
        pg.evaluate("""()=>{const st=S;st.pages.push({id:'shared',title:'New title from phone',parent:null,tags:[],mt:9,blocks:[{id:'s',t:'p',h:'new'}]});save(1);localStorage.setItem('nt.gh',JSON.stringify({repo:'me/notes',token:'tok'}))}""")
        pg.wait_for_timeout(600)
        r = pg.evaluate("fetch('/api/sync/now',{method:'POST'}).then(r=>r.json())")
        ok(r["status"] == "synced", "sync finishes: %s" % r)
        remote = json.loads(FAKE["content"])
        ids = {p["id"]: p for p in remote["pages"]}
        ok({"remote1", "shared", "phone1"} <= set(ids) and not any(p["title"] == "Welcome to Notera" for p in remote["pages"]), "GitHub now has the phone's page and keeps the laptop's, without the welcome page: %s" % sorted(ids))
        ok(ids["shared"]["title"] == "New title from phone", "the newer edit wins")
        pg.evaluate("window.__refresh=1")
        st = pg.evaluate("fetch('/api/state').then(r=>r.json())")
        ok(any(p["id"] == "remote1" for p in st["pages"]), "the laptop's page arrives on the phone")
        puts = FAKE["puts"]
        pg.evaluate("fetch('/api/sync/now',{method:'POST'}).then(r=>r.json())")
        ok(FAKE["puts"] == puts, "a second sync with nothing new uploads nothing")
        FAKE["content"] = "{}"
        bad = pg.evaluate("localStorage.setItem('nt.gh',JSON.stringify({repo:'me/missing',token:'tok'}));fetch('/api/sync/now',{method:'POST'}).then(r=>r.json())")
        ok(bad["status"] == "error", "a wrong repository gives a clear error: %s" % bad["msg"])
        pg.evaluate("localStorage.setItem('nt.gh',JSON.stringify({repo:'me/notes',token:'tok'}))")

        # python in the browser
        res = pg.evaluate("fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:'import sys\\nn=int(input())\\nprint(n*2)\\nprint(sum(range(5)))',stdin:'21'})}).then(r=>r.json())", )
        if "Could not load Python" in res.get("output", ""):
            print("SKIP python in the browser needs internet once: %s" % res["output"][:60])
        else:
            ok(res["ok"] and res["output"].split() == ["42", "10"], "Python runs in the browser with input(): %s" % res)
            err = pg.evaluate("fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:'print(1/0)'})}).then(r=>r.json())")
            ok(not err["ok"] and "ZeroDivisionError" in err["output"], "errors are shown like a normal traceback")

        # install files
        for f in ["manifest.webmanifest", "favicon.svg", "icon-192.png", "icon-512.png", "icon-maskable-512.png", "apple-touch-icon.png", "sw.js"]:
            ok(urllib.request.urlopen(URL + "/" + f).status == 200, "served: " + f)
        man = json.loads(urllib.request.urlopen(URL + "/manifest.webmanifest").read())
        ok(man["display"] == "standalone" and any(i["purpose"] == "maskable" for i in man["icons"]), "the manifest makes it installable")
        ok(pg.evaluate("!!document.querySelector('link[rel=icon]')&&!!document.querySelector('link[rel=manifest]')"), "the page links its favicon and manifest")
        ok(pg.evaluate("navigator.serviceWorker.ready.then(()=>true)"), "the service worker installs so the app opens offline")
        ok(not errors, "no page errors: %s" % errors[:2])
        br.close()
finally:
    srv.terminate()

if FAILS:
    print("\n%d check(s) failed" % len(FAILS))
    sys.exit(1)
print("\nall checks passed")
