"""test network
Run: python tests/test_network.py   (prints PASS/FAIL lines and exits non-zero on any failure)
"""
import sys as _s
FAILS=[]
import json,os,subprocess,sys,time,shutil,urllib.request,urllib.error
from pathlib import Path
import tempfile
root=Path(tempfile.mkdtemp())
shutil.rmtree(root,ignore_errors=True);root.mkdir(parents=True)
src=Path(__file__).resolve().parent.parent
procs=[]
def spawn(args,env):
    e=os.environ.copy();e.update(env);procs.append(subprocess.Popen([sys.executable]+args,cwd=str(src),env=e,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
spawn(["relay.py"],{"PORT":"5252","RELAY_DATA":str(root/"relay.json")})
for n,port in (("A",5161),("B",5162)):
    (root/n).mkdir()
    spawn(["app.py"],{"NOTERA_PORT":str(port),"NOTERA_DATA":str(root/n/"notes"),"NOTERA_HOME":str(root/n)})
time.sleep(3)
def call(port,path,body=None):
    req=urllib.request.Request("http://127.0.0.1:%d%s"%(port,path),data=None if body is None else json.dumps(body).encode(),headers={"Content-Type":"application/json"},method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read() or b"{}")
A,B=5161,5162
def ok(c,m):
    print(("PASS " if c else "FAIL ")+m)
    if not c:FAILS.append(m)
try:
    ia=call(A,"/api/me")[1];ib=call(B,"/api/me")[1]
    ok(ia["id"].startswith("NTR-") and ia["id"]!=ib["id"],"identities created: %s vs %s"%(ia["id"],ib["id"]))
    call(B,"/api/me",{"name":"Riya"});call(A,"/api/me",{"name":"Ashwarya"})
    for p in (A,B):call(p,"/api/net/relay",{"relay":"http://127.0.0.1:5252"})
    c,d=call(A,"/api/net/create",{});key=d.get("key");ok(c==200 and key and len(key)==6 and key.isdigit(),"A created 6-digit key %s"%key)
    c,d=call(B,"/api/net/join",{"key":"000000"});ok(c==400,"wrong key rejected: %s"%d.get("error"))
    c,d=call(A,"/api/net/join",{"key":key});ok(c==409 or c==400,"creator cannot join own key")
    c,d=call(B,"/api/net/join",{"key":key});ok(c==200 and d["joined"],"B joined with key")
    c,d=call(B,"/api/net/join",{"key":key});ok(c!=200,"key is single use / already joined")
    now=int(time.time()*1000)
    page={"id":"p1","title":"Shared note","parent":None,"tags":[],"fav":False,"open":True,"share":True,"mt":now,"blocks":[{"id":"b1","t":"p","h":"hello from A"}]}
    secret={"id":"p2","title":"Private note","parent":None,"tags":[],"fav":False,"open":True,"mt":now,"blocks":[{"id":"b2","t":"p","h":"secret"}]}
    call(A,"/api/state",{"pages":[page,secret],"trash":[]})
    time.sleep(9)
    sb=call(B,"/api/state")[1];titles={p["id"]:p["title"] for p in sb["pages"]}
    ok("p1" in titles and "p2" not in titles,"B received only the shared page: %s"%titles)
    # B edits, A gets it
    pb=[p for p in sb["pages"] if p["id"]=="p1"][0];pb["blocks"][0]["h"]="edited by B";pb["mt"]=int(time.time()*1000)
    rev=sb.get("_rev");call(B,"/api/state",{"pages":sb["pages"],"trash":[],"_rev":rev})
    time.sleep(9)
    sa=call(A,"/api/state")[1];pa=[p for p in sa["pages"] if p["id"]=="p1"][0]
    ok(pa["blocks"][0]["h"]=="edited by B","A received B's edit")
    ok(any(p["id"]=="p2" for p in sa["pages"]),"A still has its private page")
    call(B,"/api/net/message",{"text":"Hello Ashwarya!"});time.sleep(4)
    na=call(A,"/api/net")[1];txt=[m["text"] for m in na["messages"]]
    ok(any("Hello Ashwarya" in t for t in txt) and any("joined" in t for t in txt),"messages: %s"%txt)
    ok(len(na["members"])==2 and {m["name"] for m in na["members"]}=={"Ashwarya","Riya"},"members: %s"%[(m["name"],m["id"]) for m in na["members"]])
    # stop sharing
    c,d=call(A,"/api/net/leave",{});ok(d["joined"] is False,"A stopped sharing")
    sa=call(A,"/api/state")[1];ok(not any(p.get("share") for p in sa["pages"]) and any(p["id"]=="p1" for p in sa["pages"]),"A kept its copy, now unshared")
    time.sleep(4);nb=call(B,"/api/net")[1];ok(len(nb["members"])==1,"B sees A left: %s"%[m["name"] for m in nb["members"]])
finally:
    for p in procs:p.kill()

if FAILS:
    print("\n%d check(s) failed"%len(FAILS));_s.exit(1)
print("\nall checks passed")
