// GitHub 经典：鼠标周围浮现一片「贡献热力图」方格，划过的方格会变绿并慢慢褪色；
// 点击相当于提交了一次 commit：附近方格变成深绿，飘起一个 +1。

import type { FxContext } from './index';
import { createLayer, layerModule } from './layer';

const SIZE = 12;
const PITCH = 15;
const REACH = 3.4; // 鼠标划过时点亮的半径（格）
const SHOW = 8; // 鼠标周围显示空方格的半径（格）
const GREENS = ['#9be9a8', '#40c463', '#30a14e', '#216e39'];

type Plus = { x: number; y: number; age: number };

export default layerModule((ctx: FxContext) => {
  let cols = 0;
  let rows = 0;
  let heat = new Float32Array(0);
  const plus: Plus[] = [];

  const light = (cx: number, cy: number, radius: number, value: number) => {
    for (let r = Math.max(0, cy - Math.ceil(radius)); r <= Math.min(rows - 1, cy + Math.ceil(radius)); r++) {
      for (let c = Math.max(0, cx - Math.ceil(radius)); c <= Math.min(cols - 1, cx + Math.ceil(radius)); c++) {
        const d = Math.hypot(c - cx, r - cy);
        if (d <= radius) {
          const i = r * cols + c;
          heat[i] = Math.max(heat[i], value * (1 - (d / radius) * 0.6));
        }
      }
    }
  };

  return createLayer({
    ctx,
    className: 'qmx-fx-github',
    placement: 'under',
    onResize(layer) {
      cols = Math.ceil(layer.w / PITCH);
      rows = Math.ceil(layer.h / PITCH);
      heat = new Float32Array(cols * rows);
    },
    update(dt, layer) {
      for (let i = 0; i < heat.length; i++) if (heat[i] > 0) heat[i] = Math.max(0, heat[i] - dt / 1.6);
      const p = layer.pointer;
      if (p.active) light(Math.floor(p.x / PITCH), Math.floor(p.y / PITCH), REACH, 1);
      for (const t of plus) t.age += dt;
      while (plus.length && plus[0].age > 1) plus.shift();
    },
    draw(layer) {
      const g = layer.g;
      const p = layer.pointer;
      const pc = Math.floor(p.x / PITCH);
      const pr = Math.floor(p.y / PITCH);
      const fill = (c: number, r: number) => {
        if (g.roundRect) {
          g.beginPath();
          g.roundRect(c * PITCH, r * PITCH, SIZE, SIZE, 2);
          g.fill();
        } else {
          g.fillRect(c * PITCH, r * PITCH, SIZE, SIZE);
        }
      };

      // 鼠标附近的空方格，越远越淡
      if (p.active) {
        g.fillStyle = '#d0d7de';
        for (let r = Math.max(0, pr - SHOW); r <= Math.min(rows - 1, pr + SHOW); r++) {
          for (let c = Math.max(0, pc - SHOW); c <= Math.min(cols - 1, pc + SHOW); c++) {
            const d = Math.hypot(c - pc, r - pr);
            if (d <= SHOW && heat[r * cols + c] < 0.05) {
              g.globalAlpha = 0.42 * (1 - d / SHOW);
              fill(c, r);
            }
          }
        }
      }

      // 点亮的方格：热度越高颜色越深
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const v = heat[r * cols + c];
          if (v < 0.05) continue;
          g.fillStyle = GREENS[Math.min(3, Math.floor(v * 4))];
          g.globalAlpha = 0.35 + 0.5 * v;
          fill(c, r);
        }
      }

      g.fillStyle = '#216e39';
      g.font = '600 13px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
      g.textAlign = 'center';
      for (const t of plus) {
        g.globalAlpha = 1 - t.age;
        g.fillText('+1', t.x, t.y - t.age * 34);
      }
      g.globalAlpha = 1;
    },
    onDown(x, y) {
      light(Math.floor(x / PITCH), Math.floor(y / PITCH), 2.6, 1);
      plus.push({ x, y, age: 0 });
      ctx.audio.commit();
    },
  });
});
