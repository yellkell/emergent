/**
 * Papercraft Desert — an IWSDK / WebXR scene.
 *
 * A calm, encompassing 360° desert you stand inside: open sand underfoot,
 * rolling dunes and banded mesas ringing the horizon all around you, sparse
 * saguaro silhouettes, a gradient sky with drifting clouds, wheeling birds,
 * tumbleweeds, and the occasional wandering dust devil. Locomotion lets you
 * walk / teleport across the sands.
 */
import {
  AmbientLight,
  Color,
  DirectionalLight,
  EnvironmentType,
  Fog,
  HemisphereLight,
  LocomotionEnvironment,
  SessionMode,
  World,
} from '@iwsdk/core';

import { buildDesertScene, makeSkyDome } from './desert.js';
import { Bird, Cloud, DesertSystem, DustDevil, SunGlow, Sway, Tumbleweed } from './systems.js';

World.create(document.getElementById('scene-container') as HTMLDivElement, {
  assets: {},
  xr: {
    sessionMode: SessionMode.ImmersiveVR,
    offer: 'always',
    features: { handTracking: true },
  },
  features: { locomotion: true },
}).then((world) => {
  const { scene, camera } = world;

  // --- sky & light: a warm, slightly hazy desert afternoon ---
  scene.background = new Color(0xf4d2a4);
  scene.fog = new Fog(0xf4d2a4, 22, 88);
  scene.add(makeSkyDome());
  scene.add(new HemisphereLight(0xfff3da, 0xc98a4a, 1.05));
  const sunLight = new DirectionalLight(0xffd9a0, 1.65);
  sunLight.position.set(-12, 11, -8);
  scene.add(sunLight);
  scene.add(new AmbientLight(0xffe9c9, 0.22));

  // --- populate the world ---
  const d = buildDesertScene();

  // Walkable ground (locomotion raycasts hit this).
  world
    .createTransformEntity(d.ground)
    .addComponent(LocomotionEnvironment, { type: EnvironmentType.STATIC });

  // Static scenery (dunes, mesas, fixed cacti).
  world.createTransformEntity(d.statics);

  // Animated members of the ecosystem.
  world.createTransformEntity(d.sun).addComponent(SunGlow);
  d.swayCacti.forEach((o) => world.createTransformEntity(o).addComponent(Sway));
  d.tumbleweeds.forEach((o) => world.createTransformEntity(o).addComponent(Tumbleweed));
  d.birds.forEach((o) => world.createTransformEntity(o).addComponent(Bird));
  d.clouds.forEach((o) => world.createTransformEntity(o).addComponent(Cloud));
  d.dustDevils.forEach((o) => world.createTransformEntity(o).addComponent(DustDevil));

  // Initial framing for the emulator / flat-screen preview (the headset pose
  // takes over inside VR).
  camera.position.set(0, 1.7, 6);
  camera.lookAt(0, 1.5, -12);

  world.registerSystem(DesertSystem);
});
