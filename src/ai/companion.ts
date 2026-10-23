// AI 助手的鲸鱼形象：右下角常驻的桌宠。回答的气泡由 chat-ui.ts 画在它的上方。
//
// 动画来自一个「动作包」（见 sprite.mjs）：每个动作是一张精灵图，按需下载，一次只播一个。
// 状态分两层：
//   base   一直在做的事（待机、思考、回答、睡觉……），由请求的进度决定；
//   react  播一遍就回到 base 的反应（开心、难过、被戳、偶尔的小动作……）。
// 包的来源，按优先级：用户导入的 8×11 图集（只存在本机浏览器）→ 站点自带的 public/ai-pet/pack.json → 内置的简易 SVG。
/* eslint-disable @typescript-eslint/no-explicit-any */
import {
  clipFrame, framePosition, pickClip, pickExtra, validatePack, legacyPack, isValidSheet, isLoopMood,
} from './sprite.mjs';

export type Mood =
  | 'idle' | 'thinking' | 'talking' | 'sleep' | 'drag' | 'waiting'
  | 'happy' | 'sad' | 'wave' | 'wake' | 'scare' | 'poke';

const PET_KEY = 'qmx-ai-pet';
const POS_KEY = 'qmx-ai-pet-pos';
const SLEEP_AFTER = 150_000;

const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const compact = matchMedia('(max-width: 50rem), (pointer: coarse)');

// ---------- 存取：用户导入的图集放在 IndexedDB ----------
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

// ---------- 动作包 ----------
let pack: any = null;
let packBase = '/';
let ownBlobUrl: string | null = null; // 导入图集的 blob: 地址，换包时要释放
const views = new Set<SpriteView>();

const clipUrl = (clip: any) => new URL(clip.src, packBase).href;
const stillUrl = () => (pack?.still ? new URL(pack.still, packBase).href : null);

function probeSize(url: string): Promise<[number, number] | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve([img.naturalWidth, img.naturalHeight]);
    img.onerror = () => resolve(null);
    img.src = url;
  });
}

// 已下载并解码的图集。每张解码后有几十 MB，所以只留最近用过的几张，别的交给浏览器回收。
const held = new Map<string, HTMLImageElement>();
const loading = new Map<string, Promise<boolean>>();
const KEEP = 4;

function loadSheet(url: string): Promise<boolean> {
  const done = held.get(url);
  if (done) { held.delete(url); held.set(url, done); return Promise.resolve(true); } // 刷新「最近使用」
  let p = loading.get(url);
  if (!p) {
    p = new Promise<boolean>((resolve) => {
      const img = new Image();
      img.decoding = 'async';
      img.onload = () => {
        const finish = () => {
          held.set(url, img);
          loading.delete(url);
          const inUse = new Set([...views].map((v) => v.url));
          for (const key of [...held.keys()]) {
            if (held.size <= KEEP) break;
            if (!inUse.has(key)) held.delete(key);
          }
          resolve(true);
        };
        (img.decode ? img.decode() : Promise.resolve()).then(finish, finish);
      };
      img.onerror = () => { loading.delete(url); resolve(false); };
      img.src = url;
    });
    loading.set(url, p);
  }
  return p;
}

function setPack(next: any, base: string, blobUrl: string | null) {
  if (ownBlobUrl && ownBlobUrl !== blobUrl) URL.revokeObjectURL(ownBlobUrl);
  ownBlobUrl = blobUrl;
  pack = next;
  packBase = base;
  held.clear();
  const root = document.documentElement;
  const still = stillUrl();
  if (still) { root.dataset.qmxWhale = '1'; root.style.setProperty('--qmx-whale-still', `url("${still}")`); }
  else { delete root.dataset.qmxWhale; root.style.removeProperty('--qmx-whale-still'); }
  views.forEach((v) => v.reset());
  restart();
}

/** 读取用户导入的图集，没有就读站点自带的包；都没有就用内置的 SVG。 */
export async function loadPack(base: string) {
  const saved = await idb<Blob>('readonly', (s) => s.get('sheet') as IDBRequest<Blob>);
  if (saved instanceof Blob) {
    const url = URL.createObjectURL(saved);
    const size = await probeSize(url);
    if (size && isValidSheet(size[0], size[1])) { setPack(legacyPack(url), location.href, url); return; }
    URL.revokeObjectURL(url);
  }
  const root = `${base}ai-pet/`;
  try {
    const res = await fetch(`${root}pack.json`);
    const checked = res.ok ? validatePack(await res.json()) : null;
    if (checked) { setPack(checked, new URL(root, location.href).href, null); return; }
  } catch { /* 离线或没有这个文件：用内置形象 */ }
  setPack(null, root, null);
}

