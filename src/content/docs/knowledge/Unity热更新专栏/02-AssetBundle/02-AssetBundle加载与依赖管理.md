---
title: "2.2 AssetBundle 加载与依赖管理"
description: LoadFromFile、LoadFromMemory 与 UnityWebRequest 三种加载方式的区别、依赖先加载、异步加载流程、同名包冲突、资源管理器的基本设计。
sidebar:
  order: 2
---

> 适用版本：Unity 2021 LTS 到 Unity 6000.x。API 名称以 `AssetBundle` 与 `UnityWebRequestAssetBundle` 官方文档为准。

## 要点

- 加载 AB 分两步：先加载 **AB 文件本身**（得到 `AssetBundle` 对象），再从中**加载具体资源**（`LoadAsset`）。两步都有同步和异步版本。
- 三种来源：`LoadFromFile`（本地文件，最省内存）、`LoadFromMemory`（字节数组，会多一份内存，一般不推荐）、`UnityWebRequestAssetBundle`（网络或本地，带缓存）。
- 依赖需要**手动先加载**：加载包 A 之前，要把 A 依赖的所有包加载完，否则 A 中资源的引用丢失（表现为材质变粉、贴图空白）。
- 同一个 AB 不能重复加载（同名包未卸载时再加载会报错），必须自己做缓存与引用计数。
- 卸载要小心：`Unload(false)` 与 `Unload(true)` 语义不同，见 2.3。

## 三种加载方式对比

| 方式 | 数据来源 | 内存占用 | 是否支持 LZMA | 适用 |
|---|---|---|---|---|
| `AssetBundle.LoadFromFile(Async)` | 本地文件路径 | 最小（未压缩或 LZ4 可按需读取） | 支持，但整包解压 | 已下载到本地的包（首选） |
| `AssetBundle.LoadFromMemory(Async)` | `byte[]` | 字节数组 + 解析后一份 | 支持 | 自行解密后再加载 |
| `UnityWebRequestAssetBundle.GetAssetBundle` | URL（http/file） | 由 Unity 管理，可走缓存 | 支持 | 直接从网络加载并缓存 |

加密包的处理：如果对 AB 做了字节级加密，运行时需要先解密再 `LoadFromMemory`，这会让内存里同时存在原始字节和解析数据。可选方案是只加密文件头部若干字节并在流式读取时解密，或使用解密后落盘再 `LoadFromFile`，代价是明文暴露在磁盘上，见 7.2。

## 异步加载示例

```csharp
IEnumerator LoadBundle(string path, Action<AssetBundle> done)
{
    var req = AssetBundle.LoadFromFileAsync(path);
    yield return req;
    done(req.assetBundle);   // 失败为 null，必须判空
}

IEnumerator LoadAsset<T>(AssetBundle ab, string name, Action<T> done) where T : UnityEngine.Object
{
    var req = ab.LoadAssetAsync<T>(name);
    yield return req;
    done(req.asset as T);
}
```

注意：`LoadAsset` 参数是 **AB 内资源名**（通常是资源路径或文件名，取决于构建方式），写错会返回 null，不会抛异常。

## 依赖加载

```csharp
// manifest 来自总 AB 的 AssetBundleManifest
string[] deps = manifest.GetAllDependencies("ui_main");
foreach (var d in deps) yield return LoadBundleOnce(d);   // 先加载依赖
yield return LoadBundleOnce("ui_main");
```

要点：

- `GetAllDependencies` 返回递归的全部依赖，`GetDirectDependencies` 只返回一层。
- 已加载的包不要重复加载，维护一个 `Dictionary<string, BundleRef>` 做缓存。
- 并发加载同一个包时，第二个请求应等待第一个完成，而不是再发起加载。

## 同名包冲突

同一个 AB 文件已经加载，再次 `LoadFromFile` 会失败，日志类似 "The AssetBundle 'xxx' can't be loaded because another AssetBundle with the same files is already loaded"。解决：统一经过资源管理器，加载前先查缓存，卸载后再重新加载。

## 资源管理器的基本设计

一个能用的最小设计：

```csharp
class BundleRef
{
    public AssetBundle bundle;
    public int refCount;
    public string[] deps;
}
```

- `Acquire(bundleName)`：引用计数加一；首次加载时递归加载依赖，依赖的引用计数同样加一。
- `Release(bundleName)`：引用计数减一；归零时按策略卸载，并递归释放依赖。
- 对外暴露按资源路径加载的接口，内部映射到 `bundleName + assetName`，调用方不关心包名。
- 区分"常驻包"（Shader、字体、通用图集）与"临时包"（某个界面），常驻包不参与卸载。

引用计数的难点：谁持有资源、何时释放。常见约定是以"界面/场景/实体"为生命周期单位，在其创建时 Acquire，销毁时 Release。

## 加载线程与卡顿

- 异步加载由后台线程读取与反序列化，但**最终对象实例化与上传（贴图上传 GPU、网格上传）仍在主线程**，大量同时加载会造成帧率波动。可使用 `Application.backgroundLoadingPriority` 控制后台加载优先级，换取更平滑的帧时间，代价是加载更慢。
- 大批量加载分帧：每帧限制并发数或耗时预算。
- `Instantiate` 大预制体本身也是主线程开销，需要预热或对象池配合（参见 C# 底层专栏 3.5）。

## 常见坑

1. **忘记先加载依赖**：材质变粉、引用为 null。
2. **同包重复加载**：报错且返回 null，要有缓存与等待队列。
3. **`LoadAsset` 名字写错**：返回 null 不报异常，要判空并打日志。
4. **把 `LoadFromMemory` 当主力**：内存翻倍，仅在必须自行解密时使用。
5. **异步回调时对象已销毁**：请求发出后界面关闭，回调里访问空引用。需要为请求设置取消或有效性标记。
6. **同步加载造成卡顿**：`LoadAsset`、`LoadFromFile` 在大资源上会明显阻塞，运行时尽量用异步。

## 面试追问

**Q：为什么加载一个 AB 里的资源前要先加载它的依赖包？**
AB 内资源对其他 AB 内资源的引用靠 AB 之间的依赖解析，依赖包没加载则引用解析为空，表现为资源缺失。

**Q：`LoadFromFile` 与 `LoadFromMemory` 的区别？**
前者由引擎直接读文件，不额外占一份字节数组；后者需要先把整个字节数组读进托管或原生内存再解析，峰值内存更高。

**Q：怎样避免重复加载同一个 AB？**
统一经过资源管理器，用字典缓存加载状态（未加载、加载中、已加载），加载中的请求排队等待同一个结果。

## 参考资料

- [Unity Scripting API: AssetBundle](https://docs.unity3d.com/ScriptReference/AssetBundle.html)
- [Unity Manual: Loading AssetBundles](https://docs.unity3d.com/Manual/AssetBundles-Native.html)
- [Unity Scripting API: UnityWebRequestAssetBundle](https://docs.unity3d.com/ScriptReference/Networking.UnityWebRequestAssetBundle.html)
- [Unity Scripting API: Application.backgroundLoadingPriority](https://docs.unity3d.com/ScriptReference/Application-backgroundLoadingPriority.html)
