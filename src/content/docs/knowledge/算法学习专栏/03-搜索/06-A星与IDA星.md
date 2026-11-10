---
title: "3.6 ⭐A* 与 IDA*"
description: "用启发函数让搜索朝目标方向走：A* 的 f = g + h，启发函数的可采纳性，以及内存只用一条路径的 IDA*。"
sidebar:
  order: 306
  badge:
    text: 进阶
    variant: caution
---

> 适用版本：C++17。前置知识：3.2 BFS、优先队列（`priority_queue`）；了解 Dijkstra 更好（5.2）。什么时候需要学：状态空间很大、能估计“离目标还有多远”，比如八数码、十五数码、带障碍的网格寻路。

## 要点

- A\* 搜索用优先队列，每次取 **f = g + h** 最小的状态：g 是起点到当前状态已经花的代价，h（启发函数，heuristic）是当前状态到目标的**估计**代价。
- 只要 h **永远不高估**真实代价（称为可采纳，admissible），A\* 找到的就是最优解。h = 0 时 A\* 就是 Dijkstra。
- h 越接近真实代价，需要扩展的状态越少。
- IDA\*（iterative deepening A\*）= 迭代加深 + f 值剪枝，内存只需要一条路径，适合状态太多、A\* 的 `open` 表放不下的题。

## A\*：把 Dijkstra 的方向改向目标

Dijkstra 按 g 从小到大扩展，像水波一样向四面八方展开，不管目标在哪边。A\* 把排序依据换成 f = g + h：离起点近、并且（估计）离目标也近的状态优先。

要保证最优，h 要满足：

- **可采纳**：对每个状态，h(状态) ≤ 它到目标的真实最短代价。
- **一致性（consistency）**：对每条边 u → v，有 h(u) ≤ cost(u, v) + h(v)。一致的 h 一定是可采纳的，并且每个状态第一次出队时的 g 就是最优，可以像 Dijkstra 一样用 `dist` 数组做松弛。

网格上，每步代价 1、可以上下左右走时，**曼哈顿距离** `|x1 - x2| + |y1 - y2|` 满足一致性，是常用的 h。

### 例题：带墙的网格寻路

![同一张图，Dijkstra 与 A* 扩展的格子对比](/qmx-Gameknowledge/assets/algo/c3-astar.svg)

下面的代码里，把 `useH` 设为 `false` 时 h 恒为 0，等于 Dijkstra，方便对比。

```cpp
#include <bits/stdc++.h>
using namespace std;

int R, C;
vector<string> g;
const int dx[] = {1, -1, 0, 0}, dy[] = {0, 0, 1, -1};

// 返回 {最短步数, 出队(扩展)的格子数}；useH = false 时 h 恒为 0，退化成 Dijkstra
pair<int, int> search(pair<int, int> s, pair<int, int> t, bool useH) {
    auto h = [&](int x, int y) { return useH ? abs(x - t.first) + abs(y - t.second) : 0; };   // 曼哈顿距离
    vector<vector<int>> dist(R, vector<int>(C, INT_MAX));
    // 堆里存 {f, x, y}，f = g + h；f 小的先出
    priority_queue<tuple<int, int, int>, vector<tuple<int, int, int>>, greater<>> pq;
    dist[s.first][s.second] = 0;
    pq.push({h(s.first, s.second), s.first, s.second});
    int popped = 0;
    while (!pq.empty()) {
        auto [f, x, y] = pq.top(); pq.pop();
        if (f > dist[x][y] + h(x, y)) continue;         // 过期记录（后来找到了更短的 g）
        popped++;
        if (make_pair(x, y) == t) return {dist[x][y], popped};
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx < 0 || nx >= R || ny < 0 || ny >= C || g[nx][ny] == '#') continue;
            if (dist[x][y] + 1 < dist[nx][ny]) {
                dist[nx][ny] = dist[x][y] + 1;
                pq.push({dist[nx][ny] + h(nx, ny), nx, ny});
            }
        }
    }
    return {-1, popped};
}

int main() {
    g = {
        "..........",
        "..........",
        "....####..",
        "....#.....",
        "S...#....T",
        "....#.....",
        "....####..",
        "..........",
    };
    R = g.size(); C = g[0].size();
    pair<int, int> s, t;
    for (int i = 0; i < R; i++)
        for (int j = 0; j < C; j++) {
            if (g[i][j] == 'S') s = {i, j};
            if (g[i][j] == 'T') t = {i, j};
        }
    auto [d0, c0] = search(s, t, false);
    auto [d1, c1] = search(s, t, true);
    cout << "无启发(Dijkstra): 步数 " << d0 << "，扩展 " << c0 << " 个格子\n";
    cout << "A*(曼哈顿):       步数 " << d1 << "，扩展 " << c1 << " 个格子\n";
}
```

