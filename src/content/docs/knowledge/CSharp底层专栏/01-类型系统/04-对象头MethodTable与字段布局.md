---
title: "1.4 对象头、MethodTable 与字段布局"
description: CoreCLR、Unity Mono、IL2CPP 的托管对象头结构，MethodTable 里装了什么，字段布局规则（Auto/Sequential/Explicit）、padding、false sharing，以及与 C++ 对象布局的对照。
sidebar:
  order: 4
---

> 适用版本：对象头与 MethodTable 以 CoreCLR（.NET 8 左右）x64 为主；Mono 的 `MonoObject`/`MonoVTable`、IL2CPP 的 `Il2CppObject`/`Il2CppClass` 分别单独说明。字段排布是实现细节，不属于语言规范，未经验证的细节标"待核实"。

## 要点

- CoreCLR x64 上，引用类型对象 = 8 字节 ObjHeader（在引用指向位置的负偏移处）+ 8 字节 MethodTable 指针 + 字段。空对象最小 24 字节。
- Unity Mono 与 IL2CPP 的对象头都是两个指针：类/虚表指针 + 监视器（同步）指针，共 16 字节。
- MethodTable（CoreCLR）/ `MonoVTable`（Mono）/ `Il2CppClass`（IL2CPP）是每个类型一份的运行时描述，包含大小、虚方法槽、接口映射、GC 描述（GCDesc）、基类指针等。虚调用和接口调用都经由它。
- 字段布局：`class` 默认 `LayoutKind.Auto` 风格（CLR 可重排以减少 padding），`struct` 默认 `Sequential`，但含引用字段时 CLR 会忽略 Sequential。`Explicit` 用 `FieldOffset` 手动指定，引用字段不能与非引用字段重叠。
- 同一缓存行（常见 64 字节）上被多个线程写的不同字段会产生 false sharing，用 padding 或拆分结构解决。
- 与 C++ 对照：C++ 的多态对象头只有 vptr（8 字节），布局由声明顺序决定；C# 对象多一个对象头，但字段顺序可被运行时重排。

## CoreCLR 对象结构

x64 上：

```
地址          内容
p - 8         ObjHeader：同步块索引 / thin lock / 哈希码（取决于位）
p + 0         MethodTable*
p + 8         字段 / 数组长度 + 元素 / 字符串长度 + 字符
```

`p` 是托管引用的值。因此"引用指向 MethodTable 指针"，对象头在引用之前。几个常用数字（x64）：

| 对象 | 大小 | 构成 |
|---|---|---|
| `new object()` | 24 字节 | 头 8 + MT 8 + 最小 8 字节 |
| 含一个 `int` 字段的 class | 24 字节 | 头 8 + MT 8 + int 4 + 4 padding |
| `int[0]` | 24 字节 | 头 8 + MT 8 + length 4（+4 对齐） |
| `byte[n]` | 24 + n 向上对齐到 8 | length 之后是元素 |
| `string`（长度 n） | 约 22 + 2n，对齐到 8 | 头 8 + MT 8 + length 4 + 字符 2(n+1)，含尾部 `\0` |

"最小 24 字节"的原因：GC 回收后，一段对象内存可能被重新解释为 free object（也有 MethodTable，并带一个大小字段），要求至少容纳三个指针宽度。x86 上最小是 12 字节。

最后一行 string 的数字是公式化估算，具体值可以用 `ObjectLayoutInspector` 之类工具或 `!dumpobj`（WinDbg/SOS）验证。

### ObjHeader 里存什么

ObjHeader 4 字节有效位（x64 上占 8 字节，其中一半是对齐填充，不同版本实现不同，待核实）用来承载：

- **thin lock**：线程 id 和递归计数，`lock` 无竞争时直接用 CAS 修改对象头，不分配同步块。
- **哈希码**：第一次调用 `RuntimeHelpers.GetHashCode`/未重写的 `Object.GetHashCode` 时，生成哈希码存进对象头。
- **同步块索引**：当发生竞争、`Monitor.Wait`、或哈希码与 thin lock 冲突时，对象头里改存同步块表索引，指向堆外的 `SyncBlock`，其中保存真正的监视器和哈希码。

这解释了两个面试点：`lock(obj)` 的 obj 必须是引用类型（值类型会装箱成每次不同的盒子，永远拿不到同一把锁）；`GetHashCode` 默认实现不依赖对象的内存地址，因为 GC 会移动对象。

## Unity Mono 与 IL2CPP 的对象头

两者结构相似：

```c
// Mono
struct MonoObject {
    MonoVTable *vtable;
    MonoThreadsSync *synchronisation;
};
// IL2CPP
struct Il2CppObject {
    Il2CppClass *klass;      // 或 union 里的 vtable
    MonitorData *monitor;
};
```

x64 上头部 16 字节，后面直接是字段，没有"负偏移"部分。Boehm GC 本身给每个分配块没有额外的托管头，块大小按 GC 粒度取整（具体粒度待核实）。所以 Unity 里对象的内存估算：16 字节头 + 字段，再向上取整。

