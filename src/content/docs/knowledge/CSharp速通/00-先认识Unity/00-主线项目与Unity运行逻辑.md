---
title: "主线项目与 Unity 运行逻辑"
description: "先建立组件、场景和生命周期的整体模型，再用一个方块地牢作为贯穿全专栏的项目。"
sidebar:
  order: 0
---

## 本篇的项目结果

创建一个 3D Unity 项目和 `Dungeon` 场景，场景中至少有 `GameRoot`、`Player`、`Main Camera` 和 `Ground`。本篇结束时，玩家可以用 WASD 移动，摄像机跟随玩家，Console 能输出一次启动日志和一条逐帧状态日志。

后续所有 C# 练习都在这个项目中继续。临时演示脚本放到 `Assets/Speedrun/Labs/`，主线代码放到 `Assets/Speedrun/Game/`，避免每篇重复创建同名 `Health`、`Enemy` 或 `GameManager`。

## Unity 中的四个基本词

| 概念 | 在场景中的角色 | 本项目中的例子 |
| --- | --- | --- |
| `GameObject` | 场景中的实体容器 | `Player`、`Enemy_Slime`、`Exit` |
| `Component` | 附加到对象上的能力 | `Transform`、`BoxCollider`、`Rigidbody`、脚本 |
| `MonoBehaviour` | 能被 Unity 生命周期驱动的脚本组件 | `PlayerController`、`CameraFollow` |
| Prefab | 可重复生成的对象模板 | 敌人、陷阱、掉落物 |

`Transform`、`Collider` 和脚本不是三种互相独立的对象：它们共同挂在一个 `GameObject` 上，通过 `GetComponent<T>()` 或 Inspector 引用协作。理解这层关系后，才知道为什么脚本通常不直接 `new PlayerController()`：`MonoBehaviour` 的实例由 Unity 和场景共同管理。

## 一帧里发生什么

可以先用下面的简化顺序观察项目：

```text
读取输入
  → Update：根据输入更新意图和非物理状态
  → FixedUpdate：在固定物理步中移动 Rigidbody（需要时）
  → 碰撞/触发器回调
  → LateUpdate：让摄像机追上玩家
  → 渲染当前 Transform 和 UI
```

实际调用还会受到启用状态、场景加载和脚本执行顺序影响，因此不要把“代码写在 Update 里”理解成“它一定最后执行”。`Awake`、`OnEnable`、`Start` 的职责在本专栏中固定为：准备自己、订阅事件、读取其他对象。

## 建立主线场景

1. 新建 3D 项目和 `Assets/Speedrun/Scenes/Dungeon.unity`。
2. 新建空物体 `GameRoot`，挂载 `GameBootstrap`；新建 Cube `Player`，挂载 `PlayerController` 和 `Rigidbody`。
3. 新建 Plane `Ground`，保留 Collider；将 `Player` 放在地面上方一点。
4. 让 `Main Camera` 挂载 `CameraFollow`，把 `Player` 拖到 `Target`。
5. 创建 `Assets/Speedrun/Prefabs`、`Scripts`、`UI`、`Scenes` 四个目录。

## 第一份可运行脚本

```csharp
using UnityEngine;

/// <summary>主线项目的最小启动器：只记录启动，不保存游戏状态。</summary>
public sealed class GameBootstrap : MonoBehaviour
{
    private void Awake()
    {
        Debug.Log("Dungeon bootstrap: Awake");
    }

    private void Start()
    {
        Debug.Log("Dungeon bootstrap: Start");
    }
}
```

```csharp
using UnityEngine;

/// <summary>把输入转换为玩家的平面位移，先不引入攻击或敌人规则。</summary>
public sealed class PlayerController : MonoBehaviour
{
    [SerializeField] private float speed = 5f;

    private void Update()
    {
        Vector3 input = new Vector3(
            Input.GetAxisRaw("Horizontal"),
            0f,
            Input.GetAxisRaw("Vertical"));

        if (input.sqrMagnitude > 1f)
            input.Normalize();

        transform.position += input * speed * Time.deltaTime;
    }
}
```

```csharp
using UnityEngine;

/// <summary>摄像机只负责跟随，不把玩家输入和镜头规则混在一起。</summary>
public sealed class CameraFollow : MonoBehaviour
{
    [SerializeField] private Transform target;
    [SerializeField] private Vector3 offset = new Vector3(0f, 8f, -6f);

    private void LateUpdate()
    {
        if (target == null) return;
        transform.position = target.position + offset;
        transform.LookAt(target);
    }
}
```

## 验收与排错

- Play 后玩家能移动，停止 Play 后对象回到编辑器保存的位置；
- Console 先出现 `Awake` 再出现 `Start`；
- `CameraFollow.Target` 为空时，镜头不报错但不会跟随；
- 玩家移动速度不随帧率明显改变，因为位移乘了 `Time.deltaTime`；
- 若脚本不执行，先检查文件名、类名、Console 编译错误和脚本是否真的挂在对象上；
- 若触发器或 Rigidbody 后续不工作，检查至少一方是否有 Rigidbody，以及 Collider 的 `Is Trigger` 是否符合当前目标。

## 下一篇会复用什么

下一篇从这里继续：把输入值、速度、玩家名称和生命值加入同一个 `PlayerController`/`PlayerStats` 项目上下文；不再新建一个脱离场景的 `Lab` 示例。
## 项目应用决策：先看运行链，再学语法

这篇不是 Unity 菜单导览，而是后面所有语法的运行上下文：场景保存对象和组件，生命周期驱动脚本，脚本修改状态，UI 和渲染显示结果。后续每篇文章都要能指出自己处在这条链的哪一段。

如果一个例子无法说明“哪个 GameObject 挂了它、谁调用它、状态改在哪里、如何观察结果”，它就只能算控制台语法练习，不能算主线项目代码。验收时从空场景启动到玩家移动，逐项在 Hierarchy、Inspector 和 Console 找到对应证据。


> **本篇主线标记**：本篇的组件、生命周期和场景装配是 `【主线实践】`；代码片段只负责建立运行载体，具体装配见[项目启动与场景装配](./05-主线实践项目启动与场景装配/)。