export async function importSheet(file: File): Promise<string> {
  if (!/^image\/(webp|png)$/.test(file.type)) return '请选择 webp 或 png 图集。';
  if (file.size > 12 * 1024 * 1024) return '文件超过 12 MB，请压缩后再导入。';
  const url = URL.createObjectURL(file);
  const size = await probeSize(url);
  if (!size || !isValidSheet(size[0], size[1])) {
    URL.revokeObjectURL(url);
    return '图集尺寸不对：需要 8 列 × 11 行的版式（单格 192×208，宽高比约 1536:2288）。';
  }
  await idb('readwrite', (s) => s.put(file, 'sheet'));
  setPack(legacyPack(url), location.href, url);
  return '已导入，图集只保存在这台设备的浏览器里。';
}

export async function resetSheet(base: string) {
  await idb('readwrite', (s) => s.delete('sheet'));
  await loadPack(base);
}

// ---------- 单个形象：按当前动作播放图集里的帧 ----------
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

class SpriteView {
  readonly el = document.createElement('div');
  url = ''; // 当前背景用的图集地址
  private clip: any = null;
  private once = false;
  private t0 = 0;
  private last = -1;
  private token = 0;
  private fallback: SVGSVGElement | null = null;
  private done: (() => void) | null = null;

  constructor(private scale: number) {
    this.el.className = 'qmx-sprite';
    this.el.setAttribute('aria-hidden', 'true');
    views.add(this);
    this.reset();
  }

  destroy() { views.delete(this); this.el.remove(); }
  setScale(scale: number) { this.scale = scale; this.reset(); }

  /** 换包或换大小之后：先显示静止画面，动作由控制器重新指定。 */
  reset() {
    this.token++;
    this.clip = null;
    this.url = '';
    this.done = null;
    this.last = -1;
    const cell = pack?.cell ?? [200, 175];
    this.el.style.width = `${cell[0] * this.scale}px`;
    this.el.style.height = `${cell[1] * this.scale}px`;
    this.el.classList.toggle('qmx-sprite--fallback', !pack);
    if (!pack) {
      this.el.style.backgroundImage = 'none';
      if (!this.fallback) this.el.appendChild((this.fallback = fallbackSvg()));
      return;
    }
    this.fallback?.remove();
    this.fallback = null;
    const still = stillUrl();
    if (still) {
      this.el.style.backgroundImage = `url("${still}")`;
      this.el.style.backgroundSize = `${cell[0] * this.scale}px ${cell[1] * this.scale}px`;
      this.el.style.backgroundPosition = '0 0';
    }
  }

  private view: any = null;

  /** 播放一个动作。图集还没下载好时先继续显示现在的画面，下载好再切过去。once：循环动作也只播一遍。 */
  async play(id: string, opts: { once?: boolean; onDone?: () => void } = {}) {
    const clip = pack?.clips?.[id];
    if (!clip) return;
    const token = ++this.token;
    if (reduced.matches && stillUrl()) return; // 减少动态效果：只显示静止画面，连图集都不下载
    const url = clipUrl(clip);
    if (url !== this.url) {
      const ok = await loadSheet(url);
      if (token !== this.token || !ok) return;
      this.url = url;
      this.el.style.backgroundImage = `url("${url}")`;
    }
    this.clip = clip;
    this.view = opts.once ? { ...clip, loop: false } : clip;
    this.done = opts.onDone ?? null;
    this.t0 = performance.now();
    this.last = -1;
    this.render(this.t0);
  }

  render(now: number) {
    if (!this.clip) return;
    const { frame, done } = reduced.matches ? { frame: 0, done: false } : clipFrame(this.view, now - this.t0);
    if (frame !== this.last) {
      this.last = frame;
      const p = framePosition(this.clip, pack.cell, frame, this.scale);
      this.el.style.backgroundSize = `${p.sheetW}px ${p.sheetH}px`;
      this.el.style.backgroundPosition = `${p.x}px ${p.y}px`;
    }
    if (done && this.done) {
      const cb = this.done;
      this.done = null;
      cb();
    }
  }
}

// 所有形象共用一个绘制循环；标签页隐藏或「减少动态效果」时不转。帧没变就什么都不做。
let raf = 0;
function tick(now: number) {
  raf = requestAnimationFrame(tick);
  views.forEach((v) => v.render(now));
}
function startLoop() {
  if (!raf && views.size && !document.hidden && !reduced.matches) raf = requestAnimationFrame(tick);
}
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { cancelAnimationFrame(raf); raf = 0; } else startLoop();
});

