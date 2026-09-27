import {focusSockets} from './magic-articulation.js';
// Shared illustrated puppet compositor: creation, DOM figures and arcade.
// Only consumes the public doll model. It never infers mechanics from art.
//
// CLEAN CEL style (2026-09-23): one ink weight, flat two-tone fills (base +
// one shadow on the back side), no gradients or texture noise. Far limbs sit a
// step darker so the silhouette reads at combat scale. Details are shapes, not
// lines: if a feature cannot be read at 80 px tall it is not drawn.
import {SkeletalRig,GESTURES,SOCKET_NAMES,UPPER_BODY_POSES} from './skeletal-rig.js';
export {SkeletalRig,GESTURES,SOCKET_NAMES,UPPER_BODY_POSES};
const INK='#171b24', GOLD='#d9b56e', LW=1.1;
const color=(a,k,f)=>/^#[0-9a-f]{6}$/i.test(a[k]?.hex||'')?a[k].hex:f;
const id=(a,k,f)=>a[k]?.id||f;
// Hard cel steps: shadow toward ink, light toward white. Exported for other rigs.
export function celShade(hex,k=.3){return mix(hex,'#141826',k);}
export function celLight(hex,k=.25){return mix(hex,'#ffffff',k);}
function mix(a,b,k){const p=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)),x=p(a),y=p(b);
  return '#'+x.map((v,i)=>Math.round(v+(y[i]-v)*k).toString(16).padStart(2,'0')).join('');}
