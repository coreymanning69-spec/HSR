/* Host-backed first-time custom character journey. All saves live in a temporary data root. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const os=require('node:os');const path=require('node:path');
const {spawn}=require('node:child_process');const net=require('node:net');
const root=path.resolve(__dirname,'..');
const codexPython='C:/Users/ACore/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const python=process.env.HSR_PYTHON||(fs.existsSync(codexPython)?codexPython:'python');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'hsr-creator-e2e-'));
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function freePort(){const server=net.createServer();server.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));const port=server.address().port;await new Promise(resolve=>server.close(resolve));return port;}
async function request(base,command,fields={}){const response=await fetch(base+'/api/host',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id:`e2e-${Date.now()}-${Math.random()}`,command,...fields})});assert(response.ok,`${command} HTTP ${response.status}`);const payload=await response.json();assert(payload.ok,`${command}: ${payload.error?.message||'host rejected request'}`);return payload.result;}
(async()=>{
  let child,browser,hostBase;
  try{
    assert(fs.existsSync(python),`Python runtime not found: ${python}`);
    const port=await freePort(),base=hostBase=`http://127.0.0.1:${port}`;
    child=spawn(python,[path.join(root,'hollowstar_web_server.py'),'--data-root',path.join(temp,'.local'),'--port',String(port)],{cwd:root,stdio:['ignore','pipe','pipe']});
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
    await page.locator('.cc-fork-card[data-action="create"]').waitFor();
    await page.getByRole('button',{name:'Build a custom character',exact:true}).click();
    const step=()=>page.locator('.cc-shell').getAttribute('data-create-step');
    const next=async expected=>{await page.locator('.cc-next').click();await page.waitForFunction(id=>document.querySelector('.cc-shell')?.dataset.createStep===id,expected);};
    const output=path.join(root,'.local','puppet-check');fs.mkdirSync(output,{recursive:true});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.getByLabel('Lead name').fill('Puppet Aster');await next('ancestry');
    await page.locator('[data-choice="race:half-elf"]').click();await next('class');
    await page.locator('[data-choice="class:magician"]').click();await next('background');
    await next('abilities');await page.getByRole('button',{name:'Roll ability scores',exact:true}).click();
    await page.locator('.cc-die-set').first().waitFor();await next('training');await next('look');
    await page.getByRole('button',{name:/Hair and build/}).click();
    await page.locator('[data-look="hair_style:braided"]').click();await page.locator('[data-look="hair_color:auburn"]').click();
    await page.getByRole('button',{name:'Done',exact:true}).click();
    await page.locator('[data-puppet-pose="run"]').first().click();
    await page.waitForFunction(()=>document.querySelector('.cc-doll-figure')?.dataset.renderedPose==='run');
    await page.locator('[data-puppet-facing]').first().click();
    assert.equal(await page.locator('[data-puppet-preview]').first().getAttribute('data-preview-facing'),'-1');
    await page.mouse.move(10,100);
    await page.screenshot({path:path.join(output,'creator-look.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'creator-phone.png'),fullPage:true});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'phone horizontal overflow');
    await page.setViewportSize({width:1440,height:1100});
    await page.locator('[data-puppet-pose="idle"]').first().click();
    await next('summary');await page.getByText('Final sheet · not saved',{exact:true}).waitFor();
    await page.waitForTimeout(250);
    const previewModel=await page.locator('[data-puppet-model]').first().getAttribute('data-puppet-model');
    await page.screenshot({path:path.join(output,'creator-summary.png'),fullPage:true});
    await page.locator('.cc-shell .cc-confirm [data-action="confirm-build"]').click();
    await page.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready'&&!HollowStarUI.getStatus().busy);
    const view=await page.evaluate(()=>HollowStarUI.getPublicView()),runStatus=await page.evaluate(()=>HollowStarUI.getStatus());
    const lead=view.party.find(a=>a.name==='Puppet Aster');assert(lead);fs.writeFileSync(path.join(output,'public-lead.json'),JSON.stringify(lead,null,2));assert.equal(lead.appearance.hair_style.id,'braided');assert.equal(lead.appearance.hair_color.id,'auburn');
    assert.deepEqual(JSON.parse(previewModel).appearanceData,lead.appearance,'preview and public actor appearance');
    await page.screenshot({path:path.join(output,'custom-journey.png'),fullPage:true});
    // Save -> Menu -> Continue exercises the real public browser flow.
    await page.locator('.top-nav-menu-btn').click();
    await page.locator('.game-system-modal-actions [data-action="save"]').click();
    await page.waitForFunction(()=>!HollowStarUI.getStatus().busy);
    await page.locator('.game-system-modal-actions [data-action="title"]').click();
    await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();await page.locator('[data-action="continue:SANDBOX"]').click();
    await page.getByRole('button',{name:'Resume',exact:true}).first().click();
    await page.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready'&&!HollowStarUI.getStatus().busy);
    const restored=await page.evaluate(()=>HollowStarUI.getPublicView());assert.equal(restored.run_id,runStatus.run_id);
    assert.deepEqual(restored.party.find(a=>a.id===lead.id).appearance,lead.appearance);
    assert.deepEqual(restored.party.find(a=>a.id===lead.id).equipment,lead.equipment);
    await page.screenshot({path:path.join(output,'custom-resumed.png'),fullPage:true});
    assert.deepEqual(errors,[]);console.log(JSON.stringify({ok:true,run:runStatus.run_id,appearancePreserved:true,equipmentPreserved:true,saveMenuContinue:true,output}));
  }finally{
    if(browser)await browser.close().catch(()=>{});
    if(child&&child.exitCode===null){try{await fetch(hostBase+'/api/host',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id:'stop-e2e-host',command:'shutdown'})});}catch{}await Promise.race([new Promise(resolve=>child.once('exit',resolve)),wait(2000)]);if(child.exitCode===null)child.kill();}
    fs.rmSync(temp,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exit(1)});
