---
title: "7. Native 容器与 Allocator"
description: "解释 NativeArray 句柄、分配器选择、别名有效期、初始化与常见释放误区。"
sidebar:
  order: 7
---

## NativeArray 是句柄加原生存储

```csharp
var a = new Unity.Collections.NativeArray<float>(
    16, Unity.Collections.Allocator.Persistent);
var b = a;
b[0] = 4f; // a[0] 也改变。
a.Dispose();
// 不再访问或释放 b：共享的底层分配已经失效。
```

NativeArray 是结构体。赋值时复制长度、访问底层数据所需的信息及相关安全状态，不会深拷贝所有元素，也不自动增加引用计数。

不要把某个副本的 `IsCreated` 当作跨副本的有效性证明。另一个句柄释放底层分配后，旧副本仍可能保留旧状态。正确性依赖所有权与生命周期协议。

## Allocator 选择

| 分配器 | 适用场景 | 生命周期约束 |
| --- | --- | --- |
| Temp | 当前线程短时临时工作 | 主线程通常当前帧内；Job 内通常到该 Job 结束，不能将主线程 Temp 容器作为 Job 字段传入 |
| TempJob | 很快完成的 Job 输入/输出 | 必须在分配后的四帧内释放 |
| Persistent | 跨帧任务、缓存和服务共享数据 | 无四帧期限，但仍必须由所有者释放 |

四帧不是四个 Job，也不是四次 Schedule。无法保证任务在期限内结束，就应重新设计生命周期或使用适合长期持有的分配方式。

Temp 采用批量回收机制，容器 Dispose 与分配器实际归还单块存储的行为应区分；不要由此推断所有分配器都可以省略清理。TempJob 和 Persistent 必须安排释放。

Persistent 不表示磁盘持久化，不保证性能更好，也不表示容器可以无依赖地跨线程访问。自定义和 Rewindable 分配器适合后续学习：整体回绕同样必须等待所有使用者。

## 初始化、清空和释放

NativeArray 默认清零；选择 `NativeArrayOptions.UninitializedMemory` 可以跳过清零，但必须确保每个将被读取的元素已经写入。不能依赖未初始化数据恰好为零。

`NativeList.Clear()` 保留存储容量；Dispose 结束资源生命周期；重新分配会建立新的生命周期。不要混用这几个操作。

## 视图不取得所有权

NativeSlice、NativeArray 子数组以及 NativeList.AsArray 等入口通常借用既有分配，具体限制以 API 契约为准。底层释放、搬迁或某些结构变化后，视图不能继续使用。不要单独释放借用视图来“帮助”所有者清理。

安全检查可以在开启时发现很多非法访问，但关闭检查不会让错误变正确。`NativeDisableParallelForRestriction` 等属性也不能代替正确的访问证明。

## 自测

**问：为何 b = a 后不能 a、b 各 Dispose 一次？** 答：只有一份底层分配；两个句柄不是两个所有者。

**问：选择 Persistent 后能否无限期不清理？** 答：可以长期持有，但不再需要时仍须释放，否则是泄漏。

继续：[Job 依赖与并发安全](/qmx-Gameknowledge/knowledge/csharp与unity内存基础/08-jobs-and-safety/)。深入：[分配器与生命周期](/qmx-Gameknowledge/knowledge/unity-job与burst/01-job系统/05-内存分配器与生命周期/)。参考：[Collections 2.5 分配器概览](https://docs.unity3d.com/Packages/com.unity.collections@2.5/manual/allocator-overview.html)。
