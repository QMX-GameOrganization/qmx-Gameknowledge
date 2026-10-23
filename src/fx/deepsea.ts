// 深海蓝：水泡从页面底部缓缓升起，鼠标划过会把附近的水泡推开，点击迸出一串小水泡。
// 水泡画在内容之下，不拦截鼠标；系统要求「减少动态效果」时只画静止的一帧。

import type { FxContext } from './index';
import { createLayer, layerModule, type Layer } from './layer';
import { burst, pushAway, stepParticles, life01 } from './particles.mjs';

const TAU = Math.PI * 2;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

type Bubble = { x: number; y: number; vx: number; vy: number; r: number; rise: number; phase: number; life: number; max: number; size: number; rot: number; vr: number; color: string };

export default layerModule((ctx: FxContext) => {
  const bubbles: Bubble[] = [];
  const pops: Bubble[] = [];

  const spawn = (layer: Layer, anywhere: boolean): Bubble => ({
    x: Math.random() * layer.w,
    y: anywhere ? Math.random() * layer.h : layer.h + 20,
    vx: 0,
    vy: -20,
    r: 2 + Math.random() * 7,
    rise: 14 + Math.random() * 30,
    phase: Math.random() * TAU,
    life: 1,
    max: 1,
    size: 0,
    rot: 0,
    vr: 0,
    color: '',
  });

  return createLayer({
    ctx,
    className: 'qmx-fx-deepsea',
    placement: 'under',
    staticFrame: true,
    onResize(layer) {
      const want = Math.round(clamp((layer.w * layer.h) / (ctx.compact ? 36000 : 22000), 16, 60));
      while (bubbles.length < want) bubbles.push(spawn(layer, true));
      bubbles.length = Math.min(bubbles.length, want);
    },
    update(dt, layer) {
      const { pointer } = layer;
      if (pointer.active) pushAway(bubbles, pointer.x, pointer.y, 120, 700, dt);
      for (const b of bubbles) {
        b.phase += dt * (0.8 + b.r * 0.05);
        // 大水泡升得快，并且左右轻轻摇摆
        b.vx += (Math.sin(b.phase) * 10 - b.vx) * Math.min(1, dt * 1.5);
        b.vy += (-b.rise - b.r * 2 - b.vy) * Math.min(1, dt * 1.2);
        b.x += b.vx * dt;
        b.y += b.vy * dt;
        if (b.y < -20) Object.assign(b, spawn(layer, false));
        if (b.x < -20) b.x = layer.w + 20;
        else if (b.x > layer.w + 20) b.x = -20;
      }
      stepParticles(pops, dt, { gravity: -40, drag: 0.6 });
    },
    draw(layer) {
      const g = layer.g;
      const rim = layer.token('--qmx-accent', '#38bdf8');
      g.lineWidth = 1.2;
      g.strokeStyle = rim;
      g.fillStyle = rim;
      for (const b of bubbles) {
        g.globalAlpha = 0.14;
        g.beginPath();
        g.arc(b.x, b.y, b.r, 0, TAU);
        g.fill();
        g.globalAlpha = 0.45;
        g.stroke();
        g.globalAlpha = 0.6; // 高光
        g.fillStyle = '#ffffff';
        g.beginPath();
        g.arc(b.x - b.r * 0.35, b.y - b.r * 0.35, Math.max(0.8, b.r * 0.18), 0, TAU);
        g.fill();
        g.fillStyle = rim;
      }
      for (const p of pops) {
        g.globalAlpha = 0.6 * life01(p);
        g.beginPath();
        g.arc(p.x, p.y, p.size, 0, TAU);
        g.stroke();
      }
      g.globalAlpha = 1;
    },
    onDown(x, y) {
      burst(pops, x, y, 10, { speed: [30, 140], life: [0.8, 1.5], size: [2, 6], colors: [''], cap: 50 });
      ctx.audio.chime(true);
    },
  });
});
