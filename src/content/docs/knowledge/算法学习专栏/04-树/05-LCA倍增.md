---
title: "4.5 LCA：倍增法"
description: "最近公共祖先的定义，倍增表的构造，求第 k 个祖先和 LCA，以及树上两点距离。"
sidebar:
  order: 405
---

> 适用版本：C++17。前置知识：4.4 一般树（父亲、深度），二进制拆分。

## 要点

- 有根树中，u 和 v 的**最近公共祖先**（Lowest Common Ancestor，LCA）是同时是两者祖先的节点里深度最大的一个。节点本身也算自己的祖先。
- 逐步向上爬的暴力做法是 O(深度)，链状树上会超时。
- 倍增法预处理 `up[k][v]`，表示 v 的第 2^k 个祖先，预处理 O(n log n)，每次查询 O(log n)。
- 求 LCA 分两步：先把较深的点跳到同一深度，再让两点从大到小尝试一起上跳，只在跳完两点仍不相同时才真的跳。
- 有了 LCA，树上两点距离是 `dep[u] + dep[v] - 2 * dep[lca]`。

## 问题与暴力做法

树上有 q 次询问，每次给出 u 和 v，问 LCA。最直接的做法：先把较深的点往上爬到与另一点同一深度，然后两个点一起往上爬，直到相遇。每次询问最坏爬 O(n) 步。

倍增的想法来自二进制：往上爬 13 步可以拆成 8 + 4 + 1，只要事先知道“向上跳 1、2、4、8…步会到哪里”，任何步数都能用不超过 log n 次跳跃完成。

## 倍增表

![倍增表：up[k][v] 是 v 的第 2^k 个祖先，由 up[k-1] 两次跳跃得到](/qmx-Gameknowledge/assets/algo/c4-05-jump-table.svg)

定义 `up[k][v]` 为 v 向上走 2^k 步到达的节点，超过根就记为 0（节点编号从 1 开始，0 表示不存在）。递推关系：

`up[0][v] = v 的父亲`

`up[k][v] = up[k-1][ up[k-1][v] ]`

第二条的含义是：走 2^k 步，等于先走 2^(k-1) 步，再从那里走 2^(k-1) 步。图里 8 号节点：`up[1][8] = up[0][up[0][8]] = up[0][7] = 4`，`up[2][8] = up[1][up[1][8]] = up[1][4] = 1`。注意 `up[k][0]` 必须是 0，这样越过根之后继续跳仍然是“不存在”。

k 的上限取到 2^k 大于最大深度即可，n ≤ 10^5 时 `LOG = 17` 足够（2^17 = 131072）。

## 求第 k 个祖先

把 k 写成二进制，哪一位是 1 就用对应的 `up[b]` 跳一次：

```cpp
// 片段：v 的第 k 个祖先，不存在返回 0
int kthAncestor(int v, int k) {
    for (int b = 0; b <= LOG; b++)
        if (k >> b & 1) v = up[b][v];
    return v;
}
```

## 求 LCA

![倍增求 LCA(8, 6)：先把 8 跳到与 6 同深度，再从大到小同时上跳，最后停在 LCA 的两个孩子上](/qmx-Gameknowledge/assets/algo/c4-05-lca-steps.svg)

1. 如果 `dep[u] < dep[v]` 就交换，保证 u 更深。用 `kthAncestor` 把 u 上跳 `dep[u] - dep[v]` 步。此时如果 `u == v`，v 本身就是 LCA。
2. 否则，k 从大到小枚举：如果 `up[k][u] != up[k][v]`，说明跳 2^k 步之后两点还没汇合（还在 LCA 下面），就让两点都跳；相同则不跳，因为可能已经跳到 LCA 或更高。
3. 循环结束后，u 和 v 是 LCA 的两个不同孩子，LCA 就是 `up[0][u]`。

**为什么第 2 步这样跳是对的？** 设 u、v 到 LCA 的距离都是 d。从高位到低位尝试，相当于在构造 d - 1 的二进制：能跳的位（跳完仍不相等）都跳，最终总共跳了 d - 1 步，恰好停在 LCA 的孩子上。如果某一步跳完两点相等，说明这一步跳过头了，那一位必须是 0。超过根时 `up` 都是 0，也相等，同样不会跳。

