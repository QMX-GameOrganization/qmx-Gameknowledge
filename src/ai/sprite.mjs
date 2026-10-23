// 鲸鱼形象的「动作包」与帧计算，纯逻辑，可以直接在 node 里测试。
//
// 一个包（pack）是一份清单，描述若干动作（clip）：每个动作是一张精灵图，帧按行优先排成网格。
//   { cell: [宽, 高], still, clips: { id: { src, cols, rows, frames, fps, loop, loopFrom?, row0? } },
//     moods: { 状态: [动作 id…] }, extras: [待机时偶尔做的小动作 id…] }
// 默认的包由 scripts/export-pet-sprites.py 从 dsh-pet 的动画导出（public/ai-pet/pack.json）。
// 用户导入的 8×11 旧版图集（Codex 桌宠 V2 版式）用 legacyPack() 转成同样的结构，播放器不用区分。

/** 一直在做的状态；其余状态（开心、难过、被戳……）是播一遍就回到待机的「反应」。 */
export const LOOP_MOODS = ['idle', 'thinking', 'talking', 'sleep', 'drag', 'waiting'];

export const isLoopMood = (mood) => LOOP_MOODS.includes(mood);

/** 动作开始后经过 elapsedMs 毫秒时显示第几帧；done 表示不循环的动作已经播完（停在最后一帧）。 */
export function clipFrame(clip, elapsedMs) {
  const n = Math.max(0, Math.floor((elapsedMs / 1000) * clip.fps));
  if (n < clip.frames) return { frame: n, done: false };
  if (!clip.loop) return { frame: clip.frames - 1, done: true };
  const from = clip.loopFrom ?? 0;
  return { frame: from + ((n - clip.frames) % (clip.frames - from)), done: false };
}

export const clipDurationMs = (clip) => (clip.frames / clip.fps) * 1000;

/** 某一帧在放大 scale 倍后的背景位置和尺寸（px）。cols/rows 是整张图集的网格，row0 是这个动作从第几行开始。 */
export function framePosition(clip, cell, frame, scale = 1) {
  const col = frame % clip.cols;
  const row = (clip.row0 ?? 0) + Math.floor(frame / clip.cols);
  return {
    x: -col * cell[0] * scale,
    y: -row * cell[1] * scale,
    sheetW: clip.cols * cell[0] * scale,
    sheetH: clip.rows * cell[1] * scale,
    w: cell[0] * scale,
    h: cell[1] * scale,
  };
}

/** 从某个状态的候选动作里挑一个，尽量不和上一次相同。找不到就退回待机。 */
export function pickClip(pack, mood, /** @type {string | null | undefined} */ lastId = null, rng = Math.random) {
  const list = (pack.moods[mood] ?? pack.moods.idle ?? []).filter((id) => pack.clips[id]);
  if (!list.length) return null;
  const pool = list.length > 1 ? list.filter((id) => id !== lastId) : list;
  return pool[Math.floor(rng() * pool.length)];
}

/** 待机时偶尔做的小动作。 */
export function pickExtra(pack, /** @type {string | null | undefined} */ lastId = null, rng = Math.random) {
  const list = (pack.extras ?? []).filter((id) => pack.clips[id]);
  if (!list.length) return null;
  const pool = list.length > 1 ? list.filter((id) => id !== lastId) : list;
  return pool[Math.floor(rng() * pool.length)];
}

const SAFE_SRC = /^[\w\-./]+$/;
const num = (v, lo, hi) => typeof v === 'number' && Number.isFinite(v) && v >= lo && v <= hi;

/**
 * 校验并整理从 pack.json 读到的清单；不合法返回 null。
 * 图集路径只允许相对路径（不能带协议、不能出现 ..），避免清单被改成指向别处。
 */
