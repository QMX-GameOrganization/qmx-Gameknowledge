---
title: "3.2 BFS 与多源 BFS：一层一层找最短"
description: "用队列实现广度优先搜索：网格最短路、路径还原、多源 BFS，以及把“状态”当作节点的 BFS。"
sidebar:
  order: 302
---

> 适用版本：C++17。前置知识：3.1 DFS；会用 `queue`。本篇的 BFS 是最短路（5.2）和拓扑排序（5.1）的基础。

## 要点

- BFS（广度优先搜索，breadth-first search）按"离起点的步数"一层一层扩展：先处理所有 1 步能到的点，再处理 2 步能到的点。
- 在**每条边代价相同**的图里，BFS 第一次到达某个点时走的就是最短路径，所以入队时就能标记距离。
- 用 `from[]` 数组记录"从哪个点走过来"，可以倒着还原出一条具体的最短路径。
- 多源 BFS：把所有起点同时放进队列，一次搜索就能求出每个点到最近起点的距离。
- BFS 的节点不一定是坐标，可以是任何"状态"，如棋盘局面、锁的读数。只要能列出"一步能到的下一个状态"即可。

## 一层一层向外扩

队列 `queue` 的先进先出，天然保证了顺序：先入队的点距离更小，先被处理。队列里任何时刻只有相邻两层的点：当前层剩下的，以及已经放进去的下一层。

```text
bfs(起点):
    dist[起点] = 0，起点入队
    当队列非空：
        取出队首 u
        对 u 的每个邻居 v：
            如果 v 没到过：
                dist[v] = dist[u] + 1，from[v] = u，v 入队
```

## 例题：网格最短路并输出路径

`S` 是起点，`T` 是终点，`#` 是墙，每步走上下左右一格。求最少步数，并输出一条路径。

![BFS 在迷宫上的分层：数字是最少步数，红框是还原出的路径](/qmx-Gameknowledge/assets/algo/c3-bfs-layers.svg)

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    vector<string> g = {
        "S.#..",
        ".##.#",
        "....#",
        "#.##.",
        "...T.",
    };
    int R = g.size(), C = g[0].size();
    const int dx[] = {1, -1, 0, 0}, dy[] = {0, 0, 1, -1};

    vector<vector<int>> dist(R, vector<int>(C, -1));                 // -1 表示还没到过
    vector<vector<pair<int, int>>> from(R, vector<pair<int, int>>(C, {-1, -1}));
    queue<pair<int, int>> q;
    int tx = 0, ty = 0;
    for (int i = 0; i < R; i++)
        for (int j = 0; j < C; j++) {
            if (g[i][j] == 'S') { dist[i][j] = 0; q.push({i, j}); }
            if (g[i][j] == 'T') { tx = i; ty = j; }
        }

    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx < 0 || nx >= R || ny < 0 || ny >= C) continue;
            if (g[nx][ny] == '#' || dist[nx][ny] != -1) continue;
            dist[nx][ny] = dist[x][y] + 1;                           // 第一次到达就是最短
            from[nx][ny] = {x, y};                                   // 记录从哪里来，用来还原路径
            q.push({nx, ny});
        }
    }

    cout << "最短步数: " << dist[tx][ty] << '\n';
    vector<pair<int, int>> path;
    for (pair<int, int> p = {tx, ty}; p.first != -1; p = from[p.first][p.second]) path.push_back(p);
    reverse(path.begin(), path.end());
    for (auto [x, y] : path) cout << '(' << x << ',' << y << ") ";
    cout << '\n';
}
```

```text
最短步数: 7
(0,0) (1,0) (2,0) (2,1) (3,1) (4,1) (4,2) (4,3) 
```

读图验证：从 `(0,0)` 出发，沿路径一共 7 步到达 `(4,3)`，和图里 T 格子的步数一致。

**为什么入队时标记就够**：BFS 按步数从小到大处理节点，一个点被第一次发现时，一定是通过步数最少的父节点。如果等到出队再标记，同一个点可能被多次放入队列，浪费时间。

**复杂度**：每个格子最多入队一次，每次检查 4 个方向，O(R · C)。

## 多源 BFS：多个起点一起出发

问题：给一个 0/1 矩阵，求每个格子到最近的 0 的距离（LeetCode 542）。

如果对每个格子单独跑一次 BFS，复杂度太高。换个角度：把**所有 0 同时放进队列**，距离都是 0，然后只扩展一次。这等价于在所有 0 前面加一个"超级源点"，连边到每个 0，从它出发做 BFS。

![多源 BFS：所有 0 同时入队，一层层向外扩](/qmx-Gameknowledge/assets/algo/c3-multi-bfs.svg)

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    // 每个格子到最近的 0 的距离（LeetCode 542）
    vector<vector<int>> a = {
        {0, 0, 0},
        {0, 1, 0},
        {1, 1, 1},
    };
    int R = a.size(), C = a[0].size();
    const int dx[] = {1, -1, 0, 0}, dy[] = {0, 0, 1, -1};

    vector<vector<int>> dist(R, vector<int>(C, -1));
    queue<pair<int, int>> q;
    for (int i = 0; i < R; i++)
        for (int j = 0; j < C; j++)
            if (a[i][j] == 0) { dist[i][j] = 0; q.push({i, j}); }   // 所有源点一次性入队

    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx < 0 || nx >= R || ny < 0 || ny >= C || dist[nx][ny] != -1) continue;
            dist[nx][ny] = dist[x][y] + 1;
            q.push({nx, ny});
        }
    }
    for (auto& row : dist) {
        for (int v : row) cout << v << ' ';
        cout << '\n';
    }
}
```

