/* Text-first UI probe: report what the web client shows without a screenshot.

   Loads the web client headlessly, optionally runs a few steps, then prints a
   compact text readout: client status, errors, headings, visible controls,
   visible text, and layout defects (overflow, clipping, overlaps, offscreen).
   Pixels are only produced on request, saved to disk, and diffed locally so an
   agent learns *whether and where* something changed before paying to look.

   Usage (from "hollow star scripts"):
     node tools/ui-probe.cjs                               # title screen
     node tools/ui-probe.cjs --do "click:Simulation Mode"  # steps, in order
     node tools/ui-probe.cjs --viewport phone --text 1500
     node tools/ui-probe.cjs --select ".mode-menu-card"    # boxes + styles
     node tools/ui-probe.cjs --baseline menu               # save reference png
     node tools/ui-probe.cjs --diff menu                   # pixel diff vs it
     node tools/ui-probe.cjs --shot menu --crop 0,0,600,400 # small png to look at

   Steps: click:<button text> | key:<Key> | wait:<ms> | nav:<screen> |
          hover:<button text> | type:<text> | eval:<js expression>
   Server: HSR_UI_URL, else a live host on 127.0.0.1:8765, else a static
   server over web/ (host calls then fail; menus still render).

   --mock  Fakes /api/host with a small SANDBOX fixture (one party member, one
   room, one scene) and drives Simulation Mode -> Continue -> load the fake
   run, landing in phase 'ready' before your --do steps run. Use this in a
   container where the real Python engine can't boot (location-guard fails
   closed off the real desktop -- see repo README) but you still need a real
   gameplay screen, not just the title/menus. `nav:<screen>` then reaches any
   of the 10 tabs directly. Override the fixture with --view <path-to-json>
   (same shape as the `view` object tests/ui-browser-check.cjs builds).

   Output files: .local/ui-probe/ (disposable run state). Exit 1 on page errors
   or layout defects, so it can gate a change without anyone looking. */
const {chromium}=require('playwright');
const fs=require('node:fs');const path=require('node:path');const http=require('node:http');
const root=path.resolve(__dirname,'..');const webRoot=path.join(root,'web');
const out=path.join(root,'.local','ui-probe');

function parseArgs(argv){
  const a={do:[],select:[],text:800,viewport:'desktop'};
  for(let i=0;i<argv.length;i++){const k=argv[i],v=argv[i+1];
    if(k==='--do'){a.do.push(v);i++;}else if(k==='--select'){a.select.push(v);i++;}
    else if(['--text','--viewport','--baseline','--diff','--shot','--crop','--url','--view'].includes(k)){a[k.slice(2)]=v;i++;}
    else if(k==='--full')a.full=true;else if(k==='--mock')a.mock=true;else if(k==='--help'||k==='-h')a.help=true;
    else throw new Error(`unknown arg ${k}`);}
  return a;}

// The same shape tests/ui-browser-check.cjs builds by hand; kept here so a
// bare `--mock` works without also requiring a fixture file on disk.
function defaultMockView(root){
  const preview=JSON.parse(fs.readFileSync(path.join(root,'web','item-preview.json'),'utf8'));
  return {schema:'hollow-star-public-view-1',run_id:'ui-probe-fixture',mode:'SANDBOX',status:'active',
    party:[{id:'p0',name:'Probe adventurer',hp:32,max_hp:40,armor_class:16,equipment:preview.equipment}],
    room:{id:'1:1',name:'Public probe room',description:'A public room description.',law:'Quiet',terrain:'Stone floor',
      exits:{north:{id:'1:2',name:'North hall'}},visible_tells:['Visible lamp'],objects:{},npcs:{}},
    scene:{floor_id:'town',phase:'exploration',progress:0.4,background_id:'town-square',direction:'right',
      visible_entities:[{id:'npc1',name:'Old Man',role:'resident'}]},
    opposition:[],inventory:[],imprints:{},progression:{gold:24},available_actions:[{id:'inspect',label:'Inspect'}],recent_receipts:[]};}

