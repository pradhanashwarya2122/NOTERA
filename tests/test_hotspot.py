"""Hotspot and shared Wi-Fi: the hosted relay must be reachable through every network address of the host,
discoverable by broadcast-style probe, and testable. Run: python tests/test_hotspot.py"""
import json, os, sys, tempfile, urllib.request
from pathlib import Path

tmp = tempfile.mkdtemp()
os.environ.update({"NOTERA_DATA": os.path.join(tmp, "n"), "NOTERA_HOME": os.path.join(tmp, "h"), "NOTERA_DISC_PORT": "5393", "RELAY_DATA": os.path.join(tmp, "relay.json")})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app  # noqa: E402

FAILS = []


def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


ips = app.lan_ips()
ok(len(ips) >= 1 and all(i.count(".") == 3 for i in ips), "lists the host's network addresses: %s" % ips)
app.host_relay()
reach = {}
for ip in ["127.0.0.1"] + [i for i in ips if i != "127.0.0.1"]:
    try:
        with urllib.request.urlopen("http://%s:5252/relay/ping" % ip, timeout=4) as r:
            reach[ip] = json.loads(r.read())["service"] == "notera-relay"
    except Exception as e:
        reach[ip] = False
ok(all(reach.values()), "hosted relay answers on every address a hotspot might use: %s" % reach)
found = app.discover_relays(timeout=1.5, targets=[("127.0.0.1", 5393)])
ok(len(found) == 1 and found[0]["relay"].endswith(":5252") and found[0]["name"], "a friend's app can discover the host without typing an address: %s" % found)
c = app.app.test_client()
r = c.post("/api/net/test", json={"relay": "http://127.0.0.1:5252"}).get_json()
ok(r["ok"] and r["ms"] >= 0, "connection test succeeds against the host (%s ms)" % r.get("ms"))
r = c.post("/api/net/test", json={"relay": "http://127.0.0.1:5999"}).get_json()
ok(not r["ok"] and "same Wi-Fi or hotspot" in r["error"], "connection test explains what to check when it fails")
r = c.post("/api/net/test", json={"relay": "http://127.0.0.1:%d" % 5393}).get_json()
ok(not r["ok"], "a non-Notera service on the port is not accepted")
v = c.get("/api/net").get_json()
ok(v["hosting"] and v["lans"] and all(u.endswith(":5252") for u in v["lans"]), "the panel gets every address to share: %s" % v["lans"])
app._relay_srv.shutdown()
if FAILS:
    print("\n%d check(s) failed" % len(FAILS))
    sys.exit(1)
print("\nall checks passed")
