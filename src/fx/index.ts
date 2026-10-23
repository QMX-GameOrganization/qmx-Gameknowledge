// 主题特效控制器。
//
// 每个有特效的主题对应 src/fx/ 下的一个模块，导出 default: FxModule。
// 切到该主题时才动态加载(其他主题的访客不会下载这部分代码)，切走时调用 stop() 清理。
//
// 新增主题特效：写一个模块，在下面的 registry 里登记 id 即可。

import { AudioManager } from './audio';

export interface FxContext {
  root: HTMLElement;
  audio: AudioManager;
  /** 站点 base，例如 /qmx-Gameknowledge/ ，末尾带斜杠 */
  base: string;
  /** 用户系统设置了「减少动态效果」 */
  reduced: boolean;
  /** 窄屏设备：模块应降低数量 / 尺寸 */
  compact: boolean;
}

export interface FxModule {
  start(ctx: FxContext): void | Promise<void>;
  stop(): void;
}

type Loader = () => Promise<{ default: FxModule }>;

const registry: Record<string, Loader> = {
  starry: () => import('./starry'),
  rhodes: () => import('./rhodes'),
};

const KEY = 'qmx-fx';

export function initFx(base: string) {
  const root = document.documentElement;
  const audio = new AudioManager();
  const reducedQuery = matchMedia('(prefers-reduced-motion: reduce)');
  const compactQuery = matchMedia('(max-width: 50rem), (pointer: coarse)');

  let enabled = true;
  try {
    enabled = localStorage.getItem(KEY) !== 'off';
  } catch {
    /* 读不到就用默认值 */
  }

  let current: FxModule | null = null;
  let token = 0; // 防止快速切换主题时，慢加载的旧模块覆盖新主题

  async function apply(themeId: string) {
    const mine = ++token;
    current?.stop();
    current = null;
    delete root.dataset.qmxFxActive;

    const load = registry[themeId];
    if (!load) {
      delete root.dataset.qmxHasFx;
      return;
    }
    root.dataset.qmxHasFx = themeId;
    if (!enabled) return;

    try {
      const mod = (await load()).default;
      if (mine !== token) return; // 加载期间主题又变了
      current = mod;
      root.dataset.qmxFxActive = themeId;
      await mod.start({ root, audio, base, reduced: reducedQuery.matches, compact: compactQuery.matches });
    } catch (error) {
      // 特效是锦上添花，出错不能影响阅读。
      console.warn('[qmx-fx] 主题特效启动失败：', error);
      current?.stop();
      current = null;
      delete root.dataset.qmxFxActive;
    }
  }

  const currentTheme = () => root.dataset.qmxTheme ?? 'starry';

  document.addEventListener('qmx-themechange', (event) => {
    void apply((event as CustomEvent<{ id: string }>).detail.id);
  });

  // 开关按钮：ThemeSelect 里渲染，这里统一接管(页面里可能有多份，例如桌面顶栏和移动端菜单)。
  const fxButtons = () => document.querySelectorAll<HTMLButtonElement>('[data-qmx-fx-toggle]');
  const soundButtons = () => document.querySelectorAll<HTMLButtonElement>('[data-qmx-sound-toggle]');

  function syncButtons() {
    fxButtons().forEach((b) => b.setAttribute('aria-pressed', String(enabled)));
    soundButtons().forEach((b) => b.setAttribute('aria-pressed', String(audio.enabled)));
  }

  document.addEventListener('click', async (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;

    if (target.closest('[data-qmx-fx-toggle]')) {
      enabled = !enabled;
      try {
        localStorage.setItem(KEY, enabled ? 'on' : 'off');
      } catch {
        /* 忽略 */
      }
      syncButtons();
      void apply(currentTheme());
    } else if (target.closest('[data-qmx-sound-toggle]')) {
      await audio.setEnabled(!audio.enabled);
      syncButtons();
    }
  });

  syncButtons();
  void apply(currentTheme());
}