async function installMock(page,view){
  const run={run_id:view.run_id,mode:'SANDBOX',context:{host_mode:'SANDBOX'},status:'active'};
  await page.route('**/api/health',route=>route.fulfill({json:{ok:true,result:{state:'booted'}}}));
  await page.route('**/api/host',route=>{
    const request=route.request().postDataJSON();let payload;
    if(request.command==='health')payload={ok:true};
    else if(request.command==='list_runs')payload={ok:true,result:{runs:[run]}};
    else if(request.command==='inspect_run')payload={ok:true,result:{run}};
    else if(['readout','design_turn'].includes(request.command))payload={ok:true,v:'hollow-star-transfer-capsule-1',view,receipt:{message:'Probe fixture receipt'},run:view.run_id};
    else payload={ok:true,result:{}};
    return route.fulfill({json:payload});});}

async function bootToReady(page){
  await page.getByRole('button',{name:'Simulation Mode',exact:true}).waitFor();
  await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();
  await page.locator('[data-action="continue:SANDBOX"]').click();
  await page.getByRole('heading',{name:'Resume the Simulation'}).waitFor();
  await page.locator('[data-action^="load:"]').first().click();
  await page.waitForFunction(()=>globalThis.HollowStarUI?.getStatus?.().phase==='ready');}

const VIEWPORTS={desktop:{width:1440,height:1000},laptop:{width:1280,height:800},tablet:{width:768,height:1024},phone:{width:390,height:844}};

function probeUrl(url){return new Promise(res=>{const req=http.get(url,r=>{r.resume();res(r.statusCode<500);});req.on('error',()=>res(false));req.setTimeout(800,()=>{req.destroy();res(false);});});}

async function startStatic(){
  const server=http.createServer((q,r)=>{const p=new URL(q.url,'http://x').pathname;const file=p==='/'||p==='/web/'||p==='/web/index.html'?'index.html':p.replace(/^\/(web\/)?/,'');
    const t=path.resolve(webRoot,file);if(!t.startsWith(webRoot)||!fs.existsSync(t)||!fs.statSync(t).isFile()){r.writeHead(404);r.end();return;}
    const type=t.endsWith('.js')?'text/javascript':t.endsWith('.css')?'text/css':t.endsWith('.svg')?'image/svg+xml':t.endsWith('.json')?'application/json':t.endsWith('.png')?'image/png':'text/html';
    r.writeHead(200,{'content-type':type});r.end(fs.readFileSync(t));});
  server.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
  return {server,base:`http://127.0.0.1:${server.address().port}/web/index.html`};}

async function clickText(page,text,hover){
  const byRole=page.getByRole('button',{name:text,exact:true});
  const target=(await byRole.count())?byRole.first():page.getByText(text,{exact:true}).first();
  if(hover)await target.hover();else await target.click();}

async function runStep(page,step){
  const i=step.indexOf(':');const op=i<0?step:step.slice(0,i),arg=i<0?'':step.slice(i+1);
  if(op==='click')return clickText(page,arg,false);
  if(op==='hover')return clickText(page,arg,true);
  if(op==='key')return page.keyboard.press(arg);
  if(op==='type')return page.keyboard.type(arg);
  if(op==='wait')return page.waitForTimeout(Number(arg)||250);
  if(op==='nav')return page.evaluate(s=>globalThis.HollowStarUI?.navigate(s),arg);
  if(op==='eval'){const v=await page.evaluate(arg);console.log(`eval ${arg} => ${JSON.stringify(v)?.slice(0,300)}`);return;}
  throw new Error(`unknown step ${step}`);}

