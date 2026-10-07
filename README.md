# 游戏知识库

这是 QMX 工作室共同维护的游戏开发、设计、工具和项目经验知识库。

网站地址：<https://qmx-gameorganization.github.io/qmx-Gameknowledge/>

## 本地运行

需要 Node.js 22 或更高版本：

```bash
npm install
npm run dev
```

打开 <http://localhost:4321/qmx-Gameknowledge/> 预览网站。

## 写作方式

网站使用 Astro Starlight 构建。左侧导航根据 `src/content/docs/` 下的文件夹自动生成，不需要手动编辑导航配置。

- 长期知识库放在 `src/content/docs/knowledge/`。
- 项目文章放在 `src/content/docs/projects/`。
- 使用指南放在 `src/content/docs/guide/`。
- 每篇文章是一个 `.md` 文件，文件名使用英文短名。
- 文件夹会自动成为导航层级，文件名会成为导航条目。

文章示例：

```markdown
---
title: 我的文章
description: 文章摘要
---

## 第一章

这里写正文。
```

## 发布流程

向 `main` 分支提交代码后，GitHub Actions 会自动执行 `npm run build` 并发布到 GitHub Pages。
