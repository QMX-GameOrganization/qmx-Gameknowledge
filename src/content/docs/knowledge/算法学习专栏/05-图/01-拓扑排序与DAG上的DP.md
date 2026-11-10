---
title: "5.1 拓扑排序与 DAG 上的 DP"
description: "先学图的两种存储方式,再用 Kahn 算法做拓扑排序、判断有环,最后在有向无环图上做最长路和路径计数。"
sidebar:
  order: 501
---

> 适用版本:C++17。需要会用 `vector` 和 `queue`,并理解 BFS 的队列写法(3.2 篇)。

## 本章学习建议

图是整个专栏里应用最广的一章,建议按下面的顺序走:

- **先学基础部分**:5.1 到 5.4 覆盖拓扑排序、最短路、最小生成树、二分图染色,这四类题占图论题的大半。每篇的例题都自己默写一遍,再做入门档练习。
- **最短路(5.2)是重点**。先理解"松弛"这个动作,再看三种算法只是松弛的顺序不同。Dijkstra 和 Kruskal 要练到不看资料能写出来。
- **⭐进阶篇(5.5 以后)互相独立**。SPFA 和差分约束(5.5、5.6)学完最短路就可以看;强连通分量、网络流等偏竞赛,遇到题目再回头补。
- 做题时先画图。画出点、边和每一步的状态,比直接写代码出错更少。

## 要点

- 图的存储有两种常用写法:`vector` 邻接表和链式前向星。多数题用 `vector` 就够了。
- 拓扑序是把有向图的点排成一列,使每条边都从前指向后。只有有向无环图(DAG)才有拓扑序。
- Kahn 算法反复取出入度为 0 的点,时间 O(n + m)。取出的点数不足 n,说明图里有环。
- 在 DAG 上做 DP 时,拓扑序就是一个合法的计算顺序:处理到某个点时,它的所有前驱已经算完。
- 最长路、路径计数、可达性这类问题,都可以在拓扑序上一遍扫完。

## 先把图存下来

图由点和边组成。存储方式决定了"遍历一个点的所有出边"有多快,这是图算法里最常做的操作。

**邻接矩阵**用 `w[u][v]` 记录边权,查询一条边 O(1),但占 O(n²) 空间,遍历出边要扫整行。只有 n 在两千以内的稠密图适合用它(比如 5.2 的 Floyd)。

**邻接表**对每个点只存它的出边。用 `vector` 写最简单:

```cpp
vector<vector<pair<int, int>>> g(n + 1);   // g[u] 存 (v, w)
g[u].push_back({v, w});                    // 有向边 u -> v,权 w
// 无向图:再加一条 g[v].push_back({u, w});
```

**链式前向星**是用数组模拟链表的邻接表。`head[u]` 指向 u 最近加入的一条出边,`nxt[e]` 指向同一个起点的上一条边。它不需要动态分配内存,而且每条边有固定编号,后面写网络流时可以用 `e ^ 1` 找反向边。

![同一张图的邻接表和链式前向星,以及前向星如何沿 nxt 遍历 1 的出边](/qmx-Gameknowledge/assets/algo/c5-01-adj-storage.svg)

下面的程序同时用两种方式存同一张图,并遍历每个点的出边:

```cpp
#include <bits/stdc++.h>
using namespace std;

const int N = 100005, M = 200005;
// 链式前向星:head[u] 是 u 的最近一条出边的编号,nxt[e] 是同一起点的上一条边
int head[N], nxt[M], to[M], wt[M], cnt;

void add(int u, int v, int w) {
    to[++cnt] = v;       // 边编号从 1 开始,0 表示"没有边"
    wt[cnt] = w;
    nxt[cnt] = head[u];  // 头插法
    head[u] = cnt;
}

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<pair<int, int>>> g(n + 1);  // 邻接表:g[u] 存 (v, w)
    for (int i = 0; i < m; i++) {
        int u, v, w;
        cin >> u >> v >> w;
        g[u].push_back({v, w});
        add(u, v, w);
    }
    for (int u = 1; u <= n; u++) {
        cout << u << " 邻接表:";
        for (auto [v, w] : g[u]) cout << " ->" << v << "(" << w << ")";
        cout << "\n" << u << " 前向星:";
        for (int e = head[u]; e; e = nxt[e]) cout << " ->" << to[e] << "(" << wt[e] << ")";
        cout << "\n";
    }
    return 0;
}
```

输入:

```text
3 4
1 2 5
1 3 7
1 2 1
3 1 2
```

输出:

```text
1 邻接表: ->2(5) ->3(7) ->2(1)
1 前向星: ->2(1) ->3(7) ->2(5)
2 邻接表:
2 前向星:
3 邻接表: ->1(2)
3 前向星: ->1(2)
```

