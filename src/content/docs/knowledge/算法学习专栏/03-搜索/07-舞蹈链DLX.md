---
title: "3.7 ⭐舞蹈链 DLX"
description: "用十字双向链表实现精确覆盖的 Algorithm X：删除与恢复只改指针，并用它解数独。"
sidebar:
  order: 307
  badge:
    text: 进阶
    variant: caution
---

> 适用版本：C++17。前置知识：3.1 回溯、3.3 剪枝；会写双向链表。什么时候需要学：题目能转化成“每个约束恰好被满足一次”，如数独、多米诺铺满棋盘、拼图。普通数独用 3.3 的位运算回溯已经够快，DLX 的价值在于**通用**，一个模板解很多题。

## 要点

- 精确覆盖（exact cover）问题：给一个 0/1 矩阵，选出若干行，使**每一列恰好有一个 1**。
- Algorithm X（Knuth 提出）是回溯：选一列，逐行尝试覆盖它，再递归处理剩下的列。
- 舞蹈链（Dancing Links，DLX）是 Algorithm X 的数据结构：把矩阵里的每个 1 放进十字双向链表，**删除一个结点只改两个指针，恢复时按相反顺序还原**，所以回溯时撤销非常快。
- 选择“1 最少的列”开始，分支最少，相当于 3.3 里的搜索顺序剪枝。

## 精确覆盖

例：元素 1 到 7，6 个集合 A 到 F。选出若干个集合，使每个元素恰好出现在一个集合里。

![精确覆盖的矩阵：解是 B、D、F](/qmx-Gameknowledge/assets/algo/c3-dlx-matrix.svg)

B = {1,4}，D = {3,5,6}，F = {2,7}，三个集合互不相交，并起来恰好是 1 到 7，所以解是 B、D、F。

## Algorithm X

```text
solve():
    如果没有剩余的列：找到一个解
    选择含 1 最少的列 c
    如果 c 里没有 1：失败，返回
    对 c 中每个有 1 的行 r（把 r 加入当前解）：
        对 r 中每个有 1 的列 j：从矩阵中删除列 j，
                                 以及所有在列 j 里有 1 的行（它们与 r 冲突）
        solve()
        还原刚才的删除，把 r 从当前解中拿掉
```

“删除一列，以及这一列里有 1 的所有行”是关键操作，称为 cover；还原称为 uncover。如果矩阵用二维数组存，每次都要复制或遍历整张表，很慢。

## 舞蹈链

把矩阵中每个 1 做成一个结点，每个结点有 `L R U D` 四个指针，指向同一行的左右邻居和同一列的上下邻居，行、列各自首尾相连成环。另外有一排**列头**，记录这一列当前剩多少个 1（`cnt`），列头之间也用 `L R` 串起来，最左边加一个总表头 `0`。

双向链表中删除结点 `x` 只要两步：

```text
R[L[x]] = R[x];  L[R[x]] = L[x];
```

关键点是 `x` 自己的 `L[x]`、`R[x]` **不改**，仍然指着原来的邻居。恢复时只需要：

```text
R[L[x]] = x;  L[R[x]] = x;
```

条件是**恢复的顺序必须和删除的顺序严格相反**。这样每个结点恢复时，它左右的邻居正好是它被删除前的那两个。

![删除 B 只改 A 和 C 的指针；B 的指针保持不变，恢复时一步还原](/qmx-Gameknowledge/assets/algo/c3-dlx-remove.svg)

### 代码

下面的 `DLX` 结构体包含：建表（`addRow`）、`cover`、`uncover`、搜索（`dfs`）。`main` 里先跑 Knuth 的小例子，再用它解数独。

