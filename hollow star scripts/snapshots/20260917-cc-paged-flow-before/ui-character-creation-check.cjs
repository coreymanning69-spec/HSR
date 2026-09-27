/* Character creator browser smoke test. Host responses are mocked; no profile or run is saved. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const http=require('node:http');const path=require('node:path');
const root=path.resolve(__dirname,'..'),webRoot=path.join(root,'web');
const options=JSON.parse(fs.readFileSync(path.join(root,'hollowstar','content','character_creation.json'),'utf8'));
const profile={name:'Aster',race:'Half-Elf',race_id:'half-elf',character_class:'Cleric',class_id:'cleric',level:1,
 ability_scores:{STR:10,DEX:12,CON:11,INT:10,WIS:15,CHA:12},max_hp:9,armor_class:16,speed:30,proficiency_bonus:2,
 skill_bonuses:{History:2,Insight:4},features:['Spellcasting','Channel Grace'],interaction_tags:['human','elf','bridge_kin'],
 known_spells:['Guidance@5e','Light@5e'],build_rules:{saves:{STR:0,DEX:1,CON:0,INT:0,WIS:4,CHA:1},casting_energy_max:3,spell_rank_cap:1},
 background:{name:'Acolyte',starting_gold:16},origin_item:{name:'family letter'},heirloom_item:{}};
const receipt={race_bonuses:{CHA:2,STR:0,DEX:0,CON:0,INT:0,WIS:0},floating_bonuses:['STR','CON'],spell_budget:5,spell_points_spent:2,
 origin_roll:{item_id:'family-letter'},heirloom_roll:{triggered:false}};
const character={profile,receipt,build_hash:'a'.repeat(64)};
const server=http.createServer((request,response)=>{
  if(request.url==='/api/health'){response.writeHead(200,{'content-type':'application/json'});response.end(JSON.stringify({ok:true}));return;}
  const file=request.url==='/web/index.html'?'index.html':request.url.replace(/^\/web\//,'');
  const target=path.resolve(webRoot,file);
  if(!target.startsWith(webRoot)||!fs.existsSync(target)){response.writeHead(404);response.end();return;}
  response.writeHead(200,{'content-type':target.endsWith('.js')?'text/javascript':target.endsWith('.css')?'text/css':'text/html'});response.end(fs.readFileSync(target));
});
(async()=>{
  const commands=[];server.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  const browser=await chromium.launch({headless:true,channel:process.env.HSR_BROWSER_CHANNEL||'chrome'});const page=await browser.newPage({viewport:{width:1440,height:1100}});
  await page.route('**/api/host',async route=>{const request=route.request().postDataJSON();commands.push(request.command);let payload={ok:true,result:{}};
    if(request.command==='character_options')payload={ok:true,result:{schema:options.schema,version:options.version,ability_method:options.ability_method,rerolls:1,level_range:options.level_range,default_level:1,advancement_levels:options.advancement_levels,races:Object.entries(options.races).map(([id,row])=>({id,...row})),classes:Object.entries(options.classes).map(([id,row])=>({id,...row})),backgrounds:Object.entries(options.backgrounds).map(([id,row])=>({id,...row})),skills:options.skills}};
    else if(request.command==='character_roll')payload={ok:true,result:{ability_roll:{method:'4d6-drop-lowest',creation_seed:request.creation_seed,roll_set:request.roll_set,rolls:[1,2,3,4,1,2].map((total,index)=>({dice:[total,3,4,5],dropped:total,total})),scores:[15,14,13,12,11,10]}}};
    else if(request.command==='preview_character')payload={ok:true,result:{character}};
    else if(request.command==='readout')payload={ok:true,result:{readout:{public_view:{schema:'hollow-star-public-view-1',run_id:request.run_id,room:{name:'The Town Above the Well'},party:[],available_actions:[]},public_receipt:{message:'created'}}}};
    return route.fulfill({json:payload});
  });
  try {
    await page.goto(base+'/web/index.html');await page.getByRole('button',{name:'New Game',exact:true}).click();await page.getByRole('button',{name:'Engine Host game',exact:true}).click();
    await page.getByLabel('Lead name').fill('Aster');await page.locator('[data-race-choice="half-elf"]').click();await page.getByLabel('Class').selectOption('cleric');await page.getByLabel('Background').selectOption('acolyte');
    assert.equal(await page.locator('[data-race-choice="half-elf"]').getAttribute('aria-pressed'),'true');
    assert.equal(await page.locator('.race-option img').count(),5);assert.equal(await page.locator('.race-option img').evaluateAll(images=>images.every(image=>image.complete&&image.naturalWidth>0)),true);
    assert.equal(await page.locator('.race-option img').evaluateAll(images=>images.every(image=>image.src.endsWith('-female.png'))),true);
    await page.getByLabel('Gender').selectOption('male');
    assert.equal(await page.locator('.race-option img').count(),5);assert.equal(await page.locator('.race-option img').evaluateAll(images=>images.every(image=>image.src.endsWith('-male.png'))),true);
    assert.equal(await page.locator('.race-preview-art img').getAttribute('src'),'assets/sprites/characters/half-elf-male.png');
    await page.getByLabel('Gender').selectOption('female');
    for(const viewport of [{width:1440,height:1100},{width:820,height:900},{width:390,height:844},{width:844,height:390}]){await page.setViewportSize(viewport);await page.waitForTimeout(30);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),true,`horizontal overflow at ${viewport.width}x${viewport.height}`);}
    await page.setViewportSize({width:390,height:844});
    await page.evaluate(()=>document.body.dataset.layout='idle');assert.equal(await page.locator('.race-preview-art').evaluate(node=>getComputedStyle(node).display),'none');assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),true);
    await page.evaluate(()=>document.body.dataset.layout='sanctum');
    await page.getByRole('button',{name:'Roll ability scores',exact:true}).click();await page.getByText('Rolled 4d6-drop-lowest',{exact:true}).waitFor();
    await page.locator('[data-floating="STR"]').check();await page.locator('[data-floating="CON"]').check();
    await page.getByRole('button',{name:'Choose skills manually',exact:true}).click();await page.locator('[data-skill="History"]').check();await page.locator('[data-skill="Insight"]').check();
    await page.getByRole('button',{name:'Choose spells manually',exact:true}).click();await page.locator('[data-spell="Guidance@5e"]').check();await page.locator('[data-spell="Light@5e"]').check();
    assert((await page.locator('.creator-detail').allTextContents()).join(' ').includes('Half-Elf'));assert((await page.locator('.creator-detail').allTextContents()).join(' ').includes('Cleric'));
    await page.getByRole('button',{name:'Preview',exact:true}).click();await page.getByText('Final sheet · not saved',{exact:true}).waitFor();assert((await page.locator('#app').innerText()).includes('Half-Elf Cleric'));
    await page.getByRole('button',{name:'Confirm and create run',exact:true}).click();await page.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready');
    assert(commands.includes('character_options')&&commands.includes('character_roll')&&commands.includes('preview_character')&&commands.includes('build_character')&&commands.includes('create_run')&&commands.includes('readout'));
    assert.deepEqual(await page.evaluate(()=>HollowStarUI.getStatus().phase),'ready');console.log(JSON.stringify({ok:true,commands}));
  } finally {await browser.close();server.close();}
})().catch(error=>{console.error(error);process.exit(1)});