// Everything below runs in the page and returns plain data.
function readout(opts){
  const vis=el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'&&Number(s.opacity)>0.05;};
  const box=r=>`${Math.round(r.x)},${Math.round(r.y)} ${Math.round(r.width)}x${Math.round(r.height)}`;
  const label=el=>(el.getAttribute('aria-label')||el.innerText||el.value||el.title||'').trim().replace(/\s+/g,' ').slice(0,60);
  const W=innerWidth,H=innerHeight;
  const status=globalThis.HollowStarUI?.getStatus?.()??null;
  const headings=[...document.querySelectorAll('h1,h2,h3')].filter(vis).map(h=>`${h.tagName.toLowerCase()} ${label(h)}`).slice(0,15);
  const ctrls=[...document.querySelectorAll('button,a[href],input,select,textarea,[role=button],[role=tab]')].filter(vis);
  const controls=ctrls.slice(0,60).map(el=>{const flags=[el.disabled&&'disabled',el.classList.contains('active')&&'active',el.classList.contains('is-active')&&'hl',el.getAttribute('aria-selected')==='true'&&'selected',document.activeElement===el&&'focus'].filter(Boolean);return `${label(el)||'<'+el.tagName.toLowerCase()+'>'}${flags.length?' ['+flags.join(',')+']':''}`;});
  const issues=[];
  if(document.documentElement.scrollWidth>W+1)issues.push(`H-OVERFLOW page ${document.documentElement.scrollWidth}px > ${W}px`);
  for(const el of ctrls){const r=el.getBoundingClientRect();if(r.right>W+1||r.left<-1)issues.push(`OFFSCREEN "${label(el)}" @${box(r)}`);}
  const rects=ctrls.slice(0,150).map(el=>[el,el.getBoundingClientRect()]);
  for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){const[a,ra]=rects[i],[b,rb]=rects[j];if(a.contains(b)||b.contains(a))continue;
    const ox=Math.min(ra.right,rb.right)-Math.max(ra.left,rb.left),oy=Math.min(ra.bottom,rb.bottom)-Math.max(ra.top,rb.top);
    if(ox>4&&oy>4)issues.push(`OVERLAP "${label(a)}" @${box(ra)} x "${label(b)}" @${box(rb)}`);}
  for(const el of document.querySelectorAll('body *')){if(!vis(el)||!el.childNodes.length)continue;const s=getComputedStyle(el);
    const own=[...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());if(!own)continue;
    if((s.overflow==='hidden'||s.overflowX==='hidden'||s.textOverflow==='ellipsis')&&el.scrollWidth>el.clientWidth+2)issues.push(`CLIPPED "${label(el)}" ${el.scrollWidth}>${el.clientWidth}px`);}
  for(const img of document.querySelectorAll('img'))if(vis(img)&&img.complete&&!img.naturalWidth)issues.push(`BROKEN-IMG ${img.getAttribute('src')}`);
  const text=(document.body.innerText||'').replace(/\n{2,}/g,'\n').trim();
  const selected=opts.select.map(sel=>{const els=[...document.querySelectorAll(sel)];return {sel,count:els.length,items:els.slice(0,5).map(el=>{const s=getComputedStyle(el);return `${vis(el)?'':'(hidden) '}@${box(el.getBoundingClientRect())} color=${s.color} bg=${s.backgroundColor} font=${s.fontSize}/${s.fontWeight} z=${s.zIndex} "${label(el)}"`;})};});
  return {url:location.href,title:document.title,viewport:`${W}x${H}`,status,headings,controls,controlCount:ctrls.length,issues:[...new Set(issues)].slice(0,25),text:opts.full?text:text.slice(0,opts.text),textLen:text.length,selected};}

