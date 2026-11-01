---
title: "4. GC、隐藏分配与测量"
description: "理解可达性、GC Root、常见临时分配及 Unity 中 GC.Alloc 的实际含义。"
sidebar:
  order: 4
---

## GC 回收不可达对象

GC 从运行时识别的根集合出发追踪引用。静态字段、运行时识别的活动引用、句柄等可能让对象保持可达。对象互相引用但无法从根到达，也可以被回收；GC 不只是简单的引用计数。

```csharp
float[] values = new float[1024];
values = null;
```

第二句仅切断一个引用。若还有其他引用，数组仍可达；即使已不可达，也不保证立刻回收。GC 的对象回收也不保证操作系统看到的进程占用立刻下降。

## 分配量、存活量和回收成本不同

| 现象 | 可能原因 | 应查看什么 |
| --- | --- | --- |
| 每帧分配很多，存活量稳定 | 大量临时对象反复创建 | GC.Alloc 调用栈、回收频率与耗时 |
| 场景切换后托管对象持续存活 | 静态缓存、事件订阅、其他长期引用 | 内存快照与引用链 |
| GC.Alloc 很低，原生占用上涨 | Native 容器或 Unity 资源未释放 | 原生内存、资源数量、泄漏提示 |
| 内存稳定但帧耗时高 | 计算、同步、复制或其他系统成本 | CPU Timeline 等性能数据 |

`GC.Alloc` 主要反映托管分配，不是总内存分配量，也不是该帧 GC 回收耗时。零 GC.Alloc 不等于零成本或无泄漏。

## 常见隐藏分配

- 高频字符串拼接、格式化和日志参数构造。
- 值类型装箱为 object 或接口。
- 捕获局部变量的 lambda，可能创建闭包对象和委托。
- LINQ、迭代器、async 状态机，取决于具体写法和执行路径。
- 每帧新建集合、调用会返回新数组的 API。

不要记成“所有 foreach 都分配”或“所有 lambda 都分配”。例如 List 的具体类型枚举器与通过接口枚举的路径可能不同，缓存委托也与每次捕获不同。用实际调用栈判断。

## Unity GC 与现代 .NET GC 分开学习

CoreCLR 常见的分代回收、LOH、POH 不能自动套用到 Unity Mono/IL2CPP。Unity 具体回收器以编辑器与后端文档为准。增量 GC 将部分工作分散到多个时段，不能消除分配，也不能保证任何场景都没有停顿。

## 一个可重复的观察练习

1. 写两个功能一致的版本：每次新建 float 数组，以及复用已有数组。
2. 在相同平台、相同输入和相同执行次数下预热。
3. 在 Profiler 中记录 GC.Alloc、CPU 耗时与 GC 样本；需要时使用 Development Player，区分 Editor 干扰。
4. 停止任务后比较内存快照中的存活对象与引用链。

数组复用可能降低分配频率，也会长期保留容量。不要仅凭一次帧时间或 Editor 日志得出性能结论，不要把频繁手动 GC.Collect 当作常规修复。

## 自测

**问：两个对象互相引用就永远回收不了吗？** 答：不是，若从 GC 根不可达，仍可回收。

**问：GC.Alloc 为零能证明 NativeArray 都释放了吗？** 答：不能，它不覆盖原生分配的完整生命周期。

继续：[容器、容量与数据布局](/qmx-Gameknowledge/knowledge/csharp与unity内存基础/05-containers-and-layout/)。深入：[Unity GC](/qmx-Gameknowledge/knowledge/csharp底层专栏/03-gc/03-unity-boehm-gc与增量gc/)、[GC 调优与诊断](/qmx-Gameknowledge/knowledge/csharp底层专栏/03-gc/06-gc调优与诊断工具/)。
