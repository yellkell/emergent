/**
 * Procedural "papercraft" desert — detailed edition.
 *
 * Plain Three.js (re-exported by @iwsdk/core): low-poly geometry + flat-shaded
 * matte materials, faceted like folded cardstock, with dark "fold" seams on the
 * hero shapes and gentle per-face colour variation. Builders return detached
 * Object3Ds with their position set; `src/index.ts` turns them into IWSDK
 * entities and attaches behaviour/interaction. Animation params ride in
 * `userData`.
 */
import {
  BackSide,
  BoxGeometry,
  BufferAttribute,
  CapsuleGeometry,
  CircleGeometry,
  Color,
  ConeGeometry,
  CylinderGeometry,
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
  SphereGeometry,
  TorusGeometry,
} from '@iwsdk/core';

// ---- palette (warm, slightly desaturated "paper" tones) -------------------
const PALETTE = {
  sand: 0xe7c98a,
  sandWarm: 0xdcb878,
  sandPale: 0xeed7a6,
  // banded sandstone for the mesas (Monument-Valley reds)
  mesa: [0xb9603b, 0xc4744a, 0xd98a5a, 0xc26240, 0xa84e34, 0xe0a96d],
  mesaTalus: 0x8f4a33,
  cactus: 0x6fa86a,
  cactusDark: 0x5c8f57,
  pear: 0x79b06a,
  agave: 0x7bae9b,
  agaveDark: 0x639685,
  shrub: 0x9aae86,
  shrubDark: 0x86996f,
  grass: 0xd6c074,
  flower: [0xe7708e, 0xe0584f, 0xf2c14e, 0xf3ede0, 0xc85a9c, 0xef9a52],
  rock: 0xb6a085,
  rockDark: 0x9c876f,
  rockRed: 0xb9745a,
  cloud: 0xfbf6ec,
  cloudShade: 0xe7d8c1,
  sunCore: 0xffd86b,
  sunRays: 0xffae4d,
  brush: 0x9c7440,
  brushPale: 0xc7a064,
  bird: 0x4a3f37,
  water: 0x49a6c9,
  trunk: 0x9c6b43,
  palm: 0x5fa05a,
  skyTop: 0xa9c6dc,
  skyHorizon: 0xf4d2a4,
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
const rand = rng(0x10de57);
const between = (lo: number, hi: number) => lo + (hi - lo) * rand();
const pick = <T>(arr: T[]): T => arr[Math.floor(rand() * arr.length)];

function paper(color: number, jitter = 0.05): MeshStandardMaterial {
  const c = new Color(color);
  if (jitter) c.offsetHSL(0, (rand() - 0.5) * 0.02, (rand() - 0.5) * jitter);
  return new MeshStandardMaterial({ color: c, flatShading: true, roughness: 0.97, metalness: 0 });
}
function unlit(color: number, opacity = 1): MeshBasicMaterial {
  return new MeshBasicMaterial({ color: new Color(color), transparent: opacity < 1, opacity, side: DoubleSide });
}
/** Subtle dark "fold" seams along a geometry's hard edges. */
function seams(geometry: any, opacity = 0.14): LineSegments {
  return new LineSegments(new EdgesGeometry(geometry, 18),
    new LineBasicMaterial({ color: 0x3a2c1f, transparent: true, opacity }));
}
function meshSeam(geometry: any, material: MeshStandardMaterial, seamOpacity = 0.14): Group {
  const g = new Group();
  g.add(new Mesh(geometry, material), seams(geometry, seamOpacity));
  return g;
}

// ---- ground & sky ---------------------------------------------------------
export function makeGround(radius = 46): Mesh {
  const geo = new CircleGeometry(radius, 56);
  geo.rotateX(-Math.PI / 2);
  return new Mesh(geo, new MeshStandardMaterial({
    color: new Color(PALETTE.sand), roughness: 1, metalness: 0, side: DoubleSide,
  }));
}

export function makeSkyDome(): Mesh {
  const geo = new SphereGeometry(120, 24, 16);
  const top = new Color(PALETTE.skyTop);
  const hor = new Color(PALETTE.skyHorizon);
  const pos = geo.attributes.position;
  const colors = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const y = pos.getY(i) / 120;            // -1..1
    const t = Math.pow(Math.max(0, y), 0.6); // bias the warm band toward the horizon
    const c = hor.clone().lerp(top, t);
    colors.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new BufferAttribute(colors, 3));
  return new Mesh(geo, new MeshBasicMaterial({ vertexColors: true, side: BackSide, fog: false }));
}