// ---------- 控制器：base / react、待机小动作、睡觉 ----------
let pet: SpriteView | null = null;
let base: Mood = 'idle';
let override: Mood | null = null; // 拖动时临时覆盖 base
let reaction = 0; // 当前反应的序号：换了新的状态，旧反应播完后的回调就作废
let reactionUntil = 0; // 在这个时间之前认为还有反应在播，不插入小动作
const lastClip: Record<string, string | null> = {};
let lastExtra: string | null = null;
let extraTimer = 0;
let sleepTimer = 0;

const currentMood = (): Mood => override ?? base;

function playBase() {
  if (!pack || !pet) return;
  const mood = currentMood();
  const id = pickClip(pack, mood, lastClip[mood]);
  if (!id) return;
  lastClip[mood] = id;
  pet.play(id);
}

function playReaction(id: string) {
  const mine = ++reaction;
  reactionUntil = performance.now() + (pack.clips[id].frames / pack.clips[id].fps) * 1000 + 1500;
  pet?.play(id, { once: true, onDone: () => { if (reaction === mine) { reactionUntil = 0; playBase(); } } });
}

/** 一直在做的事。请求开始、回答中、睡觉等由调用方切换。 */
export function setBase(mood: Mood) {
  if (!isLoopMood(mood)) { react(mood); return; }
  base = mood;
  reaction++;
  reactionUntil = 0;
  playBase();
  schedule();
}

/** 播一遍就回到 base 的反应：开心、难过、被戳、打招呼…… */
export function react(mood: Mood) {
  if (!pack) return;
  const id = pickClip(pack, mood, lastClip[mood]);
  if (!id) return;
  lastClip[mood] = id;
  playReaction(id);
  schedule();
}

function hold(mood: Mood | null) {
  override = mood;
  reaction++;
  reactionUntil = 0;
  playBase();
}

/** 有用户活动：重新计时，睡着了就醒来。 */
export function activity() {
  if (base === 'sleep') setBase('idle');
  schedule();
}

function schedule() {
  clearTimeout(extraTimer);
  clearTimeout(sleepTimer);
  extraTimer = window.setTimeout(() => {
    if (pack && currentMood() === 'idle' && performance.now() > reactionUntil && !document.hidden && !reduced.matches) {
      const id = pickExtra(pack, lastExtra);
      if (id) { lastExtra = id; playReaction(id); }
    }
    schedule();
  }, 20_000 + Math.random() * 25_000);
  sleepTimer = window.setTimeout(() => {
    if (base === 'idle' && !override && performance.now() > reactionUntil && pack?.moods.sleep) setBase('sleep');
  }, SLEEP_AFTER);
}

function restart() {
  reaction++;
  reactionUntil = 0;
  for (const k of Object.keys(lastClip)) delete lastClip[k];
  playBase();
  startLoop();
  schedule();
}

// ---------- 桌宠本体 ----------
let petBtn: HTMLButtonElement | null = null;
let bubble: HTMLElement | null = null;
let bubbleTimer = 0;
let forced = false; // 对话打开时，即使用户关掉了常驻也要露面
let chatOpen = false;

export function isPetEnabled(): boolean {
  try { return localStorage.getItem(PET_KEY) !== 'off'; } catch { return true; }
}

function syncHidden() {
  if (petBtn) petBtn.hidden = !(isPetEnabled() || forced);
  if (bubble && petBtn?.hidden) bubble.hidden = true;
}

export function setPetEnabled(on: boolean) {
  try { localStorage.setItem(PET_KEY, on ? 'on' : 'off'); } catch { /* 隐私模式下忽略 */ }
  syncHidden();
  if (on) activity();
}

/** 对话打开时让桌宠露面（它是回答气泡的「说话人」）；关闭时按用户的常驻设置恢复。 */
export function setChatOpen(open: boolean) {
  chatOpen = open;
  forced = open;
  if (open && bubble) bubble.hidden = true;
  syncHidden();
}

export function say(text: string, ms = 3200) {
  if (!bubble || !petBtn || petBtn.hidden || chatOpen) return;
  bubble.textContent = text;
  bubble.hidden = false;
  clearTimeout(bubbleTimer);
  bubbleTimer = window.setTimeout(() => { if (bubble) bubble.hidden = true; }, ms);
}

export function petRect(): DOMRect | null {
  return petBtn && !petBtn.hidden ? petBtn.getBoundingClientRect() : null;
}