```cpp
#include <bits/stdc++.h>
using namespace std;

const int N = 100005, LOG = 17;
vector<int> g[N];
int up[LOG + 1][N], dep[N], n;

void build(int root) {                 // 用 BFS 建父亲和深度，避免递归过深
    vector<int> order = {root};
    up[0][root] = 0; dep[root] = 0;
    for (size_t i = 0; i < order.size(); i++) {
        int u = order[i];
        for (int v : g[u])
            if (v != up[0][u]) { up[0][v] = u; dep[v] = dep[u] + 1; order.push_back(v); }
    }
    for (int k = 1; k <= LOG; k++)
        for (int v = 1; v <= n; v++)
            up[k][v] = up[k - 1][up[k - 1][v]];
}

int kthAncestor(int v, int k) {
    for (int b = 0; b <= LOG; b++)
        if (k >> b & 1) v = up[b][v];
    return v;
}

int lca(int u, int v) {
    if (dep[u] < dep[v]) swap(u, v);
    u = kthAncestor(u, dep[u] - dep[v]);       // 对齐深度
    if (u == v) return u;
    for (int k = LOG; k >= 0; k--)
        if (up[k][u] != up[k][v]) { u = up[k][u]; v = up[k][v]; }
    return up[0][u];
}

int dist(int u, int v) { return dep[u] + dep[v] - 2 * dep[lca(u, v)]; }

int main() {
    n = 8;
    int e[][2] = {{1, 2}, {1, 3}, {2, 4}, {2, 5}, {3, 6}, {4, 7}, {7, 8}};
    for (auto& x : e) { g[x[0]].push_back(x[1]); g[x[1]].push_back(x[0]); }
    build(1);
    for (int k = 0; k <= 2; k++) {                 // 打印倍增表，和上面的图对照
        for (int v = 1; v <= n; v++) printf("%d ", up[k][v]);
        puts("");
    }
    printf("%d %d %d %d\n", lca(8, 6), lca(8, 5), lca(7, 4), lca(5, 6));
    printf("%d\n", dist(8, 6));
    printf("%d %d\n", kthAncestor(8, 2), kthAncestor(8, 5));
}
```

```output
0 1 1 2 2 3 4 7
0 0 0 1 1 1 2 4
0 0 0 0 0 0 0 1
1 2 4 1
6
4 0
```

预处理 O(n log n)，空间 O(n log n)，约 18 × 10^5 个 int，不到 8 MB。每次 `lca` 或 `kthAncestor` 是 O(log n)。

**其他求 LCA 的办法**：离线的 Tarjan 算法（配合并查集）每次询问接近 O(1)；欧拉序加 ST 表（2.5）可以做到 O(1) 查询；树链剖分（4.13）常数小，还能同时处理路径上的修改。倍增最容易写对，也能顺便得到第 k 个祖先，所以是首选。

## 例题

### 例 1：二叉树的最近公共祖先（LeetCode 236）

