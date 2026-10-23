# 贡献指南

## 新增知识库页面

1. 在 `src/content/docs/knowledge/` 下选择合适的目录创建 Markdown 文件。
2. 用文件夹组织章节；Starlight 会自动把目录结构生成到左侧导航。
3. 使用清晰的标题、步骤和代码示例，并注明适用版本。

## 新增项目文章

在 `src/content/docs/projects/` 中创建 Markdown 文件：

```yaml
---
title: 我的项目文章
description: 文章摘要
---
```

不需要修改导航配置。文件名会成为页面路径，所在文件夹会成为导航层级。

## 图片

图片放在 `public/assets/`，正文中使用 `/qmx-Gameknowledge/assets/文件名.png` 引用。

## 新增主题

1. 在 `src/themes.mjs` 里登记：`id`、显示名称、`mode`（`light` 或 `dark`，必须和主题实际明暗一致）。
2. 在 `src/styles/themes.css` 里复制一个同明暗模式的主题块，改颜色。令牌含义见 `src/styles/custom.css` 顶部。
3. 运行 `node scripts/check-contrast.mjs`，所有主题文字对比度需达到 4.5:1 以上。

使用第三方调色板或素材时，请在 `public/themes/` 下对应目录的 `NOTICE.txt` 里写明来源和协议。

## 提交规范

提交信息建议使用以下前缀：

- `docs:` 新增或修改知识内容
- `fix:` 修正错误
- `style:` 调整网站样式
- `chore:` 修改构建或工作流

提交前请在本地执行：

```bash
npm install
npm run build
```
