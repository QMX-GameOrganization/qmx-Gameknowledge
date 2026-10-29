// 文章配图的点击放大预览。
//
//   · 点击正文里的图片：从缩略图的位置飞出，放大到完整放进窗口；
//   · 滚轮 / 触控板捏合 / 双指 / 按钮 / 键盘缩放，以光标为中心；拖拽平移；双击在「适应窗口」和「放大」之间切换；
//   · 同一页的图片组成相册：← → 或按钮翻页，触屏左右滑动；
//   · Esc、点空白处、关闭按钮退出，焦点回到被点击的图片；
//   · 系统开启「减少动态效果」时没有飞入飞出动画。
//
// 纯计算部分在 lightbox-math.mjs，界面样式在 src/styles/lightbox.css。

import {
  fitScale, scaleLimits, clampPan, centered, zoomAt, panBy, wheelFactor, doubleTapTarget,
  nextIndex, isSwipe, thumbTransform, rectVisible, percent, clamp,
} from './lightbox-math.mjs';

type Transform = { s: number; x: number; y: number };
type Pointer = { x: number; y: number };

const SELECTOR = '.sl-markdown-content img';
const MIN_DISPLAY = 64; // 比这更小的多半是图标 / 徽章，不做放大
const ICONS = {
  close: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  prev: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>',
  next: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>',
  open: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
};

let started = false;

const svgSizeCache = new Map<string, { w: number; h: number } | null>();