async function pixelDiff(page,aPath,bPath){
  const a='data:image/png;base64,'+fs.readFileSync(aPath).toString('base64');
  const b='data:image/png;base64,'+fs.readFileSync(bPath).toString('base64');
  return page.evaluate(async([a,b])=>{
    const load=src=>new Promise((res,rej)=>{const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=src;});
    const [ia,ib]=await Promise.all([load(a),load(b)]);
    if(ia.width!==ib.width||ia.height!==ib.height)return {sizeChanged:`${ia.width}x${ia.height} -> ${ib.width}x${ib.height}`};
    const c=document.createElement('canvas');c.width=ia.width;c.height=ia.height;const x=c.getContext('2d');
    x.drawImage(ia,0,0);const da=x.getImageData(0,0,c.width,c.height).data;x.clearRect(0,0,c.width,c.height);x.drawImage(ib,0,0);const db=x.getImageData(0,0,c.width,c.height).data;
    let n=0,minX=1e9,minY=1e9,maxX=-1,maxY=-1;const cell=40,grid=new Map();
    for(let p=0;p<da.length;p+=4){if(Math.abs(da[p]-db[p])+Math.abs(da[p+1]-db[p+1])+Math.abs(da[p+2]-db[p+2])>48){n++;const q=p/4,px=q%c.width,py=(q/c.width)|0;
      if(px<minX)minX=px;if(py<minY)minY=py;if(px>maxX)maxX=px;if(py>maxY)maxY=py;const k=`${(px/cell)|0},${(py/cell)|0}`;grid.set(k,(grid.get(k)||0)+1);}}
    const hot=[...grid.entries()].sort((p,q)=>q[1]-p[1]).slice(0,5).map(([k,v])=>{const[gx,gy]=k.split(',').map(Number);return `${gx*cell},${gy*cell} ${cell}x${cell} (${v}px)`;});
    return {changed:n,pct:+(100*n/(c.width*c.height)).toFixed(3),bbox:n?`${minX},${minY} ${maxX-minX+1}x${maxY-minY+1}`:null,hot};
  },[a,b]);}

