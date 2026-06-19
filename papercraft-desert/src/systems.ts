/**
 * Behaviour for the living parts of the desert.
 *
 * Each animated object carries a tiny marker component; one system advances
 * them every frame using parameters stashed in the object's `userData`
 * (filled in by the builders in `desert.ts`).
 */
import { createComponent, createSystem } from '@iwsdk/core';

export const SunGlow = createComponent('SunGlow', {});
export const Tumbleweed = createComponent('Tumbleweed', {});
export const Bird = createComponent('Bird', {});
export const Sway = createComponent('Sway', {});
export const Cloud = createComponent('Cloud', {});

export class DesertSystem extends createSystem({
  suns: { required: [SunGlow] },
  tumbleweeds: { required: [Tumbleweed] },
  birds: { required: [Bird] },
  sways: { required: [Sway] },
  clouds: { required: [Cloud] },
}) {
  update(delta: number, time: number) {
    const dt = Math.min(delta, 0.05); // guard against hitches / paused tabs

    // The sun breathes a little.
    this.queries.suns.entities.forEach((e) => {
      const o = e.object3D!;
      const base = (o.userData.baseScale as number) ?? 1;
      o.scale.setScalar(base * (1 + 0.05 * Math.sin(time * 1.2)));
    });

    // Tumbleweeds roll across the flats, bounce, and tumble end over end.
    this.queries.tumbleweeds.entities.forEach((e) => {
      const o = e.object3D!;
      const u = o.userData;
      o.position.x += dt * u.speed;
      if (o.position.x > u.xMax) o.position.x = u.xMin;
      o.position.y = u.baseY + Math.abs(Math.sin(o.position.x * 1.5)) * 0.18;
      o.rotation.z -= dt * u.speed * 2.4; // roll in the travel direction
      o.rotation.x += dt * u.speed * 0.8; // chaotic tumble
    });

    // Birds wheel overhead, banking and flapping.
    this.queries.birds.entities.forEach((e) => {
      const o = e.object3D!;
      const u = o.userData;
      const a = time * u.speed + u.phase;
      o.position.set(
        u.cx + Math.cos(a) * u.radius,
        u.y + Math.sin(a * 2) * 0.4,
        u.cz + Math.sin(a) * u.radius,
      );
      o.rotation.y = -a + Math.PI / 2;
      const flap = Math.sin(time * 9 + u.phase) * 0.5;
      if (u.wings) {
        u.wings[0].rotation.z = 0.3 + flap;
        u.wings[1].rotation.z = -0.3 - flap;
      }
    });

    // Cacti sway gently in the breeze.
    this.queries.sways.entities.forEach((e) => {
      const o = e.object3D!;
      const u = o.userData;
      o.rotation.z = Math.sin(time * u.speed + u.phase) * u.amp;
    });

    // Clouds drift slowly and wrap around the sky.
    this.queries.clouds.entities.forEach((e) => {
      const o = e.object3D!;
      const u = o.userData;
      o.position.x += dt * u.speed;
      if (o.position.x > u.xMax) o.position.x = u.xMin;
    });
  }
}
