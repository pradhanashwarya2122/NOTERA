/* Usability layer: undo toasts, clear sync status, plain-language errors, accessibility, phone bar, speed check. */
(()=>{
const $=s=>document.querySelector(s);

/* ---------- toast with an optional action ---------- */
window.toast=function(t,label,fn){const e=$('#toast');if(!e)return;
 e.textContent='';e.append(document.createTextNode(t));
 if(label&&fn){const b=document.createElement('button');b.className='tact';b.textContent=label;b.onclick=()=>{e.className='';fn()};e.append(b)}
 e.className='s'+(label?' act':'');clearTimeout(window.toast.t);window.toast.t=setTimeout(()=>e.className='',label?6500:1800)};
const tt=$('#toast');if(tt){tt.setAttribute('role','status');tt.setAttribute('aria-live','polite')}

/* ---------- deleting is undoable instead of asking first ---------- */
const hasKids=id=>S.pages.some(x=>x.parent===id);
const delOrig=window.delPage;
window.delPage=function(id,quiet){const p=P(id);if(!p)return;
 if(!quiet&&(p.folder||hasKids(id)))return delOrig(id,quiet);
 const name=p.title||'Untitled';delOrig(id,true);
 toast('Moved "'+name+'" to Trash','Undo',()=>undo())};

/* ---------- sync wording ---------- */
SYNC_TXT.synced='Synced to GitHub';SYNC_TXT.off='Saved on this device';SYNC_TXT.error='Sync problem. Click to retry';SYNC_TXT.offline='Offline. Will sync later';
const ssOrig=window.setSaveStatus;
window.setSaveStatus=function(t,err){if(t==='Saved')t=(typeof syncInfo!=='undefined'&&syncInfo.status==='synced')?SYNC_TXT.synced:SYNC_TXT.off;
 if(err){t='Not saved. Notera is not responding. Click to retry';const e=$('#sv');if(e){e.setAttribute('role','alert');e.title='Your last edit is kept in this window. Check that the launcher is still open.'}}
 ssOrig(t,err)};
const sv=$('#sv');if(sv){sv.setAttribute('role','status');sv.setAttribute('aria-live','polite');sv.tabIndex=0;sv.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();sv.click()}}}

