import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ── Scene Setup ──────────────────────────────────────────────
const canvas = document.getElementById('canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.5;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x1a2a4a, 0.005);

const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 500);
camera.position.set(45, 30, 55);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.minDistance = 20;
controls.maxDistance = 150;
controls.maxPolarAngle = Math.PI / 2 - 0.05;
controls.target.set(0, 10, 0);

// ── Lighting ─────────────────────────────────────────────────
const ambient = new THREE.AmbientLight(0xaaccff, 0.8);
scene.add(ambient);

const sun = new THREE.DirectionalLight(0xffffee, 2.5);
sun.position.set(50, 80, 40);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 200;
sun.shadow.camera.left = -60;
sun.shadow.camera.right = 60;
sun.shadow.camera.top = 60;
sun.shadow.camera.bottom = -60;
sun.shadow.bias = -0.0005;
scene.add(sun);

const fillLight = new THREE.DirectionalLight(0x88ccff, 1.2);
fillLight.position.set(-40, 30, -30);
scene.add(fillLight);

const rimLight = new THREE.DirectionalLight(0xffffff, 0.8);
rimLight.position.set(0, -20, -60);
scene.add(rimLight);

// Additional top light for brightness
const topLight = new THREE.DirectionalLight(0xffeedd, 1.0);
topLight.position.set(0, 100, 0);
scene.add(topLight);

// ── Ice Material ─────────────────────────────────────────────
function createIceMaterial() {
  return new THREE.MeshPhysicalMaterial({
    color: 0x44ddff,
    metalness: 0.05,
    roughness: 0.08,
    transmission: 0.9,
    thickness: 2.0,
    ior: 1.31,
    clearcoat: 1.0,
    clearcoatRoughness: 0.05,
    envMapIntensity: 1.5,
    side: THREE.DoubleSide,
    flatShading: true,
  });
}

const iceMaterial = createIceMaterial();

// ── Geometry Helpers ─────────────────────────────────────────
function createWallSegment(width, height, depth, segmentsX, segmentsY) {
  const geom = new THREE.BoxGeometry(width, height, depth, segmentsX, segmentsY, 2);
  
  // Displace vertices for organic ice look
  const pos = geom.attributes.position;
  const noiseScale = 0.15;
  
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    
    // Skip inner vertices (keep crisp edges)
    const isEdge = Math.abs(x) === width / 2 || Math.abs(y) === height / 2 || Math.abs(z) === depth / 2;
    if (!isEdge) continue;
    
    const n = Math.sin(x * noiseScale + y * 0.3) * Math.cos(z * noiseScale + y * 0.2);
    const displacement = n * 0.35 * (1 - Math.abs(y) / (height / 2));
    
    if (Math.abs(x) === width / 2) pos.setX(i, x + displacement);
    if (Math.abs(z) === depth / 2) pos.setZ(i, z + displacement);
  }
  
  geom.computeVertexNormals();
  return geom;
}

function createCrystalCluster(radius, count) {
  const geom = new THREE.BufferGeometry();
  const positions = [];
  const scales = [];
  
  for (let i = 0; i < count; i++) {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const r = radius * (0.3 + Math.random() * 0.7);
    
    positions.push(
      r * Math.sin(phi) * Math.cos(theta),
      r * Math.sin(phi) * Math.sin(theta),
      r * Math.cos(phi)
    );
    scales.push(0.5 + Math.random() * 1.2);
  }
  
  geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geom.setAttribute('aScale', new THREE.Float32BufferAttribute(scales, 1));
  return geom;
}

// ── Palace Walls ─────────────────────────────────────────────
const palaceGroup = new THREE.Group();
scene.add(palaceGroup);

let wallSegments = 12;
let wallHeight = 15;
const wallThickness = 1.2;
const palaceRadius = 22;
const wallCount = 8; // Octagon base

