import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

export default defineConfig({
  site: "https://qmx-gameorganization.github.io",
  base: "/qmx-Gameknowledge",
  integrations: [
    starlight({
      title: "游戏知识库",
      description: "由工作室共同维护的游戏开发、设计与运营知识库",
      defaultLocale: "root",
      locales: {
        root: { label: "简体中文", lang: "zh-CN" }
      },
      customCss: ["./src/styles/custom.css"],
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