export function validatePack(json) {
  if (!json || typeof json !== 'object') return null;
  const cell = json.cell;
  if (!Array.isArray(cell) || cell.length !== 2 || !num(cell[0], 8, 2048) || !num(cell[1], 8, 2048)) return null;
  const clips = {};
  for (const [id, c] of Object.entries(json.clips ?? {})) {
    if (!c || typeof c.src !== 'string' || !SAFE_SRC.test(c.src) || c.src.includes('..') || c.src.startsWith('/')) continue;
    if (!num(c.cols, 1, 64) || !num(c.rows, 1, 256) || !num(c.frames, 1, 2000) || !num(c.fps, 1, 60)) continue;
    if (c.frames > c.cols * c.rows) continue;
    clips[id] = { src: c.src, cols: c.cols, rows: c.rows, frames: c.frames, fps: c.fps, loop: !!c.loop, loopFrom: num(c.loopFrom, 0, c.frames - 1) ? c.loopFrom : 0, row0: num(c.row0, 0, 255) ? c.row0 : 0 };
  }
  if (!clips.idle) return null; // 没有待机动作就没法作为包使用
  const known = (list) => (Array.isArray(list) ? list.filter((id) => typeof id === 'string' && clips[id]) : []);
  const moods = {};
  for (const [mood, list] of Object.entries(json.moods ?? {})) {
    const ids = known(list);
    if (ids.length) moods[mood] = ids;
  }
  moods.idle ??= ['idle'];
  const still = typeof json.still === 'string' && SAFE_SRC.test(json.still) && !json.still.includes('..') && !json.still.startsWith('/') ? json.still : null;
  return { name: typeof json.name === 'string' ? json.name : '', cell: [cell[0], cell[1]], still, clips, moods, extras: known(json.extras) };
}

// ---------- 旧版 8×11 图集（用户在设置里导入的） ----------
export const LEGACY = { COLS: 8, ROWS: 11, CELL_W: 192, CELL_H: 208 };

/** 导入的图集必须是 8×11 的版式（按宽高比判断，允许整体缩放）。 */
export function isValidSheet(width, height) {
  if (!(width >= LEGACY.COLS * 8 && height >= LEGACY.ROWS * 8)) return false;
  return Math.abs(width / height - (LEGACY.COLS * LEGACY.CELL_W) / (LEGACY.ROWS * LEGACY.CELL_H)) < 0.02;
}

// row：这个动作在第几行；loopFrom：循环时从第几帧回头（睡觉前几帧是打哈欠，只播一次）
const LEGACY_ROWS = {
  idle: { row: 0, frames: 7, fps: 5, loop: true },
  runRight: { row: 1, frames: 8, fps: 12, loop: true },
  wave: { row: 3, frames: 4, fps: 5, loop: false },
  thinking: { row: 4, frames: 5, fps: 4, loop: true },
  sad: { row: 5, frames: 8, fps: 6, loop: false },
  sleep: { row: 6, frames: 6, fps: 3, loop: true, loopFrom: 3 },
  talking: { row: 7, frames: 6, fps: 6, loop: true },
  happy: { row: 8, frames: 6, fps: 7, loop: false },
};

/** 把旧版图集包装成和默认包一样的结构。src 是图集的地址（通常是 blob: 地址，所以不走 validatePack）。 */
export function legacyPack(src) {
  const clips = {};
  for (const [id, r] of Object.entries(LEGACY_ROWS)) {
    clips[id] = { src, cols: LEGACY.COLS, rows: LEGACY.ROWS, frames: r.frames, fps: r.fps, loop: r.loop, loopFrom: r.loopFrom ?? 0, row0: r.row };
  }
  const moods = { idle: ['idle'], thinking: ['thinking'], talking: ['talking'], happy: ['happy'], sad: ['sad'], sleep: ['sleep'], wave: ['wave'], poke: ['wave'], drag: ['runRight'] };
  return { name: '自定义图集', cell: [LEGACY.CELL_W, LEGACY.CELL_H], still: null, clips, moods, extras: [] };
}
