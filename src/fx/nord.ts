// Nord 极光：顶部缓缓摆动的极光带，加上被鼠标拨开的飘雪；点击卷起一阵雪粒，伴随冰晶般的长音。

import type { FxContext } from './index';
import { createLayer, layerModule, type Layer } from './layer';
import { burst, pushAway, stepParticles, life01 } from './particles.mjs';

const TAU = Math.PI * 2;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

type Flake = { x: number; y: number; vx: number; vy: number; r: number; fall: number; phase: number; life: number; max: number; size: number; rot: number; vr: number; color: string };
type Sparkle = { x: number; y: number; vx: number; vy: number; life: number; max: number; size: number; rot: number; vr: number; color: string };

// 三条极光带：基线高度、颜色、摆动幅度
const RIBBONS = [
  { y: 0.12, color: '136,192,208', amp: 26, speed: 0.25 },
  { y: 0.19, color: '143,188,187', amp: 34, speed: 0.31 },
  { y: 0.26, color: '180,142,173', amp: 40, speed: 0.19 },
];

export default layerModule((ctx: FxContext) => {
  const flakes: Flake[] = [];
  const sparkles: Sparkle[] = [];
  let shift = 0; // 极光随鼠标横向偏移，平滑过渡

  const spawn = (layer: Layer, anywhere: boolean): Flake => ({
    x: Math.random() * layer.w,
    y: anywhere ? Math.random() * layer.h : -10,
    vx: 0,
    vy: 20,
    r: 1 + Math.random() * 1.6,
    fall: 18 + Math.random() * 30,
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
    className: 'qmx-fx-nord',
    placement: 'under',
    staticFrame: true,
    onResize(layer) {
      const want = Math.round(clamp((layer.w * layer.h) / (ctx.compact ? 40000 : 26000), 24, 80));
      while (flakes.length < want) flakes.push(spawn(layer, true));
      flakes.length = Math.min(flakes.length, want);
    },
    update(dt, layer) {
      const { pointer, t } = layer;
      const goal = pointer.active ? (pointer.x / layer.w - 0.5) * 36 : 0;
      shift += (goal - shift) * Math.min(1, dt * 2);

      if (pointer.active) pushAway(flakes, pointer.x, pointer.y, 110, 900, dt);
      for (const f of flakes) {
        f.phase += dt;
        f.vx += (Math.sin(f.phase * 0.8 + t * 0.2) * 12 - f.vx) * Math.min(1, dt * 1.2);
        f.vy += (f.fall - f.vy) * Math.min(1, dt * 1.2);
        f.x += f.vx * dt;
        f.y += f.vy * dt;
        if (f.y > layer.h + 10) Object.assign(f, spawn(layer, false));
        if (f.x < -10) f.x = layer.w + 10;
        else if (f.x > layer.w + 10) f.x = -10;
      }
      stepParticles(sparkles, dt, { gravity: 40, drag: 0.55 });
    },
    draw(layer) {
      const g = layer.g;
      const { w, h, t } = layer;

      // 极光：每条是一个上下边缘都在摆动的色带，用一次竖向渐变填充
      g.globalCompositeOperation = 'lighter';
      RIBBONS.forEach((r, i) => {
        const base = h * r.y;
        const top = base - r.amp - 20;
        const grad = g.createLinearGradient(0, top, 0, base + 130);
        grad.addColorStop(0, `rgba(${r.color},0)`);
        grad.addColorStop(0.35, `rgba(${r.color},0.16)`);
        grad.addColorStop(1, `rgba(${r.color},0)`);
        g.fillStyle = grad;
        g.beginPath();
        const steps = Math.ceil(w / 14);
        for (let s = 0; s <= steps; s++) {
          const x = s * 14;
          const y = base + Math.sin((x + shift) * 0.004 + t * r.speed + i * 1.7) * r.amp + Math.sin((x + shift) * 0.011 - t * 0.4) * r.amp * 0.4;
          if (s === 0) g.moveTo(x, y);
          else g.lineTo(x, y);
        }
        for (let s = steps; s >= 0; s--) {
          const x = s * 14;
          const y = base + 100 + Math.sin((x + shift) * 0.006 + t * 0.3 + i) * 38 + Math.sin((x + shift) * 0.004 + t * r.speed + i * 1.7) * r.amp;
          g.lineTo(x, y);
        }
        g.closePath();
        g.fill();
      });
      g.globalCompositeOperation = 'source-over';

      g.fillStyle = '#eceff4';
      for (const f of flakes) {
        g.globalAlpha = 0.35 + f.r * 0.2;
        g.beginPath();
        g.arc(f.x, f.y, f.r, 0, TAU);
        g.fill();
      }
      for (const s of sparkles) {
        g.globalAlpha = life01(s);
        g.fillStyle = s.color;
        g.beginPath();
        g.arc(s.x, s.y, s.size, 0, TAU);
        g.fill();
      }
      g.globalAlpha = 1;
    },
    onDown(x, y) {
      // 点击卷起一阵雪：附近的雪花被吹开，同时迸出一些冰晶
      for (const f of flakes) {
        const dx = f.x - x;
        const dy = f.y - y;
        const d = Math.hypot(dx, dy);
        if (d < 200 && d > 0.001) {
          const k = 1 - d / 200;
          f.vx += (dx / d) * k * 260;
          f.vy += (dy / d) * k * 260;
        }
      }
      burst(sparkles, x, y, 14, { speed: [40, 180], life: [0.8, 1.4], size: [1.2, 2.6], colors: ['#eceff4', '#88c0d0', '#8fbcbb'], cap: 60 });
      ctx.audio.icy();
    },
  });
});
