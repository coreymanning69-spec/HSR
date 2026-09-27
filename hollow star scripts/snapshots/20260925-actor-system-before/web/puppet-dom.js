// One animation scheduler for every mounted DOM figure. No per-render loops.
import {SkeletalRig,drawPuppet,drawChampion,puppetStyle,poseFor,SOCKET_NAMES,UPPER_BODY_POSES} from './puppet-renderer.js';
import {championPoseArt,championRig} from './sprite-renderer.js';
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
      // A canvas re-bound to another figure starts clean: champion rigs reshape
      // the skeleton and keep blend state on it, which must not leak across.
      if(rec.model&&rec.model.identity!==model.identity)Object.assign(rec,{rig:new SkeletalRig(),pose:'',snap:null,deathAt:0,doranContact:null,downK:null,sockets:null});
      rec.model=model;rec.source=node.dataset.puppetModel;
    }
  });
  if(mounted.size&&!request){last=performance.now();request=requestAnimationFrame(tick);}
}
function tick(now) {
  request=0;const dt=Math.min(64,Math.max(0,now-last));last=now;
  for(const [canvas,r] of mounted){
    if(!canvas.isConnected){mounted.delete(canvas);continue;}
    paint(r,now,dt);
  }
  if(mounted.size)request=requestAnimationFrame(tick);
}
// measure: pose and read sockets without touching the canvas (socket queries).
function paint(r,now,dt,measure=false) {
  const {node,canvas,rig,model}=r;
  const w=node.clientWidth,h=node.clientHeight;if(!w||!h)return;
  // The director writes data-casting directly; parse it only when it changes.
  if(r.castingSource!==node.dataset.casting){r.castingSource=node.dataset.casting;r.casting=node.dataset.casting?JSON.parse(node.dataset.casting):null;}
  // A rigged champion's canvas overhangs the figure box (his blade does); all
  // drawing and sockets stay in the figure's own coordinates.
  const ox=canvas.offsetLeft||0,oy=canvas.offsetTop||0,cw=canvas.clientWidth||w,ch=canvas.clientHeight||h;
  const dpr=Math.min(2,devicePixelRatio||1);
  if(!measure&&(canvas.width!==Math.round(cw*dpr)||canvas.height!==Math.round(ch*dpr))){canvas.width=Math.round(cw*dpr);canvas.height=Math.round(ch*dpr);}
  const ctx=canvas.getContext('2d');
  if(!measure){ctx.setTransform(dpr,0,0,dpr,-ox*dpr,-oy*dpr);ctx.clearRect(ox,oy,cw,ch);}
  const preview=node.closest('[data-puppet-preview]');
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
  if(clip&&!preview){
    if(clip.contact!=null&&!r.contacted&&(progress>=clip.contact||reduced)){r.contacted=true;emit(node,'rig:contact',pose);}
    if(!clip.loop&&!r.done&&progress>=1){r.done=true;emit(node,'rig:done',pose);}
  }
  const facing=Number(preview?.dataset.previewFacing||1);
  const style=puppetStyle(model);
  const rigged=model.base?.type==='rig'&&championRig(model.identity);
  // A fallen figure lies wider and lower; ease the layout so the fall never pops.
  const downT=pose==='down'&&!rigged?1:0;
  r.downK=r.downK==null||reduced?downT:r.downK+(downT-r.downK)*(1-Math.exp(-dt/180));
  const dk=r.downK;
  rig.scale=Math.min(w/(rigged?100:model.base.type==='art'?115+35*dk:100+50*dk),h/123)*style.height;
  if(rigged){
    r.sockets=rigged.draw(ctx,rig,model,{x:w*.5,y:h*.94,facing,dt:reduced?0:dt,now,pose,beat:preview?'':beat,paint:!measure,
      attackAnimation:node.dataset.attackAnimation||'',casting:r.casting,reducedMotion:reduced,idleFidgets:!preview&&model.pose==='idle'});
    // The rig's own clock: Doran's hitstop hold, Wren's release, is the moment of contact.
    const hit=(rig.doran||rig.wren)?.contactAt;
    if(hit!=null&&hit!==r.doranContact){r.doranContact=hit;if(!preview)emit(node,'rig:contact',rig.pose);}
    node.dataset.renderedPose=rig.pose||pose;
    return;
  }
  // Upper-body actions keep the legs of a locomotion base pose.
  const base=poseFor(model,{},'');
  const lower=LOCOMOTION.includes(base)&&UPPER_BODY_POSES.includes(pose)?base:null;
  rig.applyPose(pose,{progress,lower,weapon:model.weapon,staffStyle:style.weaponStyle,casting:r.casting,bodyWidth:style.width,reducedMotion:reduced});
  if(r.snap)rig.blendFrom(r.snap,Math.min(1,age/BLEND_MS(pose)));
  if(r.snap&&age>=BLEND_MS(pose))r.snap=null;
  const side=facing<0?.35:.65;
  rig.update(reduced?0:dt,w*(.5+(side-.5)*dk),h*(.94-.09*dk),facing);
  const img=node.querySelector('.doll-base-art');
  const authored=!pose.startsWith('cast')&&img?.complete&&img.naturalWidth>0&&!node.classList.contains('champion-pose-fallback');
  if(!authored&&!measure)drawPuppet(ctx,rig,model);
  r.sockets=Object.fromEntries(SOCKET_NAMES.map(n=>[n,rig.getSocket(n)]));
  if(authored){
    const art=championPoseArt(model.identity),poseKey=node.dataset.championPose||model.base.poseKey;
    r.sockets=drawChampion(ctx,rig,img,art,poseKey,{down:pose==='down',paint:!measure});
  }
  node.dataset.renderedPose=pose;
}
export function figureSocket(node,socket='chest',container=node?.offsetParent) {
  const r=mounted.get(node?.querySelector('.puppet-canvas'));if(!r)return null;
  // Refresh immediately: the FX scheduler may run before the shared puppet tick.
  // dt 0 measures the current pose without advancing its animation.
  paint(r,performance.now(),0,true);
  // Same fallback as SkeletalRig.getSocket: an unanswered name lands on the chest.
  const key=socket==='body'?'chest':socket==='root'?'ground':socket;
  const p=r.sockets?.[key]||(key==='weapon_tip'||key==='focus'?r.sockets?.main_hand:null)||r.sockets?.chest;if(!p)return null;
  const nr=node.getBoundingClientRect(),cr=container.getBoundingClientRect();
  const mirrored=getComputedStyle(node).transform.startsWith('matrix(-');
  return {x:(nr.left-cr.left+(mirrored?node.clientWidth-p.x:p.x)*nr.width/node.clientWidth)*container.clientWidth/cr.width,
    y:(nr.top-cr.top+p.y*nr.height/node.clientHeight)*container.clientHeight/cr.height,rotation:p.rotation||0};
}
export function puppetDiagnostics(){return {mounted:mounted.size,scheduled:Boolean(request)};}
export function destroyPuppets(){cancelAnimationFrame(request);request=0;mounted.clear();}