export function puppetStyle(model) {
  const a=model.appearanceData||{}, race=model.race||'human';
  const body=id(a,'body_type','average');
  const width={slight:.83,lean:.92,average:1,sturdy:1.12,broad:1.23}[body]||1;
  const gender=model.gender==='female'?.92:model.gender==='male'?1.06:1;
  return {a,race,width:width*gender,height:race==='goblin'?.8:race==='orc'?1.04:1,
    skin:color(a,'skin_tone',race==='orc'?'#8d9a76':race==='goblin'?'#94a36d':'#d6b394'),
    hair:color(a,'hair_color','#3b2a1d'),eye:color(a,'eye_color','#777096'),
    cloth:color(a,'cloth_color',color(a,'outfit','#3f4a63')),
    accent:color(a,'accent_color','#d9b56e'),
    hairStyle:id(a,'hair_style','short'),
    face:id(a,'face_shape','balanced'),ears:id(a,'ear_shape',/elf/.test(race)?'pointed':'standard'),
    marks:id(a,'facial_marks','none'),outfit:id(a,'outfit','travel'),
    cloak:id(a,'cloak_style','none'),headgear:model.itemTokens.includes('full-helm')?'full-helm':model.itemTokens.includes('headgear')?'half-helm':id(a,'headgear_style','none'),
    offhand:model.itemTokens.includes('offhand-shield')?'kite-shield':id(a,'offhand_style','none'),
    trinket:id(a,'trinket_style',model.itemTokens.includes('trinket')?'pendant':'none'),
    weaponStyle:id(a,'weapon_style','plain'),armor:model.gearTheme||'travel'};
}
function shape(ctx,points,fill,stroke=INK) {
  ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();
  if(fill){ctx.fillStyle=fill;ctx.fill();}
  if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=LW;ctx.lineJoin='round';ctx.stroke();}
}
function oval(ctx,x,y,rx,ry,fill,stroke=INK) {
  ctx.beginPath();ctx.ellipse(x,y,Math.max(.1,rx),Math.max(.1,ry),0,0,Math.PI*2);
  if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=LW;ctx.stroke();}
}
function bar(ctx,x,y,xx,yy,c,w=1) {
  ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(xx,yy);ctx.strokeStyle=c;ctx.lineWidth=w;ctx.lineCap='round';ctx.stroke();
}
function trace(ctx,pts){ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();}
// Paint the back (shadow) side of a closed outline as one flat cel.
function backShadow(ctx,pts,fill,x=2) {
  ctx.save();trace(ctx,pts);ctx.clip();ctx.fillStyle=celShade(fill,.32);ctx.fillRect(-60,-80,60+x,200);ctx.restore();
}
function atBone(ctx,rig,name,fn) {
  const b=rig.bones.get(name);ctx.save();ctx.translate(b.worldX,b.worldY);
  ctx.scale(rig.facing*rig.scale,rig.scale);ctx.rotate(b.angle);fn(b);ctx.restore();
}
// A limb chain is outlined as one piece, then filled, so joints never seam.
function chain(ctx,rig,parts) {
  for(const pass of ['ink','fill','shade'])for(const [name,fill,w] of parts)atBone(ctx,rig,name,b=>{
    const L=b.length;if(!L)return;
    if(pass==='ink')bar(ctx,0,0,0,L,INK,w+LW*2);
    else if(pass==='fill')bar(ctx,0,0,0,L,fill,w);
    else bar(ctx,-w*.28,1,-w*.28,L-1,celShade(fill,.3),w*.36);
  });
}
function metalOf(style){return style==='weathered'?'#8e938f':style==='ceremonial'?'#eadbb0':'#dfe5ea';}
function weapon(ctx,type,style) {
  const metal=metalOf(style),dark=celShade(metal,.35),wide=style==='heavy'?1.4:1,grip='#4a3a30';
  ctx.save();ctx.scale(wide,1);
  // Blades: flat face + one shaded half along the spine. Nothing else.
  const blade=(pts,half)=>{shape(ctx,pts,metal);shape(ctx,half,dark,null);shape(ctx,pts,null);};
  if(type==='staff'||type==='wand'||type==='polearm') {
    const stretch=type==='polearm'?1:focusSockets(type,style).length/54;ctx.scale(type==='wand'?.7:1,stretch);
    bar(ctx,0,16,0,-44,INK,4+LW*2);bar(ctx,0,16,0,-44,'#6b4d36',4);
    if(type==='staff'||type==='wand'){shape(ctx,[[0,-54],[5,-46],[0,-38],[-5,-46]],'#8fd0cb');shape(ctx,[[0,-54],[0,-38],[-5,-46]],'#5c9d98',null);}
    else blade([[-2.5,-43],[-2.5,-60],[6,-51],[3,-40]],[[-2.5,-43],[-2.5,-60],[.5,-50]]);
  } else if(type==='bow') {
    ctx.lineCap='round';ctx.beginPath();ctx.moveTo(0,-32);ctx.bezierCurveTo(19,-20,19,18,0,29);
    ctx.strokeStyle=INK;ctx.lineWidth=4+LW*2;ctx.stroke();ctx.strokeStyle='#8c6a44';ctx.lineWidth=4;ctx.stroke();
    bar(ctx,0,-32,0,29,'#efe8d4',.8);bar(ctx,-8,0,25,0,'#cdb285',1.2);shape(ctx,[[25,-2.5],[31,0],[25,2.5]],metal);
  } else if(type==='mace') {
    bar(ctx,0,9,0,-22,INK,3.4+LW*2);bar(ctx,0,9,0,-22,grip,3.4);
    shape(ctx,[[-6,-22],[-7,-30],[0,-35],[7,-30],[6,-22],[0,-19]],metal);shape(ctx,[[-6,-22],[-7,-30],[0,-35],[0,-19]],dark,null);
  } else if(type==='axe') {
    bar(ctx,0,10,0,-33,INK,3.2+LW*2);bar(ctx,0,10,0,-33,grip,3.2);
    blade([[1,-32],[13,-39],[16,-24],[8,-21],[1,-25]],[[1,-32],[13,-39],[9,-28],[1,-27]]);
  } else if(type==='sword'||type==='dagger') {
    const n=type==='dagger'?18:32;
    blade([[-2.6,-5],[-2.6,-n+4],[0,-n-3],[2.6,-n+4],[2.6,-5]],[[0,-5],[0,-n-3],[2.6,-n+4],[2.6,-5]]);
    bar(ctx,-6.5,-5,6.5,-5,INK,2.6+LW*2);bar(ctx,-6.5,-5,6.5,-5,GOLD,2.6);
    bar(ctx,0,-3,0,6,INK,3+LW*2);bar(ctx,0,-3,0,6,grip,3);oval(ctx,0,7.5,2.2,2.2,GOLD);
  }
  if(style==='runed')for(let y=-12;y>-28;y-=7)shape(ctx,[[0,y-2],[1.8,y],[0,y+2],[-1.8,y]],'#7fe0d6',null);
  if(style==='weathered')for(let y=-12;y>-26;y-=8)bar(ctx,-2,y,1.5,y-2.5,'#5a6468',1);
  if(style==='ceremonial')oval(ctx,0,-5,1.6,1.6,'#c0504d',null);
  ctx.restore();
}
function head(ctx,s,cloak) {
  const fw={balanced:1,angular:.95,round:1.12,narrow:.84,soft:1.05}[s.face]||1;
  const hair=s.hairStyle, full=s.headgear==='full-helm', hood=s.headgear==='hood'||cloak==='hooded-cloak';
  const brow=hair==='shaved'?celShade(s.skin,.5):s.hair;
  if(['long','braided'].includes(hair)&&!full&&!hood){
    shape(ctx,[[-11,-6],[3,-6],[1,hair==='long'?22:10],[-12,hair==='long'?24:12]],celShade(s.hair,.2));
    if(hair==='braided')for(let y=10;y<27;y+=4.5)oval(ctx,-9,y,2.8,2.6,s.hair);
  }
  // Ears: one flat shape per style so species reads by silhouette alone.
  const ear=s.ears==='standard'?(s.race==='goblin'?11:s.race==='elf'?9:s.race==='half-elf'?5.5:s.race==='orc'?4:2.5):s.ears==='swept'?13:8;
  if(!full&&!hood)shape(ctx,[[-6,-1],[-7-ear,s.ears==='swept'?-9:-5],[s.ears==='notched'?-8-ear*.6:-8,s.ears==='notched'?-1:3],[-5,5]],celShade(s.skin,.18));
  // Head: base + back-side cel. Faces turn toward the facing direction.
  const ry=s.face==='round'?10.5:s.face==='narrow'?12:s.face==='soft'?10.8:11;
  const pts=s.face==='angular'?[[-9,-8],[-5,-12],[6,-12],[10,-6],[9,5],[3,10],[-5,9],[-9,3]]
    :Array.from({length:24},(_,i)=>{const t=i/24*Math.PI*2;return [.5+Math.cos(t)*9.5*fw,-1+Math.sin(t)*ry];});
  shape(ctx,pts,s.skin,null);backShadow(ctx,pts,s.skin,-4);shape(ctx,pts,null);
  if(!full){
    // Eyes: ink ovals with an iris-coloured core; brows in hair colour.
    oval(ctx,2.4,-1.2,1.25,1.9,INK,null);oval(ctx,7,-1.2,1.1,1.8,INK,null);
    oval(ctx,2.6,-1,.7,1.1,s.eye,null);oval(ctx,7.2,-1,.6,1,s.eye,null);
    bar(ctx,.2,-5.2,3.8,-5.6,brow,1.5);bar(ctx,5.5,-5.6,8.8,-5,brow,1.5);
    bar(ctx,3,5.5,6.5,5.2,celShade(s.skin,.45),1);
    if(s.race==='orc'){shape(ctx,[[2,7],[2.6,3],[4,6.6]],'#efe4c2');shape(ctx,[[6,6.6],[7.4,3],[8,6.6]],'#efe4c2');}
    if(s.race==='goblin')shape(ctx,[[7,0],[12,3],[7,4]],s.skin);
    if(s.marks==='freckles')for(const [x,y] of [[1,2],[3,3],[6,2.5],[8,3.2]])oval(ctx,x,y,.55,.55,'#8a5a40',null);
    if(s.marks==='cheek-scar')bar(ctx,6,0,8.5,5,'#a0473f',1.1);
    if(s.marks==='war-paint')bar(ctx,-1,1.5,9,1.5,'#4f6d93',2.2);
    if(s.marks==='temple-mark')shape(ctx,[[-3,-6],[-1.5,-4],[-3,-2],[-4.5,-4]],'#7a62a0',null);
  }
  // Hair cap: one clean shape, style adds a single silhouette feature.
  if(hair!=='shaved'&&!full&&!hood){
    shape(ctx,[[-10,2],[-11,-8],[-6,-13.5],[3,-14],[10,-9],[10.5,-5],[5,-8.5],[-1,-8],[-6,-6],[-8,2]],s.hair);
    shape(ctx,[[-10,2],[-11,-8],[-6,-13.5],[-3,-13.7],[-6,-6],[-8,2]],celShade(s.hair,.3),null);
    if(hair==='cropped')shape(ctx,[[-9,-9],[-4,-13.5],[6,-13],[9,-9]],celLight(s.hair,.15));
    if(hair==='tousled')shape(ctx,[[-11,-8],[-14,-13],[-7,-13],[-5,-18],[1,-14],[8,-17],[7,-12],[12,-11],[10,-8]],s.hair);
    if(hair==='topknot'){oval(ctx,-2,-17,5,4.2,s.hair);bar(ctx,-5.5,-14.2,1.5,-14.2,GOLD,1.6);}
    if(hair==='long')shape(ctx,[[10,-9],[12,-2],[9,0]],s.hair);
  }
  if(hood){shape(ctx,[[-13,11],[-14,-9],[-6,-17],[6,-17],[13,-9],[12,-1],[9,-8],[0,-12],[-7,-8],[-9,10]],s.cloth);
    shape(ctx,[[-13,11],[-14,-9],[-6,-17],[-2,-16],[-7,-8],[-9,10]],celShade(s.cloth,.3),null);}
  if(s.headgear==='circlet'){bar(ctx,-9.5,-8,10,-8.5,INK,2.2+LW*2);bar(ctx,-9.5,-8,10,-8.5,GOLD,2.2);oval(ctx,4,-8.4,1.5,1.5,'#7fd0c6');}
  if(s.headgear==='half-helm'||full){
    const steel='#b9c4cb';shape(ctx,[[-11,1],[-11,-10],[-4,-15],[5,-15],[11,-9],[11,-2],[4,-5],[-4,-5]],steel);
    shape(ctx,[[-11,1],[-11,-10],[-4,-15],[-2,-15],[-4,-5]],celShade(steel,.3),null);bar(ctx,0,-14.5,0,-5.5,GOLD,1.2);
  }
  if(full){const steel='#aab6be';shape(ctx,[[-10,-5],[11,-5],[10,6],[3,10],[-7,8]],steel);bar(ctx,1,-1,10,-1,INK,1.8);
    shape(ctx,[[-10,-5],[-3,-5],[-2,9.6],[-7,8]],celShade(steel,.3),null);}
}
// Palm, finger block and thumb, each on its own joint, so a grip closes over
// the weapon and an open hand reads open. Shapes only (CLEAN CEL).
function fist(ctx,rig,side,fill) {
  atBone(ctx,rig,side+'_hand',()=>oval(ctx,0,.5,3.3,3.6,fill));
  if(!rig.bones.get(side+'_fingers'))return;
  atBone(ctx,rig,side+'_fingers',b=>shape(ctx,[[-2.6,-.4],[2.6,-.4],[2.2,b.length+.6],[-2.2,b.length+.6]],celShade(fill,.12)));
  atBone(ctx,rig,side+'_thumb',b=>shape(ctx,[[-1.1,0],[1.1,0],[.8,b.length+.4],[-.8,b.length+.4]],fill));
}
export function drawPuppet(ctx,rig,model,{shadow=true}={}) {
  const s=puppetStyle(model),w=s.width,GOLD=s.accent;
  const sleeve=s.armor==='plate'?'#b3c0c8':s.armor==='chain'?'#7d8d96':s.armor==='leather'?'#7a5641':s.cloth;
  const pants=celShade(s.cloth,.45),boot='#4a372c',glove=s.armor==='plate'?'#8e9aa3':s.skin;
  const root=rig.getSocket('ground');
  const onRoot=fn=>{ctx.save();ctx.translate(root.x,root.y);ctx.scale(rig.scale,rig.scale);fn();ctx.restore();};
  if(shadow)onRoot(()=>oval(ctx,0,1,22*w,3.6,'#00000045',null));
  if(model.effects.length)onRoot(()=>oval(ctx,0,0,27*w,6,null,model.effects.includes('ember')?'#ef9f5f':'#8fd0d8'));
  const cloak=s.cloak!=='none'?s.cloak:model.itemTokens.includes('cloak')?'travel-cape':'none';
  if(cloak!=='none'){
    const fill=celShade(s.cloth,.22), long=cloak==='long-mantle'||cloak==='hooded-cloak';
    const links=cloak==='shoulder-mantle'?[['cape_1',fill,20*w]]
      :[['cape_1',fill,20*w],['cape_2',celShade(fill,.14),23*w],...(long?[['cape_3',celShade(fill,.14),25*w]]:[])];
    chain(ctx,rig,links);
    atBone(ctx,rig,'torso',()=>bar(ctx,-11*w,-4,11*w,-4,GOLD,1.2));
  }
  // Loose hair trails on its own three-joint chain, behind the head.
  if(['long','braided','topknot'].includes(s.hairStyle)&&s.headgear!=='full-helm'&&s.headgear!=='hood'&&cloak!=='hooded-cloak'){
    const tail=s.hairStyle==='long'?[['hair_1',s.hair,8],['hair_2',celShade(s.hair,.15),7],['hair_3',celShade(s.hair,.15),5.5]]
      :[['hair_1',s.hair,4.5],['hair_2',s.hair,4],['hair_3',celShade(s.hair,.15),3.5]];
    chain(ctx,rig,tail);
  }
  // Far side (drawn first) is one cel step darker than the near side.
  const far=c=>celShade(c,.28), foot=[[-4,-4],[3,-4],[8,.5],[8,2.5],[-4.5,2.5]];
  chain(ctx,rig,[['left_thigh',far(pants),8.5*w],['left_shin',far(boot),7*w]]);
  atBone(ctx,rig,'left_foot',()=>shape(ctx,foot,far(boot)));
  chain(ctx,rig,[['left_upper_arm',far(sleeve),7*w],['left_lower_arm',far(sleeve),6*w]]);
  fist(ctx,rig,'left',far(glove));
  chain(ctx,rig,[['right_thigh',pants,8.5*w],['right_shin',boot,7*w]]);
  atBone(ctx,rig,'right_foot',()=>shape(ctx,foot,boot));
  // Torso: shoulders, waist, hem. Outfit and armor change the silhouette and
  // the fill; decoration is at most one accent.
  atBone(ctx,rig,'torso',()=>{
    const robe=s.outfit==='robe'||s.armor==='robe', coat=s.outfit==='coat'||s.outfit==='uniform';
    const hem=robe?54:coat?40:s.outfit==='travel'?32:28, flare=robe?19:coat?16:14;
    const body=s.armor==='plate'?'#c3ced4':s.armor==='chain'?'#8d9ca4':s.armor==='leather'?'#855f47':s.cloth;
    const pts=[[-12*w,-5],[12*w,-5],[10*w,20],[flare*w,hem],[-flare*w,hem],[-10*w,20]];
    shape(ctx,pts,body,null);backShadow(ctx,pts,body,-3);shape(ctx,pts,null);
    if(s.outfit==='vest')shape(ctx,[[-4,-5],[5,-5],[4,20],[-3,20]],celLight(s.cloth,.2));
    if(s.outfit==='uniform')for(let y=2;y<19;y+=5.5)oval(ctx,3,y,1.1,1.1,GOLD,null);
    if(s.outfit==='coat')bar(ctx,2,20,2,hem-1,INK,LW);
    if(s.outfit==='tunic')shape(ctx,[[-2,-5],[6,-5],[2,3]],celShade(body,.3),null);
    if(s.armor==='plate')shape(ctx,[[-9,-3],[10,-3],[8,15],[1,19],[-7,15]],celLight(body,.3));
    if(s.armor==='chain')for(let y=3;y<19;y+=5)bar(ctx,-8,y,9,y,celShade(body,.3),1);
    if(s.armor==='leather')bar(ctx,-9,-3,9,19,'#c49e72',2.4);
    shape(ctx,[[-11*w,19],[11*w,19],[11*w,23.5],[-11*w,23.5]],'#3b2e2a');shape(ctx,[[0,19],[4.5,19],[4.5,23.5],[0,23.5]],GOLD);
    bar(ctx,-flare*w+1,hem-1.2,flare*w-1,hem-1.2,GOLD,1.3);
    if(s.trinket==='satchel'){bar(ctx,-10,-3,11,24,'#a3804f',2);shape(ctx,[[-15,22],[-6,22],[-6,32],[-15,31]],'#8a6045');}
    else if(s.trinket!=='none'){bar(ctx,-3,-5,2,8,GOLD,.8);bar(ctx,7,-5,2,8,GOLD,.8);
      if(s.trinket==='medal')oval(ctx,2,10,2.8,2.8,GOLD);
      else shape(ctx,[[2,6],[s.trinket==='talisman'?5.5:4,10],[2,14.5],[-1.5,10]],s.trinket==='talisman'?'#79c0ad':GOLD);}
  });
  atBone(ctx,rig,'head',()=>head(ctx,s,cloak));
  // Off-hand props hang from the far fist, behind the near arm.
  atBone(ctx,rig,rig.casting&&(rig.casting.hands===2||rig.weapon!=='none')?'pelvis':'left_hand',()=>{
    if(s.offhand==='buckler'){oval(ctx,0,0,9.5,10.5,'#7b8e9b');oval(ctx,0,0,3,3,GOLD);}
    else if(s.offhand==='kite-shield'){const pts=[[-11,-13],[10,-13],[12,-2],[0,19],[-12,-2]];shape(ctx,pts,'#5f7688');
      shape(ctx,[[-11,-13],[0,-13],[0,19],[-12,-2]],celShade('#5f7688',.3),null);shape(ctx,pts,null,GOLD);oval(ctx,0,-1,2.6,2.6,GOLD);}
    else if(s.offhand==='tome'){shape(ctx,[[-8,-10],[8,-10],[8,11],[-8,11]],'#6f4f62');bar(ctx,-5,-8,-5,9,GOLD,1.4);}
    else if(s.offhand==='lantern'){bar(ctx,0,0,0,5,INK,1);shape(ctx,[[-5,5],[5,5],[6,16],[-6,16]],'#f0c565');shape(ctx,[[-5,5],[0,5],[0,16],[-6,16]],'#c9973d',null);}
  });
  // Near arm last, weapon in the fist, fist over the grip.
  chain(ctx,rig,[['right_upper_arm',sleeve,7*w],['right_lower_arm',sleeve,6*w]]);
  atBone(ctx,rig,'right_weapon',()=>{
    ctx.save();ctx.rotate(model.weapon==='bow'?Math.PI/2:Math.PI);weapon(ctx,model.weapon,s.weaponStyle);ctx.restore();
  });
  // Supporting fingers sit over the shaft, not underneath the torso or weapon.
  if(rig.twoHanded()||rig.casting)fist(ctx,rig,'left',far(glove));
  fist(ctx,rig,'right',glove);
}
// Every beat the combat director can set, and the pose it drives. A beat not
// listed here falls through to the model's own pose.
export const BEAT_POSES=Object.freeze({impact:'hit',hit:'hit',crit:'crit',miss:'dodge',dodge:'dodge',
  windup:'windup',strike:'strike',attack:'attack',cast:'cast',cast_channel:'cast_channel',cast_release:'cast_release',
  guard:'guard',move:'run',death:'death'});
