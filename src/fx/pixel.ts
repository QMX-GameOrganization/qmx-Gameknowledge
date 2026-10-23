// 像素终端：光标后面拖着一串像素方块；点击迸出像素碎片，键盘敲击有 8 位按键声。

import type { FxContext } from './index';
import { createLayer, layerModule } from './layer';
import { burst, stepParticles, life01 } from './particles.mjs';

const CELL = 6;

type Trail = { x: number; y: number; life: number; max: number };
type Bit = { x: number; y: number; vx: number; vy: number; life: number; max: number; size: number; rot: number; vr: number; color: string };

export default layerModule((ctx: FxContext) => {
  const trail: Trail[] = [];
  const bits: Bit[] = [];
  let lastCell = '';

  return createLayer({
    ctx,
    className: 'qmx-fx-pixel',
    placement: 'over',
    update(dt, layer) {
      const p = layer.pointer;
      if (p.active) {
        const gx = Math.floor(p.x / CELL);
        const gy = Math.floor(p.y / CELL);
        const key = `${gx},${gy}`;
        if (key !== lastCell) {
          lastCell = key;
          trail.push({ x: gx * CELL, y: gy * CELL, life: 0.55, max: 0.55 });
          if (trail.length > 90) trail.shift();
        }
      }
      for (const t of trail) t.life -= dt;
      while (trail.length && trail[0].life <= 0) trail.shift();
      stepParticles(bits, dt, { gravity: 700 });
    },
    draw(layer) {
      const g = layer.g;
      const accent = layer.token('--qmx-accent', '#a3e635');
      g.fillStyle = accent;
      for (const t of trail) {
        g.globalAlpha = 0.7 * (t.life / t.max);
        g.fillRect(t.x, t.y, CELL, CELL);
      }
      for (const b of bits) {
        g.globalAlpha = life01(b);
        g.fillStyle = b.color;
        // 贴着像素网格绘制，保持「点阵」的颗粒感
        g.fillRect(Math.round(b.x / 2) * 2, Math.round(b.y / 2) * 2, Math.round(b.size), Math.round(b.size));
      }
      g.globalAlpha = 1;
    },
    onDown(x, y) {
      burst(bits, x, y, 14, { speed: [90, 300], life: [0.5, 0.9], size: [4, 8], colors: ['#a3e635', '#22c55e', '#ecfccb', '#facc15'], cap: 120 });
      ctx.audio.retro('click');
    },
    onKey() {
      ctx.audio.retro('key');
    },
  });
});
