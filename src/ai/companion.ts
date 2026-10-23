// AI 助手的鲸鱼形象：右下角常驻的桌宠，加上回答面板里的头像。
// 两者共用同一张图集和同一个「心情」，心情跟着请求的进度变化（思考 → 回答 → 完成 / 出错）。
//
// 图集来源，按优先级：
//   1. 用户在设置里导入的文件（只保存在本机浏览器的 IndexedDB，不会上传）；
//   2. 站点自带的 public/ai-pet/spritesheet.webp；
//   3. 内置的简易 SVG 小鲸鱼（前两者都没有时）。
import { MOODS, CELL_W, CELL_H, frameAt, framePosition, isValidSheet } from './sprite.mjs';

export type Mood = 'idle' | 'thinking' | 'talking' | 'happy' | 'sad' | 'sleep' | 'wave' | 'runRight' | 'runLeft';

const PET_KEY = 'qmx-ai-pet';
const POS_KEY = 'qmx-ai-pet-pos';
const SLEEP_AFTER = 120_000;

const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const compact = matchMedia('(max-width: 50rem), (pointer: coarse)');

// ---------- 图集存取 ----------
const DB = 'qmx-ai';
function idb<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>): Promise<T | undefined> {
  return new Promise((resolve) => {
    try {
      const open = indexedDB.open(DB, 1);
      open.onupgradeneeded = () => open.result.createObjectStore('kv');
      open.onerror = () => resolve(undefined);
      open.onsuccess = () => {
        const db = open.result;
        const req = run(db.transaction('kv', mode).objectStore('kv'));
        req.onsuccess = () => { resolve(req.result); db.close(); };
        req.onerror = () => { resolve(undefined); db.close(); };
      };
    } catch {
      resolve(undefined); // 隐私模式等场景下 IndexedDB 不可用
    }
  });
}

let sheetUrl: string | null = null;
let ownUrl = false; // 是 blob: 地址时，换图前要释放
const views = new Set<SpriteView>();

function probe(url: string): Promise<boolean> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(isValidSheet(img.naturalWidth, img.naturalHeight));
    img.onerror = () => resolve(false);
    img.src = url;
  });
}

function useSheet(url: string | null, blob: boolean) {
  if (ownUrl && sheetUrl) URL.revokeObjectURL(sheetUrl);
  sheetUrl = url;
  ownUrl = blob;
  const root = document.documentElement;
  if (url) {
    root.dataset.qmxWhale = '1';
    root.style.setProperty('--qmx-whale-sheet', `url("${url}")`);
  } else {
    delete root.dataset.qmxWhale;
    root.style.removeProperty('--qmx-whale-sheet');
  }
  views.forEach((v) => v.refreshSheet());
}

export async function loadSheet(base: string) {
  const saved = await idb<Blob>('readonly', (s) => s.get('sheet') as IDBRequest<Blob>);
  if (saved instanceof Blob) {
    const url = URL.createObjectURL(saved);
    if (await probe(url)) { useSheet(url, true); return; }
    URL.revokeObjectURL(url);
  }
  const bundled = `${base}ai-pet/spritesheet.webp`;
  useSheet((await probe(bundled)) ? bundled : null, false);
}

export async function importSheet(file: File): Promise<string> {
  if (!/^image\/(webp|png)$/.test(file.type)) return '请选择 webp 或 png 图集。';
  if (file.size > 12 * 1024 * 1024) return '文件超过 12 MB，请压缩后再导入。';
  const url = URL.createObjectURL(file);
  const ok = await probe(url);
  if (!ok) {
    URL.revokeObjectURL(url);
    return '图集尺寸不对：需要 8 列 × 11 行的版式（单格 192×208，宽高比约 1536:2288）。';
  }
  await idb('readwrite', (s) => s.put(file, 'sheet'));
  useSheet(url, true);
  return '已导入，图集只保存在这台设备的浏览器里。';
}

export async function resetSheet(base: string) {
  await idb('readwrite', (s) => s.delete('sheet'));
  await loadSheet(base);
}

// ---------- 单个形象：按心情播放图集里的一行 ----------
function fallbackSvg(): SVGSVGElement {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 96 104');
  svg.setAttribute('aria-hidden', 'true');
  const part = (tag: string, attrs: Record<string, string>) => {
    const n = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    svg.appendChild(n);
  };
  part('path', { d: 'M70 62c10-4 18-12 20-24-12 2-20 8-24 16z', fill: '#2563eb' }); // 尾巴
  part('ellipse', { cx: '44', cy: '62', rx: '34', ry: '28', fill: '#3b82f6' }); // 身体
  part('ellipse', { cx: '40', cy: '72', rx: '24', ry: '14', fill: '#dbeafe' }); // 肚皮
  part('circle', { cx: '30', cy: '56', r: '4', fill: '#0b1b33' }); // 眼睛
  part('circle', { cx: '31.2', cy: '54.8', r: '1.4', fill: '#fff' });
  part('path', { d: 'M44 30c0-8 4-12 8-14M44 30c-2-6-6-8-10-8', stroke: '#93c5fd', 'stroke-width': '3', fill: 'none', 'stroke-linecap': 'round' }); // 喷水
  return svg;
}

