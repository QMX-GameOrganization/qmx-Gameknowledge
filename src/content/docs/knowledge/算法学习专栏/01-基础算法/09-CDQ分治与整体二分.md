---
title: "1.9 ⭐CDQ 分治与整体二分"
description: "用分治处理“前面的元素对后面的元素的贡献”（三维偏序），以及把一批询问放在一起二分答案（静态区间第 k 小）。"
sidebar:
  order: 109
  badge:
    text: 进阶
    variant: caution
---

> 适用版本：C++17。前置：1.1 归并排序与逆序对、1.2 二分、4.6 树状数组（本篇代码要用）。什么时候需要学它：三维及以上的偏序计数；带修改的离线统计；一批询问各自要二分答案、单个二分的判定又很贵。

## 要点

- CDQ 分治（得名于陈丹琦的论文）：处理区间 `[l, r]` 时，先递归处理左右两半，再计算“左半对右半”的贡献。它是 1.1 里“归并时统计逆序对”的推广。
- 二维偏序是逆序对：排序一维，另一维归并。三维偏序：排序一维，CDQ 分治第二维，树状数组处理第三维，复杂度 O(n log²n)。
- 偏序问题的统一写法：先按第一维排序，这样分治时“左半的第一维都不大于右半”自动成立，第一维不再需要考虑。
- 整体二分（parallel / overall binary search）：把所有询问放在一起，同时对答案二分，每一层把询问按答案落在左半还是右半分组。适合离线、答案满足单调性、单个询问的判定可以批量完成的场景。
- 两者都是**离线**算法：必须事先知道全部操作和询问。

## CDQ 分治：三维偏序

![先递归左右两半，再统计左半对右半的贡献](/qmx-Gameknowledge/assets/algo/c1-cdq.svg)

问题（洛谷 P3810）：给定 `n` 个点 `(a, b, c)`，对每个点 `i`，求有多少个其他点 `j` 满足 `a[j] ≤ a[i]`、`b[j] ≤ b[i]`、`c[j] ≤ c[i]`。输出：对每个 `d`，恰好有 `d` 个点的个数。

做法：

1. 按 `(a, b, c)` 字典序排序，相同的点合并成一个，带上权重 `w`（相同点互相算作贡献）。排序之后，如果 `j` 满足三个条件，则 `j` 一定排在 `i` 前面。这样**第一维被消掉了**，只需要考虑“排在前面的点对排在后面的点”。
2. `cdq(l, r)`：先递归 `[l, m)` 和 `[m, r)`。递归返回时，两半各自已经按 `b` 升序排好。
3. 统计左半对右半的贡献：对右半每个点 `j`（按 `b` 升序），把左半中 `b ≤ b[j]` 的点依次加入树状数组（以 `c` 为下标累加权重），然后查询 `c ≤ c[j]` 的权重和，累加到 `j` 的答案上。
4. 撤销树状数组中的修改（逐个减回去，不能整体清零，否则复杂度退化）。
5. 把 `[l, r)` 按 `b` 归并，供上一层使用。

