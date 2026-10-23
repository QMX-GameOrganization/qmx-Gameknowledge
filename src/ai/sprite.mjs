// 鲸鱼形象的精灵图规格与帧计算，纯逻辑，可以直接在 node 里测试。
//
// 图集沿用 Codex 桌宠 V2 的版式：8 列 × 11 行，单格 192×208（可整体等比放大）。
// 每一行是一种动作，行内帧数不同，后面的格子是空的：
//   0 待机 7 帧 · 1 向右跑 8 · 2 向左跑 8 · 3 挥手 4 · 4 歪头带问号 5
//   5 倒地 8 · 6 睡觉 6 · 7 伏案写字 6 · 8 敲鼓庆祝 6 · 9、10 十六方向的视线

export const COLS = 8;
export const ROWS = 11;
export const CELL_W = 192;
export const CELL_H = 208;
export const SHEET_W = COLS * CELL_W; // 1536
export const SHEET_H = ROWS * CELL_H; // 2288

/**
 * 心情 → 图集里的动作。
 * still：系统要求「减少动态效果」时显示的静止帧；
 * loopFrom：循环播放时从第几帧回头（睡觉的前几帧是打哈欠，只播一次）；
 * loop 为 false 时播完停在最后一帧。
 */
export const MOODS = {
  idle: { row: 0, frames: 7, fps: 5, loop: true, loopFrom: 0, still: 0 },
  thinking: { row: 4, frames: 5, fps: 4, loop: true, loopFrom: 0, still: 2 },
  talking: { row: 7, frames: 6, fps: 6, loop: true, loopFrom: 0, still: 0 },
  happy: { row: 8, frames: 6, fps: 7, loop: true, loopFrom: 0, still: 4 },
  sad: { row: 5, frames: 8, fps: 6, loop: false, loopFrom: 0, still: 7 },
  sleep: { row: 6, frames: 6, fps: 3, loop: true, loopFrom: 3, still: 4 },
  wave: { row: 3, frames: 4, fps: 5, loop: false, loopFrom: 0, still: 2 },
  runRight: { row: 1, frames: 8, fps: 12, loop: true, loopFrom: 0, still: 0 },
  runLeft: { row: 2, frames: 8, fps: 12, loop: true, loopFrom: 0, still: 0 },
};

/** 心情开始后经过 elapsedMs 毫秒时应该显示第几帧。 */
export function frameAt(mood, elapsedMs) {
  const m = MOODS[mood] ?? MOODS.idle;
  const n = Math.max(0, Math.floor((elapsedMs / 1000) * m.fps));
  if (n < m.frames) return n;
  if (!m.loop) return m.frames - 1;
  const span = m.frames - m.loopFrom;
  return m.loopFrom + ((n - m.frames) % span);
}

/** 导入的图集必须是 8×11 的版式（按宽高比判断，允许整体缩放）。 */
export function isValidSheet(width, height) {
  if (!(width >= COLS * 8 && height >= ROWS * 8)) return false;
  return Math.abs(width / height - SHEET_W / SHEET_H) < 0.02;
}

/** 某一帧在放大 scale 倍后的背景样式（单位 px）。 */
export function framePosition(mood, frame, scale) {
  const m = MOODS[mood] ?? MOODS.idle;
  return {
    x: -frame * CELL_W * scale,
    y: -m.row * CELL_H * scale,
    sheetW: SHEET_W * scale,
    sheetH: SHEET_H * scale,
    w: CELL_W * scale,
    h: CELL_H * scale,
  };
}
