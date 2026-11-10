---
title: "3.1 DFS 与回溯：选择、递归、撤销"
description: "用一棵决策树理解回溯：写出全排列、子集、组合、N 皇后的统一模板，并学会去重和在网格上做 DFS。"
sidebar:
  order: 301
---

> 适用版本：C++17。前置知识：递归（0.2 篇）。本篇是树、图和动态规划的入口，后面几乎每章都会回到 DFS。

## 本章学习建议

搜索是把"所有可能"一个不漏地走一遍。本章 3.1 到 3.4 是必学内容，3.5 以后带 ⭐ 的是进阶，可以先跳过。

- 3.1 和 3.2 要手写到不看模板也能写出来。DFS 要练到能在纸上画出递归树，BFS 要能解释"为什么第一次到达就是最短"。
- 3.3 的剪枝没有固定模板，靠做题积累，建议配合 3.1 的题一起练。
- 3.4 记忆化搜索是第 6 章动态规划的预备，学完请带着它去看第 6 章第 1 篇。
- ⭐ 的 5 到 8 篇都是独立专题，遇到对应题型再回来学。

## 要点

- 回溯就是 DFS 加"撤销"：每一层递归做一次选择，往下走，回来时把选择撤销，让现场恢复到进入前的样子。
- 回溯的搜索空间是一棵树。递归的一层对应树的一层，叶子是一个完整的方案，复杂度就是树的节点数。
- 排列用 `used[]` 标记谁已被选；子集和组合用 `start` 下标规定"只能往后选"，这样 `{1,2}` 不会和 `{2,1}` 重复。
- 输入有重复元素时，先排序，再在同一层跳过与前一个相同的数。
- 在图或网格上做 DFS 遍历时，`visited` 标记不需要撤销；这是和回溯方案的主要区别。

## DFS 和回溯的关系

DFS（深度优先搜索，depth-first search）的意思是：能往深处走就一直走，走不通再退回来。回溯（backtracking）是 DFS 在"构造方案"时的叫法：每走一步就做一个决定，把决定记在 `path` 里；退回来的时候，把这个决定从 `path` 里拿掉。

两者代码的差别只在一点：

- **遍历一张已有的图**（找连通块、判断能否到达）：访问过的点标记即可，不需要取消标记。
- **构造方案**（排列、子集、棋盘摆放）：同一个点在不同方案里会被选中，所以退回时必须取消标记。

## 全排列：回溯的标准模板

把 1 到 n 排成一排，有多少种排法？先想"第 1 个位置放谁，第 2 个位置放谁……"。每个位置是一次决策，可选的是还没用过的数。

![全排列的递归树，绿色是第一条走到底的路径](/qmx-Gameknowledge/assets/algo/c3-perm-tree.svg)

```text
dfs(depth):
    如果 depth == n：记录答案，返回
    对每个候选 i：
        如果 i 不能选：跳过
        选 i（修改 path、used）
        dfs(depth + 1)
        撤销 i（把 path、used 改回去）
```

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> path;       // 当前已经选好的数
vector<bool> used;      // used[i]：数字 i 是否已在 path 中

void dfs(int depth) {
    if (depth == n) {                       // 选满 n 个：得到一个完整排列
        for (int x : path) cout << x << ' ';
        cout << '\n';
        return;
    }
    for (int i = 1; i <= n; i++) {
        if (used[i]) continue;              // 选过的数不能再选
        used[i] = true;                     // 1. 选择
        path.push_back(i);
        dfs(depth + 1);                     // 2. 递归，处理下一个位置
        path.pop_back();                    // 3. 撤销，恢复现场
        used[i] = false;
    }
}

int main() {
    n = 3;
    used.assign(n + 1, false);
    dfs(0);
}
```

输出：

```text
1 2 3 
1 3 2 
2 1 3 
2 3 1 
3 1 2 
3 2 1 
```

撤销是最容易漏的一步。下表追踪前 6 步里 `path` 和 `used` 的变化：第 3 步输出 `[1,2,3]` 后，要先撤销 3，再撤销 2，`path` 才回到只有 `[1]` 的状态，这时才能选 3 得到 `[1,3]`。

![追踪 path 和 used：橙色行是撤销](/qmx-Gameknowledge/assets/algo/c3-backtrack-steps.svg)

**复杂度**：叶子有 n! 个，每个叶子要输出 n 个数，总共 O(n · n!)。n 超过 10 或 11 就跑不动了，这类题 n 通常很小。

## 子集与组合：用 start 避免重复

子集（subset）的每个元素只有"选"和"不选"。如果还像排列那样枚举"下一个选谁"，`{1,2}` 和 `{2,1}` 会被当成两个方案。解决办法是规定**下一个数的下标必须比上一个大**，用参数 `start` 表示。

![子集的搜索树：每个节点本身就是一个答案](/qmx-Gameknowledge/assets/algo/c3-subset-tree.svg)

子集的每个节点都是答案；组合（combination）只在恰好选了 k 个数时记录，到了深度 k 就可以不再往下走。

```cpp
#include <bits/stdc++.h>
using namespace std;

