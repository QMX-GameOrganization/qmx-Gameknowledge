// 特效里的纯逻辑测试(星星物理、桌宠状态机)。用法：node scripts/test-fx.mjs
import assert from "node:assert/strict";
import { createStars, stepStars, shockwave, homePosition, drawPosition } from "../src/fx/star-physics.mjs";
import { addParticle, stepParticles, burst, pushAway, life01 } from "../src/fx/particles.mjs";
import { createPet, stepPet, noteActivity, grab, dragTo, release, poke, maxX, groundY, PET_DEFAULTS } from "../src/fx/pet-logic.mjs";

// 固定随机序列，结果可复现
function seeded(seed = 7) {
  return () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
}
const view = { width: 1280, height: 800, scrollY: 0 };
const dt = 1 / 60;
let passed = 0;
const test = (name, fn) => { fn(); passed++; console.log("✓", name); };

test("没有鼠标时星星不动", () => {
  const stars = createStars(120, seeded());
  for (let i = 0; i < 120; i++) stepStars(stars, dt, { x: 0, y: 0, active: false }, view);
  assert.ok(stars.every((s) => s.ox === 0 && s.oy === 0));
});

test("鼠标靠近时星星被推开，且是朝远离鼠标的方向", () => {
  const stars = createStars(400, seeded());
  const pointer = { x: 640, y: 400, active: true };
  const near = stars.filter((s) => {
    const h = homePosition(s, view.width, view.height, 0);
    return Math.hypot(h.x - pointer.x, h.y - pointer.y) < 70;
  });
  assert.ok(near.length >= 3, "测试数据里鼠标附近应当有星星");
  const before = near.map((s) => { const h = homePosition(s, view.width, view.height, 0); return Math.hypot(h.x - pointer.x, h.y - pointer.y); });
  for (let i = 0; i < 30; i++) stepStars(stars, dt, pointer, view);
  near.forEach((s, i) => {
    const p = drawPosition(s, view.width, view.height, 0);
    const after = Math.hypot(p.x - pointer.x, p.y - pointer.y);
    assert.ok(after > before[i] + 5, `星星应远离鼠标：${before[i].toFixed(1)} -> ${after.toFixed(1)}`);
  });
});

test("影响半径之外的星星不受影响", () => {
  const stars = createStars(400, seeded());
  const pointer = { x: 640, y: 400, active: true };
  const far = stars.filter((s) => {
    const h = homePosition(s, view.width, view.height, 0);
    return Math.hypot(h.x - pointer.x, h.y - pointer.y) > 200;
  });
  for (let i = 0; i < 60; i++) stepStars(stars, dt, pointer, view);
  assert.ok(far.every((s) => s.ox === 0 && s.oy === 0));
});

test("鼠标离开后星星回到原位", () => {
  const stars = createStars(400, seeded());
  for (let i = 0; i < 40; i++) stepStars(stars, dt, { x: 640, y: 400, active: true }, view);
  assert.ok(stars.some((s) => Math.hypot(s.ox, s.oy) > 20), "应当有星星被推开");
  for (let i = 0; i < 60 * 4; i++) stepStars(stars, dt, { x: 0, y: 0, active: false }, view);
  const worst = Math.max(...stars.map((s) => Math.hypot(s.ox, s.oy)));
  assert.ok(worst < 0.5, `4 秒后应基本回位，最大残留偏移 ${worst.toFixed(3)}`);
});

test("偏移不超过上限，也不会出现 NaN", () => {
  const stars = createStars(300, seeded());
  for (let i = 0; i < 300; i++) {
    stepStars(stars, 0.5, { x: 640 + Math.sin(i) * 5, y: 400, active: true }, view); // 故意用很大的步长模拟掉帧
    if (i % 40 === 0) shockwave(stars, 640, 400, view);
  }
  for (const s of stars) {
    assert.ok(Number.isFinite(s.ox) && Number.isFinite(s.oy) && Number.isFinite(s.vx) && Number.isFinite(s.vy));
    assert.ok(Math.hypot(s.ox, s.oy) <= 220 + 1e-6);
  }
});

