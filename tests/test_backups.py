"""Snapshot history is thinned (not truncated) and listed quickly.
Run: python tests/test_backups.py"""
import json, os, sys, tempfile, time
from pathlib import Path

tmp = tempfile.mkdtemp()
os.environ.update({"NOTERA_DATA": os.path.join(tmp, "n"), "NOTERA_HOME": os.path.join(tmp, "h")})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app  # noqa: E402

FAILS = []


def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


app.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
now = time.time()
body = json.dumps({"pages": [{"id": "a", "title": "t", "blocks": []}]})
ages = [60 * i for i in range(1, 30)] + [3 * 3600 + 60 * i for i in range(0, 50, 5)] + [3 * 86400 + 3600 * i for i in range(0, 48)] + [100 * 86400]
for i, a in enumerate(ages):
    f = app.BACKUP_DIR / ("pages-x%03d.json" % i)
    f.write_text(body, encoding="utf-8")
    os.utime(f, (now - a, now - a))
app._prune_backups()
left = sorted(app.BACKUP_DIR.glob("pages-*.json"))
kept_ages = sorted((now - f.stat().st_mtime) for f in left)
ok(sum(1 for a in kept_ages if a <= 2 * 3600) == 29, "everything from the last two hours is kept")
ok(1 <= sum(1 for a in kept_ages if 3 * 3600 <= a < 2 * 86400) <= 2, "older snapshots are thinned to one per hour")
ok(sum(1 for a in kept_ages if 2 * 86400 < a < 90 * 86400) <= 3, "after two days, one per day")
ok(not any(a > 90 * 86400 for a in kept_ages), "snapshots older than 90 days are dropped")
c = app.app.test_client()
r = c.get("/api/backups").get_json()
ok(len(r) == len(left) and r[0]["pageCount"] == 1, "listing works and is cached")
if FAILS:
    sys.exit(1)
print("\nall checks passed")
