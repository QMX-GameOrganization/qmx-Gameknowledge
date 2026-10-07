---
title: 使用说明
description: 游戏知识库的写作和维护方式
---

# 使用说明

## 新增知识库章节

在 `src/content/docs/knowledge/` 下创建文件夹和 Markdown 文件，文件夹结构会自动变成左侧导航。

```text
knowledge/
└─ unity/
   ├─ index.md
   ├─ animation.md
   └─ tools.md
```

## 新增项目文章

在 `src/content/docs/projects/` 下创建 Markdown 文件。文章正文直接使用 Markdown，不需要修改导航配置。

```markdown
---
title: 我的项目文章
description: 文章摘要
---

## 项目背景

这里写正文。
```

## 本地预览

```bash
npm install
npm run dev
```

## 发布

提交到 `main` 分支后，GitHub Actions 会自动构建并发布到 GitHub Pages。