export class SpriteView {
  readonly el = document.createElement('div');
  private mood: Mood = 'idle';
  private since = performance.now();
  private last = -1;
  private fallback: SVGSVGElement | null = null;

  constructor(private scale: number) {
    this.el.className = 'qmx-sprite';
    this.el.setAttribute('aria-hidden', 'true');
    views.add(this);
    this.refreshSheet();
  }

  destroy() { views.delete(this); this.el.remove(); }

  setScale(scale: number) { this.scale = scale; this.last = -1; this.refreshSheet(); }

  setMood(mood: Mood) {
    if (mood === this.mood) return;
    this.mood = mood;
    this.since = performance.now();
    this.last = -1;
    this.el.dataset.mood = mood;
    this.render(this.since);
  }

  refreshSheet() {
    const { w, h } = framePosition('idle', 0, this.scale);
    this.el.style.width = `${w}px`;
    this.el.style.height = `${h}px`;
    this.last = -1;
    if (sheetUrl) {
      this.fallback?.remove();
      this.fallback = null;
      this.el.style.backgroundImage = `url("${sheetUrl}")`;
      this.el.classList.remove('qmx-sprite--fallback');
    } else {
      this.el.style.backgroundImage = 'none';
      this.el.classList.add('qmx-sprite--fallback');
      if (!this.fallback) this.el.appendChild((this.fallback = fallbackSvg()));
    }
    this.render(performance.now());
  }

  render(now: number) {
    if (!sheetUrl) return;
    const m = MOODS[this.mood];
    const frame = reduced.matches ? m.still : frameAt(this.mood, now - this.since);
    if (frame === this.last) return;
    this.last = frame;
    const p = framePosition(this.mood, frame, this.scale);
    this.el.style.backgroundSize = `${p.sheetW}px ${p.sheetH}px`;
    this.el.style.backgroundPosition = `${p.x}px ${p.y}px`;
  }
}

// 所有形象共用一个定时器；标签页隐藏时不转。
setInterval(() => {
  if (document.hidden || reduced.matches) return;
  const now = performance.now();
  views.forEach((v) => v.render(now));
}, 60);

// ---------- 心情：桌宠和面板头像一起变 ----------
let avatar: SpriteView | null = null;
let pet: SpriteView | null = null;
let currentMood: Mood = 'idle';
let moodTimer = 0;
let sleepTimer = 0;

function applyMood(mood: Mood) {
  currentMood = mood;
  pet?.setMood(mood);
  avatar?.setMood(mood);
}

/** 切换心情。holdMs > 0 时到点自动回到待机（用于「完成」「出错」这类一次性表情）。 */
export function setMood(mood: Mood, holdMs = 0) {
  clearTimeout(moodTimer);
  applyMood(mood);
  if (holdMs > 0) moodTimer = window.setTimeout(() => applyMood('idle'), holdMs);
  poke();
}

/** 有用户活动：重新计时，睡着了就醒来挥个手。 */
export function poke() {
  clearTimeout(sleepTimer);
  if (currentMood === 'sleep') setMood('wave', 1200);
  sleepTimer = window.setTimeout(() => {
    if (currentMood === 'idle') applyMood('sleep');
  }, SLEEP_AFTER);
}

export function makeAvatar(): HTMLElement {
  avatar?.destroy();
  avatar = new SpriteView(0.3);
  avatar.setMood(currentMood);
  return avatar.el;
}

// ---------- 桌宠本体 ----------
let petBtn: HTMLButtonElement | null = null;
let bubble: HTMLElement | null = null;
let bubbleTimer = 0;

export function isPetEnabled(): boolean {
  try { return localStorage.getItem(PET_KEY) !== 'off'; } catch { return true; }
}

export function say(text: string, ms = 3200) {
  if (!bubble || !petBtn || petBtn.hidden) return;
  bubble.textContent = text;
  bubble.hidden = false;
  clearTimeout(bubbleTimer);
  bubbleTimer = window.setTimeout(() => { if (bubble) bubble.hidden = true; }, ms);
}

export function petRect(): DOMRect | null {
  return petBtn && !petBtn.hidden ? petBtn.getBoundingClientRect() : null;
}

function petScale() { return compact.matches ? 0.4 : 0.55; }

type Pos = { x: number; y: number };
function loadPos(): Pos | null {
  try {
    const p = JSON.parse(localStorage.getItem(POS_KEY) ?? 'null');
    return p && Number.isFinite(p.x) && Number.isFinite(p.y) ? { x: Math.min(1, Math.max(0, p.x)), y: Math.min(1, Math.max(0, p.y)) } : null;
  } catch { return null; }
}

function placePet(pos: Pos | null) {
  if (!petBtn) return;
  if (!pos) { petBtn.style.left = petBtn.style.top = ''; petBtn.classList.remove('is-placed'); return; }
  const w = petBtn.offsetWidth || CELL_W * petScale();
  const h = petBtn.offsetHeight || CELL_H * petScale();
  petBtn.classList.add('is-placed');
  petBtn.style.left = `${pos.x * Math.max(0, window.innerWidth - w)}px`;
  petBtn.style.top = `${pos.y * Math.max(0, window.innerHeight - h)}px`;
}

