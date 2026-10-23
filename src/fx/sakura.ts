// 春樱：花瓣在页面背后飘落。
//   · 风会慢慢变向；鼠标划过时带起一阵风，把附近的花瓣吹开；
//   · 点击会撒出一小把花瓣，并伴随一声筝的拨弦。

import type { FxContext } from './index';
import { createLayer, layerModule, type Layer } from './layer';
import { burst, stepParticles, life01 } from './particles.mjs';

const TAU = Math.PI * 2;
const PINKS = ['#f9a8c9', '#fbb6ce', '#f78fb3', '#ffc2d8'];

type Petal = { x: number; y: number; vx: number; vy: number; size: number; rot: number; vr: number; flip: number; flipSpeed: number; phase: number; sway: number; fall: number; color: string };
type Spark = { x: number; y: number; vx: number; vy: number; life: number; max: number; size: number; rot: number; vr: number; color: string; flip: number };

function drawPetal(g: CanvasRenderingContext2D, x: number, y: number, s: number, rot: number, flip: number, color: string, alpha: number) {
  g.save();
  g.translate(x, y);
  g.rotate(rot);
  g.scale(1, 0.55 + 0.45 * Math.abs(Math.cos(flip))); // 翻转时的透视压缩
  g.globalAlpha = alpha;
  g.fillStyle = color;
  g.beginPath();
  g.moveTo(0, -s);
  g.bezierCurveTo(s * 0.95, -s * 0.7, s * 0.8, s * 0.55, 0, s);
  g.bezierCurveTo(-s * 0.8, s * 0.55, -s * 0.95, -s * 0.7, 0, -s);
  g.fill();
  g.restore();
}

export default layerModule((ctx: FxContext) => {
  const petals: Petal[] = [];
  const sparks: Spark[] = [];
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

  const spawn = (layer: Layer, anywhere: boolean): Petal => ({
    x: Math.random() * layer.w,
    y: anywhere ? Math.random() * layer.h : -20,
    vx: 0,
    vy: 20,
    size: 6 + Math.random() * 6,
    rot: Math.random() * TAU,
    vr: (Math.random() - 0.5) * 1.6,
    flip: Math.random() * TAU,
    flipSpeed: 1 + Math.random() * 2,
    phase: Math.random() * TAU,
    sway: 0.6 + Math.random() * 0.9,
    fall: 26 + Math.random() * 30,
    color: PINKS[Math.floor(Math.random() * PINKS.length)],
  });

  const target = (layer: Layer) => Math.round(clamp((layer.w * layer.h) / (ctx.compact ? 70000 : 42000), 12, 42));

  return createLayer({
    ctx,
    className: 'qmx-fx-sakura',
    placement: 'under',
    staticFrame: true,
    // 花瓣数量在 onResize 里补齐(创建画布时会先调用一次)
    onResize(layer) {
      const want = target(layer);
      while (petals.length < want) petals.push(spawn(layer, true));
      petals.length = Math.min(petals.length, want);
    },
    update(dt, layer) {
      const { pointer, t } = layer;
      const wind = Math.sin(t * 0.3) * 22 + Math.sin(t * 0.11) * 14;
      for (const p of petals) {
        p.phase += dt * p.sway;
        p.flip += dt * p.flipSpeed;
        p.vx += (wind + Math.sin(p.phase) * 18 - p.vx) * Math.min(1, dt * 1.5);
        p.vy += (p.fall - p.vy) * Math.min(1, dt * 1.2);

        if (pointer.active) {
          const dx = p.x - pointer.x;
          const dy = p.y - pointer.y;
          const d = Math.hypot(dx, dy);
          if (d < 130 && d > 0.001) {
            const k = 1 - d / 130;
            p.vx += (dx / d) * k * k * 520 * dt + clamp(pointer.vx, -1200, 1200) * 0.8 * k * dt;
            p.vy += (dy / d) * k * k * 520 * dt + clamp(pointer.vy, -1200, 1200) * 0.4 * k * dt;
          }
        }

        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.rot += (p.vr + p.vx * 0.004) * dt;
        if (p.y > layer.h + 20) Object.assign(p, spawn(layer, false));
        if (p.x < -30) p.x = layer.w + 30;
        else if (p.x > layer.w + 30) p.x = -30;
      }
      stepParticles(sparks, dt, { gravity: 70, drag: 0.5 });
    },
    draw(layer) {
      const g = layer.g;
      for (const p of petals) drawPetal(g, p.x, p.y, p.size, p.rot, p.flip, p.color, 0.78);
      for (const s of sparks) drawPetal(g, s.x, s.y, s.size, s.rot, s.flip + layer.t * 3, s.color, 0.85 * life01(s));
      g.globalAlpha = 1;
    },
    onDown(x, y) {
      burst(sparks, x, y, 16, {
        speed: [60, 220],
        angle: [-Math.PI * 0.95, -Math.PI * 0.05],
        life: [1.6, 2.6],
        size: [5, 9],
        colors: PINKS,
        extra: (rng: () => number) => ({ flip: rng() * TAU }),
        cap: 80,
      });
      ctx.audio.pluck();
    },
  });
});
