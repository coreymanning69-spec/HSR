/* Doran: actual host Grand Cleave receipt, continuous mirrored rig, and burst playback. */
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),web=path.join(root,'web'),out=path.join(root,'.local','doran-combat-proof');
const python='C:/Users/ACore/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
(async()=>{let browser,server;try{
 fs.mkdirSync(out,{recursive:true});
 const seed=spawnSync(python,['-B','-'],{cwd:root,encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'},input:`
import json
from unittest.mock import patch
from tests.test_doran_combat import DoranCombatTests
from hollowstar import tactical as t
from hollowstar.view_model import public_event_summary
f=DoranCombatTests();f.setUp()
try:
 r=f.ready()
 with patch.object(r.rng,'d20',return_value=20):
  event=t.apply(r,{'type':'grand_cleave','actor':'p0','facing':'east'})
 print(json.dumps(public_event_summary(event)))
finally:f.tearDown()
`});assert.equal(seed.status,0,seed.stderr);
 const receipt=JSON.parse(seed.stdout.trim());fs.writeFileSync(path.join(out,'host-grand-cleave.json'),JSON.stringify(receipt,null,2));
 server=http.createServer((req,res)=>{const url=new URL(req.url,'http://local');if(url.pathname==='/'){res.setHeader('content-type','text/html; charset=utf-8');res.end('<html><head><link rel="stylesheet" href="/styles.css"></head><body style="background:#111823;color:#edf0f6;margin:20px"><h1>Doran · combat rig proof</h1><div id="gallery" style="display:grid;grid-template-columns:repeat(2,620px);gap:12px"></div><div id="stage" class="combat-stage" style="position:relative;width:1200px;height:340px"></div></body></html>');return;}
 const f=path.resolve(web,decodeURIComponent(url.pathname.slice(1)));if(!f.startsWith(web+path.sep)||!fs.existsSync(f)){res.writeHead(404);res.end();return;}
 res.setHeader('content-type',f.endsWith('.js')?'text/javascript':f.endsWith('.css')?'text/css':'image/png');res.end(fs.readFileSync(f));});
 server.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
 browser=await chromium.launch({headless:true,channel:'chrome'});const page=await browser.newPage({viewport:{width:1300,height:2400}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));await page.goto(`http://127.0.0.1:${server.address().port}/`);
 const geometry=await page.evaluate(async()=>{
  const {SkeletalRig}=await import('/skeletal-rig.js'),D=await import('/doran-rig.js'),{swingTiming}=await import('/stage-world.js');
  const results={maxGripError:0,maxBoneError:0,tempo:[],elbows:[],gallery:[]};
  for(const style of ['chop','cleave','sweep','rise']){const a=swingTiming(style,'cleaver'),b=swingTiming(style,'sword'),d=swingTiming(style,'daggers');if(a.ms!==b.ms||d.ms>=a.ms*.5)throw Error('weapon tempo '+style);results.tempo.push({style,cleaver:a.ms,sword:b.ms,daggers:d.ms});}
  for(const facing of [-1,1])for(const style of Object.keys(D.DORAN_SWINGS)){
   const rig=new SkeletalRig({scale:1.5}),T=D.DORAN_SWINGS[style],canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');
   for(let now=1000;now<1000+T.ms+T.hitstop;now+=8){
    const sockets=D.drawDoran(ctx,rig,{alive:true,loadout:'cleaver'},{x:0,y:0,dt:8,now,pose:'ready',carry:'ready',swing:style,swingAt:1000,facing,paint:false,idleFidgets:false});
    for(const side of ['left','right']){const u=rig.bones.get(side+'_upper_arm'),l=rig.bones.get(side+'_lower_arm');results.maxBoneError=Math.max(results.maxBoneError,Math.abs(Math.hypot(u.endX-u.x,u.endY-u.y)-u.length*rig.scale),Math.abs(Math.hypot(l.endX-l.x,l.endY-l.y)-l.length*rig.scale));}
    if(rig.doran.ch.sup>.98){const ch=rig.doran.ch,g=Math.max(D.CLEAVER.handle/2+1,D.CLEAVER.grips.reach+(D.CLEAVER.grips.choke-D.CLEAVER.grips.reach)*ch.gr),along=(g>=D.CLEAVER.handle/2?-1:1)*D.CLEAVER.support*rig.scale;
     const dx=-Math.sin(ch.bl)*along*facing,dy=Math.cos(ch.bl)*along;
     results.maxGripError=Math.max(results.maxGripError,Math.hypot(sockets.off_hand.x-sockets.main_hand.x-dx,sockets.off_hand.y-sockets.main_hand.y-dy));}
   }
  }
  const samples=[['Guard','guard','cleaver',1],['Guard mirrored','guard','cleaver',-1],['Windup','windup','cleaver',1],['Contact','strike','cleaver',1],['Dagger main hand','strike','daggers',1],['Dagger off hand','strike','daggers',1],['Grand Cleave contact','grand_cleave','cleaver',1],['Grand Cleave mirrored','grand_cleave','cleaver',-1]];
  for(const [label,pose,loadout,facing] of samples){const box=document.createElement('section');box.style.background='#233040';box.innerHTML='<h2 style="padding-left:16px">'+label+'</h2>';const c=document.createElement('canvas');c.width=620;c.height=510;box.append(c);document.querySelector('#gallery').append(box);const rig=new SkeletalRig({scale:1.6});let sockets;
   const T=D.DORAN_SWINGS.grand_cleave;
   for(let i=0;i<40;i++)D.drawDoran(c.getContext('2d'),rig,{alive:true,loadout},{x:310,y:370,dt:16,now:300+i*16,pose:'ready',loadout,facing,paint:false,idleFidgets:false});
   const count=pose==='strike'?(loadout==='daggers'?4:9):100;
   for(let i=0;i<count;i++){const now=pose==='grand_cleave'?1000+Math.min(i*8,T.ms*T.contact):1000+i*16;sockets=D.drawDoran(c.getContext('2d'),rig,{alive:true,loadout},{x:310,y:370,dt:16,now,pose:pose==='grand_cleave'?'ready':pose,beat:pose==='strike'?'strike':'',loadout,facing,swing:pose==='grand_cleave'?'grand_cleave':'',swingAt:1000,attackAnimation:label.includes('off hand')?'dagger_offhand':'dagger_main',idleFidgets:false,paint:false});}
   c.getContext('2d').clearRect(0,0,c.width,c.height);
   D.drawDoran(c.getContext('2d'),rig,{alive:true,loadout},{x:310,y:370,dt:0,now:pose==='grand_cleave'?1000+T.ms*T.contact:pose==='strike'?1000+(count-1)*16:2584,pose:pose==='grand_cleave'?'ready':pose,beat:pose==='strike'?'strike':'',loadout,facing,swing:pose==='grand_cleave'?'grand_cleave':'',swingAt:1000,attackAnimation:label.includes('off hand')?'dagger_offhand':'dagger_main',idleFidgets:false});
   results.gallery.push(label);
  }
  await import('/ui-components.js');const {characterFigure}=await import('/paperdoll.js'),P=await import('/puppet-dom.js'),{createCombatDirector}=await import('/combat-director.js');
  const stage=document.querySelector('#stage');stage.innerHTML=['p0','e0','e1'].map((id,i)=>characterFigure({id,name:id==='p0'?'Doran':'Target '+i,identity:id==='p0'?'doran':'custom',hp:100,max_hp:100,equipment:[]},'combatant','combat',{attrs:{'data-stage-actor':id}})).join('');
  [...stage.children].forEach((n,i)=>Object.assign(n.style,{position:'absolute',left:(i*340)+'px',top:'30px',width:'200px',height:'270px'}));P.syncPuppets(stage);
  window.proof={director:createCombatDirector({getStage:()=>stage,settings:()=>({fillMissing:false,speed:4})}),stage,P};
  return results;
 });
 await page.screenshot({path:path.join(out,'doran-poses.png'),fullPage:true});
 assert(geometry.maxBoneError<1e-6,JSON.stringify(geometry));assert(geometry.maxGripError<1.1,JSON.stringify(geometry));
 await page.screenshot({path:path.join(out,'doran-poses.png'),fullPage:true});
 const playback=await page.evaluate(async receipt=>{
  const d=window.proof.director,view={run_id:'proof',recent_receipts:[],party:[],opposition:[]};d.ingest(null,view);
  d.ingest(view,{...view,recent_receipts:[receipt]});d.kick();const deadline=performance.now()+6000;
  while((d.playing||d.pending)&&performance.now()<deadline)await new Promise(r=>setTimeout(r,30));
  if(d.playing)throw Error('Grand Cleave playback did not finish');
  const labels=[...document.querySelectorAll('.combat-float')].map(n=>n.textContent);
  const before=d.history.length;
  const burst=Array.from({length:13},(_,i)=>({type:'attack',source:'p0',target:'e0',mode:'dagger',roll:{natural:2,total:18,bonus:16,success:false},presentation:{actor_id:'p0',action:'attack',weapon_mode:'dagger',animation:{attack:'melee_1h'}},evidence:{serial:i}}));
  const ingested=d.ingest(view,{...view,recent_receipts:burst});const pending=d.pending;
  const quiet=(await import('/combat-director.js')).createCombatDirector({getStage:()=>window.proof.stage,reducedMotion:()=>true});quiet.ingest(null,{...view,run_id:'quiet'});quiet.ingest(null,{...view,run_id:'quiet',recent_receipts:burst});quiet.kick();
  while(quiet.playing||quiet.pending)await new Promise(r=>setTimeout(r,20));
  return {labels,grandHistory:d.history.slice(0,before),ingested,pending,playedBurst:quiet.history.length,loadoutCleared:!document.querySelector('[data-stage-actor="p0"]').dataset.combatLoadout};
 },receipt);
 assert.equal(playback.pending,13,JSON.stringify(playback));assert.equal(playback.playedBurst,13);assert.equal(playback.grandHistory.length,1);assert(playback.loadoutCleared);assert.equal(errors.length,0,errors.join('\n'));
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({geometry,playback,errors},null,2));
 console.log('PASS Doran mirrored arm geometry, both grips, longsword Cleaver tempo, fast daggers, host Grand Cleave, 13 retained and played attacks. '+out);
}finally{if(browser)await browser.close();if(server)await new Promise(r=>server.close(r));}})().catch(e=>{console.error(e);process.exitCode=1;});
