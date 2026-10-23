// 星夜主题的星星物理。纯函数，不碰 DOM，方便在 Node 里直接测试。
//
// 每颗星有一个「家」(u, v 为 0~1 的相对坐标，随视口缩放)，再加一个偏移 (ox, oy)。
// 鼠标靠近时给偏移一个远离鼠标的加速度；弹簧把偏移拉回 0；速度带阻尼。
// 页面滚动时，不同层的星星以不同速度「向上漂」，形成视差。

/** @typedef {{ u:number, v:number, r:number, layer:number, phase:number, speed:number, tint:number,
 *             ox:number, oy:number, vx:number, vy:number }} Star */

export const DEFAULT_PARAMS = {
  radius: 150, // 鼠标影响半径(px)
  strength: 4200, // 鼠标正中心处的推力(px/s²)
  spring: 26, // 回弹弹簧系数
  damping: 0.9, // 每 1/60 秒的速度保留比例
  maxOffset: 220, // 偏移上限(px)
  parallax: 0.06, // 滚动视差系数(每层)
};

/**
 * @param {number} count
 * @param {() => number} [rng] 返回 [0,1) 的随机函数，测试时可传固定种子
 * @returns {Star[]}
 */
export function createStars(count, rng = Math.random) {
  const stars = [];
  for (let i = 0; i < count; i++) {
    const layer = rng() < 0.55 ? 0 : rng() < 0.65 ? 1 : 2; // 0 远 / 1 中 / 2 近
    stars.push({
      u: rng(),
      v: rng(),
      r: 0.5 + layer * 0.45 + rng() * 0.6,
      layer,
      phase: rng() * Math.PI * 2,
      speed: 0.6 + rng() * 1.6,
      tint: rng() < 0.62 ? 0 : rng() < 0.6 ? 1 : 2, // 0 白蓝 / 1 强调色 / 2 第二强调色
      ox: 0,
      oy: 0,
      vx: 0,
      vy: 0,
    });
  }
  return stars;
}

/** 星星「家」在当前视口里的位置(含滚动视差，纵向循环)。 */
export function homePosition(star, width, height, scrollY, parallax = DEFAULT_PARAMS.parallax) {
  const drift = scrollY * parallax * (star.layer + 1);
  const y = (((star.v * height - drift) % height) + height) % height;
  return { x: star.u * width, y };
}

/**
 * 推进一帧。
 * @param {Star[]} stars
 * @param {number} dt 秒
 * @param {{x:number,y:number,active:boolean}} pointer 视口坐标
 * @param {{width:number,height:number,scrollY:number}} view
 * @param {Partial<typeof DEFAULT_PARAMS>} [overrides]
 * @returns {number} 本帧被鼠标明显推动的星星数(可用来触发音效)
 */
export function stepStars(stars, dt, pointer, view, overrides) {
  const p = { ...DEFAULT_PARAMS, ...overrides };
  const step = Math.min(dt, 1 / 20); // 掉帧时限制步长，避免弹飞
  const damp = Math.pow(p.damping, step * 60);
  let pushed = 0;

  for (const s of stars) {
    if (pointer.active) {
      const home = homePosition(s, view.width, view.height, view.scrollY, p.parallax);
      const dx = home.x + s.ox - pointer.x;
      const dy = home.y + s.oy - pointer.y;
      const d = Math.hypot(dx, dy);
      if (d < p.radius) {
        const t = 1 - d / p.radius;
        // 近处的星星(layer 大)被推得更远一点，增强层次感
        const force = t * t * p.strength * (0.7 + s.layer * 0.2);
        const nx = d > 0.001 ? dx / d : Math.cos(s.phase);
        const ny = d > 0.001 ? dy / d : Math.sin(s.phase);
        s.vx += nx * force * step;
        s.vy += ny * force * step;
        if (t > 0.45) pushed++;
      }
    }

    s.vx += -s.ox * p.spring * step;
    s.vy += -s.oy * p.spring * step;
    s.vx *= damp;
    s.vy *= damp;
    s.ox += s.vx * step;
    s.oy += s.vy * step;

    const len = Math.hypot(s.ox, s.oy);
    if (len > p.maxOffset) {
      s.ox = (s.ox / len) * p.maxOffset;
      s.oy = (s.oy / len) * p.maxOffset;
    }
  }
  return pushed;
}

/** 点击产生的冲击波：把半径内的星星朝外弹开一下。 */
export function shockwave(stars, x, y, view, radius = 240, power = 520, parallax = DEFAULT_PARAMS.parallax) {
  for (const s of stars) {
    const home = homePosition(s, view.width, view.height, view.scrollY, parallax);
    const dx = home.x + s.ox - x;
    const dy = home.y + s.oy - y;
    const d = Math.hypot(dx, dy);
    if (d < radius) {
      const t = 1 - d / radius;
      const nx = d > 0.001 ? dx / d : Math.cos(s.phase);
      const ny = d > 0.001 ? dy / d : Math.sin(s.phase);
      s.vx += nx * t * power;
      s.vy += ny * t * power;
    }
  }
}

/** 星星当前的绘制位置。 */
export function drawPosition(star, width, height, scrollY, parallax = DEFAULT_PARAMS.parallax) {
  const h = homePosition(star, width, height, scrollY, parallax);
  return { x: h.x + star.ox, y: h.y + star.oy };
}
