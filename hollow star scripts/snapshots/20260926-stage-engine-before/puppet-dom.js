// One animation scheduler for every mounted DOM figure. No per-render loops.
//
// Each frame runs in two phases so the browser lays out at most once: first
// every figure's box, canvas size and on-screen position are READ, then every
// canvas is PAINTED. Sockets are cached from the paint, so the FX engine and
// the combat director can ask where a hand or a staff tip is without forcing
// another layout or re-posing the figure.
import {SkeletalRig,drawPuppet,drawChampion,puppetStyle,poseFor,SOCKET_NAMES,UPPER_BODY_POSES} from './puppet-renderer.js';
import {championPoseArt,actorRig} from './sprite-renderer.js';
import {heroBurst} from './hero-rig.js';
import {actorStats} from './actor-core.js';
const mounted=new Map(); let request=0,last=0;
// One-shot clips: ms is the clip length (progress clamps at 1 and holds);
// contact is the fraction where the blow lands or the spell leaves the hand.
// The figure node receives rig:contact and rig:done events at those moments,
// so the combat director can sync impacts to the animation, not a timer.
export const CLIPS=Object.freeze({attack:{ms:850,contact:.42},strike:{ms:200,contact:.5},windup:{ms:140},
  cast:{ms:460,contact:.4},cast_channel:{ms:600,loop:true},cast_release:{ms:260,contact:.3},
  hit:{ms:300},crit:{ms:380},dodge:{ms:340},death:{ms:700},
  point:{ms:1400},cheer:{ms:1400},wave:{ms:1400},salute:{ms:1400},look:{ms:1800},crossed:{ms:1800}});
