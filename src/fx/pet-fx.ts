// 通用桌宠：把「形象 + 台词 + 音效」交给 PetKit，行为和交互都在这里。
//
//   · 在页面底部来回走动、发呆、久了打瞌睡，眼睛跟着鼠标转；
//   · 点击会招手并用气泡说一句话；可以拖起来扔出去，落地有缓冲；
//   · 换页后位置会接着上一页，不会每次都从头走进来；
//   · 系统开启「减少动态效果」时不显示。
//
// 角色素材：默认是内置的原创 SVG。想换成自己有权使用的角色，把精灵图和 pet.json 放进
// public/themes/<主题 id>/pet/ 即可，格式见 CONTRIBUTING.md「自定义桌宠素材」。
// 仓库本身不包含任何第三方游戏素材。

import type { FxContext, FxModule } from './index';
import type { AudioManager } from './audio';
import { createPet, stepPet, noteActivity, grab, dragTo, release, poke, PET_DEFAULTS } from './pet-logic.mjs';

export interface PetKit {
  /** 形象标识，写到 data-pet 上，fx.css 按它区分动画：bot | slime | cat */
  kind: string;
  /** 内置 SVG，类名约定见 fx.css（pet-bob / pet-leg-a / pet-eyes / pet-zzz ...） */
  svg: string;
  lines: string[];
  greeting: string;
  wakeLine: string;
  endLine: string;
  /** 像素/秒，默认 44 */
  walkSpeed?: number;
  onPoke(audio: AudioManager): void;
  onLand(audio: AudioManager): void;
  onBoot(audio: AudioManager): void;
}

type SpriteState = { src: string; frames: number; fps: number };
type SpriteConfig = { size?: [number, number]; faceRight?: boolean; states: Record<string, SpriteState> };

const STORE_KEY = 'qmx-pet';

// 引擎状态 -> 精灵图状态名；缺少的状态回退到 idle
const SPRITE_STATE: Record<string, string> = {
  enter: 'walk', walk: 'walk', idle: 'idle', sleep: 'sleep', drag: 'drag', fall: 'fall', land: 'fall', wave: 'wave',
};

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const safeName = (s: unknown): s is string => typeof s === 'string' && /^[\w.-]+$/.test(s);

async function loadSpriteConfig(base: string, themeId: string): Promise<SpriteConfig | null> {
  try {
    const res = await fetch(`${base}themes/${themeId}/pet/pet.json`, { cache: 'no-cache' });
    if (!res.ok) return null;
    const cfg = (await res.json()) as SpriteConfig;
    const idle = cfg?.states?.idle;
    if (!idle || !safeName(idle.src) || !(idle.frames >= 1) || !(idle.fps > 0)) return null;
    return cfg;
  } catch {
    return null; // 没有素材(404)或不是合法 JSON：使用内置形象
  }
}