```cpp
#include <bits/stdc++.h>
using namespace std;

// 舞蹈链(Dancing Links) 精确覆盖：选出若干行，使每一列恰好被覆盖一次
struct DLX {
    int n;                                   // 列数
    vector<int> L, R, U, D, col, row;        // 十字双向链表；col[i]、row[i]：结点所在的列、行
    vector<int> cnt;                         // cnt[c]：第 c 列当前的结点数
    vector<int> ans;                         // 当前选中的行
    int sz;

    DLX(int n_) : n(n_) {
        int total = n + 1;                   // 0 号是总表头，1..n 是各列的表头
        L.resize(total); R.resize(total); U.resize(total); D.resize(total);
        col.resize(total); row.resize(total); cnt.assign(total, 0);
        for (int i = 0; i <= n; i++) {
            L[i] = i - 1; R[i] = i + 1; U[i] = D[i] = i; col[i] = i;
        }
        L[0] = n; R[n] = 0;                  // 表头首尾相接成环
        sz = n + 1;
    }

    // 添加第 r 行，cols 是这一行覆盖的列（从 1 开始）
    void addRow(int r, const vector<int>& cols) {
        int first = -1;
        for (int c : cols) {
            L.push_back(0); R.push_back(0); U.push_back(0); D.push_back(0); col.push_back(c); row.push_back(r);
            int x = sz++;
            // 纵向：插到第 c 列的最下面
            U[x] = U[c]; D[x] = c; D[U[c]] = x; U[c] = x;
            cnt[c]++;
            // 横向：插到本行的最右边
            if (first == -1) { first = x; L[x] = R[x] = x; }
            else { L[x] = L[first]; R[x] = first; R[L[first]] = x; L[first] = x; }
        }
    }

    // 删除列 c：把这一列从表头链上摘掉，并把"覆盖了这一列的所有行"从其他列里摘掉
    void cover(int c) {
        L[R[c]] = L[c]; R[L[c]] = R[c];
        for (int i = D[c]; i != c; i = D[i])
            for (int j = R[i]; j != i; j = R[j]) {
                U[D[j]] = U[j]; D[U[j]] = D[j]; cnt[col[j]]--;
            }
    }
    // 恢复列 c：与 cover 完全相反的顺序，所以链表能原样"跳回来"
    void uncover(int c) {
        for (int i = U[c]; i != c; i = U[i])
            for (int j = L[i]; j != i; j = L[j]) {
                U[D[j]] = j; D[U[j]] = j; cnt[col[j]]++;
            }
        L[R[c]] = c; R[L[c]] = c;
    }

    bool dfs() {
        if (R[0] == 0) return true;          // 所有列都被覆盖：找到一个解
        int c = R[0];
        for (int i = R[0]; i != 0; i = R[i]) // 选结点数最少的列，分支最少
            if (cnt[i] < cnt[c]) c = i;
        if (cnt[c] == 0) return false;       // 这一列没有任何行能覆盖：死路
        cover(c);
        for (int i = D[c]; i != c; i = D[i]) {
            ans.push_back(row[i]);
            for (int j = R[i]; j != i; j = R[j]) cover(col[j]);
            if (dfs()) return true;
            for (int j = L[i]; j != i; j = L[j]) uncover(col[j]);
            ans.pop_back();
        }
        uncover(c);
        return false;
    }
};

int main() {
    // 例 1：Knuth 论文里的小例子。集合 A..F 覆盖元素 1..7，要求每个元素恰好被覆盖一次
    {
        vector<vector<int>> sets = {{1, 4, 7}, {1, 4}, {4, 5, 7}, {3, 5, 6}, {2, 3, 6, 7}, {2, 7}};
        DLX d(7);
        for (int i = 0; i < (int)sets.size(); i++) d.addRow(i, sets[i]);
        if (d.dfs()) {
            sort(d.ans.begin(), d.ans.end());
            cout << "精确覆盖选中的集合:";
            for (int r : d.ans) cout << ' ' << char('A' + r);
            cout << '\n';
        }
    }
    // 例 2：数独。行 = (格子, 数字) 的 729 种选择；列 = 324 个约束
    {
        string s = "530070000600195000098000060800060003400803001700020006060000280000419005000080079";
        DLX d(324);
        auto add = [&](int r, int c, int v) {   // v 取 0..8
            int id = (r * 9 + c) * 9 + v;
            d.addRow(id, {1 + r * 9 + c,                // 约束 1：格子 (r,c) 有数
                          82 + r * 9 + v,               // 约束 2：第 r 行有数字 v
                          163 + c * 9 + v,              // 约束 3：第 c 列有数字 v
                          244 + (r / 3 * 3 + c / 3) * 9 + v});  // 约束 4：第 b 宫有数字 v
        };
        for (int r = 0; r < 9; r++)
            for (int c = 0; c < 9; c++) {
                int ch = s[r * 9 + c] - '0';
                if (ch) add(r, c, ch - 1);              // 已知数字：只放一行
                else for (int v = 0; v < 9; v++) add(r, c, v);   // 空格：9 种可能各放一行
            }
        if (d.dfs()) {
            vector<int> grid(81);
            for (int id : d.ans) grid[id / 9] = id % 9 + 1;
            for (int r = 0; r < 9; r++) {
                for (int c = 0; c < 9; c++) cout << grid[r * 9 + c];
                cout << '\n';
            }
        }
    }
}
```

