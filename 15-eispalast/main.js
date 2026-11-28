import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const canvas = document.getElementById('canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 2.2;
renderer.setClearColor(0x1a2a4a, 1);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x4488cc, 0.0006);

const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 500);
camera.position.set(80, 45, 100);
camera.lookAt(0, 15, 0);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.minDistance = 30;
controls.maxDistance = 250;
controls.maxPolarAngle = Math.PI / 2 - 0.02;
controls.target.set(0, 15, 0);

const ambient = new THREE.AmbientLight(0xaaccff, 2.0);
scene.add(ambient);

const sun = new THREE.DirectionalLight(0xffeedd, 3.5);
sun.position.set(60, 120, 50);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 300;
sun.shadow.camera.left = -100;
sun.shadow.camera.right = 100;
sun.shadow.camera.top = 100;
sun.shadow.camera.bottom = -100;
sun.shadow.bias = -0.0005;
scene.add(sun);

const fillLight = new THREE.DirectionalLight(0x66aaff, 2.0);
fillLight.position.set(-80, 40, -70);
scene.add(fillLight);

const rimLight = new THREE.DirectionalLight(0xffffff, 2.5);
rimLight.position.set(0, -30, -100);
scene.add(rimLight);

const accentLight = new THREE.PointLight(0x00ffff, 500, 80);
accentLight.position.set(0, 35, 0);
scene.add(accentLight);

function createIceMaterial() {
  return new THREE.MeshPhysicalMaterial({
    color: 0x66ddff,
    metalness: 0.05,
    roughness: 0.08,
    transmission: 0.85,
    thickness: 3.0,
    ior: 1.33,
    clearcoat: 1.0,
    clearcoatRoughness: 0.03,
    envMapIntensity: 3.0,
    side: THREE.DoubleSide,
    flatShading: true,
  });
}

const iceMaterial = createIceMaterial();

function createWallSegment(width, height, depth, segmentsX, segmentsY) {
  const geom = new THREE.BoxGeometry(width, height, depth, segmentsX, segmentsY, 2);
  const pos = geom.attributes.position;
  const noiseScale = 0.18;
  
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    
    const isEdge = Math.abs(x) === width / 2 || Math.abs(y) === height / 2 || Math.abs(z) === depth / 2;
    if (!isEdge) continue;
    
    const n = Math.sin(x * noiseScale + y * 0.4) * Math.cos(z * noiseScale + y * 0.25);
    const displacement = n * 0.4 * (1 - Math.abs(y) / (height / 2));
    
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
    const r = radius * (0.2 + Math.random() * 0.8);
    
    positions.push(
      r * Math.sin(phi) * Math.cos(theta),
      r * Math.sin(phi) * Math.sin(theta),
      r * Math.cos(phi)
    );
    scales.push(0.4 + Math.random() * 1.0);
  }
  
  geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geom.setAttribute('aScale', new THREE.Float32BufferAttribute(scales, 1));
  return geom;
}

const palaceGroup = new THREE.Group();
scene.add(palaceGroup);

