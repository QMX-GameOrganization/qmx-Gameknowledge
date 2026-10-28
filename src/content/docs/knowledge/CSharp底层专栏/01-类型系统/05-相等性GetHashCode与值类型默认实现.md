---
title: "1.5 相等性、GetHashCode 与值类型默认实现"
description: ValueType.Equals 的按位比较与反射两条路径、GetHashCode 的默认实现问题、Dictionary 键的装箱与比较器选择、IEquatable 与 EqualityComparer 的分派，以及 Unity 上的注意事项。
sidebar:
  order: 5
---

> 适用版本：ValueType 的默认实现细节以 CoreCLR（.NET 6 至 8）源码为参照；Unity Mono 与 IL2CPP 的 BCL 来自 Mono 分支，实现不同，涉及差异处标"待核实"。C# 记录结构体（`record struct`）需要 C# 10，Unity 6 的 C# 9.0 不支持。

## 要点

- 引用类型默认 `==`/`Equals` 是引用相等；值类型默认 `Equals` 由 `ValueType.Equals(object)` 提供，语义是"字段逐个相等"，但实现有快慢两条路径：能按位比较时用 `memcmp` 式的快路径，否则用反射逐字段比较。
- `ValueType.Equals(object)` 的参数是 `object`，所以调用它本身就要装箱参数。
- 默认的 `ValueType.GetHashCode()` 质量和性能都不可靠，文档明确说明它可能只使用部分字段，且不要依赖其具体算法。自定义 struct 做字典键时，必须重写 `Equals`/`GetHashCode` 并实现 `IEquatable<T>`。
- `Dictionary<TKey,TValue>`、`HashSet<T>` 通过 `EqualityComparer<TKey>.Default` 取比较器。当 `TKey` 实现 `IEquatable<TKey>` 时，比较器直接调用泛型 `Equals(T)`，没有装箱。
- 重写了 `Equals` 必须重写 `GetHashCode`：相等的对象哈希必须相等，反之不要求。
- 枚举做键、`float` 做键、含浮点的 struct 有额外陷阱。

## 引用相等、值相等与 `==`

| 运算 | 引用类型默认 | 值类型默认 |
|---|---|---|
| `a == b` | 引用相等（除非重载） | 没有默认 `==`，struct 不重载就不能用；基元类型除外 |
| `a.Equals(b)` | `Object.Equals` → `ReferenceEquals` | `ValueType.Equals`：字段逐个比较 |
| `ReferenceEquals(a, b)` | 比较引用 | 两个参数分别装箱，永远 false |
| `a.GetHashCode()` | 基于对象头里的哈希码，与内容无关 | `ValueType.GetHashCode`：基于字段内容（但实现粗糙） |

`string` 是特例：重载了 `==` 和 `Equals` 为内容相等，但仍是引用类型。

## ValueType.Equals 的两条路径

CoreCLR 里 `ValueType.Equals(object obj)` 的逻辑（概念化的伪代码）：

```csharp
public override bool Equals(object obj)
{
    if (obj is null) return false;
    if (GetType() != obj.GetType()) return false;       // 类型必须精确一致
    if (CanCompareBits(this))                            // 快路径
        return FastEqualsCheck(this, obj);               // 内存逐字节比较
    // 慢路径：反射
    FieldInfo[] fields = GetType().GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
    for (int i = 0; i < fields.Length; i++)
    {
        object a = fields[i].GetValue(this);            // 每个字段都会装箱
        object b = fields[i].GetValue(obj);
        if (a == null) { if (b != null) return false; }
        else if (!a.Equals(b)) return false;
    }
    return true;
}
```

`CanCompareBits` 为真的条件，按 CoreCLR 的实现大致是：

1. struct 不包含任何引用字段（引用比较的语义要用 `Equals`，不能按位）。
2. struct 内存紧凑，没有 padding（padding 字节的内容未定义，按位比较会错）。
3. 不含浮点字段（`float`/`double`）：`NaN != NaN` 而位模式相同，`+0.0 == -0.0` 而位模式不同，按位比较语义不对。
4. 不含重写了 `Equals` 的值类型字段（需要调用它的自定义逻辑）。

以上第 3、4 条是对源码行为的转述，不同版本细节可能有差异（待核实）。结论很明确：

- 只含整数且无 padding 的 struct，默认 `Equals` 很快，但参数 `object` 仍然要装箱。
- 含 `float`（如 `Vector3`）、含引用、有 padding 的 struct，走反射慢路径，每个字段取值都装箱，成本非常高。

Unity Mono 的实现是另一份代码（Mono 的 `ValueType.Equals` 通过内部调用实现，同样有"无引用则整块比较，否则逐字段"的结构），性能结论方向一致，具体条件待核实。IL2CPP 的 `ValueType.Equals` 同样来自 Mono 的 BCL 并走 icall。

### `Vector3.Equals`

Unity 的 `Vector3` 重写了 `Equals(Vector3)` 和 `GetHashCode`，`==` 使用近似比较（差的平方小于 1e-10 即认为相等），而 `Equals` 是精确逐分量比较。这个差异在字典键、`Contains`、`==` 之间不一致，容易导致"`==` 为真但 `Equals` 为假"。

