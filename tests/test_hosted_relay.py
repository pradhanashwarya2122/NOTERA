"""test hosted relay
Run: python tests/test_hosted_relay.py   (prints PASS/FAIL lines and exits non-zero on any failure)
"""
import sys as _s
FAILS=[]
import json,os,subprocess,sys,time,shutil,urllib.request,urllib.error
from pathlib import Path
import tempfile
root=Path(tempfile.mkdtemp())
shutil.rmtree(root,ignore_errors=True);root.mkdir(parents=True)
src=Path(__file__).resolve().parent.parent;procs=[]
for n,port in (("A",5161),("B",5162)):
    (root/n).mkdir();e=os.environ.copy();e.update({"NOTERA_PORT":str(port),"NOTERA_DATA":str(root/n/"notes"),"NOTERA_HOME":str(root/n),"RELAY_DATA":str(root/"relay.json")})
    procs.append(subprocess.Popen([sys.executable,"app.py"],cwd=str(src),env=e,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
time.sleep(3)
def call(port,path,body=None):
    req=urllib.request.Request("http://127.0.0.1:%d%s"%(port,path),data=None if body is None else json.dumps(body).encode(),headers={"Content-Type":"application/json"},method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read() or b"{}")
def ok(c,m):
    print(("PASS " if c else "FAIL ")+m)
    if not c:FAILS.append(m)
try:
    c,d=call(5161,"/api/net/host",{});ok(c==200 and d["hosting"] and d["lan"].endswith(":5252"),"A hosts relay, LAN address %s"%d["lan"])
    c,d=call(5161,"/api/net/create",{});key=d.get("key");ok(c==200 and key,"A created key via its own relay")
    call(5162,"/api/net/relay",{"relay":"http://127.0.0.1:5252"})
    c,d=call(5162,"/api/net/join",{"key":key});ok(c==200 and len(d["members"])==2,"B joined through A's hosted relay")
finally:
    for p in procs:p.kill()

if FAILS:
    print("\n%d check(s) failed"%len(FAILS));_s.exit(1)
print("\nall checks passed")