```text
无启发(Dijkstra): 步数 15，扩展 64 个格子
A*(曼哈顿):       步数 15，扩展 36 个格子
```

两种方式的最短步数都是 15，A\* 少扩展了约 44% 的格子（64 个对 36 个）。

代码里的 `if (f > dist[x][y] + h(x, y)) continue;` 是过期记录检查：同一个格子可能因为后来找到更短的 g 被重复放进堆，旧记录出队时直接丢掉。

## 八数码与启发函数

八数码的状态是 3 × 3 棋盘。常用的 h 是**每个数字到目标位置的曼哈顿距离之和**（不含空格）。每一步只能移动一个数字一格，h 最多减少 1，所以它不会高估，是可采纳的。

### 无解判断

不是所有局面都能还原。对 3 × 3 棋盘和目标 `123456780`：去掉空格后，把剩下的 8 个数字按顺序写成一行，数**逆序对**（前面的数比后面的数大）的个数，只有偶数才有解。不先判断，搜索会一直跑下去。

## IDA\*：迭代加深的 A\*

A\* 的缺点是要把所有见过的状态存在 `open` 表和距离表里，状态数多时内存不够。IDA\* 的做法：

1. 设一个上限 `limit`，初始为 h(起点)。
2. 做一次普通 DFS，遇到 f = g + h > `limit` 的状态就剪枝，同时记下被剪掉的状态里**最小的 f**。
3. 找到目标就结束，此时 `limit` 就是最少步数。否则把 `limit` 更新为上一步记下的最小 f，重新来一遍。

内存只有 DFS 的一条路径。代价是前几轮的工作会被后几轮重复，但每轮的节点数大致按指数增长，所以重复部分占比很小。

![起点 724506831 的 IDA* 逐轮放宽上限](/qmx-Gameknowledge/assets/algo/c3-idastar-rounds.svg)

在八数码里，每走一步 g 加 1，h 加或减 1，所以 f 只会不变或增加 2。上限因此是 14、16、18、20 这样跳着增加，不会出现奇数。

