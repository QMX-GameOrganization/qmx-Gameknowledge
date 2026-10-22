const STORAGE_KEY = "qmx-theme-preferences";

const presets = {
  ocean: { name: "深海蓝", accent: "#38bdf8", accentStrong: "#0ea5e9", bg: "#07111f", panel: "#0d1b2e", text: "#e5f3ff" },
  forest: { name: "松林绿", accent: "#34d399", accentStrong: "#10b981", bg: "#071711", panel: "#10251b", text: "#e5fff2" },
  sunset: { name: "落日橙", accent: "#fb923c", accentStrong: "#f97316", bg: "#1b100c", panel: "#2a1811", text: "#fff3e8" },
  lavender: { name: "薰衣草", accent: "#c084fc", accentStrong: "#a855f7", bg: "#151022", panel: "#23183a", text: "#f7edff" }
};

const defaults = { preset: "ocean", accent: presets.ocean.accent, wallpaper: "", opacity: 0.86, blur: 18 };
const load = () => { try { return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") }; } catch { return { ...defaults }; } };
const save = (state) => localStorage.setItem(STORAGE_KEY, JSON.stringify(state));

function apply(state) {
  const preset = presets[state.preset] || presets.ocean;
  const root = document.documentElement;
  root.style.setProperty("--qmx-accent", state.accent || preset.accent);
  root.style.setProperty("--qmx-accent-strong", preset.accentStrong);
  root.style.setProperty("--qmx-wallpaper", state.wallpaper ? `url("${state.wallpaper.replace(/"/g, "\\\"")}")` : "none");
  root.style.setProperty("--qmx-panel-opacity", state.opacity);
  root.style.setProperty("--qmx-panel-blur", `${state.blur}px`);
  root.dataset.qmxTheme = state.preset;
  root.dataset.qmxWallpaper = state.wallpaper ? "on" : "off";
}

function mount() {
  if (document.querySelector(".qmx-theme-toggle")) return;
  const state = load();
  apply(state);
  const toggle = document.createElement("button");
  toggle.className = "qmx-theme-toggle";
  toggle.type = "button";
  toggle.setAttribute("aria-label", "打开主题工作台");
  toggle.innerHTML = "<span aria-hidden=\"true\">✦</span><span>主题</span>";
  const panel = document.createElement("aside");
  panel.className = "qmx-theme-panel";
  panel.setAttribute("aria-label", "主题工作台");
  panel.innerHTML = `<div class="qmx-theme-panel__head"><div><span class="qmx-kicker">WORKSPACE</span><h2>主题工作台</h2></div><button class="qmx-theme-close" type="button" aria-label="关闭">×</button></div>
    <p class="qmx-theme-lede">把知识库调成你喜欢的节奏。设置会自动保存在当前浏览器。</p>
    <section><div class="qmx-theme-label">预设主题</div><div class="qmx-theme-grid">${Object.entries(presets).map(([key, item]) => `<button type="button" class="qmx-preset" data-preset="${key}"><span style="--swatch:${item.accent}"></span><b>${item.name}</b><small>${key}</small></button>`).join("")}</div></section>
    <section><div class="qmx-theme-label">自定义强调色 <output class="qmx-color-value">${state.accent}</output></div><div class="qmx-color-row"><input class="qmx-color" type="color" value="${state.accent}" aria-label="强调色"><input class="qmx-color-text" value="${state.accent}" spellcheck="false" aria-label="强调色十六进制值"></div></section>
    <section><label class="qmx-theme-label" for="qmx-wallpaper">壁纸地址</label><input id="qmx-wallpaper" class="qmx-wallpaper" value="${state.wallpaper}" placeholder="https://… 或 /images/wallpaper.jpg"><div class="qmx-wallpaper-hint">支持远程图片与站点 public 目录中的图片</div></section>
    <section><label class="qmx-theme-label" for="qmx-opacity">面板透明度 <output class="qmx-opacity-value">${Math.round(state.opacity * 100)}%</output></label><input id="qmx-opacity" class="qmx-range" type="range" min="0.64" max="0.98" step="0.01" value="${state.opacity}"></section>
    <section><label class="qmx-theme-label" for="qmx-blur">背景模糊 <output class="qmx-blur-value">${state.blur}px</output></label><input id="qmx-blur" class="qmx-range" type="range" min="0" max="32" step="1" value="${state.blur}"></section>
    <button type="button" class="qmx-reset">恢复默认设置</button>`;
  document.body.append(toggle, panel);
  const update = () => { save(state); apply(state); panel.querySelector(".qmx-color-value").textContent = state.accent; panel.querySelector(".qmx-opacity-value").textContent = `${Math.round(state.opacity * 100)}%`; panel.querySelector(".qmx-blur-value").textContent = `${state.blur}px`; };
  toggle.addEventListener("click", () => { panel.classList.toggle("is-open"); toggle.setAttribute("aria-expanded", panel.classList.contains("is-open")); });
  panel.querySelector(".qmx-theme-close").addEventListener("click", () => panel.classList.remove("is-open"));
  panel.querySelectorAll(".qmx-preset").forEach((button) => button.addEventListener("click", () => { state.preset = button.dataset.preset; state.accent = presets[state.preset].accent; panel.querySelector(".qmx-color").value = state.accent; panel.querySelector(".qmx-color-text").value = state.accent; update(); }));
  panel.querySelector(".qmx-color").addEventListener("input", (event) => { state.accent = event.target.value; panel.querySelector(".qmx-color-text").value = state.accent; update(); });
  panel.querySelector(".qmx-color-text").addEventListener("change", (event) => { if (/^#[\da-f]{6}$/i.test(event.target.value)) { state.accent = event.target.value; panel.querySelector(".qmx-color").value = state.accent; update(); } });
  panel.querySelector(".qmx-wallpaper").addEventListener("change", (event) => { state.wallpaper = event.target.value.trim(); update(); });
  panel.querySelector("#qmx-opacity").addEventListener("input", (event) => { state.opacity = Number(event.target.value); update(); });
  panel.querySelector("#qmx-blur").addEventListener("input", (event) => { state.blur = Number(event.target.value); update(); });
  panel.querySelector(".qmx-reset").addEventListener("click", () => { Object.assign(state, defaults); panel.querySelector(".qmx-color").value = state.accent; panel.querySelector(".qmx-color-text").value = state.accent; panel.querySelector(".qmx-wallpaper").value = ""; panel.querySelector("#qmx-opacity").value = state.opacity; panel.querySelector("#qmx-blur").value = state.blur; update(); });
}

document.addEventListener("DOMContentLoaded", mount);
document.addEventListener("astro:page-load", mount);