let wallSegments = 12;
let wallHeight = 15;
let crystalDensity = 30;
const wallThickness = 1.2;
const palaceRadius = 20;
const wallCount = 8;

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
    
    const wallGeom = createWallSegment(wallWidth, wallHeight, wallThickness, wallSegments, 8);
    const wall = new THREE.Mesh(wallGeom, iceMaterial);
    wall.position.set((x1 + x2) / 2, wallHeight / 2, (z1 + z2) / 2);
    wall.rotation.y = -wallAngle - Math.PI / 2;
    wall.castShadow = true;
    wall.receiveShadow = true;
    wall.userData = { baseAngle: wallAngle, index: i };
    palaceGroup.add(wall);
    
    const crestGeom = new THREE.BoxGeometry(wallWidth * 0.9, 1.4, wallThickness * 1.6, 4, 2, 2);
    const crest = new THREE.Mesh(crestGeom, iceMaterial);
    crest.position.set((x1 + x2) / 2, wallHeight + 0.7, (z1 + z2) / 2);
    crest.rotation.y = -wallAngle - Math.PI / 2;
    crest.castShadow = true;
    palaceGroup.add(crest);
    
    const pillarGeom = createWallSegment(1.6, wallHeight + 2, 1.6, 4, 6);
    const pillar = new THREE.Mesh(pillarGeom, iceMaterial);
    pillar.position.set(x1, (wallHeight + 2) / 2, z1);
    pillar.castShadow = true;
    pillar.receiveShadow = true;
    palaceGroup.add(pillar);
    
    const crystalGeom = createCrystalCluster(1.0, Math.floor(crystalDensity / 4));
    const crystalMat = new THREE.PointsMaterial({
      size: 0.6,
      color: 0xffffff,
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
  
  const spireHeight = wallHeight * 1.9;
  const spireGeom = new THREE.ConeGeometry(3.0, spireHeight, 8, 6, true);
  const spire = new THREE.Mesh(spireGeom, iceMaterial);
  spire.position.set(0, spireHeight / 2, 0);
  spire.castShadow = true;
  palaceGroup.add(spire);
  
  const tipCrystalGeom = createCrystalCluster(1.8, Math.floor(crystalDensity / 2));
  const tipCrystals = new THREE.Points(tipCrystalGeom, new THREE.PointsMaterial({
    size: 0.8,
    color: 0xffffff,
    transparent: true,
    opacity: 1,
    sizeAttenuation: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  }));
  tipCrystals.position.set(0, spireHeight + 0.8, 0);
  palaceGroup.add(tipCrystals);
  
  const groundGeom = new THREE.CircleGeometry(palaceRadius * 1.8, 64);
  const groundMat = new THREE.MeshPhysicalMaterial({
    color: 0x1a3a6a,
    metalness: 0.4,
    roughness: 0.25,
    clearcoat: 1.0,
    clearcoatRoughness: 0.08,
  });
  const ground = new THREE.Mesh(groundGeom, groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.05;
  ground.receiveShadow = true;
  palaceGroup.add(ground);
  
  const innerFloorGeom = new THREE.CircleGeometry(palaceRadius * 0.85, 32);
  const innerFloorMat = new THREE.MeshPhysicalMaterial({
    color: 0x3388dd,
    metalness: 0.6,
    roughness: 0.05,
    transmission: 0.5,
    thickness: 0.8,
    ior: 1.33,
    clearcoat: 1,
    clearcoatRoughness: 0.01,
    side: THREE.DoubleSide,
  });
  const innerFloor = new THREE.Mesh(innerFloorGeom, innerFloorMat);
  innerFloor.rotation.x = -Math.PI / 2;
  innerFloor.position.y = 0.02;
  palaceGroup.add(innerFloor);
}

buildWalls();

const snowCount = 3500;
const snowGeom = new THREE.BufferGeometry();
const snowPos = new Float32Array(snowCount * 3);
const snowVel = new Float32Array(snowCount * 3);
const snowSize = new Float32Array(snowCount);

for (let i = 0; i < snowCount; i++) {
  snowPos[i * 3] = (Math.random() - 0.5) * 130;
  snowPos[i * 3 + 1] = Math.random() * 70 + 10;
  snowPos[i * 3 + 2] = (Math.random() - 0.5) * 130;
  snowVel[i * 3] = (Math.random() - 0.5) * 0.25;
  snowVel[i * 3 + 1] = -0.12 - Math.random() * 0.2;
  snowVel[i * 3 + 2] = (Math.random() - 0.5) * 0.25;
  snowSize[i] = 0.12 + Math.random() * 0.3;
}

snowGeom.setAttribute('position', new THREE.BufferAttribute(snowPos, 3));
snowGeom.setAttribute('aVelocity', new THREE.BufferAttribute(snowVel, 3));
snowGeom.setAttribute('aSize', new THREE.BufferAttribute(snowSize, 1));

const snowMat = new THREE.PointsMaterial({
  size: 1.5,
  color: 0xffffff,
  transparent: true,
  opacity: 0.9,
  sizeAttenuation: true,
  depthWrite: false,
  blending: THREE.AdditiveBlending,
});

const snow = new THREE.Points(snowGeom, snowMat);
scene.add(snow);

const auroraGeom = new THREE.SphereGeometry(280, 32, 16);
auroraGeom.scale(1, 0.4, 1);
const auroraMat = new THREE.MeshBasicMaterial({
  color: 0x44aaff,
  side: THREE.BackSide,
  transparent: true,
  opacity: 0.25,
});
const aurora = new THREE.Mesh(auroraGeom, auroraMat);
aurora.position.y = 50;
scene.add(aurora);

let time = 0;

function animate() {
  requestAnimationFrame(animate);
  time += 0.016;
  
  controls.update();
  
  const positions = snowGeom.attributes.position.array;
  const velocities = snowGeom.attributes.aVelocity.array;
  
  for (let i = 0; i < snowCount; i++) {
    positions[i * 3] += velocities[i * 3];
    positions[i * 3 + 1] += velocities[i * 3 + 1];
    positions[i * 3 + 2] += velocities[i * 3 + 2];
    
    if (positions[i * 3 + 1] < -5) {
      positions[i * 3 + 1] = 75;
      positions[i * 3] = (Math.random() - 0.5) * 130;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 130;
    }
    
    const dist = Math.hypot(positions[i * 3], positions[i * 3 + 2]);
    if (dist > 85) {
      const angle = Math.atan2(positions[i * 3 + 2], positions[i * 3]);
      positions[i * 3] = Math.cos(angle) * 65;
      positions[i * 3 + 2] = Math.sin(angle) * 65;
    }
  }
  snowGeom.attributes.position.needsUpdate = true;
  
  palaceGroup.children.forEach(child => {
    if (child.userData.baseAngle !== undefined) {
      const sway = Math.sin(time * 0.6 + child.userData.index) * 0.0015;
      child.rotation.y += sway;
    }
    if (child.isPoints && child.material.blending === THREE.AdditiveBlending) {
      child.rotation.y += 0.0006;
      child.material.opacity = 0.9 + Math.sin(time * 1.8 + (child.userData.index || 0)) * 0.1;
    }
  });
  
  aurora.rotation.y += 0.00015;
  aurora.rotation.x = Math.sin(time * 0.04) * 0.04;
  
  accentLight.intensity = 400 + Math.sin(time * 2) * 100;
  
  renderer.render(scene, camera);
}

animate();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

const segmentsInput = document.getElementById('segments');
const heightInput = document.getElementById('height');
const crystalsInput = document.getElementById('crystals');
const exposureInput = document.getElementById('exposure');

segmentsInput.addEventListener('input', (e) => {
  wallSegments = parseInt(e.target.value);
  buildWalls();
});

heightInput.addEventListener('input', (e) => {
  wallHeight = parseInt(e.target.value);
  buildWalls();
});

crystalsInput.addEventListener('input', (e) => {
  crystalDensity = parseInt(e.target.value);
  buildWalls();
});

exposureInput.addEventListener('input', (e) => {
  renderer.toneMappingExposure = parseFloat(e.target.value);
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'f' || e.key === 'F') {
    if (!document.fullscreenElement) {
      canvas.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  }
});

console.log('❄️ Eispalast Teil 4 initialisiert – Sichtbarkeit & Farben optimiert.');