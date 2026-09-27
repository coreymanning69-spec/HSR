/* Live isolated host proof for QOL: menus, speech, daylight, transitions and doors. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path'), os=require('node:os'), net=require('node:net');
const {spawn,spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'), out=path.join(root,'.local','qol-day-night');
const python='C:/Users/ACore/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const data=path.join(fs.mkdtempSync(path.join(os.tmpdir(),'hsr-qol-')),'.local');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function freePort(){const s=net.createServer();s.listen(0,'127.0.0.1');await new Promise(r=>s.once('listening',r));const p=s.address().port;await new Promise(r=>s.close(r));return p;}
(async()=>{
 let child,browser,logs='';
 try {
  fs.mkdirSync(out,{recursive:true});
  const seed=spawnSync(python,['-',data],{cwd:root,encoding:'utf8',input:`
import sys
from pathlib import Path
from hollowstar.run_service import RunService
from hollowstar.life_sim import _ambient_exchange
s=RunService(Path(sys.argv[1])/'reliquary_runs')
for name,seconds in [('day',0),('dawn',21*3600+1800),('dusk',9*3600+1800),('night',12*3600)]:
    rid='qol-'+name
    s.create(rid,['Doran'],['Townsperson'],seed='qol',scenario='reliquary_city')
    s.design_start(rid)
    r=s._active[rid];r.context['host_mode']='SANDBOX'
    w=r.context['life_world'];w['event_clock']['seconds']=seconds;w['world_time']=8*3600+seconds
    for n in w['residents'].values():n['location']='market';n['schedule']=[]
    w['ambient_events']=[];w['ambient_last_seconds']=-30
    _ambient_exchange(w,rid)
    s.save(rid)
s.create('qol-dungeon',['Doran'],['Townsperson'],seed='qol-dungeon')
s.design_start('qol-dungeon')
r=s._active['qol-dungeon'];r.context['host_mode']='SANDBOX'
from hollowstar import dungeon
r.context['dungeon']['floor']=2;r.context['dungeon']['room']=0;dungeon.enter(r);s.save('qol-dungeon')
print('Five saved live fixtures')
`});
  assert.equal(seed.status,0,seed.stderr);console.log(seed.stdout.trim());
  const port=await freePort(),base=`http://127.0.0.1:${port}`;
  child=spawn(python,[path.join(root,'hollowstar_web_server.py'),'--hostless','--data-root',data,'--port',String(port)],{cwd:root,stdio:['ignore','pipe','pipe']});
  child.stdout.on('data',s=>logs+=s);child.stderr.on('data',s=>logs+=s);
  for(let i=0;i<100;i++){if(child.exitCode!==null)throw Error(logs);try{if((await fetch(base+'/api/health')).ok)break;}catch{}await delay(100);}
  browser=await chromium.launch({headless:true,channel:'chrome'});
  const page=await browser.newPage({viewport:{width:1440,height:1000},recordVideo:{dir:out,size:{width:1440,height:1000}}}),errors=[],requests=[];
  page.setDefaultTimeout(10000);
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().endsWith('/api/host'))requests.push(r.postDataJSON()?.command);});
  async function load(name){
    await page.goto(base+'/web/index.html');
    await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();
    await page.locator('[data-action="continue:SANDBOX"]').click();
    await page.locator(`[data-action="load:qol-${name}"]`).click();
    await page.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready'&&!HollowStarUI.getStatus().busy);
    await page.evaluate(()=>HollowStarUI.navigate('room'));
    await page.waitForFunction(()=>globalThis.__hsrStage?.el.isConnected);
    await page.waitForTimeout(500);
  }
  await load('day');
  const initial=await page.evaluate(()=>HollowStarUI.getPublicView());
  assert.equal(initial.scene.time.minute_of_day,480);
  assert(initial.scene.ambient_events.length);
  await page.waitForFunction(()=>document.querySelector('.ws-speech:not([hidden])'));
  const speech=await page.locator('.ws-speech').innerText();
  await page.screenshot({path:path.join(out,'npc-speech.png'),fullPage:true});
  await page.locator('[data-action="toggle-messages"]').first().click();
  assert((await page.locator('.message-history').first().innerText()).includes(speech));
  await page.screenshot({path:path.join(out,'npc-speech-log.png'),fullPage:true});
  await page.locator('[data-action="toggle-messages"]').first().click();
  // The app and baked canvas must retain identity throughout menu operations.
  await page.evaluate(()=>{window.qolCanvas=__hsrStage.el.querySelector('.ws-bake');window.qolActor=__hsrStage.el.querySelector('[data-resident]');});
  const npc=page.locator('.world-stage [data-resident]').first();
  assert(await npc.count(),'visible resident actor');
  const before=requests.length;
  await npc.dispatchEvent('contextmenu',{clientX:700,clientY:420});
  const title=await page.locator('.context-menu-title').innerText();
  assert.equal(await page.locator('.hsr-context-menu button').count(),4);
  await page.mouse.move(40,40);await page.mouse.move(900,700);await page.waitForTimeout(200);
  assert.equal(await page.locator('.context-menu-title').innerText(),title);
  assert.equal(requests.length,before,'menu open/move must make no host calls');
  assert(await page.evaluate(()=>qolCanvas===__hsrStage.el.querySelector('.ws-bake')&&qolActor===__hsrStage.el.querySelector('[data-resident]')));
  await page.screenshot({path:path.join(out,'right-click-resident.png'),fullPage:true});
  await page.keyboard.press('Escape');assert.equal(await page.locator('.hsr-context-menu').count(),0);
  await page.locator('#app').dispatchEvent('contextmenu',{clientX:400,clientY:350});
  assert.equal(await page.locator('.hsr-context-menu button').count(),2);
  await page.getByRole('button',{name:'Fullscreen',exact:true}).click();
  await page.waitForFunction(()=>Boolean(document.fullscreenElement));
  await page.keyboard.press('F11');await page.waitForFunction(()=>!document.fullscreenElement);
  await npc.focus();await page.keyboard.press('Shift+F10');
  assert.equal(await page.locator('.hsr-context-menu button').count(),4);
  const exams=requests.filter(x=>x==='examine').length;
  await page.getByRole('button',{name:'Examine',exact:true}).click();
  await page.locator('dialog[open]').waitFor();
  assert.equal(requests.filter(x=>x==='examine').length,exams+1);
  await page.keyboard.press('Escape');
  // Accessible names alone must never produce hover tooltips.
  await page.evaluate(()=>{const b=document.createElement('button');b.id='qol-label-only';b.style.cssText='position:fixed;top:70px;left:200px;z-index:9999';b.textContent='New game';b.setAttribute('aria-label','New game');document.querySelector('#app').append(b);});
  await page.locator('#qol-label-only').hover();assert.equal(await page.locator('#hsr-tooltip').count(),0);
  await page.evaluate(()=>{const b=document.querySelector('#qol-label-only');b.dataset.tooltip='Explains an unfamiliar mechanic';});
  await page.mouse.move(1,1);await page.locator('#qol-label-only').hover();
  assert.equal(await page.locator('#hsr-tooltip').innerText(),'Explains an unfamiliar mechanic');
  await page.evaluate(()=>document.querySelector('#qol-label-only').remove());
  // Actual navigation fades while normal readouts leave the cover clear.
  await page.evaluate(()=>{
    window.qolSwapOpacity=[];
    window.qolSwapObserver=new MutationObserver(()=>{const cover=document.querySelector('#hsr-screen-fade');if(cover?.classList.contains('covered'))qolSwapOpacity.push(Number(getComputedStyle(cover).opacity));});
    qolSwapObserver.observe(document.querySelector('#app'),{childList:true,subtree:true});
    HollowStarUI.navigate('roster');
  });
  await page.waitForFunction(()=>document.querySelector('#hsr-screen-fade')?.classList.contains('covered'));
  await page.waitForTimeout(105);
  await page.screenshot({path:path.join(out,'screen-transition-midpoint.png')});
  await page.waitForTimeout(350);
  const swapOpacity=await page.evaluate(()=>{qolSwapObserver.disconnect();return qolSwapOpacity;});assert(swapOpacity.length&&swapOpacity.every(n=>n===1),'screen swaps occur under fully black cover');
  await page.evaluate(()=>{HollowStarUI.navigate('room');HollowStarUI.navigate('inventory');HollowStarUI.navigate('room');});
  await page.waitForTimeout(400);assert(await page.evaluate(()=>__hsrStage.el.isConnected));
  await page.evaluate(()=>{HollowStarUI.navigate('roster');setTimeout(()=>HollowStarUI.navigate('room'),110);});
  await page.waitForTimeout(400);assert(await page.evaluate(()=>__hsrStage.el.isConnected),'navigation during the black layout frames keeps the latest destination');
  await page.evaluate(()=>HollowStarUI.refreshReadout());await page.waitForTimeout(300);
  assert.equal(await page.locator('#hsr-screen-fade.covered').count(),0);
  assert.equal((await page.evaluate(()=>HollowStarUI.getPublicView())).scene.time.minute_of_day,480);
  const countBefore=await page.evaluate(()=>document.querySelectorAll('.message-text').length);
  await page.evaluate(()=>HollowStarUI.refreshReadout());await page.waitForTimeout(200);
  const seen=await page.evaluate(()=>JSON.parse(localStorage.getItem('hsr-ambient-seen:qol-day')));
  assert(seen.some(id=>id.endsWith(':0')),'first spoken line persisted for reconnect deduplication');
  // Host-derived lighting phases and all ordinary door sizes/hotspots.
  // Swapped pointer buttons use the same target and never run both actions.
  await page.evaluate(()=>HollowStarUI.navigate('options'));await page.waitForTimeout(400);
  await page.evaluate(()=>{const n=document.querySelector('[data-pref="swapMouseButtons"]');n.checked=true;n.dispatchEvent(new Event('change',{bubbles:true}));});
  await page.evaluate(()=>HollowStarUI.navigate('room'));await page.waitForTimeout(400);
  const ally=page.locator('.world-stage [data-actor="p0"]');
  await ally.click({force:true});assert.equal(await page.locator('.hsr-context-menu button').count(),4);
  await page.keyboard.press('Escape');
  await ally.click({button:'right',force:true});await page.waitForTimeout(100);assert.equal(await page.locator('.hsr-context-menu').count(),0);
  await page.evaluate(()=>HollowStarUI.navigate('options'));await page.waitForTimeout(400);
  await page.evaluate(()=>{const n=document.querySelector('[data-pref="swapMouseButtons"]');n.checked=false;n.dispatchEvent(new Event('change',{bubbles:true}));});
  const phases={};
  for(const name of ['day','dawn','dusk','night','dungeon']){
    await load(name);
    phases[name]=await page.evaluate(()=>({time:HollowStarUI.getPublicView().scene.time,theme:__hsrStage.st.themeId,tod:__hsrStage.st.tod,
      doors:__hsrStage.st.bays.map(b=>({kind:b.kind,h:b.h,w:b.w})),label:__hsrStage.el.querySelector('.scene-frame-label small').textContent}));
    for(const door of phases[name].doors)if(door.kind!=='gate')assert.equal(door.h,7.1);
    if(name==='dungeon'){
      assert(['foundry','dungeon'].includes(phases[name].theme));
      // An isolated shared-art fixture supplies openings; host dungeon rooms have no exit hotspots.
      await page.evaluate(()=>__hsrStage.setRoom({themeId:'dungeon',roomId:'door-art-proof',name:'Dungeon door refinement · art fixture',tod:'night',exits:[['west',{id:'hall',name:'Lower Hall'}],['east',{id:'crypt',name:'Crypt'}]]}));
      await page.waitForTimeout(200);
    }
    await page.screenshot({path:path.join(out,`doors-${name}.png`),fullPage:true});
  }
  assert.equal(phases.dawn.time.lighting_phase,'dawn');assert.equal(phases.dusk.time.lighting_phase,'dusk');assert.equal(phases.night.time.lighting_phase,'night');
  const geometry=await page.evaluate(async()=>{
    const m=await import('./stage-set.js'),proto=CanvasRenderingContext2D.prototype,original=proto.strokeRect;
    let boxes=[];proto.strokeRect=function(...args){boxes.push(args);return original.apply(this,args);};
    try{m.bakeSet('market',900,500,{seed:'stable-town',tod:480});const day=boxes;boxes=[];m.bakeSet('market',900,500,{seed:'stable-town',tod:1200});return {day,night:boxes};}finally{proto.strokeRect=original;}
  });assert.deepEqual(geometry.day,geometry.night,'changing the hour must preserve building and window geometry');
  const palettes=await page.evaluate(async()=>{const m=await import('./stage-set.js');return [300,330,360,390,420,1020,1050,1080,1110,1140].map(t=>m.paletteAt(t).ambient);});
  assert(new Set(palettes).size>=8,'dawn/dusk palettes should blend');
  await page.setViewportSize({width:390,height:844});
  await page.locator('#app').dispatchEvent('contextmenu',{clientX:389,clientY:843});
  assert(await page.locator('.hsr-context-menu').evaluate(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight;}));
  await page.screenshot({path:path.join(out,'menu-phone.png'),fullPage:true});await page.keyboard.press('Escape');
  await page.emulateMedia({reducedMotion:'reduce'});await page.evaluate(()=>HollowStarUI.navigate('roster'));
  assert.equal(await page.locator('#hsr-screen-fade.covered').count(),0);
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({ok:true,liveHost:true,menus:true,noPointerRequests:true,canvasPreserved:true,speechLogged:true,swappedButtons:true,phoneMenu:true,dungeonDoorArtFixture:true,stableBuildingGeometry:true,swapOpacity,phases,paletteSamples:palettes,errors},null,2));
  const video=page.video();await page.close();fs.copyFileSync(await video.path(),path.join(out,'qol-walkthrough.webm'));
  console.log(JSON.stringify({ok:true,output:out,errors}));
 }catch(e){console.error(logs.slice(-1500));throw e;}
 finally{await browser?.close();child?.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
