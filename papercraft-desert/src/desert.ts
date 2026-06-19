/**
 * Procedural "papercraft" desert — open & encompassing.
 *
 * A calm, surrounding scene rather than a cluttered diorama: open sand at your
 * feet, rolling dunes and banded mesas ringing you 360°, sparse saguaro
 * silhouettes, a gradient sky with drifting clouds, wheeling birds, tumbleweeds
 * and the occasional wandering dust devil. Plain Three.js (re-exported by
 * @iwsdk/core): low-poly + flat-shaded, faceted like folded cardstock, with
 * dark "fold" seams on the hero shapes. Builders return detached Object3Ds;
 * `src/index.ts` turns them into IWSDK entities. Animation params ride in
 * `userData`.
 */
import {
  BackSide,
  BufferAttribute,
  CapsuleGeometry,
  CircleGeometry,
  Color,
  ConeGeometry,
  CylinderGeometry,
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
  BoxGeometry,
} from '@iwsdk/core';

// ---- palette --------------------------------------------------------------
const PALETTE = {
  sand: 0xe7c98a,
  sandWarm: 0xdcb878,
  sandPale: 0xeed7a6,
  mesa: [0xb9603b, 0xc4744a, 0xd98a5a, 0xc26240, 0xa84e34, 0xe0a96d], // banded sandstone
  mesaTalus: 0x8f4a33,
  cactus: 0x6fa86a,
  cloud: 0xfbf6ec,
  cloudShade: 0xe7d8c1,
  sunCore: 0xffd86b,
  sunRays: 0xffae4d,
  dust: 0xdcc097,
  dustPale: 0xe9d6b4,
  bird: 0x4a3f37,
  skyTop: 0xa9c6dc,
  skyHorizon: 0xf4d2a4,
};

// ---- seeded RNG -----------------------------------------------------------
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
const rand = rng(0x0a51de);
const between = (lo: number, hi: number) => lo + (hi - lo) * rand();

function paper(color: number, jitter = 0.05, opts: object = {}): MeshStandardMaterial {
  const c = new Color(color);
  if (jitter) c.offsetHSL(0, (rand() - 0.5) * 0.02, (rand() - 0.5) * jitter);
  return new MeshStandardMaterial({ color: c, flatShading: true, roughness: 0.97, metalness: 0, ...opts });
}
function unlit(color: number, opacity = 1): MeshBasicMaterial {
  return new MeshBasicMaterial({ color: new Color(color), transparent: opacity < 1, opacity, side: DoubleSide });
}
function seams(geometry: any, opacity = 0.14): LineSegments {
  return new LineSegments(new EdgesGeometry(geometry, 18),
    new LineBasicMaterial({ color: 0x3a2c1f, transparent: true, opacity }));
}
function meshSeam(geometry: any, material: MeshStandardMaterial, seamOpacity = 0.16): Group {
  const g = new Group();
  g.add(new Mesh(geometry, material), seams(geometry, seamOpacity));
  return g;
}

// ---- ground & sky ---------------------------------------------------------
export function makeGround(radius = 60): Mesh {
  const geo = new CircleGeometry(radius, 64);
  geo.rotateX(-Math.PI / 2);
  return new Mesh(geo, new MeshStandardMaterial({
    color: new Color(PALETTE.sand), roughness: 1, metalness: 0, side: DoubleSide,
  }));
}

export function makeSkyDome(): Mesh {
  const geo = new SphereGeometry(140, 24, 16);
  const top = new Color(PALETTE.skyTop);
  const hor = new Color(PALETTE.skyHorizon);
  const pos = geo.attributes.position;
  const colors = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const t = Math.pow(Math.max(0, pos.getY(i) / 140), 0.6);
    const c = hor.clone().lerp(top, t);
    colors.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new BufferAttribute(colors, 3));
  return new Mesh(geo, new MeshBasicMaterial({ vertexColors: true, side: BackSide, fog: false }));
}

