/* Live host proof: eight combatants, eighty effects, selection and save/resume. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),net=require('node:net');
const {spawn,spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const codexPython='C:/Users/ACore/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const python=process.env.HSR_PYTHON||(fs.existsSync(codexPython)?codexPython:'python');
const output=path.join(root,'.local','combat-capacity-check');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'hsr-combat-capacity-'));
const dataRoot=path.join(temp,'.local');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function freePort(){const s=net.createServer();s.listen(0,'127.0.0.1');await new Promise(r=>s.once('listening',r));const port=s.address().port;await new Promise(r=>s.close(r));return port;}
async function request(base,command,fields={}){const response=await fetch(base+'/api/host',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id:`capacity-${Date.now()}-${Math.random()}`,command,...fields})});assert(response.ok);const wire=await response.json();assert(wire.ok,`${command}: ${JSON.stringify(wire.error)}`);return wire;}
(async()=>{
 let browser,child,base,logs='';
 try{
  fs.mkdirSync(output,{recursive:true});
  const seed=spawnSync(python,['-',dataRoot],{cwd:root,input:`
import sys, tempfile
from pathlib import Path
from tests.test_gameplay import CombatCapacityTests
from hollowstar.run_state import save_run
root=Path(sys.argv[1])/'reliquary_runs'
fixture=CombatCapacityTests()
for count in range(1,8):
    with tempfile.TemporaryDirectory() as seed:
        _,run=fixture.fixture(Path(seed)/'.local/reliquary_runs',count,8-count)
        run.context['host_mode']='SANDBOX'
        run.context['party_rules']={key:{'identity':'adventurer'} for key in __import__('hollowstar.tactical',fromlist=['actors']).actors(run)}
        run.context['combat']['order']=list(run.context['combat']['rules'])
        run.context['combat']['cursor']=0
        run.context['combat']['positions']={key:[10 if key.startswith('p') else 15,10,0] for key in run.context['combat']['order']}
        from copy import deepcopy
        from hollowstar.loader import load_items
        weapon=load_items()['longsword']
        for member in run.party+run.opposition:
            member.equipment=[deepcopy(weapon)]
        run.context['dungeon']['rooms']['1:1']['visited']=True
        run.context['dungeon']['status']='active'
        save_run(run,f'capacity-{count}-{8-count}',root/f'capacity-{count}-{8-count}.json')
        if count==4:
            run.context['combat']['rules']['p0']['identity']='wren'
            run.party[0].name='Wren'
            run.context['combat']['positions']['p0'][2]=10
            save_run(run,'capacity-flight',root/'capacity-flight.json')
print('Seeded seven isolated host fixtures')
`,encoding:'utf8'});
  assert.equal(seed.status,0,seed.stderr);console.log(seed.stdout.trim());
  const saveRoot=path.join(dataRoot,'reliquary_runs');
  const fixtureBytes=new Map(fs.readdirSync(saveRoot).filter(name=>name.endsWith('.json')).map(name=>[name,fs.readFileSync(path.join(saveRoot,name))]));
  const port=await freePort();base=`http://127.0.0.1:${port}`;
  child=spawn(python,[path.join(root,'hollowstar_web_server.py'),'--data-root',dataRoot,'--port',String(port)],{cwd:root,stdio:['ignore','pipe','pipe']});
  child.stdout.on('data',s=>logs+=s);child.stderr.on('data',s=>logs+=s);
  for(let i=0;i<100;i++){if(child.exitCode!==null)throw Error(logs);try{if((await fetch(base+'/api/health')).ok)break;}catch{}await delay(100);}
  browser=await chromium.launch({headless:true,channel:process.env.HSR_BROWSER_CHANNEL||'chrome'});
  const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  async function load(count,runId=`capacity-${count}-${8-count}`){
    const filename=runId+'.json';
    fs.writeFileSync(path.join(saveRoot,filename),fixtureBytes.get(filename));
    await page.goto(base+'/web/index.html');
    await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();
    await page.locator('[data-action="continue:SANDBOX"]').click();
    await page.locator(`[data-action="load:${runId}"]`).click();
    try{await page.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready'&&!HollowStarUI.getStatus().busy);}catch(error){console.log('LOAD FAILURE',runId,await page.evaluate(()=>({status:HollowStarUI.getStatus(),text:document.body.innerText.slice(-2500)})),logs.slice(-2500));throw error;}
    await page.evaluate(()=>HollowStarUI.navigate('encounter'));
    await page.locator('.combat-stage [data-stage-actor]').first().waitFor();
  }
  async function geometry(label){
    const report=await page.locator('.combat-stage').evaluate(stage=>{
      const s=stage.getBoundingClientRect();
      return [...stage.querySelectorAll(':scope > [data-stage-actor]')].map(node=>{
        const b=node.getBoundingClientRect(),rack=node.querySelector('.doll-chips')?.getBoundingClientRect();
        const center={x:(b.left+b.right)/2,y:(b.top+b.bottom)/2};
        const hit=document.elementFromPoint(center.x,center.y)?.closest('[data-stage-actor]')?.dataset.stageActor;
        return {id:node.dataset.stageActor,box:{left:b.left,top:b.top,right:b.right,bottom:b.bottom},stage:{left:s.left,top:s.top,right:s.right,bottom:s.bottom},rack:rack?{left:rack.left,top:rack.top,right:rack.right,bottom:rack.bottom}:null,hit};
      });
    });
    assert.equal(report.length,8,label+' actor count');
    for(const actor of report){
      const {box,stage,rack}=actor;
      assert.equal(actor.hit,actor.id,`${label} ${actor.id} cannot be targeted at its center`);
      assert(box.left>=stage.left-1&&box.right<=stage.right+1&&box.top>=stage.top-1&&box.bottom<=stage.bottom+1,`${label} ${actor.id} clipped: ${JSON.stringify(actor)}`);
      assert(rack&&rack.left>=stage.left-1&&rack.right<=stage.right+1&&rack.top>=stage.top-1,`${label} ${actor.id} rack clipped: ${JSON.stringify(actor)}`);
    }
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),label+' horizontal overflow');
    fs.writeFileSync(path.join(output,label+'-bounds.json'),JSON.stringify(report,null,2));
    return report;
  }
  const results=[];
  for(const count of (process.env.HSR_COMBAT_QUICK ? [4] : [4,1,7,2,6,3,5])){
    await page.setViewportSize({width:1440,height:1100});await load(count);
    const view=await page.evaluate(()=>HollowStarUI.getPublicView());
    assert.equal(view.party.length,count);assert.equal(view.opposition.length,8-count);
    assert.equal(await page.locator('.combat-stage .doll-effect').count(),80);
    assert.equal(await page.locator('.ff-status-row').count(),8);
    await page.locator('.combat-stage').screenshot({path:path.join(output,`${count}v${8-count}-debug.png`)});
    await geometry(`${count}v${8-count}-desktop`);
    await page.locator('.combat-stage').screenshot({path:path.join(output,`${count}v${8-count}-desktop.png`)});
    await page.setViewportSize({width:390,height:844});
    await geometry(`${count}v${8-count}-phone`);
    await page.locator('.combat-stage').screenshot({path:path.join(output,`${count}v${8-count}-phone.png`)});
    results.push(`${count}v${8-count}`);
  }
  await page.setViewportSize({width:1440,height:1100});await load(4,'capacity-flight');
  assert.equal(await page.locator('.flight-actor[data-stage-actor]').count(),8);
  assert.equal(await page.locator('.combat-stage .doll-effect').count(),80);
  await page.locator('.combat-stage').screenshot({path:path.join(output,'4v4-flight-debug.png')});
  await geometry('4v4-flight-desktop');
  await page.locator('.combat-stage').screenshot({path:path.join(output,'4v4-flight-desktop.png')});
  await page.setViewportSize({width:390,height:844});
  await geometry('4v4-flight-phone');
  await page.locator('.combat-stage').screenshot({path:path.join(output,'4v4-flight-phone.png')});
  await page.setViewportSize({width:1440,height:1100});await load(4);
  // Target selection travels through the live UI; effect details stay keyboard reachable.
  await page.locator('[data-stage-actor="e3"]').click();
  assert(await page.locator('[data-stage-actor="e3"]').evaluate(n=>n.classList.contains('is-targeted')));
  await page.locator('.ff-effects summary').first().click();
  assert(await page.locator('.ff-effects').first().evaluate(n=>n.open));
  await page.locator('.ff-cmd[data-engine-action="attack"]').click();
  const choice=page.locator('[data-action="target-choice:attack:target:e3"]');
  if(await choice.count())await choice.click();
  try{await page.waitForFunction(()=>HollowStarUI.getPublicView().combat.economy.p0.action===0&&!HollowStarUI.getStatus().busy);}catch(error){console.log('ATTACK FAILURE',await page.evaluate(()=>document.body.innerText.slice(-2000)),logs.slice(-1500));throw error;}
  await page.locator('.ff-cmd[data-engine-action="end_turn"]').click();
  await page.waitForFunction(()=>HollowStarUI.getPublicView().combat.current==='p1'&&!HollowStarUI.getStatus().busy);
  const afterTurn=await page.evaluate(()=>HollowStarUI.getPublicView());
  assert(afterTurn.party.find(a=>a.id==='p0').active_effects.every(e=>e.remaining===1));
  await page.locator('.top-nav-menu-btn').click();
  await page.locator('.game-system-modal-actions [data-action="save"]').click();await page.waitForFunction(()=>!HollowStarUI.getStatus().busy);
  await page.locator('.game-system-modal-actions [data-action="title"]').click();
  await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();
  await page.locator('[data-action="continue:SANDBOX"]').click();
  await page.locator('[data-action="load:capacity-4-4"]').click();
  await page.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready'&&!HollowStarUI.getStatus().busy);
  const resumed=await page.evaluate(()=>HollowStarUI.getPublicView());
  assert.deepEqual(resumed.party.map(a=>a.active_effects),afterTurn.party.map(a=>a.active_effects));
  assert.deepEqual(resumed.opposition.map(a=>a.active_effects),afterTurn.opposition.map(a=>a.active_effects));
  assert.deepEqual(resumed.combat.order,afterTurn.combat.order);assert.equal(resumed.combat.current,'p1');
  assert.deepEqual(errors,[]);
  const receipt={ok:true,teamSplits:results,simultaneousEffects:80,flight:true,attack:true,targetSelection:true,turnExpiry:true,saveMenuContinue:true,errors,output};
  fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify(receipt));
 }finally{
  if(browser)await browser.close().catch(()=>{});
  if(child&&child.exitCode===null){try{await request(base,'shutdown');}catch{}await Promise.race([new Promise(r=>child.once('exit',r)),delay(1500)]);if(child.exitCode===null)child.kill();}
  const resolved=path.resolve(temp);assert(resolved.startsWith(path.resolve(os.tmpdir())+path.sep));fs.rmSync(resolved,{recursive:true,force:true});
 }
})().catch(error=>{console.error(error);process.exit(1)});