// ---- terrain features -----------------------------------------------------
function makeDune(r: number): Group {
  const g = new Group();
  const base = new Mesh(new IcosahedronGeometry(r, 1), paper(PALETTE.sandWarm, 0.05));
  base.geometry.scale(1, 0.4, 1.15);
  base.position.y = -r * 0.26;
  base.rotation.y = rand() * Math.PI;
  const crest = new Mesh(new IcosahedronGeometry(r * 0.62, 1), paper(PALETTE.sandPale, 0.04));
  crest.geometry.scale(1.1, 0.4, 0.8);
  crest.position.set(r * 0.18, r * 0.05, 0);
  crest.rotation.y = rand() * Math.PI;
  g.add(base, crest);
  return g;
}

/** Layered banded sandstone mesa/butte — the new horizon landmark. */
function makeMesa(height: number, rBase: number): Group {
  const g = new Group();
  const layers = 5 + Math.floor(rand() * 3);
  let y = 0;
  for (let i = 0; i < layers; i++) {
    const t = i / layers;
    const lh = (height / layers) * between(0.85, 1.15);
    const r = rBase * (1 - t * 0.42) * between(0.96, 1.04);
    const sides = 7;
    const geo = new CylinderGeometry(r, r * 1.03, lh, sides);
    geo.rotateY(rand() * 0.4);
    const mat = paper(PALETTE.mesa[i % PALETTE.mesa.length], 0.04);
    const layer = meshSeam(geo, mat, 0.18);
    layer.position.y = y + lh / 2;
    g.add(layer);
    y += lh;
  }
  // talus skirt
  const skirt = new Mesh(new ConeGeometry(rBase * 1.25, height * 0.28, 7), paper(PALETTE.mesaTalus, 0.03));
  skirt.position.y = height * 0.14;
  g.add(skirt);
  return g;
}

// ---- flora ----------------------------------------------------------------
function blossoms(parent: Group, points: [number, number, number][]) {
  for (const [x, y, z] of points) {
    const b = new Mesh(new IcosahedronGeometry(between(0.06, 0.09), 0), paper(pick([0xf3ede0, 0xf2c14e, 0xe7708e])));
    b.position.set(x, y, z);
    parent.add(b);
  }
}

function makeSaguaro(height = 2.6): Group {
  const g = new Group();
  const mat = paper(PALETTE.cactus, 0.04);
  const r = 0.27;
  const trunk = meshSeam(new CapsuleGeometry(r, height - 2 * r, 4, 9), mat, 0.1);
  trunk.position.y = height / 2;
  g.add(trunk);
  const tops: [number, number, number][] = [[0, height + 0.05, 0]];
  const addArm = (side: number, atY: number, armH: number) => {
    const elbowX = side * 0.44;
    const horiz = new Mesh(new CapsuleGeometry(0.15, 0.32, 3, 7), mat);
    horiz.rotation.z = Math.PI / 2;
    horiz.position.set(side * 0.27, atY, 0);
    const vert = new Mesh(new CapsuleGeometry(0.17, armH, 3, 7), mat);
    vert.position.set(elbowX, atY + armH / 2, 0);
    g.add(horiz, vert);
    tops.push([elbowX, atY + armH + 0.1, 0]);
  };
  addArm(1, height * 0.46, between(0.55, 0.85));
  if (rand() > 0.3) addArm(-1, height * 0.62, between(0.45, 0.75));
  blossoms(g, tops.filter(() => rand() > 0.4));
  return g;
}

function makePricklyPear(): Group {
  const g = new Group();
  const mat = paper(PALETTE.pear, 0.05);
  const pad = (x: number, y: number, z: number, s: number, tilt: number, yaw: number) => {
    const m = new Mesh(new IcosahedronGeometry(s, 1), mat);
    m.geometry.scale(1, 1.25, 0.2);
    m.position.set(x, y, z);
    m.rotation.set(tilt, yaw, between(-0.2, 0.2));
    g.add(m);
    // a couple of red fruits on the upper rim
    if (rand() > 0.5) {
      const fruit = new Mesh(new IcosahedronGeometry(0.05, 0), paper(0xc0392b));
      fruit.position.set(x + Math.sin(yaw) * s * 0.2, y + s * 1.1, z + Math.cos(yaw) * s * 0.2);
      g.add(fruit);
    }
    return [x, y, s] as const;
  };
  const base = pad(0, 0.28, 0, between(0.26, 0.34), 0, between(0, Math.PI));
  const n = 2 + Math.floor(rand() * 3);
  for (let i = 0; i < n; i++) {
    const yaw = rand() * Math.PI * 2;
    pad(base[0] + Math.sin(yaw) * 0.18, base[1] + between(0.3, 0.5), Math.cos(yaw) * 0.18,
      between(0.18, 0.28), between(0.2, 0.6), yaw);
  }
  return g;
}