int n = 3, k = 2;
vector<int> path;

// 子集：每个节点本身就是一个答案，下一个数只能从 start 往后选，避免 {1,2} 与 {2,1} 重复
void subsets(int start) {
    cout << "{ ";
    for (int x : path) cout << x << ' ';
    cout << "}\n";
    for (int i = start; i <= n; i++) {
        path.push_back(i);
        subsets(i + 1);
        path.pop_back();
    }
}

// 组合：只在恰好选了 k 个数时才算答案
void combine(int start) {
    if ((int)path.size() == k) {
        for (int x : path) cout << x << ' ';
        cout << '\n';
        return;
    }
    for (int i = start; i <= n; i++) {
        path.push_back(i);
        combine(i + 1);
        path.pop_back();
    }
}

int main() {
    cout << "子集:\n";
    subsets(1);
    cout << "组合 C(3,2):\n";
    combine(1);
}
```

```text
子集:
{ }
{ 1 }
{ 1 2 }
{ 1 2 3 }
{ 1 3 }
{ 2 }
{ 2 3 }
{ 3 }
组合 C(3,2):
1 2 
1 3 
2 3 
```

**复杂度**：子集共 2^n 个，每个最长 n，O(n · 2^n)。组合 C(n, k) 个。

## 含重复元素：先排序，同层跳过

输入是 `{1, 1, 2}` 时，直接做全排列会得到 6 个结果，其中有重复。去重的思路是：**同一层里，相同的数只让第一个出场**。排序后相同的数相邻，判断"和前一个数相同，并且前一个数在本层没被用"就跳过。

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> a = {1, 1, 2};
vector<int> path;
vector<bool> used;

void dfs() {
    if (path.size() == a.size()) {
        for (int x : path) cout << x << ' ';
        cout << '\n';
        return;
    }
    for (int i = 0; i < (int)a.size(); i++) {
        if (used[i]) continue;
        // 同一层里，相同的数只让第一个出场；前一个相同的数没被用，说明它在本层已经试过
        if (i > 0 && a[i] == a[i - 1] && !used[i - 1]) continue;
        used[i] = true;
        path.push_back(a[i]);
        dfs();
        path.pop_back();
        used[i] = false;
    }
}

int main() {
    sort(a.begin(), a.end());               // 先排序，让相同的数相邻
    used.assign(a.size(), false);
    dfs();
}
```

```text
1 1 2 
1 2 1 
2 1 1 
```

判断条件 `!used[i-1]` 的含义：如果前一个相同的数 `used` 为真，说明它在当前路径的上层，是本方案的一部分，当前这个数可以放；如果为假，说明前一个相同的数在本层已经试过了，再试就重复。这一条可以先背下来，写出几个小例子手算后再理解。

## 例题

### 例题 1：N 皇后

