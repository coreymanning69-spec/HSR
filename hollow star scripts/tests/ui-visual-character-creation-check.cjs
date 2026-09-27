/* Visual workshop character creator smoke test. Host responses are mocked; no profile or run is saved. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const http=require('node:http');const path=require('node:path');
const root=path.resolve(__dirname,'..'),webRoot=path.join(root,'web');
const evidenceRoot=path.join(root,'.local','ui-character-creation-audit');fs.mkdirSync(evidenceRoot,{recursive:true});
const server=http.createServer((request,response)=>{
  const url=new URL(request.url,'http://127.0.0.1');
  if(url.pathname==='/api/health'){response.writeHead(200,{'content-type':'application/json'});response.end(JSON.stringify({ok:true}));return;}
  if(url.pathname==='/api/host'){
    const chunks=[];request.on('data',chunk=>chunks.push(chunk));request.on('end',()=>{
      const req=JSON.parse(Buffer.concat(chunks).toString('utf8'));let payload={ok:true,result:{}};
      if(req.command==='boot')payload={ok:true,result:{ready:true}};
      else if(req.command==='character_options')payload={ok:true,result:{schema:options.schema,version:options.version,ability_method:options.ability_method,rerolls:1,level_range:options.level_range,default_level:1,advancement_levels:options.advancement_levels,races:Object.entries(options.races).map(([id,row])=>({id,...row})),classes:Object.entries(options.classes).map(([id,row])=>({id,...row})),backgrounds:Object.entries(options.backgrounds).map(([id,row])=>({id,...row})),skills:options.skills}};
      else if(req.command==='allocate_creation_seed'||req.command==='peek_creation_seed')payload={ok:true,result:{seed:{creation_seed:'00007',number:7}}};
      else if(req.command==='character_roll')payload={ok:true,result:{ability_roll:{method:'4d6-drop-lowest',creation_seed:req.creation_seed,roll_set:req.roll_set,rolls:[1,2,3,4,1,2].map((total,index)=>({dice:[total,3,4,5],dropped:total,total})),scores:[15,14,13,12,11,10]}}};
      else if(req.command==='preview_character')payload={ok:true,result:{character}};
      response.writeHead(200,{'content-type':'application/json'});response.end(JSON.stringify(payload));
    });return;
  }
  const relative=url.pathname==='/'||url.pathname==='/web/index.html'?'index.html':url.pathname.replace(/^\/(?:web\/)?/,'');
  const target=path.resolve(webRoot,relative);
  if(!target.startsWith(webRoot)||!fs.existsSync(target)){response.writeHead(404);response.end();return;}
  const type=target.endsWith('.js')?'text/javascript':target.endsWith('.css')?'text/css':target.endsWith('.svg')?'image/svg+xml':target.endsWith('.png')?'image/png':'text/html';
  response.writeHead(200,{'content-type':type});response.end(fs.readFileSync(target));
});
const options=JSON.parse(fs.readFileSync(path.join(root,'hollowstar','content','character_creation.json'),'utf8'));
const character={profile:{name:'Aster',race:'Half-Elf',race_id:'half-elf',character_class:'Cleric',class_id:'cleric',level:1,
  ability_scores:{STR:10,DEX:12,CON:11,INT:10,WIS:15,CHA:12},max_hp:9,armor_class:16,speed:30,proficiency_bonus:2,
  skill_bonuses:{History:2,Insight:4},features:['Spellcasting','Channel Grace'],interaction_tags:['human','elf','bridge_kin'],
  known_spells:['Guidance@5e','Light@5e'],background:{name:'Acolyte',starting_gold:16},origin_item:{name:'family letter'},heirloom_item:{}},
  receipt:{race_bonuses:{CHA:2},floating_bonuses:['STR','CON'],spell_budget:5,spell_points_spent:2},build_hash:'a'.repeat(64)};
const view={schema:'hollow-star-public-view-1',run_id:'web-aster-run',room:{name:'The Town Above the Well',apparent_function:'A town at the threshold of the Reliquary.'},party:[{id:'p0',name:'Aster',hp:9,max_hp:9,armor_class:16,equipment:[]}],opposition:[],progression:{hsr_rank:1,rank_xp:0,gold:24,platinum:0,rooms_cleared:0},inventory:[],available_actions:[],recent_receipts:[]};
(async()=>{
  server.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  const browser=await chromium.launch({headless:true,channel:process.env.HSR_BROWSER_CHANNEL||'chrome'});const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(5000);
  try {
    await page.goto(base+'/web/index.html');
    await page.getByRole('button',{name:'Simulation Mode',exact:true}).waitFor();
    await page.getByRole('button',{name:'Simulation Mode',exact:true}).click();
    await page.locator('[data-action="mode:SANDBOX"]').click();
    await page.locator('.cc-fork-card[data-action="create"]').waitFor();
    await page.getByRole('button',{name:'Build a custom character',exact:true}).click();
    await page.locator('.cc-shell[data-create-step="identity"]').waitFor();
    await page.getByLabel('Lead name').fill('Aster');
    const next=async()=>{await page.locator('.cc-next').click();await page.waitForTimeout(260);};
    await next();
    await page.locator('[data-race-choice="half-elf"]').click();
    await page.getByRole('button',{name:/Ancestry bonuses/}).click();
    await page.locator('[data-floating="STR"]').check();await page.locator('[data-floating="CON"]').check();
    await page.getByRole('button',{name:'Done',exact:true}).click();await next();
    await page.locator('[data-choice="class:cleric"]').click();await next();
    await page.locator('[data-choice="background:acolyte"]').click();await next();
    await page.getByRole('button',{name:'Roll ability scores',exact:true}).click();
    await page.locator('.cc-die-set').first().waitFor();
    await page.getByRole('button',{name:/Next: Training/}).click();await page.waitForTimeout(260);
    await page.getByRole('button',{name:/Trained skills/}).click();
    await page.locator('[data-skill-pick="History"]').click();await page.locator('[data-skill-pick="Insight"]').click();
    await page.getByRole('button',{name:'Done',exact:true}).click();
    await page.getByRole('button',{name:/Spells/}).click();
    await page.getByRole('button',{name:'Choose manually',exact:true}).click();
    await page.locator('[data-spell="Guidance@5e"]').click();await page.locator('[data-spell="Light@5e"]').click();
    await page.getByRole('button',{name:'Done',exact:true}).click();await next();
    await next();
    await page.getByText('Final sheet · not saved',{exact:true}).waitFor();assert((await page.locator('#app').innerText()).includes('Half-Elf Cleric'));
    assert.equal(await page.locator('.cc-shell .cc-confirm [data-action="confirm-build"]').count(),1);
    await page.screenshot({path:path.join(evidenceRoot,'visual-summary-1440x1100.png'),fullPage:true});
    console.log(JSON.stringify({ok:true,commands:'host-backed'}));
  } finally {await browser.close();server.closeAllConnections?.();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exit(1)});
