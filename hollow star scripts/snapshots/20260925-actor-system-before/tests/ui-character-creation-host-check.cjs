/* Host-backed first-time custom character journey. All saves live in a temporary data root. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const os=require('node:os');const path=require('node:path');
const {spawn}=require('node:child_process');const net=require('node:net');
const root=path.resolve(__dirname,'..');
const python=process.env.HSR_PYTHON||'C:/Users/ACore/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'hsr-creator-e2e-'));
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function freePort(){const server=net.createServer();server.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));const port=server.address().port;await new Promise(resolve=>server.close(resolve));return port;}
async function request(base,command,fields={}){const response=await fetch(base+'/api/host',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id:`e2e-${Date.now()}-${Math.random()}`,command,...fields})});assert(response.ok,`${command} HTTP ${response.status}`);const payload=await response.json();assert(payload.ok,`${command}: ${payload.error?.message||'host rejected request'}`);return payload.result;}
(async()=>{
  let child,browser,hostBase;
  try{
    assert(fs.existsSync(python),`Python runtime not found: ${python}`);
    const port=await freePort(),base=hostBase=`http://127.0.0.1:${port}`;
    child=spawn(python,[path.join(root,'hollowstar_web_server.py'),'--hostless','--data-root',path.join(temp,'.local'),'--port',String(port)],{cwd:root,stdio:['ignore','pipe','pipe']});
    let logs='';child.stdout.on('data',chunk=>logs+=chunk);child.stderr.on('data',chunk=>logs+=chunk);
    let ready=false;for(let i=0;i<100;i++){if(child.exitCode!==null)throw Error(`isolated host exited early:\n${logs}`);try{const response=await fetch(base+'/api/health');if(response.ok){ready=true;break;}}catch{}await wait(100);}
    assert(ready,`isolated host did not become ready:\n${logs}`);
    browser=await chromium.launch({headless:true,channel:process.env.HSR_BROWSER_CHANNEL||'chrome'});
    const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'}),previews=[];
    page.on('response',async response=>{if(!response.url().endsWith('/api/host'))return;try{const wire=response.request().postDataJSON();if(wire.command==='preview_character')previews.push(await response.json());}catch{}});
    await page.goto(base+'/web/index.html');
    // Truly fresh path: title -> Simulation Mode -> New Run -> gateway -> Choose Lead.
    await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();
    await page.locator('[data-action="mode:SANDBOX"]').click();
    await page.getByRole('button',{name:'Use local gateway',exact:true}).click();
    await page.locator('.cc-fork-card[data-action="create"]').waitFor();
    await page.getByRole('button',{name:'Build a custom character',exact:true}).click();
    const step=()=>page.locator('.cc-shell').getAttribute('data-create-step');
    const next=async expected=>{await page.locator('.cc-next').click();await page.waitForFunction(id=>document.querySelector('.cc-shell')?.dataset.createStep===id,expected);};
    await page.getByLabel('Lead name').fill('E2E Aster');await next('ancestry');
    await page.locator('[data-choice="race:half-elf"]').click();await next('class');
    await page.locator('[data-choice="class:magician"]').click();await next('background');
    await page.locator('[data-choice="background:scholar"]').click();await next('abilities');
    await page.getByRole('button',{name:'Roll ability scores',exact:true}).click();await page.locator('.cc-die-set').first().waitFor();
    await page.getByRole('button',{name:'Surprise me',exact:true}).click();await page.getByRole('button',{name:'Use recommended placement',exact:true}).click();await next('training');
    await page.getByRole('button',{name:/Trained skills/}).click();
    await page.locator('[data-skill-pick="Arcana"]').click();await page.locator('[data-skill-pick="History"]').click();
    await page.getByRole('button',{name:'Done',exact:true}).click();
    await page.getByRole('button',{name:/Spells/}).click();await page.getByRole('button',{name:'Choose manually',exact:true}).click();
    await page.locator('[data-spell="Light@5e"]').check();await page.locator('[data-spell="Mending@5e"]').check();
    await page.getByRole('button',{name:'Done',exact:true}).click();await next('look');
    await page.getByRole('button',{name:/Hair and build/}).click();await page.locator('[data-look^="hair_color:"]').nth(1).click();
    await page.getByRole('button',{name:'Done',exact:true}).click();await next('summary');
    await page.getByText('Final sheet · not saved',{exact:true}).waitFor();
    const profileListBefore=await request(base,'list_profiles');assert.equal(profileListBefore.profiles.length,0,'review must not save a profile before confirmation');
    const summary=await page.locator('.cc-summary').innerText();assert(summary.includes('Light'));assert(summary.includes('Mending'));
    const preview=[...previews].reverse().find(row=>row.ok&&row.result?.character?.profile?.known_spells?.includes('Light@5e')&&row.result.character.profile.known_spells.includes('Mending@5e'));
    assert(preview,'host preview accepted both manual spell selections');
    const receipt=preview.result.character.receipt;
    assert(receipt.spell_points_spent<=receipt.spell_budget,'host accepted selected spells within its calculated budget');
    assert(receipt.spell_budget>0,'host calculated a positive spell budget');
    const preConfirmStatus=await page.evaluate(()=>HollowStarUI.getStatus());assert.equal(preConfirmStatus.phase,'create');assert.equal(preConfirmStatus.run_id,null,'review does not start a run');
    await page.locator('.cc-shell .cc-confirm [data-action="confirm-build"]').click();
    await page.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready'&&!HollowStarUI.getStatus().busy);
    const runStatus=await page.evaluate(()=>HollowStarUI.getStatus()),view=await page.evaluate(()=>HollowStarUI.getPublicView());
    assert(runStatus.run_id);assert.equal(view.run_id,runStatus.run_id);assert(view.room,'new character enters the first room');
    const lead=view.party.find(actor=>actor.name==='E2E Aster');assert(lead,'created lead is present in the first room party');assert(lead.id,'created lead has a usable host actor id');
    assert((view.available_actions||[]).length>0,'first room exposes at least one usable host action');
    const seed=summary.match(/Build #([^\s]+)/)?.[1];assert(seed,'summary exposes the host allocated profile seed');
    const profileId=`web-${seed.toLowerCase().replace(/[^a-z0-9_-]+/g,'-').replace(/^-|-$/g,'')}`;
    const saved=await request(base,'inspect_profile',{profile_id:profileId});
    assert(saved.profile.known_spells.includes('Light@5e')&&saved.profile.known_spells.includes('Mending@5e'),'saved profile retains manual spells');
    const resumed=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});await resumed.goto(base+'/web/index.html');
    await resumed.getByRole('button',{name:'Simulation Mode',exact:true}).click();await resumed.locator('[data-action="continue:SANDBOX"]').click();
    await resumed.getByRole('button',{name:'Resume',exact:true}).first().click();
    await resumed.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready'&&!HollowStarUI.getStatus().busy);
    const resumedView=await resumed.evaluate(()=>HollowStarUI.getPublicView());
    assert.equal(resumedView.run_id,runStatus.run_id,'a fresh browser session resumes the saved run');
    assert(resumedView.party.some(actor=>actor.name==='E2E Aster'),'resumed run restores the custom lead');
    await resumed.close();
    console.log(JSON.stringify({ok:true,run_id:runStatus.run_id,lead:lead.name,room:view.room.name,spells:lead.known_spells,spell_points:`${receipt.spell_points_spent}/${receipt.spell_budget}`,resumed:true,data_root:'temporary'}));
  }finally{
    if(browser)await browser.close().catch(()=>{});
    if(child&&child.exitCode===null){try{await fetch(hostBase+'/api/host',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id:'stop-e2e-host',command:'shutdown'})});}catch{}await Promise.race([new Promise(resolve=>child.once('exit',resolve)),wait(2000)]);if(child.exitCode===null)child.kill();}
    fs.rmSync(temp,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exit(1)});