数组：`MonoArray`/`Il2CppArray` 头部之后是 `bounds` 指针（多维数组用）、`max_length`，之后是元素，所以 `T[]` 的头部比 CoreCLR 略大（具体字节数待核实）。

## MethodTable 里有什么

以 CoreCLR 为例（概念结构，不是逐字段布局）：

| 内容 | 作用 |
|---|---|
| 基类（EEClass/ParentMethodTable） | 继承链、类型转换检查 |
| 实例大小、组件大小 | 分配时用；数组、字符串用 component size 乘长度 |
| 虚方法表（vtable slots） | 虚调用：先取 MT 再按槽号间接调用 |
| 接口映射 | 接口方法分派（用虚存根分派 VSD 缓存） |
| GCDesc | 描述对象内哪些偏移是引用，GC 标记时据此遍历；含引用的类型才有 |
| 类型标志 | 是否值类型、是否含指针、是否泛型实例等 |
| 泛型字典指针 | 共享泛型代码用来查实际类型参数（见第 4 章） |

虚方法调用的机器码形态（示意）：

```
mov rax, [rcx]          ; 取 MethodTable*
mov rax, [rax+0x40]     ; 取 vtable 槽（偏移随槽号）
call rax
```

CoreCLR 的接口调用比虚调用复杂（虚存根分派，带缓存），.NET 的 tiered PGO 还会做 guarded devirtualization。Unity 的 IL2CPP 把虚调用翻译成 C++ 的虚表式调用（通过 `Il2CppClass` 的 vtable 数组间接调用），接口调用用 interface offset 表。具体代码形态见 4.1 节。

## 字段布局规则

三种 `LayoutKind`：

| 取值 | 含义 | 引用字段 |
|---|---|---|
| `Auto` | CLR 自由重排以减少 padding | 允许 |
| `Sequential` | 按声明顺序，按字段自然对齐放置 | 含引用时，CLR 的托管布局会忽略 Sequential，改用 Auto 式布局（待核实不同运行时的细则） |
| `Explicit` | 用 `[FieldOffset]` 手动指定 | 引用字段必须按指针宽度对齐，且不能与其他字段重叠 |

C# 编译器的默认：`class` 发出 `auto`，`struct` 发出 `sequential`。注意 CoreCLR 对"只包含 blittable 字段"的 struct 才真正保证 Sequential 的布局（这也是 interop 需要的），含引用的 struct 无法保证与源码声明顺序一致。因此**不要依赖托管布局做 P/Invoke 传递**，要显式 `[StructLayout(LayoutKind.Sequential)]` 并只含 blittable 字段（见第 2 章）。

CoreCLR 对 `class` 的自动布局大致策略（实现细节，非规范）：先放引用字段（使 GC 扫描区域连续），再按字段大小从大到小放原始类型，以此减少 padding；继承时子类字段排在基类字段之后。

```csharp
class A { byte b1; long l; byte b2; int i; object o; }
// 按声明顺序需要：1 + 7(pad) + 8 + 1 + 3(pad) + 4 + 8 = 32 字节字段区
// 自动重排后：o(8) + l(8) + i(4) + b1(1) + b2(1) + 2(pad) = 24 字节字段区
```

用 `Unsafe.SizeOf<T>()` 可查值类型大小，`Marshal.SizeOf` 是非托管布局下的大小，两者可能不同。引用类型大小要用 `ObjectLayoutInspector`、WinDbg `!objsize`、或者 `GC.GetAllocatedBytesForCurrentThread` 前后差值来估算。

### struct 的 padding

```csharp
struct Bad  { byte a; long b; byte c; }   // 24 字节：1+7+8+1+7
struct Good { long b; byte a; byte c; }   // 16 字节：8+1+1+6
```

`Sequential` 下，自然对齐 = 字段自身大小（最大 8），struct 整体对齐 = 最大字段对齐。字段顺序直接影响数组中每个元素的大小，也就影响缓存利用率。Unity 的 `StructLayout(LayoutKind.Sequential, Pack=1)` 或 `Explicit` 可强制紧凑，但 Pack=1 在 ARM 上的未对齐访问可能变慢或在某些平台出错，一般只在序列化/网络数据里使用。

### Explicit 与联合体

```csharp
[StructLayout(LayoutKind.Explicit)]
struct FloatInt
{
    [FieldOffset(0)] public float F;
    [FieldOffset(0)] public int I;
}
```

用来做按位重解释（等价于 C++ union 的 type punning）。限制：不能让引用字段与其他字段重叠（否则 GC 会把整数当作指针，或相反，运行时拒绝加载这样的类型）。在 IL2CPP 上 `Explicit` 布局同样受支持，生成的 C++ 使用 union 或偏移访问。

## False sharing 与缓存行

多线程环境（Job System、`Task`）下，两个线程分别写同一缓存行的不同字段，会导致该行在核心之间来回失效，性能可能下降数倍。