## GetHashCode 的约定与默认实现

契约：

1. 同一对象在不修改参与比较的状态时，多次调用返回同一个值。
2. `a.Equals(b)` 为真则 `a.GetHashCode() == b.GetHashCode()`。
3. 分布尽量均匀，否则哈希表退化为链表。

`ValueType.GetHashCode` 的官方说明是：默认实现可能只用类型的第一个非 null 非静态字段，且在某些情况下相等的值得到相同哈希，不相等的也可能大量冲突；文档明确建议自己重写。典型后果：

```csharp
struct Pos { public int X, Y; }   // 未重写
// 若默认实现只取第一个字段，则所有 X 相同的 Pos 全部落入同一个桶
```

不同运行时、不同版本的默认算法不同，所以不要依赖，也不要把默认哈希值持久化或用于跨进程。

### 自己写

```csharp
readonly struct CellKey : IEquatable<CellKey>
{
    public readonly int X, Y;
    public CellKey(int x, int y) { X = x; Y = y; }

    public bool Equals(CellKey o) => X == o.X && Y == o.Y;
    public override bool Equals(object obj) => obj is CellKey o && Equals(o);
    public override int GetHashCode() => HashCode.Combine(X, Y);   // .NET Core 2.1+/.NET Standard 2.1
    public static bool operator ==(CellKey a, CellKey b) => a.Equals(b);
    public static bool operator !=(CellKey a, CellKey b) => !a.Equals(b);
}
```

`HashCode.Combine` 在 Unity 6 的 .NET Standard 2.1 API 中是否可用，需验证（待核实）。不可用时手写：

```csharp
public override int GetHashCode()
{
    unchecked { return (X * 397) ^ Y; }          // 经典做法，质量一般
}
// 更好的混合，适合网格坐标：
// unchecked { uint h = (uint)X * 0x9E3779B1u; h ^= (uint)Y + 0x7F4A7C15u + (h << 6) + (h >> 2); return (int)h; }
```

网格坐标做键时，把 `(x, y)` 压成一个 `long` 或 `int` 再做键，常比自定义 struct 键更快（比较和哈希都是单个整数操作）。

## Dictionary 与比较器

`Dictionary<TKey,TValue>` 内部：

```csharp
// 简化：构造时
_comparer = comparer ?? EqualityComparer<TKey>.Default;
// 查找时
int hash = _comparer.GetHashCode(key);
... _comparer.Equals(entries[i].key, key) ...
```

`EqualityComparer<T>.Default` 的选择逻辑（CoreCLR）：

| T 的特征 | 默认比较器 | 是否装箱 |
|---|---|---|
| `T : IEquatable<T>` | `GenericEqualityComparer<T>` | 否，调用 `IEquatable<T>.Equals(T)` |
| `Nullable<U>` 且 `U : IEquatable<U>` | `NullableEqualityComparer<U>` | 否 |
| 枚举 | `EnumEqualityComparer<T>` | 否（特化处理） |
| 其他 | `ObjectEqualityComparer<T>` | 调用 `object.Equals(object)`，值类型的参数会装箱 |

在 CoreCLR 的 tiered JIT 下，对值类型 `TKey`，`EqualityComparer<TKey>.Default.Equals(a, b)` 可以被 JIT 当作内建识别并去虚拟化（devirtualization），内联成直接比较，没有虚调用。Mono 与 IL2CPP 上没有这种优化，是虚调用（IL2CPP 会静态实例化泛型，但调用仍是虚调用，待核实）。

### 在 Unity 上的几个老问题

1. **枚举做键**：早期 Mono 的 `EnumEqualityComparer` 在比较时通过装箱完成，所以经典建议是传入自定义 `IEqualityComparer<MyEnum>`。新的 Unity 版本（2021 起的 .NET Standard 2.1 BCL）已经好很多，是否仍装箱要用 Profiler 对具体版本实测（待核实）。
2. **IL2CPP 上值类型泛型实例化要求**：`Dictionary<MyStruct, V>` 要在编译期可见才能生成代码，通常没问题，因为你的代码直接写了这个类型。反射创建的泛型字典可能缺失实例化（见 4.2 节）。
3. **`Dictionary` 的 `TKey` 是 `struct` 且没实现 `IEquatable<T>`**：落到 `ObjectEqualityComparer`，每次查找装箱，可能再加上反射。这是线上最常见的字典分配源。

```csharp
// 反例
struct Key { public int A; public float B; }                 // 含 float，走反射慢路径
var d = new Dictionary<Key, int>();                          // 每次 TryGetValue 装箱 + 反射

// 正例
var d2 = new Dictionary<CellKey, int>();                     // CellKey : IEquatable<CellKey>
// 或者提供自定义比较器
var d3 = new Dictionary<Key, int>(new KeyComparer());
sealed class KeyComparer : IEqualityComparer<Key>
{
    public bool Equals(Key a, Key b) => a.A == b.A && a.B == b.B;
    public int GetHashCode(Key k) => HashCode.Combine(k.A, k.B);
}
```

