/** Presentation-only skeleton. Local +Y points down; reflection happens once,
 * after forward kinematics. All dimensions and sockets share the same scale. */
import {staffSockets,focusSockets,isCastingImplement} from './magic-articulation.js';
export class Bone {
  constructor(name, parent = null, length = 0, angle = 0, offsetX = 0, offsetY = 0) {
    Object.assign(this, {name, parent, length, restAngle: angle, localAngle: angle,
      restX: offsetX, restY: offsetY, localX: offsetX, localY: offsetY});
  }
  compute(x, y, angle = 0, facing = 1, scale = 1) {
    this.angle = angle + this.localAngle;
    this.x = x + (this.localX * Math.cos(angle) - this.localY * Math.sin(angle)) * scale;
    this.y = y + (this.localX * Math.sin(angle) + this.localY * Math.cos(angle)) * scale;
    this.endX = this.x - Math.sin(this.angle) * this.length * scale;
    this.endY = this.y + Math.cos(this.angle) * this.length * scale;
  }
}
// Weapon reach from the grip to the business end, in rig units, plus the bone
// angle that lines it up with the art drawn by puppet-renderer weapon(): the
// art sits in the hand frame rotated by `r` and points up its local -y (the
// bow's point is its arrowhead, along local +x). weapon_tip rides this bone.
const TWO_HANDED=['staff','bow','polearm'];
const WEAPON_REACH={sword:35,dagger:21,staff:54,polearm:60,mace:35,axe:39,bow:31};
function weaponBone(weapon) {
  const L=weapon==='wand'?focusSockets(weapon).length:WEAPON_REACH[weapon];if(!L)return {length:0,angle:0};
  const r=TWO_HANDED.includes(weapon)||weapon==='wand'?-.15:1.15;
  return {length:L,angle:weapon==='bow'?r-Math.PI/2:Math.PI+r};
}
// Every socket name the rig answers; anything else warns once and falls back
// to the chest so an FX call never lands at the origin.
export const SOCKET_NAMES=Object.freeze(['head','chest','main_hand','off_hand','ground','weapon_main','weapon_tip',
  'weapon_off','focus','shield','cape','hair','jaw']);
// The contract every renderer answers -- this rig and each champion rig's
// draw(). FX and the combat director may ask for any of these on any figure.
export const CORE_SOCKETS=Object.freeze(['head','chest','main_hand','off_hand','ground','weapon_main','weapon_tip','focus','shield']);
const SOCKET_BONE={main_hand:'right_hand',off_hand:'left_hand',chest:'torso',body:'torso',ground:'root',root:'root',head:'head',
  weapon_main:'right_hand',weapon_tip:'right_weapon',weapon_off:'left_weapon',shield:'shield',cape:'cape_1',hair:'hair_1',jaw:'jaw'};
const warned=new Set();
// Lower-body bones: a locomotion pose keeps these while the upper body acts.
const LOWER_BODY=['root','pelvis','left_hip','right_hip','left_thigh','right_thigh','left_shin','right_shin',
  'left_foot','right_foot','left_toe','right_toe'];
// Upper-body actions that may layer over a moving lower body.
export const UPPER_BODY_POSES=Object.freeze(['attack','strike','windup','cast','cast_channel','cast_release',
  'point','cheer','crossed','look','wave','salute']);
