---
title: "4.6 树的 DFS 序与子树查询"
description: "用进入时间把子树映射为数组连续区间，再配合前缀和、树状数组或线段树完成子树统计。"
sidebar:
  order: 406
---

> 适用版本：C++17。前置知识：4.5 一般树与树的直径，能写带父节点参数的 DFS。

## 本篇解决什么问题

树上经常出现这样的操作：给一个节点，询问它整棵子树的和、最大值或修改整棵子树。直接遍历子树的复杂度可能达到 O(n)，如果询问很多次就会超时。

DFS 序提供了一个关键转换：**一棵子树在 DFS 的进入顺序中对应一段连续区间**。于是树上的子树问题可以转成数组上的区间问题，再交给前缀和、树状数组或线段树处理。

## 进入时间和离开时间

从根开始 DFS。第一次到达节点 u 时记录 `tin[u]`，所有孩子都处理完、准备离开 u 时记录 `tout[u]`。

![DFS 序把每个子树映射为进入顺序中的连续区间](/qmx-Gameknowledge/assets/algo/c4-tree-dfs-order.svg)

如果使用进入顺序数组 `order`，节点 u 的子树满足：

```text
order[tin[u] .. tout[u]] 恰好是 u 的整棵子树
```

下面的例子中，节点 2 的子树节点是 2、4、5、7，它们在 DFS 序中连续出现。

```text
节点 u      1  2  4  5  7  3  6
进入时间    1  2  3  4  5  6  7
```

需要注意下标约定。本文使用 `tin` 从 1 开始，并让 `tout[u]` 表示子树最后一个节点在 `order` 中的位置。

## DFS 序模板

```cpp
#include <bits/stdc++.h>
using namespace std;

const int N = 100005;
vector<int> g[N];
int tin[N], tout[N], timer;
vector<int> order;

void dfs(int u, int parent) {
    tin[u] = ++timer;
    order.push_back(u);

    for (int v : g[u]) {
        if (v == parent) continue;      
        dfs(v, u);
    }

    tout[u] = timer;
}
```

为什么 `tout[u]` 可以直接取当前 `timer`？因为 DFS 处理完 u 的最后一个孩子后，u 的整棵子树已经全部进入 `order`，之后才会回到 u 的父亲并进入别的子树。

子树判断也可以写成进入和离开时间的包含关系：

```cpp
bool isAncestor(int u, int v) {
    return tin[u] <= tin[v] && tout[v] <= tout[u];
}
```

这里的“祖先”包含节点自身。这个判断在 LCA、树上路径和虚树等内容中都会出现。

## 子树求和

如果节点权值是 `value[u]`，先按 DFS 序重排成数组：

```cpp
flat[tin[u]] = value[u];
```

再对 `flat` 做前缀和，就能 O(1) 查询子树和：

```cpp
subtreeSum(u) = prefix[tout[u]] - prefix[tin[u] - 1]
```

```cpp
long long value[N], flat[N], prefix[N];

void prepare(int n) {
    for (int u = 1; u <= n; u++)
        flat[tin[u]] = value[u];
    for (int i = 1; i <= n; i++)
        prefix[i] = prefix[i - 1] + flat[i];
}

long long querySubtree(int u) {
    return prefix[tout[u]] - prefix[tin[u] - 1];
}
```

如果只有静态查询，前缀和足够。如果节点值会单点修改，换成树状数组。如果需要修改整棵子树，通常换成线段树并对 `[tin[u], tout[u]]` 操作。

## 子树修改为什么也能变成区间修改

DFS 序只改变了节点的排列顺序，没有改变“某节点属于哪棵子树”。因此：

| 树上的操作 | DFS 序后的数组操作 |
| --- | --- |
| 查询 u 的子树和 | 查询 `[tin[u], tout[u]]` |
| 修改 u 的权值 | 修改 `tin[u]` |
| 给 u 的整棵子树加 v | 给 `[tin[u], tout[u]]` 加 v |
| 查询 u 的子树最大值 | 查询 `[tin[u], tout[u]]` 的最大值 |

