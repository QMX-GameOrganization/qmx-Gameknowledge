---
title: "3.5 ⭐0-1 BFS 与双向 BFS"
description: "边权只有 0 和 1 时用双端队列做最短路；起点终点都已知时用双向 BFS 把搜索量开方。"
sidebar:
  order: 305
  badge:
    text: 进阶
    variant: caution
---

> 适用版本：C++17。前置知识：3.2 BFS，了解 `deque`。什么时候需要学：网格题里“走某些格子要付出 1 的代价，走另一些免费”；或者状态空间很大、起点和终点都明确，普通 BFS 超时、爆内存。

## 要点

- 0-1 BFS：边权只有 0 和 1 的最短路，用双端队列 `deque`，权 0 的邻居插队头，权 1 的邻居插队尾，复杂度 O(V + E)，比 Dijkstra 少一个 log。
- 双向 BFS：同时从起点和终点各搜一边，在中间相遇。状态数随深度指数增长，把深度减半，搜索量从 b^d 降到约 2·b^(d/2)。
- 双向 BFS 要求**能从终点反向走**；若状态转移不可逆，不能用。

## 0-1 BFS

普通 BFS 保证“队列中的距离单调不降”，所以第一次到达就是最短。边权出现 0 以后，这个性质被破坏：走 0 权边的邻居距离和当前点相同，应当和当前点同一层处理。

解决办法是把队列换成 `deque`：

- 代价为 0：邻居和当前点同一层，放到**队头**，下一个就处理它。
- 代价为 1：邻居在下一层，放到**队尾**。

这样队列里始终只有距离 d 和 d + 1 两种值，并且从队头到队尾单调不降，和普通 BFS 的不变式一致。

![0-1 BFS 的双端队列](/qmx-Gameknowledge/assets/algo/c3-01bfs-deque.svg)

一个点的距离可能先被设成 d + 1（权 1 的边），后来又被改成 d（权 0 的边），所以松弛时要判断 `dist[x][y] + w < dist[nx][ny]`，满足才更新并入队。每个点最多更新两次，总复杂度 O(V + E)。

### 例题：到达角落需要移除的障碍物最少数目

网格里 `0` 是空格，`1` 是障碍。走进空格免费，走进障碍需要移除它，代价 1。求从左上角到右下角最少移除几个障碍（LeetCode 2290）。

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    // LeetCode 2290：从左上角走到右下角，经过障碍格(1)需要付出 1 的代价，空格(0)代价为 0
    vector<vector<int>> a = {
        {0, 1, 1},
        {1, 1, 0},
        {1, 1, 0},
    };
    int R = a.size(), C = a[0].size();
    const int dx[] = {1, -1, 0, 0}, dy[] = {0, 0, 1, -1};
    const int INF = 1e9;

    vector<vector<int>> dist(R, vector<int>(C, INF));
    deque<pair<int, int>> dq;
    dist[0][0] = 0;
    dq.push_back({0, 0});
    while (!dq.empty()) {
        auto [x, y] = dq.front(); dq.pop_front();
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx < 0 || nx >= R || ny < 0 || ny >= C) continue;
            int w = a[nx][ny];                          // 走进 (nx,ny) 的代价：0 或 1
            if (dist[x][y] + w < dist[nx][ny]) {        // 能松弛才更新（同一格可能被入队多次）
                dist[nx][ny] = dist[x][y] + w;
                if (w == 0) dq.push_front({nx, ny});    // 代价 0：和当前点同一层，插到队头
                else dq.push_back({nx, ny});            // 代价 1：下一层，插到队尾
            }
        }
    }
    cout << "最少需要清除的障碍数: " << dist[R - 1][C - 1] << '\n';
}
```

```text
最少需要清除的障碍数: 2
```

例子里一条最优路径是 `(0,0) → (0,1) → (0,2) → (1,2) → (2,2)`，经过两个障碍，答案 2。

## 双向 BFS

普通 BFS 从起点出发，搜到深度 d 才碰到终点，需要访问约 b^d 个状态（b 是每个状态的后继个数）。双向 BFS 同时从起点和终点各搜 d/2 层，两边在中间碰头，各访问约 b^(d/2) 个状态，合计约 2·b^(d/2)。

![单向 BFS 是一个半径为 d 的大圆，双向 BFS 是两个半径 d/2 的小圆](/qmx-Gameknowledge/assets/algo/c3-bidir.svg)

实现要点：

1. 两侧各自维护一份距离表（`da`、`db`）和一层的边界（`qa`、`qb`）。
2. 每次扩展**边界较小的一侧**，并且扩展完**整整一层**。
3. 扩展时，如果某个新状态在另一侧的距离表里已经有了，就说明两边相遇，候选答案为 `me[s] + 1 + other[t]`。
4. 一层处理完之后，如果这一层发现过相遇，取其中的最小值返回；整层处理完再返回，是为了保证答案是最短的。

### 例题：八数码

3 × 3 棋盘上有 1 到 8 和一个空格，每步把空格和相邻的数字交换，求从初始局面到 `123456780` 的最少步数。下面的初始局面 `867254301` 是 31 步的最难局面之一。

```cpp
#include <bits/stdc++.h>
using namespace std;