const petScale = () => (compact.matches ? 0.7 : 0.9);

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
  const w = petBtn.offsetWidth || 160;
  const h = petBtn.offsetHeight || 140;
  petBtn.classList.add('is-placed');
  petBtn.style.left = `${pos.x * Math.max(0, window.innerWidth - w)}px`;
  petBtn.style.top = `${pos.y * Math.max(0, window.innerHeight - h)}px`;
}

export function initPet(opts: { onOpen: () => void; isOpen: () => boolean }) {
  if (petBtn) return;
  pet = new SpriteView(petScale());

  petBtn = document.createElement('button');
  petBtn.type = 'button';
  petBtn.className = 'qmx-whale'; // 注意别叫 qmx-pet：那是主题桌宠（fx.css）用的类名，样式会互相污染
  petBtn.setAttribute('aria-label', '打开 AI 助手');
  petBtn.title = '点我提问，也可以拖动';
  petBtn.appendChild(pet.el);

  bubble = document.createElement('div');
  bubble.className = 'qmx-whale-say';
  bubble.setAttribute('aria-hidden', 'true');
  bubble.hidden = true;
  document.body.append(petBtn, bubble);
  syncHidden();

  // 气泡跟着桌宠走
  const followBubble = () => {
    if (!bubble || !petBtn) return;
    const r = petBtn.getBoundingClientRect();
    bubble.style.left = `${Math.min(Math.max(8, r.left + r.width / 2), window.innerWidth - 8)}px`;
    bubble.style.top = `${Math.max(8, r.top - 6)}px`;
  };
  new MutationObserver(followBubble).observe(bubble, { attributes: true, attributeFilter: ['hidden'] });

  // 点击 / 拖动：移动超过 5px 才算拖动，拖动时播放「悬空」动作
  let drag: { sx: number; sy: number; ox: number; oy: number; moved: boolean } | null = null;
  let swallowClick = false;
  const poked = () => {
    if (opts.isOpen()) react('poke'); // 对话已经开着：戳一下是互动
    else { react('wave'); opts.onOpen(); }
  };
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
    if (!drag.moved) { drag.moved = true; if (bubble) bubble.hidden = true; hold('drag'); }
    const x = Math.min(Math.max(0, drag.ox + dx), window.innerWidth - petBtn.offsetWidth);
    const y = Math.min(Math.max(0, drag.oy + dy), window.innerHeight - petBtn.offsetHeight);
    petBtn.classList.add('is-placed');
    petBtn.style.left = `${x}px`;
    petBtn.style.top = `${y}px`;
    window.dispatchEvent(new Event('qmx-pet-move'));
  });
  const end = (e: PointerEvent) => {
    if (!drag || !petBtn) return;
    const moved = drag.moved;
    drag = null;
    if (petBtn.hasPointerCapture(e.pointerId)) petBtn.releasePointerCapture(e.pointerId);
    if (moved) {
      const r = petBtn.getBoundingClientRect();
      const pos = { x: r.left / Math.max(1, window.innerWidth - r.width), y: r.top / Math.max(1, window.innerHeight - r.height) };
      try { localStorage.setItem(POS_KEY, JSON.stringify(pos)); } catch { /* 忽略 */ }
      hold(null);
    } else if (e.type === 'pointerup') {
      swallowClick = true; // 紧跟着会触发 click，避免重复处理
      poked();
    }
  };
  petBtn.addEventListener('pointerup', end);
  petBtn.addEventListener('pointercancel', end);
  petBtn.addEventListener('click', () => {
    if (swallowClick) { swallowClick = false; return; }
    poked(); // 键盘 Enter / 空格
  });

  window.addEventListener('resize', () => { placePet(loadPos()); window.dispatchEvent(new Event('qmx-pet-move')); });
  compact.addEventListener('change', () => { pet?.setScale(petScale()); placePet(loadPos()); });
  for (const type of ['pointerdown', 'keydown', 'wheel'] as const) {
    window.addEventListener(type, activity, { passive: true });
  }

  placePet(loadPos());
  playBase(); // 包可能在桌宠创建之前就加载好了
  startLoop();
  schedule();
  if (isPetEnabled()) {
    // 每个会话只在第一次打招呼，别每翻一页都跳出来
    try {
      if (!sessionStorage.getItem('qmx-ai-pet-hi')) {
        sessionStorage.setItem('qmx-ai-pet-hi', '1');
        // 只说一句话，不播打招呼的动作：那个动作的图集有 1 MB，不值得为了一句问候在首页就去下载
        setTimeout(() => { say('划词就能问我哦'); followBubble(); }, 1200);
      }
    } catch { /* 忽略 */ }
  }
}
