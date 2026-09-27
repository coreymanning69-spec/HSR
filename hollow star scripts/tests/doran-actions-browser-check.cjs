/* Real browser buttons -> isolated local host -> saved champion results. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),net=require('node:net');
const {spawn,spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),python='C:/Users/ACore/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',out=path.join(root,'.local','doran-combat-proof');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'hsr-doran-actions-')),data=path.join(temp,'.local'),file=path.join(data,'reliquary_runs','doran-actions.json');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{let child,browser,logs='';try{
 fs.mkdirSync(out,{recursive:true});
 const seed=spawnSync(python,['-B','-',data],{cwd:root,encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'},input:`
import sys
from pathlib import Path
from tests.test_doran_combat import DoranCombatTests
from hollowstar.run_state import save_run
f=DoranCombatTests();f.setUp()
try:
 r=f.ready();r.context['host_mode']='SANDBOX'
 r.context['dungeon']['status']='active'
 r.context['dungeon']['rooms']['1:1']['visited']=True
 save_run(r,'doran-actions',Path(sys.argv[1])/'reliquary_runs/doran-actions.json')
finally:f.tearDown()
`});assert.equal(seed.status,0,seed.stderr);const original=fs.readFileSync(file);
 const s=net.createServer();s.listen(0,'127.0.0.1');await new Promise(r=>s.once('listening',r));const port=s.address().port;await new Promise(r=>s.close(r));
 const base=`http://127.0.0.1:${port}`;child=spawn(python,['-B',path.join(root,'hollowstar_web_server.py'),'--data-root',data,'--port',String(port)],{cwd:root,stdio:['ignore','pipe','pipe'],env:{...process.env,PYTHONIOENCODING:'utf-8'}});child.stdout.on('data',s=>logs+=s);child.stderr.on('data',s=>logs+=s);
 for(let i=0;i<100;i++){if(child.exitCode!==null)throw Error(logs);try{if((await fetch(base+'/api/health')).ok)break;}catch{}await delay(100);}
 browser=await chromium.launch({headless:true,channel:'chrome'});const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 async function settled(){await page.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready'&&!HollowStarUI.getStatus().busy);}
 async function load(){fs.writeFileSync(file,original);await page.goto(base+'/web/index.html');await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();if(await page.locator('[data-action="start-engine"]').count()){await page.locator('[data-action="start-engine"]').click();await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();}await page.locator('[data-action="continue:SANDBOX"]').click();await page.locator('[data-action="load:doran-actions"]').click();await settled();await page.evaluate(()=>HollowStarUI.navigate('encounter'));await page.locator('#engine-help > summary').click();}
 const results=[];
 await load();for(const id of ['grand_cleave','read_seam','action_surge','quick_toss','dagger_attack','cleaver_attack','maneuver_trip_attack'])assert(await page.locator(`[data-engine-action="${id}"]`).count(),id+' missing');
 await page.screenshot({path:path.join(out,'champion-actions.png'),fullPage:true});
 await page.locator('[data-engine-action="action_surge"]').click();await settled();let v=await page.evaluate(()=>HollowStarUI.getPublicView());assert.equal(v.combat.economy.p0.action,2);results.push('Action Surge button adds one action');
 await load();await page.locator('[data-engine-action="read_seam"]').click();await page.locator('[data-action="target-choice:read_seam:target:e0"]').click();await settled();v=await page.evaluate(()=>HollowStarUI.getPublicView());assert.equal(v.combat.economy.p0.bonus,0);results.push('Read the Seam button consumes bonus action');
 await load();await page.locator('[data-engine-action="quick_toss"]').click();await page.locator('[data-action="target-choice:quick_toss:target:e0"]').click();await settled();v=await page.evaluate(()=>HollowStarUI.getPublicView());assert.equal(v.combat.economy.p0.bonus,0);results.push('Quick Toss button reaches maneuver host');
 await load();await page.locator('[data-engine-action="grand_cleave"]').click();await page.locator('[data-action="target-choice:grand_cleave:facing:east"]').click();await settled();v=await page.evaluate(()=>HollowStarUI.getPublicView());const grand=v.recent_receipts.find(r=>r.type==='grand_cleave');assert(grand,JSON.stringify(v.recent_receipts));assert(grand.targets.length>0);results.push('Grand Cleave button resolves one arc through host');
 await page.screenshot({path:path.join(out,'grand-cleave-result.png'),fullPage:true});assert.equal(errors.length,0,errors.join('\n'));fs.writeFileSync(path.join(out,'live-actions.json'),JSON.stringify({results,grand,errors},null,2));console.log('PASS live Doran champion buttons, host costs, Grand Cleave result; zero page errors. '+out);
}finally{if(browser)await browser.close();if(child){child.kill();await Promise.race([new Promise(r=>child.once('exit',r)),delay(2000)]);}}})().catch(e=>{console.error(e);process.exitCode=1;});