题目链接：[LeetCode 236 二叉树的最近公共祖先](https://leetcode.cn/problems/lowest-common-ancestor-of-a-binary-tree/)。只有一次询问时，不必建表，一次递归就够。思路是自底向上汇报：当前子树里找到了 p 或 q 就把它返回；如果左右子树各返回了一个非空结果，说明 p 和 q 分居两侧，当前节点就是 LCA；否则把非空的那个继续向上传。

```cpp
#include <bits/stdc++.h>
using namespace std;

struct Node {
    int val;
    Node *l = nullptr, *r = nullptr;
    explicit Node(int v) : val(v) {}
};

Node* lca(Node* t, Node* p, Node* q) {
    if (!t || t == p || t == q) return t;      // 空树或碰到目标，直接返回
    Node* a = lca(t->l, p, q);
    Node* b = lca(t->r, p, q);
    if (a && b) return t;                      // p、q 分居左右，t 就是 LCA
    return a ? a : b;                          // 都在同一侧，继续向上传
}

int main() {
    vector<Node*> nd(7);
    for (int i = 1; i <= 6; i++) nd[i] = new Node(i);
    nd[1]->l = nd[2]; nd[1]->r = nd[3];
    nd[2]->l = nd[4]; nd[2]->r = nd[5];
    nd[3]->l = nd[6];
    printf("%d %d %d\n", lca(nd[1], nd[4], nd[5])->val,
                         lca(nd[1], nd[4], nd[6])->val,
                         lca(nd[1], nd[2], nd[4])->val);
}
```

```output
2 1 2
```

每次询问 O(n)，q 次询问总共 O(nq)。询问多的时候用前面的倍增。

### 例 2：树节点的第 K 个祖先（LeetCode 1483）

题目链接：[LeetCode 1483 树节点的第 K 个祖先](https://leetcode.cn/problems/kth-ancestor-of-a-tree-node/)。题目给出 `parent` 数组（`parent[0] = -1`，节点从 0 编号），反复询问某节点的第 k 个祖先。这正是倍增表的直接应用。这里用 `-1` 表示不存在，并且因为父亲的编号不一定小于孩子，所以先按 k 分层，再对所有点填表：

```cpp
#include <bits/stdc++.h>
using namespace std;

struct TreeAncestor {
    static const int LOG = 16;                    // 题目保证 k <= 5 * 10^4 < 2^16
    vector<array<int, LOG>> up;

    TreeAncestor(int n, const vector<int>& parent) : up(n) {
        for (int v = 0; v < n; v++) up[v][0] = parent[v];
        for (int k = 1; k < LOG; k++)
            for (int v = 0; v < n; v++) {
                int mid = up[v][k - 1];
                up[v][k] = mid < 0 ? -1 : up[mid][k - 1];
            }
    }
    int getKthAncestor(int v, int k) {
        for (int b = 0; b < LOG && v >= 0; b++)
            if (k >> b & 1) v = up[v][b];
        return v;                                 // 中途变成 -1 就一直是 -1
    }
};

int main() {
    TreeAncestor ta(7, {-1, 0, 0, 1, 2, 2, 2});
    printf("%d %d %d\n", ta.getKthAncestor(3, 1), ta.getKthAncestor(5, 2), ta.getKthAncestor(6, 3));
}
```

```output
1 0 -1
```

### 例 3：判断点是否在路径上

用距离公式就能判断：点 w 在 u 到 v 的路径上，当且仅当 `dist(u, w) + dist(w, v) == dist(u, v)`。更一般地，要在树上求若干点的某种“汇合点”，常常转化为几个 LCA 与距离的组合，洛谷 P4281 就是这类题。

## 常见坑

- `LOG` 开小了：2^LOG 必须大于最大深度。链状树、n = 10^5 时 `LOG` 至少是 17。
- 二维数组 `up[k][v]` 的第二维是节点，初始化 `up[k][0] = 0` 依赖全局数组默认值，多组数据要清空。
- 第二阶段的判断是 `up[k][u] != up[k][v]`，不是比较深度。越过根的两个祖先都是 0，相等，不会跳。
- 忘记先交换使 u 更深，或者对齐深度后没有判断 `u == v` 就直接进入循环，会得到 LCA 的父亲。
- 递归建表在链状树上会爆栈，用 BFS 序更稳。

## 练习

**入门**

- [LeetCode 236 二叉树的最近公共祖先](https://leetcode.cn/problems/lowest-common-ancestor-of-a-binary-tree/)（中等）。
- [LeetCode 235 二叉搜索树的最近公共祖先](https://leetcode.cn/problems/lowest-common-ancestor-of-a-binary-search-tree/)（中等）：利用 BST 的大小关系，不需要建表。

**进阶**

- 洛谷 P3379 【模板】最近公共祖先（LCA）：本篇模板。
- [LeetCode 1483 树节点的第 K 个祖先](https://leetcode.cn/problems/kth-ancestor-of-a-tree-node/)（困难）：倍增表的直接应用。
- 洛谷 P4281 [AHOI2008] 紧急集合 / 聚会：三个点的“汇合点”，用 LCA 求距离。

**挑战**

- 洛谷 P1967 [NOIP2013 提高组] 货车运输：最大生成树（5.3）加 LCA 求路径最小值。
- 洛谷 P2680 [NOIP2015 提高组] 运输计划：二分答案加树上差分，LCA 是其中一环。

下一篇：4.6 树状数组。

