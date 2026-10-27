"""Checks that every DSA pattern template shipped in static/index.html is valid, runnable Python
and that a representative set returns correct answers. Needs Node.js to read the JS array; skipped without it.
Run: python tests/test_patterns.py"""
import ast, json, shutil, subprocess, sys, tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
FAILS = []


def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


if not shutil.which("node"):
    print("SKIP: Node.js not installed")
    sys.exit(0)
tmp = Path(tempfile.mkdtemp())
(tmp / "x.js").write_text(
    "const fs=require('fs');const s=fs.readFileSync(%s,'utf8');const a=s.indexOf('const PAT=['),b=s.indexOf('function installPatterns');"
    "const PAT=eval('('+s.slice(a+'const PAT='.length,b).trim().replace(/;$/,'')+')');"
    "fs.writeFileSync(%s,JSON.stringify(PAT.map(p=>({cat:p[0],name:p[1],code:p[4],n:p.length}))));" % (json.dumps(str(root / "static" / "index.html")), json.dumps(str(tmp / "pat.json"))),
    encoding="utf-8",
)
subprocess.run(["node", str(tmp / "x.js")], check=True)
P = json.loads((tmp / "pat.json").read_text(encoding="utf-8"))
ok(len(P) >= 35, "at least 35 patterns shipped (%d)" % len(P))
ok(all(p["n"] == 10 for p in P), "every pattern has idea, clues, template, explanation, complexity, examples, mistakes and related")
bad = []
for p in P:
    try:
        ast.parse(p["code"])
    except SyntaxError as e:
        bad.append((p["name"], str(e)))
ok(not bad, "every template is valid Python %s" % (bad or ""))
code = {p["name"]: p["code"] for p in P}


def run(name, fn, *a):
    g = {}
    exec(code[name], g)
    return g[fn](*a)


ok(run("Complement lookup", "two_sum", [2, 7, 11, 15], 9) == [0, 1], "two sum")
ok(run("Sliding window", "longest_unique", "abcabcbb") == 3, "sliding window")
ok(run("Kadane's algorithm", "max_subarray", [-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6, "kadane")
ok(run("Binary search and boundaries", "lower_bound", [1, 2, 4, 4, 7], 4) == 2, "lower bound")
ok(run("Monotonic stack", "next_greater", [2, 1, 2, 4, 3]) == [4, 2, 4, -1, -1], "monotonic stack")
ok(run("Tabulation and state definitions", "coin_change", [1, 2, 5], 11) == 3, "coin change")
ok(run("Transition equations", "lcs", "abcde", "ace") == 3, "lcs")
ok(sorted(run("Constraint pruning", "combination_sum", [2, 3, 6, 7], 7)) == [[2, 2, 3], [7]], "combination sum")
ok(run("Topological sorting", "topo_order", 2, [[0, 1], [1, 0]]) == [], "topological sort reports a cycle")
ok(run("Interval problems", "merge", [[1, 3], [2, 6], [8, 10]]) == [[1, 6], [8, 10]], "merge intervals")
if FAILS:
    print("\n%d check(s) failed" % len(FAILS))
    sys.exit(1)
print("\nall checks passed")
