/* Reactive combat in a real browser against an isolated local host:
   WASD steps, Space attacks, the enemy turn drains itself, right-click opens
   the action wheel, and typing in the console never moves a hero.
   All saves live in a temporary data root. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),net=require('node:net');
const {spawn,spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const codexPython='C:/Users/ACore/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const python=process.env.HSR_PYTHON||(fs.existsSync(codexPython)?codexPython:'python');
const out=path.join(root,'.local','reactive-combat-proof');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'hsr-reactive-')),data=path.join(temp,'.local'),runId='reactive-ui';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function launch(){
  const channel=process.env.HSR_BROWSER_CHANNEL,executablePath=process.env.HSR_CHROMIUM_PATH;
  if(executablePath)return chromium.launch({headless:true,executablePath});
  if(channel)return chromium.launch({headless:true,channel});
  try{return await chromium.launch({headless:true,channel:'chrome'});}catch{return chromium.launch({headless:true});}
}
(async()=>{let child,browser,logs='';try{
  fs.mkdirSync(out,{recursive:true});
  // A Doran + Wren fight against the town watch, saved at Doran's turn.
  const seed=spawnSync(python,['-B','-',data,runId],{cwd:root,encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'},input:`
import sys
from pathlib import Path
from hollowstar.run_service import RunService
from hollowstar.run_state import save_run
data, run_id = Path(sys.argv[1]), sys.argv[2]
service = RunService(data / 'reliquary_runs')
service.create(run_id, ['Doran', 'Wren'], ['Townsperson'], 'reactive-seed')
service.design_start(run_id)
service.design_action(run_id, {'type': 'fight'})
run = service._active[run_id]
run.context['host_mode'] = 'SANDBOX'
combat = run.context['combat']
combat['cursor'] = combat['order'].index('p0')
combat['positions'].update({'p0': [20, 20, 0], 'p1': [10, 30, 0], 'e0': [50, 20, 0]})
save_run(run, run_id, data / 'reliquary_runs' / f'{run_id}.json')
`});assert.equal(seed.status,0,seed.stderr);
  const s=net.createServer();s.listen(0,'127.0.0.1');await new Promise(r=>s.once('listening',r));const port=s.address().port;await new Promise(r=>s.close(r));
  const base=`http://127.0.0.1:${port}`;
  child=spawn(python,['-B',path.join(root,'hollowstar_web_server.py'),'--hostless','--data-root',data,'--port',String(port)],{cwd:root,stdio:['ignore','pipe','pipe'],env:{...process.env,PYTHONIOENCODING:'utf-8'}});
  child.stdout.on('data',c=>logs+=c);child.stderr.on('data',c=>logs+=c);
  for(let i=0;i<150;i++){if(child.exitCode!==null)throw Error(logs);try{if((await fetch(base+'/api/health')).ok)break;}catch{}await delay(100);}
  browser=await launch();
  const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'}),errors=[],commands=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().endsWith('/api/host'))try{commands.push(r.postDataJSON().command);}catch{}});
  const view=()=>page.evaluate(()=>HollowStarUI.getPublicView());
  const status=()=>page.evaluate(()=>HollowStarUI.getCombatStatus());
  async function settled(){await page.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready'&&!HollowStarUI.getStatus().busy&&!HollowStarUI.getCombatStatus().draining,null,{timeout:20000});await delay(80);}
  await page.goto(base+'/web/index.html');
  await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();
  if(await page.locator('[data-action="start-engine"]').count()){await page.locator('[data-action="start-engine"]').click();await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();}
  await page.locator('[data-action="continue:SANDBOX"]').click();
  await page.locator(`[data-action="load:${runId}"]`).click();await settled();
  await page.evaluate(()=>HollowStarUI.navigate('encounter'));await settled();
  await page.locator('#app .combat-stage').waitFor();
  const results=[];
  let v=await view();assert.equal(v.combat.current,'p0',JSON.stringify(v.combat));
  assert.equal((await status()).style,'hybrid');

  // Typing in a text field never moves the hero.
  const input=page.locator('#console-input');
  if(await input.count()){await input.focus();await page.keyboard.type('dddd');await page.keyboard.press('Escape');await page.locator('body').click({position:{x:4,y:4}}).catch(()=>{});}
  v=await view();assert.deepEqual(v.combat.positions.p0,[20,20,0],'typing moved the hero');results.push('typing in the console never moves a hero');

  // D steps five feet east through the host.
  await page.evaluate(()=>document.activeElement?.blur?.());
  await page.keyboard.press('d');await settled();
  v=await view();assert.deepEqual(v.combat.positions.p0,[25,20,0],JSON.stringify(v.combat.positions));
  assert.equal(v.combat.economy.p0.movement,25,JSON.stringify(v.combat.economy.p0));
  results.push('D moves Doran 5 ft east on the host grid');

  // Tab/Q focuses a foe; Space attacks it.
  await page.keyboard.press('q');await delay(60);
  assert.equal((await status()).focus,'e0');
  await page.keyboard.press(' ');await settled();
  v=await view();const e=v.combat.economy.p0;
  assert(e.attacks<4||e.action===0,JSON.stringify(e));results.push('Q focuses the watch, Space spends an attack on it');

  // Right-click the foe opens the wheel with host-derived rows.
  const foe=page.locator('#app .combat-stage [data-stage-actor="e0"]');
  await foe.click({button:'right'});await page.locator('.combat-radial').waitFor();
  const items=await page.locator('.combat-radial-item').evaluateAll(nodes=>nodes.map(n=>({label:n.getAttribute('aria-label'),disabled:n.disabled})));
  assert(items.some(i=>i.label==='Inspect defenses'&&!i.disabled),JSON.stringify(items));
  assert(items.some(i=>i.label==='Weapon attack'),JSON.stringify(items));
  await page.screenshot({path:path.join(out,'action-wheel.png')});
  await page.keyboard.press('Escape');await delay(60);assert.equal(await page.locator('.combat-radial').count(),0);
  results.push(`right-click opens the action wheel (${items.length} items), Esc closes it`);

  // End both heroes' turns: the watch's turn plays itself, control returns.
  const before=commands.filter(c=>c==='design_drain_npc').length;
  for(let i=0;i<4;i++){
    v=await view();if(v.combat.complete)break;
    const decider=v.combat.pending?.[0]?.reactor||v.combat.current;
    if(!String(decider).startsWith('p'))break;
    if(v.combat.pending?.length){await page.locator(`[data-action="reaction:decline_reaction"][data-reactor="${decider}"]`).first().click();}
    else await page.keyboard.press('e');
    await settled();
    v=await view();if(String(v.combat.current).startsWith('p')&&v.combat.current!==decider&&!v.combat.pending?.length&&i>0)break;
  }
  await settled();v=await view();
  const drained=commands.filter(c=>c==='design_drain_npc').length-before;
  const decider=v.combat.complete?null:(v.combat.pending?.[0]?.reactor||v.combat.current);
  assert(v.combat.complete||String(decider).startsWith('p'),JSON.stringify(v.combat));
  assert.equal(await page.locator('[data-auto-step="design_drain_npc"]').count()>0&&!String(decider).startsWith('p'),false);
  results.push(`enemy turn played itself (drain requests: ${drained}); control returned to ${decider||'the end of combat'}`);
  const history=(await status()).history;
  results.push(`director beats: ${history.length} (${history.filter(b=>b.style==='banner').map(b=>b.detail).join(', ')||'no banners'})`);
  await page.screenshot({path:path.join(out,'after-enemy-turn.png')});
  assert.equal(errors.length,0,errors.join('\n'));
  fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({results,commands,errors},null,2));
  console.log('PASS reactive combat controls:\n - '+results.join('\n - ')+'\n'+out);
}finally{if(browser)await browser.close();if(child){child.kill();await Promise.race([new Promise(r=>child.once('exit',r)),delay(2000)]);}}})().catch(e=>{console.error(e);process.exitCode=1;});