// 八数码：状态是 9 个字符的字符串，'0' 表示空格；每步把空格和相邻格交换
vector<string> neighbors(const string& s) {
    vector<string> res;
    int z = s.find('0'), x = z / 3, y = z % 3;
    const int dx[] = {1, -1, 0, 0}, dy[] = {0, 0, 1, -1};
    for (int d = 0; d < 4; d++) {
        int nx = x + dx[d], ny = y + dy[d];
        if (nx < 0 || nx >= 3 || ny < 0 || ny >= 3) continue;
        string t = s;
        swap(t[z], t[nx * 3 + ny]);
        res.push_back(t);
    }
    return res;
}

// 普通 BFS，返回 {步数, 出队的状态数}
pair<int, int> bfs(const string& from, const string& to) {
    unordered_map<string, int> dist;
    queue<string> q;
    dist[from] = 0; q.push(from);
    int popped = 0;
    while (!q.empty()) {
        string s = q.front(); q.pop(); popped++;
        if (s == to) return {dist[s], popped};
        for (auto& t : neighbors(s))
            if (!dist.count(t)) { dist[t] = dist[s] + 1; q.push(t); }
    }
    return {-1, popped};
}

// 双向 BFS：每次把"较小的一侧"扩展一整层；两侧碰面时，步数 = 两侧距离之和
pair<int, int> bidirectional(const string& from, const string& to) {
    if (from == to) return {0, 0};
    unordered_map<string, int> da, db;
    vector<string> qa = {from}, qb = {to};
    da[from] = 0; db[to] = 0;
    int popped = 0;
    while (!qa.empty() && !qb.empty()) {
        bool useA = qa.size() <= qb.size();
        auto& cur = useA ? qa : qb;
        auto& me = useA ? da : db;
        auto& other = useA ? db : da;
        vector<string> next;
        int best = -1;
        for (auto& s : cur) {
            popped++;
            for (auto& t : neighbors(s)) {
                auto it = other.find(t);
                if (it != other.end()) {                // 碰到对面已经到过的状态：相遇
                    int total = me[s] + 1 + it->second;
                    if (best == -1 || total < best) best = total;
                }
                if (!me.count(t)) { me[t] = me[s] + 1; next.push_back(t); }
            }
        }
        if (best != -1) return {best, popped};         // 整层扩展完才返回，保证是最短
        cur = next;
    }
    return {-1, popped};
}

int main() {
    string from = "867254301", to = "123456780";       // 这个初始局面是八数码里最难的之一，需要 31 步
    auto [d1, c1] = bfs(from, to);
    auto [d2, c2] = bidirectional(from, to);
    cout << "普通 BFS: 步数 " << d1 << "，出队 " << c1 << " 个状态\n";
    cout << "双向 BFS: 步数 " << d2 << "，出队 " << c2 << " 个状态\n";
}
```

```text
普通 BFS: 步数 31，出队 181440 个状态
双向 BFS: 步数 31，出队 12452 个状态
```

答案相同，都是 31 步，而双向 BFS 只处理了约 7% 的状态。我另外用 190 个随机的可解局面对比了两种写法的步数，全部一致。

## 适用与不适用

| 情况 | 能否用 |
| --- | --- |
| 边权只有 0 和 1 | 0-1 BFS |
| 边权是少数几种整数（如 0, 1, 2） | 可以拆边或用多层队列，但这时直接用 Dijkstra 更省心 |
| 起点、终点都明确，转移可逆 | 双向 BFS |
| 终点是一类状态（如“任意一个目标格”） | 双向 BFS 不方便，可以反向多源 BFS |
| 转移不可逆 | 双向 BFS 不能用 |

## 常见坑

- **0-1 BFS 把 0 权也放队尾**：就退化成普通 BFS，距离可能出错。
- **0-1 BFS 入队时不判断松弛**：直接 `if (!vis) ...` 的写法在有 0 权边时会得到偏大的距离。
- **双向 BFS 一发现相遇就返回**：此时当前层还没处理完，可能还有更短的。
- **双向 BFS 不挑较小的一侧扩展**：失去了开方的收益，甚至比单向更慢。
- **起点等于终点**：要单独处理，否则循环里不会相遇。

## 练习

**入门**

- LeetCode 752 打开转盘锁（先用普通 BFS，再改双向）
- LeetCode 127 单词接龙（双向 BFS 写法）

**进阶**

- LeetCode 2290 到达角落需要移除障碍物的最小数目
- LeetCode 1368 使网格图至少有一条有效路径的最小代价
- 洛谷 P1379 八数码难题

**挑战**

- LeetCode 126 单词接龙 II
- LeetCode 1263 推箱子
- 洛谷 P4667 Switch the Lamp On（0-1 BFS，题号待核实）

下一篇：3.6 ⭐A\* 与 IDA\*。