```csharp
class Counters
{
    public long A;   // 线程 1 写
    public long B;   // 线程 2 写，与 A 在同一个 64 字节缓存行
}

[StructLayout(LayoutKind.Explicit, Size = 128)]
struct PaddedLong
{
    [FieldOffset(64)] public long Value;   // 前后各留 64 字节
}
```

CoreCLR 里的 `ConcurrentQueue<T>` 内部用 128 字节的 padding 隔离头尾索引（128 是因为部分处理器会预取相邻缓存行，待核实具体源码位置）。缓存行大小常见 64 字节，Apple Silicon 的 L1 缓存行为 128 字节（待核实）。.NET 8 之后没有官方的 `[CacheLinePadding]` 特性，需要手写 padding。

Unity 的 `NativeArray` 分块并行写入时，每个 Job 处理的块要按缓存行对齐边界切分，不然相邻块边界处会 false sharing（见 Job 与 Burst 专栏的调度粒度一节）。

## 与 C++ 对照

| 项目 | C++ | C# CoreCLR |
|---|---|---|
| 对象头 | 无；多态对象有 vptr（8 字节） | 8 字节 ObjHeader + 8 字节 MT 指针 |
| 字段顺序 | 严格按声明顺序，标准布局保证 | class 可被重排；struct 含引用时不保证 |
| 控制 | `alignas`、`#pragma pack`、`[[no_unique_address]]` | `StructLayout`、`FieldOffset`、`Pack` |
| 空对象大小 | 至少 1 字节（空基类优化可为 0） | 24 字节（x64 CoreCLR） |
| 虚调用 | vptr → vtable → 函数 | MT → vtable slot → 方法；接口走分派存根 |
| 同步 | 无内置，需 `std::mutex` | 每个对象都能 `lock`，由对象头承载 |
| union | `union` | `Explicit` + 同偏移 |

IL2CPP 把 C# 类生成成 C++ 的 `struct`，第一个成员是 `Il2CppObject`（头），其后是继承链上的字段，布局基本按声明顺序由 C++ 编译器决定。因此在 IL2CPP 上，`class` 的字段排布和 CoreCLR 的自动重排可能不同（待核实），所以不要写依赖字段偏移的代码。

## 常见坑

1. **用 `sizeof` 或 `Marshal.SizeOf` 估算对象内存**：它们描述的是非托管布局，不含对象头，也不反映重排。
2. **以为 `string` 或 `object` 字段很小**：每个引用字段 8 字节，且指向的对象有独立的头和对齐。
3. **布局依赖**：`unsafe` 代码按偏移读托管 `class` 字段是脆弱的；用 `blittable struct` + `Sequential` 做互操作。
4. **用 struct 数组时忽略 padding**：加一个 `bool` 可能让每个元素多 8 字节。
5. **`lock` 一个值类型或字符串字面量**：值类型每次装箱是新盒子；字符串字面量全局驻留，可能与其他代码锁同一把锁。
6. **忽略 false sharing**：多线程计数器按线程分片时，数组相邻元素在同一缓存行内。

## 面试追问

**Q：一个空 `object` 在 64 位 .NET 里占多少字节？为什么？**
24 字节：8 字节 ObjHeader、8 字节 MethodTable 指针、8 字节最小字段区。最小字段区是因为 GC 回收后需要把这段内存当作 free object，需要容纳 MT 指针和大小字段。

**Q：`lock(obj)` 的实现原理？**
无竞争时用 CAS 把线程 id 写进对象头（thin lock）；出现竞争、`Wait/Pulse` 或需要同时保存哈希码时，膨胀成 SyncBlock，对象头存同步块索引。因此 `lock` 的对象必须是有对象头的引用类型。

**Q：虚方法调用在机器码层面是什么样的？和 C++ 比有什么区别？**
取对象的 MethodTable 指针，加槽偏移读函数指针，间接调用。与 C++ 的 vptr/vtable 机制本质相同，区别在于 CLR 有接口分派存根、JIT 可以基于 PGO 做 guarded devirtualization，C++ 则靠编译期 devirtualization 和 LTO。

**Q：struct 字段顺序会影响性能吗？**
会。`Sequential` 下 padding 取决于声明顺序，数组中每个元素的大小直接影响缓存命中。把大字段放前、小字段放后通常更紧凑。

**Q：什么是 false sharing，C# 里怎么避免？**
不同线程写同一缓存行的不同变量导致缓存行反复失效。用 `StructLayout(Size=...)`/`FieldOffset` 做 padding，或让每个线程写自己的缓存行对齐的槽位，最后归约。

## 参考资料

- [Book of the Runtime: Type Loader（MethodTable、EEClass）](https://github.com/dotnet/runtime/blob/main/docs/design/coreclr/botr/type-loader.md)
- [Book of the Runtime: Garbage Collection Design（对象头与 GC 描述）](https://github.com/dotnet/runtime/blob/main/docs/design/coreclr/botr/garbage-collection.md)
- [Layout of structs for interop - StructLayoutAttribute](https://learn.microsoft.com/dotnet/api/system.runtime.interopservices.structlayoutattribute)
- [Unity Manual: IL2CPP Overview](https://docs.unity3d.com/Manual/IL2CPP.html)
