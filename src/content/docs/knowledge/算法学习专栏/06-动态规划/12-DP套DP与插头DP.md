---
title: "6.12 ⭐DP 套 DP 与插头 DP"
description: "把内层 DP 的整行结果压成外层 DP 的状态，统计 DP 结果满足条件的对象个数；再用轮廓线与括号表示做网格上的连通性 DP。"
sidebar:
  order: 612
  badge:
    text: 进阶
    variant: caution
---

> 适用版本：C++17。前置：6.2 线性 DP（LCS）、6.6 状压 DP。什么时候需要学：要统计「某个 DP 的结果等于 k」的对象有多少个（DP 套 DP）；或者要在小网格上数回路、路径（插头 DP）。两部分互相独立，可以分开读。

## 要点

- DP 套 DP：外层 DP 的状态就是内层 DP 当前的整个状态（一行或一个数组），要求这个状态能压缩得很小。
- 原始做法是枚举所有对象，再对每个对象跑一遍内层 DP，对象数是指数级。
- 条件：内层 DP 的状态在压缩后个数有限（如差分只有 0/1，压成 m 位二进制数）。
- 插头 DP 是轮廓线 DP 的推广：逐格推进，状态记录「轮廓线上哪些位置有路径穿过」，再用括号标明哪些位置属于同一条路径。
- 状态数随网格宽度 m 指数增长，m 一般不超过 12 到 14。

## 第一部分：DP 套 DP

### 问题与瓶颈

给定一个 DNA 串 S（长度 m ≤ 15，字符集 ACGT）。对每个 k = 0..m，统计长度为 n 的 ACGT 串 T 中，满足 LCS(S, T) = k 的个数，对 1e9+7 取模。

原始想法：枚举全部 4ⁿ 个 T，对每个跑 O(mn) 的 LCS。n 稍大就不行。

### 观察：LCS 一行可以压成 m 位

LCS 的内层 DP：令 f[j] = LCS(S 的前 j 个字符, 当前已生成的 T)。每追加 T 的一个字符，f 整行更新一次：

```
g[j] = max(g[j-1], f[j])                  若 S[j] ≠ 新字符
g[j] = f[j-1] + 1                          若 S[j] = 新字符
```

f 本身的值有 m 种，范围 0..m，一整行 f 有 (m+1)^m 种取值，状态太多。但是相邻的差有很强的限制：

```
f[j-1] ≤ f[j] ≤ f[j-1] + 1
```

因为多看一个字符，LCS 最多增加 1，也不会减少。所以差分 `f[j] - f[j-1]` 只能是 0 或 1，整行 f 由 m 个 0/1 决定，压成一个 m 位二进制数 mask 即可，状态数 2^m ≤ 32768。mask 中 1 的个数就是 f[m] = LCS 的长度。

![S=ABCB，依次追加 B、C、B，每一行 f 对应一个差分 mask，最后 mask=0111，LCS=3](/qmx-Gameknowledge/assets/algo/c6-12-lcs-bits.svg)

### 外层 DP

外层状态：`dp[i][mask]` 表示已经生成了 i 个字符，并且内层 DP 状态为 mask 的 T 的个数。转移：枚举追加的字符 c，按内层的更新规则从 mask 得到新状态 `trans[mask][c]`。转移表可以预处理，O(2^m · 4 · m)。

最终答案：`ans[k] = Σ dp[n][mask]`，其中 mask 的二进制 1 的个数为 k。

总复杂度 O(2^m · 4 · m + n · 2^m · 4)。

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll MOD = 1e9 + 7;

