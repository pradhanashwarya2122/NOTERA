import getpass
import hashlib
import json
import socket
import os
import random
import re
import shutil
import subprocess
import secrets
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import webbrowser
import zipfile
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("NOTERA_DATA", BASE_DIR / "notes_data"))
HOME_DIR = Path(os.environ.get("NOTERA_HOME", BASE_DIR))  # identity.json and net.json live here (never synced to git)
PAGES_FILE = DATA_DIR / "pages.json"
BACKUP_DIR = DATA_DIR / "backups"
FULL_BACKUP_DIR = DATA_DIR / "full_backups"
STATIC_DIR = BASE_DIR / "static"
MAX_BACKUPS = 300
MAX_FULL_BACKUPS = 30

DATA_DIR.mkdir(exist_ok=True)
FULL_BACKUP_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=None)


def load_state():
    if PAGES_FILE.exists():
        try:
            return json.loads(PAGES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    pid = str(uuid.uuid4())[:8]
    return {
        "pages": [
            {
                "id": pid,
                "title": "Welcome",
                "parent": None,
                "tags": ["start"],
                "fav": True,
                "open": True,
                "blocks": [
                    {"id": str(uuid.uuid4())[:8], "t": "h2", "h": "Notes with Python"},
                    {
                        "id": str(uuid.uuid4())[:8],
                        "t": "callout",
                        "h": "Type <b>/</b> in an empty block for the block menu. Code runs with the real Python on your machine.",
                    },
                    {
                        "id": str(uuid.uuid4())[:8],
                        "t": "code",
                        "h": 'def greet(n):\n    return f"Hello, {n}!"\n\nprint(greet("world"))\nprint(sum(range(10)))',
                        "out": "",
                    },
                ],
            }
        ],
        "trash": [],
    }


_last_backup_at = 0.0
BACKUP_THROTTLE_SECONDS = 30  # routine backups at most every 30 seconds


def _count_blocks(state):
    try:
        return sum(len(p.get("blocks", [])) for p in state.get("pages", []))
    except (AttributeError, TypeError):
        return 0


def _backup_current(new_state):
    """Snapshot whatever is currently on disk before it gets overwritten.
    Always backs up on a suspicious shrink (fewer pages/blocks than before);
    otherwise throttled so routine autosaves don't flood the folder."""
    global _last_backup_at
    if not PAGES_FILE.exists():
        return
    try:
        current_text = PAGES_FILE.read_text(encoding="utf-8")
        current_state = json.loads(current_text)
    except (OSError, json.JSONDecodeError):
        return

    old_pages = len(current_state.get("pages", []))
    new_pages = len(new_state.get("pages", []))
    old_blocks = _count_blocks(current_state)
    new_blocks = _count_blocks(new_state)
    shrinking = new_pages < old_pages or new_blocks < old_blocks
    due = (time.time() - _last_backup_at) >= BACKUP_THROTTLE_SECONDS

    if not (shrinking or due):
        return

    ts = time.strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"pages-{ts}.json"
    i = 1
    while dest.exists():
        dest = BACKUP_DIR / f"pages-{ts}-{i}.json"
        i += 1
    dest.write_text(current_text, encoding="utf-8")
    _last_backup_at = time.time()
    _prune_backups()


def _prune_backups():
    files = sorted(BACKUP_DIR.glob("pages-*.json"), key=lambda p: p.stat().st_mtime)
    excess = len(files) - MAX_BACKUPS
    for f in files[:excess]:
        try:
            f.unlink()
        except OSError:
            pass


_state_lock = threading.RLock()


def save_state(state):
    with _state_lock:
        _backup_current(state)
        tmp = PAGES_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(PAGES_FILE)


def file_rev():
    """Short fingerprint of what is on disk. Clients send the rev they last saw so a stale tab can't clobber newer notes."""
    try:
        return hashlib.md5(PAGES_FILE.read_bytes()).hexdigest()[:16]
    except OSError:
        return "none"


# ---------------------------------------------------------------- merging
def _trash_ids(state):
    ids = {}
    for t in state.get("trash", []) or []:
        for pg in t.get("pages", []):
            ids[pg.get("id")] = t.get("at", 0)
    return ids


def merge_states(mine, theirs):
    """Merge two notebooks page by page. The page with the newer `mt` (last-modified ms) wins;
    ties go to `theirs`. A page missing from one side is kept unless that side trashed it after the last edit."""
    mp = {p["id"]: p for p in mine.get("pages", [])}
    tp = {p["id"]: p for p in theirs.get("pages", [])}
    m_trash, t_trash = _trash_ids(mine), _trash_ids(theirs)
    order = [p["id"] for p in mine.get("pages", [])] + [i for i in tp if i not in mp]
    pages = []
    for i in order:
        a, b = mp.get(i), tp.get(i)
        if a and b:
            pages.append(a if a.get("mt", 0) > b.get("mt", 0) else b)
        elif a:
            if not (i in t_trash and t_trash[i] >= a.get("mt", 0)):
                pages.append(a)
        elif not (i in m_trash and m_trash[i] >= b.get("mt", 0)):
            pages.append(b)
    keep = {p["id"]: p for p in pages}
    trash, seen = [], set()
    for t in (mine.get("trash") or []) + (theirs.get("trash") or []):
        root = keep.get(t.get("root"))
        if t.get("id") in seen or (root and root.get("mt", 0) > t.get("at", 0)):
            continue
        seen.add(t.get("id"))
        trash.append(t)
    return {**theirs, **mine, "pages": pages, "trash": trash}


# ---------------------------------------------------------------- git sync
CONFIG_FILE = HOME_DIR / "sync_config.json"
SYNC = {"status": "off", "msg": "Local only", "last": 0}
_sync_lock = threading.RLock()
_kick = threading.Event()
_interactive = False
NOTES_IGNORE = "backups/\nfull_backups/\nexports/\n*.tmp\n"


def load_config():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def git(*args, timeout=120):
    env = os.environ.copy()
    if not _interactive:
        env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        r = subprocess.run(["git", *args], cwd=DATA_DIR, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout, r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, "", str(e)


def _set_sync(status, msg=""):
    SYNC.update(status=status, msg=msg)
    if status == "synced":
        SYNC["last"] = time.time()


def _init_repo(remote):
    DATA_DIR.mkdir(exist_ok=True)
    ignore = DATA_DIR / ".gitignore"
    if not ignore.exists():
        ignore.write_text(NOTES_IGNORE, encoding="utf-8")
    if not (DATA_DIR / ".git").exists():
        git("init", "-b", "main")
    git("config", "user.name", "Notera sync")
    git("config", "user.email", "notera@localhost")
    rc, _, _ = git("remote", "set-url", "origin", remote)
    if rc != 0:
        git("remote", "add", "origin", remote)


_vis_cache = {}


def repo_is_public(remote):
    """Notes are private. If anyone could open the repo without signing in, refuse to push them there."""
    m = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", remote.strip())
    if not m:
        return False
    hit = _vis_cache.get(remote)
    if hit and time.time() - hit[0] < 120:
        return hit[1]
    pub = False
    try:
        req = urllib.request.Request("https://github.com/%s/%s" % m.groups(), method="HEAD", headers={"User-Agent": "notera"})
        with urllib.request.urlopen(req, timeout=8) as r:
            pub = r.status == 200
    except Exception:
        pub = False
    _vis_cache[remote] = (time.time(), pub)
    return pub


def sync_now():
    """Commit local notes, merge with the private notes repo page by page, and push. Safe to call any time."""
    remote = load_config().get("notes_remote")
    if not remote:
        _set_sync("off", "Local only")
        return SYNC
    if shutil.which("git") is None:
        _set_sync("error", "Git is not installed")
        return SYNC
    with _sync_lock:
        _set_sync("syncing", "Syncing")
        try:
            if repo_is_public(remote) and not load_config().get("allow_public"):
                _set_sync("error", "That notes repo is public. Make it private on GitHub, then sync again.")
                return SYNC
            _init_repo(remote)
            rc, _, err = git("fetch", "origin", timeout=180)
            if rc != 0:
                _set_sync("offline", err.strip().splitlines()[-1] if err.strip() else "Offline")
                return SYNC
            has_remote = git("rev-parse", "--verify", "-q", "origin/main")[0] == 0
            if has_remote and not PAGES_FILE.exists():
                git("checkout", "-f", "-B", "main", "origin/main")
            for attempt in range(3):
                with _state_lock:
                    git("add", *[f for f in (".gitignore", "pages.json") if (DATA_DIR / f).exists()])
                    if git("diff", "--cached", "--quiet")[0] != 0:
                        git("commit", "-m", "notes " + time.strftime("%Y-%m-%d %H:%M:%S"))
                    if has_remote and git("merge-base", "--is-ancestor", "origin/main", "HEAD")[0] != 0:
                        rc, remote_text, _ = git("show", "origin/main:pages.json")
                        merged = merge_states(load_state(), json.loads(remote_text)) if rc == 0 else None
                        git("merge", "-s", "ours", "--no-edit", "--allow-unrelated-histories", "origin/main")
                        if merged is not None and json.dumps(merged, ensure_ascii=False, indent=2) != PAGES_FILE.read_text(encoding="utf-8"):
                            save_state(merged)
                        if PAGES_FILE.exists():
                            git("add", "pages.json")
                        if git("diff", "--cached", "--quiet")[0] != 0:
                            git("commit", "-m", "merge " + time.strftime("%Y-%m-%d %H:%M:%S"))
                rc, _, err = git("push", "origin", "HEAD:main", timeout=180)
                if rc == 0:
                    _set_sync("synced", "Synced")
                    return SYNC
                git("fetch", "origin")
                has_remote = git("rev-parse", "--verify", "-q", "origin/main")[0] == 0
            _set_sync("offline", "Could not push")
        except Exception as e:  # never let sync take the app down
            _set_sync("error", str(e)[:120])
    return SYNC


# ---------------------------------------------------------------- identity + sharing network
IDENT_FILE = HOME_DIR / "identity.json"
NET_FILE = HOME_DIR / "net.json"
NET_DEFAULT = BASE_DIR / "network_config.json"
PALETTE = ["#e03e3e", "#d9730d", "#dfab01", "#0f7b6c", "#0b6e99", "#6940a5", "#ad1a72", "#64473a"]
NETST = {"status": "off", "msg": "", "members": [], "messages": [], "key": None, "keyexp": 0, "last": 0}
_net_lock = threading.RLock()


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_identity():
    """A stable per-person identity made on first run: an id like NTR-4F9A21 plus an editable name and colour."""
    d = _read_json(IDENT_FILE)
    if not d.get("id"):
        try:
            name = getpass.getuser().replace(".", " ").replace("_", " ").title()
        except Exception:
            name = "Writer"
        d = {"id": "NTR-" + secrets.token_hex(3).upper(), "name": name or "Writer", "color": random.choice(PALETTE), "emoji": "", "created": time.time()}
        _write_json(IDENT_FILE, d)
    return d


def get_net():
    d = _read_json(NET_FILE)
    d.setdefault("relay", os.environ.get("NOTERA_RELAY") or _read_json(NET_DEFAULT).get("relay", ""))
    return d


_relay_srv = None


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
            sk.connect(("10.255.255.255", 1))
            return sk.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def host_relay():
    """Run the relay inside this app so two computers on the same network can pair with no hosting."""
    global _relay_srv
    if _relay_srv:
        return
    import relay as relaymod
    from werkzeug.serving import make_server

    _relay_srv = make_server("0.0.0.0", 5252, relaymod.app, threaded=True)
    threading.Thread(target=_relay_srv.serve_forever, daemon=True).start()


def relay_call(path, body=None):
    relay = (get_net().get("relay") or "").strip().rstrip("/")
    if not relay:
        return 0, {"error": "Add a relay address first (see README: Sharing)."}
    req = urllib.request.Request(relay + "/relay" + path, data=json.dumps(body or {}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {"error": "Relay error %s" % e.code}
    except Exception as e:
        return 0, {"error": "Can't reach the relay: %s" % str(e)[:80]}


def _public_user(me):
    return {"id": me["id"], "name": me["name"], "color": me["color"], "emoji": me.get("emoji", "")}


def net_sync():
    """Push the pages I chose to share, pull the room's merged copy, and apply anything newer."""
    with _net_lock:
        net, me = get_net(), get_identity()
        room = net.get("room")
        if not room:
            NETST.update(status="off", members=[], messages=[])
            return
        with _state_lock:
            state = load_state()
            pages = state.get("pages", [])
            ids = {pg["id"] for pg in pages}
            payload = [dict(pg) for pg in pages if pg.get("share")]
            tombs = net.setdefault("tombs", {})
            for sid in net.get("shared_ids", []):
                if sid not in ids and sid not in tombs:
                    tombs[sid] = int(time.time() * 1000)
            payload += [{"id": i, "deleted": True, "mt": t} for i, t in tombs.items()]
            code, data = relay_call("/room/%s/sync" % room, {"user_id": me["id"], "pages": payload})
            if code == 403:
                net.pop("room", None), net.pop("shared_ids", None), net.pop("tombs", None)
                _write_json(NET_FILE, net)
                NETST.update(status="off", msg="The shared space was closed.", members=[], messages=[], key=None)
                return
            if code != 200:
                NETST.update(status="offline", msg=data.get("error", "Offline"))
                return
            changed = False
            for bp in data.get("pages", []):
                local = next((x for x in pages if x["id"] == bp["id"]), None)
                if bp.get("deleted"):
                    if local and bp.get("mt", 0) >= local.get("mt", 0):
                        pages.remove(local)
                        changed = True
                elif local is None or bp.get("mt", 0) > local.get("mt", 0):
                    if local is None and tombs.get(bp["id"], 0) >= bp.get("mt", 0):
                        continue
                    bp["share"] = True
                    if local is None:
                        pages.append(bp)
                    else:
                        pages[pages.index(local)] = bp
                    changed = True
            if changed:
                if not pages:
                    pages.append({"id": uuid.uuid4().hex[:8], "title": "", "parent": None, "tags": [], "fav": False, "open": True, "blocks": [{"id": uuid.uuid4().hex[:8], "t": "p", "h": ""}]})
                state["pages"] = pages
                save_state(state)
            net["shared_ids"] = [pg["id"] for pg in pages if pg.get("share")]
            _write_json(NET_FILE, net)
        NETST.update(status="synced", msg="Connected", members=data.get("members", []), messages=data.get("messages", []), last=time.time())
        if len(NETST["members"]) > 1:
            NETST["key"] = None


def _net_loop():
    while True:
        time.sleep(3)
        try:
            if get_net().get("room"):
                net_sync()
        except Exception as e:
            NETST.update(status="error", msg=str(e)[:100])


def _net_view():
    net = get_net()
    return {
        "identity": get_identity(),
        "relay": net.get("relay", ""),
        "joined": bool(net.get("room")),
        "status": NETST["status"],
        "msg": NETST["msg"],
        "members": NETST["members"],
        "messages": NETST["messages"],
        "key": NETST["key"] if NETST["keyexp"] > time.time() else None,
        "keyexp": NETST["keyexp"],
        "hosting": _relay_srv is not None,
        "lan": "http://%s:5252" % lan_ip(),
    }


def _sync_loop():
    while True:
        kicked = _kick.wait(timeout=20)
        if kicked:
            time.sleep(3)  # let a burst of edits settle into one commit
            _kick.clear()
        sync_now()


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.route("/api/state", methods=["GET"])
def get_state():
    with _state_lock:
        return jsonify({**load_state(), "_rev": file_rev()})


@app.route("/api/rev", methods=["GET"])
def get_rev():
    return jsonify({"rev": file_rev(), "sync": SYNC, "net": {"joined": bool(get_net().get("room")), "peers": max(0, len(NETST["members"]) - 1), "status": NETST["status"], "messages": len(NETST["messages"])}})


@app.route("/api/state", methods=["POST"])
def put_state():
    state = request.get_json(force=True)
    base = state.pop("_rev", None)
    resp = {"ok": True}
    with _state_lock:
        if base is not None and PAGES_FILE.exists() and base != file_rev():
            # another tab or laptop saved since this client last looked: merge instead of overwriting
            state = merge_states(state, load_state())
            resp["state"] = state
        save_state(state)
        resp["rev"] = file_rev()
    _kick.set()
    return jsonify(resp)


@app.route("/api/me", methods=["GET", "POST"])
def me_route():
    me = get_identity()
    if request.method == "POST":
        body = request.get_json(force=True)
        if str(body.get("name", "")).strip():
            me["name"] = str(body["name"]).strip()[:40]
        if body.get("color"):
            me["color"] = str(body["color"])[:12]
        if "emoji" in body:
            me["emoji"] = str(body["emoji"])[:4]
        _write_json(IDENT_FILE, me)
    return jsonify(me)


@app.route("/api/onboard", methods=["GET", "POST"])
def onboard_route():
    me = get_identity()
    if request.method == "POST":
        me["onboarded"] = True
        _write_json(IDENT_FILE, me)
        return jsonify({"ok": True})
    needed = not me.get("onboarded") and not PAGES_FILE.exists()
    if not me.get("onboarded") and PAGES_FILE.exists():
        me["onboarded"] = True  # an existing notebook never sees the welcome screen
        _write_json(IDENT_FILE, me)
    return jsonify({"needed": needed, "git": shutil.which("git") is not None, "remote": load_config().get("notes_remote", "")})


@app.route("/api/net", methods=["GET"])
def net_route():
    return jsonify(_net_view())


@app.route("/api/net/relay", methods=["POST"])
def net_relay_route():
    net = get_net()
    net["relay"] = str(request.get_json(force=True).get("relay", "")).strip()
    _write_json(NET_FILE, net)
    return jsonify(_net_view())


@app.route("/api/net/host", methods=["POST"])
def net_host_route():
    try:
        host_relay()
    except OSError as e:
        return jsonify({"ok": False, "error": "Could not start the relay: %s" % e}), 500
    net = get_net()
    net["relay"], net["host"] = "http://127.0.0.1:5252", True
    _write_json(NET_FILE, net)
    return jsonify({"ok": True, **_net_view()})


@app.route("/api/net/create", methods=["POST"])
def net_create_route():
    with _net_lock:
        net = get_net()
        if net.get("room"):
            return jsonify({"ok": False, "error": "You are already sharing. Stop sharing first."}), 409
        code, data = relay_call("/pair/create", {"user": _public_user(get_identity())})
        if code != 200:
            return jsonify({"ok": False, "error": data.get("error", "Failed")}), 502
        net["room"], net["shared_ids"], net["tombs"] = data["room"], [], {}
        _write_json(NET_FILE, net)
        NETST.update(key=data["key"], keyexp=data["expires"], status="synced", msg="Waiting for someone to enter your key")
    net_sync()
    return jsonify({"ok": True, **_net_view()})


@app.route("/api/net/join", methods=["POST"])
def net_join_route():
    key = str(request.get_json(force=True).get("key", "")).strip()
    with _net_lock:
        net = get_net()
        if net.get("room"):
            return jsonify({"ok": False, "error": "You are already sharing. Stop sharing first."}), 409
        code, data = relay_call("/pair/join", {"key": key, "user": _public_user(get_identity())})
        if code != 200:
            return jsonify({"ok": False, "error": data.get("error", "Failed")}), 400 if code else 502
        net["room"], net["shared_ids"], net["tombs"] = data["room"], [], {}
        _write_json(NET_FILE, net)
        NETST.update(key=None, members=data.get("members", []), messages=data.get("messages", []), status="synced", msg="Connected")
    net_sync()
    return jsonify({"ok": True, **_net_view()})


@app.route("/api/net/leave", methods=["POST"])
def net_leave_route():
    with _net_lock:
        net, me = get_net(), get_identity()
        room = net.get("room")
        if room:
            relay_call("/room/%s/leave" % room, {"user_id": me["id"]})
        for k in ("room", "shared_ids", "tombs"):
            net.pop(k, None)
        _write_json(NET_FILE, net)
        with _state_lock:
            state = load_state()
            for pg in state.get("pages", []):
                if pg.pop("share", None):
                    pg["mt"] = int(time.time() * 1000)  # unsharing is an edit, so it syncs to the other laptop too
            save_state(state)
        NETST.update(status="off", msg="", members=[], messages=[], key=None, keyexp=0)
    return jsonify({"ok": True, **_net_view()})


@app.route("/api/net/message", methods=["POST"])
def net_message_route():
    text = str(request.get_json(force=True).get("text", "")).strip()
    net = get_net()
    if not net.get("room") or not text:
        return jsonify({"ok": False}), 400
    code, data = relay_call("/room/%s/message" % net["room"], {"user_id": get_identity()["id"], "text": text})
    if code == 200:
        NETST["messages"] = data.get("messages", [])
    return jsonify({"ok": code == 200, **_net_view()})


@app.route("/api/sync/now", methods=["POST"])
def sync_route():
    return jsonify(sync_now())


@app.route("/api/sync/config", methods=["POST"])
def sync_config():
    remote = (request.get_json(force=True).get("remote") or "").strip()
    if not remote:
        return jsonify({"ok": False}), 400
    CONFIG_FILE.write_text(json.dumps({"notes_remote": remote}, indent=2), encoding="utf-8")
    return jsonify(sync_now())


@app.route("/api/export", methods=["GET"])
def export_state():
    return jsonify(load_state())


@app.route("/api/export-notes/download", methods=["GET"])
def export_notes_download():
    """Reliable server-generated download of the current notes (text, code, images — all embedded), independent of any client-side Blob/anchor quirks."""
    state = load_state()
    data = json.dumps(state, ensure_ascii=False, indent=2)
    ts = time.strftime("%Y%m%d-%H%M%S")
    resp = app.response_class(data, mimetype="application/json")
    resp.headers["Content-Disposition"] = f'attachment; filename="notera-notes-{ts}.json"'
    return resp


@app.route("/api/backups", methods=["GET"])
def list_backups():
    items = []
    for f in sorted(BACKUP_DIR.glob("pages-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            state = json.loads(f.read_text(encoding="utf-8"))
            pages = state.get("pages", [])
            titles = [p.get("title") or "Untitled" for p in pages][:4]
            blocks = _count_blocks(state)
        except (OSError, json.JSONDecodeError):
            pages, titles, blocks = [], [], 0
        items.append(
            {
                "file": f.name,
                "mtime": f.stat().st_mtime,
                "pageCount": len(pages),
                "blockCount": blocks,
                "titles": titles,
            }
        )
    return jsonify(items)


@app.route("/api/backups/<name>", methods=["GET"])
def get_backup(name):
    if not re.fullmatch(r"pages-[0-9a-zA-Z._-]+\.json", name):
        return jsonify({"ok": False, "error": "bad name"}), 400
    f = BACKUP_DIR / name
    if not f.exists():
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify(json.loads(f.read_text(encoding="utf-8")))


@app.route("/api/backups/<name>/restore", methods=["POST"])
def restore_backup(name):
    if not re.fullmatch(r"pages-[0-9a-zA-Z._-]+\.json", name):
        return jsonify({"ok": False, "error": "bad name"}), 400
    f = BACKUP_DIR / name
    if not f.exists():
        return jsonify({"ok": False, "error": "not found"}), 404
    state = json.loads(f.read_text(encoding="utf-8"))
    now = int(time.time() * 1000)
    for pg in state.get("pages", []):
        pg["mt"] = now  # a restore is a deliberate edit, so it must win the next sync
    save_state(state)
    _kick.set()
    return jsonify({"ok": True})


@app.route("/api/run", methods=["POST"])
def run_code():
    body = request.get_json(force=True)
    code = body.get("code", "")

    with tempfile.TemporaryDirectory() as td:
        script_path = Path(td) / "snippet.py"
        script_path.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(script_path)],
                cwd=td,
                capture_output=True,
                text=True,
                timeout=15,
            )
            out = proc.stdout
            err = proc.stderr
            ok = proc.returncode == 0
            combined = out if ok else (out + err if out else err)
            return jsonify({"ok": ok, "output": combined.strip() or "(no output)"})
        except subprocess.TimeoutExpired:
            return jsonify({"ok": False, "output": "Timed out after 15 seconds."})


def _prune_full_backups():
    files = sorted(FULL_BACKUP_DIR.glob("notera-backup-*.zip"), key=lambda p: p.stat().st_mtime)
    excess = len(files) - MAX_FULL_BACKUPS
    for f in files[:excess]:
        try:
            f.unlink()
        except OSError:
            pass


@app.route("/api/full-backup", methods=["POST"])
def full_backup():
    """Zip the whole NOTERA folder (app, notes, images, code, history) into one file."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    dest = FULL_BACKUP_DIR / f"notera-backup-{ts}.zip"
    skip_dirs = {FULL_BACKUP_DIR.resolve(), (BASE_DIR / "__pycache__").resolve()}
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE_DIR):
            root_path = Path(root).resolve()
            if any(root_path == d or str(root_path).startswith(str(d) + os.sep) for d in skip_dirs):
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                fpath = Path(root) / name
                zf.write(fpath, fpath.relative_to(BASE_DIR))
    _prune_full_backups()
    return jsonify({"ok": True, "file": dest.name, "size": dest.stat().st_size})


@app.route("/api/full-backup/latest", methods=["GET"])
def full_backup_latest():
    files = sorted(FULL_BACKUP_DIR.glob("notera-backup-*.zip"), key=lambda p: p.stat().st_mtime)
    if not files:
        return jsonify({"ok": False, "error": "no backups yet"}), 404
    return send_file(files[-1], as_attachment=True, download_name=files[-1].name)


@app.route("/api/full-backup/list", methods=["GET"])
def full_backup_list():
    items = [
        {"file": f.name, "mtime": f.stat().st_mtime, "size": f.stat().st_size}
        for f in sorted(FULL_BACKUP_DIR.glob("notera-backup-*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    ]
    return jsonify(items)


@app.route("/api/full-backup/<name>/download", methods=["GET"])
def full_backup_download(name):
    if not re.fullmatch(r"notera-backup-[0-9a-zA-Z._-]+\.zip", name):
        return jsonify({"ok": False, "error": "bad name"}), 400
    f = FULL_BACKUP_DIR / name
    if not f.exists():
        return jsonify({"ok": False, "error": "not found"}), 404
    return send_file(f, as_attachment=True, download_name=name)


@app.route("/api/save-py", methods=["POST"])
def save_py():
    body = request.get_json(force=True)
    filename = body.get("filename", "notes.py")
    code = body.get("code", "")
    safe_name = "".join(c for c in filename if c.isalnum() or c in ("_", "-", ".")) or "notes.py"
    out_dir = DATA_DIR / "exports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / safe_name
    out_path.write_text(code, encoding="utf-8")
    return jsonify({"ok": True, "path": str(out_path)})


@app.route("/api/save-md", methods=["POST"])
def save_md():
    body = request.get_json(force=True)
    filename = body.get("filename", "notes.md")
    text = body.get("text", "")
    safe_name = "".join(c for c in filename if c.isalnum() or c in ("_", "-", ".")) or "notes.md"
    out_dir = DATA_DIR / "exports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / safe_name
    out_path.write_text(text, encoding="utf-8")
    return jsonify({"ok": True, "path": str(out_path)})


if __name__ == "__main__":
    if "--sync-once" in sys.argv:
        # used by start.bat: pull the notes (may open a GitHub sign-in the first time on a new laptop)
        _interactive = True
        print("Syncing notes...", sync_now()["msg"])
        sys.exit(0)
    port = int(os.environ.get("NOTERA_PORT", 5151))
    url = "http://127.0.0.1:%d/" % port
    try:  # already running? just bring up the browser instead of failing on the busy port
        with urllib.request.urlopen(url + "api/rev", timeout=1.5):
            if "--open" in sys.argv:
                webbrowser.open(url)
            print("Notera is already running at", url)
            sys.exit(0)
    except (OSError, urllib.error.URLError):
        pass
    threading.Thread(target=_sync_loop, daemon=True).start()
    threading.Thread(target=_net_loop, daemon=True).start()
    if "--open" in sys.argv:
        threading.Timer(1.2, webbrowser.open, [url]).start()
    if get_net().get("host"):
        try:
            host_relay()
        except OSError:
            pass
    _kick.set()
    print("Notera is running at", url, "(close this window to stop it)")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
