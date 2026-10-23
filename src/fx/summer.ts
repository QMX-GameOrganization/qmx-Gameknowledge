// 夏日天气：云慢慢飘，太阳放出光芒，偶尔下一场阵雨。
//   · 阵雨期间云变灰、雨滴落下并在地面溅起涟漪，开启音效时还有淡淡的雨声；
//   · 点击会溅起一圈涟漪和水珠，伴随一声水滴。

import type { FxContext } from './index';
import { createLayer, layerModule, type Layer } from './layer';
import { burst, stepParticles, life01 } from './particles.mjs';

const TAU = Math.PI * 2;

type Cloud = { x: number; y: number; scale: number; speed: number; alpha: number };
type Drop = { x: number; y: number; speed: number; len: number; landY: number };
type Ripple = { x: number; y: number; age: number; max: number };
type Splash = { x: number; y: number; vx: number; vy: number; life: number; max: number; size: number; rot: number; vr: number; color: string };

export default layerModule((ctx: FxContext) => {
  const clouds: Cloud[] = [];
  const drops: Drop[] = [];
  const ripples: Ripple[] = [];
  const splashes: Splash[] = [];
  // 天气状态：raining 为 true 时 rainK 渐渐升到 1，否则降回 0
  let raining = false;
  let nextChange = 25 + Math.random() * 25; // 距离下一次天气变化的秒数
  let rainK = 0;
  let dropCount = 0;
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

  const newDrop = (layer: Layer, anywhere: boolean): Drop => ({
    x: Math.random() * (layer.w + 200) - 100,
    y: anywhere ? Math.random() * layer.h : -30 - Math.random() * 200,
    speed: 620 + Math.random() * 260,
    len: 12 + Math.random() * 14,
    landY: layer.h * (0.55 + Math.random() * 0.45),
  });

  function drawCloud(g: CanvasRenderingContext2D, c: Cloud, gray: number) {
    const s = c.scale;
    // 晴天是白云，下雨时偏灰蓝
    const r = Math.round(255 - gray * 85);
    const gg = Math.round(255 - gray * 62);
    const b = Math.round(255 - gray * 40);
    g.fillStyle = `rgba(${r},${gg},${b},${c.alpha})`;
    g.beginPath();
    for (const [dx, dy, rad] of [[0, 0, 22], [26, -10, 28], [58, -2, 24], [84, 6, 18], [-22, 8, 16]]) {
      g.moveTo(c.x + dx * s + rad * s, c.y + dy * s);
      g.arc(c.x + dx * s, c.y + dy * s, rad * s, 0, TAU);
    }
    g.fill();
  }

  return createLayer({
    ctx,
    className: 'qmx-fx-summer',
    placement: 'under',
    staticFrame: true,
    init(layer) {
      const n = ctx.compact ? 3 : 5;
      for (let i = 0; i < n; i++) {
        clouds.push({ x: (i / n) * layer.w + Math.random() * 120, y: layer.h * (0.08 + Math.random() * 0.34), scale: 0.9 + Math.random() * 1.1, speed: 6 + Math.random() * 10, alpha: 0.5 + Math.random() * 0.2 });
      }
    },
    onResize(layer) {
      dropCount = Math.round(clamp(layer.w / (ctx.compact ? 22 : 11), 30, 150));
      while (drops.length < dropCount) drops.push(newDrop(layer, true));
      drops.length = dropCount;
    },
    update(dt, layer) {
      nextChange -= dt;
      if (nextChange <= 0) {
        raining = !raining;
        nextChange = raining ? 10 + Math.random() * 7 : 45 + Math.random() * 40;
        ctx.audio.rain(raining);
      }
      rainK = clamp(rainK + (raining ? dt / 2.5 : -dt / 3), 0, 1);

      for (const c of clouds) {
        c.x += c.speed * dt;
        if (c.x > layer.w + 160) c.x = -200;
      }

      if (rainK > 0.02) {
        const active = Math.round(dropCount * rainK);
        for (let i = 0; i < active; i++) {
          const d = drops[i];
          d.y += d.speed * dt;
          d.x -= d.speed * 0.18 * dt; // 风让雨丝微微倾斜
          if (d.y >= d.landY) {
            if (ripples.length < 40) ripples.push({ x: d.x, y: d.y, age: 0, max: 0.7 });
            Object.assign(d, newDrop(layer, false));
          }
        }
      }
      for (const r of ripples) r.age += dt;
      for (let i = ripples.length - 1; i >= 0; i--) if (ripples[i].age > ripples[i].max) ripples.splice(i, 1);
      stepParticles(splashes, dt, { gravity: 900 });
    },
    draw(layer) {
      const g = layer.g;
      const { w, t } = layer;

      // 太阳：下雨时淡出
      const sunAlpha = (1 - rainK) * (0.2 + Math.sin(t * 0.8) * 0.02);
      if (sunAlpha > 0.01) {
        const sx = w * 0.82;
        const sy = layer.h * 0.16;
        const glow = g.createRadialGradient(sx, sy, 10, sx, sy, 280);
        glow.addColorStop(0, `rgba(251,191,36,${sunAlpha * 1.6})`);
        glow.addColorStop(1, 'rgba(251,191,36,0)');
        g.fillStyle = glow;
        g.fillRect(0, 0, w, layer.h * 0.7);
        g.save();
        g.translate(sx, sy);
        g.rotate(t * 0.05);
        g.strokeStyle = `rgba(251,191,36,${sunAlpha * 0.5})`;
        g.lineWidth = 2;
        for (let i = 0; i < 12; i++) {
          g.rotate(TAU / 12);
          g.beginPath();
          g.moveTo(70, 0);
          g.lineTo(150 + (i % 2) * 40, 0);
          g.stroke();
        }
        g.restore();
      }

      for (const c of clouds) drawCloud(g, c, rainK);

      if (rainK > 0.02) {
        g.strokeStyle = `rgba(90,160,210,${0.55 * rainK})`;
        g.lineWidth = 1.2;
        g.beginPath();
        const active = Math.round(dropCount * rainK);
        for (let i = 0; i < active; i++) {
          const d = drops[i];
          g.moveTo(d.x, d.y);
          g.lineTo(d.x + d.len * 0.18, d.y - d.len);
        }
        g.stroke();
      }

      g.lineWidth = 1.2;
      for (const r of ripples) {
        const k = r.age / r.max;
        g.strokeStyle = `rgba(70,140,200,${0.5 * (1 - k)})`;
        g.beginPath();
        g.ellipse(r.x, r.y, 4 + k * 34, (4 + k * 34) * 0.35, 0, 0, TAU);
        g.stroke();
      }
      for (const s of splashes) {
        g.fillStyle = s.color;
        g.globalAlpha = life01(s);
        g.beginPath();
        g.arc(s.x, s.y, s.size, 0, TAU);
        g.fill();
      }
      g.globalAlpha = 1;
    },
    onDown(x, y) {
      ripples.push({ x, y, age: 0, max: 0.9 });
      burst(splashes, x, y, 8, { speed: [90, 240], angle: [-Math.PI * 0.9, -Math.PI * 0.1], life: [0.5, 0.9], size: [1.5, 3], colors: ['#7ec3ea', '#5aa9d6', '#a8dcf5'], cap: 60 });
      ctx.audio.plink();
    },
    onDestroy() {
      ctx.audio.rain(false);
    },
  });
});
