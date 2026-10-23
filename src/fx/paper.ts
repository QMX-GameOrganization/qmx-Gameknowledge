// 护眼纸张：点击处洇开一滴墨；页面顶部有一条阅读进度的墨线，读完一页会轻轻响一声铃。
// 进度条不是动画，所以即使系统要求减少动态效果也会保留。

import type { FxContext, FxModule } from './index';
import { createLayer } from './layer';

const TAU = Math.PI * 2;

type Blot = { dx: number; dy: number; r: number };
type Ink = { x: number; y: number; age: number; max: number; blots: Blot[] };

let teardown: (() => void) | null = null;

const paper: FxModule = {
  start(ctx: FxContext) {
    teardown?.();
    const inks: Ink[] = [];

    const built = createLayer({
      ctx,
      className: 'qmx-fx-paper',
      placement: 'under',
      update(dt) {
        for (const ink of inks) ink.age += dt;
        for (let i = inks.length - 1; i >= 0; i--) if (inks[i].age > inks[i].max) inks.splice(i, 1);
      },
      draw(layer) {
        const g = layer.g;
        g.fillStyle = '#3b2f22';
        for (const ink of inks) {
          const k = ink.age / ink.max;
          const spread = 1 - Math.pow(1 - Math.min(1, k * 1.6), 3); // 先快后慢地洇开
          g.globalAlpha = 0.17 * Math.pow(1 - k, 1.5);
          g.beginPath();
          for (const b of ink.blots) {
            g.moveTo(ink.x + b.dx * spread + b.r * spread, ink.y + b.dy * spread);
            g.arc(ink.x + b.dx * spread, ink.y + b.dy * spread, b.r * spread, 0, TAU);
          }
          g.fill();
        }
        g.globalAlpha = 1;
      },
      onDown(x, y) {
        const blots: Blot[] = [{ dx: 0, dy: 0, r: 34 + Math.random() * 16 }];
        for (let i = 0; i < 4; i++) {
          const a = Math.random() * TAU;
          const d = 14 + Math.random() * 22;
          blots.push({ dx: Math.cos(a) * d, dy: Math.sin(a) * d, r: 14 + Math.random() * 18 });
        }
        inks.push({ x, y, age: 0, max: 1.8, blots });
        if (inks.length > 12) inks.shift();
        ctx.audio.paper();
      },
    });

    // 阅读进度：顶部一条随滚动变长的墨线
    const bar = document.createElement('div');
    bar.className = 'qmx-read-progress';
    bar.setAttribute('aria-hidden', 'true');
    document.body.append(bar);

    let ticking = false;
    let belled = false;
    const update = () => {
      ticking = false;
      const doc = document.documentElement;
      const max = doc.scrollHeight - window.innerHeight;
      const p = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
      bar.style.transform = `scaleX(${p})`;
      if (p >= 0.985 && max > window.innerHeight * 0.5 && !belled) {
        belled = true;
        ctx.audio.bell();
      } else if (p < 0.9) {
        belled = false;
      }
    };
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(update);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    update();

    teardown = () => {
      built?.destroy();
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      bar.remove();
    };
  },

  stop() {
    teardown?.();
    teardown = null;
  },
};

export default paper;
