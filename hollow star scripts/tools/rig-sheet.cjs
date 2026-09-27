/* Rig sheet: render the paperdoll rigs into a pose sheet, with the skeleton
   drawn over them, and print numeric reports. For tuning torso, shoulders and
   arms without paying for full screenshots: the PNG is small, the reports are text.

   Usage (from "hollow star scripts"):
     node tools/rig-sheet.cjs                                   # hero, pose set A
     node tools/rig-sheet.cjs --rig doran --set D --scale 2.9 --cols 4
     node tools/rig-sheet.cjs --armor plate --gender female --set A
     node tools/rig-sheet.cjs --weapon axe --hands two-handed     # weapon family: sword axe mace dagger polearm staff wand bow none
     node tools/rig-sheet.cjs --poses "idle,combat:windup,combat:strike+,crossed"
     node tools/rig-sheet.cjs --overlay 0                        # art only
     node tools/rig-sheet.cjs --rig doran --set H --scale 2.6 --cols 4   # Doran's carries and swings (pose:beat:carry, swing:<style>@<0..1>)
     node tools/rig-sheet.cjs --report drift                     # torso hem vs hips, per pose
     node tools/rig-sheet.cjs --report reach                     # arm targets the IK could not reach
     node tools/rig-sheet.cjs --report elbow                     # per-frame arm jumps across blends
     node tools/rig-sheet.cjs --rig doran --report swings        # Doran's swings frame by frame: elbow jumps, share of frames two-handed
     node tools/rig-sheet.cjs --report trace --poses "cheer,combat:windup" --frames 10   # arm data frame by frame
     node tools/rig-sheet.cjs --yaw 0.35                         # body turn (needs web/rig-body.js)
     node tools/rig-sheet.cjs --from snapshots/20260926-rig-torso-arms-before   # render the pre-edit files

   Sets: A idle/combat/windup/strike/follow/guard - B run/point/wave/cheer/crossed/kneel
         C hit/crit/cast/victory/study - D a mixed eight. A pose is `pose` or `pose:beat`;
         a trailing + on the beat (strike+) settles into the follow-through.
   Output: .local/rig-sheet/<name>.png (disposable run state). Presentation only. */
const {chromium}=require('playwright');
const fs=require('node:fs');const path=require('node:path');const http=require('node:http');
const root=path.resolve(__dirname,'..');const webRoot=path.join(root,'web');const outDir=path.join(root,'.local','rig-sheet');

const SETS={
  A:'idle,combat,combat:windup,combat:strike,combat:strike+,combat:guard',
  H:'idle::stowed,idle::shoulder,idle::ready,run::ready,swing:chop@.3,swing:chop@.56,swing:sweep@.4,swing:sweep@.6',
  B:'run,point,wave,cheer,crossed,kneel',
  C:'combat:hit,combat:crit,combat:cast_channel,combat:cast_release,victory,study',
  D:'idle,combat,combat:windup,combat:strike,combat:strike+,combat:guard,run,crossed',
};
function parseArgs(argv){
  const a={rig:'hero',gender:'male',armor:'',weapon:'sword',set:'A',overlay:'1',scale:'3.4',cols:'6',report:'',loadout:'',yaw:'',hands:'',carry:'',wide:''};
  for(let i=0;i<argv.length;i++){const k=argv[i],v=argv[i+1];
    if(k==='--help'||k==='-h'){a.help=true;continue;}
    if(!k.startsWith('--')||v==null)throw new Error(`bad arg ${k}`);
    a[k.slice(2)]=v;i++;}
  return a;}

