/* Notera standalone mode.
   The same app runs without the laptop server: notes live in this browser (IndexedDB), Python runs in the browser (Pyodide),
   and notes sync with your private GitHub repo straight from the phone.
   On a laptop (localhost or a home-network address) this file does nothing: every request goes to app.py as before. */
(() => {
  'use strict';
  const realFetch = window.fetch.bind(window);
  const ls = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) { } return null; };
  const onLaptop = /^(localhost|127\.|\[::1\]|192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)/.test(location.hostname);
  const local = !onLaptop || ls('nt.local') === '1';
  window.NOTERA_STANDALONE = local;

  /* ---------- the service worker and install button work everywhere ---------- */
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {
    addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => { }));
  }
  let installEv = null;
  addEventListener('beforeinstallprompt', e => {
    e.preventDefault(); installEv = e;
    const menu = document.getElementById('mmenu');
    if (menu && !document.getElementById('instb')) {
      const b = document.createElement('button'); b.className = 'b mi'; b.id = 'instb'; b.innerHTML = '<span class="lbl">Install Notera as an app</span>';
      b.onclick = async () => { menu.classList.remove('show'); installEv.prompt(); await installEv.userChoice; installEv = null; b.remove(); };
      menu.prepend(b);
    }
  });

  if (!local) return;
  document.documentElement.dataset.standalone = '1';

  /* ---------- helpers ---------- */
  const J = (o, status = 200, headers = {}) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json', ...headers } });
  const uid = () => Math.random().toString(36).slice(2, 10);
  const idb = () => idb.p || (idb.p = new Promise((res, rej) => { const r = indexedDB.open('notera', 1); r.onupgradeneeded = () => r.result.createObjectStore('kv'); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); }));
  const kv = async (k, v) => {
    const db = await idb();
    return new Promise((res, rej) => {
      const tx = db.transaction('kv', v === undefined ? 'readonly' : 'readwrite'), st = tx.objectStore('kv');
      const rq = v === undefined ? st.get(k) : v === null ? st.delete(k) : st.put(v, k);
      rq.onsuccess = () => res(rq.result); rq.onerror = () => rej(rq.error);
    });
  };
  const starter = () => { const t = Date.now(); return { pages: [{ id: uid(), title: 'Welcome to Notera', parent: null, tags: [], fav: false, open: true, mt: t, starter: true, starterMt: t, blocks: [
    { id: uid(), t: 'h2', h: 'Your notes live on this device' },
    { id: uid(), t: 'p', h: 'Everything works offline, including running Python. Open the ⋯ menu or tap the sync status at the bottom to connect your private GitHub notes repo, and your laptop and phone stay in step.' }] }], trash: [] }; };
  const newRev = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  let rev = null;
  async function loadState() { let s = await kv('state'); if (!s) { s = starter(); await saveState(s); } return s; }
  async function saveState(s) { await kv('state', s); rev = newRev(); await kv('rev', rev); }
  const getRev = async () => rev || (rev = (await kv('rev')) || (await saveState(await loadState()), rev));
  const me = () => { let m; try { m = JSON.parse(ls('nt.me') || 'null'); } catch (e) { } if (!m) { m = { id: 'NTR-' + uid().slice(0, 6).toUpperCase(), name: 'Me', color: '#2383e2', emoji: '', created: Date.now() / 1000, onboarded: true }; ls('nt.me', JSON.stringify(m)); } return m; };

  /* ---------- merging, the same rule the laptop uses: the newer page wins ---------- */
  const trashIds = s => { const o = {}; (s.trash || []).forEach(t => (t.pages || []).forEach(p => { o[p.id] = t.at || 0; })); return o; };
  function mergeStates(mine, theirs) {
    const mp = new Map((mine.pages || []).map(p => [p.id, p])), tp = new Map((theirs.pages || []).map(p => [p.id, p]));
    const mt = trashIds(mine), tt = trashIds(theirs);
    const order = [...(mine.pages || []).map(p => p.id), ...[...tp.keys()].filter(i => !mp.has(i))], pages = [];
    for (const i of order) {
      const a = mp.get(i), b = tp.get(i);
      if (a && b) pages.push((a.mt || 0) > (b.mt || 0) ? a : b);
      else if (a) { if (!(i in tt && tt[i] >= (a.mt || 0))) pages.push(a); }
      else if (!(i in mt && mt[i] >= (b.mt || 0))) pages.push(b);
    }
    const keep = new Map(pages.map(p => [p.id, p])), trash = [], seen = new Set();
    for (const t of [...(mine.trash || []), ...(theirs.trash || [])]) {
      const root = keep.get(t.root);
      if (seen.has(t.id) || (root && (root.mt || 0) > (t.at || 0))) continue;
      seen.add(t.id); trash.push(t);
    }
    return { ...theirs, ...mine, pages, trash };
  }
  const canon = o => Array.isArray(o) ? o.map(canon) : o && typeof o === 'object' ? Object.fromEntries(Object.keys(o).sort().map(k => [k, canon(o[k])])) : o;
  const norm = s => { const byId = (a, b) => String(a.id).localeCompare(String(b.id)); return JSON.stringify(canon({ ...s, pages: [...(s.pages || [])].sort(byId), trash: [...(s.trash || [])].sort(byId) })); };
  window.__nt = { mergeStates };

  /* ---------- GitHub sync from the phone ---------- */
  let syncInfo = { status: 'off', msg: 'Saved on this device', last: 0 }, syncing = false, syncT = 0;
  const gcfg = () => { try { return JSON.parse(ls('nt.gh') || 'null'); } catch (e) { return null; } };
  const b64 = s => { const u = new TextEncoder().encode(s); let bin = ''; for (let i = 0; i < u.length; i += 0x8000) bin += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(bin); };
  const GH = 'https://api.github.com';
  async function gh(path, cfg, opts = {}) {
    return realFetch(GH + path, { ...opts, headers: { Authorization: 'Bearer ' + cfg.token, 'X-GitHub-Api-Version': '2022-11-28', Accept: 'application/vnd.github+json', ...(opts.headers || {}) } });
  }
  async function ghSync() {
    const cfg = gcfg();
    if (!cfg) { syncInfo = { status: 'off', msg: 'Saved on this device', last: 0 }; return syncInfo; }
    if (syncing) return syncInfo;
    syncing = true; syncInfo = { ...syncInfo, status: 'syncing', msg: 'Syncing' };
    try {
      if (!cfg.branch) {
        const r = await gh('/repos/' + cfg.repo, cfg);
        if (r.status === 401) throw new Error('GitHub rejected the token.');
        if (r.status === 404) throw new Error('Repository not found, or the token cannot see it.');
        if (!r.ok) throw new Error('GitHub answered ' + r.status);
        cfg.branch = (await r.json()).default_branch || 'main'; ls('nt.gh', JSON.stringify(cfg));
      }
      const path = '/repos/' + cfg.repo + '/contents/pages.json';
      let sha = null, remote = null;
      const meta = await gh(path + '?ref=' + encodeURIComponent(cfg.branch), cfg);
      if (meta.status === 200) {
        sha = (await meta.json()).sha;
        const raw = await gh(path + '?ref=' + encodeURIComponent(cfg.branch), cfg, { headers: { Accept: 'application/vnd.github.raw+json' } });
        if (!raw.ok) throw new Error('Could not read the notes file (' + raw.status + ').');
        remote = JSON.parse(await raw.text());
      } else if (meta.status === 401) throw new Error('GitHub rejected the token.');
      else if (meta.status !== 404) throw new Error('GitHub answered ' + meta.status);
      let mine = await loadState();
      /* the untouched welcome page is only for a brand-new phone: it never goes into your real notes */
      if (remote && (remote.pages || []).length) { const kept = mine.pages.filter(p => !(p.starter && p.mt === p.starterMt)); if (kept.length !== mine.pages.length) { mine = { ...mine, pages: kept }; await saveState(mine); } }
      const merged = remote ? mergeStates(mine, remote) : mine;
      if (norm(merged) !== norm(mine)) await saveState(merged);
      if (!remote || norm(merged) !== norm(remote)) {
        const put = await gh(path, cfg, { method: 'PUT', body: JSON.stringify({ message: 'notes from phone ' + new Date().toISOString().slice(0, 16).replace('T', ' '), content: b64(JSON.stringify(merged, null, 2)), branch: cfg.branch, ...(sha ? { sha } : {}) }) });
        if (put.status === 409 || put.status === 422) throw new Error('The repo changed while syncing. Trying again soon.');
        if (!put.ok) throw new Error('Could not upload (' + put.status + ').');
      }
      syncInfo = { status: 'synced', msg: 'Synced with GitHub', last: Date.now() / 1000 };
    } catch (e) {
      syncInfo = { status: navigator.onLine ? 'error' : 'offline', msg: String(e.message || e), last: syncInfo.last };
    }
    syncing = false;
    return syncInfo;
  }
  const kickSync = (ms = 15000) => { if (!gcfg()) return; clearTimeout(syncT); syncT = setTimeout(ghSync, ms); };
  addEventListener('online', () => kickSync(500));
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') kickSync(800); });
  setTimeout(() => kickSync(100), 2500);
  setInterval(() => kickSync(100), 120000);

  function openSyncDialog() {
    let w = document.getElementById('psy');
    if (!w) {
      w = document.createElement('div'); w.id = 'psy'; document.body.append(w);
      const st = document.createElement('style');
      st.textContent = '#psy{position:fixed;inset:0;z-index:90;display:flex;justify-content:center;align-items:flex-start;padding:8vh 14px 0;background:rgba(10,10,10,.4);-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px);opacity:0;visibility:hidden;transition:opacity .16s,visibility .16s}#psy.show{opacity:1;visibility:visible}#psy .icb label{display:flex;flex-direction:column;gap:4px;font:500 12px var(--ui);color:var(--mut)}#psy .icb input{background:var(--bg);border:1px solid var(--ln);border-radius:10px;padding:10px 12px;font:500 15px var(--ui);color:var(--tx);outline:0}#psy .icb small{font:12.5px/1.5 var(--ui);color:var(--mut)}#psy .icb small a{color:var(--y)}#psy .psb{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap}#psy .psb button{padding:9px 16px;border-radius:10px;border:1px solid var(--ln);font:600 13.5px var(--ui);color:var(--tx)}#psy .psb .pri{background:var(--tx);color:var(--bg);border-color:transparent}#psy .pss{font:600 13px var(--ui);color:var(--mut)}';
      document.head.append(st);
    }
    const cfg = gcfg() || { repo: 'pradhanashwarya2122/notera-notes', token: '' };
    w.innerHTML = '<div class="icbox"><div class="ich"><b>Sync with GitHub</b><button id="psx" aria-label="Close">×</button></div><div class="icb">' +
      '<small>Your notes stay on this device and are copied to your <b>private</b> notes repository, the same one your laptop uses. The token is saved only in this browser.</small>' +
      '<label>Notes repository<input id="psr" value="' + cfg.repo.replace(/"/g, '&quot;') + '" placeholder="owner/notera-notes" spellcheck="false" autocapitalize="off"></label>' +
      '<label>Access token<input id="pst" type="password" value="' + (cfg.token || '').replace(/"/g, '&quot;') + '" placeholder="github_pat_..." autocomplete="off" spellcheck="false"></label>' +
      '<small>Create one at <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">github.com/settings/personal-access-tokens</a>: choose <b>Only select repositories</b> → your notes repo, then <b>Repository permissions → Contents → Read and write</b>.</small>' +
      '<div class="pss" id="pss">' + (syncInfo.status === 'off' ? 'Not connected yet' : syncInfo.msg) + '</div>' +
      '<div class="psb"><button id="psd">Disconnect</button><button class="pri" id="psg">Save and sync</button></div></div></div>';
    const close = () => w.classList.remove('show');
    w.querySelector('#psx').onclick = close; w.onmousedown = e => { if (e.target === w) close(); };
    w.querySelector('#psd').onclick = () => { ls('nt.gh', null); syncInfo = { status: 'off', msg: 'Saved on this device', last: 0 }; close(); document.getElementById('sv') && (document.getElementById('sv').textContent = 'Saved on this device'); };
    w.querySelector('#psg').onclick = async () => {
      const repo = w.querySelector('#psr').value.trim().replace(/^https:\/\/github\.com\//, '').replace(/\.git$/, ''), token = w.querySelector('#pst').value.trim();
      if (!/^[\w.-]+\/[\w.-]+$/.test(repo) || !token) { w.querySelector('#pss').textContent = 'Enter the repository as owner/name and paste the token.'; return; }
      ls('nt.gh', JSON.stringify({ repo, token })); w.querySelector('#pss').textContent = 'Syncing…';
      const r = await ghSync(); w.querySelector('#pss').textContent = r.status === 'synced' ? 'Synced. Your notes are now on GitHub.' : r.msg;
      if (r.status === 'synced') setTimeout(close, 900);
    };
    w.classList.add('show');
  }

  /* ---------- Python in the browser ---------- */
  const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/';
  const workerSrc = `importScripts('${PYODIDE}pyodide.js');let py=null;
onmessage=async e=>{const {id,code,stdin}=e.data;
 try{if(!py)py=await loadPyodide({indexURL:'${PYODIDE}'});
  let out='',err='';py.setStdout({batched:s=>{out+=s+'\\n'}});py.setStderr({batched:s=>{err+=s+'\\n'}});
  const lines=String(stdin||'').split('\\n');let i=0;py.setStdin({stdin:()=>i<lines.length?lines[i++]:undefined});
  const t0=performance.now();let ok=true;
  try{const g=py.globals.get('dict')();await py.runPythonAsync(code,{globals:g});g.destroy()}catch(ex){ok=false;let m=String(ex&&ex.message||ex);const k=m.indexOf('  File "<exec>"');if(k>0)m='Traceback (most recent call last):\\n'+m.slice(k);err+=m}
  postMessage({id,ok,out,err,ms:Math.round(performance.now()-t0)})}
 catch(ex){postMessage({id,ok:false,out:'',err:'Could not load Python: '+String(ex&&ex.message||ex)+'. It needs an internet connection the first time.',ms:0})}};`;
  let worker = null, seq = 0;
  function runPython(code, stdin) {
    return new Promise(resolve => {
      if (!worker) worker = new Worker(URL.createObjectURL(new Blob([workerSrc], { type: 'text/javascript' })));
      const id = ++seq, w = worker;
      const timer = setTimeout(() => { w.terminate(); if (worker === w) worker = null; resolve({ ok: false, output: 'Timed out after 15 seconds.' }); }, 20000);
      w.onmessage = e => {
        if (e.data.id !== id) return; clearTimeout(timer);
        const { ok, out, err, ms } = e.data, text = ok ? out : (out + err);
        resolve({ ok, output: (text || '').trim() || '(no output)', ms });
      };
      w.postMessage({ id, code, stdin });
    });
  }

  /* ---------- the little API the app talks to ---------- */
  const no = (msg) => J({ ok: false, error: msg }, 400);
  async function handle(path, method, body) {
    switch (true) {
      case path === '/api/state' && method === 'GET': { const s = await loadState(); await getRev(); return J({ ...s, _rev: rev }); }
      case path === '/api/state' && method === 'POST': {
        const s = body; if (!s || !Array.isArray(s.pages)) return no('Not a notebook.');
        delete s._rev; await saveState(s); kickSync(); return J({ ok: true, rev });
      }
      case path === '/api/rev': await getRev(); return J({ rev, sync: syncInfo, net: { joined: false, peers: 0, status: 'off', messages: 0 } });
      case path === '/api/me': { if (method === 'POST') { const m = { ...me(), ...(body || {}) }; ls('nt.me', JSON.stringify(m)); } return J(me()); }
      case path === '/api/net': return J({ hosting: false, relay: '', joined: false, key: null, keyexp: 0, members: [], messages: [], lan: '', lans: [], status: 'off', identity: me() });
      case path === '/api/onboard': return J({ needed: false, git: false, remote: '' });
      case path === '/api/sync/now': { if (!gcfg()) { openSyncDialog(); return J({ status: 'syncing', msg: 'Set up sync', last: 0 }); } return J(await ghSync()); }
      case path === '/api/sync/config': openSyncDialog(); return J({ ok: true });
      case path === '/api/run': { const r = await runPython(String(body && body.code || ''), body && body.stdin); return J(r); }
      case path === '/api/export-notes/download': {
        const s = await loadState(); return new Response(JSON.stringify(s, null, 2), { status: 200, headers: { 'content-type': 'application/json', 'Content-Disposition': 'attachment; filename="notera-notes-' + new Date().toISOString().slice(0, 10) + '.json"' } });
      }
      case path === '/api/backups' || path === '/api/full-backup/list': return J([]);
      case path === '/api/ai/config': return J({ configured: false, model: '', provider: 'anthropic', providers: [], base: '' });
      case path === '/api/ai': return J({ ok: false, error: 'AI help needs the laptop app for now. Everything else works here.' }, 400);
      case path === '/api/lc/fetch': return J({ ok: false, error: 'Fetching from LeetCode needs the laptop app. You can still fill the card in by hand.' }, 400);
      default: return J({ ok: false, error: 'This is only available in the laptop app.' }, 404);
    }
  }
  window.fetch = async function (input, init) {
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    if (!url.pathname.startsWith('/api/')) return realFetch(input, init);
    const method = ((init && init.method) || (typeof input !== 'string' && input.method) || 'GET').toUpperCase();
    let body = null;
    if (init && typeof init.body === 'string') { try { body = JSON.parse(init.body); } catch (e) { } }
    try { return await handle(url.pathname, method, body); } catch (e) { return J({ ok: false, error: String(e) }, 500); }
  };
})();
