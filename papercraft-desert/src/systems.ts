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
export const DustDevil = createComponent('DustDevil', {});

export class DesertSystem extends createSystem({
  suns: { required: [SunGlow] },
  tumbleweeds: { required: [Tumbleweed] },
  birds: { required: [Bird] },
  sways: { required: [Sway] },
  clouds: { required: [Cloud] },
  dustDevils: { required: [DustDevil] },
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
      o.rotation.z -= dt * u.speed * 2.4;
      o.rotation.x += dt * u.speed * 0.8;
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
      o.rotation.y = -a; // face along the circular path
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

    // Dust devils: spin up, swirl and wander, then fade out and reform elsewhere.
    this.queries.dustDevils.entities.forEach((e) => {
      const o = e.object3D!;
      const u = o.userData;
      u.t = (u.t ?? 0) + dt;
      const p = (u.t % u.period) / u.period;
      const up = 0.2, dn = 0.22;
      let env = p < up ? p / up : p > 1 - dn ? (1 - p) / dn : 1;
      env = env * env * (3 - 2 * env); // smoothstep in/out
      if (p < (u.prevP ?? 0)) {
        // new cycle while invisible: relocate to a fresh spot around the player
        const a = Math.random() * Math.PI * 2, d = 9 + Math.random() * 13;
        u.cx = Math.cos(a) * d; u.cz = Math.sin(a) * d; u.phase0 = Math.random() * Math.PI * 2;
      }
      u.prevP = p;
      o.scale.setScalar(Math.max(0.0001, env * (u.baseScale ?? 1)));
      const ang = u.t * u.wanderSpeed + (u.phase0 ?? 0);
      o.position.x = u.cx + Math.cos(ang) * u.wanderR;
      o.position.z = u.cz + Math.sin(ang) * u.wanderR;
      o.rotation.y += dt * u.spinSpeed;
      if (u.rings) for (const ring of u.rings) ring.rotation.y += dt * ring.userData.spin;
    });
  }
}
