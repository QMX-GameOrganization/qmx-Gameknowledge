// 赛博霓虹：光标拖出品红到青色的发光轨迹；点击时炸开两圈霓虹波纹，标题短暂「故障」抖一下。

import type { FxContext } from './index';
import { createLayer, layerModule } from './layer';

const TAU = Math.PI * 2;
const TRAIL_LIFE = 0.5;

type Point = { x: number; y: number; age: number };
type Ring = { x: number; y: number; age: number; delay: number; color: string };

export default layerModule((ctx: FxContext) => {
  const points: Point[] = [];
  const rings: Ring[] = [];
  let glitchTimer = 0;

  return createLayer({
    ctx,
    className: 'qmx-fx-neon',
    placement: 'over',
    update(dt, layer) {
      const p = layer.pointer;
      const last = points[points.length - 1];
      if (p.active && (!last || Math.hypot(p.x - last.x, p.y - last.y) > 3)) {
        points.push({ x: p.x, y: p.y, age: 0 });
        if (points.length > 40) points.shift();
      }
      for (const pt of points) pt.age += dt;
      while (points.length && points[0].age > TRAIL_LIFE) points.shift();
      for (const r of rings) r.age += dt;
      for (let i = rings.length - 1; i >= 0; i--) if (rings[i].age - rings[i].delay > 0.7) rings.splice(i, 1);
    },
    draw(layer) {
      const g = layer.g;
      const pink = layer.token('--qmx-accent', '#ff4fd8');
      const cyan = layer.token('--qmx-accent-2', '#00f0ff');
      g.globalCompositeOperation = 'lighter';
      g.lineCap = 'round';

      // 轨迹：越新越粗越亮，颜色从品红渐变到青色
      for (let i = 1; i < points.length; i++) {
        const a = points[i - 1];
        const b = points[i];
        const k = 1 - b.age / TRAIL_LIFE;
        g.strokeStyle = i % 2 ? pink : cyan;
        g.globalAlpha = 0.22 * k;
        g.lineWidth = 12 * k;
        g.beginPath();
        g.moveTo(a.x, a.y);
        g.lineTo(b.x, b.y);
        g.stroke();
        g.globalAlpha = 0.9 * k;
        g.lineWidth = 2.4 * k;
        g.shadowColor = i % 2 ? pink : cyan;
        g.shadowBlur = 10;
        g.stroke();
        g.shadowBlur = 0;
      }

      if (layer.pointer.active) {
        const pulse = 3 + Math.sin(layer.t * 8) * 0.8;
        g.globalAlpha = 0.9;
        g.fillStyle = '#ffffff';
        g.shadowColor = pink;
        g.shadowBlur = 14;
        g.beginPath();
        g.arc(layer.pointer.x, layer.pointer.y, pulse, 0, TAU);
        g.fill();
        g.shadowBlur = 0;
      }

      for (const r of rings) {
        const age = r.age - r.delay;
        if (age < 0) continue;
        const k = age / 0.7;
        g.globalAlpha = 0.8 * (1 - k);
        g.strokeStyle = r.color;
        g.lineWidth = 2.2;
        g.shadowColor = r.color;
        g.shadowBlur = 12;
        g.beginPath();
        g.arc(r.x, r.y, 8 + k * 150, 0, TAU);
        g.stroke();
        g.shadowBlur = 0;
      }
      g.globalCompositeOperation = 'source-over';
      g.globalAlpha = 1;
    },
    onDown(x, y, layer) {
      rings.push({ x, y, age: 0, delay: 0, color: layer.token('--qmx-accent', '#ff4fd8') });
      rings.push({ x, y, age: 0, delay: 0.08, color: layer.token('--qmx-accent-2', '#00f0ff') });
      // 标题故障抖动：样式在 fx.css 里，这里只负责打开 / 关闭标记
      ctx.root.dataset.qmxGlitch = '1';
      clearTimeout(glitchTimer);
      glitchTimer = window.setTimeout(() => delete ctx.root.dataset.qmxGlitch, 260);
      ctx.audio.zap();
    },
    onDestroy() {
      clearTimeout(glitchTimer);
      delete ctx.root.dataset.qmxGlitch;
    },
  });
});