```cpp
#include <bits/stdc++.h>
using namespace std;

// 八数码的 IDA*：启发函数 = 各数字到目标位置的曼哈顿距离之和（不含空格），它永远不会高估
int board[9];
const int goalPos[9][2] = {{2, 2}, {0, 0}, {0, 1}, {0, 2}, {1, 0}, {1, 1}, {1, 2}, {2, 0}, {2, 1}};   // 数字 v 的目标行列
const int dx[] = {1, -1, 0, 0}, dy[] = {0, 0, 1, -1};
long long nodes;

int heuristic() {
    int h = 0;
    for (int i = 0; i < 9; i++)
        if (board[i]) h += abs(i / 3 - goalPos[board[i]][0]) + abs(i % 3 - goalPos[board[i]][1]);
    return h;
}

// g：已走步数；limit：本轮的深度上限；lastDir：上一步方向，避免立刻走回头路
// 返回 -1 表示找到；否则返回"超出上限的最小 f 值"，作为下一轮的上限
int dfs(int zero, int g, int limit, int lastDir) {
    nodes++;
    int h = heuristic();
    if (g + h > limit) return g + h;                    // f 超过上限：剪枝，并把 f 报告给上层
    if (h == 0) return -1;
    int nextLimit = INT_MAX;
    for (int d = 0; d < 4; d++) {
        if (lastDir != -1 && d == (lastDir ^ 1)) continue;      // 方向 0/1、2/3 互为反向
        int x = zero / 3 + dx[d], y = zero % 3 + dy[d];
        if (x < 0 || x >= 3 || y < 0 || y >= 3) continue;
        int nz = x * 3 + y;
        swap(board[zero], board[nz]);
        int r = dfs(nz, g + 1, limit, d);
        swap(board[zero], board[nz]);                   // 回溯
        if (r == -1) return -1;
        nextLimit = min(nextLimit, r);
    }
    return nextLimit;
}

// 3x3 棋盘的可解性：去掉空格后的逆序对个数为偶数，才能还原到 123456780
bool solvable(const string& s) {
    int inv = 0;
    for (int i = 0; i < 9; i++)
        for (int j = i + 1; j < 9; j++)
            if (s[i] != '0' && s[j] != '0' && s[i] > s[j]) inv++;
    return inv % 2 == 0;
}

int idastar(const string& s) {
    int zero = 0;
    for (int i = 0; i < 9; i++) { board[i] = s[i] - '0'; if (!board[i]) zero = i; }
    int limit = heuristic();                            // 第一轮上限 = h(起点)
    while (true) {
        int r = dfs(zero, 0, limit, -1);
        if (r == -1) return limit;                      // 找到时，limit 就是最少步数
        limit = r;                                      // 否则放宽到"刚好超出的最小 f"
    }
}

int main() {
    for (string s : {"724506831", "867254301", "123456087"}) {
        if (!solvable(s)) { cout << "起点 " << s << ": 无解\n"; continue; }
        nodes = 0;
        int steps = idastar(s);
        cout << "起点 " << s << ": 最少 " << steps << " 步，搜索 " << nodes << " 个节点\n";
    }
}
```

```text
起点 724506831: 最少 20 步，搜索 351 个节点
起点 867254301: 最少 31 步，搜索 26799 个节点
起点 123456087: 无解
```

三个起点依次是：一个 20 步的局面、一个 31 步的最难局面、一个无解局面（逆序对为奇数）。我另外随机生成了 300 个局面，可解的都与完整 BFS 的结果对照过，步数全部一致，无解的局面也都被正确识别。

## 适用与不适用

| 情况 | 建议 |
| --- | --- |
| 有较好的 h，状态数中等 | A\* |
| 状态数大、内存紧，h 较好 | IDA\* |
| 想不出可采纳的 h | 退回 BFS 或 Dijkstra |
| 允许近似解 | 把 h 放大（不再可采纳），速度更快但不保证最优 |
| 图很大且要求多次查询 | A\* 不是预处理方案，考虑其他最短路算法（5.2） |

## 常见坑

- **h 高估了**：解可能不是最优。比如把空格也算进曼哈顿距离和，就会高估。
- **A\* 没有处理过期的堆记录**：同一状态多次出队，节点数和结果都会出问题。
- **IDA\* 忘记禁止“走回头路”**：上一步的反方向走法会让搜索树变大很多。
- **IDA\* 的下一轮上限取错**：必须是被剪掉的所有状态中最小的 f，不是随便加 1。
- **没有先判无解**：八数码这类题一定要先判断。

## 练习

**入门**

- LeetCode 1197 进击的骑士（BFS，再试 A\*）
- LeetCode 773 滑动谜题

**进阶**

- 洛谷 P1379 八数码难题（A\* 和 IDA\* 都试一遍）

**挑战**

- 洛谷 P2324 骑士精神（IDA\*，题号待核实）
- 洛谷 P2901 Cow Jogging（A\* 求 k 短路，题号待核实）

下一篇：3.7 ⭐舞蹈链 DLX。
