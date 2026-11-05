---
title: "6.1 从 Main 到 MonoBehaviour：脚本在 Unity 里怎么跑"
description: "Unity 没有 Main，脚本是挂在物体上的组件；生命周期函数、Inspector 序列化、常用 API，以及前五章语法在 Unity 里的落点。"
sidebar:
  order: 1
---

> 适用版本：以 Unity 2021 LTS 到 Unity 6000.x 的 C# 脚本为准。输入示例用传统 `Input` 类；新版 Input System 的写法不同，不在本篇范围。

## 要点

- Unity 里**没有 `Main`**。引擎持有场景中的 `GameObject`，每个物体上挂着若干**组件**，你写的脚本就是一种组件。
- 脚本类要继承 `MonoBehaviour`，**文件名必须与类名一致**才能挂到物体上。
- 引擎在合适的时机自动调用你的方法：`Awake`、`Start`、`Update` 等，称为**生命周期函数**。
- 你在前五章学的语法，几乎每一条都能在 Unity API 里找到落点。

## 最小脚本

```csharp
using UnityEngine;                          // Unity 的类型都在这个命名空间

public class Hello : MonoBehaviour          // 文件名必须是 Hello.cs
{
    void Start()                            // 第一次 Update 之前调用一次
    {
        Debug.Log("游戏开始");
    }

    void Update()                           // 每一帧调用一次
    {
        Debug.Log("一帧过去了");
    }
}
```

把脚本拖到场景中某个物体上，点击播放，Console 窗口就会输出。注意这些方法没有 `public`、也没有任何地方"调用"它们，因为它们是被引擎按名字找到并调用的。

## 生命周期顺序

| 函数 | 调用时机 | 常见用途 |
| --- | --- | --- |
| `Awake` | 脚本实例被创建时，仅一次 | 初始化自身、缓存 `GetComponent` |
| `OnEnable` | 脚本启用时，每次启用都调用 | 订阅事件 |
| `Start` | 第一次 `Update` 前，仅一次 | 依赖其他对象的初始化 |
| `FixedUpdate` | 固定时间间隔 | 物理相关（刚体加力） |
| `Update` | 每一帧 | 输入、逻辑、移动 |
| `LateUpdate` | 所有 `Update` 之后 | 相机跟随 |
| `OnDisable` | 脚本被禁用时 | 取消订阅事件 |
| `OnDestroy` | 对象销毁时 | 清理 |

记一条经验：**`Awake` 管自己，`Start` 管别人**。多个对象的 `Awake` 都执行完之后才会开始执行 `Start`，所以在 `Start` 里访问其他对象的数据最安全。

## 一个小脚本串起前面所学

```csharp
using System;
using UnityEngine;

public enum PlayerState { Idle, Run }                    // 2.1 枚举

public class PlayerController : MonoBehaviour            // 3.1 类，4.1 继承
{
    [SerializeField] private float speed = 5f;           // 5.4 特性：显示在 Inspector
    [SerializeField] private int maxHp = 100;

    public event Action<int, int> OnHpChanged;           // 5.2 事件
    public int Hp { get; private set; }                  // 3.3 属性
    public PlayerState State { get; private set; } = PlayerState.Idle;

    void Awake() { Hp = maxHp; }

    void Update()
    {
        float h = Input.GetAxisRaw("Horizontal");
        float v = Input.GetAxisRaw("Vertical");
        Vector3 dir = new Vector3(h, 0, v);              // 2.5 结构体（值类型）

        State = dir.sqrMagnitude > 0 ? PlayerState.Run : PlayerState.Idle;
        transform.position += dir.normalized * speed * Time.deltaTime;
    }

    public void TakeDamage(int amount)
    {
        int old = Hp;
        Hp = Mathf.Max(Hp - amount, 0);
        OnHpChanged?.Invoke(old, Hp);                    // 通知血条，但不认识血条
    }
}
```

`Time.deltaTime` 是上一帧耗时（秒）。移动要乘上它，才能保证高帧率和低帧率机器上速度一致：`速度 × 时间 = 距离`。

## 常用 API 速览

| 要做的事 | 写法 | 提示 |
| --- | --- | --- |
| 打日志 | `Debug.Log("..")`、`Debug.LogWarning`、`Debug.LogError` | 代替 `Console.WriteLine` |
| 取同物体上的组件 | `GetComponent<Rigidbody>()` | 泛型方法（5.1），在 `Awake` 里缓存，不要每帧调用 |
| 创建物体 | `Instantiate(prefab, position, rotation)` | 频繁创建销毁请用对象池 |
| 销毁物体 | `Destroy(gameObject)`、`Destroy(obj, 2f)` | 当帧末尾才真正销毁 |
| 位置与旋转 | `transform.position`、`transform.rotation` | 属性，返回副本（3.3） |
| 按名字或标签找物体 | `GameObject.Find`、`CompareTag("Enemy")` | `Find` 慢，不要放进 `Update` |
| 时间 | `Time.deltaTime`、`Time.time` | |

## 从 C++ 来要换的几个念头

1. 不要自己写 `new` 创建脚本对象，Unity 管理这个对象的生命周期。
2. 引用别的物体，**优先在 Inspector 里拖拽**赋值，而不是在代码里 `Find`。
3. 数据通过 Inspector 序列化，意味着代码里写的字段初始值**可能被 Inspector 保存的值覆盖**。
4. 一切在主线程执行，一帧里的代码如果太久，整个游戏就会卡。

## 常见坑

- 类名和文件名不一致，脚本无法挂载。
- 忘记 `using UnityEngine;`，所有 Unity 类型找不到。
- 在 `Update` 里每帧 `GetComponent`、`Find`、拼字符串。
- 把 `Start` 写成 `start`：大小写错误不会报错，但引擎找不到，这个函数永远不会被调用。
- 修改 `public` 字段的初始值，但场景里已经保存了旧值，运行结果没变。

下一篇：[迭代器与协程](../02-迭代器与协程/)。