// ---- terrain --------------------------------------------------------------
function makeDune(r: number): Group {
  const g = new Group();
  const base = new Mesh(new IcosahedronGeometry(r, 1), paper(PALETTE.sandWarm, 0.05));
  base.geometry.scale(1, 0.36, 1.2);
  base.position.y = -r * 0.24;
  base.rotation.y = rand() * Math.PI;
  const crest = new Mesh(new IcosahedronGeometry(r * 0.6, 1), paper(PALETTE.sandPale, 0.04));
  crest.geometry.scale(1.15, 0.36, 0.8);
  crest.position.set(r * 0.2, r * 0.04, 0);
  crest.rotation.y = rand() * Math.PI;
  g.add(base, crest);
  return g;
}

/** Layered banded sandstone mesa/butte — the horizon landmark. */
function makeMesa(height: number, rBase: number): Group {
  const g = new Group();
  const layers = 5 + Math.floor(rand() * 3);
  let y = 0;
  for (let i = 0; i < layers; i++) {
    const t = i / layers;
    const lh = (height / layers) * between(0.85, 1.15);
    const r = rBase * (1 - t * 0.42) * between(0.96, 1.04);
    const geo = new CylinderGeometry(r, r * 1.03, lh, 7);
    geo.rotateY(rand() * 0.4);
    const layer = meshSeam(geo, paper(PALETTE.mesa[i % PALETTE.mesa.length], 0.04), 0.18);
    layer.position.y = y + lh / 2;
    g.add(layer);
    y += lh;
  }
  const skirt = new Mesh(new ConeGeometry(rBase * 1.25, height * 0.28, 7), paper(PALETTE.mesaTalus, 0.03));
  skirt.position.y = height * 0.14;
  g.add(skirt);
  return g;
}

function makeSaguaro(height = 2.8): Group {
  const g = new Group();
  const mat = paper(PALETTE.cactus, 0.04);
  const r = 0.27;
  const trunk = meshSeam(new CapsuleGeometry(r, height - 2 * r, 4, 9), mat, 0.1);
  trunk.position.y = height / 2;
  g.add(trunk);
  const addArm = (side: number, atY: number, armH: number) => {
    const horiz = new Mesh(new CapsuleGeometry(0.15, 0.32, 3, 7), mat);
    horiz.rotation.z = Math.PI / 2;
    horiz.position.set(side * 0.27, atY, 0);
    const vert = new Mesh(new CapsuleGeometry(0.17, armH, 3, 7), mat);
    vert.position.set(side * 0.44, atY + armH / 2, 0);
    g.add(horiz, vert);
  };
  addArm(1, height * 0.46, between(0.55, 0.85));
  if (rand() > 0.3) addArm(-1, height * 0.62, between(0.45, 0.75));
  return g;
}

// ---- sky elements ---------------------------------------------------------
export function makeSun(): Group {
  const g = new Group();
  const pts = 16;
  const rays = new Group();
  for (let i = 0; i < pts; i++) {
    const a = (i / pts) * Math.PI * 2;
    const ray = new Mesh(new ConeGeometry(0.5, 1.5, 3), unlit(PALETTE.sunRays, 0.55));
    ray.position.set(Math.cos(a) * 2.0, Math.sin(a) * 2.0, -0.05);
    ray.rotation.z = a - Math.PI / 2;
    rays.add(ray);
  }
  g.add(rays, new Mesh(new CircleGeometry(1.45, 36), unlit(PALETTE.sunCore)));
  g.userData.baseScale = 1;
  return g;
}

function makeCloud(scale = 1): Group {
  const g = new Group();
  const n = 5 + Math.floor(rand() * 4);
  for (let i = 0; i < n; i++) {
    const puff = new Mesh(new IcosahedronGeometry(between(0.8, 1.5) * scale, 1),
      paper(rand() > 0.3 ? PALETTE.cloud : PALETTE.cloudShade, 0.02));
    puff.geometry.scale(1.2, 0.62, 1);
    puff.position.set(between(-2.2, 2.2) * scale, between(-0.15, 0.25) * scale, between(-0.5, 0.5) * scale);
    g.add(puff);
  }
  return g;
}