export function createPetFx(themeId: string, kit: PetKit): FxModule {
  let cleanup: (() => void) | null = null;
  // 每次 start / stop 都会递增。start 里要等素材加载，期间如果用户切走了主题，
  // 加载完成后发现代数变了，就直接放弃，避免留下一个没人管的桌宠。
  let generation = 0;
  const greetedKey = `qmx-pet-greeted-${themeId}`;
  const cfg = { ...PET_DEFAULTS, walkSpeed: kit.walkSpeed ?? PET_DEFAULTS.walkSpeed };

  return {
    async start(ctx: FxContext) {
      cleanup?.();
      const mine = ++generation;
      const { audio, base, reduced, compact } = ctx;
      if (reduced) return; // 桌宠会一直动，系统要求减少动态效果时不显示

      const sprite = await loadSpriteConfig(base, themeId);
      if (mine !== generation) return;

      // ───── 尺寸与 DOM ─────
      let petW = compact ? 72 : 96;
      let petH = petW;
      let faceRight = true;
      if (sprite) {
        const [sw, sh] = sprite.size ?? [96, 96];
        const scale = Math.min(1, (compact ? 84 : 112) / sh);
        petW = Math.round(sw * scale);
        petH = Math.round(sh * scale);
        faceRight = sprite.faceRight !== false;
      }

      const el = document.createElement('div');
      el.className = 'qmx-pet';
      el.dataset.state = 'enter';
      el.dataset.kind = sprite ? 'sprite' : 'svg';
      el.dataset.pet = kit.kind;
      el.setAttribute('aria-hidden', 'true');
      el.style.width = `${petW}px`;
      el.style.height = `${petH}px`;
      el.innerHTML = `<div class="qmx-pet-flip">${sprite ? '<div class="qmx-pet-sprite"></div>' : kit.svg}</div>`;
      document.body.append(el);

      const bubble = document.createElement('div');
      bubble.className = 'qmx-pet-bubble';
      bubble.dataset.pet = kit.kind;
      bubble.setAttribute('aria-hidden', 'true');
      bubble.hidden = true;
      document.body.append(bubble);

      const spriteEl = el.querySelector<HTMLElement>('.qmx-pet-sprite');
      let spriteState = '';
      function setSpriteState(mode: string) {
        if (!sprite || !spriteEl) return;
        const wanted = SPRITE_STATE[mode] ?? 'idle';
        const candidate = sprite.states[wanted];
        const usable = candidate && safeName(candidate.src) && candidate.frames >= 1 && candidate.fps > 0;
        const state = usable ? candidate : sprite.states.idle;
        const key = state === sprite.states.idle ? 'idle' : wanted;
        if (key === spriteState) return;
        spriteState = key;
        const frames = Math.max(1, Math.floor(state.frames));
        spriteEl.style.setProperty('--sheet-w', `${petW * frames}px`);
        spriteEl.style.backgroundImage = `url("${base}themes/${themeId}/pet/${state.src}")`;
        spriteEl.style.backgroundSize = `${petW * frames}px ${petH}px`;
        spriteEl.style.animation = `qmx-sprite ${frames / state.fps}s steps(${frames}) infinite`;
      }

      // ───── 状态 ─────
      const world = { width: innerWidth, height: innerHeight, petW, petH, margin: PET_DEFAULTS.margin, groundGap: PET_DEFAULTS.groundGap };
      let start: { x: number; dir: number } | undefined;
      try {
        const raw = sessionStorage.getItem(STORE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw);
          if (Number.isFinite(parsed?.x)) start = { x: parsed.x, dir: parsed.dir };
        }
      } catch {
        /* 没有存档就从左边走进来 */
      }
      const pet = createPet(world, Math.random, start);

      const pointer = { x: innerWidth / 2, y: innerHeight / 2 };
      let lastLine = -1;
      let typing: { text: string; i: number; nextAt: number; hideAt: number } | null = null;
      let chatterIn = 70 + Math.random() * 50;
      let endSaid = false;
      let raf = 0;
      let last = performance.now();
      let renderedState = '';
      let renderedDir = 0;
      let lastEye = '';

      function say(text: string) {
        bubble.hidden = false;
        bubble.textContent = '';
        typing = { text, i: 0, nextAt: performance.now(), hideAt: 0 };
      }
      function sayRandom() {
        let i = Math.floor(Math.random() * kit.lines.length);
        if (i === lastLine) i = (i + 1) % kit.lines.length;
        lastLine = i;
        say(kit.lines[i]);
      }

      function render(now: number) {
        el.style.transform = `translate3d(${pet.x.toFixed(1)}px, ${pet.y.toFixed(1)}px, 0)`;
        if (pet.mode !== renderedState) {
          renderedState = pet.mode;
          el.dataset.state = pet.mode;
          setSpriteState(pet.mode);
        }
        if (pet.dir !== renderedDir) {
          renderedDir = pet.dir;
          el.style.setProperty('--dir', String(faceRight ? pet.dir : -pet.dir));
        }

        if (!sprite) {
          // 眼睛看向鼠标(镜像翻转时左右要反过来)
          const flip = faceRight ? pet.dir : -pet.dir;
          const ex = Math.round(clamp((pointer.x - (pet.x + petW / 2)) / 70, -3, 3) * flip * 2) / 2;
          const ey = Math.round(clamp((pointer.y - (pet.y + petH * 0.35)) / 70, -2, 2) * 2) / 2;
          const eye = `${ex},${ey}`;
          if (eye !== lastEye) {
            lastEye = eye;
            el.style.setProperty('--ex', String(ex));
            el.style.setProperty('--ey', String(ey));
          }
        }

        // 气泡：逐字打出，说完停留一会儿再收起
        if (typing) {
          while (now >= typing.nextAt && typing.i < typing.text.length) {
            typing.i++;
            bubble.textContent = typing.text.slice(0, typing.i);
            typing.nextAt += 38;
            if (typing.i % 2 === 0) audio.tick();
          }
          if (typing.i >= typing.text.length && typing.hideAt === 0) typing.hideAt = now + 2600 + typing.text.length * 80;
          if (typing.hideAt && now > typing.hideAt) {
            bubble.hidden = true;
            typing = null;
          }
        }
        if (!bubble.hidden) {
          const bw = bubble.offsetWidth;
          const bh = bubble.offsetHeight;
          const bx = clamp(pet.x + petW / 2 - bw / 2, 8, Math.max(8, world.width - bw - 8));
          let by = pet.y - bh - 10;
          if (by < 8) by = pet.y + petH + 10; // 头顶放不下就放到脚下
          bubble.style.transform = `translate3d(${bx.toFixed(1)}px, ${by.toFixed(1)}px, 0)`;
        }
      }

      function frame(now: number) {
        raf = requestAnimationFrame(frame);
        const dt = Math.min((now - last) / 1000, 0.05);
        last = now;

        for (const event of stepPet(pet, dt, world, Math.random, cfg)) {
          if (event === 'land') kit.onLand(audio);
          if (event === 'arrived' && !sessionStorage.getItem(greetedKey)) {
            try { sessionStorage.setItem(greetedKey, '1'); } catch { /* 忽略 */ }
            poke(pet);
            say(kit.greeting);
          }
        }

        // 偶尔自言自语：只在空闲且没有在说话时
        if (!typing && (pet.mode === 'idle' || pet.mode === 'walk')) {
          chatterIn -= dt;
          if (chatterIn <= 0) {
            sayRandom();
            chatterIn = 70 + Math.random() * 50;
          }
        }
        render(now);
      }

      // ───── 交互 ─────
      let drag: { id: number; offX: number; offY: number; sx: number; sy: number; t0: number; moved: number; lx: number; ly: number; lt: number; vx: number; vy: number } | null = null;

      el.addEventListener('pointerdown', (e) => {
        if (e.button !== 0) return;
        e.preventDefault();
        el.setPointerCapture(e.pointerId);
        grab(pet);
        const t = performance.now();
        drag = { id: e.pointerId, offX: e.clientX - pet.x, offY: e.clientY - pet.y, sx: e.clientX, sy: e.clientY, t0: t, moved: 0, lx: e.clientX, ly: e.clientY, lt: t, vx: 0, vy: 0 };
      });
      el.addEventListener('pointermove', (e) => {
        if (!drag || e.pointerId !== drag.id) return;
        dragTo(pet, e.clientX - drag.offX, e.clientY - drag.offY, world);
        const t = performance.now();
        const span = (t - drag.lt) / 1000;
        if (span > 0.016) {
          drag.vx = (e.clientX - drag.lx) / span;
          drag.vy = (e.clientY - drag.ly) / span;
          drag.lx = e.clientX;
          drag.ly = e.clientY;
          drag.lt = t;
        }
        drag.moved = Math.max(drag.moved, Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy));
      });
      const endDrag = (e: PointerEvent) => {
        if (!drag || e.pointerId !== drag.id) return;
        const click = drag.moved < 5 && performance.now() - drag.t0 < 500;
        if (click) {
          pet.mode = 'idle';
          pet.timer = 1;
          poke(pet);
          kit.onPoke(audio);
          sayRandom();
        } else {
          // 松手前鼠标已经停住了，就不要带着旧速度扔出去
          const stale = performance.now() - drag.lt > 80;
          release(pet, stale ? 0 : drag.vx * 0.6, stale ? 0 : drag.vy * 0.6);
        }
        drag = null;
      };
      el.addEventListener('pointerup', endDrag);
      el.addEventListener('pointercancel', endDrag);

      let lastActivity = 0;
      const onActivity = (e?: Event) => {
        if (e && 'clientX' in e) {
          pointer.x = (e as PointerEvent).clientX;
          pointer.y = (e as PointerEvent).clientY;
        }
        const now = performance.now();
        if (now - lastActivity < 250) return;
        lastActivity = now;
        if (noteActivity(pet)) say(kit.wakeLine);
      };
      const onScroll = () => {
        onActivity();
        const doc = document.documentElement;
        if (!endSaid && doc.scrollHeight > innerHeight * 1.5 && scrollY + innerHeight >= doc.scrollHeight - 48) {
          endSaid = true;
          say(kit.endLine);
        }
      };
      const onResize = () => {
        world.width = innerWidth;
        world.height = innerHeight;
      };
      const onVisibility = () => {
        if (document.hidden) {
          cancelAnimationFrame(raf);
        } else {
          last = performance.now();
          raf = requestAnimationFrame(frame);
        }
      };
      const save = () => {
        try { sessionStorage.setItem(STORE_KEY, JSON.stringify({ x: pet.x, dir: pet.dir })); } catch { /* 忽略 */ }
      };

      window.addEventListener('pointermove', onActivity, { passive: true });
      window.addEventListener('pointerdown', onActivity, { passive: true });
      window.addEventListener('keydown', onActivity, { passive: true });
      window.addEventListener('scroll', onScroll, { passive: true });
      window.addEventListener('resize', onResize);
      window.addEventListener('pagehide', save);
      document.addEventListener('visibilitychange', onVisibility);

      kit.onBoot(audio);
      render(last);
      raf = requestAnimationFrame(frame);

      cleanup = () => {
        save();
        cancelAnimationFrame(raf);
        window.removeEventListener('pointermove', onActivity);
        window.removeEventListener('pointerdown', onActivity);
        window.removeEventListener('keydown', onActivity);
        window.removeEventListener('scroll', onScroll);
        window.removeEventListener('resize', onResize);
        window.removeEventListener('pagehide', save);
        document.removeEventListener('visibilitychange', onVisibility);
        el.remove();
        bubble.remove();
      };
    },

    stop() {
      generation++;
      cleanup?.();
      cleanup = null;
    },
  };
}