(async()=>{
  const args=parseArgs(process.argv.slice(2));
  if(args.help){console.log(fs.readFileSync(__filename,'utf8').split('*/')[0]);return;}
  fs.mkdirSync(out,{recursive:true});
  let base=args.url||process.env.HSR_UI_URL,server,source='env';
  if(!base){
    // --mock replaces the host with a fixture via page.route, so it always
    // wants the plain static server underneath -- a live host would still
    // answer /api/health and get picked here, defeating the point.
    if(!args.mock&&await probeUrl('http://127.0.0.1:8765/api/health')){base='http://127.0.0.1:8765/';source='live host :8765';}
    else{({server,base}=await startStatic());source=args.mock?'static web/ + --mock fixture':'static web/ (no host)';}}
  // Cloud containers pin a pre-fetched Chromium (PLAYWRIGHT_BROWSERS_PATH) whose
  // revision can trail this repo's @playwright/test pin; channel/revision lookup
  // then either hangs or reports a missing headless_shell. Point straight at the
  // bundled binary when one is present -- e.g. Corey's own PC -- fall through to
  // Playwright's normal channel/revision resolution.
  const bundledChromium='/opt/pw-browsers/chromium';
  const launchOpts=process.env.HSR_BROWSER_CHANNEL?{headless:true,channel:process.env.HSR_BROWSER_CHANNEL}
    :fs.existsSync(bundledChromium)?{headless:true,executablePath:bundledChromium,args:['--no-sandbox']}
    :{headless:true};
  const browser=await chromium.launch(launchOpts);
  let code=0;
  try{
    const page=await browser.newPage({viewport:VIEWPORTS[args.viewport]||VIEWPORTS.desktop,reducedMotion:'reduce'});
    // Frozen motion keeps pixel diffs about layout, not about where a drift was.
    await page.addInitScript(()=>{addEventListener('DOMContentLoaded',()=>{const st=document.createElement('style');st.textContent='*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';document.head.appendChild(st);});});
    const errors=[],failed=[];
    page.on('pageerror',e=>errors.push(`PAGEERROR ${e.message.split('\n')[0]}`));
    page.on('console',m=>{if(m.type()==='error'||m.type()==='warning')errors.push(`CONSOLE.${m.type()} ${m.text().slice(0,200)}`);});
    page.on('requestfailed',r=>failed.push(`${r.method()} ${r.url().replace(/^https?:\/\/[^/]+/,'')} ${r.failure()?.errorText}`));
    page.on('response',r=>{if(r.status()>=400)failed.push(`${r.status()} ${r.request().method()} ${r.url().replace(/^https?:\/\/[^/]+/,'')}`);});
    if(args.mock)await installMock(page,args.view?JSON.parse(fs.readFileSync(args.view,'utf8')):defaultMockView(root));
    await page.goto(base,{waitUntil:'networkidle'});
    if(args.mock){try{await bootToReady(page);}catch(e){errors.push(`MOCK-BOOT-FAILED: ${e.message.split('\n')[0]}`);}}
    for(const step of args.do){try{await runStep(page,step);await page.waitForTimeout(120);}catch(e){errors.push(`STEP-FAILED "${step}": ${e.message.split('\n')[0]}`);break;}}
    await page.waitForTimeout(200);
    const r=await page.evaluate(readout,{select:args.select,text:Number(args.text),full:!!args.full});
    const L=[];
    L.push(`UI PROBE · ${source} · ${r.viewport} · ${r.url.replace(/^https?:\/\/[^/]+/,'')}`);
    if(r.status)L.push(`status: ${JSON.stringify(r.status)}`);
    L.push(`errors: ${errors.length?'':'none'}`);errors.slice(0,15).forEach(e=>L.push(`  ${e}`));
    if(failed.length){L.push(`http: ${failed.length} failed`);[...new Set(failed)].slice(0,8).forEach(f=>L.push(`  ${f}`));}
    L.push(`layout: ${r.issues.length?r.issues.length+' issue(s)':'clean'}`);r.issues.forEach(i=>L.push(`  ${i}`));
    L.push(`headings: ${r.headings.join(' | ')||'none'}`);
    L.push(`controls (${r.controlCount}): ${r.controls.join(' · ')}`);
    for(const s of r.selected){L.push(`select ${s.sel}: ${s.count} match(es)`);s.items.forEach(i=>L.push(`  ${i}`));}
    L.push(`text (${r.textLen} chars${r.textLen>r.text.length?', first '+r.text.length:''}):`);
    L.push(r.text.split('\n').map(t=>'  '+t).join('\n'));
    const shotName=args.baseline||args.diff||args.shot;
    if(shotName){
      await page.evaluate(()=>document.querySelectorAll('canvas').forEach(c=>c.style.visibility='hidden'));
      const clip=args.crop?(([x,y,w,h])=>({x,y,width:w,height:h}))(args.crop.split(',').map(Number)):undefined;
      const file=path.join(out,`${shotName}${args.baseline?'.baseline':''}.png`);
      // Settle: status pills and late fetches repaint after load; wait for two equal frames.
      let prev=null,stable=false;for(let n=0;n<8&&!stable;n++){const buf=await page.screenshot({clip});stable=prev&&buf.equals(prev);prev=buf;if(!stable)await page.waitForTimeout(250);}
      fs.writeFileSync(file,prev);if(!stable)L.push('note: page never settled; diff may include live motion');
      L.push(`png: ${path.relative(root,file).replace(/\\/g,'/')}`);
      if(args.diff){const ref=path.join(out,`${shotName}.baseline.png`);
        if(!fs.existsSync(ref))L.push(`diff: no baseline (run --baseline ${shotName} first)`);
        else{const d=await pixelDiff(page,ref,file);
          L.push(d.sizeChanged?`diff: SIZE CHANGED ${d.sizeChanged}`:d.pct<0.25?`diff: no meaningful change (${d.pct}% noise${d.bbox?' @'+d.bbox:''})`:d.changed?`diff: ${d.pct}% changed, bbox ${d.bbox}; hottest cells: ${d.hot.join(' · ')}\n  look only if needed: --shot ${shotName} --crop <x,y,w,h from bbox>`:'diff: identical to baseline');}}
    }
    if(errors.some(e=>e.startsWith('PAGEERROR')||e.startsWith('STEP-FAILED'))||r.issues.length)code=1;
    const text=L.join('\n');fs.writeFileSync(path.join(out,'last.txt'),text+'\n');console.log(text);
  }finally{await browser.close();server?.close();}
  process.exitCode=code;
})().catch(e=>{console.error(`UI PROBE FAILED: ${e.message}`);process.exitCode=2;});
