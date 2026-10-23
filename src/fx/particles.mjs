// 通用粒子工具。纯函数，不碰 DOM，方便测试。
// 粒子是普通对象：{ x, y, vx, vy, life, max, size, rot, vr, color, ...自定义字段 }
// life 从 max 倒数到 0，到 0 时被移除；life / max 可以直接当作透明度或缩放系数用。

const TAU = Math.PI * 2;
const lerp = ([a, b], t) => a + (b - a) * t;

/** 加入一个粒子；超过上限时丢弃最老的，保证数量有界。 */
export function addParticle(list, p, cap = 500) {
  if (list.length >= cap) list.shift();
  list.push(p);
  return p;
}

/**
 * 推进所有粒子并移除寿命耗尽的。
 * env: { gravity, drag(每秒速度保留比例, 1=无阻力), windX, windY, floor(y 上限), bounce(0~1) }
 */
export function stepParticles(list, dt, env = {}) {
  const { gravity = 0, drag = 1, windX = 0, windY = 0, floor = Infinity, bounce = 0 } = env;
  const step = Math.min(dt, 0.05);
  const damp = Math.pow(drag, step);
  for (let i = list.length - 1; i >= 0; i--) {
    const p = list[i];
    p.life -= step;
    if (p.life <= 0) {
      list.splice(i, 1);
      continue;
    }
    p.vx += windX * step;
    p.vy += (gravity + windY) * step;
    p.vx *= damp;
    p.vy *= damp;
    p.x += p.vx * step;
    p.y += p.vy * step;
    p.rot += p.vr * step;
    if (p.y > floor) {
      p.y = floor;
      p.vy = bounce > 0 ? -p.vy * bounce : 0;
      p.vx *= 0.7;
    }
  }
}

/**
 * 在 (x, y) 处爆出 count 个粒子。
 * o: { speed:[min,max], angle:[min,max](弧度), life:[min,max](秒), size:[min,max], colors:[...], spin:[min,max], cap, extra(rng)=>自定义字段 }
 */
export function burst(list, x, y, count, o = {}, rng = Math.random) {
  const { speed = [80, 260], angle = [0, TAU], life = [0.6, 1.1], size = [3, 7], colors = ['#ffffff'], spin = [-6, 6], cap = 500, extra } = o;
  for (let i = 0; i < count; i++) {
    const a = lerp(angle, rng());
    const s = lerp(speed, rng());
    const l = lerp(life, rng());
    addParticle(
      list,
      {
        x,
        y,
        vx: Math.cos(a) * s,
        vy: Math.sin(a) * s,
        life: l,
        max: l,
        size: lerp(size, rng()),
        rot: rng() * TAU,
        vr: lerp(spin, rng()),
        color: colors[Math.floor(rng() * colors.length) % colors.length],
        ...(extra ? extra(rng) : null),
      },
      cap,
    );
  }
}

/** 把半径内的粒子从 (px, py) 推开，越近推得越狠。连续作用力，每帧调用。 */
export function pushAway(list, px, py, radius, strength, dt) {
  for (const p of list) {
    const dx = p.x - px;
    const dy = p.y - py;
    const d = Math.hypot(dx, dy);
    if (d < radius && d > 0.001) {
      const t = 1 - d / radius;
      const f = t * t * strength * dt;
      p.vx += (dx / d) * f;
      p.vy += (dy / d) * f;
    }
  }
}

/** 寿命进度 1 → 0，用作淡出。 */
export const life01 = (p) => Math.max(0, p.life / p.max);