// 给定 DNA 串 S（长度 m <= 15，字符集 ACGT），对每个 k = 0..m，
// 统计长度为 n 的 ACGT 串 T 中，满足 LCS(S, T) = k 的个数
// 内层 DP：f[j] = LCS(S 的前 j 个字符, 当前已生成的 T)。相邻差 f[j]-f[j-1] 只会是 0 或 1，
// 所以整行 f 可以压成一个 m 位的二进制数 mask（第 j-1 位 = f[j]-f[j-1]）
int main() {
    int n;
    string S;
    cin >> S >> n;
    int m = S.size();
    const string AL = "ACGT";
    int full = 1 << m;
    // trans[mask][c]：当前内层状态为 mask，再追加字符 AL[c] 之后的新状态
    vector<array<int, 4>> trans(full);
    for (int mask = 0; mask < full; mask++) {
        vector<int> f(m + 1, 0), g(m + 1, 0);
        for (int j = 1; j <= m; j++) f[j] = f[j - 1] + ((mask >> (j - 1)) & 1);
        for (int c = 0; c < 4; c++) {
            for (int j = 1; j <= m; j++) {
                g[j] = max(g[j - 1], f[j]);
                if (S[j - 1] == AL[c]) g[j] = max(g[j], f[j - 1] + 1);
            }
            int nm = 0;
            for (int j = 1; j <= m; j++) nm |= (g[j] - g[j - 1]) << (j - 1);
            trans[mask][c] = nm;
        }
    }
    // 外层 DP：dp[mask] = 生成了 i 个字符、内层状态为 mask 的串的个数
    vector<ll> dp(full, 0), nd(full);
    dp[0] = 1;                            // 空串：f 全为 0
    for (int i = 0; i < n; i++) {
        fill(nd.begin(), nd.end(), 0);
        for (int mask = 0; mask < full; mask++) {
            if (!dp[mask]) continue;
            for (int c = 0; c < 4; c++) {
                int nm = trans[mask][c];
                nd[nm] = (nd[nm] + dp[mask]) % MOD;
            }
        }
        dp = nd;
    }
    vector<ll> ans(m + 1, 0);
    for (int mask = 0; mask < full; mask++)
        ans[__builtin_popcount(mask)] = (ans[__builtin_popcount(mask)] + dp[mask]) % MOD;
    for (int k = 0; k <= m; k++) cout << ans[k] << "\n";
    return 0;
}
```

输入 `ACG` 与 `2`（S = ACG，n = 2），输出 `1 12 3 0`：16 个长度为 2 的串里，LCS 为 0 的只有 `TT` 一个，LCS 为 2 的是 AC、AG、CG 三个。

### 通用套路

1. 写出内层 DP，确认它的「状态」是什么（一行、一个数组、一个集合）。
2. 找出压缩方法：差分有界、取值有界、可以排序去重。
3. 把压缩后的内层状态作为外层 DP 的状态，转移就是「内层追加一个元素」。
4. 在外层 DP 的终止状态上读出内层答案。

## 第二部分：轮廓线 DP 与插头 DP

### 从轮廓线 DP 开始：多米诺铺满棋盘

用 1×2 的骨牌铺满 n×m 棋盘，数方案。逐格处理，处理到 (i, j) 时，之前的信息只剩一条「轮廓线」：长度为 m 的 0/1 串，记录 m 个位置的格子是否已被占。

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

// 轮廓线 DP：用 1×2 的多米诺骨牌铺满 n×m 的棋盘，求方案数（n、m 较小时）
// 逐格处理，mask 的第 j 位表示：
//   当前行已处理过的列（< 当前列）：下一行第 j 格是否已被竖放的骨牌占住
//   当前行未处理的列（>= 当前列）：当前行第 j 格是否已被占住
int main() {
    int n, m;
    cin >> n >> m;
    vector<ll> dp(1 << m, 0), nd(1 << m);
    dp[0] = 1;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            fill(nd.begin(), nd.end(), 0);
            for (int mask = 0; mask < (1 << m); mask++) {
                ll v = dp[mask];
                if (!v) continue;
                if (mask >> j & 1) {
                    // 这一格已被占：清掉标记，下一行的这一格不被占
                    nd[mask ^ (1 << j)] += v;
                } else {
                    // 竖放：占住这一格和下一行同列的格子
                    if (i + 1 < n) nd[mask | (1 << j)] += v;
                    // 横放：占住这一格和右边的格子（右边必须存在且空）
                    if (j + 1 < m && !(mask >> (j + 1) & 1)) nd[mask | (1 << (j + 1))] += v;
                }
            }
            swap(dp, nd);
        }
    }
    cout << dp[0] << "\n";
    return 0;
}
```

输入 `3 4`，输出 `11`；输入 `8 8` 输出 `12988816`，都与已知结果一致。

