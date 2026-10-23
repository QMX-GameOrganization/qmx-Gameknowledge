// 初音未来：页面底部是一排随鼠标起伏的音频条；点击弹出音符，并按固定旋律依次发声。
// 页面上的桌宠仍由 ThemeSelect 加载的第三方 Hatsune Miku Web Pet 提供。

import type { FxContext } from './index';
import { createLayer, layerModule } from './layer';
import { burst, stepParticles, life01 } from './particles.mjs';

type Note = { x: number; y: number; vx: number; vy: number; life: number; max: number; size: number; rot: number; vr: number; color: string; glyph: string };

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export default layerModule((ctx: FxContext) => {
  const notes: Note[] = [];
  let bars: number[] = [];
  let pulse = 0;
  let sparkle = 0;
  let gradient: CanvasGradient | null = null;

  const pitch = () => (ctx.compact ? 22 : 14);

  return createLayer({
    ctx,
    className: 'qmx-fx-miku',
    placement: 'over',
    staticFrame: true,
    onResize(layer) {
      const count = Math.round(clamp(layer.w / pitch(), 16, 120));
      bars = Array.from({ length: count }, (_, i) => bars[i] ?? 4);
      gradient = layer.g.createLinearGradient(0, 0, layer.w, 0);
      gradient.addColorStop(0, layer.token('--qmx-accent', '#39c5bb'));
      gradient.addColorStop(1, layer.token('--qmx-accent-2', '#ff6fae'));
    },
    update(dt, layer) {
      const { pointer, t, w } = layer;
      pulse = Math.max(0, pulse - dt * 1.6);
      const step = w / bars.length;
      for (let i = 0; i < bars.length; i++) {
        let target = 5 + (Math.sin(t * 1.4 + i * 0.35) + 1) * 3 + (Math.sin(t * 0.8 - i * 0.21) + 1) * 2.5;
        if (pointer.active) {
          const k = Math.max(0, 1 - Math.abs(i * step + step / 2 - pointer.x) / 190);
          target += k * k * 42;
        }
        target += pulse * (10 + 22 * (0.5 + 0.5 * Math.sin(i * 0.5 + t * 4)));
        bars[i] += (target - bars[i]) * Math.min(1, dt * 10);
      }

      // 鼠标快速移动时，在光标后面洒下几颗星屑
      sparkle -= dt;
      if (pointer.active && Math.hypot(pointer.vx, pointer.vy) > 500 && sparkle <= 0) {
        sparkle = 0.12;
        burst(notes, pointer.x, pointer.y, 1, { speed: [10, 40], angle: [-Math.PI, 0], life: [0.6, 0.9], size: [8, 13], colors: ['#ffffff', layer.token('--qmx-accent', '#39c5bb'), layer.token('--qmx-accent-2', '#ff6fae')], spin: [0, 0], cap: 60, extra: () => ({ glyph: '✦' }) });
      }
      stepParticles(notes, dt, { gravity: -35, drag: 0.6 });
    },
    draw(layer) {
      const g = layer.g;
      const { w, h } = layer;
      const step = w / bars.length;
      if (gradient) {
        g.fillStyle = gradient;
        g.globalAlpha = 0.34;
        for (let i = 0; i < bars.length; i++) {
          const bh = bars[i];
          g.beginPath();
          g.roundRect ? g.roundRect(i * step + 2, h - bh, Math.max(3, step - 5), bh + 2, 3) : g.rect(i * step + 2, h - bh, Math.max(3, step - 5), bh + 2);
          g.fill();
        }
      }
      g.textAlign = 'center';
      g.textBaseline = 'middle';
      for (const n of notes) {
        g.globalAlpha = life01(n);
        g.fillStyle = n.color;
        g.font = `${n.size}px sans-serif`;
        g.fillText(n.glyph, n.x, n.y);
      }
      g.globalAlpha = 1;
    },
    onDown(x, y, layer) {
      pulse = 1;
      burst(notes, x, y, 5, {
        speed: [40, 120],
        angle: [-Math.PI * 0.85, -Math.PI * 0.15],
        life: [1.4, 2.2],
        size: [16, 26],
        colors: ['#ffffff', layer.token('--qmx-accent', '#39c5bb'), layer.token('--qmx-accent-2', '#ff6fae')],
        spin: [0, 0],
        cap: 60,
        extra: (rng: () => number) => ({ glyph: ['♪', '♫', '♬'][Math.floor(rng() * 3)] }),
      });
      ctx.audio.melody();
    },
  });
});
