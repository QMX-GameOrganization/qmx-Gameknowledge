// 图片预览的缩放 / 平移逻辑测试。用法：node scripts/test-lightbox.mjs
import assert from "node:assert/strict";
import {
  fitScale, scaleLimits, clampPan, centered, zoomAt, panBy, wheelFactor, doubleTapTarget,
  nextIndex, isSwipe, thumbTransform, rectVisible, percent,
} from "../src/lightbox/lightbox-math.mjs";

let passed = 0;
const test = (name, fn) => { fn(); passed++; console.log("✓", name); };
const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) < eps, `${a} ≈ ${b}`);

const V = { w: 1200, h: 700 }; // 舞台尺寸

test("大图缩小到完整放进舞台；小位图不放大；SVG 可以放大", () => {
  const big = fitScale(2240, 605, V.w, V.h);
  assert.ok(big < 1 && 2240 * big <= V.w && 605 * big <= V.h);
  assert.equal(fitScale(400, 300, V.w, V.h), 1, "位图最多 100%");
  const svg = fitScale(900, 470, V.w, V.h, { cap: Infinity });
  assert.ok(svg > 1 && 900 * svg <= V.w);
  const tall = fitScale(677, 1441, V.w, V.h);
  assert.ok(1441 * tall <= V.h, "竖长图按高度适应");
});

test("多图时两侧留出翻页按钮的位置，单图不留", () => {
  const solo = fitScale(2240, 605, V.w, V.h);
  const multi = fitScale(2240, 605, V.w, V.h, { padX: 72 });
  assert.ok(multi < solo);
  assert.ok(2240 * multi <= V.w - 72 * 2 + 1e-6, "图片宽度不压到左右各 72px");
  assert.ok(fitScale(2240, 605, 360, 700, { padX: 72 }) * 2240 >= 360 * 0.64 - 1, "窄屏的留白被限制在 18%，不会把图缩得太小");
});

test("退化输入不会得到 0、负数或 NaN", () => {
  for (const args of [[0, 0, 100, 100], [100, 100, 0, 0], [100, 100, 20, 20], [NaN, 1, 1, 1]]) {
    const s = fitScale(...args);
    assert.ok(Number.isFinite(s) && s > 0, `fitScale(${args}) = ${s}`);
  }
});

test("缩放范围：最小是适应窗口，最大至少 4 倍", () => {
  assert.deepEqual(scaleLimits(0.3), { min: 0.3, max: 4 });
  assert.equal(scaleLimits(1).max, 8);
});

test("图比舞台小：居中；比舞台大：不会露出空白", () => {
  const small = clampPan({ s: 1, x: 999, y: -999 }, 400, 300, V.w, V.h);
  near(small.x, (V.w - 400) / 2); near(small.y, (V.h - 300) / 2);
  const large = clampPan({ s: 2, x: 500, y: 500 }, 1000, 800, V.w, V.h); // 2000×1600
  assert.equal(large.x, 0); assert.equal(large.y, 0);
  const far = clampPan({ s: 2, x: -9999, y: -9999 }, 1000, 800, V.w, V.h);
  near(far.x, V.w - 2000); near(far.y, V.h - 1600);
});

test("以光标为中心缩放：光标下的那个像素保持不动", () => {
  const nw = 2000, nh = 1200;
  const fit = fitScale(nw, nh, V.w, V.h);
  const lim = scaleLimits(fit);
  const t0 = centered(fit, nw, nh, V.w, V.h);
  const cx = 800, cy = 300;
  const u = { x: (cx - t0.x) / t0.s, y: (cy - t0.y) / t0.s }; // 光标下的图像坐标
  const t1 = zoomAt(t0, 1, cx, cy, lim, nw, nh, V.w, V.h);
  near(t1.s, 1);
  near(t1.x + u.x * t1.s, cx, 1e-6); near(t1.y + u.y * t1.s, cy, 1e-6);
});

