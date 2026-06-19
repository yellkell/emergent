/**
 * Papercraft Desert — an IWSDK / WebXR scene.
 *
 * A 360° low-poly desert you can stand inside: rolling dunes, saguaro and
 * barrel cacti, distant pyramids, a sunburst sun, an oasis, plus tumbleweeds
 * and birds that move. Locomotion lets you walk/teleport the sands; a few
 * props (rocks, barrel cacti) are grab-and-throwable.
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

import { buildDesertScene } from './desert.js';
import { Bird, DesertSystem, SunGlow, Sway, Tumbleweed } from './systems.js';

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
  scene.background = new Color(0xf6c79a);
  scene.fog = new Fog(0xf6c79a, 16, 62);
  scene.add(new HemisphereLight(0xfff2d8, 0xc98a4a, 1.05));
  const sunLight = new DirectionalLight(0xffd9a0, 1.7);
  sunLight.position.set(-9, 12, -10);
  scene.add(sunLight);
  scene.add(new AmbientLight(0xffe9c9, 0.25));

  // --- populate the world ---
  const d = buildDesertScene();

  // Walkable ground (locomotion raycasts hit this).
  world
    .createTransformEntity(d.ground)
    .addComponent(LocomotionEnvironment, { type: EnvironmentType.STATIC });

  // Static scenery (dunes, pyramids, oasis, fixed cacti & rocks).
  world.createTransformEntity(d.statics);

  // Animated members of the ecosystem.
  world.createTransformEntity(d.sun).addComponent(SunGlow);
  d.swayCacti.forEach((o) => world.createTransformEntity(o).addComponent(Sway));
  d.tumbleweeds.forEach((o) => world.createTransformEntity(o).addComponent(Tumbleweed));
  d.birds.forEach((o) => world.createTransformEntity(o).addComponent(Bird));

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
  camera.lookAt(0, 1.3, -8);

  world.registerSystem(DesertSystem);
});