```cpp
#include <bits/stdc++.h>
using namespace std;

struct P { int a, b, c, w, ans; };
vector<P> p;
vector<int> bit;
int K;   // c 的值域上界

void add(int i, int v) { for (; i <= K; i += i & -i) bit[i] += v; }
int query(int i) { int s = 0; for (; i > 0; i -= i & -i) s += bit[i]; return s; }

// 处理 p[l, r)：执行后 p[l, r) 按 (b, c) 升序，且左半对右半的贡献已累加
void cdq(int l, int r) {
    if (r - l <= 1) return;
    int m = (l + r) / 2;
    cdq(l, m);
    cdq(m, r);
    int i = l;
    for (int j = m; j < r; j++) {
        while (i < m && p[i].b <= p[j].b) { add(p[i].c, p[i].w); i++; }
        p[j].ans += query(p[j].c);
    }
    for (int t = l; t < i; t++) add(p[t].c, -p[t].w);   // 撤销，不能用 memset
    inplace_merge(p.begin() + l, p.begin() + m, p.begin() + r,
                  [](const P& x, const P& y) { return x.b != y.b ? x.b < y.b : x.c < y.c; });
}

int main() {
    vector<array<int, 3>> pts = {{3, 3, 3}, {2, 3, 3}, {2, 3, 1}, {3, 1, 1}, {3, 1, 2},
                                 {1, 3, 1}, {1, 1, 2}, {1, 2, 2}, {1, 3, 2}, {1, 2, 1}};
    int n = pts.size();
    sort(pts.begin(), pts.end());                       // 消掉第一维
    K = 0;
    for (auto& t : pts) K = max(K, t[2]);
    bit.assign(K + 1, 0);
    for (int i = 0; i < n; i++) {                       // 合并完全相同的点
        if (!p.empty() && p.back().a == pts[i][0] && p.back().b == pts[i][1] && p.back().c == pts[i][2])
            p.back().w++;
        else
            p.push_back({pts[i][0], pts[i][1], pts[i][2], 1, 0});
    }
    cdq(0, p.size());
    vector<int> level(n, 0);
    for (auto& q : p) level[q.ans + q.w - 1] += q.w;    // 答案 = 其他组的贡献 + 同组其他点数
    for (int d = 0; d < n; d++) printf("%d\n", level[d]);
    // 依次输出 3 1 3 0 1 0 1 0 0 1
}
```

关键细节：

- 相同的点合并后，组内互相都满足条件，所以点 `i` 的最终答案是 `ans + w - 1`（`ans` 是其他组贡献的权重和，`w - 1` 是组内其他点数）。
- 右半点 `j` 按 `b` 升序处理，而左半指针 `i` 只前进不后退，每一对左右点只经过一次，加上树状数组的 `log`，一层是 O(n log n)，共 log n 层。
- `b` 相等时 `p[i].b <= p[j].b` 把左半这个点也加进去了，`c` 相等时 `query` 的前缀包含了它，满足题目的“不大于”。

### 其他适用形式

CDQ 分治不只用于静态偏序。把“时间”当作一维，就能处理带修改的问题：每个操作视为一个点，修改在时间上排在询问前面，则“左半的修改对右半的询问的影响”正是 CDQ 要统计的。例如“动态二维数点”“带修改的最长上升子序列”（用 CDQ 优化 DP，要特别注意按“左 → 中 → 右”的顺序，DP 值必须在左半算完之后才能用来更新右半）。

## 整体二分

先看一个单独的问题：静态数组上，多次询问“区间 `[l, r]` 的第 `k` 小”。

对单个询问二分答案 `x`：数区间内 `≤ x` 的个数 `cnt`，若 `cnt ≥ k` 答案不超过 `x`。一次计数需要 O(n)，`q` 个询问就是 O(qn log V)，太慢。

整体二分的想法：把**所有询问放在一起**，对答案值域 `[lo, hi]` 二分。取 `mid`，把所有值在 `[lo, mid]` 的元素统一加入树状数组（位置上加 1），然后对每个询问查询它区间内的元素个数 `c`：

- `k ≤ c`：答案在 `[lo, mid]`，询问分到左边。
- 否则：答案在 `[mid+1, hi]`，同时 `k -= c`（左边这 `c` 个已经比答案小），询问分到右边。

处理完再撤销树状数组，递归处理左右两组询问。每个询问沿着二分的路径一路往下走，每层元素总数和询问总数都是 `O(n + q)`，所以整体复杂度 O((n + q) log n log V)。

为了避免写离散化，这里按“排名”二分：先把下标按值排序得到 `ord_`，二分的是排名区间。