```text
0 0 0 
0 1 0 
1 2 1 
```

**复杂度**：O(R · C)，和单源 BFS 相同。腐烂的橘子（LeetCode 994）、血色先锋队这类"多个感染源同时扩散"的题都是这个模型。

## 状态也可以是节点

BFS 的"点"可以是任意状态。洛谷 P1443 马的遍历：棋盘上有一匹马，求它走到每个格子的最少步数。状态是坐标，"一步能到的下一个状态"是 8 个马步。

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 3, m = 3, sx = 1, sy = 1;               // 洛谷 P1443 的样例：3x3 棋盘，马在 (1,1)
    const int dx[] = {1, 2, 2, 1, -1, -2, -2, -1};
    const int dy[] = {2, 1, -1, -2, -2, -1, 1, 2};

    vector<vector<int>> dist(n + 1, vector<int>(m + 1, -1));
    queue<pair<int, int>> q;
    dist[sx][sy] = 0;
    q.push({sx, sy});
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 8; d++) {               // 状态就是坐标，走法有 8 种
            int nx = x + dx[d], ny = y + dy[d];
            if (nx < 1 || nx > n || ny < 1 || ny > m || dist[nx][ny] != -1) continue;
            dist[nx][ny] = dist[x][y] + 1;
            q.push({nx, ny});
        }
    }
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) cout << dist[i][j] << ' ';
        cout << '\n';
    }
}
```

```text
0 3 2 
3 -1 1 
2 1 4 
```

输出里的 `-1` 表示走不到。3 × 3 棋盘中心格子，马无法到达，和输出一致。

其他常见的状态 BFS：

- 打开转盘锁（LeetCode 752）：状态是 4 位数字，每步拨动一位。
- 单词接龙（LeetCode 127）：状态是单词，每步改一个字母。
- 滑动谜题（LeetCode 773）：状态是整个棋盘，每步移动空格。

状态较多时需要用哈希表（`unordered_map<string,int>`）代替数组记录距离。

## BFS 和 DFS 怎么选

| 需求 | 选 |
| --- | --- |
| 边权相同，求最少步数 | BFS |
| 列出所有方案、排列组合 | DFS（回溯） |
| 判断连通性、数连通块 | 都可以，大网格用 BFS 避免栈溢出 |
| 搜索深度很深但分支很少 | DFS |
| 状态空间很大，目标较近 | BFS，但注意队列内存 |

BFS 的缺点是内存：队列里会同时存放一整层，层越宽占的内存越多。DFS 只占一条路径的内存。

## 常见坑

- **边权不相同却用 BFS**：BFS 的"最短"是步数最少，不是代价最小。边权为 0 或 1 见 3.5（0-1 BFS），一般边权见 5.2（Dijkstra）。
- **忘记起点标记**：起点入队时没设 `dist` 或 `visited`，后面又走回起点。
- **出队才标记**：同一个点被重复入队，轻则变慢，重则内存爆炸。
- **多源 BFS 误写成循环单源**：对每个源点分别跑 BFS，复杂度从 O(RC) 变成 O(RC · 源点数)。
- **坐标写反**：行列和 `dx`、`dy` 的对应关系必须一致，建议用 `nx, ny` 变量命名，不要用 `i, j` 混着写。

## 练习

**入门**

- LeetCode 1091 二进制矩阵中的最短路径
- LeetCode 994 腐烂的橘子
- 洛谷 P1443 马的遍历
- 洛谷 P1135 奇怪的电梯

**进阶**

- LeetCode 542 01 矩阵
- LeetCode 752 打开转盘锁
- LeetCode 127 单词接龙
- 洛谷 P1162 填涂颜色
- 洛谷 P1332 血色先锋队（题号待核实）

**挑战**

- LeetCode 773 滑动谜题
- LeetCode 126 单词接龙 II（要输出所有最短路径）

下一篇：3.3 剪枝：把不可能的分支提前砍掉。