```text
精确覆盖选中的集合: B D F
534678912
672195348
198342567
859761423
426853791
713924856
961537284
287419635
345286179
```

第一行是小例子的解 B、D、F。后面 9 行是数独的解，和 3.3 里用位运算回溯得到的答案相同。

### 数独怎么变成精确覆盖

- **行**：每个“(格子, 数字)”的选择是一行，共 9 × 9 × 9 = 729 行。
- **列**：数独的 4 类约束，每类 81 个，共 324 列：
  1. 每个格子恰好有一个数；
  2. 每行的每个数字恰好出现一次；
  3. 每列的每个数字恰好出现一次；
  4. 每宫的每个数字恰好出现一次。
- 每一行恰好覆盖 4 列（它满足 4 个约束）。已知数字的格子只放那一行，空格放 9 行。

找到解时，选中的 81 行就是每个格子的数字。N 皇后也可以建模，但“对角线至多一个皇后”不是“恰好一次”，需要把对角线列设为可选列，这是 DLX 的一个扩展用法，本篇不展开。

## 复杂度与特点

- 最坏情况仍是指数级，因为精确覆盖是 NP 完全问题。
- 实际速度很快：选“1 最少的列”让分支数最小；cover/uncover 的开销和被改动的结点数成正比，没有任何拷贝。
- 内存：结点数 = 矩阵中 1 的个数，加列头。

## 适用与不适用

| 情况 | 建议 |
| --- | --- |
| “恰好一次”的覆盖约束 | DLX |
| 只要至多一次或至少一次 | 需要 DLX 的扩展（可选列、重复覆盖），或换别的方法 |
| 状态规模小，约束简单 | 位运算回溯更短更快 |
| 要计数方案数而不是找一个解 | 搜索时不在第一个解返回，累加计数即可 |

## 常见坑

- **cover 和 uncover 的遍历方向不对称**：cover 时遍历行结点用 `R`，uncover 时必须用 `L` 并且按列从下往上（`U`）。我的代码里 `uncover` 用 `U`、`L`，与 `cover` 的 `D`、`R` 正好相反。
- **列头的 `cnt` 没有同步维护**：选列时会选错，退化成很慢。
- **只在找到解时返回 `true`，没有还原现场**：找一个解可以直接返回，但如果之后还要复用这个结构，必须还原。
- **行号与列号从 0 还是从 1 开始**：0 号位置是总表头，列从 1 开始。

## 练习

**入门**

- 洛谷 P4929 【模板】舞蹈链（DLX）
- LeetCode 37 解数独（用 DLX 重写一次）

**进阶**

- 洛谷 P1074 靶形数独（先求所有解，再评分）
- 改写 `dfs`，统计精确覆盖的解的总数（找到解后不返回，继续搜），用 Knuth 的小例子验证总数为 1

**挑战**

- 洛谷 P1219 八皇后（建模时对角线是“可选列”：不要求被覆盖，需要给 DLX 加上可选列的支持）
- 把一块 6 × 10 的棋盘用 12 种五格骨牌铺满（Pentomino，自己建模）

下一篇：3.8 ⭐模拟退火与爬山。
