---
title: "5.2 Wrap 生成、GC 与性能优化"
description: Lua 与 C# 交互的开销来源、Wrap 生成与裁剪、值类型与 GC 分配、Lua 侧的写法优化、脚本加载与调试。
sidebar:
  order: 2
---

> 适用版本：xLua、ToLua 的常见版本。性能数据没有统一基准，**所有量化判断应以项目内的 Profiler 实测为准**。特定版本的优化特性（例如无 GC 的 Vector3 传递）需查所用版本的文档，标"待核实"。

## 要点

- Lua 方案的性能问题大多出在**边界**：Lua 与 C# 之间每一次调用、每一次对象传递都有成本，包括栈操作、类型检查、对象表查找、GC 分配。
- 优化方向：**减少跨界次数、避免每帧创建临时 table/userdata、避免反射兜底、让热点逻辑留在一侧**。
- Wrap 的生成要有范围控制：生成太多导致包体和代码量膨胀、IL2CPP 编译时间长；生成太少会走反射。
- 内存要同时看两个堆：Lua 堆（`collectgarbage("count")`）和 C# 托管堆，二者的 GC 触发时机不同步。

## 开销来源

一次 `go.transform.position = pos` 的 Lua 调用大致发生：

1. Lua 取 `go`（userdata）→ 查对象表得到 C# 对象。
2. 访问 `transform`：调用 C# 属性，返回的对象再注册到对象表并包装为 userdata。
3. 设置 `position`：把 `pos` 从 Lua 值转换为 C# 的 `Vector3` 再调用。
4. 每个环节都可能产生临时对象、查表。

对比纯 C# 的一次赋值，开销高出一到两个数量级（量级仅为示意，待实测）。所以**不要在 Lua 的每帧循环里对大量对象做细碎的属性读写**。

## Wrap 生成与管理

- 只对 Lua 确实需要调用的类型生成 Wrap：业务相关类、常用的 Unity 类（`GameObject`、`Transform`、`Image` 等）。
- 配置方式：xLua 使用配置类（实现 `LuaCallCSharp` 列表）或标签；通过白名单控制。
- 生成的代码要与 C# 工程一起参与编译，因此**Wrap 会固化 C# 的 API 形态**。如果 C# 类型改了公开成员而未重新生成，会出现运行时找不到成员或签名不匹配。
- 生成代码要纳入 CI：每次构建前先生成再编译，避免与源码不一致。
- 避免为大量不常用类型生成 Wrap，它们会放大 IL2CPP 产出的 C++ 体量和构建时间。
- 裁剪：Wrap 里引用的类型不会被 stripping 删掉，但“只用反射访问”的类型需要 `link.xml` 或标签保留，否则真机找不到（与 C# 底层专栏 4.2 同理）。

## GC 与内存

### C# 侧分配

常见分配点：

- 反射调用：参数装箱、`object[]` 分配。
- 值类型传递：`Vector3`、`Quaternion`、`Color` 等装箱成 userdata。
- `string` 往返：Lua 字符串到 C# `string` 的转换（编码与复制）。
- 委托：`[CSharpCallLua]` 生成的委托适配器对象；频繁创建 Lua 闭包并传给 C# 事件。

### Lua 侧分配

- 每帧创建 table（如 `{x, y, z}`）。
- 字符串拼接（`..`）。
- 闭包创建。

### 管理方法

1. **对象复用**：热路径预分配 table，每帧重用。
2. **字符串缓存**：把要频繁使用的拼接结果缓存。
3. **手动 GC 控制**：在战斗等关键阶段停用 Lua 的自动 GC（`collectgarbage("stop")`），在加载界面或切场景时手动 `collectgarbage("collect")`。xLua 提供 `luaEnv.Tick()` 驱动其内部 GC 逻辑，需要定期调用（待核实）。
4. **注意跨堆引用**：Lua 里持有 C# 对象，或者 C# 持有 Lua 函数（委托），任一端不释放都会使对方不能回收。离开界面时要置空 Lua 引用并 `Dispose` 掉保存的 `LuaFunction`/`LuaTable`（xLua 里它们是需要释放的 C# 对象，不释放会泄漏，待核实）。

## Lua 写法优化

```lua
-- 差: 每帧反复查全局、反复调用跨界属性
function Update()
    local t = CS.UnityEngine.GameObject.Find("Player").transform
    t.position = CS.UnityEngine.Vector3(t.position.x + 1, 0, 0)
end

-- 好: 缓存引用，减少跨界，必要时把运算放到 C# 辅助方法里
local transform
function Start()
    transform = self.gameObject.transform
end
function Update()
    CSUtil.MoveX(transform, 1)   -- 一次调用完成读取和写入,C# 内部无 Lua 开销
end
```

通用做法：

- 局部变量缓存常用的 `CS.xxx` 类型引用，避免每次从 `CS` 命名空间逐级查找。
- 把批量处理放进 C# 辅助函数，Lua 只做调度。
- 不用 Lua 做密集计算（寻路、物理、大规模循环），交给 C#。
- 用 `table.concat` 代替循环字符串拼接。

## 脚本加载

- 脚本不要散文件，打包成 AB 或自定义归档，降低 IO 次数。
- 启动时批量预加载常用脚本，运行时 `require` 只查缓存。
- 可预编译成 Lua 字节码，加快解析；但要与所用的 Lua 版本一致，且调试和排错不方便（待核实）。
- 加密与签名见 7.2。

## 调试与排错

- 使用 Lua 调试器（EmmyLua、LuaPanda 等，具体可用工具待核实）进行断点调试，需要把脚本源路径映射好。
- 报错堆栈要同时能看到 C# 和 Lua 的调用链，统一日志入口，把 Lua 错误转发到 C# 日志并上报。
- 内存泄漏：定期打印 `collectgarbage("count")`，结合对象表大小；用 Lua 侧的引用快照工具对比。

## 常见坑

1. **每帧在 Lua 里创建 `CS.UnityEngine.Vector3(...)`**：持续 GC 分配与卡顿。
2. **漏生成 Wrap 触发反射**：编辑器没事，真机反射失败或慢。
3. **事件订阅没有退订**：C# 事件里挂了 Lua 函数，界面销毁后函数仍被持有。
4. **`LuaFunction` 不释放**：在 C# 保存 Lua 函数，关闭时必须 `Dispose`。
5. **在战斗中触发 Lua 全量 GC**：产生明显的停顿，应控制时机。
6. **Wrap 与 C# 不同步**：改了 C# API 没有重新生成。

## 面试追问

**Q：Lua 项目里 GC 压力大，怎么排查？**
区分 Lua 堆和 C# 堆。C# 侧用 Profiler 查看 GC.Alloc 的调用栈，是否来自反射、装箱或字符串转换；Lua 侧查每帧创建的 table、字符串和闭包。

**Q：为什么要生成 Wrap？**
避免反射。Wrap 是预生成的静态绑定，调用直接进 C# 方法，无反射和 `object[]` 分配；同时 IL2CPP 无法运行时生成代码，需要预先生成。

**Q：怎么让 Lua 和 C# 的边界开销降下来？**
减少跨界调用次数，缓存引用，批量接口，热点逻辑留在 C#，避免在热路径传递值类型与创建临时对象。

## 参考资料

- [xLua 文档（含 FAQ 与性能相关说明）](https://github.com/Tencent/xLua/tree/master/Assets/XLua/Doc)
- [Lua 性能指南 (Lua Performance Tips)](https://www.lua.org/gems/sample.pdf)
- [Unity Manual: Profiler 与 GC.Alloc 分析](https://docs.unity3d.com/Manual/profiler-introduction.html)