function makeAgave(): Group {
  const g = new Group();
  const n = 11 + Math.floor(rand() * 5);
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + rand() * 0.2;
    const len = between(0.7, 1.1);
    const blade = new Mesh(new ConeGeometry(0.07, len, 3), paper(rand() > 0.5 ? PALETTE.agave : PALETTE.agaveDark, 0.05));
    const out = 0.12;
    blade.position.set(Math.cos(a) * out, len / 2 * 0.8, Math.sin(a) * out);
    blade.rotation.z = -Math.cos(a) * between(0.7, 1.0);
    blade.rotation.x = Math.sin(a) * between(0.7, 1.0);
    g.add(blade);
  }
  if (rand() > 0.6) { // occasional flower stalk
    const stalk = new Mesh(new CylinderGeometry(0.03, 0.04, between(1.6, 2.4), 5), paper(PALETTE.brush));
    stalk.position.y = stalk.geometry.parameters.height / 2;
    g.add(stalk);
  }
  return g;
}

function makeBarrelCactus(): Group {
  const g = new Group();
  const body = meshSeam(new IcosahedronGeometry(0.36, 1), paper(PALETTE.cactus, 0.04), 0.1);
  (body.children[0] as Mesh).geometry.scale(1, 0.85, 1);
  body.position.y = 0.3;
  g.add(body);
  const k = 5 + Math.floor(rand() * 3);
  for (let i = 0; i < k; i++) {
    const a = (i / k) * Math.PI * 2;
    const f = new Mesh(new ConeGeometry(0.07, 0.12, 6), paper(pick(PALETTE.flower)));
    f.position.set(Math.cos(a) * 0.16, 0.62, Math.sin(a) * 0.16);
    g.add(f);
  }
  return g;
}

function makeSagebrush(): Group {
  const g = new Group();
  const n = 5 + Math.floor(rand() * 4);
  for (let i = 0; i < n; i++) {
    const puff = new Mesh(new IcosahedronGeometry(between(0.12, 0.22), 0), paper(rand() > 0.5 ? PALETTE.shrub : PALETTE.shrubDark, 0.06));
    puff.position.set(between(-0.25, 0.25), between(0.12, 0.4), between(-0.25, 0.25));
    g.add(puff);
  }
  return g;
}

function makeGrassTuft(): Group {
  const g = new Group();
  const n = 6 + Math.floor(rand() * 5);
  for (let i = 0; i < n; i++) {
    const blade = new Mesh(new ConeGeometry(0.018, between(0.3, 0.55), 3), paper(PALETTE.grass, 0.07));
    const a = rand() * Math.PI * 2;
    blade.position.set(Math.cos(a) * 0.06, blade.geometry.parameters.height / 2, Math.sin(a) * 0.06);
    blade.rotation.z = Math.cos(a) * 0.5;
    blade.rotation.x = Math.sin(a) * 0.5;
    g.add(blade);
  }
  return g;
}

function makeFlower(): Group {
  const g = new Group();
  const h = between(0.18, 0.34);
  const stem = new Mesh(new CylinderGeometry(0.012, 0.012, h, 4), paper(0x6f9a55));
  stem.position.y = h / 2;
  const head = new Mesh(new IcosahedronGeometry(between(0.05, 0.08), 0), paper(pick(PALETTE.flower)));
  head.position.y = h;
  g.add(stem, head);
  return g;
}

// ---- rocks ----------------------------------------------------------------
function makeRock(r = 0.5): Mesh {
  const geo = new DodecahedronGeometry(r, 0);
  geo.scale(between(0.8, 1.3), between(0.5, 0.9), between(0.8, 1.3));
  const m = new Mesh(geo, paper(pick([PALETTE.rock, PALETTE.rockDark, PALETTE.rockRed]), 0.08));
  m.rotation.set(rand(), rand() * Math.PI, rand());
  m.position.y = r * 0.3;
  return m;
}

function makeRockStack(): Group {
  const g = new Group();
  let y = 0;
  let r = between(0.45, 0.6);
  for (let i = 0; i < 3; i++) {
    const geo = new DodecahedronGeometry(r, 0);
    geo.scale(between(0.9, 1.2), between(0.6, 0.85), between(0.9, 1.2));
    const rock = meshSeam(geo, paper(rand() > 0.5 ? PALETTE.rockRed : PALETTE.rockDark, 0.05), 0.12);
    rock.position.set(between(-0.05, 0.05), y + r * 0.4, between(-0.05, 0.05));
    g.add(rock);
    y += r * 0.75;
    r *= between(0.6, 0.78);
  }
  return g;
}