function buildWalls() {
  palaceGroup.clear();
  
  for (let i = 0; i < wallCount; i++) {
    const angle = (i / wallCount) * Math.PI * 2;
    const nextAngle = ((i + 1) / wallCount) * Math.PI * 2;
    
    const x1 = Math.cos(angle) * palaceRadius;
    const z1 = Math.sin(angle) * palaceRadius;
    const x2 = Math.cos(nextAngle) * palaceRadius;
    const z2 = Math.sin(nextAngle) * palaceRadius;
    
    const wallWidth = Math.hypot(x2 - x1, z2 - z1);
    const wallAngle = Math.atan2(z2 - z1, x2 - x1);
    
    // Main wall
    const wallGeom = createWallSegment(wallWidth, wallHeight, wallThickness, wallSegments, 8);
    const wall = new THREE.Mesh(wallGeom, iceMaterial);
    wall.position.set(
      (x1 + x2) / 2,
      wallHeight / 2,
      (z1 + z2) / 2
    );
    wall.rotation.y = -wallAngle - Math.PI / 2;
    wall.castShadow = true;
    wall.receiveShadow = true;
    wall.userData = { baseAngle: wallAngle, index: i };
    palaceGroup.add(wall);
    
    // Top crest
    const crestGeom = new THREE.BoxGeometry(wallWidth * 0.9, 1.5, wallThickness * 1.8, 4, 2, 2);
    const crest = new THREE.Mesh(crestGeom, iceMaterial);
    crest.position.set(
      (x1 + x2) / 2,
      wallHeight + 0.75,
      (z1 + z2) / 2
    );
    crest.rotation.y = -wallAngle - Math.PI / 2;
    crest.castShadow = true;
    palaceGroup.add(crest);
    
    // Corner pillar
    const pillarGeom = createWallSegment(1.8, wallHeight + 2, 1.8, 4, 6);
    const pillar = new THREE.Mesh(pillarGeom, iceMaterial);
    pillar.position.set(x1, (wallHeight + 2) / 2, z1);
    pillar.castShadow = true;
    pillar.receiveShadow = true;
    palaceGroup.add(pillar);
    
    // Ice crystals on pillar top
    const crystalGeom = createCrystalCluster(1.2, 8);
    const crystalMat = new THREE.PointsMaterial({
      size: 0.6,
      color: 0x88ffff,
      transparent: true,
      opacity: 1.0,
      sizeAttenuation: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const crystals = new THREE.Points(crystalGeom, crystalMat);
    crystals.position.set(x1, wallHeight + 2.5, z1);
    palaceGroup.add(crystals);
  }
  
  // Central spire
  const spireHeight = wallHeight * 1.8;
  const spireGeom = new THREE.ConeGeometry(3.5, spireHeight, 8, 6, true);
  const spire = new THREE.Mesh(spireGeom, iceMaterial);
  spire.position.set(0, spireHeight / 2, 0);
  spire.castShadow = true;
  palaceGroup.add(spire);
  
  // Spire tip crystals
  const tipCrystalGeom = createCrystalCluster(2, 15);
  const tipCrystals = new THREE.Points(tipCrystalGeom, new THREE.PointsMaterial({
    size: 0.8,
    color: 0xffffff,
    transparent: true,
    opacity: 1,
    sizeAttenuation: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  }));
  tipCrystals.position.set(0, spireHeight + 1, 0);
  palaceGroup.add(tipCrystals);
  
  // Ground plane
  const groundGeom = new THREE.CircleGeometry(palaceRadius * 1.5, 64);
  const groundMat = new THREE.MeshPhysicalMaterial({
    color: 0x1a3a5a,
    metalness: 0.1,
    roughness: 0.5,
    clearcoat: 0.8,
    clearcoatRoughness: 0.2,
  });
  const ground = new THREE.Mesh(groundGeom, groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.05;
  ground.receiveShadow = true;
  palaceGroup.add(ground);
  
  // Inner reflective floor
  const innerFloorGeom = new THREE.CircleGeometry(palaceRadius * 0.9, 32);
  const innerFloorMat = new THREE.MeshPhysicalMaterial({
    color: 0x2a5a8a,
    metalness: 0.3,
    roughness: 0.15,
    transmission: 0.4,
    thickness: 0.5,
    ior: 1.31,
    clearcoat: 1,
    clearcoatRoughness: 0.05,
    side: THREE.DoubleSide,
  });
  const innerFloor = new THREE.Mesh(innerFloorGeom, innerFloorMat);
  innerFloor.rotation.x = -Math.PI / 2;
  innerFloor.position.y = 0.02;
  palaceGroup.add(innerFloor);
}

buildWalls();

// ── Particle Snow ────────────────────────────────────────────
const snowCount = 3000;
const snowGeom = new THREE.BufferGeometry();
const snowPos = new Float32Array(snowCount * 3);
const snowVel = new Float32Array(snowCount * 3);
const snowSize = new Float32Array(snowCount);

for (let i = 0; i < snowCount; i++) {
  snowPos[i * 3] = (Math.random() - 0.5) * 120;
  snowPos[i * 3 + 1] = Math.random() * 60 + 10;
  snowPos[i * 3 + 2] = (Math.random() - 0.5) * 120;
  snowVel[i * 3] = (Math.random() - 0.5) * 0.3;
  snowVel[i * 3 + 1] = -0.15 - Math.random() * 0.25;
  snowVel[i * 3 + 2] = (Math.random() - 0.5) * 0.3;
  snowSize[i] = 0.15 + Math.random() * 0.35;
}

snowGeom.setAttribute('position', new THREE.BufferAttribute(snowPos, 3));
snowGeom.setAttribute('aVelocity', new THREE.BufferAttribute(snowVel, 3));
snowGeom.setAttribute('aSize', new THREE.BufferAttribute(snowSize, 1));

const snowMat = new THREE.PointsMaterial({
  size: 1,
  color: 0xffffff,
  transparent: true,
  opacity: 0.8,
  sizeAttenuation: true,
  depthWrite: false,
  blending: THREE.AdditiveBlending,
});

const snow = new THREE.Points(snowGeom, snowMat);
scene.add(snow);

// ── Aurora Background ────────────────────────────────────────
const auroraGeom = new THREE.SphereGeometry(200, 32, 16);
auroraGeom.scale(1, 0.5, 1);
const auroraMat = new THREE.MeshBasicMaterial({
  color: 0x3a6a9a,
  side: THREE.BackSide,
  transparent: true,
  opacity: 0.25,
});
const aurora = new THREE.Mesh(auroraGeom, auroraMat);
aurora.position.y = 30;
scene.add(aurora);

// ── Animation ────────────────────────────────────────────────
let time = 0;

function animate() {
  requestAnimationFrame(animate);
  time += 0.016;
  
  controls.update();
  
  // Animate snow
  const positions = snowGeom.attributes.position.array;
  const velocities = snowGeom.attributes.aVelocity.array;
  
  for (let i = 0; i < snowCount; i++) {
    positions[i * 3] += velocities[i * 3];
    positions[i * 3 + 1] += velocities[i * 3 + 1];
    positions[i * 3 + 2] += velocities[i * 3 + 2];
    
    // Wrap around
    if (positions[i * 3 + 1] < -5) {
      positions[i * 3 + 1] = 70;
      positions[i * 3] = (Math.random() - 0.5) * 120;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 120;
    }
    
    // Horizontal wrap
    const dist = Math.hypot(positions[i * 3], positions[i * 3 + 2]);
    if (dist > 80) {
      const angle = Math.atan2(positions[i * 3 + 2], positions[i * 3]);
      positions[i * 3] = Math.cos(angle) * 60;
      positions[i * 3 + 2] = Math.sin(angle) * 60;
    }
  }
  snowGeom.attributes.position.needsUpdate = true;
  
  // Subtle palace breathing
  palaceGroup.children.forEach(child => {
    if (child.userData.baseAngle !== undefined) {
      const sway = Math.sin(time * 0.7 + child.userData.index) * 0.002;
      child.rotation.y += sway;
    }
    if (child.isPoints && child.material.blending === THREE.AdditiveBlending) {
      child.rotation.y += 0.0008;
      child.material.opacity = 0.8 + Math.sin(time * 2 + (child.userData.index || 0)) * 0.15;
    }
  });
  
  // Aurora slow rotation
  aurora.rotation.y += 0.0001;
  aurora.rotation.x = Math.sin(time * 0.05) * 0.05;
  
  renderer.render(scene, camera);
}

animate();

// ── Resize & Controls ────────────────────────────────────────
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

const segmentsInput = document.getElementById('segments');
const heightInput = document.getElementById('height');

segmentsInput.addEventListener('input', (e) => {
  wallSegments = parseInt(e.target.value);
  buildWalls();
});

heightInput.addEventListener('input', (e) => {
  wallHeight = parseInt(e.target.value);
  buildWalls();
});

// ── Keyboard: toggle fullscreen ──
document.addEventListener('keydown', (e) => {
  if (e.key === 'f' || e.key === 'F') {
    if (!document.fullscreenElement) {
      canvas.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  }
});

console.log('❄️ Eispalast initialisiert – Die ersten Wände stehen.');