自定义比较器类应声明为 `sealed` 并复用同一个实例，避免每次 new。

## 浮点数做键与比较

- `float.Equals(float)` 与 `==` 不同：`float.NaN.Equals(float.NaN)` 为 `true`，`NaN == NaN` 为 `false`；`0.0f.Equals(-0.0f)` 为 `true`（与 `==` 一致），但它们的 `GetHashCode` 需要保证相等，CoreCLR 的实现对 `+0` 和 `-0` 做了特殊处理使哈希一致（待核实）。
- 把 `Vector3` 直接当字典键，浮点精度会让"看起来相同"的点命中不同的键。应当量化成整数网格坐标作为键。
- 包含浮点数的 struct 用默认 `Equals` 会走反射路径（见上），哪怕你只想比较位置。

## record struct 与自动生成

C# 10 的 `record struct` 会自动生成 `IEquatable<T>`、`Equals`、`GetHashCode`、`==`。Unity 6 的 C# 9 不支持 `record struct`，只支持 `record`（引用类型，自动生成值相等，但堆分配）。想用 `record struct` 需要自己升级编译器，不推荐。手写 `IEquatable<T>` 配合 IDE 的"生成 Equals 和 GetHashCode"重构即可。

## 与 C++ 对照

C++ 里自定义哈希表键需要特化 `std::hash<T>` 并提供 `operator==`，使用 `std::unordered_map<K,V,Hash,Eq>`，哈希和相等是模板参数，编译期绑定、可内联，没有装箱问题。C# 的 `IEquatable<T>` 加泛型实例化在 CoreCLR 上达到类似效果；Mono/IL2CPP 的虚调用开销更接近 C++ 的 `std::function`。C++ 的 `memcmp` 比较结构体有同样的 padding 和浮点陷阱，`std::has_unique_object_representations<T>` 恰好描述"可以按位比较"的条件，和 CLR 的 `CanCompareBits` 对应。

## 常见坑

1. **重写 `Equals` 不重写 `GetHashCode`**：编译器给警告，运行时哈希表行为错误。
2. **用可变字段参与哈希**：对象放进字典后字段被改，哈希变化，找不到。键应该不可变。
3. **默认 `ValueType.GetHashCode` 冲突严重**：不要把未重写的 struct 当键。
4. **`ReferenceEquals` 比较值类型永远 false**：两侧各自装箱。
5. **`Equals(object)` 与 `Equals(T)` 语义不一致**：必须一致。
6. **`==` 和 `Equals` 对浮点、`Vector3` 不一致**：Unity 的 `Vector3 ==` 是近似比较，字典键用的是精确 `Equals`。
7. **含 `string` 字段的 struct 键**：比较字符串每次都是内容比较，哈希需遍历字符串，开销较大；考虑先转成整数 id（字符串驻留表）。

## 面试追问

**Q：为什么自定义 struct 做 `Dictionary` 键要实现 `IEquatable<T>`？**
不实现的话，`EqualityComparer<T>.Default` 落到 `ObjectEqualityComparer`，调用 `ValueType.Equals(object)`，每次比较装箱参数；如果 struct 含浮点或引用或有 padding，还要走反射慢路径。实现后使用 `GenericEqualityComparer<T>` 调用 `Equals(T)`，无装箱。同时要重写 `GetHashCode`，默认实现质量不可靠。

**Q：`ValueType.Equals` 什么时候可以按位比较？**
没有引用字段、没有 padding、没有浮点字段、没有重写了 `Equals` 的值类型字段时。否则反射逐字段比较，且字段值都要装箱。

**Q：重写 `Equals` 为什么必须重写 `GetHashCode`？**
哈希表先用哈希定位桶再用 `Equals` 确认。相等的对象哈希不同，会落进不同桶，永远找不到。

**Q：`EqualityComparer<T>.Default` 在 CoreCLR 上有什么优化？**
对值类型 `T`，tiered JIT 把 `Default.Equals` 识别为 intrinsic 并去虚拟化，内联为直接比较。Mono 和 IL2CPP 上没有这个特性，仍是虚调用。

**Q：用 `float`/`Vector3` 做字典键有什么问题？**
精度问题使近似相等的点落在不同键；`NaN` 和 `±0` 的相等与哈希特殊；Unity `Vector3 ==` 与 `Equals` 语义不一致。建议量化为整数网格坐标，或用 `int` 编码后做键。

## 参考资料

- [ValueType.Equals Method](https://learn.microsoft.com/dotnet/api/system.valuetype.equals)
- [ValueType.GetHashCode Method（备注：默认实现的局限）](https://learn.microsoft.com/dotnet/api/system.valuetype.gethashcode)
- [Object.GetHashCode - Notes to inheritors](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)
- [How to define value equality for a class or struct](https://learn.microsoft.com/dotnet/csharp/programming-guide/statements-expressions-operators/how-to-define-value-equality-for-a-type)
- [dotnet/runtime: ValueType.cs](https://github.com/dotnet/runtime/blob/main/src/libraries/System.Private.CoreLib/src/System/ValueType.cs)