test("点击冲击波把附近的星星弹开", () => {
  const stars = createStars(400, seeded());
  shockwave(stars, 640, 400, view);
  for (let i = 0; i < 10; i++) stepStars(stars, dt, { x: 0, y: 0, active: false }, view);
  assert.ok(stars.some((s) => Math.hypot(s.ox, s.oy) > 10));
});

test("滚动产生视差：近层比远层移动得更多，且纵向循环不越界", () => {
  const stars = createStars(200, seeded());
  const far = stars.find((s) => s.layer === 0);
  const near = stars.find((s) => s.layer === 2);
  const dFar = Math.abs(homePosition(far, 1280, 800, 0).y - homePosition(far, 1280, 800, 300).y);
  const dNear = Math.abs(homePosition(near, 1280, 800, 0).y - homePosition(near, 1280, 800, 300).y);
  assert.ok(dNear > dFar);
  for (const s of stars) {
    const y = homePosition(s, 1280, 800, 99999).y;
    assert.ok(y >= 0 && y < 800);
  }
});

// ───────── 粒子工具 ─────────
test("burst 生成指定数量的粒子，并且不超过上限", () => {
  const list = [];
  burst(list, 100, 100, 20, { cap: 500 }, seeded(9));
  assert.equal(list.length, 20);
  burst(list, 100, 100, 600, { cap: 50 }, seeded(9));
  assert.equal(list.length, 50, "数量有界");
  assert.ok(list.every((p) => p.life > 0 && p.life === p.max && Number.isFinite(p.vx)));
});

test("粒子受重力下落，寿命耗尽后被移除", () => {
  const list = [];
  burst(list, 0, 0, 30, { speed: [0, 0], life: [0.5, 0.5] }, seeded(2));
  const y0 = list[0].y;
  for (let i = 0; i < 20; i++) stepParticles(list, dt, { gravity: 900 });
  assert.ok(list[0].y > y0 + 10, "应当下落");
  for (let i = 0; i < 60; i++) stepParticles(list, dt, { gravity: 900 });
  assert.equal(list.length, 0, "寿命耗尽后全部移除");
});

test("地面：不反弹的粒子停在地面，反弹的粒子会向上弹起", () => {
  const rest = [];
  addParticle(rest, { x: 0, y: 90, vx: 50, vy: 400, life: 5, max: 5, size: 4, rot: 0, vr: 0, color: "#fff" });
  for (let i = 0; i < 120; i++) stepParticles(rest, dt, { gravity: 900, floor: 100 });
  assert.equal(rest[0].y, 100);
  assert.equal(rest[0].vy, 0);
  const bouncy = [];
  addParticle(bouncy, { x: 0, y: 90, vx: 0, vy: 600, life: 5, max: 5, size: 4, rot: 0, vr: 0, color: "#fff" });
  let sawUp = false;
  for (let i = 0; i < 60; i++) { stepParticles(bouncy, dt, { gravity: 900, floor: 100, bounce: 0.5 }); if (bouncy[0].vy < 0) sawUp = true; }
  assert.ok(sawUp);
});

test("pushAway 只推半径内的粒子，方向远离中心", () => {
  const list = [];
  addParticle(list, { x: 110, y: 100, vx: 0, vy: 0, life: 1, max: 1, size: 1, rot: 0, vr: 0, color: "#fff" });
  addParticle(list, { x: 500, y: 100, vx: 0, vy: 0, life: 1, max: 1, size: 1, rot: 0, vr: 0, color: "#fff" });
  pushAway(list, 100, 100, 120, 2000, dt);
  assert.ok(list[0].vx > 0, "右边的粒子被向右推");
  assert.equal(list[1].vx, 0);
});

