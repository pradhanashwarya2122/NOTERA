"""test first run sync
Run: python tests/test_first_run_sync.py   (prints PASS/FAIL lines and exits non-zero on any failure)
"""
import sys as _s
FAILS=[]
import json,os,subprocess,sys,time,shutil,urllib.request,urllib.error
from pathlib import Path
import tempfile
root=Path(tempfile.mkdtemp())
shutil.rmtree(root,ignore_errors=True);root.mkdir(parents=True)
src=Path(__file__).resolve().parent.parent;procs=[]
bare=root/"remote.git";subprocess.run(["git","init","--bare","-b","main",str(bare)],check=True,capture_output=True)
seed=root/"seed";seed.mkdir();run=lambda *a,cwd=seed:subprocess.run(a,cwd=cwd,check=True,capture_output=True)
run("git","init","-b","main");(seed/"README.md").write_text("# notera-notes");run("git","add","README.md");run("git","-c","user.name=x","-c","user.email=x@x","commit","-m","first commit");run("git","remote","add","origin",str(bare));run("git","push","-u","origin","main")
def spawn(n,port):
    (root/n).mkdir();e=os.environ.copy();e.update({"NOTERA_PORT":str(port),"NOTERA_DATA":str(root/n/"notes"),"NOTERA_HOME":str(root/n)})
    procs.append(subprocess.Popen([sys.executable,"app.py"],cwd=str(src),env=e,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
def call(port,path,body=None):
    req=urllib.request.Request("http://127.0.0.1:%d%s"%(port,path),data=None if body is None else json.dumps(body).encode(),headers={"Content-Type":"application/json"},method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req,timeout=60) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read() or b"{}")
def ok(c,m):
    print(("PASS " if c else "FAIL ")+m)
    if not c:FAILS.append(m)
try:
    spawn("A",5161);spawn("B",5162);time.sleep(3)
    ok(call(5161,"/api/onboard")[1]["needed"],"fresh install A is offered the welcome screen")
    now=int(time.time()*1000)
    call(5161,"/api/state",{"pages":[{"id":"n1","title":"Two Sum","parent":None,"tags":["leetcode"],"fav":False,"open":True,"mt":now,"blocks":[{"id":"b","t":"p","h":"hash map"}]}],"trash":[]})
    ok(not call(5161,"/api/onboard")[1]["needed"],"after notes exist the welcome is not shown again")
    c,d=call(5161,"/api/sync/config",{"remote":str(bare)});ok(d.get("status")=="synced","A pushed to README-only remote: %s %s"%(d.get("status"),d.get("msg")))
    o=subprocess.run(["git","--git-dir",str(bare),"show","main:pages.json"],capture_output=True,text=True);ok("Two Sum" in o.stdout,"remote now holds pages.json")
    ok(call(5162,"/api/onboard")[1]["needed"],"laptop B sees the welcome screen")
    c,d=call(5162,"/api/sync/config",{"remote":str(bare)});ok(d.get("status")=="synced","B fetched notes: %s"%d.get("msg"))
    st=call(5162,"/api/state")[1];ok(any(p["title"]=="Two Sum" for p in st["pages"]),"B has A's note: %s"%[p["title"] for p in st["pages"]])
    ok(not call(5162,"/api/onboard")[1]["needed"],"B welcome finished")
finally:
    for p in procs:p.kill()

if FAILS:
    print("\n%d check(s) failed"%len(FAILS));_s.exit(1)
print("\nall checks passed")