状态数 2^m，格子数 n·m，总复杂度 O(n·m·2^m)。

### 插头 DP：数网格里的哈密顿回路

把「是否被占」换成「是否有路径穿过轮廓线」。每条穿过轮廓线的路径段称为一个**插头**，沿轮廓线从左到右，每个位置有三种情形：

- 0：没有插头。
- 1：左括号，这条路径的一端。
- 2：右括号，同一条路径的另一端，与前面最近的未配对的左括号配对。

括号配对表示的是「轮廓线上哪两个插头在已处理部分是连通的」，这个信息对避免提前闭合成环必不可少。

![3×4 网格处理到 (1,2)：轮廓线上有 5 个位置，状态是 1 2 0 1 2](/qmx-Gameknowledge/assets/algo/c6-12-plug-profile.svg)

处理格子 (i, j) 时，轮廓线下标 j 是从左边来的插头 a，下标 j+1 是从上边来的插头 b。这个格子必须恰好有两条边，所以分情况（障碍格要求 a = b = 0 并保持状态不变）：

- a = 0 且 b = 0：新开一条路径，向下和向右各伸出一个插头，写作 `( )`。
- 只有一个插头 c：路径继续，向下或向右延伸。
- a = 1，b = 1：两个左括号相连，b 的配对右括号（向右找）变成左括号。
- a = 2，b = 2：两个右括号相连，a 的配对左括号（向左找）变成右括号。
- a = 2，b = 1：不同路径相连，两端自动配成新的一对，括号序列不用改。
- a = 1，b = 2：同一条路径首尾相接，形成回路。只有当这是最后一个空格、并且轮廓线其余位置都是 0 时才计入答案，否则这个状态作废。

![六种情形的括号序列变化](/qmx-Gameknowledge/assets/algo/c6-12-plug-cases.svg)

每行末尾要把整个状态左移一个位置（下一行的第 0 格没有左插头），并要求最右边的插头为 0。状态用 2 位一组编码在一个 long long 里，用哈希表保存「状态 → 方案数」。

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

// 插头 DP：n×m 网格，'.' 为空格、'*' 为障碍，
// 求经过所有空格恰好一次的回路（哈密顿回路）条数。
// 状态：轮廓线上 m+1 个位置，每个位置 2 位：0 无插头，1 左括号插头，2 右括号插头。
// 处理格子 (i,j) 时，下标 j 是从左边来的插头，下标 j+1 是从上边来的插头。
int n, m;
vector<string> g;

static inline int getp(ll s, int k) { return (int)((s >> (2 * k)) & 3); }
static inline ll setp(ll s, int k, ll v) { return (s & ~(3LL << (2 * k))) | (v << (2 * k)); }