这也是树链剖分能处理子树操作的基础。树链剖分属于进阶内容，本篇只使用它的 DFS 序部分。

## 节点权和边权的区别

节点权可以直接放在 `flat[tin[u]]`。边权需要先约定它归属哪个节点，常用约定是把父亲到 u 的边权放到 u 的位置：

```cpp
edgeValue[tin[u]] = weight(parent[u], u);
```

这样，u 子树中的边权可以按区间统计，但 u 与父亲之间的边是否包含在查询中，要根据题目定义确认。路径问题尤其容易出现端点多算或少算，写代码前先手算一条两节点路径。

## 递归过深的替代写法

链状树的 DFS 深度可能达到 n。n 较大时，可以先用显式栈完成进入和离开事件：

```cpp
void iterativeDfs(int root) {
    vector<pair<int, int>> st;
    st.push_back({root, 0});

    while (!st.empty()) {
        auto& [u, state] = st.back();
        if (state == 0) {
            tin[u] = ++timer;
            order.push_back(u);
            state = 1;
        }

        if (state <= (int)g[u].size()) {
            int v = g[u][state - 1];
            state++;
            if (v == (st.size() >= 2 ? st[st.size() - 2].first : 0)) continue;
            st.push_back({v, 0});
        } else {
            tout[u] = timer;
            st.pop_back();
        }
    }
}
```

如果只需要父节点、深度和子树大小，也可以使用 BFS 得到父子顺序，再倒序处理。具体写法见 4.5。

## 例题

### 例 1，子树和查询

给定一棵根为 1 的树和每个节点的权值，询问多个节点的子树和。先 DFS 得到 `tin` 与 `tout`，再做前缀和。预处理 O(n)，每次查询 O(1)。

### 例 2，单点修改与子树查询

如果节点权值会变化，使用 4.8 的树状数组：修改 `tin[u]`，查询 `[tin[u], tout[u]]`。预处理 O(n log n)，每次修改和查询都是 O(log n)。

### 例 3，子树修改与子树查询

使用 4.9 的带懒标记线段树，对 `[tin[u], tout[u]]` 做区间加和区间查询。树的部分只负责把子树变成区间，区间数据结构负责维护统计量。

## 常见坑

- 只记录进入时间，却没有记录子树结束位置，无法得到完整区间。
- `tout[u]` 记录成离开时间戳后，又把它当作 `order` 的最后下标使用，导致区间多出一位。
- DFS 序依赖根节点。换根后，原来的子树区间通常不再表示同一批节点。
- 边权没有说明归属节点，路径和子树查询会出现端点重复计算。
- 无向树 DFS 忘记跳过父节点，程序会沿边来回走。
- 递归深度等于树高，链状数据要考虑 BFS 倒序或显式栈。

## 练习

**入门**

- [洛谷 P3374 树状数组 1](https://www.luogu.com.cn/problem/P3374)：先把单点与前缀查询写熟。
- [LeetCode 307 区域和检索 - 数组可修改](https://leetcode.cn/problems/range-sum-query-mutable/)：数组版本的单点修改和区间查询。
- [LeetCode 590 N 叉树的后序遍历](https://leetcode.cn/problems/n-ary-tree-postorder-traversal/)：练习树的后序顺序。

**进阶**

- [洛谷 P3320 [SDOI2015] 寻宝游戏](https://www.luogu.com.cn/problem/P3320)：DFS 序、欧拉序和树上距离的综合使用。
- [Codeforces 877E Danil and a Part-time Job](https://codeforces.com/problemset/problem/877/E)：子树区间加、区间翻转和区间求和。
- [AtCoder ABC202 E Count Descendants](https://atcoder.jp/contests/abc202/tasks/abc202_e)：按深度限制统计子树节点。

**挑战**

- [洛谷 P4211 [LNOI2014] LCA](https://www.luogu.com.cn/problem/P4211)：DFS 序与 LCA、树状数组的综合题。
- [Codeforces 570D Tree Requests](https://codeforces.com/problemset/problem/570/D)：DFS 序、深度分组和子树回文判断。

下一篇：4.7 LCA：倍增法。