/* ---------- plain-language errors ---------- */
let lastErr=0;const say=m=>{if(Date.now()-lastErr>8000){lastErr=Date.now();toast(m)}};
const f0=window.fetch.bind(window);
window.fetch=async function(u,o){const url=typeof u==='string'?u:(u&&u.url)||'';
 try{const r=await f0(u,o);
  if(!r.ok&&/\/api\//.test(url)){
   if(/\/api\/ai/.test(url))say(r.status===401||r.status===403?'The AI key was not accepted. Open AI settings and check it.':r.status===429?'The AI service says you are going too fast or are out of quota. Wait a minute or try another model.':'The AI could not answer. Check your key and connection, then try again.');
   else if(/\/api\/lc/.test(url))say('Could not read that LeetCode link. Check the address, or paste the problem in by hand.');
   else if(/\/api\/sync/.test(url))say('Sync did not go through. Your notes are safe on this device and it will try again.')}
  return r}
 catch(err){if(/\/api\//.test(url)&&!/\/api\/(rev|net|state)/.test(url))say('Notera could not reach its server. If you closed the launcher window, open it again.');throw err}};

/* ---------- other device updates: say which page and where the old copy is ---------- */
const t0=window.toast;
window.toast=function(t,l,f){if(t==='Updated from your other laptop')return t0('Updated from another device. The newest edit wins; older copies are in History.','See history',()=>{const b=$('#hib');b&&b.click()});return t0(t,l,f)};

/* ---------- "last edited" and a hint on an empty page ---------- */
const ago=ms=>{const s=(Date.now()-ms)/1000;if(s<60)return 'just now';if(s<3600)return Math.round(s/60)+' min ago';if(s<86400)return Math.round(s/3600)+' h ago';return new Date(ms).toLocaleDateString()};
function decorate(){const ti=$('#ti');if(!ti||typeof page!=='function'||(typeof homeOn!=='undefined'&&homeOn))return;const p=page();if(!p)return;
 if(!document.querySelector('.lastedit')&&p.mt){const d=document.createElement('div');d.className='lastedit';d.textContent='Edited '+ago(p.mt);ti.after(d)}
 const bl=$('#bl');if(bl&&!p.folder&&p.blocks&&p.blocks.length===1&&!p.blocks[0].h&&!document.querySelector('.emptyhint')){const h=document.createElement('div');h.className='emptyhint';h.innerHTML='Start typing, or press <kbd>/</kbd> for headings, code, flashcards and more. <kbd>Ctrl P</kbd> finds any page. <kbd>?</kbd> shows every shortcut.';bl.before(h)}}
/* ---------- accessibility: names for icon-only controls ---------- */
function label(){document.querySelectorAll('button:not([aria-label])').forEach(b=>{if(b.textContent.trim().length>1)return;const t=b.title||b.dataset.c||b.id;if(t)b.setAttribute('aria-label',t)});
 document.querySelectorAll('input:not([aria-label]):not([type=checkbox])').forEach(i=>{const t=i.placeholder||i.title;if(t)i.setAttribute('aria-label',t)})}
const ed=$('#ed');if(ed)new MutationObserver(()=>{clearTimeout(decorate.t);decorate.t=setTimeout(()=>{decorate();label()},80)}).observe(ed,{childList:true});
setTimeout(()=>{decorate();label()},300);

/* ---------- the "..." menu: everyday items first, rare ones folded ---------- */
(()=>{const m=$('#mmenu');if(!m)return;const rare=['hib','recb','tsb','prb','ms'].map(i=>document.getElementById(i)).filter(Boolean);if(!rare.length)return;
 const d=document.createElement('details');d.className='mrare';d.innerHTML='<summary>More tools</summary>';rare.forEach(b=>d.append(b));m.append(d)})();

/* ---------- text size ---------- */
const sizes=[0.9,1,1.15,1.3];let si=1;try{si=Math.max(0,Math.min(3,+localStorage.getItem('nt.ts')||1))}catch(e){}
const applySize=()=>{document.documentElement.style.setProperty('--tz',sizes[si]);const b=$('#tsz');if(b)b.querySelector('.lbl').textContent='Text size: '+Math.round(sizes[si]*100)+'%'};
(()=>{const m=$('#mmenu');if(!m)return;const b=document.createElement('button');b.className='b mi';b.id='tsz';b.title='Make the text bigger or smaller';b.innerHTML='<span class="lbl"></span>';
 b.onclick=e=>{e.stopPropagation();si=(si+1)%sizes.length;try{localStorage.setItem('nt.ts',si)}catch(x){}applySize()};m.insertBefore(b,m.firstChild);applySize()})();

/* ---------- speed check ---------- */
function speed(){const main=$('#main');if(!main)return;toast('Measuring speed...');
 const t=performance.now();try{render()}catch(e){}const rt=performance.now()-t;
 let n=0,worst=0,last=performance.now();const start=last,top0=main.scrollTop;
 (function f(){const now=performance.now();worst=Math.max(worst,now-last);last=now;n++;main.scrollTop+=30;
  if(now-start<1200)requestAnimationFrame(f);else{main.scrollTop=top0;const fps=Math.round(n/((now-start)/1000));
   toast('Speed: '+fps+' fps scrolling, longest frame '+Math.round(worst)+' ms, page draw '+Math.round(rt)+' ms. '+(fps>=50&&worst<60?'Smooth.':'Slow. Try a smaller page or another browser.'))}})()}
window.ntSpeed=speed;
(()=>{const m=$('#mmenu'),d=document.querySelector('.mrare');if(!m)return;const b=document.createElement('button');b.className='b mi';b.id='spb';b.title='Measure how smooth scrolling and drawing feel on this device';b.innerHTML='<span class="lbl">Speed check</span>';b.onclick=()=>{m.classList.remove('show');speed()};(d||m).append(b)})();

/* ---------- phone bottom bar ---------- */
(()=>{const bar=document.createElement('nav');bar.id='bnav';bar.setAttribute('aria-label','Main');
 const items=[['Home','homeb'],['Find','qsb'],['New','np'],['Review','revb']];
 bar.innerHTML=items.map(([l,id])=>'<button data-t="'+id+'">'+l+'</button>').join('')+'<button data-t="menu">Pages</button>';
 bar.onclick=e=>{const b=e.target.closest('button');if(!b)return;const id=b.dataset.t;if(id==='menu'){const s=$('#sctoggle');if(typeof setSidebar==='function')setSidebar(false);else s&&s.click()}else{const x=document.getElementById(id);x&&x.click()}};
 document.body.append(bar)})();

/* ---------- contrast: muted text and accents reach 4.5:1 in every theme ---------- */
(()=>{if(typeof THEMES==='undefined')return;
 const hx=c=>{c=String(c);if(!/^#[0-9a-f]{6}$/i.test(c))return null;return[1,3,5].map(i=>parseInt(c.slice(i,i+2),16))};
 const lum=([r,g,b])=>[r,g,b].map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
 const cr=(a,b)=>{const x=lum(a),y=lum(b);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
 const hex=a=>'#'+a.map(v=>Math.round(v).toString(16).padStart(2,'0')).join('');
 let fixed=0;
 for(const k in THEMES){const t=THEMES[k],bg=hx(t.bg),tx=hx(t.tx);if(!bg||!tx)continue;
  for(const key of['mut','y']){let c=hx(t[key]);if(!c||cr(c,bg)>=4.5)continue;
   for(let i=1;i<=20&&cr(c,bg)<4.5;i++)c=c.map((v,j)=>v+(tx[j]-v)*.08);
   t[key]=hex(c);if(key==='y'){t.ac=t.y}fixed++}}
 if(fixed&&typeof applyTheme==='function')try{applyTheme(localStorage.getItem('nt.theme')||'light',localStorage.getItem('nt.accent')||undefined)}catch(e){}})();
})();
