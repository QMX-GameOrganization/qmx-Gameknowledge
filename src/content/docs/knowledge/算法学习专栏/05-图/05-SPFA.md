---
title: "5.5 ⭐SPFA:队列优化的 Bellman-Ford"
description: "理解 SPFA 为什么比 Bellman-Ford 快,掌握用路径边数判负环的写法,并清楚它的最坏复杂度和适用场景。"
sidebar:
  order: 505
  badge:
    text: 进阶
    variant: caution
---

> 适用版本:C++17。前置:5.2 的 Bellman-Ford。**什么时候需要它**:图里有负边,Bellman-Ford 的 O(nm) 太慢,又不方便做别的转换时;或需要判断负环。没有负边时直接用 Dijkstra。

## 要点

- SPFA 是 Bellman-Ford 的队列优化:只有"距离刚被改小的点"的出边,才有可能产生新的松弛,所以只让这些点进队。
- 一个点可以多次进出队列,用 `inq` 数组避免它同时在队列里重复出现。
- 判负环:记录每个点当前最短路径包含的边数 `len`,如果 `len[v] >= n`,说明路径在绕圈。
- **最坏复杂度仍是 O(nm)**,存在专门构造的数据能把它卡到这个上界。边权非负时用 Dijkstra 更稳妥。

## 想法

Bellman-Ford 每一轮都把所有 m 条边松弛一遍,但其中大多数边的起点这一轮根本没变,松弛一次不会有结果,是白做的。

一条边 `u -> v` 要产生新的松弛,必须是 `dist[u]` 刚被改小。所以不需要扫所有边,只需要维护一个队列,里面是"距离刚变化、还没用它去松弛邻居"的点:

1. 起点入队,`dist[s] = 0`。
2. 取出队首 u,枚举 u 的出边 `u -> v`:如果 `dist[u] + w < dist[v]`,更新 `dist[v]`;如果 v 不在队列里,把 v 入队。
3. 队列空时结束。

![SPFA 在一张含负边的图上的队列变化,点 2、4、5 各入队两次](/qmx-Gameknowledge/assets/algo/c5-05-spfa-queue.svg)

看这张图里的执行过程:点 3 先把 `dist[2]` 从 5 改成 1,点 2 因此第二次入队,又把点 4 改小,点 4 再把点 5 改小。点 2、4、5 第一次拿到的都不是最终距离。

## 模板

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

const ll INF = LLONG_MAX / 4;

int main() {
    int n, m, s;
    cin >> n >> m >> s;
    vector<vector<pair<int, ll>>> g(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        ll w;
        cin >> u >> v >> w;
        g[u].push_back({v, w});
    }
    vector<ll> dist(n + 1, INF);
    vector<int> len(n + 1, 0);       // len[v]:当前最短路径包含的边数
    vector<bool> inq(n + 1, false);  // v 是否已经在队列里
    queue<int> q;
    dist[s] = 0;
    q.push(s);
    inq[s] = true;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        inq[u] = false;
        for (auto [v, w] : g[u]) {
            if (dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                len[v] = len[u] + 1;
                if (len[v] >= n) {  // 最短路径多于 n-1 条边,必然重复经过某个点,说明有负环
                    cout << "存在从 s 可达的负环\n";
                    return 0;
                }
                if (!inq[v]) {
                    q.push(v);
                    inq[v] = true;
                }
            }
        }
    }
    for (int i = 1; i <= n; i++) {
        if (dist[i] == INF) cout << "INF ";
        else cout << dist[i] << " ";
    }
    cout << "\n";
    return 0;
}
```

输入(图中的有向图,起点 1):

```text
5 6 1
1 2 5
1 3 2
3 2 -1
2 4 3
3 4 6
4 5 1
```

输出:`0 1 2 4 5`。

代码里的几个细节:

- `inq[v]` 表示 v 当前是否在队列里。已经在队列里的点再被更新时只改 `dist`,不重复入队。
- 距离比较用 `dist[u] + w < dist[v]`。起点以外的点初始为 INF,但 INF 点不会被取出(它们没进过队列),所以不用额外判断。

## 判负环

**负环**是权和为负的环。从起点可达的负环会让某些点的最短距离无限小。SPFA 里,这表现为队列永远不空。

怎么判?最短路径(无负环时)是简单路径,最多 n - 1 条边。给每个点记 `len[v]`:当前 `dist[v]` 对应的路径含有多少条边。每次成功松弛时 `len[v] = len[u] + 1`。如果某次 `len[v] >= n`,说明这条"最短路"包含至少 n 条边,必定重复经过某个点,而重复经过的这一圈让距离变小,所以那一圈是负环。

![环 2→3→4→2 的权和为 -1,第二次更新点 2 时 len[2] = 4 达到 n](/qmx-Gameknowledge/assets/algo/c5-05-neg-cycle.svg)

上面的模板已经包含了这个判断。用负环例子测试:

```text
4 4 1
1 2 1
2 3 -1
3 4 -1
4 2 1
```

输出:`存在从 s 可达的负环`。

另一种常见写法是统计每个点的入队次数,超过 n 次判负环。它也正确,但要等到入队次数累积到 n 才能发现,通常比边数法慢。

### 判断整张图有没有负环

上面只能发现**从 s 可达**的负环。要判断整张图,把"所有点距离为 0,且全部入队"作为初始状态,等价于接一个到所有点的超级源点:

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

// 判断整张图里有没有负环(不要求从某个点可达)
int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<pair<int, ll>>> g(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        ll w;
        cin >> u >> v >> w;
        g[u].push_back({v, w});
    }
    vector<ll> dist(n + 1, 0);       // 所有点的初始距离都是 0,相当于接了一个超级源点
    vector<int> len(n + 1, 0);
    vector<bool> inq(n + 1, true);   // 所有点一开始都在队列里
    queue<int> q;
    for (int i = 1; i <= n; i++) q.push(i);
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        inq[u] = false;
        for (auto [v, w] : g[u]) {
            if (dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                len[v] = len[u] + 1;
                if (len[v] >= n) {
                    cout << "有负环\n";
                    return 0;
                }
                if (!inq[v]) {
                    q.push(v);
                    inq[v] = true;
                }
            }
        }
    }
    cout << "无负环\n";
    return 0;
}
```

