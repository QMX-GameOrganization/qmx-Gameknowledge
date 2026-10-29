// 图片预览的缩放 / 平移计算。纯函数，不碰 DOM，方便在 Node 里测试。
//
// 坐标约定：图片左上角为原点、按原始像素尺寸 (nw × nh) 排版，
// 屏幕上的位置 = translate(x, y) scale(s)。所有 x、y 都相对于「舞台」(预览区域)的左上角。

export const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** 初始缩放：让整张图完整放进舞台。cap 限制放大倍数(位图不要放大到发糊，SVG 可以放开)。 */
export function fitScale(nw, nh, vw, vh, { cap = 1, pad = 24, padX = pad } = {}) {
  if (!(nw > 0 && nh > 0 && vw > 0 && vh > 0)) return 1;
  const px = Math.min(padX, vw * 0.18); // 两侧留白(多图时要躲开翻页按钮)，窄屏最多占 18%
  const py = Math.min(pad, vh * 0.1);
  const raw = Math.min((vw - px * 2) / nw, (vh - py * 2) / nh);
  return Math.max(Math.min(raw, cap), 0.01);
}

/** 缩放范围：最小就是「适应窗口」，最大至少 4 倍。 */
export function scaleLimits(fit, { maxFactor = 8, floor = 4 } = {}) {
  return { min: fit, max: Math.max(floor, fit * maxFactor) };
}

/** 平移边界：图比舞台小的方向居中；比舞台大的方向不允许露出空白。 */
export function clampPan(t, nw, nh, vw, vh) {
  const w = nw * t.s;
  const h = nh * t.s;
  return {
    s: t.s,
    x: w <= vw ? (vw - w) / 2 : clamp(t.x, vw - w, 0),
    y: h <= vh ? (vh - h) / 2 : clamp(t.y, vh - h, 0),
  };
}

export function centered(s, nw, nh, vw, vh) {
  return clampPan({ s, x: 0, y: 0 }, nw, nh, vw, vh);
}

/** 缩放到 nextS，并让 (cx, cy) 处的像素保持在原来的屏幕位置(以光标 / 双指中心为轴)。 */
export function zoomAt(t, nextS, cx, cy, limits, nw, nh, vw, vh) {
  const s = clamp(nextS, limits.min, limits.max);
  const k = s / t.s;
  return clampPan({ s, x: cx - (cx - t.x) * k, y: cy - (cy - t.y) * k }, nw, nh, vw, vh);
}

export function panBy(t, dx, dy, nw, nh, vw, vh) {
  return clampPan({ s: t.s, x: t.x + dx, y: t.y + dy }, nw, nh, vw, vh);
}

/** 滚轮 → 缩放倍数。触控板双指捏合会带 ctrlKey，每次的 delta 很小，所以灵敏度更高。 */
export function wheelFactor(deltaY, deltaMode = 0, ctrl = false) {
  const dy = deltaMode === 1 ? deltaY * 16 : deltaMode === 2 ? deltaY * 400 : deltaY;
  return Math.exp(-clamp(dy, -240, 240) * (ctrl ? 0.012 : 0.002));
}

/** 双击：已经放大就回到适应窗口，否则放大到原始尺寸(原图比窗口大得不多就放大 2.5 倍)。 */
export function doubleTapTarget(s, fit, max) {
  if (s > fit * 1.05) return fit;
  const target = 1 > fit * 1.2 ? 1 : fit * 2.5;
  return Math.min(target, max);
}

/** 相册循环翻页。 */
export function nextIndex(i, n, dir) {
  return n <= 0 ? 0 : (((i + dir) % n) + n) % n;
}

/** 水平滑动够远且基本水平，才算翻页手势。 */
export function isSwipe(dx, dy) {
  return Math.abs(dx) > 70 && Math.abs(dy) < Math.abs(dx) * 0.6;
}

/** 打开 / 关闭动画用：把图片摆到缩略图所在的位置(相对舞台)。 */
export function thumbTransform(rect, stageRect, nw) {
  return { s: rect.width / nw, x: rect.left - stageRect.left, y: rect.top - stageRect.top };
}

/** 缩略图是否在视口里(不在就不做飞回动画，直接淡出)。 */
export function rectVisible(rect, vw, vh) {
  return rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.right > 0 && rect.top < vh && rect.left < vw;
}

export const percent = (s) => `${Math.round(s * 100)}%`;
