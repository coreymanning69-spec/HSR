const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=path.resolve(__dirname,'..'),web=path.join(root,'web'),out=path.join(root,'.local','puppet-check');
const catalog=JSON.parse(fs.readFileSync(path.join(root,'hollowstar/content/character_creation.json'),'utf8'));
(async()=>{let browser,server;try{
fs.mkdirSync(out,{recursive:true});
server=http.createServer((req,res)=>{let f=decodeURIComponent(new URL(req.url,'http://local').pathname).replace(/^\/(web\/)?/,'');if(!f)f='index.html';const target=path.resolve(web,f);if(!target.startsWith(web+path.sep)||!fs.existsSync(target)){res.writeHead(404);res.end();return;}res.setHeader('content-type',f.endsWith('.js')?'text/javascript':f.endsWith('.css')?'text/css':f.endsWith('.png')?'image/png':'text/html');res.end(fs.readFileSync(target));});
server.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
browser=await chromium.launch({headless:true,channel:'chrome'});const page=await browser.newPage({viewport:{width:1300,height:950}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(`http://127.0.0.1:${server.address().port}/`);
await page.evaluate(async catalog=>{
 const {dollModel,characterFigure}=await import('/paperdoll.js');const {SkeletalRig,drawPuppet}=await import('/puppet-renderer.js');
 const {syncPuppets,destroyPuppets,puppetDiagnostics,figureSocket}=await import('/puppet-dom.js');const {TraversalController}=await import('/traversal-controller.js');
 const {FXEngine,reconcileAuras}=await import('/fx-engine.js');
 window.puppetTest={dollModel,characterFigure,SkeletalRig,drawPuppet,syncPuppets,destroyPuppets,puppetDiagnostics,figureSocket,catalog};
 const check=(v,m)=>{if(!v)throw Error(m);};
 const rig=new SkeletalRig({scale:2});rig.applyPose('guard');rig.update(0,100,180,1);const right=rig.getSocket('main_hand');rig.update(0,100,180,-1);const left=rig.getSocket('main_hand');check(Math.abs(right.x+left.x-200)<1e-6,'mirrored socket');check(right.y===left.y,'mirrored height');
 const traversal=new TraversalController();const result=traversal.update('p0',{position:[10,0,0],movement_mode:'RUN'},[{position:[10,0],kind:'wall',height:40,required_mode:['climb']}],rig);check(result.elevationZ===0&&result.pose==='idle','no invented traversal');
 const fx=new FXEngine();reconcileAuras(fx,'p0',{conditions:['burning']});check(fx.auras.size===1,'aura appears');reconcileAuras(fx,'p0',{});check(fx.auras.size===0,'aura clears');
 const defaults=Object.fromEntries(Object.entries(catalog.appearance.fields).map(([k,v])=>[k,v.options[0]]));
 const appearance={...defaults,hair_style:catalog.appearance.fields.hair_style.options.find(x=>x.id==='braided'),outfit:catalog.appearance.fields.outfit.options.find(x=>x.id==='coat')};
 const equipment=[{presentation:{silhouette:'sword',material:'steel',rarity:'mundane'}}];
 const base={id:'p0',name:'Aster',race_id:'human',gender:'other',appearance,equipment};window.puppetTest.base=base;
 const render=(actor,pose='idle',facing=1)=>{const c=document.createElement('canvas');c.width=220;c.height=280;const model=dollModel(actor,{pose}),r=new SkeletalRig({scale:2});r.time=180;r.applyPose(pose,{progress:.5,weapon:model.weapon});r.update(0,110,260,facing);drawPuppet(c.getContext('2d'),r,model);return c;};
 window.puppetTest.render=render;
 // Every available option must affect pixels when it is not covered by equipment.
 const variants={};
 for(const [field,spec]of Object.entries(catalog.appearance.fields)){
  const signatures=spec.options.map(option=>render({...base,appearance:{...defaults,[field]:option}}).toDataURL());
  check(new Set(signatures).size===spec.options.length,`indistinguishable ${field} options`);variants[field]=signatures.length;
 }
 check(dollModel({...base,equipment:[]}).weapon==='none','unarmed must not invent sword');
 document.body.innerHTML='<h1>Shared character sprite — creation and gameplay</h1><main id="gallery"></main>';
 const css=document.createElement('style');css.textContent='body{background:#121d2e!important;color:#e7ddc4!important;overflow:auto!important;height:auto!important;margin:20px!important}#gallery{display:flex;flex-wrap:wrap;gap:12px}article{background:linear-gradient(#243449,#172331);border:1px solid #58657a;border-radius:12px;text-align:center;width:190px;padding:8px}article canvas{width:180px;height:230px}h1{font:24px Georgia}';document.head.append(css);
 const add=(actor,pose,facing)=>{const el=document.createElement('article');el.append(render(actor,pose,facing));el.append(`${actor.race_id} · ${actor.gender} · ${pose}`);document.querySelector('#gallery').append(el);};
 for(const [i,race]of ['human','elf','half-elf','orc','goblin'].entries())add({...base,race_id:race,gender:['female','male','other'][i%3],appearance:{...appearance,skin_tone:catalog.appearance.fields.skin_tone.options[i*2],hair_color:catalog.appearance.fields.hair_color.options[i]}},'idle',1);
 for(const pose of ['run','attack','guard','jump','down'])add(base,pose,pose==='guard'?-1:1);
 window.puppetTest.variants=variants;
},catalog);
await page.screenshot({path:path.join(out,'puppet-gallery.png'),fullPage:true});
// Real DOM adapter, equipment swap, resize, missing art, and loop teardown.
await page.evaluate(async()=>{
 const t=puppetTest;const check=(v,m)=>{if(!v)throw Error(m);};
 document.body.innerHTML='<main id="fixtures" style="position:relative;width:1000px;height:420px"></main>';
 const mount=document.querySelector('#fixtures');
 const actor={...t.base,name:'DOM fixture',base_type:'canvas'};
 for(let i=0;i<20;i++){mount.innerHTML=t.characterFigure(actor);t.syncPuppets(mount,{reducedMotion:()=>true});}
 await new Promise(requestAnimationFrame);check(t.puppetDiagnostics().mounted===1,'one mount after repeated render');
 const node=mount.querySelector('[data-puppet-model]');node.style.cssText='position:relative;left:0;bottom:0;width:220px;height:280px;transform:none';
 await new Promise(requestAnimationFrame);
 const actual=node.querySelector('canvas');const model=t.dollModel(actor);const expected=document.createElement('canvas');expected.width=actual.width;expected.height=actual.height;
 // The canvas overhangs the box sideways (styles.css); draw in box coordinates.
 check(actual.width===Math.round(220*1.7)&&actual.offsetLeft===-77,'puppet canvas overhangs sideways');expected.getContext('2d').translate(77,0);
 const {puppetStyle}=await import('/puppet-renderer.js');const rig=new t.SkeletalRig({scale:Math.min(220/100,280/123)*puppetStyle(model).height});
 rig.applyPose('idle',{weapon:model.weapon,bodyWidth:puppetStyle(model).width,reducedMotion:true});rig.update(0,110,280*.94);t.drawPuppet(expected.getContext('2d'),rig,model);
 check(expected.toDataURL()===actual.toDataURL(),'DOM uses exact shared compositor pixels');
 const before=actual.toDataURL();node.dataset.puppetModel=JSON.stringify(t.dollModel({...actor,equipment:[{presentation:{silhouette:'axe',rarity:'mundane'}}]}));t.syncPuppets(mount);await new Promise(requestAnimationFrame);check(actual.toDataURL()!==before,'equipment updates pixels');
 node.style.width='320px';await new Promise(requestAnimationFrame);check(actual.width===Math.round(320*1.7),'resize updates canvas');
 const socket=t.figureSocket(node,'main_hand',mount);check(Number.isFinite(socket.x)&&socket.x>0,'live socket coordinate');
 node.dataset.beat='impact';await new Promise(requestAnimationFrame);check(node.dataset.renderedPose==='hit','combat beat drives puppet');delete node.dataset.beat;
 // Every director beat reaches a real pose; gestures ride data-beat="gesture:<name>".
 const {BEAT_POSES,GESTURES,SOCKET_NAMES}=await import('/puppet-renderer.js');
 for(const [beat,pose] of [...Object.entries(BEAT_POSES),...GESTURES.map(g=>['gesture:'+g,g])]){
   node.dataset.beat=beat;await new Promise(requestAnimationFrame);check(node.dataset.renderedPose===pose,`beat ${beat} drives ${pose}, got ${node.dataset.renderedPose}`);}
 delete node.dataset.beat;await new Promise(requestAnimationFrame);
 // The strike's contact frame reaches the director as an event.
 let contacts=0;node.addEventListener('rig:contact',()=>contacts++);
 node.dataset.beat='strike';await new Promise(r=>setTimeout(r,60));check(contacts===1,'strike reports contact once');delete node.dataset.beat;
 // Anchors: every socket is live; a weapon tip and a spell focus exist off the hand.
 const sr=new t.SkeletalRig({scale:2});sr.applyPose('cast_channel',{weapon:'staff'});sr.update(0,100,200,1);
 for(const n of SOCKET_NAMES){const s=sr.getSocket(n);check(Number.isFinite(s.x)&&Number.isFinite(s.y),`socket ${n}`);}
 const tip=sr.getSocket('weapon_tip'),hand=sr.getSocket('main_hand');check(Math.hypot(tip.x-hand.x,tip.y-hand.y)>40,'staff tip sits past the hand');
 check(t.figureSocket(node,'weapon_tip',mount)&&t.figureSocket(node,'focus',mount),'dom publishes spell anchors');
 // Upper/lower layering: casting on the run keeps the running legs.
 const run=new t.SkeletalRig();run.time=500;run.applyPose('run');const legs=run.bones.get('left_thigh').localAngle;
 run.applyPose('cast',{lower:'run'});check(run.bones.get('left_thigh').localAngle===legs&&run.pose==='cast','cast layers over run');
 node.dataset.beat='impact';await new Promise(requestAnimationFrame);delete node.dataset.beat;
 const still=actual.toDataURL();await new Promise(r=>setTimeout(r,100));check(actual.toDataURL()!==still,'return from hit pose');const fixed=actual.toDataURL();await new Promise(r=>setTimeout(r,100));check(actual.toDataURL()===fixed,'reduced motion freezes idle');
 const poses=['idle','run','attack','guard','jump','climb','vault','hit','down'];
 for(const pose of poses)for(const facing of [-1,1]){
   mount.innerHTML=`<div data-puppet-preview data-preview-pose="${pose}" data-preview-facing="${facing}">${t.characterFigure(actor)}</div>`;
   const n=mount.querySelector('[data-puppet-model]');n.style.cssText='position:relative;left:0;bottom:0;width:220px;height:280px;transform:none';t.syncPuppets(mount);await new Promise(requestAnimationFrame);
   const c=n.querySelector('canvas'),pixels=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
   let edge=0;for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++)if((x<1||x>=c.width-1||y<1||y>=c.height-1)&&pixels[(y*c.width+x)*4+3])edge++;
   check(edge===0,`clipped ${pose} ${facing}`);
 }
 // Doran is a layered rig: parts on the shared skeleton, no frame art to swap.
 mount.innerHTML=t.characterFigure({identity:'doran',name:'Doran'});const dn=mount.querySelector('[data-puppet-model]');
 dn.style.cssText='position:relative;left:0;bottom:0;width:220px;height:280px;transform:none';t.syncPuppets(mount,{reducedMotion:()=>false});await new Promise(r=>setTimeout(r,120));
 check(dn.dataset.dollBase==='rig'&&dn.classList.contains('doll-rig')&&dn.dataset.loadout==='cleaver'&&!dn.querySelector('img'),'doran draws through his rig');
 const dc=dn.querySelector('canvas');check(dc.clientWidth>220&&dc.offsetLeft<0&&dc.offsetTop<0,'rig canvas overhangs the figure box');
 const dp=dc.getContext('2d').getImageData(0,0,dc.width,dc.height).data;let ink=0;for(let i=3;i<dp.length;i+=4)if(dp[i])ink++;check(ink>4000,'rig paints');
 check(dn.dataset.renderedPose==='rest','idle doran rests on the planted cleaver');
 dn.dataset.beat='windup';await new Promise(r=>setTimeout(r,80));check(dn.dataset.renderedPose==='windup','windup beat drives rig');
 dn.dataset.beat='impact';await new Promise(r=>setTimeout(r,80));check(dn.dataset.renderedPose==='hit','hit beat drives rig');delete dn.dataset.beat;
 const ds=t.figureSocket(dn,'main_hand',mount);check(Number.isFinite(ds.x)&&Number.isFinite(ds.y),'rig socket');
 t.destroyPuppets();check(t.puppetDiagnostics().mounted===0&&!t.puppetDiagnostics().scheduled,'scheduler teardown');
 const {createArcadeCanvas}=await import('/arcade-canvas.js');
 mount.innerHTML='<div id="arena" style="width:900px"></div>';const arcade=createArcadeCanvas(document.querySelector('#arena'));
 arcade.setOptions({reducedMotion:true,sceneKey:'fixture:1'});arcade.setActors([{...actor,id:'p0',hp:20,max_hp:20},{id:'p1',name:'Doran',identity:'doran',hp:370,max_hp:370},{...actor,id:'e0',hp:10,max_hp:10}]);
 arcade.setState({frame:10,bounds:{x:[0,120]},entities:{p0:{position:[50,30,0],velocity:[1,0],movement_mode:'run',facing:1},p1:{position:[35,30,0],facing:1,attack_ticks:2},e0:{team:'opposition',position:[65,30,0],movement_mode:'run',facing:-1}},obstacles:[],projectiles:[]});
 await new Promise(requestAnimationFrame);window.puppetTest.arcade=arcade;
});
await page.screenshot({path:path.join(out,'puppet-arcade.png'),fullPage:true});
await page.evaluate(()=>{puppetTest.arcade.setOptions({sceneKey:'fixture:2'});puppetTest.arcade.setState({frame:0,entities:{},obstacles:[],projectiles:[]});puppetTest.arcade.destroy();});
console.log(await page.evaluate(()=>puppetTest.variants));
assert.deepEqual(errors,[]);console.log('PASS rig, all appearance options, traversal authority, FX removal, unarmed rendering and the Doran layered rig. '+out);
}finally{await browser?.close();await new Promise(r=>server?server.close(r):r());}})().catch(e=>{console.error(e);process.exitCode=1;});
