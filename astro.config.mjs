import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import { themes, defaultThemes, STORAGE_KEY } from "./src/themes.mjs";

const base = "/qmx-Gameknowledge";

// 首屏前同步执行：恢复上次选择的主题，并把明暗模式同步给 Starlight 的 data-theme。
// 放在 <head> 里是为了避免先显示默认主题、再跳到用户主题的闪烁。
const modes = Object.fromEntries(themes.map((t) => [t.id, t.mode]));
const themeBootstrap = `(function(){
var K=${JSON.stringify(STORAGE_KEY)},M=${JSON.stringify(modes)},D=${JSON.stringify(defaultThemes)};
var r=document.documentElement;
function put(k,v){try{localStorage.setItem(k,v)}catch(e){}}
function apply(id,persist){
  if(!M[id])id=D[matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'];
  r.dataset.qmxTheme=id;
  r.dataset.theme=M[id];
  put('starlight-theme',M[id]);
  if(persist)put(K,id);
  document.dispatchEvent(new CustomEvent('qmx-themechange',{detail:{id:id,mode:M[id]}}));
  return id;
}
var saved;try{saved=localStorage.getItem(K)}catch(e){}
window.QMXTheme={apply:function(id){return apply(id,true)}};
apply(saved,false);
})();`;

// 主题装饰图标的地址依赖 base，统一在这里生成成 CSS 变量，样式文件里不再写死路径。
const icon = (name) => `url("${base}/themes/fluent/${name}.svg")`;
const themeAssets = `:root{--qmx-icon-star:${icon("star")};--qmx-icon-sakura:${icon("cherry-blossom")};--qmx-icon-sun:${icon("sun")};}`;

export default defineConfig({
  site: "https://qmx-gameorganization.github.io",
  base,
  integrations: [
    starlight({
      title: "游戏知识库",
      description: "由工作室共同维护的游戏开发、设计与运营知识库",
      defaultLocale: "root",
      locales: {
        root: { label: "简体中文", lang: "zh-CN" }
      },
      customCss: ["./src/styles/custom.css", "./src/styles/themes.css", "./src/styles/fx.css", "./src/styles/ai.css", "./src/styles/lightbox.css"],
      head: [
        { tag: "script", content: themeBootstrap },
        { tag: "style", content: themeAssets }
      ],
      components: {
        ThemeSelect: "./src/components/ThemeSelect.astro",
        MobileMenuFooter: "./src/components/MobileMenuFooter.astro",
        Footer: "./src/components/Footer.astro"
      },
      social: [{
        icon: "github",
        label: "GitHub",
        href: "https://github.com/QMX-GameOrganization/qmx-Gameknowledge"
      }],
      sidebar: [
        { label: "知识库", autogenerate: { directory: "knowledge" } },
        { label: "项目文章", autogenerate: { directory: "projects" } },
        { label: "使用指南", autogenerate: { directory: "guide" } }
      ]
    })
  ]
});