function makeBird(): Group {
  const g = new Group();
  const mat = paper(PALETTE.bird, 0);
  // Spindle body running front-to-back, with a beak and a forked tail.
  const body = new Mesh(new CapsuleGeometry(0.05, 0.26, 2, 6), mat);
  body.rotation.x = Math.PI / 2;
  const beak = new Mesh(new ConeGeometry(0.035, 0.12, 4), paper(0xc98a3a, 0));
  beak.rotation.x = -Math.PI / 2;
  beak.position.z = 0.24;
  const tail = new Mesh(new ConeGeometry(0.07, 0.18, 3), mat);
  tail.rotation.x = Math.PI / 2;
  tail.position.z = -0.22;
  g.add(body, beak, tail);
  // Wings flap about the body axis (z).
  const wing = new BoxGeometry(0.5, 0.02, 0.18);
  const left = new Mesh(wing, mat); left.position.x = 0.27; left.rotation.z = 0.3;
  const right = new Mesh(wing, mat); right.position.x = -0.27; right.rotation.z = -0.3;
  g.add(left, right);
  g.userData.wings = [left, right];
  return g;
}

/** Tangled dry brush: crisscrossing faceted rings + stray twigs. */
function makeTumbleweed(r = 0.5): Group {
  const g = new Group();
  const rings = 7 + Math.floor(rand() * 3);
  for (let i = 0; i < rings; i++) {
    const ring = new Mesh(new TorusGeometry(r * between(0.7, 1.0), 0.022, 3, 9),
      paper(0x9c7440, 0.06));
    ring.rotation.set(rand() * Math.PI, rand() * Math.PI, rand() * Math.PI);
    g.add(ring);
  }
  for (let i = 0; i < 5; i++) {
    const twig = new Mesh(new ConeGeometry(0.02, between(0.3, 0.5), 3), paper(0xc7a064, 0.05));
    const a = rand() * Math.PI * 2, b = rand() * Math.PI;
    twig.position.set(Math.sin(b) * Math.cos(a) * r, Math.cos(b) * r, Math.sin(b) * Math.sin(a) * r);
    twig.rotation.set(rand() * Math.PI, rand() * Math.PI, rand() * Math.PI);
    g.add(twig);
  }
  return g;
}

/**
 * A wandering dust devil: a flaring column of semi-transparent, swirling dust.
 * Built from open (C-shaped) faceted rings up a leaning helix, so spinning them
 * reads as a whirling vortex. Lifecycle (fade in/out, relocate) and spin live in
 * the DesertSystem; the spinnable rings are exposed via `userData.rings`.
 */
export function makeDustDevil(): Group {
  const g = new Group();
  const rings: Mesh[] = [];
  const segs = 9;
  const height = between(3.6, 5.6);
  const baseR = 0.16;
  const topR = between(0.9, 1.5);
  const dustMat = () => paper(rand() > 0.4 ? PALETTE.dust : PALETTE.dustPale, 0.05,
    { transparent: true, opacity: between(0.26, 0.46), depthWrite: false, side: DoubleSide });
  for (let i = 0; i < segs; i++) {
    const t = i / (segs - 1);
    const r = baseR + (topR - baseR) * Math.pow(t, 0.7);
    const ring = new Mesh(new TorusGeometry(r, 0.05 + 0.05 * t, 4, 9, between(3.4, 5.0)), dustMat());
    ring.rotation.x = Math.PI / 2;
    ring.rotation.y = rand() * Math.PI * 2;
    ring.position.set(Math.sin(t * 6) * 0.12, t * height, Math.cos(t * 6) * 0.12); // leaning helix
    ring.userData.spin = between(2.5, 5) * (rand() > 0.5 ? 1 : -1);
    if (rand() > 0.5) { // a speck of debris orbiting on this ring
      const speck = new Mesh(new IcosahedronGeometry(0.05, 0), paper(0x9c7440, 0.1));
      speck.position.x = r;
      ring.add(speck);
    }
    g.add(ring);
    rings.push(ring);
  }
  const puff = new Mesh(new IcosahedronGeometry(baseR * 2.4, 1), dustMat());
  puff.geometry.scale(1, 0.4, 1);
  puff.position.y = 0.08;
  g.add(puff);
  g.userData.rings = rings;
  return g;
}

