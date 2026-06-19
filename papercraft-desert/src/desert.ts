/**
 * Procedural "papercraft" desert.
 *
 * Everything here is plain Three.js (re-exported by @iwsdk/core): low-poly
 * geometry + flat-shaded matte materials, so each object looks like folded
 * cardstock. Builders return detached `Object3D`s with their world position
 * already set; `src/index.ts` turns them into IWSDK entities and attaches
 * behaviour/interaction components. Animation parameters ride along in each
 * object's `userData` so the ECS systems can read them.
 */
import {
  BoxGeometry,
  CapsuleGeometry,
  CircleGeometry,
  Color,
  ConeGeometry,
  DodecahedronGeometry,
  DoubleSide,
  EdgesGeometry,
  Group,
  IcosahedronGeometry,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  Shape,
  ShapeGeometry,
} from '@iwsdk/core';

// ---- palette (warm, slightly desaturated "paper" tones) -------------------
const PALETTE = {
  sand: 0xe6c685,
  duneA: 0xead3a0,
  duneB: 0xd9b879,
  cactus: 0x6fa86a,
  cactusDark: 0x5c8f57,
  flower: 0xe7708e,
  rock: 0xb6a085,
  rockDark: 0x9c876f,
  sandstone: 0xd9b98a,
  sandstoneDark: 0xc6a472,
  sunCore: 0xffd86b,
  sunRays: 0xffae4d,
  brush: 0xc9a063,
  bird: 0x4a3f37,
  water: 0x49a6c9,
  trunk: 0x9c6b43,
  palm: 0x5fa05a,
};

// ---- tiny seeded RNG so the layout is reproducible ------------------------
function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = rng(0xde5e27);
const between = (lo: number, hi: number) => lo + (hi - lo) * rand();

function paper(color: number, jitter = 0): MeshStandardMaterial {
  const c = new Color(color);
  if (jitter) c.offsetHSL(0, 0, (rand() - 0.5) * jitter);
  return new MeshStandardMaterial({ color: c, flatShading: true, roughness: 0.96, metalness: 0 });
}

/** Subtle dark "fold" seams along a geometry's hard edges. */
function seams(geometry: any, opacity = 0.16): LineSegments {
  const mat = new LineBasicMaterial({ color: 0x3a2c1f, transparent: true, opacity });
  return new LineSegments(new EdgesGeometry(geometry, 1), mat);
}

// ---- builders -------------------------------------------------------------
export function makeGround(radius = 42): Mesh {
  const geo = new CircleGeometry(radius, 48);
  geo.rotateX(-Math.PI / 2);
  const mesh = new Mesh(geo, new MeshStandardMaterial({
    color: new Color(PALETTE.sand), roughness: 1, metalness: 0, side: DoubleSide,
  }));
  mesh.position.y = 0;
  return mesh;
}

function makeDune(r: number): Mesh {
  const geo = new IcosahedronGeometry(r, 1);
  geo.scale(1, 0.42, 1);
  const m = new Mesh(geo, paper(rand() > 0.5 ? PALETTE.duneA : PALETTE.duneB, 0.06));
  m.position.y = -r * 0.28; // half-buried so only a rolling crest shows
  m.rotation.y = rand() * Math.PI;
  return m;
}

function makeSaguaro(height = 2.4): Group {
  const g = new Group();
  const mat = paper(PALETTE.cactus, 0.05);
  const r = 0.26;
  const trunk = new Mesh(new CapsuleGeometry(r, height - 2 * r, 4, 7), mat);
  trunk.position.y = height / 2;
  g.add(trunk);

  const addArm = (side: number, atY: number, armH: number) => {
    const arm = new Group();
    const elbowX = side * 0.42;
    const horiz = new Mesh(new CapsuleGeometry(0.16, 0.34, 3, 6), mat);
    horiz.rotation.z = Math.PI / 2;
    horiz.position.set(side * 0.26, atY, 0);
    const vert = new Mesh(new CapsuleGeometry(0.18, armH, 3, 6), mat);
    vert.position.set(elbowX, atY + armH / 2, 0);
    arm.add(horiz, vert);
    g.add(arm);
    // a little bloom on the arm tip
    const bloom = new Mesh(new IcosahedronGeometry(0.09, 0), paper(PALETTE.flower));
    bloom.position.set(elbowX, atY + armH + 0.12, 0);
    g.add(bloom);
  };
  addArm(1, height * 0.45, between(0.5, 0.8));
  if (rand() > 0.35) addArm(-1, height * 0.6, between(0.4, 0.7));
  return g;
}

