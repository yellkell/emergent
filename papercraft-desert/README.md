# Papercraft Desert 🏜️

A low-poly, **papercraft**-styled desert scene for **WebXR**, built on the
[Immersive Web SDK (IWSDK)](https://iwsdk.dev) — Three.js rendering + an ECS +
Vite. Stand inside a 360° desert of folded-cardstock dunes, cacti and pyramids;
walk the sands, and pick up a souvenir rock.

Everything is generated procedurally from Three.js primitives with flat-shaded
matte materials, so there are **no external 3D assets to download**.

## What's in the scene

- **Terrain** — a sandy floor ringed by rolling, half-buried low-poly dunes.
- **Flora** — saguaro cacti (most gently **sway** in the breeze) and barrel cacti.
- **Landmarks** — four-sided sandstone **pyramids** on the hazy horizon, and a small **oasis** (water + palms).
- **Sky** — a warm gradient, distance **fog**, and a papercraft **sunburst** sun that softly pulses.
- **Life** — **tumbleweeds** that roll across the flats and **birds** that wheel and flap overhead.
- **Interaction** — **VR locomotion** (walk/teleport the ground) and **grabbable** props (rocks & barrel cacti you can pick up and throw).

## Run it

Requires **Node ≥ 20.19**.

```bash
npm install
npm run dev      # starts the dev server + in-browser WebXR emulator, opens a tab
```

No headset needed to iterate: IWSDK's emulator (IWER) activates automatically
when no real XR device is present, with mouse/keyboard controls. On a Meta Quest
(or any WebXR browser), open the dev URL and **Enter VR**.

```bash
npm run build    # production bundle in dist/
npm run preview  # serve the production build
```

## How it's organized

```
src/
├── index.ts     Bootstrap: World.create(), sky + lights, wires objects into
│                ECS entities, attaches interaction/behaviour components.
├── desert.ts    Pure Three.js builders — the "papercraft" geometry + palette.
│                Each builder returns a detached Object3D; animation params ride
│                in its userData.
└── systems.ts   ECS: marker components (SunGlow, Tumbleweed, Bird, Sway) and a
                 single DesertSystem that animates them every frame.
```

The core pattern is IWSDK's: build a Three.js `Object3D`, turn it into an entity
with `world.createTransformEntity(obj)`, then `.addComponent(...)` to give it
behaviour (`Sway`, `Tumbleweed`, …) or interaction (`Interactable` +
`DistanceGrabbable`) or world role (`LocomotionEnvironment`).

## Extending it

- **New prop:** add a `makeX()` builder in `desert.ts`, push it into one of the
  `DesertScene` categories in `buildDesertScene()`, and `index.ts` will wire it up.
- **New behaviour:** add a marker `createComponent('X', {})` in `systems.ts`, a
  query to `DesertSystem`, and animate `entity.object3D` in `update(delta, time)`.
- **Tune the look:** colors live in the `PALETTE` map; lighting/fog/sky are at the
  top of `index.ts`.

Generated with the Immersive Web SDK (`@iwsdk/core` 0.4.x).