/** 读取 SVG 声明的尺寸：优先 viewBox，其次 width / height。同源请求，浏览器缓存里通常已经有了。 */
async function readSvgSize(src: string) {
  if (svgSizeCache.has(src)) return svgSizeCache.get(src)!;
  let size: { w: number; h: number } | null = null;
  try {
    const text = await (await fetch(src)).text();
    const head = text.slice(0, 2000).match(/<svg\b[^>]*>/i)?.[0] ?? '';
    const vb = head.match(/viewBox\s*=\s*["']\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)/i);
    const wAttr = head.match(/\swidth\s*=\s*["']([\d.]+)(?:px)?["']/i);
    const hAttr = head.match(/\sheight\s*=\s*["']([\d.]+)(?:px)?["']/i);
    if (vb && +vb[1] > 0 && +vb[2] > 0) size = { w: +vb[1], h: +vb[2] };
    else if (wAttr && hAttr && +wAttr[1] > 0 && +hAttr[1] > 0) size = { w: +wAttr[1], h: +hAttr[1] };
  } catch {
    size = null; // 读不到就沿用浏览器报告的尺寸
  }
  svgSizeCache.set(src, size);
  return size;
}

export function initLightbox() {
  if (started) return;
  started = true;

  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ───── 哪些图片可以放大 ─────
  function eligible(img: HTMLImageElement) {
    if (img.closest('a, [data-no-zoom], .qmx-lb')) return false; // 本来就是链接的图不抢点击
    if (img.hasAttribute('data-no-zoom')) return false;
    const r = img.getBoundingClientRect();
    return Math.max(r.width, img.naturalWidth) >= MIN_DISPLAY && img.naturalWidth > 0;
  }

  function mark(img: HTMLImageElement) {
    if (img.dataset.qmxZoom) return;
    if (!eligible(img)) return;
    img.dataset.qmxZoom = '1';
    img.tabIndex = 0;
    img.setAttribute('role', 'button');
    img.setAttribute('aria-label', `放大查看：${img.alt || '图片'}`);
  }

  function markAll() {
    document.querySelectorAll<HTMLImageElement>(SELECTOR).forEach((img) => {
      // 懒加载还没开始的图 complete 也可能是 true，但 naturalWidth 是 0，要等 load 事件
      if (img.complete && img.naturalWidth > 0) mark(img);
      else img.addEventListener('load', () => mark(img), { once: true });
    });
  }
  markAll();

  const gallery = () => [...document.querySelectorAll<HTMLImageElement>(`${SELECTOR}[data-qmx-zoom]`)];

  document.addEventListener('click', (e) => {
    const t = e.target;
    if (!(t instanceof HTMLImageElement) || !t.matches(`${SELECTOR}[data-qmx-zoom]`)) return;
    if (e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey) return;
    open(t);
  });
  document.addEventListener('keydown', (e) => {
    const t = e.target;
    if (!(t instanceof HTMLImageElement) || !t.matches(`${SELECTOR}[data-qmx-zoom]`)) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      open(t);
    }
  });

  // ───── 界面(第一次打开时才创建) ─────
  let root: HTMLDivElement;
  let stage: HTMLDivElement;
  let view: HTMLImageElement;
  let countEl: HTMLElement;
  let zoomEl: HTMLOutputElement;
  let captionEl: HTMLElement;
  let liveEl: HTMLElement;
  let openLink: HTMLAnchorElement;
  let prevBtn: HTMLButtonElement;
  let nextBtn: HTMLButtonElement;
  let built = false;

  function build() {
    if (built) return;
    built = true;
    root = document.createElement('div');
    root.className = 'qmx-lb';
    root.hidden = true;
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-label', '图片预览');
    root.innerHTML = `
      <div class="qmx-lb__backdrop"></div>
      <div class="qmx-lb__bar">
        <span class="qmx-lb__count" aria-hidden="true"></span>
        <span class="qmx-lb__tools">
          <button type="button" data-act="out" aria-label="缩小" title="缩小（-）">−</button>
          <output class="qmx-lb__zoom" aria-hidden="true">100%</output>
          <button type="button" data-act="in" aria-label="放大" title="放大（+）">+</button>
          <button type="button" data-act="fit" title="适应窗口（0）">适应</button>
          <button type="button" data-act="actual" title="原始大小（1）">1:1</button>
          <a data-act="open" target="_blank" rel="noopener" aria-label="在新标签页打开图片" title="在新标签页打开">${ICONS.open}</a>
          <button type="button" data-act="close" aria-label="关闭（Esc）" title="关闭（Esc）">${ICONS.close}</button>
        </span>
      </div>
      <div class="qmx-lb__stage"><img class="qmx-lb__img" alt="" draggable="false"></div>
      <button type="button" class="qmx-lb__nav qmx-lb__nav--prev" data-act="prev" aria-label="上一张" title="上一张（←）">${ICONS.prev}</button>
      <button type="button" class="qmx-lb__nav qmx-lb__nav--next" data-act="next" aria-label="下一张" title="下一张（→）">${ICONS.next}</button>
      <p class="qmx-lb__caption"></p>
      <div class="qmx-lb__live" aria-live="polite"></div>`;
    document.body.append(root);

    stage = root.querySelector('.qmx-lb__stage')!;
    view = root.querySelector('.qmx-lb__img')!;
    countEl = root.querySelector('.qmx-lb__count')!;
    zoomEl = root.querySelector('.qmx-lb__zoom')!;
    captionEl = root.querySelector('.qmx-lb__caption')!;
    liveEl = root.querySelector('.qmx-lb__live')!;
    openLink = root.querySelector('a[data-act="open"]')!;
    prevBtn = root.querySelector('[data-act="prev"]')!;
    nextBtn = root.querySelector('[data-act="next"]')!;

    root.addEventListener('click', onRootClick);
    stage.addEventListener('wheel', onWheel, { passive: false });
    stage.addEventListener('pointerdown', onPointerDown);
    stage.addEventListener('pointermove', onPointerMove);
    stage.addEventListener('pointerup', onPointerUp);
    stage.addEventListener('pointercancel', onPointerUp);
    stage.addEventListener('dblclick', onDoubleClick);
    window.addEventListener('resize', onResize);
    view.addEventListener('load', onViewLoad);
    view.addEventListener('error', onViewError);
  }

  // ───── 状态 ─────
  let items: HTMLImageElement[] = [];
  let index = 0;
  let isOpen = false;
  let opener: HTMLElement | null = null;
  let nw = 1;
  let nh = 1;
  let fit = 1;
  let limits = { min: 1, max: 4 };
  let t: Transform = { s: 1, x: 0, y: 0 };
  let loadToken = 0;
  let loadHandled = false;
  let svgLike = false;
  let inerted: { el: Element; had: boolean }[] = [];
  let pendingEnter: { rect: DOMRect } | null = null;
  let svgSizing: Promise<{ w: number; h: number } | null> | null = null;

  const pointers = new Map<number, Pointer>();
  let pressedOnBlank = false; // 按下时点的是舞台空白处，而不是图片(指针捕获后 pointerup 的 target 恒为舞台，所以要自己记)
  let dragMoved = 0;
  let pinch: { dist: number; s: number } | null = null;
  let swipeStart: { x: number; y: number } | null = null;

  const stageSize = () => ({ w: stage.clientWidth, h: stage.clientHeight });
  const stageRect = () => stage.getBoundingClientRect();

  function apply(next: Transform, animate = false) {
    t = next;
    view.classList.toggle('is-animating', animate && !reduced());
    view.style.transform = `translate3d(${t.x.toFixed(2)}px, ${t.y.toFixed(2)}px, 0) scale(${t.s})`;
    zoomEl.textContent = percent(t.s);
    root.classList.toggle('is-zoomed', t.s > fit * 1.02);
  }

  function setLimits() {
    const { w, h } = stageSize();
    // 多图时两侧要躲开翻页按钮(桌面 48px + 间距，手机 40px)，单图只留普通边距
    const side = items.length > 1 ? (w < 640 ? 52 : 72) : 24;
    fit = fitScale(nw, nh, w, h, { cap: svgLike ? Infinity : 1, padX: side });
    limits = scaleLimits(fit);
  }

  // ───── 打开 / 关闭 ─────
  function open(img: HTMLImageElement) {
    build();
    items = gallery();
    index = Math.max(0, items.indexOf(img));
    opener = img;
    isOpen = true;

    root.hidden = false;
    root.classList.remove('is-closing');
    // 背景设为 inert，键盘 / 读屏不会跑到预览后面去
    inerted = [...document.body.children]
      .filter((el) => el !== root)
      .map((el) => ({ el, had: el.hasAttribute('inert') }));
    inerted.forEach(({ el }) => el.setAttribute('inert', ''));

    document.addEventListener('keydown', onKey, true);
    show(index, true);
    requestAnimationFrame(() => root.classList.add('is-open'));
    (root.querySelector('[data-act="close"]') as HTMLElement).focus({ preventScroll: true });
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    document.removeEventListener('keydown', onKey, true);
    pointers.clear();
    pinch = null;

    const thumb = items[index];
    const rect = thumb?.isConnected ? thumb.getBoundingClientRect() : null;
    const fly = !!rect && rectVisible(rect, innerWidth, innerHeight) && !reduced() && nw > 1;
    root.classList.add('is-closing');
    root.classList.remove('is-open');
    if (fly && rect) apply(thumbTransform(rect, stageRect(), nw), true);

    const done = () => {
      root.hidden = true;
      root.classList.remove('is-closing', 'is-zoomed');
      view.removeAttribute('src');
      inerted.forEach(({ el, had }) => { if (!had) el.removeAttribute('inert'); });
      inerted = [];
      const back = opener && opener.isConnected ? opener : thumb;
      back?.focus({ preventScroll: true });
      opener = null;
    };
    if (reduced()) done();
    else setTimeout(done, fly ? 240 : 180);
  }

  // ───── 显示第 i 张 ─────
  function show(i: number, first = false) {
    index = i;
    const img = items[i];
    const token = ++loadToken;
    loadHandled = false;
    const src = img.currentSrc || img.src;

    svgLike = /\.svg(\?|#|$)/i.test(src);
    root.classList.remove('is-error');
    root.classList.add('is-loading');
    countEl.textContent = items.length > 1 ? `${i + 1} / ${items.length}` : '';
    prevBtn.hidden = nextBtn.hidden = items.length < 2;
    captionEl.textContent = img.alt || '';
    captionEl.hidden = !img.alt;
    openLink.href = src;
    liveEl.textContent = `${img.alt || '图片'}${items.length > 1 ? `，第 ${i + 1} 张，共 ${items.length} 张` : ''}`;

    // 缩略图已经加载好时，尺寸立刻可用，打开动画不用等
    nw = img.naturalWidth || 1;
    nh = img.naturalHeight || 1;
    pendingEnter = first ? { rect: img.getBoundingClientRect() } : null;
    // 只给 viewBox 的 SVG，浏览器报告的 naturalWidth 是按默认 300×150 套比例算出来的假尺寸，
    // 要读 SVG 自己声明的尺寸，不然「100%」和放大后的清晰度都不对
    svgSizing = svgLike ? readSvgSize(src) : null;

    view.style.width = `${nw}px`;
    view.style.height = `${nh}px`;
    view.alt = img.alt;
    view.dataset.token = String(token);
    view.src = src;
    if (view.complete && view.naturalWidth) onViewLoad();
  }

  async function onViewLoad() {
    // 缓存命中时 show() 已经处理过一次，随后 load 事件还会再来一次，要跳过，否则会重置用户刚做的缩放
    if (!isOpen || loadHandled) return;
    loadHandled = true;
    const token = loadToken;
    nw = view.naturalWidth || nw;
    nh = view.naturalHeight || nh;
    if (svgSizing) {
      const real = await svgSizing;
      if (!isOpen || token !== loadToken) return; // 等待期间用户已经翻页或关闭
      if (real) {
        nw = real.w;
        nh = real.h;
      }
    }
    root.classList.remove('is-loading');
    view.style.width = `${nw}px`;
    view.style.height = `${nh}px`;
    setLimits();
    const home = centered(fit, nw, nh, stageSize().w, stageSize().h);

    const enter = pendingEnter;
    pendingEnter = null;
    if (enter && rectVisible(enter.rect, innerWidth, innerHeight) && !reduced()) {
      // 飞入：先把图片摆在缩略图的位置，下一帧再过渡到「适应窗口」
      apply(thumbTransform(enter.rect, stageRect(), nw), false);
      view.getBoundingClientRect(); // 强制重排，让起点生效
      apply(home, true);
    } else {
      apply(home, false);
    }
  }

  function onViewError() {
    if (!isOpen) return;
    root.classList.remove('is-loading');
    root.classList.add('is-error');
    captionEl.hidden = false;
    captionEl.textContent = '图片加载失败，可以点右上角的箭头在新标签页打开';
  }

  function go(dir: number) {
    if (items.length < 2) return;
    root.classList.add('is-swapping');
    show(nextIndex(index, items.length, dir));
    setTimeout(() => root.classList.remove('is-swapping'), 160);
  }

  // ───── 缩放 / 平移 ─────
  function zoomTo(s: number, cx?: number, cy?: number, animate = false) {
    const { w, h } = stageSize();
    apply(zoomAt(t, s, cx ?? w / 2, cy ?? h / 2, limits, nw, nh, w, h), animate);
  }

  function onWheel(e: WheelEvent) {
    e.preventDefault(); // 预览打开时，滚轮只用来缩放，不让页面在后面滚动
    const r = stageRect();
    zoomTo(t.s * wheelFactor(e.deltaY, e.deltaMode, e.ctrlKey), e.clientX - r.left, e.clientY - r.top);
  }

  function onPointerDown(e: PointerEvent) {
    if (e.button !== 0 && e.pointerType === 'mouse') return;
    stage.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 1) {
      dragMoved = 0;
      pressedOnBlank = e.target === stage;
      swipeStart = { x: e.clientX, y: e.clientY };
    } else if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { dist: Math.hypot(a.x - b.x, a.y - b.y) || 1, s: t.s };
      swipeStart = null;
    }
  }

  function onPointerMove(e: PointerEvent) {
    const prev = pointers.get(e.pointerId);
    if (!prev) return;
    const cur = { x: e.clientX, y: e.clientY };
    pointers.set(e.pointerId, cur);
    const { w, h } = stageSize();
    const r = stageRect();

    if (pointers.size >= 2 && pinch) {
      const [a, b] = [...pointers.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y) || 1;
      zoomTo(pinch.s * (dist / pinch.dist), (a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top);
      dragMoved = 99;
      return;
    }
    const dx = cur.x - prev.x;
    const dy = cur.y - prev.y;
    dragMoved += Math.abs(dx) + Math.abs(dy);
    if (dragMoved > 3) {
      view.classList.add('is-dragging');
      apply(panBy(t, dx, dy, nw, nh, w, h));
    }
  }

  function onPointerUp(e: PointerEvent) {
    if (!pointers.has(e.pointerId)) return;
    const wasSingle = pointers.size === 1;
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (pointers.size === 0) view.classList.remove('is-dragging');

    if (wasSingle && swipeStart) {
      const dx = e.clientX - swipeStart.x;
      const dy = e.clientY - swipeStart.y;
      // 没有放大时，横向滑动 = 翻页
      if (e.pointerType === 'touch' && t.s <= fit * 1.02 && isSwipe(dx, dy)) go(dx < 0 ? 1 : -1);
      // 点在图片外的空白处(没有拖动)：关闭
      else if (dragMoved <= 3 && pressedOnBlank) close();
    }
    swipeStart = null;
  }

  function onDoubleClick(e: MouseEvent) {
    const r = stageRect();
    zoomTo(doubleTapTarget(t.s, fit, limits.max), e.clientX - r.left, e.clientY - r.top, true);
  }

  function onResize() {
    if (!isOpen) return;
    const wasFit = t.s <= fit * 1.02;
    setLimits();
    const { w, h } = stageSize();
    apply(wasFit ? centered(fit, nw, nh, w, h) : clampPan({ ...t, s: clamp(t.s, limits.min, limits.max) }, nw, nh, w, h));
  }

  // ───── 按钮、键盘 ─────
  function onRootClick(e: MouseEvent) {
    const target = e.target as Element;
    const act = target.closest('[data-act]')?.getAttribute('data-act');
    if (act === 'close') close();
    else if (act === 'in') zoomTo(t.s * 1.5, undefined, undefined, true);
    else if (act === 'out') zoomTo(t.s / 1.5, undefined, undefined, true);
    else if (act === 'fit') zoomTo(fit, undefined, undefined, true);
    else if (act === 'actual') zoomTo(clamp(1, limits.min, limits.max), undefined, undefined, true);
    else if (act === 'prev') go(-1);
    else if (act === 'next') go(1);
    else if (target.classList.contains('qmx-lb__backdrop')) close();
  }

  function onKey(e: KeyboardEvent) {
    if (!isOpen) return;
    const zoomed = t.s > fit * 1.02;
    const step = 90;
    const { w, h } = stageSize();
    const pan = (dx: number, dy: number) => apply(panBy(t, dx, dy, nw, nh, w, h));
    let handled = true;

    switch (e.key) {
      case 'Escape': close(); break;
      case 'ArrowLeft': zoomed ? pan(step, 0) : go(-1); break;
      case 'ArrowRight': zoomed ? pan(-step, 0) : go(1); break;
      case 'ArrowUp': if (zoomed) pan(0, step); else handled = false; break;
      case 'ArrowDown': if (zoomed) pan(0, -step); else handled = false; break;
      case 'PageUp': go(-1); break;
      case 'PageDown': go(1); break;
      case '+': case '=': zoomTo(t.s * 1.5, undefined, undefined, true); break;
      case '-': case '_': zoomTo(t.s / 1.5, undefined, undefined, true); break;
      case '0': zoomTo(fit, undefined, undefined, true); break;
      case '1': zoomTo(clamp(1, limits.min, limits.max), undefined, undefined, true); break;
      case 'Tab': {
        // 焦点不离开对话框
        const list = [...root.querySelectorAll<HTMLElement>('button:not([hidden]), a[href]')];
        const i = list.indexOf(document.activeElement as HTMLElement);
        const n = list.length;
        const to = list[(i + (e.shiftKey ? -1 : 1) + n) % n];
        to?.focus();
        break;
      }
      case ' ': case 'Enter':
        // 空格 / 回车用于按下当前聚焦的按钮，其余情况不拦截
        handled = false;
        break;
      default: handled = false;
    }
    if (handled) {
      e.preventDefault();
      e.stopImmediatePropagation(); // 别让「划词问 AI」等其他快捷键同时响应 Esc
    }
  }
}