可以看到前向星用头插法,同一个点的出边顺序和输入顺序相反。这通常不影响结果,但要输出路径或字典序时需要留意。本专栏后面的代码默认用 `vector` 邻接表;需要给边编号的算法(例如网络流的反向边)再改用前向星。

## 拓扑序

给定有向图,**拓扑序**是把所有点排成一列的方式,使得对每条边 `u -> v`,u 都排在 v 前面。可以把边理解成"u 必须先于 v 完成"的依赖关系,拓扑序就是一种可行的执行顺序。

- 只有**有向无环图**(DAG)存在拓扑序。如果有环,环上的点互相等待,无法排出先后。
- 拓扑序通常不唯一。上图的 DAG 里,点 2 和点 3 谁先都可以。
- 自环(`u -> u`)也算环。

## Kahn 算法

思路很直接:**入度为 0 的点没有任何前置条件,可以立刻排在最前面。** 把它取出来,并把它发出的边删掉,后继点的入度就少了 1。如果某个后继的入度变成 0,它也可以排了。重复这个过程。

![Kahn 算法每一步的入度数组和队列](/qmx-Gameknowledge/assets/algo/c5-01-topo-steps.svg)

为什么正确:每次取出的点,入度为 0,意味着所有指向它的边的起点都已经取出,依赖都满足了。为什么能判环:环上的点,每个点都有一个指向它的环上前驱,入度不会降到 0,所以永远不会入队。最后取出的点数小于 n,一定是有环。

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> g(n + 1);
    vector<int> indeg(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        indeg[v]++;
    }
    queue<int> q;
    for (int i = 1; i <= n; i++)
        if (indeg[i] == 0) q.push(i);  // 入度为 0 的点先入队
    vector<int> order;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        order.push_back(u);
        for (int v : g[u])
            if (--indeg[v] == 0) q.push(v);  // 删掉 u 的出边,v 的入度变 0 就可以排了
    }
    if ((int)order.size() < n) {
        cout << "有环,不存在拓扑序\n";
    } else {
        for (int x : order) cout << x << " ";
        cout << "\n";
    }
    return 0;
}
```

输入图就是上面的 DAG:

```text
6 7
1 2
1 3
2 4
3 4
3 5
4 6
5 6
```

输出:`1 2 3 4 5 6`。如果再加一条边 `6 1`(把 m 改成 8),图里出现环 1→3→4→6→1,程序会输出"有环,不存在拓扑序"。

**复杂度**:每个点入队一次,每条边被删一次,时间 O(n + m),空间 O(n + m)。

**重边**不用特殊处理:加边时入度加 1,删边时也减 1,次数一致。

**字典序最小的拓扑序**:把 `queue` 换成小根堆 `priority_queue<int, vector<int>, greater<int>>`,每次取编号最小的入度为 0 的点,复杂度变为 O(n log n + m)。

## DAG 上的 DP

很多图上的最优化问题在一般图里很难(比如最长路),但在 DAG 上很简单。原因是 DP 需要一个**没有循环依赖的计算顺序**,拓扑序正好提供了这个顺序。

以"边权为正的最长路"为例。设 `dp[v]` 是以 v 结尾的最长路径长度:

```text
dp[v] = max(0, 对每条边 u -> v 取 dp[u] + w)
```

按拓扑序处理每个点 u,用 `dp[u]` 去更新它的后继。因为 u 的所有前驱都在它前面,轮到 u 时 `dp[u]` 已经是最终值。

![DAG 上按拓扑序递推最长路,绿色粗线是最长路径](/qmx-Gameknowledge/assets/algo/c5-01-dag-dp.svg)

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<pair<int, int>>> g(n + 1);
    vector<int> indeg(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int u, v, w;
        cin >> u >> v >> w;
        g[u].push_back({v, w});
        indeg[v]++;
    }
    vector<int> dp(n + 1, 0);  // dp[v]:以 v 结尾的最长路径长度(起点任意)
    queue<int> q;
    for (int i = 1; i <= n; i++)
        if (indeg[i] == 0) q.push(i);
    int done = 0;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        done++;
        for (auto [v, w] : g[u]) {
            dp[v] = max(dp[v], dp[u] + w);  // u 已经定型,可以用它更新后继
            if (--indeg[v] == 0) q.push(v);
        }
    }
    if (done < n) {
        cout << "有环\n";
        return 0;
    }
    for (int i = 1; i <= n; i++) cout << dp[i] << " ";
    cout << "\n最长路径 = " << *max_element(dp.begin() + 1, dp.end()) << "\n";
    return 0;
}
```

输入(边权依次是 3、2、4、6、3、2、4):

```text
6 7
1 2 3
1 3 2
2 4 4
3 4 6
3 5 3
4 6 2
5 6 4
```

输出:

```text
0 3 2 8 5 10 
最长路径 = 10
```