test("缩放受上下限约束；回到适应窗口时重新居中", () => {
  const nw = 2000, nh = 1200, fit = fitScale(nw, nh, V.w, V.h), lim = scaleLimits(fit);
  let t = centered(fit, nw, nh, V.w, V.h);
  t = zoomAt(t, 999, 600, 350, lim, nw, nh, V.w, V.h);
  assert.equal(t.s, lim.max);
  t = zoomAt(t, 0.0001, 100, 100, lim, nw, nh, V.w, V.h);
  assert.equal(t.s, lim.min);
  const home = centered(fit, nw, nh, V.w, V.h);
  near(t.x, home.x); near(t.y, home.y);
});

test("平移被限制在图片范围内", () => {
  const nw = 2000, nh = 1200;
  let t = { s: 1.5, x: 0, y: 0 };
  t = panBy(t, 99999, 99999, nw, nh, V.w, V.h);
  assert.equal(t.x, 0); assert.equal(t.y, 0);
  t = panBy(t, -99999, -99999, nw, nh, V.w, V.h);
  near(t.x, V.w - nw * 1.5); near(t.y, V.h - nh * 1.5);
});

test("滚轮方向与倍数：向上放大、向下缩小；触控板捏合更灵敏；极端值有上限", () => {
  assert.ok(wheelFactor(-100) > 1 && wheelFactor(100) < 1);
  assert.ok(wheelFactor(-5, 0, true) > wheelFactor(-5, 0, false));
  assert.ok(Number.isFinite(wheelFactor(1e9)) && wheelFactor(1e9) > 0.5);
  assert.ok(wheelFactor(-3, 1) > wheelFactor(-3, 0), "按行滚动的 delta 要换算成像素");
});

test("双击：适应窗口时放大，放大后回到适应窗口", () => {
  assert.equal(doubleTapTarget(0.4, 0.4, 4), 1, "原图比窗口大得多：放大到 100%");
  near(doubleTapTarget(0.9, 0.9, 4), 2.25, 1e-9); // 原图只比窗口大一点：放大 2.5 倍
  assert.equal(doubleTapTarget(1, 0.4, 4), 0.4);
  assert.equal(doubleTapTarget(3, 3, 4), 4, "SVG 已经放大适应窗口：再放大，但不超过上限");
  assert.equal(doubleTapTarget(2.5, 1, 8), 1, "比适应窗口大得多，回到适应窗口");
  assert.ok(doubleTapTarget(1, 2, 3) <= 3, "不超过上限");
});

test("相册翻页首尾循环", () => {
  assert.equal(nextIndex(0, 5, -1), 4);
  assert.equal(nextIndex(4, 5, 1), 0);
  assert.equal(nextIndex(2, 5, 1), 3);
  assert.equal(nextIndex(0, 1, 1), 0);
  assert.equal(nextIndex(0, 0, 1), 0);
});

test("滑动手势：够远且基本水平才翻页", () => {
  assert.ok(isSwipe(120, 20));
  assert.ok(!isSwipe(40, 5), "太短");
  assert.ok(!isSwipe(100, 90), "斜着拖更像是在平移");
});

test("打开动画的起点对应缩略图的位置和大小", () => {
  const t = thumbTransform({ left: 340, top: 260, width: 650, height: 180 }, { left: 0, top: 52 }, 2240);
  near(t.s, 650 / 2240); assert.equal(t.x, 340); assert.equal(t.y, 208);
  assert.ok(rectVisible({ top: 10, left: 10, bottom: 100, right: 100, width: 90, height: 90 }, 1280, 800));
  assert.ok(!rectVisible({ top: -500, left: 10, bottom: -10, right: 100, width: 90, height: 490 }, 1280, 800), "已经滚出屏幕上方");
  assert.ok(!rectVisible({ top: 10, left: 10, bottom: 10, right: 10, width: 0, height: 0 }, 1280, 800));
});

test("百分比显示", () => {
  assert.equal(percent(0.4567), "46%");
  assert.equal(percent(1), "100%");
});

console.log(`\n${passed} 项通过`);