// ---- sky critters & set dressing -----------------------------------------
export function makeSun(): Group {
  const g = new Group();
  const pts = 16;
  const star = new Group();
  for (let i = 0; i < pts; i++) {
    const a = (i / pts) * Math.PI * 2;
    const ray = new Mesh(new ConeGeometry(0.5, 1.5, 3), unlit(PALETTE.sunRays, 0.55));
    ray.position.set(Math.cos(a) * 2.0, Math.sin(a) * 2.0, -0.05);
    ray.rotation.z = a - Math.PI / 2;
    star.add(ray);
  }
  const disc = new Mesh(new CircleGeometry(1.45, 36), unlit(PALETTE.sunCore));
  g.add(star, disc);
  g.userData.baseScale = 1;
  return g;
}

function makeCloud(scale = 1): Group {
  const g = new Group();
  const n = 5 + Math.floor(rand() * 4);
  for (let i = 0; i < n; i++) {
    const r = between(0.8, 1.5) * scale;
    const puff = new Mesh(new IcosahedronGeometry(r, 1), paper(rand() > 0.3 ? PALETTE.cloud : PALETTE.cloudShade, 0.02));
    puff.geometry.scale(1.2, 0.62, 1);
    puff.position.set(between(-2.2, 2.2) * scale, between(-0.15, 0.25) * scale, between(-0.5, 0.5) * scale);
    g.add(puff);
  }
  return g;
}

/** Tangled dry brush: crisscrossing faceted rings + a few stray twigs. */
function makeTumbleweed(r = 0.5): Group {
  const g = new Group();
  const rings = 7 + Math.floor(rand() * 3);
  for (let i = 0; i < rings; i++) {
    const ring = new Mesh(
      new TorusGeometry(r * between(0.7, 1.0), 0.022, 3, 9),
      paper(rand() > 0.5 ? PALETTE.brush : PALETTE.brushPale, 0.05),
    );
    ring.rotation.set(rand() * Math.PI, rand() * Math.PI, rand() * Math.PI);
    g.add(ring);
  }
  for (let i = 0; i < 5; i++) { // stray twigs poking out
    const twig = new Mesh(new ConeGeometry(0.02, between(0.3, 0.5), 3), paper(PALETTE.brush));
    const a = rand() * Math.PI * 2, b = rand() * Math.PI;
    twig.position.set(Math.sin(b) * Math.cos(a) * r, Math.cos(b) * r, Math.sin(b) * Math.sin(a) * r);
    twig.rotation.set(rand() * Math.PI, rand() * Math.PI, rand() * Math.PI);
    g.add(twig);
  }
  return g;
}

function makeBird(): Group {
  const g = new Group();
  const mat = paper(PALETTE.bird, 0);
  const wing = new BoxGeometry(0.5, 0.02, 0.16);
  const left = new Mesh(wing, mat); left.position.x = 0.25; left.rotation.z = 0.3;
  const right = new Mesh(wing, mat); right.position.x = -0.25; right.rotation.z = -0.3;
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
  for (let i = 0; i < 7; i++) {
    const a = (i / 7) * Math.PI * 2;
    const frond = new Mesh(new ConeGeometry(0.09, 1.2, 3), frondMat);
    frond.position.set(Math.cos(a) * 0.55, height + 0.1, Math.sin(a) * 0.55);
    frond.rotation.z = -Math.cos(a) * 1.1 + Math.PI / 2;
    frond.rotation.x = Math.sin(a) * 1.1;
    g.add(frond);
  }
  return g;
}

function makeOasis(): Group {
  const g = new Group();
  const water = new Mesh(new CircleGeometry(2.1, 30), new MeshStandardMaterial({
    color: new Color(PALETTE.water), roughness: 0.25, metalness: 0.15, side: DoubleSide,
  }));
  water.rotation.x = -Math.PI / 2;
  water.position.y = 0.02;
  g.add(water);
  const p1 = makePalm(2.8); p1.position.set(-1.6, 0, -1.2);
  const p2 = makePalm(2.3); p2.position.set(1.5, 0, -1.4);
  g.add(p1, p2);
  // a little reed fringe
  for (let i = 0; i < 14; i++) {
    const a = rand() * Math.PI * 2;
    const reed = makeGrassTuft();
    reed.position.set(Math.cos(a) * 2.25, 0, Math.sin(a) * 2.25);
    reed.scale.setScalar(between(0.6, 1));
    g.add(reed);
  }
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
  clouds: Group[];
  grabbables: Object3D[];
}