export function setPetEnabled(on: boolean) {
  try { localStorage.setItem(PET_KEY, on ? 'on' : 'off'); } catch { /* 隐私模式下忽略 */ }
  if (petBtn) petBtn.hidden = !on;
  if (!on && bubble) bubble.hidden = true;
  if (on) poke();
}

export function initPet(onOpen: () => void) {
  if (petBtn) return;
  pet = new SpriteView(petScale());
  pet.setMood(currentMood);

  petBtn = document.createElement('button');
  petBtn.type = 'button';
  petBtn.className = 'qmx-pet';
  petBtn.setAttribute('aria-label', '打开 AI 助手');
  petBtn.title = '点我提问，也可以拖动';
  petBtn.hidden = !isPetEnabled();
  petBtn.appendChild(pet.el);

  bubble = document.createElement('div');
  bubble.className = 'qmx-pet-bubble';
  bubble.setAttribute('aria-hidden', 'true');
  bubble.hidden = true;
  document.body.append(petBtn, bubble);

  // 气泡跟着桌宠走
  const followBubble = () => {
    if (!bubble || !petBtn) return;
    const r = petBtn.getBoundingClientRect();
    bubble.style.left = `${Math.min(Math.max(8, r.left + r.width / 2), window.innerWidth - 8)}px`;
    bubble.style.top = `${Math.max(8, r.top - 6)}px`;
  };
  new MutationObserver(followBubble).observe(bubble, { attributes: true, attributeFilter: ['hidden'] });

  // 点击 / 拖动：移动超过 5px 才算拖动，拖动时按方向切换跑步动作
  let drag: { sx: number; sy: number; ox: number; oy: number; moved: boolean } | null = null;
  let swallowClick = false;
  petBtn.addEventListener('pointerdown', (e) => {
    if (e.button !== 0 || !petBtn) return;
    const r = petBtn.getBoundingClientRect();
    drag = { sx: e.clientX, sy: e.clientY, ox: r.left, oy: r.top, moved: false };
    petBtn.setPointerCapture(e.pointerId);
  });
  petBtn.addEventListener('pointermove', (e) => {
    if (!drag || !petBtn) return;
    const dx = e.clientX - drag.sx;
    const dy = e.clientY - drag.sy;
    if (!drag.moved && Math.hypot(dx, dy) < 5) return;
    if (!drag.moved) { drag.moved = true; if (bubble) bubble.hidden = true; }
    const w = petBtn.offsetWidth;
    const h = petBtn.offsetHeight;
    const x = Math.min(Math.max(0, drag.ox + dx), window.innerWidth - w);
    const y = Math.min(Math.max(0, drag.oy + dy), window.innerHeight - h);
    petBtn.classList.add('is-placed');
    petBtn.style.left = `${x}px`;
    petBtn.style.top = `${y}px`;
    applyMood(dx >= 0 ? 'runRight' : 'runLeft');
  });
  const end = (e: PointerEvent) => {
    if (!drag || !petBtn) return;
    const moved = drag.moved;
    drag = null;
    if (petBtn.hasPointerCapture(e.pointerId)) petBtn.releasePointerCapture(e.pointerId);
    if (moved) {
      const r = petBtn.getBoundingClientRect();
      const pos = {
        x: r.left / Math.max(1, window.innerWidth - r.width),
        y: r.top / Math.max(1, window.innerHeight - r.height),
      };
      try { localStorage.setItem(POS_KEY, JSON.stringify(pos)); } catch { /* 忽略 */ }
      setMood('idle');
    } else if (e.type === 'pointerup') {
      swallowClick = true; // 紧跟着会触发 click，避免重复打开
      setMood('wave', 1200);
      onOpen();
    }
  };
  petBtn.addEventListener('pointerup', end);
  petBtn.addEventListener('pointercancel', end);
  petBtn.addEventListener('click', () => {
    if (swallowClick) { swallowClick = false; return; }
    setMood('wave', 1200); // 键盘 Enter / 空格
    onOpen();
  });

  window.addEventListener('resize', () => placePet(loadPos()));
  compact.addEventListener('change', () => { pet?.setScale(petScale()); placePet(loadPos()); });
  for (const type of ['pointerdown', 'keydown', 'wheel'] as const) {
    window.addEventListener(type, poke, { passive: true });
  }

  placePet(loadPos());
  if (isPetEnabled()) {
    poke();
    // 每个会话只在第一次打招呼，别每翻一页都跳出来
    try {
      if (!sessionStorage.getItem('qmx-ai-pet-hi')) {
        sessionStorage.setItem('qmx-ai-pet-hi', '1');
        setTimeout(() => { setMood('wave', 1500); say('划词就能问我哦'); followBubble(); }, 1200);
      }
    } catch { /* 忽略 */ }
  }
}
