/**
 * 主题注册表。
 *
 * 这里只登记「有哪些主题、亮色还是暗色」。具体颜色全部写在
 * src/styles/themes.css 里（每个主题一个 :root[data-qmx-theme="id"] 块）。
 *
 * 新增主题的步骤：
 *   1. 在下面的数组里加一行；
 *   2. 在 themes.css 里复制一个同模式的主题块，改颜色；
 *   3. 运行 `npm run build`，再用 `node scripts/check-contrast.mjs` 检查对比度。
 *
 * mode 决定 Starlight 的 data-theme（代码块配色、提示框配色都跟着它走），
 * 必须和主题实际的明暗一致，否则会出现「深色背景配深色文字」。
 */

/** @typedef {{ id: string, label: string, mode: 'light' | 'dark' }} QmxTheme */

/** @type {QmxTheme[]} */
export const themes = [
  // 暗色
  { id: 'starry', label: '星夜', mode: 'dark' },
  { id: 'pixel', label: '像素终端', mode: 'dark' },
  { id: 'miku', label: '初音未来', mode: 'dark' },
  { id: 'blocks', label: '方块世界', mode: 'dark' },
  { id: 'rhodes', label: '罗德岛', mode: 'dark' },
  { id: 'mocha', label: 'Catppuccin 摩卡', mode: 'dark' },
  { id: 'nord', label: 'Nord 极光', mode: 'dark' },
  { id: 'deepsea', label: '深海蓝（鲸鱼）', mode: 'dark' },
  { id: 'neon', label: '赛博霓虹', mode: 'dark' },
  { id: 'contrast', label: '高对比度', mode: 'dark' },
  // 亮色
  { id: 'sakura', label: '春樱', mode: 'light' },
  { id: 'summer', label: '夏日天气', mode: 'light' },
  { id: 'github', label: 'GitHub 经典', mode: 'light' },
  { id: 'latte', label: 'Catppuccin 拿铁', mode: 'light' },
  { id: 'paper', label: '护眼纸张', mode: 'light' },
];

/** localStorage 键名 */
export const STORAGE_KEY = 'qmx-theme';

/** 首次访问时，按系统偏好选择的默认主题 */
export const defaultThemes = { dark: 'starry', light: 'github' };
