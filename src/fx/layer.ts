// 画布层：全屏 canvas + 动画循环 + 鼠标状态 + 清理，供各主题特效复用。
//
// 模块只需要提供 update(dt) 和 draw()，其余的事情这里统一处理：
//   · 高分屏缩放(最多 2 倍)与窗口尺寸变化；
//   · 标签页隐藏时暂停动画；
//   · 鼠标位置 / 速度、点击、按键；
//   · 系统要求「减少动态效果」时只画一帧静态画面，或者干脆不显示；
//   · 销毁时移除画布和所有监听。

import type { FxContext, FxModule } from './index';

export interface Pointer {
  x: number;
  y: number;
  active: boolean;
  /** 平滑后的鼠标速度，px/s；停止移动后很快衰减回 0 */
  vx: number;
  vy: number;
}

export interface Layer {
  canvas: HTMLCanvasElement;
  g: CanvasRenderingContext2D;
  w: number;
  h: number;
  dpr: number;
  /** 从启动开始累计的秒数 */
  t: number;
  pointer: Pointer;
  ctx: FxContext;
  /** 读取主题令牌，例如 layer.token('--qmx-accent', '#fff')，这样调整配色不用改特效代码 */
  token(name: string, fallback: string): string;
}

export interface LayerOptions {
  ctx: FxContext;
  className: string;
  /** under：在页面内容之下(背景氛围)；over：在内容之上(点击、光标效果)。两种都不拦截鼠标。 */
  placement: 'under' | 'over';
  init?(layer: Layer): void;
  update(dt: number, layer: Layer): void;
  draw(layer: Layer): void;
  onDown?(x: number, y: number, layer: Layer): void;
  onKey?(event: KeyboardEvent, layer: Layer): void;
  onResize?(layer: Layer): void;
  /** 减少动态效果时：true 只画一帧静态画面，不设置则完全不显示 */
  staticFrame?: boolean;
  onDestroy?(layer: Layer): void;
}

export function createLayer(o: LayerOptions): { layer: Layer; destroy: () => void } | null {
  const { ctx } = o;
  if (ctx.reduced && !o.staticFrame) return null;

  const canvas = document.createElement('canvas');
  canvas.className = `qmx-fx-layer qmx-fx-layer--${o.placement} ${o.className}`;
  canvas.setAttribute('aria-hidden', 'true');
  const g = canvas.getContext('2d');
  if (!g) return null;
  if (o.placement === 'under') document.body.prepend(canvas);
  else document.body.append(canvas);

  const css = getComputedStyle(ctx.root);
  const layer: Layer = {
    canvas,
    g,
    w: 0,
    h: 0,
    dpr: 1,
    t: 0,
    pointer: { x: -9999, y: -9999, active: false, vx: 0, vy: 0 },
    ctx,
    token: (name, fallback) => css.getPropertyValue(name).trim() || fallback,
  };

  function resize() {
    layer.w = window.innerWidth;
    layer.h = window.innerHeight;
    layer.dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(layer.w * layer.dpr);
    canvas.height = Math.round(layer.h * layer.dpr);
    g!.setTransform(layer.dpr, 0, 0, layer.dpr, 0, 0);
    o.onResize?.(layer);
  }
  resize();
  o.init?.(layer);

  let raf = 0;
  let last = 0;
  let lastMove = 0;

  function frame(now: number) {
    raf = requestAnimationFrame(frame);
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    layer.t += dt;
    const p = layer.pointer;
    const decay = Math.exp(-dt * 6);
    p.vx *= decay;
    p.vy *= decay;
    o.update(dt, layer);
    g!.clearRect(0, 0, layer.w, layer.h);
    o.draw(layer);
  }

  const onMove = (e: PointerEvent) => {
    const p = layer.pointer;
    const now = performance.now();
    if (p.active && lastMove) {
      const span = Math.max((now - lastMove) / 1000, 0.008);
      p.vx = p.vx * 0.6 + ((e.clientX - p.x) / span) * 0.4;
      p.vy = p.vy * 0.6 + ((e.clientY - p.y) / span) * 0.4;
    }
    lastMove = now;
    p.x = e.clientX;
    p.y = e.clientY;
    p.active = true;
  };
  const onUp = (e: PointerEvent) => {
    if (e.pointerType === 'touch') layer.pointer.active = false; // 手指抬起后没有「悬停」
  };
  const onOut = (e: MouseEvent) => {
    if (!e.relatedTarget) layer.pointer.active = false; // 鼠标离开了窗口
  };
  const onDown = (e: PointerEvent) => {
    layer.pointer.x = e.clientX;
    layer.pointer.y = e.clientY;
    o.onDown?.(e.clientX, e.clientY, layer);
  };
  const onKey = (e: KeyboardEvent) => o.onKey?.(e, layer);
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
      if (ctx.reduced) o.draw(layer);
    });
  };

  window.addEventListener('resize', onResize);

  if (ctx.reduced) {
    // 只画一张静态画面，不监听鼠标，不跑动画。
    o.draw(layer);
  } else {
    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerup', onUp, { passive: true });
    window.addEventListener('pointercancel', onUp, { passive: true });
    window.addEventListener('pointerdown', onDown, { passive: true });
    if (o.onKey) window.addEventListener('keydown', onKey, { passive: true });
    document.addEventListener('mouseout', onOut);
    document.addEventListener('visibilitychange', onVisibility);
    last = performance.now();
    raf = requestAnimationFrame(frame);
  }

  const destroy = () => {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', onResize);
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', onUp);
    window.removeEventListener('pointercancel', onUp);
    window.removeEventListener('pointerdown', onDown);
    window.removeEventListener('keydown', onKey);
    document.removeEventListener('mouseout', onOut);
    document.removeEventListener('visibilitychange', onVisibility);
    o.onDestroy?.(layer);
    canvas.remove();
  };

  return { layer, destroy };
}

/** 把几个特效模块组合成一个，例如「画布特效 + 桌宠」。 */
export function combine(...mods: FxModule[]): FxModule {
  return {
    async start(ctx: FxContext) {
      await Promise.all(mods.map((m) => m.start(ctx)));
    },
    stop() {
      mods.forEach((m) => m.stop());
    },
  };
}

/**
 * 把「创建 / 销毁」包装成 FxModule，省去每个模块里重复的 cleanup 样板，
 * 同时处理好重复 start 与 stop。
 */
export function layerModule(build: (ctx: FxContext) => { layer: Layer; destroy: () => void } | null) {
  let current: { destroy: () => void } | null = null;
  return {
    start(ctx: FxContext) {
      current?.destroy();
      current = build(ctx);
    },
    stop() {
      current?.destroy();
      current = null;
    },
  };
}