在 n × n 的棋盘上放 n 个皇后，任意两个不能在同一行、同一列、同一条斜线上。求方案数（[LeetCode 51 N 皇后](https://leetcode.cn/problems/n-queens/)、洛谷 P1219）。

**思路**：每行必须恰好放一个，所以递归的深度就是行号，每层只需要决定"这一行放在哪一列"。冲突判断用三个布尔数组，都是 O(1)：

- 列：`col[c]`
- 主对角线（左上到右下）：同一条线上 `r - c` 相同，下标加 n 避免负数
- 副对角线（右上到左下）：同一条线上 `r + c` 相同

![左：一个皇后攻击到的格子。右：4 皇后的第一个解](/qmx-Gameknowledge/assets/algo/c3-nqueens.svg)

```cpp
#include <bits/stdc++.h>
using namespace std;

int n, cnt;
vector<bool> col, d1, d2;   // 列、主对角线(r-c)、副对角线(r+c)是否被占用
vector<int> pos;            // pos[r] = 第 r 行皇后所在的列

void dfs(int r, bool show) {
    if (r == n) {
        if (show && cnt == 0) {                 // 只打印第一个解
            for (int i = 0; i < n; i++) {
                string row(n, '.');
                row[pos[i]] = 'Q';
                cout << row << '\n';
            }
        }
        cnt++;
        return;
    }
    for (int c = 0; c < n; c++) {
        if (col[c] || d1[r - c + n] || d2[r + c]) continue;     // 同列或同对角线
        col[c] = d1[r - c + n] = d2[r + c] = true;
        pos[r] = c;
        dfs(r + 1, show);
        col[c] = d1[r - c + n] = d2[r + c] = false;
    }
}

int solve(int size, bool show) {
    n = size;
    cnt = 0;
    col.assign(n, false);
    d1.assign(2 * n + 1, false);
    d2.assign(2 * n + 1, false);
    pos.assign(n, 0);
    dfs(0, show);
    return cnt;
}

int main() {
    cout << "n=4 的第一个解:\n";
    solve(4, true);
    for (int s = 1; s <= 9; s++) cout << "n=" << s << " 解数: " << solve(s, false) << '\n';
}
```

```text
n=4 的第一个解:
.Q..
...Q
Q...
..Q.
n=1 解数: 1
n=2 解数: 0
n=3 解数: 0
n=4 解数: 2
n=5 解数: 10
n=6 解数: 4
n=7 解数: 40
n=8 解数: 92
n=9 解数: 352
```

n = 8 时是 92 个解，n = 9 时是 352 个，和已知结果一致。N 皇后没有简单的多项式上界，最坏是 O(n!)，实际因为大量冲突被提前判掉，比排列快得多。

### 例题 2：岛屿数量（网格上的 DFS）

给一个由 `'1'`（陆地）和 `'0'`（水）组成的网格，求岛屿数量，上下左右相连的陆地算一个岛（[LeetCode 200 岛屿数量](https://leetcode.cn/problems/number-of-islands/)，洛谷 P1596 类似）。

**思路**：扫描每个格子，遇到没访问的陆地，岛屿数加一，然后用 DFS 把这座岛的所有陆地都标记掉。这里是"遍历"而不是"构造方案"，所以标记后**不撤销**。下面的代码直接把访问过的陆地改成 `'0'`，省去 `visited` 数组。

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<string> g = {
    "11000",
    "11000",
    "00100",
    "00011",
};
int R, C;
const int dx[] = {1, -1, 0, 0}, dy[] = {0, 0, 1, -1};

void dfs(int x, int y) {
    if (x < 0 || x >= R || y < 0 || y >= C || g[x][y] != '1') return;   // 越界或不是陆地
    g[x][y] = '0';                                  // 标记已访问（直接改格子，不需要 visited）
    for (int d = 0; d < 4; d++) dfs(x + dx[d], y + dy[d]);
}

int main() {
    R = g.size(); C = g[0].size();
    int cnt = 0;
    for (int i = 0; i < R; i++)
        for (int j = 0; j < C; j++)
            if (g[i][j] == '1') { cnt++; dfs(i, j); }   // 每发现一块新陆地，淹掉整座岛
    cout << "岛屿数量: " << cnt << '\n';
}
```

```text
岛屿数量: 3
```

**复杂度**：每个格子最多访问一次，O(R · C)。

**递归深度**：网格上的 DFS 最深可以达到 R · C 层。如果网格有一百万格、整片都是陆地，默认的 1 MB（Windows）或 8 MB（Linux）栈可能溢出。遇到大网格，改用 BFS（3.2 篇）或自己用 `stack` 模拟。

## 常见坑

- **忘记撤销**：`path.push_back` 后没有 `pop_back`，或 `used[i] = true` 后没有改回，第二个方案开始就出错。
- **把 `path` 按值传递或记录答案时忘记拷贝**：把答案存进 `vector<vector<int>>` 时，要存 `path` 的副本，不能存引用。
- **子集和组合没有 `start`**：得到 `{1,2}` 和 `{2,1}` 两个重复结果。
- **去重条件写成 `used[i-1]`**：和 `!used[i-1]` 都能得到正确的去重效果，但两者剪枝的程度不同，需要统一写法并理解它。
- **网格 DFS 忘记检查边界**：先判越界，再访问数组。

## 练习

**入门**

- [LeetCode 46 全排列](https://leetcode.cn/problems/permutations/)
- [LeetCode 78 子集](https://leetcode.cn/problems/subsets/)
- [LeetCode 77 组合](https://leetcode.cn/problems/combinations/)
- 洛谷 P1706 全排列问题

**进阶**

- LeetCode 47 全排列 II（含重复元素）
- LeetCode 39 组合总和
- LeetCode 17 电话号码的字母组合
- LeetCode 79 单词搜索
- 洛谷 P1036 选数

**挑战**

- LeetCode 51 N 皇后（输出所有棋盘）
- LeetCode 37 解数独
- LeetCode 301 删除无效的括号

下一篇：3.2 BFS 与多源 BFS：一层一层找最短。
