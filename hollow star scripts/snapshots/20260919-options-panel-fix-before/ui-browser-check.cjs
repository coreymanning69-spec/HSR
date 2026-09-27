/* Run with Node and Playwright available; local web server required. Uses mocked turns, never user saves. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','ui-polish');
const base=process.env.HSR_UI_URL||'http://127.0.0.1:8765';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.HSR_BROWSER_CHANNEL||'chrome'});const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const preview=JSON.parse(fs.readFileSync(path.join(root,'web','item-preview.json'),'utf8'));
 const unknown={id:'r-unknown',name:'Unidentified Rune',kind:'imprint',identified:false,slot:'ring_1',temporary:true};
 const rune={id:'r-known',name:'Steady Ring of Shelter',kind:'imprint',identified:true,slot:'ring_2',temporary:true,level:2,rarity:'rare',prefix:{name:'Steady',effect:'attack_bonus',value:1},suffix:{name:'of Shelter',effect:'ac_bonus',value:1},modifiers:[{effect:'attack_bonus',value:1},{effect:'ac_bonus',value:1}]};
 const view={schema:'hollow-star-public-view-1',run_id:'ui-isolated-fixture',mode:'DESIGN',status:'active',party:[{id:'p0',name:'Test adventurer',hp:32,max_hp:40,armor_class:16,equipment:preview.equipment}],room:{id:'1:1',name:'Public test room',visible_tells:['Visible lamp'],npcs:{smith:{npc_id:'smith',name:'Test smith',role:'smith'}}},opposition:[],inventory:[unknown,rune],imprints:{p0:{ring_2:'r-known'}},progression:{gold:24},available_actions:[{id:'inspect',label:'Inspect'}],recent_receipts:[]};
 const commands=[];let fail=false;
 await page.route('**/api/host',route=>{const request=route.request().postDataJSON();commands.push(request.command);if(request.command==='design_turn')assert.equal(request.intent,'equip p0 r-known');let payload;
 if(fail)payload={ok:false,error:{message:'Intent rejected for test'}};
 else if(request.command==='list_runs')payload={ok:true,result:{runs:[view.run_id]}};
 else if(['readout','design_turn'].includes(request.command))payload={ok:true,v:'hollow-star-transfer-capsule-1',view,receipt:{message:'Test public receipt'},run:view.run_id};
 else payload={ok:true,result:{}};
 return route.fulfill({json:payload});});
 async function overflow(label){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),label+' horizontal overflow')}
 await page.goto(base+'/#equipment');await page.getByText('Petty longsword of Ice',{exact:true}).waitFor();
 await page.locator('[data-gear="0"]').click();await page.getByText('Effects and conditions',{exact:true}).waitFor();assert((await page.locator('#modal').innerText()).includes('enemy full hp'));assert((await page.locator('#modal').innerText()).includes('PERSISTENCE'));await page.screenshot({path:path.join(out,'primary-item-desktop.png'),fullPage:true});await page.getByRole('button',{name:'Close dialog'}).click();
 assert.equal(await page.locator('.imprint-slots').getByText('Empty',{exact:true}).count(),8);
 await page.locator('#item-filter').fill('Petty');assert.equal(await page.locator('.item-card:visible').count(),1);await page.locator('#item-filter').fill('');
 for(const screen of ['room','battle','equipment','roster','residents','journal','map','options']){await page.evaluate(s=>HollowStarUI.navigate(s),screen);await overflow(screen)}
 await page.locator('#text-size').selectOption('1.15');await page.reload();assert.equal(await page.locator('#text-size').inputValue(),'1.15');await page.locator('#text-size').selectOption('1');
 await page.getByRole('button',{name:'Connect engine',exact:true}).click();await page.locator('#load-run').click();await page.waitForFunction(()=>HollowStarUI.getStatus().connected);
 await page.evaluate(()=>HollowStarUI.navigate('equipment'));assert.equal(await page.locator('.item-card').count(),4);assert((await page.locator('.imprint-slots').innerText()).includes(rune.name));
 await page.locator('[data-item="0"]').click();const unknownText=await page.locator('#modal').innerText();assert(unknownText.includes('unrevealed'));assert(!unknownText.includes('Rune modifiers'));await page.getByRole('button',{name:'Close dialog'}).click();
 await page.locator('[data-item="1"]').click();assert((await page.locator('#modal').innerText()).includes('attack_bonus'));await page.getByRole('button',{name:'Equip on Test adventurer'}).click();await page.waitForFunction(()=>!HollowStarUI.getStatus().busy);
 await page.setViewportSize({width:390,height:844});
 for(const screen of ['room','battle','equipment','roster','residents','journal','map','options']){await page.evaluate(s=>HollowStarUI.navigate(s),screen);await overflow('phone '+screen)}
 await page.evaluate(()=>HollowStarUI.navigate('equipment'));await page.screenshot({path:path.join(out,'primary-equipment-phone.png'),fullPage:true});
 await page.evaluate(()=>HollowStarUI.navigate('residents'));await page.screenshot({path:path.join(out,'primary-residents-phone.png'),fullPage:true});
 fail=true;await page.getByRole('button',{name:'Refresh',exact:true}).click();await page.waitForFunction(()=>!HollowStarUI.getStatus().busy);assert.equal(await page.evaluate(()=>HollowStarUI.getPublicView().run_id),view.run_id);fail=false;
 await page.setViewportSize({width:1440,height:1000});const before=commands.length;await page.goto(base+'/web/index.html');assert.equal(commands.length,before,'compact must not auto-connect or create');
 await page.getByRole('button',{name:'Connect engine',exact:true}).click();await page.getByRole('button',{name:'Load selected run'}).click();await page.waitForFunction(()=>HollowStarUI.getStatus().connected);
 await page.evaluate(()=>HollowStarUI.navigate('equipment'));assert.equal(await page.locator('.item-card').count(),4);await page.locator('[data-item="0"]').click();assert((await page.locator('#item-dialog').innerText()).includes('PERSISTENCE'));await page.screenshot({path:path.join(out,'compact-item-desktop.png'),fullPage:true});await page.getByRole('button',{name:'Close item details'}).click();
 await page.setViewportSize({width:390,height:844});for(const screen of ['room','battle','equipment','roster','social']){await page.evaluate(s=>HollowStarUI.navigate(s),screen);await overflow('compact phone '+screen)}
 await page.evaluate(()=>HollowStarUI.navigate('equipment'));await page.screenshot({path:path.join(out,'compact-equipment-phone.png'),fullPage:true});
 assert(!commands.includes('create_run'));assert.deepEqual(errors,[]);console.log(JSON.stringify({ok:true,desktop:[1440,1000],phone:[390,844],screens:13,commands,consoleErrors:errors,screenshots:out}));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
