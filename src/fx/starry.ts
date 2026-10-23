// 星夜：整页星空。
//   · 鼠标靠近时，周围的星星被推开，移开后弹簧一样回到原位；
//   · 被推开的星星之间会短暂连成星座线；
//   · 点击会产生冲击波和涟漪；偶尔有流星划过；
//   · 滚动页面时远近不同的星星以不同速度漂移(视差)。
// 物理部分在 star-physics.mjs，这里只负责画布、事件和绘制。

import type { FxContext, FxModule } from './index';
import { createStars, stepStars, shockwave, drawPosition, DEFAULT_PARAMS } from './star-physics.mjs';

const TAU = Math.PI * 2;

type Meteor = { x: number; y: number; vx: number; vy: number; life: number };
type Ripple = { x: number; y: number; age: number };

let cleanup: (() => void) | null = null;

const starry: FxModule = {
  start(ctx: FxContext) {
    cleanup?.();
    const { root, audio, reduced, compact } = ctx;

    const canvas = document.createElement('canvas');
    canvas.className = 'qmx-fx-stars';
    canvas.setAttribute('aria-hidden', 'true');
    document.body.prepend(canvas);
    const g = canvas.getContext('2d');
    if (!g) {
      canvas.remove();
      return;
    }

    // 颜色从主题令牌读取，以后调整配色不用改这里。
    const css = getComputedStyle(root);
    const token = (name: string, fallback: string) => css.getPropertyValue(name).trim() || fallback;
    const palette = [token('--qmx-text', '#e5f3ff'), token('--qmx-accent', '#7dd3fc'), token('--qmx-accent-2', '#a78bfa')];

    let w = 0;
    let h = 0;
    const stars = createStars(0);
    const countFor = () => Math.max(40, Math.min(260, Math.round((w * h) / (compact ? 14000 : 8500))));

    function resize() {
      w = window.innerWidth;
      h = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      g!.setTransform(dpr, 0, 0, dpr, 0, 0);
      const want = countFor();
      if (stars.length < want) stars.push(...createStars(want - stars.length));
      else stars.length = want;
    }
    resize();

    const pointer = { x: -9999, y: -9999, active: false };
    const meteors: Meteor[] = [];
    const ripples: Ripple[] = [];
    let t = 0;
    let nextMeteor = 3 + Math.random() * 5;
    let raf = 0;
    let last = 0;
    const px = new Float32Array(400);
    const py = new Float32Array(400);

    function drawFrame(animated: boolean) {
      const view = { width: w, height: h, scrollY: window.scrollY };
      g!.clearRect(0, 0, w, h);

      const near: number[] = [];
      const reach = DEFAULT_PARAMS.radius * 1.4;
      for (let i = 0; i < stars.length; i++) {
        const s = stars[i];
        const p = drawPosition(s, w, h, view.scrollY);
        px[i] = p.x;
        py[i] = p.y;
        if (animated && pointer.active && near.length < 40 && Math.hypot(p.x - pointer.x, p.y - pointer.y) < reach) near.push(i);

        const tw = animated ? 0.62 + 0.38 * Math.sin(t * s.speed + s.phase) : 0.8;
        const glow = Math.min(1, Math.hypot(s.vx, s.vy) / 350);
        const alpha = Math.min(1, (0.35 + s.layer * 0.18) * tw + glow * 0.5);
        g!.globalAlpha = alpha;
        g!.fillStyle = palette[s.tint];
        g!.beginPath();
        g!.arc(p.x, p.y, s.r * (1 + glow * 0.6), 0, TAU);
        g!.fill();

        // 最近一层较亮的星星带十字星芒
        if (s.layer === 2 && tw > 0.8) {
          const len = s.r * 4.5 * tw;
          g!.globalAlpha = alpha * 0.5;
          g!.strokeStyle = palette[s.tint];
          g!.lineWidth = 0.6;
          g!.beginPath();
          g!.moveTo(p.x - len, p.y);
          g!.lineTo(p.x + len, p.y);
          g!.moveTo(p.x, p.y - len);
          g!.lineTo(p.x, p.y + len);
          g!.stroke();
        }
      }

      if (!animated) return;

      // 星座线：鼠标周围彼此靠近的星星连起来
      g!.lineWidth = 0.7;
      g!.strokeStyle = palette[1];
      for (let a = 0; a < near.length; a++) {
        for (let b = a + 1; b < near.length; b++) {
          const i = near[a];
          const j = near[b];
          const d = Math.hypot(px[i] - px[j], py[i] - py[j]);
          if (d < 90) {
            g!.globalAlpha = 0.3 * (1 - d / 90);
            g!.beginPath();
            g!.moveTo(px[i], py[i]);
            g!.lineTo(px[j], py[j]);
            g!.stroke();
          }
        }
      }

      // 点击涟漪
      for (const r of ripples) {
        const k = r.age / 0.7;
        g!.globalAlpha = (1 - k) * 0.5;
        g!.strokeStyle = palette[2];
        g!.lineWidth = 1.2;
        g!.beginPath();
        g!.arc(r.x, r.y, 10 + r.age * 340, 0, TAU);
        g!.stroke();
      }

      // 流星
      for (const m of meteors) {
        const speed = Math.hypot(m.vx, m.vy);
        const tail = 130;
        const tx = m.x - (m.vx / speed) * tail;
        const ty = m.y - (m.vy / speed) * tail;
        const grad = g!.createLinearGradient(m.x, m.y, tx, ty);
        grad.addColorStop(0, palette[0]);
        grad.addColorStop(1, 'transparent');
        g!.globalAlpha = Math.min(1, m.life * 2);
        g!.strokeStyle = grad;
        g!.lineWidth = 1.6;
        g!.beginPath();
        g!.moveTo(m.x, m.y);
        g!.lineTo(tx, ty);
        g!.stroke();
      }
      g!.globalAlpha = 1;
    }

    function frame(now: number) {
      raf = requestAnimationFrame(frame);
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      t += dt;

      const pushed = stepStars(stars, dt, pointer, { width: w, height: h, scrollY: window.scrollY });
      if (pushed >= 3) audio.chime(true);

      for (const r of ripples) r.age += dt;
      for (let i = ripples.length - 1; i >= 0; i--) if (ripples[i].age > 0.7) ripples.splice(i, 1);

      nextMeteor -= dt;
      if (nextMeteor <= 0 && meteors.length === 0) {
        const angle = Math.PI * (0.78 + Math.random() * 0.1); // 朝左下
        meteors.push({
          x: w * (0.35 + Math.random() * 0.65),
          y: -20 + Math.random() * h * 0.3,
          vx: Math.cos(angle) * 900,
          vy: Math.sin(angle) * 900,
          life: 1,
        });
        audio.whoosh();
        nextMeteor = 6 + Math.random() * 8;
      }
      for (const m of meteors) {
        m.x += m.vx * dt;
        m.y += m.vy * dt;
        m.life -= dt * 0.45;
      }
      for (let i = meteors.length - 1; i >= 0; i--) {
        const m = meteors[i];
        if (m.life <= 0 || m.x < -200 || m.y > h + 200) meteors.splice(i, 1);
      }

      drawFrame(true);
    }

    // ───── 事件 ─────
    const onMove = (e: PointerEvent) => {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      pointer.active = true;
    };
    const onUp = (e: PointerEvent) => {
      if (e.pointerType === 'touch') pointer.active = false; // 手指抬起后没有「悬停」
    };
    const onOut = (e: MouseEvent) => {
      if (!e.relatedTarget) pointer.active = false; // 鼠标离开了窗口
    };
    const onDown = (e: PointerEvent) => {
      shockwave(stars, e.clientX, e.clientY, { width: w, height: h, scrollY: window.scrollY });
      ripples.push({ x: e.clientX, y: e.clientY, age: 0 });
      audio.chime();
    };
    const onVisibility = () => {
      if (document.hidden) {
        cancelAnimationFrame(raf);
      } else {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      }
    };
    let resizePending = false;
    const onResize = () => {
      if (resizePending) return;
      resizePending = true;
      requestAnimationFrame(() => {
        resizePending = false;
        resize();
        if (reduced) drawFrame(false);
      });
    };

    window.addEventListener('resize', onResize);

    if (reduced) {
      // 系统要求减少动态效果：只画一张静态星空，不响应鼠标、不做动画。
      drawFrame(false);
      cleanup = () => {
        window.removeEventListener('resize', onResize);
        canvas.remove();
      };
      return;
    }

    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerup', onUp, { passive: true });
    window.addEventListener('pointercancel', onUp, { passive: true });
    window.addEventListener('pointerdown', onDown, { passive: true });
    document.addEventListener('mouseout', onOut);
    document.addEventListener('visibilitychange', onVisibility);

    last = performance.now();
    raf = requestAnimationFrame(frame);

    cleanup = () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
      window.removeEventListener('pointerdown', onDown);
      document.removeEventListener('mouseout', onOut);
      document.removeEventListener('visibilitychange', onVisibility);
      canvas.remove();
    };
  },

  stop() {
    cleanup?.();
    cleanup = null;
  },
};

export default starry;