export const GESTURES=Object.freeze(['point','cheer','crossed','look','wave','salute','kneel','victory']);
export class SkeletalRig {
  constructor({scale = 1, palette = null} = {}) {
    this.scale = scale; this.palette = palette; this.time = 0; this.facing = 1;
    this.bones = new Map(); this.pose = 'idle'; this.buildSkeleton();
  }
  buildSkeleton() {
    const b = (n,p,l=0,a=0,x=0,y=0) => this.bones.set(n,new Bone(n,p,l,a,x,y));
    b('root',null); b('pelvis','root',0,0,0,-43);
    b('spine','pelvis',0,0,0,-10); b('torso','spine',0,0,0,-13);
    b('neck','torso',0,0,0,-9); b('head','neck',0,0,0,-8);
    for (const [side,sign] of [['left',-1],['right',1]]) {
      b(side+'_shoulder','torso',0,0,sign*12,0);
      b(side+'_upper_arm',side+'_shoulder',16,sign*-0.12);
      b(side+'_lower_arm',side+'_upper_arm',14,sign*-0.06);
      b(side+'_hand',side+'_lower_arm');
      b(side+'_hip','pelvis',0,0,sign*6,0);
      b(side+'_thigh',side+'_hip',21,sign*0.035);
      b(side+'_shin',side+'_thigh',21,0);
      b(side+'_foot',side+'_shin');
    }
    // Detail joints (2026-09-23). All are leaves hung off the original 22, so
    // every existing pose, IK chain and reshape() spec resolves unchanged; a
    // renderer that ignores them draws exactly what it drew before.
    b('jaw','head',4,0,0,-2);
    b('hair_1','head',6,.35,-4,-14); b('hair_2','hair_1',6,.1); b('hair_3','hair_2',5,.1);
    b('cape_1','torso',12,.08,-5,-2); b('cape_2','cape_1',12,.04); b('cape_3','cape_2',11,.03);
    for (const side of ['left','right']) {
      b(side+'_thumb',side+'_hand',3,-.7);
      b(side+'_fingers',side+'_hand',4,.15);
      b(side+'_weapon',side+'_hand');
      b(side+'_toe',side+'_foot',5,-1.5);
    }
    b('shield','left_lower_arm',0,0,0,8);
  }
  setBoneAngle(n,a) { const b=this.bones.get(n); if(b)b.localAngle=a; }
  setBoneOffset(n,x,y) { const b=this.bones.get(n); if(b){b.localX=x;b.localY=y;} }
  resetPose() { for(const b of this.bones.values()){b.localAngle=b.restAngle;b.localX=b.restX;b.localY=b.restY;} }
  // Per-character proportions: {bone:{x,y,length,angle}} in rig units. Cutout
  // dolls measure these from their own art so every part meets its joint.
  reshape(key,spec={}) {
    if(this.shape===key)return;
    for(const [n,s] of Object.entries(spec)){const b=this.bones.get(n);if(!b)continue;
      if(s.x!=null)b.restX=s.x;if(s.y!=null)b.restY=s.y;if(s.length!=null)b.length=s.length;if(s.angle!=null)b.restAngle=s.angle;}
    this.shape=key;this.resetPose();
  }
  refresh(bones=this.bones.values()) {
    for(const b of bones){b.worldX=this.rootX+b.x*this.facing;b.worldY=this.rootY+b.y;
      b.tipX=this.rootX+b.endX*this.facing;b.tipY=this.rootY+b.endY;b.worldAngle=b.angle*this.facing;}
  }
  // Two-bone IK after update(): put `side`'s hand on a point in scaled local
  // space (pre-mirror, root-relative). bend picks which way the elbow folds.
  reach(side,tx,ty,bend=1) { return this.solve(side+'_shoulder',side+'_upper_arm',side+'_lower_arm',side+'_hand',tx,ty,bend); }
  // Same solver for a leg: plant `side`'s ankle on a point.
  plant(side,tx,ty,bend=-1) { return this.solve(side+'_hip',side+'_thigh',side+'_shin',side+'_foot',tx,ty,bend); }
  solve(baseName,upperName,lowerName,endName,tx,ty,bend=1) {
    const shoulder=this.bones.get(baseName),upper=this.bones.get(upperName);
    const lower=this.bones.get(lowerName),hand=this.bones.get(endName);
    const l1=upper.length*this.scale,l2=lower.length*this.scale,dx=tx-shoulder.endX,dy=ty-shoulder.endY;
    const distance=Math.hypot(dx,dy),dist=Math.min(l1+l2-.001,Math.max(Math.abs(l1-l2)+.001,distance)),heading=Math.atan2(-dx,dy);
    tx=shoulder.endX-Math.sin(heading)*dist;ty=shoulder.endY+Math.cos(heading)*dist;
    const rawFold=Math.acos(Math.max(-1,Math.min(1,(l1*l1+dist*dist-l2*l2)/(2*l1*dist))));
    // Human flexion limits: limit maximum fold to ~160 deg (2.79 rad) and prevent hyperextension singularity (>0.005 rad)
    const fold=Math.max(0.005,Math.min(2.79,rawFold));
    upper.localAngle=heading+bend*fold-shoulder.angle;upper.compute(shoulder.endX,shoulder.endY,shoulder.angle,1,this.scale);
    lower.localAngle=Math.atan2(-(tx-upper.endX),ty-upper.endY)-upper.angle;lower.compute(upper.endX,upper.endY,upper.angle,1,this.scale);
    lower.flexion=lower.localAngle;lower.bisector=upper.angle+lower.localAngle*0.5;
    hand.compute(lower.endX,lower.endY,lower.angle,1,this.scale);this.refresh([upper,lower,hand]);
    for(const b of this.bones.values())if(b.parent===endName){b.compute(hand.endX,hand.endY,hand.angle,1,this.scale);this.refresh([b]);}
    return Math.hypot(dx,dy)<=l1+l2;
  }
  // lower: a locomotion pose (run, advance...) the legs keep while `state`
  // acts with the upper body -- cast while running, strike on the advance.
  applyPose(state='idle',opts={}) {
    const {lower=null}=opts;
    if(lower&&lower!==state&&UPPER_BODY_POSES.includes(state)){
      this.applyBody(lower,opts);
      const legs=LOWER_BODY.map(n=>{const b=this.bones.get(n);return [b,b.localAngle,b.localX,b.localY];});
      this.applyBody(state,opts);
      for(const [b,a,x,y] of legs){b.localAngle=a;b.localX=x;b.localY=y;}
      this.lower=lower;return;
    }
    this.lower=null;
    this.applyBody(state,opts);
  }
  applyBody(state='idle',{speed=1,progress=0,climbHeight=0,weapon='sword',staffStyle='plain',casting=null,bodyWidth=1,reducedMotion=false}={}) {
    this.resetPose(); this.pose=state; this.weapon=weapon; this.staffStyle=staffStyle;
    this.casting=['cast','cast_channel','cast_release'].includes(state)?casting:null;
    this.weaponStowed=Boolean(this.casting?.hands===2&&!isCastingImplement(weapon,this.casting)&&weapon!=='none');
    this.focusHold=null;this.constraintBlend=null;
    const wb=weaponBone(weapon);if(['staff','wand'].includes(weapon))wb.length=focusSockets(weapon,staffStyle).length;for(const side of ['right','left']){const b=this.bones.get(side+'_weapon');
      b.parent=side==='right'&&this.weaponStowed?'pelvis':side+'_hand';
      b.localX=side==='right'&&this.weaponStowed?-16:0;b.localY=side==='right'&&this.weaponStowed?-6:0;
      b.length=side==='right'?wb.length:0;b.localAngle=b.restAngle=side==='right'?(this.weaponStowed?Math.PI-.35:wb.angle):0;}
    for(const side of ['left','right'])for(const part of ['shoulder','hip']){const b=this.bones.get(side+'_'+part);b.localX=b.restX*bodyWidth;}
    const a=(n,v)=>this.setBoneAngle(n,v), pelvis=this.bones.get('pelvis');
    const t=reducedMotion?0:this.time, wave=Math.sin(t*.006*speed), breath=Math.sin(t*.002);
    // Poses read as silhouettes first: every combat state has a distinct
    // stance width, torso lean and weapon arc. Angles: + leans a torso forward
    // and swings a limb back; far = left, near = right (weapon hand).
    const stance=(drop=2,spread=1)=>{pelvis.localY+=drop;
      a('left_thigh',-.28*spread);a('left_shin',.22*spread);a('right_thigh',.3*spread);a('right_shin',.3*spread);};
    if(state==='run'||state==='move'||state==='travel') {
      a('left_thigh',wave*.62);a('right_thigh',-wave*.62);
      a('left_shin',.2+Math.max(0,-wave)*.9);a('right_shin',.2+Math.max(0,wave)*.9);
      a('left_upper_arm',-wave*.55);a('right_upper_arm',wave*.4-.2);a('left_lower_arm',-.5);a('right_lower_arm',-.7);
      a('spine',.14);pelvis.localY+=Math.abs(wave)*2.2;
    } else if(state==='jump'||state==='fall'||state==='fly'||state==='airborne') {
      a('left_thigh',-.7);a('right_thigh',.35);a('left_shin',1.1);a('right_shin',.8);
      a('left_upper_arm',.8);a('right_upper_arm',-1.3);a('right_lower_arm',-.5);a('spine',.1);
    } else if(state==='climb'||state==='vault') {
      const c=state==='vault'?0:Math.sin(t*.008+climbHeight*.1);
      a('left_upper_arm',2.5+c*.3);a('right_upper_arm',-2.5+c*.3);
      a('left_lower_arm',-.5);a('right_lower_arm',.5);
      a('left_thigh',-.3-c*.3);a('right_thigh',-.3+c*.3);
      a('left_shin',.8);a('right_shin',.8);
    } else if(state==='attack'||state==='strike'||state==='windup'||state==='cast') {
      // One arc: coil back (0-.35), snap through (.35-.5), settle (.5-1).
      const p=state==='windup'?.2:state==='strike'?.5:Math.min(1,Math.max(0,progress));
      const coil=p<.35?Math.sin(p/.35*Math.PI/2):p<.5?1-(p-.35)/.15:0;
      const hit=p<.35?0:p<.5?(p-.35)/.15:1-Math.min(1,(p-.5)/.5)*.55;
      stance(2+hit*2,1+hit*.5);
      a('spine',-.2*coil+.28*hit);a('head',.1*coil-.12*hit);
      a('right_upper_arm',.4-3.1*coil-1.45*hit);a('right_lower_arm',-.4-.6*coil+.3*hit);a('right_hand',2.5*hit);
      a('left_upper_arm',-.5+1*hit);a('left_lower_arm',-1.1+.5*hit);
      if(state==='cast'){a('right_upper_arm',-1.45);a('right_lower_arm',-.1);a('left_upper_arm',-1.2);a('left_lower_arm',-.3);}
      if(weapon==='bow'){a('right_upper_arm',-1.5);a('right_lower_arm',0);a('left_upper_arm',-1);a('left_lower_arm',-1.8);a('spine',0);}
    } else if(state==='cast_channel') {
      // Gathering: both hands draw in to a focus before the chest, weight
      // settles, a slow pulse runs through the arms while the spell builds.
      const pulse=Math.sin(t*.012)*.08;
      stance(3,1.1);a('spine',-.06);a('head',.06);
      a('right_upper_arm',-.95+pulse);a('right_lower_arm',-1.35);a('right_hand',.3);
      a('left_upper_arm',-.85-pulse);a('left_lower_arm',-1.45);
    } else if(state==='cast_release') {
      // Thrust: the focus drives out toward the target and the body follows.
      const p=Math.min(1,Math.max(0,progress)),push=p<.3?p/.3:1-(p-.3)/.7*.35;
      stance(2+push*2,1+push*.4);a('spine',.12+.18*push);a('head',-.08*push);
      a('right_upper_arm',-.95-.6*push);a('right_lower_arm',-1.35+1.2*push);a('right_hand',.2);
      a('left_upper_arm',-.85-.45*push);a('left_lower_arm',-1.45+.9*push);
    } else if(state==='crit') {
      // Heavy impact: the hit reaction driven further, one knee giving.
      stance(4,.6);a('spine',-.52);a('head',-.42);
      a('right_upper_arm',.85);a('right_lower_arm',-.4);a('left_upper_arm',1.0);a('left_lower_arm',-.2);
      a('left_shin',.55);pelvis.localX=-6;
    } else if(state==='dodge') {
      // Sway out of the line: weight back and low, torso pulled away.
      const p=Math.min(1,Math.max(0,progress)),out=Math.sin(Math.min(1,p*1.4)*Math.PI);
      stance(4+out*3,1.3);a('spine',-.28*out-.05);a('head',-.12*out);
      a('right_upper_arm',-.35);a('right_lower_arm',-1.1);a('left_upper_arm',.35+.3*out);a('left_lower_arm',-.8);
      pelvis.localX=-7*out;
    } else if(state==='death') {
      // Stagger back, knees buckle, then fold toward the ground; `down` holds after.
      const p=Math.min(1,Math.max(0,progress)),buckle=Math.min(1,p/.45),fall=Math.max(0,(p-.45)/.55);
      stance(1+buckle*6,.8);a('spine',-.3*buckle+.5*fall);a('head',-.35*buckle+.3*fall);
      a('left_shin',.4+1.1*buckle);a('right_shin',.4+1.2*buckle);a('left_thigh',-.3-.6*buckle);
      a('right_upper_arm',.6+.4*fall);a('right_lower_arm',-.3);a('left_upper_arm',.7+.4*fall);a('left_lower_arm',-.2);
      pelvis.localY+=fall*14;pelvis.localX=-3*buckle;
    } else if(state==='point') {
      stance(1,.6);a('spine',.06);a('head',-.04);
      a('right_upper_arm',-1.5);a('right_lower_arm',-.05);a('right_hand',.1);
      a('left_upper_arm',.1);a('left_lower_arm',-.3);
    } else if(state==='cheer') {
      stance(0,.6);a('spine',-.12);a('head',-.2);
      a('right_upper_arm',-2.9);a('right_lower_arm',-.2);a('left_upper_arm',2.8);a('left_lower_arm',.3);
      pelvis.localY+=Math.max(0,Math.sin(t*.01))*-2;
    } else if(state==='crossed') {
      stance(1,.5);a('spine',-.03);a('head',.04);
      a('right_upper_arm',-.2);a('right_lower_arm',-1.9);a('left_upper_arm',-.15);a('left_lower_arm',-1.85);
    } else if(state==='look') {
      stance(1,.55);a('spine',.02);a('head',-.14+Math.sin(t*.0015)*.06);
      a('right_upper_arm',-.08);a('right_lower_arm',-.55);a('left_upper_arm',.12);a('left_lower_arm',-.2);
    } else if(state==='wave') {
      stance(1,.55);a('spine',.02);a('head',-.06);
      a('right_upper_arm',-2.5);a('right_lower_arm',-.5+Math.sin(t*.014)*.45);
      a('left_upper_arm',.12);a('left_lower_arm',-.2);
    } else if(state==='salute') {
      stance(0,.45);a('spine',-.04);a('head',-.04);
      a('right_upper_arm',-1.1);a('right_lower_arm',-2.3);a('left_upper_arm',.05);a('left_lower_arm',-.1);
    } else if(state==='guard'||state==='combat'||state==='block') {
      stance(3.5,1.25);a('spine',.1);
      a('right_upper_arm',-.55);a('right_lower_arm',-1.05);a('right_hand',.45);
      a('left_upper_arm',-.55);a('left_lower_arm',-.9);
      pelvis.localY+=breath*.5;
    } else if(state==='hit'||state==='impact') {
      stance(1,.7);a('spine',-.34);a('head',-.3);
      a('right_upper_arm',.55);a('right_lower_arm',-.6);a('left_upper_arm',.7);a('left_lower_arm',-.3);
      pelvis.localX=-3;
    } else if(state==='down'||state==='ko') {
      pelvis.localY=-10;a('pelvis',-1.35);a('left_shin',.45);a('right_shin',.6);
    } else if(state==='ready'||state==='battleIdle') {
      // Battle line idle: weight forward, weapon up, a slow bob. `ready` is the
      // acting combatant and leans in a touch further.
      const lean=state==='ready'?.08:0;
      stance(3+lean*10,1.15);a('spine',.12+lean);a('head',-.04);
      a('right_upper_arm',-.7-lean);a('right_lower_arm',-1.0);a('right_hand',.5);
      a('left_upper_arm',-.35);a('left_lower_arm',-.95);
      pelvis.localY+=Math.sin(t*.004)*1.1;
    } else if(state==='advance'||state==='retreat') {
      // Step out to strike and back to the line; retreat reads as a backstep.
      const dir=state==='advance'?1:-1,w=Math.sin(t*.012*speed);
      a('left_thigh',w*.5*dir);a('right_thigh',-w*.5*dir);
      a('left_shin',.25+Math.max(0,-w)*.7);a('right_shin',.25+Math.max(0,w)*.7);
      a('spine',dir>0?.24:-.08);a('right_upper_arm',dir>0?-.9:-.4);a('right_lower_arm',-.9);
      a('left_upper_arm',-w*.35);a('left_lower_arm',-.6);pelvis.localY+=Math.abs(w)*1.6;
    } else if(state==='defend') {
      stance(5,1.35);a('spine',.22);a('head',.06);
      a('left_upper_arm',-1.35);a('left_lower_arm',-.35);
      a('right_upper_arm',-.2);a('right_lower_arm',-1.3);a('right_hand',.9);
    } else if(state==='victory') {
      stance(0,.6);a('spine',-.1);a('head',-.18);
      a('right_upper_arm',-2.75);a('right_lower_arm',-.25);a('right_hand',.2);
      a('left_upper_arm',.25);a('left_lower_arm',-.9);
      pelvis.localY+=Math.max(0,Math.sin(t*.006))*-1.5;
    } else if(state==='kneel') {
      // Low HP: one knee down, weapon arm braced on the thigh.
      pelvis.localY+=13;a('spine',.38);a('head',.22);
      a('left_thigh',-1.35);a('left_shin',2.05);a('right_thigh',.15);a('right_shin',1.55);
      a('right_upper_arm',-.25);a('right_lower_arm',-.9);a('left_upper_arm',.35);a('left_lower_arm',-.4);
      pelvis.localY+=breath*.8;
    } else {
      // Ready idle: loose stance, weapon low and forward, slow breath.
      stance(1,.55);a('spine',.04+breath*.012);
      a('right_upper_arm',-.08);a('right_lower_arm',-.55);a('left_upper_arm',.12);a('left_lower_arm',-.2);
      pelvis.localY+=breath*.45;
    }
    // Secondary motion on the detail joints: hair and cape trail the body's
    // lean and motion; fingers close on a grip in every armed stance.
    const lean=this.bones.get('spine').localAngle, sway=Math.sin(t*.003)*.05;
    const moving=['run','move','travel','advance','retreat'].includes(state);
    const trail=(moving?.35:.08)+(state==='jump'||state==='airborne'?-.3:0);
    a('hair_1',.35+lean*.6+trail*.6+sway);a('hair_2',.1+trail*.3+sway);a('hair_3',.1+trail*.3+sway*1.4);
    a('cape_1',.08+lean*.8+trail);a('cape_2',.04+trail*.5+sway);a('cape_3',.03+trail*.4+sway*1.2);
    const grip=!['down','ko','death','climb','vault','victory','point','wave','cheer'].includes(state);
    a('right_fingers',grip?1.25:.15);a('right_thumb',grip?-1.1:-.7);
    a('left_fingers',['defend','block','guard','crossed'].includes(state)?1.1:.2);
    a('jaw',['attack','strike','victory','hit','crit','cheer','cast_release'].includes(state)?.12:0);
    // A two-handed grip reaches the same weapon with the supporting hand.
    // Casting and reactions keep their own weapon arm; the support IK still follows.
    if(this.casting) {
      const {stance:kind,hands}=this.casting,release=state==='cast_release';
      const push=release?Math.sin(Math.min(1,progress/.6)*Math.PI/2):0;
      if(kind==='overhead') {
        a('right_upper_arm',-2.5+push*.7);a('right_lower_arm',-.45);
        a('left_upper_arm',2.5-push*.7);a('left_lower_arm',.45);a('spine',-.12+push*.2);
      } else if(kind==='mend'||kind==='ward') {
        a('right_upper_arm',-.8-push*.45);a('right_lower_arm',-1.15);
        a('left_upper_arm',.8+push*.45);a('left_lower_arm',1.15);a('spine',-.04);
      } else if(kind==='aim') {
        a('right_upper_arm',-1.1-push*.35);a('right_lower_arm',-.6+push*.45);
        a('left_upper_arm',-1.1-push*.35);a('left_lower_arm',-.6+push*.45);
      }
      // An equipped non-focus weapon stays lowered while the free hand casts.
      if(hands===1&&weapon!=='none'&&!isCastingImplement(weapon,this.casting)) {
        a('right_upper_arm',.15);a('right_lower_arm',-.35);
      } else if(hands===1&&(weapon==='none'||isCastingImplement(weapon,this.casting))) {a('left_upper_arm',.2);a('left_lower_arm',-.35);}
      a('left_fingers',.1);if(weapon==='none'||this.weaponStowed)a('right_fingers',.1);
    }
    const ownArm=['cast_channel','cast_release','crit','dodge','death'].includes(state);
    if((this.twoHanded()||this.casting&&isCastingImplement(weapon,this.casting))&&ownArm) {
      // The wrist squares the shaft to the world: upright while channelling,
      // tipped at the target on release, knocked back on a reaction.
      const tilt=this.casting?.stance==='overhead'?(state==='cast_release'?.9:-.35):{cast_channel:0,cast_release:.6,crit:-.4,dodge:-.25,death:-.9}[state];
      const g=n=>this.bones.get(n).localAngle;
      a('right_hand',tilt-(g('pelvis')+g('spine')+g('torso')+g('right_upper_arm')+g('right_lower_arm')));
    }
    if(this.twoHanded()&&!ownArm) {
      a('right_upper_arm',-.35);a('right_lower_arm',-1.2);a('right_hand',1.55);
    }
    // Focus weapons rest below the chest, already pointed into the facing direction.
    // The wrist sets the shaft angle; IK below puts both elbows on that same pose.
    const carry=['idle','ready','battleIdle','combat','guard','block','run','move','travel','advance','retreat'].includes(state);
    if(['staff','wand'].includes(weapon)&&(carry||this.casting&&(isCastingImplement(weapon,this.casting)||this.casting.hands===1))) {
      const lowered=this.casting&&!isCastingImplement(weapon,this.casting);
      const high=!lowered&&this.casting?.stance==='overhead',release=!lowered&&state==='cast_release';
      const tilt=lowered?.85:high?(release?1.25:.55):release?1.32:this.casting ? .95 : 1.05;
      this.focusHold={x:high?2:release?18:14,y:lowered?22:high?-16:release?10:16};
      const g=n=>this.bones.get(n).localAngle;
      a('right_hand',tilt+.15-(g('pelvis')+g('spine')+g('torso')+g('right_upper_arm')+g('right_lower_arm')));
    }
  }
  update(dt,x,y,facing=1) {
    this.time+=Math.max(0,Math.min(64,dt||0));this.facing=facing<0?-1:1;
    this.rootX=x;this.rootY=y;
    for(const b of this.bones.values()) {
      const p=this.bones.get(b.parent);
      b.compute(p?.endX||0,p?.endY||0,p?.angle||0,1,this.scale);
      b.worldX=x+b.x*this.facing;b.worldY=y+b.y;
      b.tipX=x+b.endX*this.facing;b.tipY=y+b.endY;b.worldAngle=b.angle*this.facing;
    }
    if(this.focusHold) {
      const hand=this.bones.get('right_hand'),angle=hand.angle,chest=this.bones.get('torso');
      this.reachPoseHand('right',chest.x+this.focusHold.x*this.scale,chest.y+this.focusHold.y*this.scale);
      this.turnHand('right',angle);
    }
    if(this.casting) {
      const {stance,hands}=this.casting,release=this.pose==='cast_release';
      const chest=this.bones.get('torso'),implement=isCastingImplement(this.weapon,this.casting);
      const high=stance==='overhead',wide=stance==='ward',mend=stance==='mend';
      const y=high?-19:mend?10:release?-1:4;
      // Both palms face forward. Mirroring a local arm angle sent the far arm
      // backward; spatial targets keep the elbows below the casting hands.
      const active=implement?(hands===2&&this.weapon==='wand'?['left']:[]):
        hands===2?['right','left']:[this.weapon==='none'?'right':'left'];
      for(const side of active) {
        const near=side==='right',x=high?(near?18:0):near?(release?32:24):(release?14:7);
        this.reachPoseHand(side,chest.x+x*this.scale,chest.y+(y+(wide&&!near?8:0))*this.scale);
        const old=this.constraintBlend?.snap.hands?.[side],k=this.constraintBlend?.k??1;
        this.turnHand(side,old?old.angle+((high?-2.4:-1.4)-old.angle)*k:high?-2.4:-1.4);
      }
    }
    if(this.twoHanded()&&this.weapon==='staff') {
      // Both grips must be reachable, including attacks and reactions. Project
      // the main grip into the overlap of the two arm workspaces before IK.
      const hand=this.bones.get('right_hand'),angle=hand.angle,g=staffSockets(this.staffStyle).grip*this.scale;
      const ox=-Math.sin(angle-.15)*g,oy=Math.cos(angle-.15)*g;
      let tx=hand.x,ty=hand.y;
      for(let i=0;i<24;i++)for(const side of ['right','left']) {
        const shoulder=this.bones.get(side+'_shoulder'),off=side==='left';
        const cx=shoulder.x-(off?ox:0),cy=shoulder.y-(off?oy:0);
        const radius=(this.bones.get(side+'_upper_arm').length+this.bones.get(side+'_lower_arm').length)*this.scale-.01;
        const dx=tx-cx,dy=ty-cy,d=Math.hypot(dx,dy);
        if(d>radius){tx=cx+dx*radius/d;ty=cy+dy*radius/d;}
      }
      this.reach('right',tx,ty,1);this.turnHand('right',angle);
    }
    if(this.twoHanded()) {
      // Supporting hand grips the actual rendered weapon shaft (same IK solver).
      const hand=this.bones.get('right_hand'),grip=this.weapon==='bow'?0:this.weapon==='staff'?staffSockets(this.staffStyle).grip:-12,angle=hand.angle-.15;
      this.reach('left',hand.x-Math.sin(angle)*grip*this.scale,hand.y+Math.cos(angle)*grip*this.scale,1);
      this.setBoneAngle('left_fingers',1.1);
      this.turnHand('left',hand.angle);
    }
    const oldWeapon=this.constraintBlend?.snap.weapon,b=this.bones.get('right_weapon');
    if(oldWeapon&&oldWeapon.parent!==b.parent) {
      // Reparenting to a stow socket changes coordinate frames. Blend the
      // rendered world frame so the staff travels continuously to/from the hip.
      const k=this.constraintBlend.k;
      b.x=oldWeapon.x+(b.x-oldWeapon.x)*k;b.y=oldWeapon.y+(b.y-oldWeapon.y)*k;
      const delta=Math.atan2(Math.sin(b.angle-oldWeapon.angle),Math.cos(b.angle-oldWeapon.angle));
      b.angle=oldWeapon.angle+delta*k;
      b.endX=b.x-Math.sin(b.angle)*b.length*this.scale;b.endY=b.y+Math.cos(b.angle)*b.length*this.scale;this.refresh([b]);
    }
  }
  reachPoseHand(side,x,y) {
    const old=this.constraintBlend?.snap.hands?.[side],k=this.constraintBlend?.k??1;
    return this.reach(side,old?old.x+(x-old.x)*k:x,old?old.y+(y-old.y)*k:y,1);
  }
  turnHand(side,angle) {
    const hand=this.bones.get(side+'_hand'),arm=this.bones.get(side+'_lower_arm');
    hand.localAngle=angle-arm.angle;hand.compute(arm.endX,arm.endY,arm.angle,1,this.scale);this.refresh([hand]);
    for(const b of this.bones.values())if(b.parent===side+'_hand'){b.compute(hand.endX,hand.endY,hand.angle,1,this.scale);this.refresh([b]);}
  }
  twoHanded() { return !(this.casting&&(this.casting.hands===1||!isCastingImplement(this.weapon,this.casting)))&&TWO_HANDED.includes(this.weapon)&&!['down','ko','death','climb','vault','point','wave','cheer','crossed','salute'].includes(this.pose); }
  // Crossfade support: capture local joint state, then after the next
  // applyPose() pull it back toward the capture by (1-k). k=1 is the new pose.
  snapshot() {
    const snap=new Map([...this.bones].map(([n,b])=>[n,[b.localAngle,b.localX,b.localY,b.parent]]));
    snap.hands=Object.fromEntries(['left','right'].map(side=>{const b=this.bones.get(side+'_hand');return [side,{x:b.x,y:b.y,angle:b.angle}];}));
    const weapon=this.bones.get('right_weapon');snap.weapon={x:weapon.x,y:weapon.y,angle:weapon.angle,parent:weapon.parent};
    return snap;
  }
  blendFrom(snap,k) {
    if(!snap||k>=1)return;const j=1-Math.max(0,k);
    this.constraintBlend={snap,k:1-j};
    for(const [n,b] of this.bones){const s=snap.get(n);if(!s||s[3]!==undefined&&s[3]!==b.parent)continue;
      b.localAngle+=(s[0]-b.localAngle)*j;b.localX+=(s[1]-b.localX)*j;b.localY+=(s[2]-b.localY)*j;}
  }
  getSocket(name) {
    if(name==='focus'){
      // Spell focus: a staff's head, else the point between both hands.
      if(isCastingImplement(this.weapon,this.casting))return this.getSocket('weapon_tip');
      if(this.casting?.hands===1)return this.getSocket(this.weapon==='none'?'main_hand':'off_hand');
      const r=this.getSocket('main_hand'),l=this.getSocket('off_hand');
      return {x:(r.x+l.x)/2,y:(r.y+l.y)/2,rotation:r.rotation,facing:this.facing,scale:this.scale};
    }
    if(name==='weapon_main'){const b=this.bones.get('right_weapon');return {x:b.worldX,y:b.worldY,rotation:b.worldAngle,facing:this.facing,scale:this.scale};}
    let n=SOCKET_BONE[name];
    if(!n){if(!warned.has(name)){warned.add(name);globalThis.console?.warn?.(`skeletal-rig: unknown socket "${name}", using chest`);}n='torso';}
    const b=this.bones.get(n);
    return {x:b?.tipX||0,y:b?.tipY||0,rotation:b?.worldAngle||0,facing:this.facing,scale:this.scale};
  }
  drawSegmented(ctx) { // Last-resort diagnostic fallback, never invent equipment.
    ctx.save();ctx.strokeStyle='#bda77e';ctx.lineWidth=4*this.scale;ctx.lineCap='round';
    for(const b of this.bones.values())if(b.length){ctx.beginPath();ctx.moveTo(b.worldX,b.worldY);ctx.lineTo(b.tipX,b.tipY);ctx.stroke();}
    ctx.restore();
  }
  drawMonolithic(ctx,image,width,height,squash=1,footPadding=0) {
    ctx.save();ctx.translate(this.rootX,this.rootY);ctx.scale(this.facing,squash);
    ctx.drawImage(image,-width/2,-height*(1-footPadding),width,height);ctx.restore();
  }
}
