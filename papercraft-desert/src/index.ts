/**
 * Papercraft Desert — an IWSDK / WebXR scene.
 *
 * A 360° low-poly desert you can stand inside: layered banded mesas, saguaro /
 * prickly-pear / agave / barrel cacti, sagebrush, wildflowers and grass, an
 * oasis, a gradient sky with drifting clouds, a sunburst sun, plus tumbleweeds
 * and birds that move. Locomotion lets you walk/teleport the sands; a few props
 * (rocks, barrel cacti) are grab-and-throwable.
 */
import {
  AmbientLight,
  Color,
  DirectionalLight,
  DistanceGrabbable,
  EnvironmentType,
  Fog,
  HemisphereLight,
  Interactable,
  LocomotionEnvironment,
  MovementMode,
  SessionMode,
  World,
} from '@iwsdk/core';

import { buildDesertScene, makeSkyDome } from './desert.js';
import { Bird, Cloud, DesertSystem, SunGlow, Sway, Tumbleweed } from './systems.js';

World.create(document.getElementById('scene-container') as HTMLDivElement, {
  assets: {},
  xr: {
    sessionMode: SessionMode.ImmersiveVR,
    offer: 'always',
    features: { handTracking: true },
  },
  features: { grabbing: true, locomotion: true },
}).then((world) => {
  const { scene, camera } = world;

  // --- sky & light: a warm, slightly hazy desert afternoon ---
  scene.background = new Color(0xf4d2a4);
  scene.fog = new Fog(0xf4d2a4, 20, 72);
  scene.add(makeSkyDome());
  scene.add(new HemisphereLight(0xfff3da, 0xc98a4a, 1.05));
  const sunLight = new DirectionalLight(0xffd9a0, 1.65);
  sunLight.position.set(-10, 11, -10);
  scene.add(sunLight);
  scene.add(new AmbientLight(0xffe9c9, 0.22));

  // --- populate the world ---
  const d = buildDesertScene();

  // Walkable ground (locomotion raycasts hit this).
  world
    .createTransformEntity(d.ground)
    .addComponent(LocomotionEnvironment, { type: EnvironmentType.STATIC });

  // Static scenery (mesas, dunes, fixed flora, rocks, oasis).
  world.createTransformEntity(d.statics);

  // Animated members of the ecosystem.
  world.createTransformEntity(d.sun).addComponent(SunGlow);
  d.swayCacti.forEach((o) => world.createTransformEntity(o).addComponent(Sway));
  d.tumbleweeds.forEach((o) => world.createTransformEntity(o).addComponent(Tumbleweed));
  d.birds.forEach((o) => world.createTransformEntity(o).addComponent(Bird));
  d.clouds.forEach((o) => world.createTransformEntity(o).addComponent(Cloud));

  // Grab-and-throw souvenirs.
  d.grabbables.forEach((o) =>
    world
      .createTransformEntity(o)
      .addComponent(Interactable)
      .addComponent(DistanceGrabbable, { movementMode: MovementMode.MoveFromTarget }),
  );

  // Initial framing for the emulator / flat-screen preview (the headset pose
  // takes over inside VR).
  camera.position.set(0, 1.7, 7);
  camera.lookAt(0, 1.4, -10);

  world.registerSystem(DesertSystem);
});
