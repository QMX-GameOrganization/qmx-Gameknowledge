---
title: "4. 输入适配、资源分层与系统边界"
description: "用 InputAction 接入共享输入契约，再以资源类型、系统职责和受控依赖组织项目。"
sidebar:
  order: 4
---

## InputAction 负责采集，规则负责玩法

Unity 新输入系统的 `Keyboard.current` 是设备读取接口；`InputAction` 和 `InputActionMap` 可以把多种设备绑定到 Move、Jump、Reload 等动作。希望支持手柄、重绑定和统一启停时，采集端适合直接使用后者。

```text
键盘 / 手柄 → Gameplay ActionMap
            → 输入来源生成快照
AI / 回放 ──→ 同一输入快照契约
            → 缓冲 → 有序规则 → 所属执行器 → 实际事实
```

Action 名为 Reload，只表示来源观察到了换弹需求；它不代表资源充分、允许打断或换弹已经开始。跨系统权限仍在规则层，武器库存和当前阶段仍由执行器管理。各执行系统无需分别绑定设备。

输入来源应明确拥有映射的启停与释放。禁用角色、失能或切换来源时，丢弃未采样边沿和待处理请求；恢复时等待新输入，不能把旧按键重新解释成新请求。同一时刻只允许一个来源取得该角色的输入控制权。重新绑定设备不应重置武器执行事实。

Update 与 FixedUpdate 不是一一对应，仍需[上一章的缓冲协议](../03-state-lifecycle/)。动作回调汇总边沿，快照表达一次采样，固定步消费被接纳事件，三者职责不同。

## 顶层按资源类型，代码内部按系统

同一个系统会使用代码、动画、参数和 Prefab，但它们具有不同的导入与修改方式。顶层先按资源类型分，再在代码内部按系统及职责分层，便于查找和限制改动范围。

```text
Assets/Game/
  Code/
    Character/{Contracts,Input,Rules,Blackboard,Lifecycle,Actions}
    Movement/{Driver,Motor,Traversal,Presentation,Editor}
    Animation/{ThirdPerson,Editor}
  Art/{Characters,Weapons,Environments,Animation,Materials}
  Config/{Input,Movement,Weapons,Catalogs}
  Prefabs/{Characters,Weapons,Environments}
  Scenes/
  Documentation/
```

这是职责示例，无需提前创建没有内容的目录。程序创建的动作映射属于代码；若采用 `.inputactions` 资产，则放在对应配置目录。路径迁移时不要把所有 `.asset` 都视为配置：Mesh 的 `.asset` 属于美术资源，动作参数 ScriptableObject 才属于配置。

Unity 资源搬家需要保留原 `.meta` 与 GUID，并检查硬编码和动态拼接路径。生成器也必须同步修改：从 Art 读取模型与动画，向 Prefabs 写预制体，向 Config 写参数，验证报告归 Documentation。仅搬现有文件却不改生成器，会在下次执行时重新产生旧目录。

## 每个系统、每个职责层写清约束

可以在系统入口及职责层放置 `AGENTS.md`，使后续任务在访问前读到所属边界。文档应包含：

- 本层解决什么问题、拥有哪些数据，例如 Motor 拥有胶囊位移与碰撞结果。
- 可依赖什么、通过哪个契约交换信息，例如动画读取只读表现快照。
- 禁止什么，例如动画改胶囊高度，输入层改弹药，Motor 反向读取玩家设备。
- 跨层修改应同步哪些接口和验证，哪些场景与资源需要保留。

约束文档需要和代码边界配合。独立程序集可限制直接引用；只读值和受控写口可限制数据归属；静态检查可以发现已知越界依赖；编译与运行测试负责验证接入后的行为。文档本身不能阻止任意反射或运行时绕过。

规则之间不互相调用，不等于彼此完全独立：它们仍通过确定顺序和更新事实协作。省去通用的运行时“审核规则的审核器”，也不等于省去开发时的代码审核。新增规则仍要检查顺序、消费时机、失败回退和写入权，见[有序规则章节](../02-ordered-rules/)。

## 结构验收与行为验收分别取证

资源迁移可记录旧路径、新路径、文件 hash 和 meta GUID，证明哪些内容保持不变。实际 Unity 验证则检查资源能否加载、Prefab 是否缺脚本、程序集能否编译、原运动回归和新增互斥/打断案例是否通过。

清理时删除已确认无调用的旧实现，并更新活跃测试与生成工具；历史基线和验证证据可以保留，但应明确它们不是当前执行入口。目录清晰、类名更合理不能证明性能提升；性能需要固定输入和测量口径另行验证。