function makeBarrelCactus(): Group {
  const g = new Group();
  const body = new Mesh(new IcosahedronGeometry(0.36, 1), paper(PALETTE.cactus, 0.05));
  body.scale.set(1, 0.82, 1);
  body.position.y = 0.3;
  g.add(body);
  const flower = new Mesh(new ConeGeometry(0.09, 0.14, 6), paper(PALETTE.flower));
  flower.position.y = 0.62;
  g.add(flower);
  return g;
}

function makeRock(r = 0.5): Mesh {
  const geo = new DodecahedronGeometry(r, 0);
  geo.scale(between(0.8, 1.3), between(0.5, 0.9), between(0.8, 1.3));
  const m = new Mesh(geo, paper(rand() > 0.5 ? PALETTE.rock : PALETTE.rockDark, 0.08));
  m.rotation.set(rand(), rand() * Math.PI, rand());
  m.position.y = r * 0.32;
  return m;
}

function makePyramid(size = 3): Group {
  const g = new Group();
  const h = size * 1.15;
  const geo = new ConeGeometry(size, h, 4);
  geo.rotateY(Math.PI / 4); // a flat face toward the viewer
  const cone = new Mesh(geo, paper(rand() > 0.5 ? PALETTE.sandstone : PALETTE.sandstoneDark, 0.04));
  cone.position.y = h / 2;
  g.add(cone, withSeams(geo, cone));
  return g;
}

function withSeams(geometry: any, at: Object3D): LineSegments {
  const s = seams(geometry);
  s.position.copy(at.position);
  return s;
}

export function makeSun(): Group {
  const g = new Group();
  const star = new Shape();
  const points = 14;
  for (let i = 0; i < points * 2; i++) {
    const rr = i % 2 === 0 ? 2.6 : 1.5;
    const a = (i / (points * 2)) * Math.PI * 2;
    const x = Math.cos(a) * rr;
    const y = Math.sin(a) * rr;
    i === 0 ? star.moveTo(x, y) : star.lineTo(x, y);
  }
  star.closePath();
  const rays = new Mesh(new ShapeGeometry(star), new MeshBasicMaterial({
    color: new Color(PALETTE.sunRays), transparent: true, opacity: 0.5, side: DoubleSide,
  }));
  rays.position.z = -0.05;
  const disc = new Mesh(new CircleGeometry(1.35, 32), new MeshBasicMaterial({
    color: new Color(PALETTE.sunCore), side: DoubleSide,
  }));
  g.add(rays, disc);
  g.userData.baseScale = 1;
  return g;
}

function makeTumbleweed(r = 0.45): Group {
  const g = new Group();
  const geo = new IcosahedronGeometry(r, 1);
  const ball = new Mesh(geo, paper(PALETTE.brush, 0.06));
  const twigs = new LineSegments(new EdgesGeometry(geo, 1), new LineBasicMaterial({
    color: 0x7a5a32, transparent: true, opacity: 0.5,
  }));
  g.add(ball, twigs);
  return g;
}

function makeBird(): Group {
  const g = new Group();
  const mat = paper(PALETTE.bird);
  const wingGeo = new BoxGeometry(0.5, 0.02, 0.16);
  const left = new Mesh(wingGeo, mat);
  left.position.x = 0.25;
  left.rotation.z = 0.3;
  const right = new Mesh(wingGeo, mat);
  right.position.x = -0.25;
  right.rotation.z = -0.3;
  g.add(left, right);
  g.userData.wings = [left, right];
  return g;
}

function makePalm(height = 2.6): Group {
  const g = new Group();
  const trunk = new Mesh(new CapsuleGeometry(0.12, height, 3, 6), paper(PALETTE.trunk));
  trunk.position.y = height / 2;
  trunk.rotation.z = between(-0.12, 0.12);
  g.add(trunk);
  const frondMat = paper(PALETTE.palm, 0.05);
  for (let i = 0; i < 6; i++) {
    const frond = new Mesh(new BoxGeometry(1.1, 0.03, 0.16), frondMat);
    const a = (i / 6) * Math.PI * 2;
    frond.position.set(Math.cos(a) * 0.5, height + 0.05, Math.sin(a) * 0.5);
    frond.rotation.y = -a;
    frond.rotation.z = 0.35; // droop outward
    g.add(frond);
  }
  return g;
}