const TYPES={'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.json':'application/json','.png':'image/png','.html':'text/html'};
async function startStatic(page,from){
  const server=http.createServer((q,r)=>{
    const p=decodeURIComponent(new URL(q.url,'http://x').pathname);
    if(p==='/__rig-sheet.html'){r.writeHead(200,{'content-type':'text/html'});r.end(page);return;}
    const rel=p.replace(/^\//,''),over=from&&path.join(from,path.basename(rel));   // --from: pre-edit copies win over web/
    const file=over&&fs.existsSync(over)&&fs.statSync(over).isFile()?over:path.resolve(webRoot,rel);
    if(!file.startsWith(webRoot)&&file!==over||!fs.existsSync(file)||!fs.statSync(file).isFile()){r.writeHead(404);r.end();return;}
    r.writeHead(200,{'content-type':TYPES[path.extname(file)]||'application/octet-stream'});r.end(fs.readFileSync(file));});
  server.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
  return {server,base:`http://127.0.0.1:${server.address().port}`};}

// The page: everything below runs in the browser against the real web modules.
const PAGE=`<!doctype html><meta charset="utf-8"><body style="margin:0;background:#121826"><canvas id="out"></canvas>
<script>globalThis.HSRUI={escape:v=>String(v??'')};</script>
<script type="module">
import {dollModel} from '/paperdoll.js';
import {actorRig,SkeletalRig} from '/sprite-renderer.js';
const cfg=window.__CFG;
let VIEW=null;if(cfg.hasBody)VIEW=(await import('/rig-body.js')).VIEW;
if(VIEW&&cfg.yaw!=='')VIEW.yaw=Number(cfg.yaw);
const S=Number(cfg.scale),cols=Number(cfg.cols),facing=1;
const list=(cfg.poses||'').split(',').filter(Boolean).map(s=>s.split(':'));
function item(){
  if(cfg.rig==='doran')return {id:'p0',name:'Doran',identity:'doran',alive:true,loadout:cfg.loadout||'cleaver'};
  if(cfg.rig==='wren')return {id:'p1',name:'Wren',identity:'wren',alive:true,loadout:cfg.loadout||'staff'};
  const eq=[{presentation:{silhouette:cfg.weapon,material:'steel',rarity:'mundane',fx:[],handedness:cfg.hands||(['bow','staff','polearm'].includes(cfg.weapon)?'two-handed':'one-handed')}}];
  if(cfg.armor)eq.push({presentation:{silhouette:'armor',material:cfg.armor,rarity:'mundane',fx:[]}});
  return {id:'h1',name:'Hero',race_id:'human',gender:cfg.gender,appearance:{},equipment:eq,hp:10};}
const model=dollModel(item(),{pose:'combat'}),def=actorRig(model);
const dummy=document.createElement('canvas').getContext('2d');
const result={};
let SWINGS={};if(cfg.rig==='doran')SWINGS=(await import('/doran-combat.js')).DORAN_SWINGS;

// Draw one pose settled (or, for beats with a trailing +, a few frames into the follow-through).
function settle(rig,ctx,pose,beat,x,floor,scale,paint=true,carry=cfg.carry||undefined){
  rig.scale=scale;
  // swing:<style>@<progress> plays one of Doran's keyframed swings up to that point of its clock.
  if(pose==='swing'){const [style,at]=beat.split('@'),ms=SWINGS[style]?.ms||500,p=Number(at||.5);let now=10000;
    for(let i=0;i<40;i++){now+=16;def.draw(dummy,rig,{...model,alive:true},{x,y:floor,facing,dt:16,now,pose:'idle',carry:'ready',idleFidgets:false,paint:false});}
    const t0=now+16,n=Math.max(1,Math.ceil(p*ms/16));
    for(let i=1;i<=n;i++){now=t0+i*16;def.draw(i===n&&paint?ctx:dummy,rig,{...model,alive:true},{x,y:floor,facing,dt:16,now,pose:'idle',carry:'ready',swing:style,swingAt:t0,idleFidgets:false,paint:i===n&&paint});}
    return;}
  const live=pose==='run'||beat==='strike+',frames=beat==='strike'?4:beat==='strike+'?12:live?26:3;let now=10000;
  for(let f=0;f<frames;f++){now+=16;
    def.draw(f===frames-1&&paint?ctx:dummy,rig,{...model,alive:pose!=='down'},{x,y:floor,facing,dt:16,now,pose,beat:beat.replace('+',''),carry,
      casting:null,reducedMotion:!live,idleFidgets:false,paint:f===frames-1&&paint});}}

// Sheet.
const cw=Math.round(60*S*(Number(cfg.wide)||1.25)),ch=Math.round(125*S*.98),rows=Math.ceil(list.length/cols);
const out=document.getElementById('out');out.width=cw*cols;out.height=ch*rows;
const c=out.getContext('2d');c.fillStyle='#121826';c.fillRect(0,0,out.width,out.height);
list.forEach(([pose,beat='',carry],i)=>{
  const x0=(i%cols)*cw,y0=Math.floor(i/cols)*ch,floor=y0+ch*.93,cx=x0+cw*.5;
  c.fillStyle=i%2?'#1a2133':'#1d2538';c.fillRect(x0,y0,cw,ch);
  c.strokeStyle='rgba(217,181,110,.25)';c.beginPath();c.moveTo(x0,floor+.5);c.lineTo(x0+cw,floor+.5);c.stroke();
  const rig=new SkeletalRig();settle(rig,c,pose,beat,cx,floor,S,true,carry||cfg.carry||undefined);
  if(cfg.overlay==='1'){
    const B=n=>rig.bones.get(n);
    const dot=(x,y,r,col)=>{c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fillStyle=col;c.fill();};
    const seg=(x1,y1,x2,y2,col,w=1.6)=>{c.beginPath();c.moveTo(x1,y1);c.lineTo(x2,y2);c.strokeStyle=col;c.lineWidth=w;c.stroke();};
    const chain=['pelvis','spine','torso','neck','head'].map(B);
    c.beginPath();chain.forEach((b,k)=>k?c.lineTo(b.worldX,b.worldY):c.moveTo(b.worldX,b.worldY));c.strokeStyle='rgba(255,255,255,.75)';c.lineWidth=1.4;c.stroke();
    for(const b of chain)dot(b.worldX,b.worldY,2.2,'#fff');
    const ls=B('left_shoulder'),rs=B('right_shoulder');seg(ls.worldX,ls.worldY,rs.worldX,rs.worldY,'rgba(255,224,122,.9)',1.2);
    for(const side of ['left','right']){
      const col=side==='right'?'#ff5050':'#4da8ff',sh=B(side+'_shoulder'),ua=B(side+'_upper_arm'),la=B(side+'_lower_arm');
      seg(ua.worldX,ua.worldY,ua.tipX,ua.tipY,col);seg(la.worldX,la.worldY,la.tipX,la.tipY,col);
      dot(sh.worldX,sh.worldY,3.4,col);dot(ua.tipX,ua.tipY,2.8,col);dot(la.tipX,la.tipY,2.8,col);
      const hp=B(side+'_hip');dot(hp.worldX,hp.worldY,2.6,col);}
  }
  c.fillStyle='rgba(232,225,207,.85)';c.font='12px system-ui';c.fillText(beat?beat.replace('+',' (follow)'):pose,x0+6,y0+15);
});

// Reports run at rig scale 1 so every number is in rig units.
const toWorld=(b,px,py)=>{const a=b.angle;return [b.x+px*Math.cos(a)-py*Math.sin(a),b.y+px*Math.sin(a)+py*Math.cos(a)];};
if(cfg.report==='drift'||cfg.report==='reach'){
  const rows=[];
  for(const [pose,beat=''] of list){
    const rig=new SkeletalRig();settle(rig,dummy,pose,beat,200,400,1);
    const st=rig.hero,B=n=>rig.bones.get(n),row={pose:beat||pose};
    if(cfg.report==='drift'&&st?.look?.dims){
      const d=st.look.dims,hem=d.waist+3.2;   // torso frame y of the hem; the same body point in the pelvis frame is hem-(spine+torso)
      const a=toWorld(B('torso'),0,hem),b=toWorld(B('pelvis'),0,hem-(d.spine+d.torso));
      row.drift=+Math.hypot(a[0]-b[0],a[1]-b[1]).toFixed(1);}
    if(cfg.report==='reach'&&st?.reach)row.reach=st.reach;
    rows.push(row);}
  result.rows=rows;
}
if(cfg.report==='elbow'){
  // Blend through the combat chain frame by frame and record the largest one-frame jump of each elbow.
  const chain=[['combat',''],['combat','windup'],['combat','strike'],['combat','guard'],['run',''],['crossed',''],['cheer',''],['combat','windup'],['combat','strike'],['combat','strike'],['combat','crit'],['combat','guard']];
  const rig=new SkeletalRig();rig.scale=1;let now=10000,worst=[];
  for(const [pose,beat] of chain){
    let prev=null,peak={step:0,frame:0},err=0;
    for(let f=0;f<26;f++){now+=16;
      def.draw(dummy,rig,{...model,alive:true},{x:200,y:400,facing,dt:16,now,pose,beat,casting:null,reducedMotion:false,idleFidgets:false,paint:false});
      const cur=['left','right'].map(s=>{const u=rig.bones.get(s+'_upper_arm');return [u.tipX,u.tipY];});
      if(prev)for(let k=0;k<2;k++){const step=Math.hypot(cur[k][0]-prev[k][0],cur[k][1]-prev[k][1]);if(step>peak.step)peak={step:+step.toFixed(1),frame:f,arm:k?'near':'far'};}
      const r=rig.hero?.reach;if(r)err=Math.max(err,r.near?.err||0,r.far?.err||0);   // how far a hand strays from its target mid-blend
      prev=cur;}
    worst.push({to:beat||pose,...peak,handErr:err});}
  result.rows=worst;
}
if(cfg.report==='swings'&&cfg.rig==='doran'){
  // Each keyframed swing played through frame by frame: largest one-frame jump of either elbow, and how far
  // the weapon hand strays from the pose target (a two-handed grip that cannot reach shows here).
  const rows=[];
  for(const style of Object.keys(SWINGS)){
    const rig=new SkeletalRig();rig.scale=1;let now=10000;
    for(let i=0;i<40;i++){now+=16;def.draw(dummy,rig,{...model,alive:true},{x:200,y:400,facing,dt:16,now,pose:'idle',carry:'ready',idleFidgets:false,paint:false});}
    const t0=now+16,ms=SWINGS[style].ms+SWINGS[style].hitstop+300;let prev=null,peak={step:0,at:0},short=0,twoHand=0,frames=0;
    for(let t=0;t<=ms;t+=16){now=t0+t;
      const sk=def.draw(dummy,rig,{...model,alive:true},{x:200,y:400,facing,dt:16,now,pose:'idle',carry:'ready',swing:style,swingAt:t0,idleFidgets:false,paint:false});
      const cur=['left','right'].map(k=>{const u=rig.bones.get(k+'_upper_arm');return [u.tipX,u.tipY];});
      if(prev)for(let k=0;k<2;k++){const d=Math.hypot(cur[k][0]-prev[k][0],cur[k][1]-prev[k][1]);if(d>peak.step)peak={step:+d.toFixed(1),at:t,arm:k?'near':'far'};}
      prev=cur;frames++;if(rig.doran.ch.sup>.9)twoHand++;const rc=rig.doran.reach||{};short=Math.max(short,rc.left?.short||0,rc.right?.short||0);}
    rows.push({style,maxElbowStep:peak,twoHandedShare:+(twoHand/frames).toFixed(2),maxShort:short});}
  result.rows=rows;
}
if(cfg.report==='trace'){
  // Frame-by-frame arm data through the listed poses, in order, on one rig.
  const rig=new SkeletalRig();rig.scale=1;let now=10000;const rows=[];
  for(const [pose,beat=''] of list)for(let f=0;f<(Number(cfg.frames)||14);f++){now+=16;
    def.draw(dummy,rig,{...model,alive:true},{x:200,y:400,facing,dt:16,now,pose,beat,casting:null,reducedMotion:false,idleFidgets:false,paint:false});
    const r=rig.hero?.reach||{},arm=k=>{const u=rig.bones.get(k+'_upper_arm');return [+(u.tipX-200).toFixed(1),+(u.tipY-400).toFixed(1)];};
    rows.push({pose:beat||pose,f,far:{bend:r.far?.bend,elbow:arm('left'),err:r.far?.err},near:{bend:r.near?.bend,elbow:arm('right'),err:r.near?.err}});}
  result.rows=rows;
}
window.__result=result;window.__done=true;
</script>`;

(async()=>{
  const a=parseArgs(process.argv.slice(2));
  if(a.help){console.log(fs.readFileSync(__filename,'utf8').split('*/')[0].replace('/*','').trim());return;}
  const cfg={...a,poses:a.poses||SETS[a.set]||SETS.A,hasBody:fs.existsSync(path.join(webRoot,'rig-body.js'))};
  const page=`${PAGE.replace('<script type="module">','<script>window.__CFG='+JSON.stringify(cfg)+';</script>\n<script type="module">')}`;
  const {server,base}=await startStatic(page,a.from?path.resolve(root,a.from):null);
  const browser=await chromium.launch();const tab=await browser.newPage({viewport:{width:1600,height:1000}});
  const logs=[];tab.on('console',m=>{if(['error','warning'].includes(m.type()))logs.push(`${m.type()}: ${m.text()}`);});
  tab.on('pageerror',e=>logs.push(`pageerror: ${e.message}`));
  await tab.goto(`${base}/__rig-sheet.html`);
  await tab.waitForFunction(()=>window.__done===true,null,{timeout:30000}).catch(e=>logs.push('timeout '+e.message));
  const result=await tab.evaluate(()=>window.__result||{});
  fs.mkdirSync(outDir,{recursive:true});
  const name=a.name||`${a.rig}-${a.poses?'custom':a.set}${a.armor?'-'+a.armor:''}${a.rig==='hero'?'-'+a.gender:''}`;
  const png=await tab.evaluate(()=>document.getElementById('out').toDataURL('image/png'));
  const file=path.join(outDir,`${name}.png`);fs.writeFileSync(file,Buffer.from(png.split(',')[1],'base64'));
  console.log(`sheet ${path.relative(root,file)}`);
  if(a.report){console.log(`report ${a.report}`);for(const row of result.rows||[])console.log('  '+JSON.stringify(row));}
  if(logs.length){console.log('page issues:');for(const l of logs.slice(0,8))console.log('  '+l);process.exitCode=1;}
  await browser.close();server.close();
})().catch(e=>{console.error(e.message);process.exit(1);});
