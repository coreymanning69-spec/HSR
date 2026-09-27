/* Character creator browser smoke test. Host responses are mocked; no profile or run is saved. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const http=require('node:http');const path=require('node:path');
const root=path.resolve(__dirname,'..'),webRoot=path.join(root,'web');
fs.mkdirSync(path.join(root,'.local','ui-character-creation-audit'),{recursive:true});
const options=JSON.parse(fs.readFileSync(path.join(root,'hollowstar','content','character_creation.json'),'utf8'));
const profile={name:'Aster',race:'Half-Elf',race_id:'half-elf',character_class:'Cleric',class_id:'cleric',level:1,
 ability_scores:{STR:10,DEX:12,CON:11,INT:10,WIS:15,CHA:12},max_hp:9,armor_class:16,speed:30,proficiency_bonus:2,
 skill_bonuses:{History:2,Insight:4},features:['Spellcasting','Channel Grace'],interaction_tags:['human','elf','bridge_kin'],
 known_spells:['Guidance@5e','Light@5e'],build_rules:{saves:{STR:0,DEX:1,CON:0,INT:0,WIS:4,CHA:1},casting_energy_max:3,spell_rank_cap:1},
 background:{name:'Acolyte',starting_gold:16},origin_item:{name:'family letter'},heirloom_item:{}};
const receipt={creation_seed:'00007',assigned_scores:{STR:10,DEX:12,CON:11,INT:10,WIS:15,CHA:10},race_bonuses:{CHA:2,STR:0,DEX:0,CON:0,INT:0,WIS:0},floating_bonuses:['STR','CON'],
 background:{ability_bonus:{STR:0,DEX:0,CON:0,INT:0,WIS:1,CHA:0}},advancements:{},final_scores:profile.ability_scores,trained_skills:['History','Insight'],spell_budget:5,spell_points_spent:2,
 origin_roll:{item_id:'family-letter'},heirloom_roll:{triggered:false}};
const notes={archetype:'Battle priest',role:'Armored healer',summary:'Battle priest: armored healer built on Wisdom and Dexterity.',strengths:['Wisdom 15 (+2) and Dexterity 12 (+1) are your best scores.'],
 watchouts:['Lowest score: Strength 10 (+0).'],synergies:['Half-Elf floating bonuses were steered into your class primaries.'],tip:'Heal before someone falls.',
 ratings:{offense:3,defense:4,magic:5,complexity:2},derived:{passive_perception:12}};
Object.assign(profile,{appearance:{},equipment:[{name:'mace',damage_dice:'1d6',attack_bonus:2,damage_modifier:0},{name:'scale mail',base_ac:14,dex_cap:2}]});
const character={profile,receipt,notes,build_hash:'a'.repeat(64)};
const server=http.createServer((request,response)=>{
  if(request.url==='/api/health'){response.writeHead(200,{'content-type':'application/json'});response.end(JSON.stringify({ok:true}));return;}
  const pathname=new URL(request.url,'http://127.0.0.1').pathname;
  const file=pathname==='/web/index.html'?'index.html':pathname.replace(/^\/web\//,'');
  const target=path.resolve(webRoot,file);
  if(!target.startsWith(webRoot)||!fs.existsSync(target)){response.writeHead(404);response.end();return;}
  response.writeHead(200,{'content-type':target.endsWith('.js')?'text/javascript':target.endsWith('.css')?'text/css':'text/html'});response.end(fs.readFileSync(target));
});
(async()=>{
  const commands=[];server.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  const browser=await chromium.launch({headless:true,channel:process.env.HSR_BROWSER_CHANNEL||'chrome'});const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
  page.setDefaultTimeout(5000);
  await page.route('**/api/host',async route=>{const request=route.request().postDataJSON();commands.push(request.command);let payload={ok:true,result:{}};
    if(request.command==='character_options')payload={ok:true,result:{schema:options.schema,version:options.version,ability_method:options.ability_method,rerolls:1,level_range:options.level_range,default_level:1,advancement_levels:options.advancement_levels,races:Object.entries(options.races).map(([id,row])=>({id,...row})),classes:Object.entries(options.classes).map(([id,row])=>({id,...row})),backgrounds:Object.entries(options.backgrounds).map(([id,row])=>({id,...row})),skills:options.skills,appearance:options.appearance,class_ratings:Object.fromEntries(Object.keys(options.classes).map(id=>[id,{offense:3,defense:3,magic:1,complexity:2,role:'Role',blurb:'Blurb.'}])),race_playstyle:{}}};
    else if(request.command==='character_roll')payload={ok:true,result:{ability_roll:{method:'4d6-drop-lowest',creation_seed:request.creation_seed,roll_set:request.roll_set,rolls:[1,2,3,4,1,2].map((total,index)=>({dice:[total,3,4,5],dropped:total,total})),scores:[15,14,13,12,11,10]}}};
    else if(request.command==='preview_character')payload={ok:true,result:{character}};
    else if(request.command==='allocate_creation_seed'||request.command==='peek_creation_seed')payload={ok:true,result:{seed:{creation_seed:'00007',number:7}}};
    else if(request.command==='randomize_build')payload={ok:true,result:{build:{creation_seed:request.creation_seed,race:'orc',character_class:'warrior',background:'laborer',gender:'male',appearance:{},level:1,roll_set:0},character}};
    else if(request.command==='readout')payload={ok:true,result:{readout:{public_view:{schema:'hollow-star-public-view-1',run_id:request.run_id,room:{name:'The Town Above the Well'},party:[],available_actions:[]},public_receipt:{message:'created'}}}};
    return route.fulfill({json:payload});
  });
  try {
    const step=()=>page.locator('.cc-shell').getAttribute('data-create-step');
    const next=async()=>{await page.locator('.cc-next').click();await page.locator('.screen-exit').waitFor({state:'detached',timeout:1000}).catch(()=>{});};
    const noOverflow=async label=>{for(const viewport of [{width:1440,height:1100},{width:820,height:900},{width:390,height:844},{width:844,height:390}]){await page.setViewportSize(viewport);await page.evaluate(()=>{window.scrollTo(0,0);document.body.scrollTop=0;document.documentElement.scrollTop=0;document.querySelector('.hsr-stage-frame')?.scrollTo(0,0)});await page.waitForTimeout(30);await page.screenshot({path:path.join(root,'.local','ui-character-creation-audit',`${label}-${viewport.width}x${viewport.height}.png`)});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),true,`horizontal overflow on ${label} at ${viewport.width}x${viewport.height}`);if(viewport.width>900)assert.equal(await page.locator('.hsr-stage .cc-main').evaluate(node=>getComputedStyle(node).overflowY),'auto',`creator content must scroll inside the fixed stage on ${label}`);const hidden=await page.locator('.cc-shell button:not(:disabled),.cc-shell input:not(:disabled),.cc-shell select:not(:disabled)').evaluateAll(nodes=>nodes.filter(node=>{const r=node.getBoundingClientRect(),s=getComputedStyle(node);return s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0||r.width===0||r.height===0}).map(node=>node.outerHTML.slice(0,100)));assert.deepEqual(hidden,[],`hidden creator controls on ${label} at ${viewport.width}x${viewport.height}`);const primary=page.locator('.cc-nav .cc-next,.cc-nav [data-action="confirm-build"]').first();if(await primary.count()){await primary.evaluate(node=>node.scrollIntoView({block:'center',behavior:'instant'}));assert.equal(await primary.isVisible(),true,`primary action is reachable on ${label} at ${viewport.width}x${viewport.height}`);const outside=await primary.evaluate(node=>{const r=node.getBoundingClientRect();return r.left<0||r.right>innerWidth||r.top<0||r.bottom>innerHeight});assert.equal(outside,false,`primary action clipped on ${label} at ${viewport.width}x${viewport.height}`);}const lead=page.locator('.cc-shell .cc-lead-top');if(await lead.count()){const clipped=await lead.evaluate(node=>{const a=node.getBoundingClientRect(),b=node.closest('.cc-lead').getBoundingClientRect();return a.left<b.left-1||a.right>b.right+1||a.top<b.top-1||a.bottom>b.bottom+1});assert.equal(clipped,false,`lead summary clipped on ${label} at ${viewport.width}x${viewport.height}`);const overlap=await lead.evaluate(node=>{const art=node.querySelector('.scene-character.paperdoll-character'),copy=node.querySelector(':scope > div:last-child');if(!art||!copy||getComputedStyle(art).display==='none')return false;const a=art.getBoundingClientRect(),b=copy.getBoundingClientRect();return a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top});assert.equal(overlap,false,`rendered lead portrait overlaps text on ${label} at ${viewport.width}x${viewport.height}`);}}await page.setViewportSize({width:1440,height:1100});};
    await page.goto(base+'/web/index.html');
    // Simulation Mode connects to the local host, then lands directly on Choose Lead.
    await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();
    await page.locator('[data-action="mode:SANDBOX"]').click();
    await page.locator('.cc-fork-card[data-action="create"]').waitFor();
    await page.getByRole('button',{name:'Build a custom character',exact:true}).click();
    // Identity: the seed is prefilled from the host counter and Next is gated on a name.
    assert.equal(await step(),'identity');await page.locator('.cc-build-number strong').filter({hasText:'#00007'}).waitFor();
    assert.equal(await page.locator('.cc-next').isDisabled(),true);assert.equal(await step(),'identity');
    await page.getByLabel('Lead name').fill('Aster');await page.getByRole('button',{name:'Female',exact:true}).click();assert.equal(await page.locator('#hsr-tooltip').count(),0,'the presentation group label must not render as a floating tooltip');await noOverflow('identity');await next();
    // Ancestry: cards, portraits follow gender, detail panel explains the pick.
    assert.equal(await step(),'ancestry');await page.locator('[data-race-choice="half-elf"]').focus();assert.equal(await page.evaluate(()=>document.activeElement?.dataset.raceChoice),'half-elf','choice receives keyboard focus');await page.keyboard.press('Enter');
    assert.equal(await page.locator('[data-race-choice="half-elf"]').getAttribute('aria-pressed'),'true');
    assert.equal(await page.locator('.cc-card-art img').count(),5);assert.equal(await page.locator('.cc-card-art img').evaluateAll(images=>images.every(image=>image.complete&&image.naturalWidth>0&&image.src.endsWith('-female.png'))),true);
    assert((await page.locator('.cc-detail').innerText()).includes('Half-Elf'));
    await page.getByRole('button',{name:/Ancestry bonuses/}).click();
    await page.locator('[data-floating="STR"]').check();await page.locator('[data-floating="CON"]').check();
    await page.getByRole('button',{name:'Done',exact:true}).click();await noOverflow('ancestry');
    assert.equal(await page.locator('.cc-node.is-done').count(),1);await next();
    // Class and background.
    assert.equal(await step(),'class');await page.locator('[data-choice="class:cleric"]').click();assert((await page.locator('.cc-detail').innerText()).includes('Cleric'));await noOverflow('class');await next();
    assert.equal(await step(),'background');await page.locator('[data-choice="background:acolyte"]').click();await next();
    // Abilities: Next is gated on the roll; Surprise me only touches placement.
    assert.equal(await step(),'abilities');assert.equal(await page.locator('.cc-next').isDisabled(),true);assert.equal(await step(),'abilities');
    await page.getByRole('button',{name:'Roll ability scores',exact:true}).click();await page.locator('.cc-die-set').first().waitFor();
    assert.equal(await page.locator('.cc-die-set').count(),6);
    const strength=page.locator('[data-assign="STR"]'),otherScore=await strength.locator('option').evaluateAll(options=>options.map(option=>option.value).find(value=>value&&value!==options.find(item=>item.selected)?.value));await strength.focus();await strength.selectOption(otherScore);
    assert.equal(await page.evaluate(()=>document.activeElement?.dataset.assign),'STR','ability assignment should retain keyboard focus after updating');
    const before=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('hsr-ui-state')).draft);
    await page.getByRole('button',{name:'Surprise me',exact:true}).click();await page.waitForTimeout(80);
    const after=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('hsr-ui-state')).draft);
    assert.equal(after.race,before.race);assert.equal(after.character_class,before.character_class);assert.notEqual(JSON.stringify(after.ability_assignment),JSON.stringify(before.ability_assignment));
    await page.getByRole('button',{name:'Use recommended placement',exact:true}).click();await noOverflow('abilities');await next();
    // Training: tap to customize skills, manual spells still available.
    assert.equal(await step(),'training');await page.setViewportSize({width:844,height:390});await page.getByRole('button',{name:/Trained skills/}).click();
    const skillBody=page.locator('.cc-overlay-body'),medicine=page.locator('[data-skill-pick="Medicine"]');await medicine.scrollIntoViewIfNeeded();await medicine.focus();const skillScroll=await skillBody.evaluate(node=>node.scrollTop);await page.keyboard.press('Space');
    assert.equal(await page.evaluate(()=>document.activeElement?.dataset.skillPick),'Medicine','skill selection should retain keyboard focus after updating');assert.equal(await skillBody.evaluate(node=>node.scrollTop),await skillBody.evaluate((node,scroll)=>Math.min(scroll,node.scrollHeight-node.clientHeight),skillScroll),'skill selection should retain its scroll position or clamp it to the rebuilt overlay');
    await page.locator('[data-skill-pick="Religion"]').click();await page.getByRole('button',{name:'Done',exact:true}).click();
    await page.getByRole('button',{name:/Spells/}).click();await page.getByRole('button',{name:'Choose manually',exact:true}).click();const lastSpell=page.locator('[data-spell]').last();await lastSpell.scrollIntoViewIfNeeded();assert.equal(await lastSpell.isVisible(),true,'manual spell list can scroll to its final option');assert.equal(await page.getByRole('button',{name:'Done',exact:true}).isVisible(),true,'manual spell overlay keeps its Done action reachable');await lastSpell.focus();const spellScroll=await skillBody.evaluate(node=>node.scrollTop);await page.keyboard.press('Space');assert.equal(await page.evaluate(()=>document.activeElement?.dataset.spell),await lastSpell.getAttribute('data-spell'),'spell selection should retain keyboard focus after updating');assert.equal(await skillBody.evaluate(node=>node.scrollTop),await skillBody.evaluate((node,scroll)=>Math.min(scroll,node.scrollHeight-node.clientHeight),spellScroll),'spell selection should retain its scroll position or clamp it to the rebuilt overlay');await page.getByRole('button',{name:'Done',exact:true}).click();await page.setViewportSize({width:1440,height:1100});await noOverflow('training');await next();
    assert.equal(await step(),'look');await page.getByRole('button',{name:/Hair and build/}).click();await page.locator('[data-look^="hair_color:"]').nth(1).click();await page.getByRole('button',{name:'Done',exact:true}).click();await noOverflow('look');await next();
    // Summary: full sheet plus build notes.
    assert.equal(await step(),'summary');await page.getByText('Final sheet · not saved',{exact:true}).waitFor();
    const sheet=await page.locator('#app').innerText();for(const text of ['Half-Elf Cleric','Battle priest'])assert(sheet.includes(text),`summary missing ${text}`);
    assert.equal(commands.includes('build_character'),false,'final sheet must not save the character before confirmation');assert.equal(commands.includes('start-run'),false,'final sheet must not start a run before confirmation');
    await page.getByRole('button',{name:/Build notes/}).click();const notesText=await page.locator('[data-overlay-root]').innerText();for(const text of ['Good at','Watch out','Synergy'])assert(notesText.includes(text),`build notes missing ${text}`);await page.getByRole('button',{name:'Done',exact:true}).click();
    await noOverflow('summary');
    await page.locator('.cc-nav [data-action="step-back"]').click();assert.equal(await step(),'look','Back returns one creator step');await page.locator('[data-action="step-goto:7"]').click();await page.waitForFunction(()=>document.querySelector('.cc-shell')?.dataset.createStep==='summary');
    // Rail: earlier steps are reachable, and the whole-build randomizer lands back on the summary.
    await page.locator('[data-action="step-goto:0"]').click();assert.equal(await step(),'identity');
    await page.locator('[data-action="randomize-build"]').click();await page.waitForFunction(()=>document.querySelector('.cc-shell')?.dataset.createStep==='summary');
    await page.locator('.cc-shell .cc-confirm [data-action="confirm-build"]').click();await page.waitForFunction(()=>HollowStarUI.getStatus().phase==='ready');
    for(const command of ['character_options','allocate_creation_seed','character_roll','preview_character','randomize_build','build_character','start-run','readout'])assert(commands.includes(command),`missing ${command}`);
    assert.deepEqual(await page.evaluate(()=>HollowStarUI.getStatus().phase),'ready');
    // With an initialized host view, New Run goes straight to Choose Lead.
    await page.locator('.top-nav-menu-btn').click();await page.locator('.play-header-tools [data-action="return-menu"]').click();await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();await page.locator('[data-action="mode:SANDBOX"]').click();
    await page.locator('.cc-fork-card[data-action="create"]').waitFor();assert.equal(await page.getByRole('button',{name:'Use local gateway',exact:true}).count(),0,'connected host route should skip gateway selection');
    await page.locator('[data-action="create"] .action').click();await page.locator('.cc-shell').waitFor();assert.equal(await step(),'identity');
    // An unsaved name and step survive reload and are restored on re-entry.
    await page.getByLabel('Lead name').fill('Draftling');await next();assert.equal(await step(),'ancestry');await page.reload();
    await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();await page.locator('[data-action="mode:SANDBOX"]').click();await page.locator('.cc-fork-card[data-action="create"]').waitFor();await page.locator('[data-action="create"] .action').click();await page.locator('.cc-shell').waitFor();
    assert((await page.locator('.cc-rail').innerText()).includes('Draftling'),'restored lead name remains visible in the step rail');assert.equal(await step(),'ancestry');
    console.log(JSON.stringify({ok:true,commands}));
  } finally {await browser.close();server.close();}
})().catch(error=>{console.error(error);process.exit(1)});
