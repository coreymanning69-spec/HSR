const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=path.resolve(__dirname,'..'),web=path.join(root,'web'),out=path.join(root,'.local','magic-check');
(async()=>{let browser,server;try{
 fs.mkdirSync(out,{recursive:true});
 server=http.createServer((req,res)=>{const url=new URL(req.url,'http://local');if(url.pathname==='/'){res.setHeader('content-type','text/html; charset=utf-8');res.end('<html><head></head><body></body></html>');return;}
 const target=path.resolve(web,decodeURIComponent(url.pathname.slice(1)));if(!target.startsWith(web+path.sep)||!fs.existsSync(target)){res.writeHead(404);res.end();return;}
 res.setHeader('content-type',target.endsWith('.js')?'text/javascript':target.endsWith('.css')?'text/css':'image/png');res.end(fs.readFileSync(target));});
 server.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
 browser=await chromium.launch({headless:true,channel:'chrome'});const page=await browser.newPage({viewport:{width:1250,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));await page.goto(`http://127.0.0.1:${server.address().port}/`);
 await page.evaluate(async()=>{
  const {SkeletalRig}=await import('/skeletal-rig.js'),{drawPuppet}=await import('/puppet-renderer.js');
  const {dollModel,characterFigure}=await import('/paperdoll.js'),{staffSockets,focusSockets,castingProfile}=await import('/magic-articulation.js');
  const {FXEngine}=await import('/fx-engine.js');const check=(v,m)=>{if(!v)throw Error(m);};
  window.magic={characterFigure,castingProfile};
  const actor={id:'p0',name:'Caster',race_id:'human',equipment:[],appearance:{outfit:{id:'robe'},hair_style:{id:'braided'}}};window.magic.actor=actor;
  const styles=['plain','runed','weathered','ceremonial','heavy'];
  for(const style of styles)for(const facing of [-1,1])for(const stance of ['aim','gather','overhead','mend','ward']) {
   const rig=new SkeletalRig({scale:1.6}),casting={stance,hands:stance==='aim'?1:2};
   rig.applyPose('cast_release',{weapon:'staff',staffStyle:style,casting,progress:.5});rig.update(0,140,260,facing);
   const hand=rig.getSocket('main_hand'),tip=rig.getSocket('weapon_tip');
   check(Math.abs(Math.hypot(tip.x-hand.x,tip.y-hand.y)-staffSockets(style).length*rig.scale)<1e-6,'staff tip matches art length');
   if(casting.hands===2){const h=rig.bones.get('right_hand'),g=staffSockets(style).grip,a=h.angle-.15,l=rig.getSocket('off_hand');
    const x=140+(h.x-Math.sin(a)*g*rig.scale)*facing,y=260+h.y+Math.cos(a)*g*rig.scale;
    check(Math.hypot(l.x-x,l.y-y)<1,'support hand on shaft');}
  }
  // Regression matrix: mirrored carry/aim, short wand tips, palm emission and elbow direction.
  for(const weapon of ['staff','wand','none','sword'])for(const facing of [-1,1])for(const bodyWidth of [.76,1,1.31]) {
   for(const source of ['hands','implement'])for(const hands of [1,2])for(const stance of ['aim','gather','overhead','mend','ward']) {
    const rig=new SkeletalRig({scale:1.4}),casting={stance,hands,source};
    rig.applyPose('cast_release',{weapon,casting,bodyWidth,progress:.5});rig.update(0,180,280,facing);
    const focus=rig.getSocket('focus'),main=rig.getSocket('main_hand'),off=rig.getSocket('off_hand'),tip=rig.getSocket('weapon_tip');
    if(source==='implement'&&['staff','wand'].includes(weapon)) {
     check(Math.hypot(focus.x-tip.x,focus.y-tip.y)<1e-6,'implement casts from its tip');
    } else {
     const expected=hands===2?{x:(main.x+off.x)/2,y:(main.y+off.y)/2}:weapon==='none'?main:off;
     check(Math.hypot(focus.x-expected.x,focus.y-expected.y)<1e-6,'hands cast from palms despite equipped weapon');
     if(weapon!=='none'&&hands===2)check(rig.bones.get('right_weapon').parent==='pelvis','weapon stowed for two palms');
     for(const side of hands===2?['right','left']:[weapon==='none'?'right':'left']) {
      const shoulder=rig.bones.get(side+'_shoulder'),arm=rig.bones.get(side+'_upper_arm'),hand=rig.bones.get(side+'_hand');
      check(hand.x>shoulder.x,'casting palm reaches forward, not inverted');
      const cross=(hand.x-shoulder.x)*(arm.endY-shoulder.y)-(hand.y-shoulder.y)*(arm.endX-shoulder.x);
      check(cross>=-1e-6,'elbow bends under the hand target');
     }
    }
    if(weapon==='wand') {
     const grip=rig.getSocket('weapon_main');
     check(Math.abs(Math.hypot(tip.x-grip.x,tip.y-grip.y)-focusSockets('wand').length*rig.scale)<1e-6,'wand tip matches short art');
     check(!rig.twoHanded(),'wand never borrows staff support grip');
    }
   }
   if(['staff','wand'].includes(weapon))for(const pose of ['idle','ready','guard']) {
    const rig=new SkeletalRig();rig.applyPose(pose,{weapon,bodyWidth});rig.update(0,180,280,facing);
    const hand=rig.getSocket('main_hand'),tip=rig.getSocket('weapon_tip'),chest=rig.getSocket('chest');
    check(hand.y>chest.y+10,'carry grip lowered below chest');
    check((tip.x-hand.x)*facing>Math.abs(tip.y-hand.y),'carry tip points mostly forward');
   }
  }
  for(const style of styles)for(const bodyWidth of [.76,1,1.31])for(const pose of ['idle','ready','guard','attack','dodge','crit']) {
   const rig=new SkeletalRig();rig.applyPose(pose,{weapon:'staff',staffStyle:style,bodyWidth,progress:.5});rig.update(0,0,0);
   const h=rig.bones.get('right_hand'),g=staffSockets(style).grip,a=h.angle-.15,l=rig.getSocket('off_hand');
   check(Math.hypot(l.x-(h.x-Math.sin(a)*g),l.y-(h.y+Math.cos(a)*g))<.02,'staff support stays on shaft through action/reaction');
  }
  for(const weapon of ['staff','wand','sword'])for(const source of ['hands','implement']) {
   const rig=new SkeletalRig();rig.applyPose('idle',{weapon});rig.update(0,0,0);
   const snap=rig.snapshot(),hand=rig.getSocket('main_hand'),tip=rig.getSocket('weapon_tip');
   rig.applyPose('cast_release',{weapon,casting:{source,hands:2,stance:'ward'}});rig.blendFrom(snap,0);rig.update(0,0,0);
   check(Math.hypot(rig.getSocket('main_hand').x-hand.x,rig.getSocket('main_hand').y-hand.y)<.02,'cast blend starts at old hand');
   check(Math.hypot(rig.getSocket('weapon_tip').x-tip.x,rig.getSocket('weapon_tip').y-tip.y)<.02,'stow blend starts at old tip');
  }
  check(dollModel({...actor,equipment:[{presentation:{silhouette:'wand'}}]}).weapon==='wand','public wand remains a wand');
  const rig=new SkeletalRig();rig.applyPose('cast_release',{weapon:'sword',casting:{stance:'aim',hands:1}});rig.update(0,100,200);
  check(rig.getSocket('focus').x===rig.getSocket('off_hand').x,'armed one-hand cast uses free hand');
  const signatures=[];document.head.innerHTML='<style>body{margin:24px;background:#101a29;color:#eee4cd;font:16px system-ui}main{display:grid;grid-template-columns:1fr 1fr;gap:16px}article{background:#1d2d42;border:1px solid #455975;border-radius:12px;padding:12px}canvas{width:100%}h1{font:26px Georgia}p{color:#b6c6d8}</style>';
  document.body.innerHTML='<h1>Magic articulation  |  casting and target response</h1><p>Presentation fixtures  |  channel  ->  release  ->  resolved effect</p><main></main>';
  const examples=[['fire','staff','implement',2],['cold','staff','implement',1],['lightning','wand','implement',1],['force','staff','hands',2],['heal','staff','hands',1],['force','none','hands',2]];
  for(const [i,[element,weapon,castSource,hands]] of examples.entries()) {
   const casting=castingProfile({type:'cast',presentation:{casting:{source:castSource,hands}},ruling:{damage_type:element,radius:element==='fire'?20:0,operation:element==='heal'?'heal':'damage'}});
   const model=dollModel({...actor,equipment:weapon==='none'?[]:[{presentation:{silhouette:weapon}}],appearance:{...actor.appearance,weapon_style:{id:styles[i%styles.length]}}});
   const c=document.createElement('canvas');c.width=560;c.height=260;const ctx=c.getContext('2d');
   const source=new SkeletalRig({scale:1.3});source.applyPose('cast_release',{weapon:model.weapon,staffStyle:styles[i%styles.length],casting,progress:.4});source.update(0,100,235);drawPuppet(ctx,source,model);
   const target=new SkeletalRig({scale:1.3}),targetModel=dollModel({...actor,name:'Target'});target.applyPose(element==='heal'?'idle':'hit',{weapon:'none'});target.update(0,455,235,-1);drawPuppet(ctx,target,targetModel);
   const from=source.getSocket('focus'),to=target.getSocket('chest'),fx=new FXEngine();
   const shot=fx.spawnProjectile({fromX:from.x,fromY:from.y,toX:to.x,toY:to.y,damageType:element,archetype:casting.delivery,impactOnHit:false,durationMs:420});
   for(let k=0;k<12;k++)shot.update(16,()=>{});
   fx.spawnSpellReaction('e0',element);fx.spellReactions[0].elapsed=350;fx.draw(ctx,()=>to);
   signatures.push(c.toDataURL());const card=document.createElement('article');card.textContent=`${element}  |  ${casting.stance}  |  ${casting.hands} hand${casting.hands===2?'s':''}  |  ${weapon}  |  ${castSource}`;card.append(c);document.querySelector('main').append(card);
   fx.update(900,()=>to);check(fx.spellReactions.length===0,'target effect expires');
  }
  check(new Set(signatures).size===examples.length,'elemental reactions differ');
 });
 await page.screenshot({path:path.join(out,'magic-gallery.png'),fullPage:true});
 await page.addStyleTag({url:'/styles.css'}); await page.addScriptTag({url:'/ui-components.js'});
 const results=await page.evaluate(async()=>{
  const {characterFigure,actor}=magic,{syncPuppets,figureSocket,destroyPuppets}=await import('/puppet-dom.js');
  const {createCombatDirector}=await import('/combat-director.js');const check=(v,m)=>{if(!v)throw Error(m);};
  document.body.innerHTML='<div id="stage" style="position:relative;width:1000px;height:500px"></div>';const stage=document.querySelector('#stage');
  for(const [i,id]of ['p0','e0','e1'].entries())stage.insertAdjacentHTML('beforeend',characterFigure({...actor,id},'', 'combat',{attrs:{'data-stage-actor':id},style:`left:${40+i*300}px;bottom:30px;width:150px;height:240px`}));
  syncPuppets(stage);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
  const director=createCombatDirector({getStage:()=>stage,settings:()=>({speed:3,gapMs:0,fillMissing:false})});
  const shots=[],castSources=[],reactions=[],fx=director.fx,spawn=fx.spawnProjectile.bind(fx),react=fx.spawnSpellReaction.bind(fx);
  fx.spawnProjectile=opts=>{const caster=stage.querySelector('[data-stage-actor="p0"]'),focus=figureSocket(caster,'focus',stage);check(Math.hypot(opts.fromX-focus.x,opts.fromY-focus.y)<3,'projectile leaves focus');shots.push(opts);castSources.push(JSON.parse(stage.querySelector('[data-casting]').dataset.casting).source);return spawn(opts);};
  fx.spawnSpellReaction=(id,element)=>{reactions.push({id,element});return react(id,element);};
  const view={run_id:'magic',party:[],opposition:[],recent_receipts:[]};director.ingest(null,view);
  const receipt={type:'cast',actor:'p0',damage:15,target:'e0',presentation:{actor_id:'p0',target_id:'e0',casting:{stance:'overhead',hands:2,source:'hands',element:'fire'}},events:[
   {target:'e0',save:{success:false},result:{damage:10,damage_type:'FIRE'}},
   {target:'e1',save:{success:true},result:{damage:5,damage_type:'FIRE'}}]};
  check(director.ingest(view,{...view,recent_receipts:[receipt]})===2,'two resolved targets, no aggregate duplicate');director.kick();
  const drain=async()=>{const end=performance.now()+5000;while(director.playing||director.pending){if(performance.now()>end)throw Error('director timeout');await new Promise(r=>setTimeout(r,25));}};
  await drain();check(shots.length===2&&reactions.length===2,'travel and reactions for both targets');check(director.history[1].damage===5&&director.history[1].outcome==='hit','successful save retains half damage');
  director.ingest(view,{...view,recent_receipts:[receipt,{type:'cast',actor:'p0',events:[{target:'e0',attack:{success:false,natural:1}}]}]});director.kick();await drain();
  check(reactions.length===2,'miss never gets target reaction');
  director.ingest(view,{...view,recent_receipts:[{type:'cast',actor:'p0',presentation:{casting:{stance:'mend',hands:1,element:'heal'}},events:[{target:'p0',healing:7}]}]});director.kick();await drain();
  check(reactions.at(-1).id==='p0'&&reactions.at(-1).element==='heal','self healing affects caster');check(!stage.querySelector('[data-casting]'),'casting metadata cleaned');
  const staffReceipt={type:'staff_cast',actor:'p0',events:[{target:'e0',result:{damage:2,damage_type:'cold'}}]};
  director.ingest(view,{...view,recent_receipts:[staffReceipt]});director.kick();await drain();
  check(castSources.at(-1)==='implement','per-target staff cast keeps implement source');
  const history=director.history;director.destroy();destroyPuppets();
  for(const identity of ['doran','wren']) {
    stage.innerHTML=characterFigure({identity,name:identity,id:'p0'},'', 'combat',{attrs:{'data-stage-actor':'p0'},style:'left:100px;bottom:30px;width:220px;height:280px'});
    const n=stage.querySelector('[data-puppet-model]');n.dataset.casting=JSON.stringify({stance:'overhead',hands:2});n.dataset.beat='cast_channel';
    syncPuppets(stage,{reducedMotion:()=>true});await new Promise(requestAnimationFrame);
    const focus=figureSocket(n,'focus',stage);check(Number.isFinite(focus.x)&&Number.isFinite(focus.y),'champion casting socket');
    n.dataset.beat='cast_release';await new Promise(requestAnimationFrame);
    const release=figureSocket(n,'focus',stage);check(Math.hypot(focus.x-release.x,focus.y-release.y)>1,'champion casting articulation');
    delete n.dataset.casting;delete n.dataset.beat;
  }
  const quiet=createCombatDirector({getStage:()=>stage,reducedMotion:()=>true});
  quiet.play([{actor:'p0',target:'p0',style:'cast',healing:4,casting:{stance:'mend',hands:1,element:'heal'},animation:{}}]);
  while(quiet.playing||quiet.pending)await new Promise(r=>setTimeout(r,20));
  check(quiet.fx.projectiles.length===0&&quiet.fx.spellReactions.length===0,'reduced motion suppresses spell motion');
  quiet.destroy();destroyPuppets();return {shots:shots.length,reactions:reactions.length,history};
 });
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));console.log('PASS lowered staff, forward elbows, hand-only casting, wand geometry, support IK, focus emission, elements, multi-target saves, miss, self heal, cleanup.',out);
}finally{await browser?.close();await new Promise(r=>server?server.close(r):r());}})().catch(e=>{console.error(e);process.exitCode=1;});