这个程序里 `dp` 初值全是 0,表示路径可以从任意点开始。如果规定必须从点 1 出发,应把其他点初值设为一个很小的负数,只让 `dp[1] = 0`,并且在更新前跳过 `dp[u]` 为负无穷的点。

把 `max` 换成 `min` 就是 DAG 上的最短路,不需要 Dijkstra,也允许负边权。

## 例题

### 例 1:判断能否完成所有课程

n 门课,有若干条"先修 u 才能修 v"的关系,问能否全部修完。这就是判断有向图有没有环,直接使用上面的 Kahn 程序:`order.size() == n` 就能修完。(LeetCode 207;要求给出一种顺序则是 LeetCode 210。)

### 例 2:路径计数

DAG 上求从点 1 到点 n 有多少条不同的路径,答案对 10^9 + 7 取模。设 `f[v]` 为从 1 到 v 的路径数,`f[1] = 1`,每条边 `u -> v` 让 `f[v] += f[u]`。

```cpp
#include <bits/stdc++.h>
using namespace std;

const int MOD = 1e9 + 7;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> g(n + 1);
    vector<int> indeg(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        indeg[v]++;
    }
    vector<long long> f(n + 1, 0);  // f[v]:从 1 到 v 的路径条数
    f[1] = 1;
    queue<int> q;
    for (int i = 1; i <= n; i++)
        if (indeg[i] == 0) q.push(i);
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int v : g[u]) {
            f[v] = (f[v] + f[u]) % MOD;
            if (--indeg[v] == 0) q.push(v);
        }
    }
    cout << f[n] << "\n";
    return 0;
}
```

对上面的 DAG(只读边,不读权),输出 `3`:路径是 1-2-4-6、1-3-4-6、1-3-5-6。

注意:`f[1] = 1` 的前提是点 1 就是起点。如果图里还有别的入度为 0 的点,它们的 `f` 保持 0,不会产生贡献,这正是题目要的"从 1 出发"。

### 例 3:找到最终的安全状态

定义:从某个点出发的每一条路径都会在有限步内到达终点(出度为 0 的点),这个点就是安全点。求所有安全点。

思路是把图**反过来**做拓扑排序。终点出度为 0,显然安全。一个点的所有后继都安全,它才安全,也就是它的"出度"在后继被确认安全时逐个减 1。

```cpp
#include <bits/stdc++.h>
using namespace std;

// 安全点:从它出发的每条路径都会走到终点(出度为 0 的点)。
int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> rg(n + 1);  // 反向图
    vector<int> outdeg(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        rg[v].push_back(u);
        outdeg[u]++;
    }
    queue<int> q;
    for (int i = 1; i <= n; i++)
        if (outdeg[i] == 0) q.push(i);
    vector<bool> safe(n + 1, false);
    while (!q.empty()) {
        int v = q.front();
        q.pop();
        safe[v] = true;
        for (int u : rg[v])
            if (--outdeg[u] == 0) q.push(u);  // u 的所有后继都安全了,u 也安全
    }
    for (int i = 1; i <= n; i++)
        if (safe[i]) cout << i << " ";
    cout << "\n";
    return 0;
}
```

输入:

```text
7 7
1 2
2 3
3 4
4 5
5 3
6 7
2 6
```

输出:`6 7`。点 3、4、5 在环里,点 2 能走进这个环,点 1 能走到点 2,所以都不安全。(LeetCode 802。)

## 常见坑

- 计入度时,边 `u -> v` 加到 `indeg[v]`,而不是 `indeg[u]`。方向写反,所有结果都错。
- 判环用 `order.size() < n`,注意 `size()` 是无符号数,和 `int` 比较要先转型,不然会有编译警告。
- 图可能不连通。Kahn 要把**所有**入度为 0 的点一起入队,而不是只放点 1。
- DAG DP 的初值要想清楚:路径起点任意用 0,起点固定用负无穷加起点为 0。
- 边权和路径数可能超过 `int`,最长路用 `long long`,计数按题意取模。
- 图的规模较大时,`vector<vector<>>` 每次测试重建要清空,多组数据别漏掉。

## 练习

**入门**

- LeetCode 207 课程表、LeetCode 210 课程表 II
- 洛谷 B3644 【模板】拓扑排序 / 家谱树
- 洛谷 P1113 杂务(DAG 最长路)

**进阶**

- 洛谷 P1137 旅行计划(拓扑序上的最长路)
- 洛谷 P4017 最大食物链计数(路径计数)
- LeetCode 802 找到最终的安全状态

**挑战**

- 洛谷 P3243 [HNOI2015] 菜肴制作(反图拓扑加大根堆,理解"字典序最小"的反向处理)
- LeetCode 1857 有向图中最大颜色值(拓扑序上做 26 个颜色的 DP)

下一篇:5.2 最短路。
