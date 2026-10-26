"""Notera relay: the tiny rendezvous server behind 6-digit share keys.

Two people each run Notera on their own computer. One creates a key, the other types it in,
and the relay hands both of them the same private room. From then on each app pushes the pages
its owner chose to share, and the relay merges them (newest edit per page wins).

Run it anywhere both people can reach:
    python relay.py                 # http://0.0.0.0:5252
Deploy it free on Render / Railway / Fly with the included Procfile, then paste its URL into
Notera's "Sharing" panel. The relay only stores what people explicitly share, never their whole notebook.
"""
import json
import os
import random
import secrets
import threading
import time
from pathlib import Path

from flask import Blueprint, Flask, jsonify, request

DATA_FILE = Path(os.environ.get("RELAY_DATA", Path(__file__).resolve().parent / "relay_data.json"))
KEY_TTL = 10 * 60  # a share key works for 10 minutes
ONLINE_WINDOW = 25  # seconds without a ping before someone shows as offline
MAX_MEMBERS = 2
MAX_MESSAGES = 200

bp = Blueprint("relay", __name__, url_prefix="/relay")
_lock = threading.RLock()
_db = {"keys": {}, "rooms": {}}
_fails = {}  # ip -> recent wrong-key timestamps
MAX_FAILS = 8  # wrong keys per minute per address


def _load():
    global _db
    try:
        _db = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _db = {"keys": {}, "rooms": {}}


def _save():
    try:
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_db), encoding="utf-8")
        tmp.replace(DATA_FILE)
    except OSError:
        pass


def _clean_user(u):
    u = u or {}
    return {
        "id": str(u.get("id", ""))[:24],
        "name": (str(u.get("name", "")).strip() or "Someone")[:40],
        "color": str(u.get("color", "#6b7cff"))[:12],
        "emoji": str(u.get("emoji", ""))[:4],
    }


def _purge():
    now = time.time()
    for k in [k for k, v in _db["keys"].items() if v["expires"] < now]:
        del _db["keys"][k]


def _public(room):
    now = time.time()
    members = []
    for m in room["members"].values():
        members.append({**m["user"], "online": now - m.get("seen", 0) < ONLINE_WINDOW, "joined": m.get("joined", 0)})
    return members


def _say(room, text, sender="system", name="Notera"):
    room["messages"].append({"id": secrets.token_hex(4), "from": sender, "name": name, "text": text[:500], "ts": time.time()})
    del room["messages"][:-MAX_MESSAGES]


def _room_for(rid, uid):
    room = _db["rooms"].get(rid)
    if not room or uid not in room["members"]:
        return None
    room["members"][uid]["seen"] = time.time()
    return room


def _merge_pages(book, incoming):
    """Newest `mt` wins per page. A tombstone ({"deleted": true}) is just a page version that happens to be newest."""
    by_id = {p["id"]: p for p in book}
    for p in incoming:
        if not isinstance(p, dict) or "id" not in p:
            continue
        cur = by_id.get(p["id"])
        if cur is None or p.get("mt", 0) > cur.get("mt", 0):
            by_id[p["id"]] = p
    return list(by_id.values())


@bp.post("/pair/create")
def pair_create():
    body = request.get_json(force=True, silent=True) or {}
    user = _clean_user(body.get("user"))
    if not user["id"]:
        return jsonify({"ok": False, "error": "missing user id"}), 400
    with _lock:
        _purge()
        key = None
        while key is None or key in _db["keys"]:
            key = "%06d" % random.randint(0, 999999)
        rid = secrets.token_urlsafe(18)
        now = time.time()
        room = {"members": {user["id"]: {"user": user, "joined": now, "seen": now}}, "book": [], "messages": [], "created": now}
        _say(room, "%s created this shared space." % user["name"])
        _db["rooms"][rid] = room
        _db["keys"][key] = {"room": rid, "expires": now + KEY_TTL}
        _save()
    return jsonify({"ok": True, "key": key, "room": rid, "expires": now + KEY_TTL})


@bp.post("/pair/join")
def pair_join():
    body = request.get_json(force=True, silent=True) or {}
    user = _clean_user(body.get("user"))
    key = str(body.get("key", "")).strip()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    with _lock:
        _purge()
        now_t = time.time()
        recent = [t for t in _fails.get(ip, []) if now_t - t < 60]
        _fails[ip] = recent
        if len(recent) >= MAX_FAILS:
            return jsonify({"ok": False, "error": "Too many wrong keys. Wait a minute and try again."}), 429
        k = _db["keys"].get(key)
        if not k:
            recent.append(now_t)
            return jsonify({"ok": False, "error": "That key is wrong or has expired."}), 404
        room = _db["rooms"].get(k["room"])
        if not room:
            return jsonify({"ok": False, "error": "That space no longer exists."}), 404
        if user["id"] in room["members"]:
            return jsonify({"ok": False, "error": "You created this key. Give it to someone else."}), 409
        if len(room["members"]) >= MAX_MEMBERS:
            return jsonify({"ok": False, "error": "That space already has two people."}), 409
        now = time.time()
        room["members"][user["id"]] = {"user": user, "joined": now, "seen": now}
        _say(room, "%s (%s) joined. You're connected." % (user["name"], user["id"]))
        del _db["keys"][key]  # keys are single use
        _save()
        return jsonify({"ok": True, "room": k["room"], "members": _public(room), "messages": room["messages"]})


@bp.post("/room/<rid>/sync")
def room_sync(rid):
    body = request.get_json(force=True, silent=True) or {}
    uid = str(body.get("user_id", ""))
    with _lock:
        room = _room_for(rid, uid)
        if room is None:
            return jsonify({"ok": False, "error": "not a member"}), 403
        incoming = body.get("pages") or []
        if incoming:
            room["book"] = _merge_pages(room["book"], incoming)
            _save()
        return jsonify({"ok": True, "pages": room["book"], "members": _public(room), "messages": room["messages"]})


@bp.post("/room/<rid>/message")
def room_message(rid):
    body = request.get_json(force=True, silent=True) or {}
    uid = str(body.get("user_id", ""))
    text = str(body.get("text", "")).strip()
    with _lock:
        room = _room_for(rid, uid)
        if room is None or not text:
            return jsonify({"ok": False}), 403
        _say(room, text, uid, room["members"][uid]["user"]["name"])
        _save()
        return jsonify({"ok": True, "messages": room["messages"]})


@bp.post("/room/<rid>/leave")
def room_leave(rid):
    body = request.get_json(force=True, silent=True) or {}
    uid = str(body.get("user_id", ""))
    with _lock:
        room = _db["rooms"].get(rid)
        if room and uid in room["members"]:
            name = room["members"][uid]["user"]["name"]
            del room["members"][uid]
            if room["members"]:
                _say(room, "%s stopped sharing and left." % name)
            else:
                del _db["rooms"][rid]
            _save()
    return jsonify({"ok": True})


@bp.get("/ping")
def ping():
    return jsonify({"ok": True, "service": "notera-relay"})


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024

    @app.after_request
    def cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    @app.route("/")
    def home():
        return "Notera relay is running."

    app.register_blueprint(bp)
    return app


_load()
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5252)), debug=False, threaded=True)
