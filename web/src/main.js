// Guardian Heart — WebGL interactive AR
// Three.js scene overlaid on a mirrored webcam, driven by MediaPipe hand tracking.
import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { HandLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';

const $ = (s) => document.querySelector(s);
const camEl = $('#cam'), badge = $('#badge'), errEl = $('#err');
function showErr(m){ errEl.textContent = String(m); console.error(m); }

// ---------- Three.js core ----------
const renderer = new THREE.WebGLRenderer({ canvas: $('#gl'), alpha: true, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();

// orthographic camera: world spans y in [-1,1], x scaled by aspect
let aspect = 1;
const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, -10, 10);
cam.position.z = 4;

// lights (key : rim : fill ~ 5:3:1, per the lock spec)
const key = new THREE.DirectionalLight(0xfff6ee, 0.42); key.position.set(-1.0, 1.3, 2.0);
const rim = new THREE.DirectionalLight(0xbfc8ff, 0.28); rim.position.set(1.4, 1.2, -1.2);
const fill = new THREE.DirectionalLight(0xfff3ea, 0.15); fill.position.set(0.3, -1.4, 1.4);
scene.add(key, rim, fill, new THREE.AmbientLight(0x556070, 0.14));
// soft pastel environment so metal + gems read
const pmrem = new THREE.PMREMGenerator(renderer);
{
  const s = new THREE.Scene();
  const g = new THREE.SphereGeometry(5, 24, 16);
  const m = new THREE.ShaderMaterial({ side: THREE.BackSide, uniforms:{},
    vertexShader:`varying vec3 vp; void main(){ vp=position; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`varying vec3 vp; void main(){ float t=clamp(vp.y/5.*.5+.5,0.,1.);
      vec3 c=mix(vec3(.12,.13,.17),vec3(.34,.36,.42),t); gl_FragColor=vec4(c,1.);}` });
  s.add(new THREE.Mesh(g, m));
  scene.environment = pmrem.fromScene(s).texture;
  scene.environment = null;  // DIAG
}

function resize(){
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h);
  aspect = w / h;
  cam.left = -aspect; cam.right = aspect; cam.top = 1; cam.bottom = -1;
  cam.updateProjectionMatrix();
  composer && composer.setSize(w, h);
}
addEventListener('resize', resize);

// bloom
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, cam));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.25, 0.4, 0.8);
composer.addPass(bloom);
composer.addPass(new OutputPass());   // applies tone mapping + sRGB (prevents white clipping)
resize();

// ---------- sprite textures (canvas-drawn) ----------
function tex(draw, size=128){
  const c = document.createElement('canvas'); c.width=c.height=size;
  draw(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function heartPath(g, s){
  const x=s/2, y=s*0.36, w=s*0.42;
  g.beginPath();
  g.moveTo(x, y+w*0.25);
  g.bezierCurveTo(x, y, x-w, y-w*0.5, x-w, y+w*0.15);
  g.bezierCurveTo(x-w, y+w*0.75, x, y+w*1.1, x, s*0.9);
  g.bezierCurveTo(x, y+w*1.1, x+w, y+w*0.75, x+w, y+w*0.15);
  g.bezierCurveTo(x+w, y-w*0.5, x, y, x, y+w*0.25);
  g.closePath();
}
const heartTex = tex((g,s)=>{ g.clearRect(0,0,s,s); g.shadowColor='rgba(255,120,170,.9)'; g.shadowBlur=s*0.14;
  heartPath(g,s); g.fillStyle='#ff5a86'; g.fill(); g.shadowBlur=0; g.lineWidth=s*0.03; g.strokeStyle='#ffd0e2'; g.stroke(); });
const orbTex = tex((g,s)=>{ const r=g.createRadialGradient(s/2,s/2,0,s/2,s/2,s/2);
  r.addColorStop(0,'rgba(255,255,255,1)'); r.addColorStop(.35,'rgba(255,245,255,.85)');
  r.addColorStop(1,'rgba(255,255,255,0)'); g.fillStyle=r; g.fillRect(0,0,s,s); });
const rayTex = tex((g,s)=>{ const r=g.createLinearGradient(0,0,0,s);
  r.addColorStop(0,'rgba(255,255,255,0)'); r.addColorStop(.5,'rgba(255,255,255,.9)');
  r.addColorStop(1,'rgba(255,255,255,0)'); g.fillStyle=r; g.fillRect(s*0.44,0,s*0.12,s); });

// ---------- artifacts ----------
// give a loaded FBX unlit materials using its own baked textures (no lighting wash)
function styleBaked(root, fallback){
  root.traverse(o=>{
    if(!o.isMesh) return;
    const src = Array.isArray(o.material) ? o.material[0] : o.material;
    const map = (src && src.map) ? src.map : null;
    if(map) map.colorSpace = THREE.SRGBColorSpace;
    o.material = new THREE.MeshBasicMaterial({ map, color: map ? 0xffffff : fallback });
  });
}
// EGG — the real egg.fbx (spins + bobs); loaded async into `egg`
const eggLoader = new FBXLoader();
eggLoader.load('./assets/egg.fbx', (fbx)=>{
  const box = new THREE.Box3().setFromObject(fbx);
  const size = new THREE.Vector3(); box.getSize(size);
  const s = 1.0 / Math.max(size.x, size.y, size.z);
  fbx.scale.setScalar(s);
  const c = new THREE.Vector3(); box.getCenter(c); fbx.position.sub(c.multiplyScalar(s));
  const holder = new THREE.Group(); holder.add(fbx);
  styleBaked(holder, 0xb01524);
  holder.scale.setScalar(0.42);
  holder.visible = false; scene.add(holder);
  egg = holder;
}, undefined, (e)=>showErr('egg FBX load fail: '+e));

// LOCK — load the FBX, gold body + white opal petals
let lockProto = null, lockPetalMats = [], lockGoldMats = [];
// unlit materials using the FBX's baked textures (gold body / opal petals) — no lighting wash.
// glow is done by tinting material.color (multiplies the texture).
function styleLock(root){
  root.traverse(o=>{
    if(!o.isMesh) return;
    const src = Array.isArray(o.material) ? o.material[0] : o.material;
    const map = (src && src.map) ? src.map : null;
    const n = o.name.toLowerCase();
    const base = map ? 0xffffff
      : n.includes('petal') ? 0xc6cede
      : n.includes('keyhole') ? 0x0a0a0a
      : 0xd28f18;
    const m = new THREE.MeshBasicMaterial({ map, color:base });
    m.userData.base = new THREE.Color(base);
    o.material = m;
    if(n.includes('petal')) lockPetalMats.push(m);
    else if(!n.includes('keyhole')) lockGoldMats.push(m);
  });
}
const loader = new FBXLoader();
loader.load('./assets/lock_touchdesigner.fbx', (fbx)=>{
  // normalize size: fit into ~1 unit
  const box = new THREE.Box3().setFromObject(fbx);
  const size = new THREE.Vector3(); box.getSize(size);
  const s = 1.0 / Math.max(size.x, size.y, size.z);
  fbx.scale.setScalar(s);
  const c = new THREE.Vector3(); box.getCenter(c); fbx.position.sub(c.multiplyScalar(s));
  const holder = new THREE.Group(); holder.add(fbx);
  styleLock(holder);
  holder.scale.setScalar(0.5);
  lockProto = holder;
}, undefined, (e)=>showErr('FBX load fail: '+e));

// live instances
let egg = null;   // set once egg.fbx loads
let lock = null;                 // set once FBX ready
function ensureLock(){ if(!lock && lockProto){ lock = lockProto.clone(true);
  lock.visible=false; scene.add(lock);
  // re-collect materials of the clone so glow drives the visible instance
  lockPetalMats=[]; lockGoldMats=[];
  lock.traverse(o=>{ if(o.isMesh){ const n=o.name.toLowerCase();
    if(n.includes('petal')) lockPetalMats.push(o.material);
    else if(!n.includes('keyhole')) lockGoldMats.push(o.material); } });
} return lock; }

// ---------- particle pools ----------
function pool(texture, n, blending=THREE.AdditiveBlending){
  const arr=[];
  for(let i=0;i<n;i++){
    const sp=new THREE.Sprite(new THREE.SpriteMaterial({ map:texture, transparent:true,
      blending, depthTest:false, opacity:0 }));
    sp.visible=false; scene.add(sp); arr.push({ sp, life:0, ttl:0, vx:0,vy:0, born:0 });
  }
  return arr;
}
const hearts = pool(heartTex, 60, THREE.NormalBlending);
const sparkles = pool(heartTex, 34, THREE.NormalBlending);
const orbs = pool(orbTex, 16);
// rays: planes (need rotation) -> use meshes
const rays = [];
for(let i=0;i<14;i++){ const m=new THREE.Mesh(new THREE.PlaneGeometry(0.06,0.5),
  new THREE.MeshBasicMaterial({ map:rayTex, transparent:true, blending:THREE.AdditiveBlending, depthTest:false, opacity:0 }));
  m.visible=false; scene.add(m); rays.push(m); }

// ---------- MediaPipe ----------
let landmarker=null;
async function initHands(){
  const files = await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.8/wasm');
  landmarker = await HandLandmarker.createFromOptions(files, {
    baseOptions:{ modelAssetPath:'./assets/hand_landmarker.task' },
    numHands:2, runningMode:'VIDEO' });
}

// ---------- gesture helpers ----------
const V = (p)=>({x:p.x, y:p.y, z:p.z||0});
function dist(a,b){ const dx=a.x-b.x, dy=a.y-b.y; return Math.hypot(dx,dy); }
function fingerExt(lm, tip, pip){ return (lm[tip].y < lm[pip].y - 0.02); } // up = smaller y
function readHands(res){
  const out=[];
  if(!res || !res.landmarks) return out;
  for(let i=0;i<res.landmarks.length;i++){
    const lm=res.landmarks[i];
    const handed = res.handednesses?.[i]?.[0]?.categoryName || 'Right';
    // MediaPipe handedness is for the raw (unmirrored) image; we display mirrored,
    // so the on-screen hand is the opposite label. Flip for intuitive left/right.
    const side = handed === 'Right' ? 'Left' : 'Right';
    const idxExt = fingerExt(lm,8,6), midExt=fingerExt(lm,12,10),
          ringExt=fingerExt(lm,16,14), pinkExt=fingerExt(lm,20,18);
    const openPalm = idxExt && midExt && ringExt && pinkExt;
    out.push({ side, lm, tipIndex:V(lm[8]), tipThumb:V(lm[4]),
      idxOnly: idxExt && !midExt && !ringExt && !pinkExt, openPalm,
      wrist:V(lm[0]) });
  }
  return out;
}
// screen (mirrored) -> world. lm.x,y in [0,1] on raw image; mirrored display => sx = 1-x
function toWorld(p){ const sx = 1 - p.x, sy = p.y;
  return { x:(sx*2-1)*aspect, y:-(sy*2-1) }; }

// ---------- classify ----------
// kinds: idle, egg, lock, fuse, fingerHeart, bigHeart
function classify(hands){
  const L = hands.find(h=>h.side==='Left'), R = hands.find(h=>h.side==='Right');
  if(hands.length>=2 && hands[0].openPalm && hands[1].openPalm) return {kind:'bigHeart', hands};
  if(L && R){
    const idxGap = dist(L.tipIndex, R.tipIndex);
    const thumbGap = dist(L.tipThumb, R.tipThumb);
    const handDist = dist(L.wrist, R.wrist);
    if(idxGap < 0.10 && handDist < 0.9){
      if(thumbGap < 0.10) return {kind:'fingerHeart', L, R};
      return {kind:'fuse', L, R};
    }
  }
  const res = {kind:'idle'};
  if(L && L.idxOnly){ res.egg = L.tipIndex; }
  if(R && R.idxOnly){ res.lock = R.tipIndex; }
  if(res.egg || res.lock) res.kind='summon';
  return res;
}

// ---------- effect spawning ----------
function spawnHearts(cx, cy, count, spd, now){
  let s=0;
  for(const h of hearts){ if(h.life>0) continue;
    const a=Math.random()*Math.PI*2, v=spd*(0.6+Math.random()*0.8);
    h.vx=Math.cos(a)*v; h.vy=Math.sin(a)*v+0.2; h.ttl=1.1+Math.random()*0.5; h.life=h.ttl; h.born=now;
    h.sp.position.set(cx,cy,0.1); h.sp.visible=true; const sc=0.08+Math.random()*0.05; h.sp.scale.setScalar(sc);
    if(++s>=count) break; }
}
function updateHearts(dt){
  for(const h of hearts){ if(h.life<=0) continue;
    h.life-=dt; if(h.life<=0){ h.sp.visible=false; h.sp.material.opacity=0; continue; }
    h.sp.position.x+=h.vx*dt; h.sp.position.y+=h.vy*dt; h.vy-=0.25*dt;
    const k=h.life/h.ttl; h.sp.material.opacity=Math.min(1,k*1.6);
    h.sp.scale.multiplyScalar(1+0.4*dt); }
}

// ---------- demo mode (no camera): scripted showcase ----------
const DEMO = new URLSearchParams(location.search).has('demo');
function demoClassify(t){
  const c = (new URLSearchParams(location.search).get('phase')==='summon') ? 0
          : (new URLSearchParams(location.search).get('phase')==='fuse') ? 5
          : t%12;
  if(c<4)  return { kind:'summon', egg:{x:0.72,y:0.42}, lock:{x:0.28,y:0.42} }; // raw coords (mirror -> egg left)
  if(c<8){ const y=0.42+0.04*Math.sin(t*1.5);
    return { kind:'fuse', L:{tipIndex:{x:0.52,y}}, R:{tipIndex:{x:0.48,y}} }; }
  return { kind:'bigHeart' };
}

// ---------- main loop ----------
let running=false, last=performance.now();
const eggRot={y:0}, lockRot={y:0};
function frame(){
  if(!running) return;
  const now=performance.now(), dt=Math.min(0.05,(now-last)/1000); last=now;
  let cls={kind:'idle'};
  if(DEMO){
    cls=demoClassify(now/1000);
  } else if(landmarker && camEl.readyState>=2){
    let res=null; try{ res=landmarker.detectForVideo(camEl, now); }catch(e){}
    cls=classify(readHands(res||{}));
  }
  const t=now/1000;

  // ---- EGG ----
  if(egg){
    egg.visible = !!cls.egg;
    if(cls.egg){ const w=toWorld(cls.egg); eggRot.y+=dt*1.0;
      egg.position.set(w.x, w.y+0.18+0.05*Math.sin(t*1.3), 0);
      egg.rotation.y=eggRot.y; }
  }

  // ---- LOCK ----
  const lk=ensureLock();
  const showLock = cls.kind==='fuse' || (cls.lock && cls.kind==='summon');
  if(lk){
    lk.visible=!!showLock;
    if(cls.kind==='fuse'){
      const wl=toWorld(cls.L.tipIndex), wr=toWorld(cls.R.tipIndex);
      lockRot.y+=dt*2.2;
      lk.position.set((wl.x+wr.x)/2,(wl.y+wr.y)/2+0.1,0);
      lk.rotation.y=lockRot.y;
      const p=0.5+0.5*Math.sin(t*3); lk.scale.setScalar(0.3*(1+0.1*p));
      // rainbow glow via color tint (brightened by pulse)
      const hue=(t*0.14)%1;
      const gc=new THREE.Color().setHSL(hue,0.8,0.55+0.12*p);
      const pc=new THREE.Color().setHSL(hue,0.45,0.82);
      lockGoldMats.forEach(m=>{ m.color.copy(gc); });
      lockPetalMats.forEach(m=>{ m.color.copy(pc); });
    } else if(showLock){
      const w=toWorld(cls.lock); lockRot.y+=dt*0.9;
      lk.position.set(w.x, w.y+0.18+0.05*Math.sin(t*1.3),0);
      lk.rotation.y=lockRot.y; lk.scale.setScalar(0.28);
      lockGoldMats.forEach(m=>{ m.color.copy(m.userData.base); });
      lockPetalMats.forEach(m=>{ m.color.copy(m.userData.base); });
    }
  }

  // ---- sparkles around the egg ----
  const sparkleOn = !!cls.egg && !!egg;
  for(let i=0;i<sparkles.length;i++){ const s=sparkles[i];
    if(!sparkleOn){ s.sp.visible=false; continue; }
    s.sp.visible=true; const gA=2.399963*i + t*0.9;
    const yy=1-(i/(sparkles.length-1))*2, ring=Math.sqrt(Math.max(0,1-yy*yy));
    const rad=0.32+0.06*Math.sin(t*1.3+i);
    s.sp.position.set(egg.position.x+Math.cos(gA)*ring*rad,
                      egg.position.y+yy*rad, 0.05);
    const tw=0.5+0.5*Math.sin(t*7+i*2.3); s.sp.scale.setScalar(0.028+0.03*tw);
    s.sp.material.opacity=0.45+0.4*tw; s.sp.material.color.setHex(0xff86ad);
  }

  // ---- fuse orbs + rays ----
  const fuse = cls.kind==='fuse' && lk && lk.visible;
  for(let i=0;i<orbs.length;i++){ const o=orbs[i];
    if(!fuse){ o.sp.visible=false; continue; }
    o.sp.visible=true; const ring=i%2, ang=t*(ring?-1.1:1.4)+i*(6.283/orbs.length);
    const rad=0.34+0.05*ring; const tw=0.5+0.5*Math.sin(t*6+i*2.1);
    o.sp.position.set(lk.position.x+Math.cos(ang)*rad,
                      lk.position.y+Math.sin(ang)*rad*0.8+0.12*Math.sin(t*1.3+i*1.7), 0.2);
    o.sp.scale.setScalar(0.06+0.05*tw); o.sp.material.opacity=0.5+0.4*tw; }
  for(let i=0;i<rays.length;i++){ const m=rays[i];
    if(!fuse){ m.visible=false; continue; }
    m.visible=true; const ang=i*(6.283/rays.length)+t*0.25;
    const pulse=0.6+0.4*Math.sin(t*3+i*0.9), len=0.42+0.2*pulse, d=len*0.5+0.1;
    m.position.set(lk.position.x+Math.cos(ang)*d, lk.position.y+Math.sin(ang)*d, 0.15);
    m.rotation.z=ang-Math.PI/2; m.scale.set(1,len/0.5,1); m.material.opacity=0.3+0.4*pulse; }

  // ---- heart bursts ----
  if(cls.kind==='fingerHeart'){ const c=toWorld({x:(cls.L.tipIndex.x+cls.R.tipIndex.x)/2, y:(cls.L.tipIndex.y+cls.R.tipIndex.y)/2});
    if(Math.random()<0.5) spawnHearts(c.x, c.y, 2, 0.7, now); }
  if(cls.kind==='bigHeart'){ const c={x:0,y:0};
    spawnHearts(c.x, c.y, 4, 1.3, now); }
  updateHearts(dt);

  // badge
  const label={idle:'대기 중…',summon:'소환',fuse:'✦ 융합 (무지개)',fingerHeart:'♡ 핑거 하트',bigHeart:'♥ 큰 하트',}[cls.kind]||'…';
  badge.textContent=label;

  renderer.render(scene, cam);
  requestAnimationFrame(frame);
}

// ---------- boot ----------
async function start(){
  $('#start').remove();
  if(DEMO){ badge.textContent='데모 (카메라 없음)'; running=true; last=performance.now(); requestAnimationFrame(frame); return; }
  try{
    const stream = await navigator.mediaDevices.getUserMedia({ video:{ width:1280, height:720, facingMode:'user' }, audio:false });
    camEl.srcObject = stream; await camEl.play();
  }catch(e){ showErr('카메라 접근 실패: '+e.message); return; }
  badge.textContent='손 인식 로딩…';
  try{ await initHands(); }catch(e){ showErr('MediaPipe 로드 실패: '+e.message); return; }
  badge.textContent='준비 완료';
  running=true; last=performance.now(); requestAnimationFrame(frame);
}
$('#go').addEventListener('click', start);
if(DEMO) start();   // auto-run scripted showcase, no camera
