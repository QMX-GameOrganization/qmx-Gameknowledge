// 桌宠状态机。纯逻辑，不碰 DOM，方便测试。
//
// 状态(mode)：
//   enter  从屏幕左边走进来          idle   站着发呆
//   walk   沿页面底部来回走          sleep  久无操作后打瞌睡
//   drag   被用户拎起来              fall   松手后下落
//   land   落地缓冲                  wave   被点击后招手
// 坐标是视口坐标，(x, y) 是桌宠左上角。

export const PET_DEFAULTS = {
  walkSpeed: 44, // px/s
  gravity: 2200, // px/s²
  sleepAfter: 45, // 秒无操作后睡着
  margin: 8, // 距左右边缘
  groundGap: 6, // 距视口底部
};

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** @typedef {{ width:number, height:number, petW:number, petH:number, margin:number, groundGap:number }} PetWorld */

export const maxX = (world) => Math.max(world.margin, world.width - world.petW - world.margin);
export const groundY = (world) => world.height - world.petH - world.groundGap;

/**
 * @param {PetWorld} world
 * @param {{x:number, dir?:number}} [start] 从上一页恢复的位置；没有就从左边走进来
 */
export function createPet(world, rng = Math.random, start) {
  if (start) {
    return { x: clamp(start.x, world.margin, maxX(world)), y: groundY(world), vx: 0, vy: 0, dir: start.dir === -1 ? -1 : 1, mode: 'idle', timer: 1 + rng() * 2, idleFor: 0 };
  }
  return { x: -world.petW, y: groundY(world), vx: 0, vy: 0, dir: 1, mode: 'enter', timer: 0, idleFor: 0 };
}

/**
 * 推进一帧，返回本帧发生的事件：'arrived' | 'sleep' | 'land'
 * @returns {string[]}
 */
export function stepPet(p, dt, world, rng = Math.random, cfg = PET_DEFAULTS) {
  const events = [];
  const step = Math.min(dt, 0.05);
  const left = world.margin;
  const right = maxX(world);
  const ground = groundY(world);

  switch (p.mode) {
    case 'enter':
      p.x += cfg.walkSpeed * 1.3 * step;
      if (p.x >= left + 40) {
        p.mode = 'idle';
        p.timer = 0.6;
        events.push('arrived');
      }
      break;

    case 'idle':
      p.idleFor += step;
      p.timer -= step;
      if (p.idleFor > cfg.sleepAfter) {
        p.mode = 'sleep';
        events.push('sleep');
      } else if (p.timer <= 0) {
        if (rng() < 0.7) {
          p.mode = 'walk';
          // 靠近哪一侧边缘，就更倾向于往另一侧走
          const toward = p.x < (left + right) / 2 ? 1 : -1;
          p.dir = rng() < 0.7 ? toward : -toward;
          p.timer = 2 + rng() * 3;
        } else {
          p.timer = 1.5 + rng() * 2.5;
        }
      }
      break;

    case 'walk':
      p.idleFor += step;
      p.x += p.dir * cfg.walkSpeed * step;
      if (p.x <= left) { p.x = left; p.dir = 1; }
      else if (p.x >= right) { p.x = right; p.dir = -1; }
      p.timer -= step;
      if (p.timer <= 0) {
        p.mode = 'idle';
        p.timer = 1.5 + rng() * 2.5;
      }
      break;

    case 'fall':
      p.vy += cfg.gravity * step;
      p.y += p.vy * step;
      p.x += p.vx * step;
      p.vx *= Math.pow(0.35, step); // 水平方向很快被摩擦掉
      if (p.x < left) { p.x = left; p.vx = Math.abs(p.vx) * 0.4; }
      if (p.x > right) { p.x = right; p.vx = -Math.abs(p.vx) * 0.4; }
      if (p.y >= ground) {
        p.y = ground;
        p.vx = 0;
        p.vy = 0;
        p.mode = 'land';
        p.timer = 0.3;
        events.push('land');
      }
      break;

    case 'land':
    case 'wave':
      p.timer -= step;
      if (p.timer <= 0) {
        p.mode = 'idle';
        p.timer = 1 + rng() * 1.5;
      }
      break;

    default: // sleep / drag：由外部事件改变状态
      break;
  }

  // 窗口尺寸变化后，保证桌宠仍在可见范围内
  if (p.mode !== 'drag' && p.mode !== 'enter') {
    p.x = clamp(p.x, left, right);
    if (p.mode !== 'fall') {
      if (p.y > ground) p.y = ground;
      else if (p.y < ground - 0.5) { p.mode = 'fall'; p.vy = 0; } // 视口变高了，悬空了就掉下去
    }
  }
  return events;
}

/** 用户有操作：重置计时，睡着的话醒来。返回是否刚被唤醒。 */
export function noteActivity(p) {
  p.idleFor = 0;
  if (p.mode === 'sleep') {
    p.mode = 'idle';
    p.timer = 1.2;
    return true;
  }
  return false;
}

export function grab(p) {
  p.mode = 'drag';
  p.vx = 0;
  p.vy = 0;
  p.idleFor = 0;
}

export function dragTo(p, x, y, world) {
  p.x = clamp(x, 0, world.width - world.petW);
  p.y = clamp(y, 0, world.height - world.petH);
}

/** 松手：带着手上的速度扔出去，之后由 fall 状态落到地面。 */
export function release(p, vx = 0, vy = 0) {
  p.mode = 'fall';
  p.vx = clamp(vx, -900, 900);
  p.vy = clamp(vy, -1200, 1200);
}

/** 被点击：招手。拖拽和下落中不响应。 */
export function poke(p) {
  if (p.mode === 'drag' || p.mode === 'fall') return false;
  p.mode = 'wave';
  p.timer = 1.6;
  p.idleFor = 0;
  return true;
}