export function poseFor(model,entity={},beat='') {
  if(model.alive===false||entity.active===false)return 'down';
  if(BEAT_POSES[beat])return BEAT_POSES[beat];
  if(beat.startsWith('gesture:')&&GESTURES.includes(beat.slice(8)))return beat.slice(8);
  if(entity.blocking)return 'guard';
  if(entity.attack_phase||entity.attack_ticks>0)return 'attack';
  const mode=String(entity.movement_mode||'').toLowerCase();
  if(['climb','vault','jump','fall','fly'].includes(mode))return mode;
  if(Number(entity.position?.[2])>0)return 'airborne';
  if(Math.hypot(...(entity.velocity||[0,0]).slice(0,2))>.05)return 'run';
  if(model.pose==='ko')return 'down';
  return model.pose==='combat'?'guard':model.pose==='travel'?'run':model.pose||'idle';
}

// Authored poses retain baked equipment; sockets transform with the same image.
export function drawChampion(ctx,rig,image,art,poseKey,{height=rig.scale*170,down=false,paint=true}={}) {
  const width=height*art.width/art.height,padding=art.footPadding||0,angle=down?-1.35:0;
  if(paint){ctx.save();ctx.translate(rig.rootX,rig.rootY);ctx.scale(rig.facing,1);ctx.rotate(angle);
  ctx.drawImage(image,-width/2,-height*(1-padding),width,height);ctx.restore();}
  return Object.fromEntries(Object.entries(art.sockets?.[poseKey]||art.sockets?.rest||{}).map(([name,p])=>{
    const x=(p[0]-.5)*width,y=(p[1]-(1-padding))*height;
    return [name,{x:rig.rootX+(x*Math.cos(angle)-y*Math.sin(angle))*rig.facing,y:rig.rootY+x*Math.sin(angle)+y*Math.cos(angle),rotation:angle*rig.facing}];
  }));
}
