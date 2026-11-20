---
title: "Unity 运行时与资源"
description: "从 PlayerLoop、对象生命周期、序列化和资源加载理解 Unity 项目运行逻辑。"
sidebar:
  order: 12
---

## 必学范围

- 场景、GameObject、Component、Prefab 和 ScriptableObject 的身份差异。
- `Awake`、`OnEnable`、`Start`、`Update`、`FixedUpdate`、`LateUpdate` 和销毁顺序。
- PlayerLoop、输入、物理、动画、渲染和脚本更新之间的关系。
- 序列化字段、Prefab 覆盖、资源引用和运行时实例。
- Resources、AssetBundle、Addressables、异步加载和依赖释放。
- 场景切换、对象池、异步任务和取消操作的生命周期。
- 编辑器脚本、Custom Inspector、AssetPostprocessor 和资源检查。

## 学习方法

每学一个 API，都回答四个问题：

| 问题 | 示例 |
| --- | --- |
| 谁创建它 | 场景、Prefab、工厂、Addressables 还是脚本 |
| 谁拥有它 | 场景、系统、对象池还是异步任务 |
| 什么时候可用 | 加载完成、激活、初始化还是下一帧 |
| 什么时候释放 | 销毁、卸载、场景切换还是引用归零 |

## 最小实践

做一个可重开的战斗场景，包含玩家、敌人、武器、UI 和配置。要求支持：

- 场景进入和退出。
- 异步加载和失败重试。
- 敌人对象池。
- 配置资产和运行时状态分离。
- 场景切换后事件不重复触发。
- 调试面板显示对象创建、销毁和加载状态。

## 验收

能画出从启动、加载、进入战斗、死亡、重开到退出的生命周期图，并说明每个对象的创建者、拥有者和释放者。