```cpp
#include <bits/stdc++.h>
using namespace std;

int n, q;
vector<int> a, ord_;             // ord_：按值升序排列的下标
vector<int> bit_;
struct Q { int l, r, k, id; };
vector<int> ans;

void add(int i, int v) { for (i++; i <= n; i += i & -i) bit_[i] += v; }
int sum(int i) { int s = 0; for (i++; i > 0; i -= i & -i) s += bit_[i]; return s; }   // 下标 [0, i]

// 排名区间 [lo, hi]；qs 中所有询问的答案都落在这个排名区间内
void solve(int lo, int hi, vector<Q>& qs) {
    if (qs.empty()) return;
    if (lo == hi) {
        for (auto& x : qs) ans[x.id] = a[ord_[lo]];
        return;
    }
    int mid = (lo + hi) / 2;
    for (int i = lo; i <= mid; i++) add(ord_[i], 1);          // 把排名 [lo, mid] 的元素放进树状数组
    vector<Q> left, right;
    for (auto& x : qs) {
        int c = sum(x.r) - (x.l ? sum(x.l - 1) : 0);          // 区间内排名在 [lo, mid] 的个数
        if (x.k <= c) left.push_back(x);
        else { x.k -= c; right.push_back(x); }
    }
    for (int i = lo; i <= mid; i++) add(ord_[i], -1);         // 撤销
    solve(lo, mid, left);
    solve(mid + 1, hi, right);
}

int main() {
    a = {1, 5, 2, 6, 3, 7, 4};
    n = a.size();
    vector<Q> qs = {{0, 4, 3, 0}, {2, 6, 1, 1}, {1, 3, 3, 2}};   // 区间 [l, r]（0 起）第 k 小
    q = qs.size();
    ans.assign(q, 0);
    ord_.resize(n);
    iota(ord_.begin(), ord_.end(), 0);
    sort(ord_.begin(), ord_.end(), [&](int x, int y) { return a[x] != a[y] ? a[x] < a[y] : x < y; });
    bit_.assign(n + 1, 0);
    solve(0, n - 1, qs);
    for (int i = 0; i < q; i++) printf("%d\n", ans[i]);   // 3 2 6
}
```

这道题有更直接的在线解法（主席树，见 4.12），整体二分的价值在于它可以套到更多题上：只要“判定”可以对一批询问同时完成，并且支持撤销，就能用。常见例子有带修改的区间第 k 小、多个询问共用的“时间最早满足条件”（如“第几天开始满足 ≥ k”）。

## 适用与不适用

| 条件 | CDQ 分治 | 整体二分 |
| --- | --- | --- |
| 能离线 | 必须 | 必须 |
| 本质 | 多维偏序、前面影响后面 | 答案可二分，批量判定 |
| 额外数据结构 | 树状数组等 | 树状数组等 |
| 复杂度 | O(n log²n) | O((n + q) log n log V) |
| 只能在线 | 不适用，换主席树、平衡树 | 不适用 |

## 常见坑

- CDQ 的树状数组撤销必须只撤销自己加的部分，用整体清零会让复杂度变成 O(n²)。
- 合并相同点后答案公式 `ans + w - 1` 容易漏掉 `- 1` 或者把 `w` 加两次。
- 排序比较函数要覆盖第一维的所有 tie（`a` 相等时按 `b` 再按 `c`），否则“排在前面的才可能被统计”这一前提不成立。
- 整体二分里询问要先按左右拆开再递归，而不是边递归边修改同一个数组，注意拷贝的开销。
- 整体二分的值域二分用到了“按排名”还是“按值”，两种写法的区间含义不同，不要混用。

## 挑战题

- 洛谷 P3810 【模板】三维偏序（陌上花开）：本篇的 CDQ 程序即可通过。
- 洛谷 P3834 【模板】可持久化线段树 2：整体二分写法对比主席树写法。
- 洛谷 P1908 逆序对：用 CDQ 的二维偏序视角重写一遍。
- 洛谷 P4390 [BOI2007] Mokia 摩基亚：CDQ 处理单点修改加二维查询。
- LeetCode 315 计算右侧小于当前元素的个数、LeetCode 493 翻转对：二维偏序形式，可以对照 1.1 的写法。

下一篇：1.10 ⭐莫队。


