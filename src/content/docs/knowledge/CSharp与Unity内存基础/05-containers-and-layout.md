---
title: "5. 容器、容量与数据布局"
description: "比较数组、List、Native 容器与借用视图，说明长度、容量、扩容和连续访问。"
sidebar:
  order: 5
---

## 容器管理的是一组元素

| 容器/视图 | 存储特点 | 长度与容量 | 生命周期重点 |
| --- | --- | --- | --- |
| `T[]` | 托管数组；元素槽连续 | 长度固定 | GC 管理数组对象 |
| `List<T>` | 托管对象管理后备数组 | Count 与 Capacity 分开 | 扩容可能分配新数组并复制 |
| `NativeArray<T>` | 原生元素存储 | 长度固定 | 所有者安排释放 |
| `NativeList<T>` | 原生可增长列表 | Length 与 Capacity 分开 | 扩容可能使已有视图失效 |
| `NativeSlice<T>` | 对既有存储的视图，可含步长 | 描述一个区间 | 不拥有底层分配，不延长寿命 |
| `Span<T>` | 对连续内存的受限视图 | 描述一个区间 | 是 ref struct，不能当普通长期字段使用 |

Span 可以引用不同来源的内存，不意味着一定来自栈。它也不是可直接替代 Job 字段中 NativeArray 的通用方案。

## 连续存储不等于每个对象连续

`float[]` 的浮点元素连续。`SomeClass[]` 连续的是引用槽，各个类对象未必相邻。结构体数组将字段内联在元素中，但结构体的引用字段仍指向别处。

CPU 会按缓存行搬运数据，顺序访问常有较好局部性；不过 NativeArray 并不天然比 float[] 的普通遍历快。Burst、边界检查、算法、调度和数据大小都会影响结果。

## 长度和容量

列表的逻辑元素数量与已分配空间不是一回事。预留足够容量可以减少扩容，但会保留更多内存。`Clear()` 通常清空逻辑内容并保留容量，不等于释放整个容器的存储。

对于 NativeList，从 `AsArray()` 取得的是共享存储的视图。列表扩容会搬迁底层存储；改变列表的结构也可能触发视图安全版本失效。不要长期缓存视图，在结构变化后重新获取，并按具体 API 契约判断有效性。

## 浅复制、深复制和视图

- 普通数组变量赋值：共享同一个数组对象。
- `Array.Copy`：复制元素；元素若是引用类型，复制的仍是引用。
- NativeArray 变量赋值：复制句柄，共享底层分配。
- 创建新 NativeArray 并复制元素：取得独立的元素存储。
- NativeSlice 或 AsArray：借用已有存储，没有建立独立所有权。

“零拷贝”省去数据复制，同时引入共享关系和有效期要求。

## 自测

**问：List.Clear 后为何内存不一定明显下降？** 答：列表通常保留后备数组容量；引用元素被清除后的对象是否回收还取决于其他引用与 GC。

**问：得到视图后是否可以释放原容器并继续读取？** 答：不可以，视图没有延长原分配的寿命。

继续：[所有权、借用与释放](/qmx-Gameknowledge/knowledge/csharp与unity内存基础/06-ownership-and-disposal/)。深入：[NativeContainer 容器](/qmx-Gameknowledge/knowledge/unity-job与burst/01-job系统/04-nativecontainer容器/)、[Span 与 ref struct](/qmx-Gameknowledge/knowledge/csharp底层专栏/02-托管与非托管/04-span与ref-struct/)。