function makeOasis(): Group {
  const g = new Group();
  const water = new Mesh(new CircleGeometry(2.0, 28), new MeshStandardMaterial({
    color: new Color(PALETTE.water), roughness: 0.3, metalness: 0.1, side: DoubleSide,
  }));
  water.rotation.x = -Math.PI / 2;
  water.position.y = 0.02;
  g.add(water);
  const p1 = makePalm(2.7); p1.position.set(-1.6, 0, -1.2);
  const p2 = makePalm(2.2); p2.position.set(1.4, 0, -1.5);
  g.add(p1, p2);
  return g;
}

// ---- the assembled scene --------------------------------------------------
export interface DesertScene {
  ground: Mesh;
  statics: Group;
  sun: Group;
  swayCacti: Group[];
  tumbleweeds: Group[];
  birds: Group[];
  grabbables: Object3D[];
}

function place(o: Object3D, x: number, z: number, rotY = rand() * Math.PI * 2): Object3D {
  o.position.x = x;
  o.position.z = z;
  o.rotation.y += rotY;
  return o;
}

export function buildDesertScene(): DesertScene {
  const statics = new Group();
  const swayCacti: Group[] = [];
  const tumbleweeds: Group[] = [];
  const birds: Group[] = [];
  const grabbables: Object3D[] = [];

  // rolling dunes all around
  for (let i = 0; i < 14; i++) {
    const ang = rand() * Math.PI * 2;
    const dist = between(6, 34);
    statics.add(place(makeDune(between(2.5, 6)), Math.cos(ang) * dist, Math.sin(ang) * dist));
  }

  // pyramids on the horizon
  [[-9, -20, 4.2], [8, -24, 3.4], [1, -30, 2.6], [-22, -10, 3.0]].forEach(([x, z, s]) => {
    statics.add(place(makePyramid(s), x, z, between(-0.3, 0.3)));
  });

  // saguaro cacti — most sway in the breeze
  for (let i = 0; i < 7; i++) {
    const ang = rand() * Math.PI * 2;
    const dist = between(3.5, 14);
    const cactus = place(makeSaguaro(between(1.8, 3.2)), Math.cos(ang) * dist, Math.sin(ang) * dist);
    if (rand() > 0.25) {
      cactus.userData = { phase: rand() * Math.PI * 2, amp: between(0.015, 0.05), speed: between(0.6, 1.1) };
      swayCacti.push(cactus as Group);
    } else {
      statics.add(cactus);
    }
  }

  // rocks — a few are grabbable "souvenirs"
  for (let i = 0; i < 12; i++) {
    const ang = rand() * Math.PI * 2;
    const dist = between(2.5, 20);
    const rock = place(makeRock(between(0.3, 0.8)), Math.cos(ang) * dist, Math.sin(ang) * dist);
    if (dist < 6 && grabbables.length < 3) grabbables.push(rock);
    else statics.add(rock);
  }

  // barrel cacti near the player — grabbable
  [[1.6, -2.6], [-2.0, -2.2], [2.4, 1.8]].forEach(([x, z]) => {
    grabbables.push(place(makeBarrelCactus(), x, z));
  });

  // an oasis off to one side
  statics.add(place(makeOasis(), 9, -6, 0));

  // ground-level scatter is done; now the sky + critters
  const sun = makeSun();
  sun.position.set(-9, 10.5, -22);

  for (let i = 0; i < 3; i++) {
    const tw = makeTumbleweed(between(0.35, 0.55));
    const z = between(-9, 6);
    tw.position.set(between(-12, -6), tw.userData.baseY ?? 0.45, z);
    tw.userData = {
      speed: between(1.2, 2.4),
      xMin: -14,
      xMax: 14,
      baseY: 0.45,
    };
    tumbleweeds.push(tw);
  }

  for (let i = 0; i < 4; i++) {
    const bird = makeBird();
    bird.userData = {
      ...bird.userData,
      cx: between(-4, 4),
      cz: between(-12, -4),
      radius: between(4, 8),
      y: between(7, 10),
      speed: between(0.2, 0.4),
      phase: rand() * Math.PI * 2,
    };
    birds.push(bird);
  }

  return { ground: makeGround(), statics, sun, swayCacti, tumbleweeds, birds, grabbables };
}