// ---- assembled scene ------------------------------------------------------
export interface DesertScene {
  ground: Mesh;
  statics: Group;
  sun: Group;
  swayCacti: Group[];
  tumbleweeds: Group[];
  birds: Group[];
  clouds: Group[];
  dustDevils: Group[];
}

function place(o: Object3D, x: number, z: number, rotY = rand() * Math.PI * 2): Object3D {
  o.position.x = x; o.position.z = z; o.rotation.y += rotY;
  return o;
}

export function buildDesertScene(): DesertScene {
  const statics = new Group();
  const swayCacti: Group[] = [];
  const tumbleweeds: Group[] = [];
  const birds: Group[] = [];
  const clouds: Group[] = [];
  const dustDevils: Group[] = [];

  // Rolling dunes ring the open centre 360° (nothing crowds the player).
  for (let i = 0; i < 20; i++) {
    const a = rand() * Math.PI * 2, d = between(10, 46);
    statics.add(place(makeDune(between(3, 7)), Math.cos(a) * d, Math.sin(a) * d));
  }

  // Banded mesas encircle the horizon.
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2 + between(-0.32, 0.32), d = between(26, 46);
    statics.add(place(makeMesa(between(3.4, 6.4), between(2.4, 4.4)), Math.cos(a) * d, Math.sin(a) * d, between(-0.3, 0.3)));
  }

  // Sparse saguaro silhouettes, kept out of the immediate foreground; most sway.
  for (let i = 0; i < 7; i++) {
    const a = rand() * Math.PI * 2, d = between(9, 26);
    const cactus = place(makeSaguaro(between(2.1, 3.4)), Math.cos(a) * d, Math.sin(a) * d) as Group;
    if (rand() > 0.25) {
      cactus.userData = { phase: rand() * Math.PI * 2, amp: between(0.015, 0.045), speed: between(0.6, 1.1) };
      swayCacti.push(cactus);
    } else statics.add(cactus);
  }

  // Sun.
  const sun = makeSun();
  sun.position.set(-12, 12, -28);

  // Clouds drift all around the sky (including behind you).
  for (let i = 0; i < 8; i++) {
    const cloud = makeCloud(between(0.9, 1.8));
    cloud.position.set(between(-26, 26), between(9, 16), between(-30, 18));
    cloud.userData = { speed: between(0.25, 0.7), xMin: -30, xMax: 30 };
    clouds.push(cloud);
  }

  // Tumbleweeds roam across the open flats (some pass behind you).
  for (let i = 0; i < 4; i++) {
    const tw = makeTumbleweed(between(0.4, 0.6));
    tw.position.set(between(-16, -6), 0.5, between(-13, 11));
    tw.userData = { speed: between(1.3, 2.6), xMin: -18, xMax: 18, baseY: 0.5 };
    tumbleweeds.push(tw);
  }

  // Occasional wandering dust devils.
  for (let i = 0; i < 2; i++) {
    const dd = makeDustDevil();
    const a = rand() * Math.PI * 2, d = between(9, 20);
    const cx = Math.cos(a) * d, cz = Math.sin(a) * d;
    dd.position.set(cx, 0, cz);
    dd.userData = {
      ...dd.userData,
      t: rand() * 30, period: between(24, 34), baseScale: between(0.9, 1.25),
      cx, cz, wanderR: between(3, 7), wanderSpeed: between(0.05, 0.12),
      spinSpeed: between(0.7, 1.3) * (rand() > 0.5 ? 1 : -1), phase0: rand() * Math.PI * 2, prevP: 0,
    };
    dustDevils.push(dd);
  }

  // Birds wheeling high overhead.
  for (let i = 0; i < 5; i++) {
    const bird = makeBird();
    bird.userData = { ...bird.userData, cx: between(-6, 6), cz: between(-16, 4), radius: between(5, 10), y: between(7, 11), speed: between(0.18, 0.36), phase: rand() * Math.PI * 2 };
    birds.push(bird);
  }

  return { ground: makeGround(), statics, sun, swayCacti, tumbleweeds, birds, clouds, dustDevils };
}
