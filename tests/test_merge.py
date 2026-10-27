"""test merge
Run: python tests/test_merge.py   (prints PASS/FAIL lines and exits non-zero on any failure)
"""
import sys as _s
FAILS=[]
import sys,types
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import app
P=lambda i,mt,t="x":{"id":i,"title":t,"mt":mt,"blocks":[]}
# 1 newer edit wins, both directions
a={"pages":[P("a",5,"A-new"),P("b",1,"B-old")],"trash":[]}
b={"pages":[P("a",2,"A-old"),P("b",9,"B-new"),P("c",3,"C-only-remote")],"trash":[]}
m=app.merge_states(a,b);t={p["id"]:p["title"] for p in m["pages"]}
assert t=={"a":"A-new","b":"B-new","c":"C-only-remote"},t
# 2 stale 1-page client must not delete anything
disk={"pages":[P("a",5),P("b",5),P("c",5)],"trash":[]}
stale={"pages":[P("z",0)],"trash":[]}
m=app.merge_states(stale,disk);assert {p["id"] for p in m["pages"]}=={"a","b","c","z"}
# 3 deletion respected when trash is newer than last edit, resurrected if edited after
tr={"id":"t1","root":"b","at":100,"pages":[P("b",50)]}
del_side={"pages":[P("a",5)],"trash":[tr]};other={"pages":[P("a",5),P("b",50)],"trash":[]}
m=app.merge_states(del_side,other);assert {p["id"] for p in m["pages"]}=={"a"},m
other2={"pages":[P("a",5),P("b",200)],"trash":[]}
m=app.merge_states(del_side,other2);assert {p["id"] for p in m["pages"]}=={"a","b"}
print("merge ok")

if FAILS:
    print("\n%d check(s) failed"%len(FAILS));_s.exit(1)
print("\nall checks passed")