function place(o: Object3D, x: number, z: number, rotY = rand() * Math.PI * 2): Object3D {
  o.position.x = x; o.position.z = z; o.rotation.y += rotY;
  return o;
}
function scatter(make: () => Object3D, count: number, rMin: number, rMax: number,
                 into: Group, scaleLo = 1, scaleHi = 1) {
  for (let i = 0; i < count; i++) {
    const a = rand() * Math.PI * 2, d = between(rMin, rMax);
    const o = make();
    o.scale.setScalar(between(scaleLo, scaleHi));
    into.add(place(o, Math.cos(a) * d, Math.sin(a) * d));
  }
}

export function buildDesertScene(): DesertScene {
  const statics = new Group();
  const swayCacti: Group[] = [];
  const tumbleweeds: Group[] = [];
  const birds: Group[] = [];
  const clouds: Group[] = [];
  const grabbables: Object3D[] = [];

  // rolling layered dunes all around
  scatter(() => makeDune(between(2.5, 6)), 16, 6, 38, statics);

  // banded mesas on the horizon (replacing the pyramids)
  ([[-10, -22, 5.0, 3.6], [9, -26, 4.2, 3.0], [-24, -14, 4.6, 3.2], [2, -33, 6.0, 4.2], [22, -20, 3.6, 2.6]] as const)
    .forEach(([x, z, h, r]) => statics.add(place(makeMesa(h, r), x, z, between(-0.3, 0.3))));

  // saguaro cacti — most sway
  for (let i = 0; i < 8; i++) {
    const a = rand() * Math.PI * 2, d = between(3.5, 15);
    const cactus = place(makeSaguaro(between(1.9, 3.3)), Math.cos(a) * d, Math.sin(a) * d) as Group;
    if (rand() > 0.25) {
      cactus.userData = { phase: rand() * Math.PI * 2, amp: between(0.015, 0.045), speed: between(0.6, 1.1) };
      swayCacti.push(cactus);
    } else statics.add(cactus);
  }

  // varied low flora
  scatter(makePricklyPear, 6, 3, 18, statics);
  scatter(makeAgave, 6, 3, 16, statics);
  scatter(makeSagebrush, 12, 3, 22, statics);
  scatter(makeGrassTuft, 18, 2.5, 24, statics, 0.7, 1.3);
  scatter(makeFlower, 22, 2.5, 16, statics, 0.7, 1.4);

  // rocks, stacks, pebbles — a few near rocks are grabbable souvenirs
  scatter(makeRockStack, 5, 5, 22, statics);
  for (let i = 0; i < 14; i++) {
    const a = rand() * Math.PI * 2, d = between(2.5, 22);
    const rock = place(makeRock(between(0.25, 0.8)), Math.cos(a) * d, Math.sin(a) * d);
    if (d < 6 && grabbables.length < 3) grabbables.push(rock);
    else statics.add(rock);
  }

  // barrel cacti near the player — grabbable
  ([[1.6, -2.6], [-2.0, -2.2], [2.5, 1.6]] as const).forEach(([x, z]) => grabbables.push(place(makeBarrelCactus(), x, z)));

  // an oasis off to one side
  statics.add(place(makeOasis(), 10, -7, 0));

  // sun
  const sun = makeSun();
  sun.position.set(-10, 11, -24);

  // drifting clouds
  for (let i = 0; i < 7; i++) {
    const cloud = makeCloud(between(0.8, 1.7));
    cloud.position.set(between(-22, 22), between(9, 15), between(-28, -6));
    cloud.userData = { speed: between(0.25, 0.7), xMin: -26, xMax: 26 };
    clouds.push(cloud);
  }

  // tumbleweeds rolling across the flats
  for (let i = 0; i < 3; i++) {
    const tw = makeTumbleweed(between(0.4, 0.6));
    tw.position.set(between(-12, -6), 0.5, between(-9, 6));
    tw.userData = { speed: between(1.3, 2.6), xMin: -15, xMax: 15, baseY: tw.scale.x * 0.5 || 0.5, r: 0.5 };
    tumbleweeds.push(tw);
  }

  // birds wheeling overhead
  for (let i = 0; i < 5; i++) {
    const bird = makeBird();
    bird.userData = { ...bird.userData, cx: between(-5, 5), cz: between(-14, -4), radius: between(4, 9), y: between(6.5, 10), speed: between(0.2, 0.4), phase: rand() * Math.PI * 2 };
    birds.push(bird);
  }

  return { ground: makeGround(), statics, sun, swayCacti, tumbleweeds, birds, clouds, grabbables };
}
