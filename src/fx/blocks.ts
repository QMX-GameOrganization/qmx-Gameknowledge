// 方块世界：点击就像挖掉一块方块，迸出草、泥土和石头的碎屑，留下一道短暂的裂纹；
// 页面底部住着一只立方史莱姆（桌宠逻辑见 pet-fx.ts）。

import type { FxContext } from './index';
import { createLayer, layerModule, combine } from './layer';
import { createPetFx } from './pet-fx';
import { slimeSvg } from './pet-art';
import { burst, stepParticles, life01 } from './particles.mjs';

type Chip = { x: number; y: number; vx: number; vy: number; life: number; max: number; size: number; rot: number; vr: number; color: string };
type Crack = { x: number; y: number; age: number; segs: number[][] };

const COLORS = ['#7cc242', '#5fa02e', '#8a5a2b', '#6b4423', '#8b8b8b', '#5d5d5d'];

const debris = layerModule((ctx: FxContext) => {
  const chips: Chip[] = [];
  const cracks: Crack[] = [];

  return createLayer({
    ctx,
    className: 'qmx-fx-blocks',
    placement: 'over',
    update(dt) {
      stepParticles(chips, dt, { gravity: 1400 });
      for (const c of cracks) c.age += dt;
      while (cracks.length && cracks[0].age > 0.45) cracks.shift();
    },
    draw(layer) {
      const g = layer.g;
      g.strokeStyle = '#111111';
      g.lineWidth = 2;
      g.lineCap = 'square';
      for (const c of cracks) {
        g.globalAlpha = 0.7 * (1 - c.age / 0.45);
        g.beginPath();
        for (const [dx, dy, ex, ey] of c.segs) {
          g.moveTo(c.x + dx, c.y + dy);
          g.lineTo(c.x + ex, c.y + ey);
        }
        g.stroke();
      }
      for (const p of chips) {
        const s = Math.round(p.size);
        g.globalAlpha = Math.min(1, life01(p) * 1.6);
        g.fillStyle = p.color;
        g.fillRect(Math.round(p.x), Math.round(p.y), s, s);
        g.fillStyle = '#00000044'; // 底部一圈阴影，让碎屑有「方块」的立体感
        g.fillRect(Math.round(p.x), Math.round(p.y) + s - 1, s, 1);
      }
      g.globalAlpha = 1;
    },
    onDown(x, y) {
      burst(chips, x, y, 12, { speed: [120, 360], angle: [-Math.PI * 0.95, -Math.PI * 0.05], life: [0.8, 1.3], size: [5, 9], colors: COLORS, cap: 90 });
      // 六道短短的裂纹，向四周随机伸出
      const segs: number[][] = [];
      for (let i = 0; i < 6; i++) {
        const a = (i / 6) * Math.PI * 2 + Math.random() * 0.6;
        const r1 = 3 + Math.random() * 4;
        const r2 = 12 + Math.random() * 14;
        segs.push([Math.cos(a) * r1, Math.sin(a) * r1, Math.cos(a + 0.2) * r2, Math.sin(a + 0.2) * r2]);
      }
      cracks.push({ x, y, age: 0, segs });
      ctx.audio.crack();
    },
  });
});

const slime = createPetFx('blocks', {
  kind: 'slime',
  svg: slimeSvg,
  walkSpeed: 34,
  lines: [
    '噗叽。我是方块史莱姆。',
    '点页面任何地方,都能挖下一块方块。',
    '这里的资料也能合成新知识。',
    '小心脚下,别被我踩到。',
    '挖到好东西了吗?',
    '拖我飞起来试试,落地不会摔坏。',
    '存档点已更新。',
  ],
  greeting: '噗叽!新的区块加载完毕。',
  wakeLine: '……噗?我没睡着。',
  endLine: '页面挖到底了,辛苦啦。',
  onPoke: (audio) => audio.boing(),
  onLand: (audio) => audio.boing(),
  onBoot: () => {},
});

export default combine(debris, slime);
