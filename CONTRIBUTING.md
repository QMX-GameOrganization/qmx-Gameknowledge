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

## 主题特效（动画、桌宠、音效）

目前星夜（星空会被鼠标驱散）和罗德岛（桌宠）带特效。代码在 `src/fx/`，样式在 `src/styles/fx.css`。

- 新增特效：在 `src/fx/` 写一个模块（`start` / `stop`，参考 `starry.ts`），再到 `src/fx/index.ts` 的 `registry` 里登记主题 id。切到该主题时才会加载，切走时自动清理。
- 音效全部由 Web Audio 合成，默认关闭，用户点「音效」开关后才会出声。
- 系统开启「减少动态效果」时，星夜只显示静态星空，罗德岛不显示桌宠。
- 纯逻辑部分（星星物理、桌宠状态机）可以直接测试：`node scripts/test-fx.mjs`。

### 自定义桌宠素材

仓库不包含任何第三方游戏素材，默认使用内置的原创形象。想换成自己有权使用的角色：把横向排列的精灵图（PNG，每帧宽高相同）和 `pet.json` 放进 `public/themes/rhodes/pet/`：

```json
{
  "size": [128, 128],
  "faceRight": true,
  "states": {
    "idle": { "src": "idle.png", "frames": 6, "fps": 8 },
    "walk": { "src": "walk.png", "frames": 8, "fps": 10 },
    "sleep": { "src": "sleep.png", "frames": 4, "fps": 3 },
    "wave": { "src": "wave.png", "frames": 6, "fps": 8 },
    "drag": { "src": "drag.png", "frames": 1, "fps": 1 },
    "fall": { "src": "fall.png", "frames": 1, "fps": 1 }
  }
}
```

只有 `idle` 是必须的，缺少的状态会用 `idle`。`size` 是单帧的像素尺寸，`faceRight` 表示图片里的角色是否朝右，文件名只能包含字母、数字、下划线、点和连字符。素材的版权和授权由放入者负责，并请在同目录的 `NOTICE.txt` 里写明来源。注意：Spine 官方运行时要求集成者持有 Spine 编辑器授权，所以这里使用普通精灵图，没有引入 Spine 运行时。

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