test("极端输入下粒子数值保持有限（掉帧、零距离）", () => {
  const list = [];
  burst(list, 5, 5, 100, {}, seeded(4));
  addParticle(list, { x: 50, y: 50, vx: 0, vy: 0, life: 2, max: 2, size: 1, rot: 0, vr: 0, color: "#fff" });
  for (let i = 0; i < 50; i++) { pushAway(list, 50, 50, 100, 5000, 0.5); stepParticles(list, 0.5, { gravity: 900, drag: 0.5, windX: 40 }); }
  assert.ok(list.every((p) => Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.vx) && Number.isFinite(p.vy)));
});

// ───────── 桌宠状态机 ─────────
const world = { width: 1280, height: 800, petW: 96, petH: 96, margin: 8, groundGap: 6 };
const run = (pet, seconds, w = world, rng = seeded(3)) => {
  const events = [];
  for (let i = 0; i < Math.round(seconds * 60); i++) events.push(...stepPet(pet, dt, w, rng));
  return events;
};

test("桌宠从屏幕左侧走进来，然后进入待机", () => {
  const pet = createPet(world);
  assert.equal(pet.mode, "enter");
  assert.ok(pet.x < 0, "起点在屏幕外");
  const events = run(pet, 4);
  assert.ok(events.includes("arrived"));
  assert.ok(pet.x >= world.margin);
});

test("桌宠长时间走动也不会越界，并且始终站在地面上", () => {
  const pet = createPet(world, seeded(5), { x: 600 });
  let walked = false;
  for (let i = 0; i < 60 * 600; i++) {
    stepPet(pet, dt, world, seeded(i + 1));
    if (pet.mode === "walk") walked = true;
    noteActivity(pet); // 一直有人操作，不让它睡着
    assert.ok(pet.x >= world.margin - 1e-9 && pet.x <= maxX(world) + 1e-9, `x=${pet.x}`);
    assert.equal(pet.y, groundY(world));
  }
  assert.ok(walked, "10 分钟里至少应该走动过");
});

test("无人操作超过设定时间后睡着，操作后醒来", () => {
  const pet = createPet(world, seeded(5), { x: 600 });
  const events = run(pet, PET_DEFAULTS.sleepAfter + 5);
  assert.ok(events.includes("sleep"));
  assert.equal(pet.mode, "sleep");
  const x = pet.x;
  run(pet, 3);
  assert.equal(pet.x, x, "睡着时不会移动");
  assert.equal(noteActivity(pet), true);
  assert.equal(pet.mode, "idle");
});

test("拎起来再扔出去：落回地面、触发落地事件、横向被限制在屏幕内", () => {
  const pet = createPet(world, seeded(5), { x: 600 });
  grab(pet);
  dragTo(pet, 1200, 100, world);
  assert.equal(pet.mode, "drag");
  run(pet, 1);
  assert.equal(pet.y, 100, "拖拽中不受重力影响");
  release(pet, 5000, -9999); // 故意给很大的速度
  assert.ok(Math.abs(pet.vx) <= 900 && Math.abs(pet.vy) <= 1200, "速度被限制");
  const events = run(pet, 3);
  assert.ok(events.includes("land"));
  assert.equal(pet.y, groundY(world));
  assert.ok(pet.x <= maxX(world));
});

test("点击招手；拖拽和下落时不响应点击", () => {
  const pet = createPet(world, seeded(5), { x: 600 });
  assert.equal(poke(pet), true);
  assert.equal(pet.mode, "wave");
  run(pet, 2);
  assert.equal(pet.mode, "idle");
  grab(pet);
  assert.equal(poke(pet), false);
  release(pet);
  assert.equal(poke(pet), false);
});

test("窗口缩小后桌宠被带回可见范围，窗口变高后悬空的桌宠会落下", () => {
  const pet = createPet(world, seeded(5), { x: 1100 });
  run(pet, 0.2);
  const small = { ...world, width: 600, height: 500 };
  run(pet, 0.2, small);
  assert.ok(pet.x <= maxX(small));
  assert.equal(pet.y, groundY(small));
  const tall = { ...world, width: 600, height: 900 };
  const events = run(pet, 3, tall);
  assert.ok(events.includes("land"));
  assert.equal(pet.y, groundY(tall));
});

console.log(`\n${passed} 项通过`);
