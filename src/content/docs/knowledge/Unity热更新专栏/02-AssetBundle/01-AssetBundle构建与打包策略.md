---
title: "2.1 AssetBundle 构建与打包策略"
description: AssetBundle 的文件结构、BuildPipeline 与 Scriptable Build Pipeline、压缩格式、依赖与重复打包、粒度划分策略、TypeTree 与增量构建。
sidebar:
  order: 1
---

> 适用版本：Unity 2021 LTS 到 Unity 6000.x。内置 `BuildPipeline.BuildAssetBundles` 仍可用，Addressables 底层使用 Scriptable Build Pipeline（SBP）。选项名称以 `BuildAssetBundleOptions` 官方 API 为准，个别选项在新版本的行为差异标"待核实"。

## 要点

- AssetBundle（AB）是 Unity 的资源归档格式：包含序列化的资源对象和一个资源表，可在运行时按名加载。它**不包含脚本代码本体**，只记录对脚本类型的引用。
- AB 里的资源依赖其他资源时：被依赖资源若未在任何 AB 中显式标记，会被**复制进每一个引用它的 AB**，造成重复打包与内存重复。解法是把共享资源单独成包，并在加载时先加载依赖。
- 压缩格式三种：不压缩、LZMA（体积最小，加载时整包解压）、LZ4（`ChunkBasedCompression`，按块解压，支持随机访问）。运行时加载首选 LZ4 或不压缩，LZMA 多用于下载传输。
- 打包粒度是工程取舍：粒度太大，改动一个文件就要重下整个包，内存里也会驻留很多用不到的资源；粒度太小，文件数暴涨，依赖管理复杂，IO 与请求次数增多。
- 构建产物需要保证**可复现、内容稳定**，否则每次打包哈希都变，增量更新失效。

## AB 的逻辑结构

一个 AB 由两部分组成：

1. **头部与资源表**：记录文件名到资源对象的映射、压缩信息。
2. **序列化对象数据**：贴图、网格、预制体里的各 Object，附带可选的 TypeTree。

此外构建会产出一个与目录同名的"总 AB"和对应的 `.manifest` 文本，其中记录每个 AB 的哈希、依赖列表。运行时可以读取 `AssetBundleManifest` 获得依赖关系。

## 构建方式

### 内置 BuildPipeline

```csharp
using UnityEditor;

public static class BuildAB
{
    [MenuItem("Tools/Build AssetBundles")]
    static void Build()
    {
        string outDir = "Build/AB/Android";
        System.IO.Directory.CreateDirectory(outDir);
        BuildPipeline.BuildAssetBundles(
            outDir,
            BuildAssetBundleOptions.ChunkBasedCompression,   // LZ4
            BuildTarget.Android);
    }
}
```

AB 名由资源的 `assetBundleName` 属性指定（可通过 `AssetImporter.GetAtPath(path).assetBundleName = "ui_main"` 在脚本里批量设置）。也可以使用 `AssetBundleBuild[]` 参数，在代码里直接描述"哪些资源进哪个包"，不依赖资源上的标记。

常用选项：

| 选项 | 作用 |
|---|---|
| `None` | 默认 LZMA 压缩 |
| `UncompressedAssetBundle` | 不压缩，加载最快，体积最大 |
| `ChunkBasedCompression` | LZ4 块压缩，推荐 |
| `DeterministicAssetBundle` | 让资源 ID 稳定（新版本默认行为，待核实） |
| `AppendHashToAssetBundleName` | 把哈希加进文件名 |
| `DisableWriteTypeTree` | 不写 TypeTree，包更小，但要求构建与运行的 Unity 版本一致 |
| `ForceRebuildAssetBundle` | 强制重建全部 |

### Scriptable Build Pipeline（SBP）

SBP 是可编程的构建管线，以任务（task）为单位，可替换、可插入。Addressables 用它作为打包底层，纯 AB 方案也可以使用 `com.unity.scriptablebuildpipeline` 包以获得更好的增量构建和缓存。它的优势是构建缓存更智能、能自定义依赖处理、产出更详细的构建报告（待核实各版本细节）。

## 压缩格式与运行时代价