int main() {
    cin >> n >> m;
    g.resize(n);
    int ei = -1, ej = -1;                 // 最后一个空格，回路只能在这里闭合
    for (int i = 0; i < n; i++) {
        cin >> g[i];
        for (int j = 0; j < m; j++)
            if (g[i][j] == '.') ei = i, ej = j;
    }
    if (ei < 0) { cout << 0 << "\n"; return 0; }
    auto canGo = [&](int i, int j) { return i < n && j < m && g[i][j] == '.'; };

    unordered_map<ll, ll> cur, nxt;
    cur[0] = 1;
    ll ans = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            nxt.clear();
            for (auto& [s, v] : cur) {
                int a = getp(s, j), b = getp(s, j + 1);   // a：左插头，b：上插头
                if (g[i][j] == '*') {                      // 障碍格：不能有插头进来
                    if (a == 0 && b == 0) nxt[s] += v;
                    continue;
                }
                ll base = setp(setp(s, j, 0), j + 1, 0);   // 清掉两个插头后的状态
                if (a == 0 && b == 0) {
                    // 新开一条路径：向下、向右各伸出一个插头
                    if (canGo(i + 1, j) && canGo(i, j + 1))
                        nxt[setp(setp(base, j, 1), j + 1, 2)] += v;
                } else if (a == 0 || b == 0) {
                    // 只有一个插头进来：继续向下或向右延伸
                    int c = a | b;
                    if (canGo(i + 1, j)) nxt[setp(base, j, c)] += v;
                    if (canGo(i, j + 1)) nxt[setp(base, j + 1, c)] += v;
                } else if (a == 1 && b == 1) {
                    // 两个左括号合并：b 的配对右括号变成左括号
                    int d = 1;
                    ll t = base;
                    for (int k = j + 2;; k++) {
                        int x = getp(s, k);
                        if (x == 1) d++;
                        else if (x == 2 && --d == 0) { t = setp(t, k, 1); break; }
                    }
                    nxt[t] += v;
                } else if (a == 2 && b == 2) {
                    // 两个右括号合并：a 的配对左括号变成右括号
                    int d = 1;
                    ll t = base;
                    for (int k = j - 1;; k--) {
                        int x = getp(s, k);
                        if (x == 2) d++;
                        else if (x == 1 && --d == 0) { t = setp(t, k, 2); break; }
                    }
                    nxt[t] += v;
                } else if (a == 2 && b == 1) {
                    nxt[base] += v;                        // 右括号接左括号：直接连上，括号序列不变
                } else {
                    // a == 1, b == 2：同一条路径的两端相接，形成回路
                    if (i == ei && j == ej && base == 0) ans += v;
                }
            }
            swap(cur, nxt);
        }
        // 换行：整体左移一个位置，最右边的插头不能存在
        nxt.clear();
        for (auto& [s, v] : cur)
            if (getp(s, m) == 0) nxt[s << 2] += v;
        swap(cur, nxt);
    }
    cout << ans << "\n";
    return 0;
}
```

输入：

```
4 4
....
....
....
....
```

输出 `6`。6×6 的全空网格输出 `1072`，10×10 输出 `467260456608`，都与已知的哈密顿回路计数一致。再看带障碍的输入：

```
3 4
....
.*..
....
```

输出 `0`。空格数是 11，网格图是二分图（按棋盘黑白染色），回路必然交替经过黑白格，所以经过全部空格的回路要求空格数为偶数。

复杂度：O(n·m·S)，S 是合法括号状态的个数，随 m 近似指数增长；m 到 12 一般还能跑。

## 适用与不适用

适用：

- DP 套 DP：统计「某个 DP 的结果取某个值」的对象数，且内层 DP 的状态能压成很少的几种。
- 插头 DP：网格小（一边不超过 12 到 14）、要求路径、回路、连通性。

不适用：

- 内层状态无法压缩（如 LCS 的差分不限于 0/1）。
- 网格两边都很大。可以把较短的一边作为 m。
- 要处理的结构不是简单的路径和回路，而是树、多条路径、带权值的复杂约束时，插头的状态需要扩展（如 3 种插头甚至更多）。

## 常见坑

- DP 套 DP 里的内层更新必须与朴素 DP 逐行对照，建议先写一个枚举全部 T 再算 LCS 的暴力程序，对拍几十组小数据。
- 插头 DP 的括号匹配要从正确的位置开始找：a=1,b=1 向右找 b 的匹配，a=2,b=2 向左找 a 的匹配，初始深度都是 1。
- 换行时没有把最右边（下标 m）的插头清掉，会让路径从右边「穿」到下一行最左边。
- 回路闭合的条件漏掉「最后一个空格」，会把不经过所有空格的小环也算进去；遇到没有空格的网格要单独处理。
- 状态编码每个位置占 2 位，轮廓线共 m+1 个位置，要用 long long 而不是 int（m 较大时超过 32 位）。

## 练习

入门

- LeetCode 790 多米诺和托米诺平铺（轮廓线的简化版，状态很小）
- 洛谷 P1879 [USACO06NOV] Corn Fields（状压 DP，轮廓线的前身）
- POJ 2411 Mondriaan's Dream（多米诺铺满棋盘，题号待核实）

进阶

- 洛谷 P1896 [SCOI2005] 互不侵犯（状压 / 轮廓线）
- 洛谷 P5056 【模板】插头 dp（回路计数）
- HDU 4899 Hero meet devil（DP 套 DP，本篇例题；题号待核实）

挑战

- 洛谷 P4590 [TJOI2018] 游园会（DP 套 DP，LCS，题号待核实）
- 洛谷 P3190 [HNOI2007] 神奇游乐园（带权的插头 DP，可以走单条路径）

本章完。
