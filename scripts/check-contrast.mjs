// 检查 src/styles/themes.css 里每个主题的文字对比度（WCAG 2.x）。
// 用法：node scripts/check-contrast.mjs
// 有任何一项低于阈值时以退出码 1 结束，可直接放进 CI。

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { themes } from "../src/themes.mjs";

const cssPath = fileURLToPath(new URL("../src/styles/themes.css", import.meta.url));
const css = readFileSync(cssPath, "utf8").replace(/\/\*[\s\S]*?\*\//g, "");

// 解析：每个 :root[data-qmx-theme="id"] 块里的 --qmx-* 十六进制颜色
const tokens = {};
for (const [, selector, body] of css.matchAll(/([^{}]+)\{([^}]*)\}/g)) {
  const ids = [...selector.matchAll(/data-qmx-theme="([\w-]+)"/g)].map((m) => m[1]);
  if (ids.length === 0) continue;
  const colors = {};
  for (const [, name, hex] of body.matchAll(/--qmx-([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) {
    colors[name] = hex.toLowerCase();
  }
  for (const id of ids) tokens[id] = { ...tokens[id], ...colors };
}

const toRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const toHex = (rgb) => "#" + rgb.map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");
const mix = (a, b, pctA) => toHex(toRgb(a).map((v, i) => (v * pctA) / 100 + (toRgb(b)[i] * (100 - pctA)) / 100));
const lum = (hex) => {
  const [r, g, b] = toRgb(hex).map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const ratio = (a, b) => {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

const required = ["bg", "nav", "sidebar", "panel", "text", "strong", "muted", "border", "code", "accent", "accent-2", "link"];
let failures = 0;
const rows = [];

for (const theme of themes) {
  const t = tokens[theme.id];
  if (!t) {
    console.error(`✗ ${theme.id}: themes.css 里没有找到这个主题`);
    failures++;
    continue;
  }
  const missing = required.filter((name) => !t[name]);
  if (missing.length) {
    console.error(`✗ ${theme.id}: 缺少令牌 ${missing.join(", ")}`);
    failures++;
    continue;
  }

  const gray3 = mix(t.muted, t.bg, 85); // 对应 --sl-color-gray-3
  const checks = [
    ["正文/背景", t.text, t.bg, 4.5],
    ["标题/背景", t.strong, t.bg, 4.5],
    ["次要/背景", t.muted, t.bg, 4.5],
    ["次要弱化/背景", gray3, t.bg, 4.5],
    ["正文/侧栏", t.text, t.sidebar, 4.5],
    ["次要/侧栏", t.muted, t.sidebar, 4.5],
    ["正文/顶栏", t.text, t.nav, 4.5],
    ["正文/浮层", t.text, t.panel, 4.5],
    ["正文/代码底", t.text, t.code, 4.5],
    ["链接/背景", t.link, t.bg, 4.5],
    ["链接/侧栏", t.link, t.sidebar, 4.5],
    ["当前项文字", t.bg, t.link, 4.5], // 侧栏当前项：底色是链接色，文字是背景色
    ["强调色/背景", t.accent, t.bg, 3],
  ];

  const bgLum = lum(t.bg);
  const modeOk = theme.mode === "dark" ? bgLum < 0.18 : bgLum > 0.4;
  if (!modeOk) {
    console.error(`✗ ${theme.id}: 登记为 ${theme.mode}，但背景亮度是 ${bgLum.toFixed(2)}`);
    failures++;
  }

  const bad = [];
  let min = Infinity;
  for (const [label, fg, bg, need] of checks) {
    const r = ratio(fg, bg);
    if (need === 4.5) min = Math.min(min, r);
    if (r < need) bad.push(`${label} ${r.toFixed(2)} < ${need}`);
  }
  failures += bad.length;
  rows.push({ 主题: `${theme.id} (${theme.mode})`, 文字最低对比度: min.toFixed(2), 结果: bad.length ? "✗ " + bad.join("；") : "✓" });
}

console.table(rows);
if (failures) {
  console.error(`\n共 ${failures} 项未通过`);
  process.exit(1);
}
console.log("\n全部主题通过（文字 ≥ 4.5:1，强调色 ≥ 3:1）");