| 格式 | 体积 | 加载方式 | 适用 |
|---|---|---|---|
| 不压缩 | 最大 | 可直接内存映射，最快 | 本地缓存后的加载 |
| LZ4 | 中等 | 按块解压，可读取局部 | 运行时首选 |
| LZMA | 最小 | 加载需整包解压到内存 | 传输下载，下载后再转存为 LZ4 |

注意：用 `UnityWebRequestAssetBundle` 下载的 LZMA 包，Unity 会在缓存时重压缩（取决于缓存压缩设置），`AssetBundle.LoadFromFile` 对 LZMA 包要整包解压，峰值内存高。

## 依赖与重复打包

场景：预制体 A、B 都引用材质 M，材质引用贴图 T。若 M、T 没有被任何 AB 显式标记：

- 打 A 的 AB 时，M、T 被复制进包 A；
- 打 B 的 AB 时，M、T 又被复制进包 B；
- 运行时同时加载 A、B，内存里有两份 T。

解决：

1. 把共享的 M、T 放进独立的"公共包"（如 `common_textures`），A、B 依赖它。
2. 构建后用工具分析重复资源（Unity 的 Build Report、第三方分析工具，或自写脚本遍历 `GetDependencies`）。
3. 明确"一个资源只属于一个包"的规则，在构建管线里做校验。

## 打包粒度策略

常见划分方式：

- **按功能模块**：一个 UI 界面一个包，一个副本一个包。粒度较大，适合经常整体加载的内容。
- **按资源类型**：贴图、音频、Shader、预制体分开，便于单独更新和单独清理。
- **按更新频率**：把几乎不变的底层资源（Shader、字体、通用图集）与经常变的活动资源分开，减少重下体积。
- **公共资源单独成包**：Shader 变体集合（ShaderVariantCollection）、字体、通用图集。

原则：同时被加载的东西尽量同包，同时更新的东西同包，生命周期不同的东西分包。

## TypeTree 与版本兼容

TypeTree 描述了序列化对象的字段结构。写入 TypeTree 时，不同 Unity 版本构建的 AB 可以被向前兼容地读取；用 `DisableWriteTypeTree` 可以让包更小、加载略快，但要求 AB 与 Player 的 Unity 版本一致，升级引擎后须重新出包。选择取决于是否会出现"引擎升级但旧热更包仍在使用"的情况。

## 常见坑

1. **Shader 丢失或变粉**：Shader 被剥离或未打进包，须将 Shader 与变体集合单独打包并预加载。
2. **脚本引用丢失**：AB 只存脚本引用，脚本所在程序集必须在运行时存在。热更程序集里的 MonoBehaviour 需要在加载 AB 前先加载程序集（见 4.2）。
3. **重复打包**：公共依赖没有显式成包，包体和内存翻倍。
4. **每次构建哈希都变**：构建环境不一致、资源导入设置有差异、时间戳参与哈希。固定 Unity 版本与导入设置，使用确定性选项。
5. **AB 名大小写**：AB 名统一小写，避免平台差异带来的找不到文件。
6. **LZMA 直接 LoadFromFile**：启动时峰值内存飙升，应转 LZ4。

## 面试追问

**Q：AB 里为什么会有重复资源，怎么解决？**
被依赖但未显式标记的资源会被复制进每个引用它的包。解法是把共享资源单独成包，并校验“一个资源只属于一个包”。

**Q：LZMA 与 LZ4 的取舍？**
LZMA 体积小但需整包解压，适合下载传输；LZ4 按块解压，体积略大但支持随机访问，适合运行时加载。

**Q：AB 能包含脚本吗？**
不能。AB 里只有对脚本的引用，脚本代码要由包或热更程序集提供。

## 参考资料

- [Unity Manual: AssetBundles 工作流](https://docs.unity3d.com/Manual/AssetBundlesIntro.html)
- [Unity Scripting API: BuildAssetBundleOptions](https://docs.unity3d.com/ScriptReference/BuildAssetBundleOptions.html)
- [Unity Manual: Asset bundle compression](https://docs.unity3d.com/Manual/AssetBundles-Building.html)
- [Scriptable Build Pipeline 文档](https://docs.unity3d.com/Packages/com.unity.scriptablebuildpipeline@latest)
