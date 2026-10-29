/* Premium interaction layer. Pure enhancement: if anything here fails the app works exactly as before. */
(()=>{
const calm=()=>matchMedia('(prefers-reduced-motion:reduce)').matches;
const $=s=>document.querySelector(s);

/* ---------- confetti and sparkles ---------- */
let cv,cx,parts=[],raf=0;
function ensureCanvas(){if(cv)return;cv=document.createElement('canvas');cv.id='confetti';document.body.append(cv);cx=cv.getContext('2d');const fit=()=>{cv.width=innerWidth*devicePixelRatio;cv.height=innerHeight*devicePixelRatio;cx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0)};fit();addEventListener('resize',fit)}
function palette(){const cs=getComputedStyle(document.documentElement);return[1,2,3,4,5,6].map(i=>cs.getPropertyValue('--f'+i).trim()||'#f59e0b')}
function step(){cx.clearRect(0,0,innerWidth,innerHeight);parts=parts.filter(p=>p.life>0);
 parts.forEach(p=>{p.vy+=p.g;p.vx*=.992;p.x+=p.vx;p.y+=p.vy;p.r+=p.vr;p.life-=1;cx.save();cx.globalAlpha=Math.min(1,p.life/30);cx.translate(p.x,p.y);cx.rotate(p.r);cx.fillStyle=p.c;
  if(p.s==='star'){cx.beginPath();for(let i=0;i<5;i++){cx.lineTo(Math.cos((i*72-90)*Math.PI/180)*p.z,Math.sin((i*72-90)*Math.PI/180)*p.z);cx.lineTo(Math.cos((i*72-54)*Math.PI/180)*p.z*.45,Math.sin((i*72-54)*Math.PI/180)*p.z*.45)}cx.closePath();cx.fill()}
  else cx.fillRect(-p.z/2,-p.z/3,p.z,p.z*.62);cx.restore()});
 if(parts.length)raf=requestAnimationFrame(step);else{cx.clearRect(0,0,innerWidth,innerHeight);raf=0}}
window.celebrate=function(x,y,small){if(calm())return;ensureCanvas();const cols=palette(),n=small?16:90;x=x==null?innerWidth/2:x;y=y==null?innerHeight*.35:y;
 for(let i=0;i<n;i++){const a=Math.random()*Math.PI*2,sp=(small?2.5:5)+Math.random()*(small?3:7);parts.push({x,y,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp-(small?2:4),g:.16,r:Math.random()*6,vr:(Math.random()-.5)*.3,z:(small?5:7)+Math.random()*6,c:cols[i%cols.length],s:Math.random()<.35?'star':'rect',life:(small?40:95)+Math.random()*30})}
 if(!raf)raf=requestAnimationFrame(step)};
/* ticking a to-do, finishing a problem and logging a clean review all get a little moment */
document.addEventListener('change',e=>{const t=e.target;if(!t||!t.matches)return;
 if(t.matches('.blk[data-t=todo] input[type=checkbox],.doc input.ck')&&t.checked){const r=t.getBoundingClientRect();celebrate(r.left+r.width/2,r.top+r.height/2,true);try{navigator.vibrate&&navigator.vibrate(8)}catch(x){}}
 if(t.matches('.lcst')&&['Solved independently','Mastered'].includes(t.value)){const r=t.getBoundingClientRect();celebrate(r.left+r.width/2,r.top)}},true);
(function wrapReview(){if(typeof window.logReview!=='function')return setTimeout(wrapReview,300);const o=window.logReview;window.logReview=function(p,out){o(p,out);if(out==='indep')celebrate()}})();

/* ---------- numbers count up ---------- */
const ease=t=>1-Math.pow(1-t,4);
function countUp(el){if(el.dataset.cu||calm())return;const m=/^([\d,]+)(%?)$/.exec(el.textContent.trim());if(!m)return;const end=+m[1].replace(/,/g,''),suf=m[2];if(!end)return;el.dataset.cu='1';const t0=performance.now(),d=Math.min(1100,500+end*3);
 const tick=now=>{const k=Math.min(1,(now-t0)/d),v=Math.round(end*ease(k));el.textContent=v.toLocaleString()+suf;if(k<1)requestAnimationFrame(tick)};requestAnimationFrame(tick)}

/* ---------- pointer spotlight on cards ---------- */
document.addEventListener('pointermove',e=>{const c=e.target.closest&&e.target.closest('.hc,.dt,.hlibt,.rdn');if(!c)return;const r=c.getBoundingClientRect();c.style.setProperty('--mx',(e.clientX-r.left)+'px');c.style.setProperty('--my',(e.clientY-r.top)+'px')},{passive:true});

/* ---------- large title that becomes a bar ---------- */
const bar=document.createElement('div');bar.id='ctb';document.body.append(bar);let io=null;
function watchTitle(){const t=$('#ti'),main=$('#main');if(io){io.disconnect();io=null}bar.classList.remove('on');if(!t||!main||typeof page!=='function')return;
 let title='';try{title=page().title||'Untitled'}catch(e){}bar.textContent=title;
 io=new IntersectionObserver(([en])=>{bar.classList.toggle('on',!en.isIntersecting&&en.boundingClientRect.top<0)},{root:main,threshold:0,rootMargin:'-8px 0px 0px 0px'});io.observe(t);
 t.addEventListener('input',()=>{bar.textContent=t.value||'Untitled'})}

/* ---------- entrances and housekeeping after every render ---------- */
let lastKey='';
function afterRender(){const ed=$('#ed');if(!ed)return;
 const key=(typeof homeOn!=='undefined'&&homeOn?'h:'+homeMode:'p:'+cur);
 const bl=$('#bl');
 if(key!==lastKey){lastKey=key;
  if(bl&&!calm()){[...bl.children].slice(0,16).forEach((c,i)=>c.style.setProperty('--i',i))}
  if(!calm()){document.body.classList.add('entering');clearTimeout(afterRender.t);afterRender.t=setTimeout(()=>document.body.classList.remove('entering'),1400)}
  ed.querySelectorAll('.hc').forEach((c,i)=>c.style.setProperty('--i',i));ed.querySelectorAll('.rdr').forEach((c,i)=>c.style.setProperty('--i',i%40));
  ed.querySelectorAll('.hstats b,.rdp b,.dt b,.rdc header span').forEach(countUp)}
 watchTitle()}
const ed=$('#ed');if(ed){new MutationObserver(afterRender).observe(ed,{childList:true})}
afterRender();

/* ---------- the sidebar highlight glides between pages ---------- */
(()=>{const tree=$('#tree');if(!tree)return;let prev=null;
 const place=()=>{const on=tree.querySelector('.pg.on');tree.classList.toggle('haspill',!!on);if(!on){prev=null;return}
  const y=on.offsetTop,h=on.offsetHeight,pill=document.createElement('div');pill.className='sbpill';
  pill.style.cssText='top:'+(prev&&!calm()?prev.y:y)+'px;height:'+(prev&&!calm()?prev.h:h)+'px';tree.prepend(pill);
  if(prev&&!calm())requestAnimationFrame(()=>requestAnimationFrame(()=>{pill.style.top=y+'px';pill.style.height=h+'px'}));prev={y,h}};
 new MutationObserver(m=>{if(m.every(x=>[...x.addedNodes].every(n=>n.className==='sbpill')&&x.removedNodes.length===0))return;place()}).observe(tree,{childList:true});place()})();

/* ---------- themes cross-fade ---------- */
(function wrapTheme(){if(typeof window.applyTheme!=='function')return setTimeout(wrapTheme,300);const o=window.applyTheme;let first=true;window.applyTheme=function(){if(!first&&!calm()){document.body.classList.add('themeswap');setTimeout(()=>document.body.classList.remove('themeswap'),550)}first=false;return o.apply(this,arguments)}})();
})();