输入:

```text
4 4
1 2 1
2 3 -2
3 2 1
3 4 1
```

输出:`有负环`(环 2→3→2 权和为 -1)。

## 复杂度与适用

- **平均**:在随机图上,SPFA 通常很快,运行时间接近 O(m)。这是经验观察,没有普遍成立的严格结论。
- **最坏**:O(nm)。一些专门针对 SPFA 的构造数据(比如特定权值的网格图)会让点反复入队,使其和 Bellman-Ford 一样慢。
- 常见的优化(如 SLF,小的优先)只改善常数,不改变最坏情况。

怎么选:

| 情况 | 建议 |
| --- | --- |
| 边权非负 | Dijkstra,稳定 O(m log m) |
| 有负边,数据规模不大 | SPFA 或 Bellman-Ford |
| 需要判负环 | SPFA(边数法),或 Bellman-Ford 第 n 轮 |
| 需要在有负边的图上稳定地求全源最短路 | Johnson(先 Bellman-Ford 求势能,再对每个点跑 Dijkstra) |

在竞赛里,题面如果是"非负边权",用 SPFA 有被卡的风险,所以有 Dijkstra 可用时应优先用它。

## 例题

### 例 1:负环模板

洛谷 P3385【模板】负环:多组数据,判断从点 1 出发能否到达负环。注意这题的输入格式:权为非负的边是双向边,权为负的边是单向边(以题面为准),需要自己按这个规则建图,再用上面的判环程序。

### 例 2:整图负环

给定有向图,问是否存在负环(不限起点),用上面的 `t5_negall` 程序。

### 例 3:差分约束

差分约束的判无解和求解,都是在约束图上跑 SPFA,见 5.6。

## 常见坑

- 忘记 `inq`:同一个点在队列里重复很多份,队列长度爆炸。
- 判负环用 `len[v] >= n`,不是 `> n`。n 个点的简单路径最多 n - 1 条边。
- 只从 s 出发无法发现 s 到不了的负环。需要整图判断就用超级源点的写法。
- 用 `int` 存距离时,有负环的情况下距离可能一直变小溢出。先判负环,或者用 `long long`。
- 多组数据时,`dist`、`len`、`inq`、队列都要重置。
- 不要用 SPFA 当成"万能最短路",面对非负边权的大数据,Dijkstra 更安全。

## 练习

**入门**

- 洛谷 P3371 【模板】单源最短路径(弱化版),用 SPFA 做一遍
- 洛谷 P3385 【模板】负环

**进阶**

- 洛谷 P5960 【模板】差分约束(见 5.6)
- LeetCode 787 K 站中转内最便宜的航班(对比 5.2 的 Bellman-Ford)

**挑战**

- 洛谷 P4779 【模板】单源最短路径(标准版):这题常被用来说明 SPFA 可能超时,可以先用 SPFA 提交一次,再改用 Dijkstra 对比
- 洛谷 P5905 【模板】全源最短路(Johnson):用 SPFA 或 Bellman-Ford 求势能后,对每个点跑 Dijkstra

下一篇:5.6 ⭐差分约束。