const BLEND_MS=pose=>pose==='hit'||pose==='crit'?60:pose==='down'?250:120;
const LOCOMOTION=['run','advance','retreat'];
function emit(node,type,pose){node.dispatchEvent(new CustomEvent(type,{detail:{pose}}));}
let reduce=()=>globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
export function syncPuppets(root=document,{reducedMotion}={}) {
  if(reducedMotion)reduce=reducedMotion;
  for(const [canvas] of mounted)if(!canvas.isConnected)mounted.delete(canvas);
  root.querySelectorAll('[data-puppet-model]').forEach(node=>{
    const canvas=node.querySelector('.puppet-canvas');if(!canvas)return;
    let rec=mounted.get(canvas);
    if(!rec){rec={node,canvas,rig:new SkeletalRig(),source:null,pose:'',poseAt:0,deathAt:0,contacted:false,done:false,snap:null,doranContact:null};mounted.set(canvas,rec);}
    if(rec.source!==node.dataset.puppetModel){
      const model=JSON.parse(node.dataset.puppetModel);
      // A canvas re-bound to another figure starts clean: rigs reshape the
      // skeleton and keep blend state on it, which must not leak across.
      if(rec.model&&rec.model.identity!==model.identity)Object.assign(rec,{rig:new SkeletalRig(),pose:'',snap:null,deathAt:0,doranContact:null,downK:null,sockets:null});
      rec.model=model;rec.source=node.dataset.puppetModel;rec.def=actorRig(model);
    }
  });
  if(mounted.size&&!request&&!document.hidden){last=performance.now();request=requestAnimationFrame(tick);}
}
if(typeof document!=='undefined'&&document.addEventListener){
  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden&&mounted.size&&!request){last=performance.now();request=requestAnimationFrame(tick);}
  });
}
// Read phase for one figure: box, canvas geometry, on-screen position.
function measure(r) {
  const {node,canvas}=r;
  r.w=node.clientWidth;r.h=node.clientHeight;
  r.ox=canvas.offsetLeft||0;r.oy=canvas.offsetTop||0;r.cw=canvas.clientWidth||r.w;r.ch=canvas.clientHeight||r.h;
  r.rect=node.getBoundingClientRect();
  // A CSS-mirrored figure (opponents face left this way) only changes with its classes.
  if(r.mirrorKey!==node.className){r.mirrorKey=node.className;r.mirrored=getComputedStyle(node).transform.startsWith('matrix(-');}
  r.preview=node.closest('[data-puppet-preview]');
}
function tick(now) {
  request=0;
  if(typeof document!=='undefined'&&document.hidden)return;
  const dt=Math.min(64,Math.max(0,now-last));last=now;
  const started=performance.now();
  for(const [canvas,r] of mounted){ if(!canvas.isConnected){mounted.delete(canvas);continue;} measure(r); }
  for(const [,r] of mounted)paint(r,now,dt);
  actorStats.frames++;actorStats.lastFrameMs=performance.now()-started;
  if(mounted.size&&!(typeof document!=='undefined'&&document.hidden))request=requestAnimationFrame(tick);
}
// measure: pose and read sockets without touching the canvas (socket queries).
function paint(r,now,dt,measureOnly=false) {
  const {node,canvas,rig,model}=r;
  if(r.w==null)measure(r);
  const w=r.w,h=r.h;if(!w||!h)return;
  // The director writes data-casting directly; parse it only when it changes.
  if(r.castingSource!==node.dataset.casting){r.castingSource=node.dataset.casting;r.casting=node.dataset.casting?JSON.parse(node.dataset.casting):null;}
  // A rigged figure's canvas overhangs the figure box (blades and spears do);
  // all drawing and sockets stay in the figure's own coordinates.
  const ox=r.ox,oy=r.oy,cw=r.cw,ch=r.ch;
  const dpr=Math.min(2,devicePixelRatio||1);
  if(!measureOnly&&(canvas.width!==Math.round(cw*dpr)||canvas.height!==Math.round(ch*dpr))){canvas.width=Math.round(cw*dpr);canvas.height=Math.round(ch*dpr);}
  const ctx=canvas.getContext('2d');
  if(!measureOnly){ctx.setTransform(dpr,0,0,dpr,-ox*dpr,-oy*dpr);ctx.clearRect(ox,oy,cw,ch);}
  const preview=r.preview;
  const beat=node.dataset.beat||'';
  let pose=preview?.dataset.previewPose||poseFor(model,{},beat);
  // Dying plays out: a figure that falls while on stage collapses first.
  if(pose==='down'&&r.pose&&!['down','death'].includes(r.pose)&&!preview)r.deathAt=now;
  if(pose!=='down')r.deathAt=0;
  if(r.deathAt&&now-r.deathAt<CLIPS.death.ms)pose='death';
  const reduced=Boolean(reduce());
  if(pose!==r.pose){
    if(r.pose&&!reduced)r.snap=rig.snapshot();else r.snap=null;
    r.pose=pose;r.poseAt=now;r.contacted=false;r.done=false;
  }
  const clip=CLIPS[pose],age=now-r.poseAt;
  const progress=reduced?(clip?1:.5):!clip?((age%850)/850):preview||clip.loop?(age%clip.ms)/clip.ms:Math.min(1,age/clip.ms);
  if(clip&&!preview&&!measureOnly){
    if(clip.contact!=null&&!r.contacted&&(progress>=clip.contact||reduced)){r.contacted=true;emit(node,'rig:contact',pose);}
    if(!clip.loop&&!r.done&&progress>=1){r.done=true;emit(node,'rig:done',pose);}
  }
  const facing=Number(preview?.dataset.previewFacing||1);
  const rigged=r.def;
  if(rigged){
    // Every figure stands on a vector rig: its proportions live in the rig,
    // so the box only sets the scale (the 5'8" baseline fills ~80% of it).
    rig.scale=Math.min(w/100,h/123);
    const started=measureOnly?0:performance.now();
    r.sockets=rigged.draw(ctx,rig,model,{x:w*.5,y:h*.94,facing,dt:reduced||measureOnly?0:dt,now,pose,beat:preview?'':beat,paint:!measureOnly,
      attackAnimation:node.dataset.attackAnimation||'',casting:r.casting,reducedMotion:reduced,idleFidgets:!preview&&model.pose==='idle',
      screenX:r.rect?r.rect.left+r.rect.width/2:null,screenY:r.rect?.bottom??null,screenFacing:r.mirrored?-facing:facing});
    if(started){actorStats.paintMs+=performance.now()-started;actorStats.paints++;}
    // The rig's own clock: Doran's hitstop hold, Wren's release, a hero's
    // blade crossing the target, is the moment of contact.
    const hit=(rig.doran||rig.wren)?.contactAt??rig.hero?.contactAt;
    if(!measureOnly&&hit!=null&&hit>=0&&hit!==r.doranContact){r.doranContact=hit;if(!preview)emit(node,'rig:contact',rig.pose);}
    const rendered=rig.pose||pose;
    if(!measureOnly&&node.dataset.renderedPose!==rendered)node.dataset.renderedPose=rendered;
    return;
  }
  // Legacy path: a model with no rig (none are built today) keeps the
  // generic puppet, with authored pose art laid over it when it has some.
  const style=puppetStyle(model);
  const downT=pose==='down'?1:0;
  r.downK=r.downK==null||reduced?downT:r.downK+(downT-r.downK)*(1-Math.exp(-dt/180));
  const dk=r.downK;
  rig.scale=Math.min(w/(model.base.type==='art'?115+35*dk:100+50*dk),h/123)*style.height;
  const base=poseFor(model,{},'');
  const lower=LOCOMOTION.includes(base)&&UPPER_BODY_POSES.includes(pose)?base:null;
  rig.applyPose(pose,{progress,lower,weapon:model.weapon,staffStyle:style.weaponStyle,casting:r.casting,bodyWidth:style.width,reducedMotion:reduced});
  if(r.snap)rig.blendFrom(r.snap,Math.min(1,age/BLEND_MS(pose)));
  if(r.snap&&age>=BLEND_MS(pose))r.snap=null;
  const side=facing<0?.35:.65;
  rig.update(reduced?0:dt,w*(.5+(side-.5)*dk),h*(.94-.09*dk),facing);
  const img=node.querySelector('.doll-base-art');
  const authored=!pose.startsWith('cast')&&img?.complete&&img.naturalWidth>0&&!node.classList.contains('champion-pose-fallback');
  if(!authored&&!measureOnly)drawPuppet(ctx,rig,model);
  r.sockets=Object.fromEntries(SOCKET_NAMES.map(n=>[n,rig.getSocket(n)]));
  if(authored){
    const art=championPoseArt(model.identity),poseKey=node.dataset.championPose||model.base.poseKey;
    r.sockets=drawChampion(ctx,rig,img,art,poseKey,{down:pose==='down',paint:!measureOnly});
  }
  if(!measureOnly&&node.dataset.renderedPose!==pose)node.dataset.renderedPose=pose;
}
const recordOf=node=>mounted.get(node?.querySelector?.('.puppet-canvas'));
// Where a figure's socket sits in `container` coordinates. Answered from the
// sockets the last paint cached and the box the last read phase measured; a
// figure not yet painted is posed once (dt 0) without advancing its clock.
export function figureSocket(node,socket='chest',container=node?.offsetParent) {
  const r=recordOf(node);if(!r)return null;
  actorStats.socketQueries++;
  if(!r.sockets){measure(r);paint(r,performance.now(),0,true);}
  // Same fallback as SkeletalRig.getSocket: an unanswered name lands on the chest.
  const key=socket==='body'?'chest':socket==='root'?'ground':socket;
  const p=r.sockets?.[key]||(key==='weapon_tip'||key==='focus'?r.sockets?.main_hand:null)||r.sockets?.chest;if(!p||!container)return null;
  const nr=r.rect||node.getBoundingClientRect(),cr=container.getBoundingClientRect();
  const nw=r.w||node.clientWidth,nh=r.h||node.clientHeight;
  return {x:(nr.left-cr.left+(r.mirrored?nw-p.x:p.x)*nr.width/nw)*container.clientWidth/cr.width,
    y:(nr.top-cr.top+p.y*nr.height/nh)*container.clientHeight/cr.height,rotation:p.rotation||0};
}
// A blow or a shove on a figure, in screen px/s: cloth, hair and the body's
// sway answer it on the next frames. Presentation only.
export function figureImpulse(node,ix,iy=0){const r=recordOf(node);r?.rig?.motion?.impulse(ix,iy);return Boolean(r);}
// Element particles thrown off a figure where an impact lands (hero rigs).
export function figureBurst(node,element,socket='chest'){
  const r=recordOf(node),p=r?.sockets?.[socket]||r?.sockets?.chest;if(!r||!p)return false;
  heroBurst(r.rig,element,p.x,p.y);return true;
}
export function puppetDiagnostics(){return {mounted:mounted.size,scheduled:Boolean(request),stats:{...actorStats}};}
export function destroyPuppets(){cancelAnimationFrame(request);request=0;mounted.clear();}
