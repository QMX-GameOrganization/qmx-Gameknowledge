---
title: "4.10 ⭐Treap 与 Splay"
description: "用随机优先级和 split/merge 实现简洁的平衡树，用伸展操作实现均摊 O(log n) 的 Splay，并用序列版 Treap 做区间翻转。"
sidebar:
  order: 410
  badge:
    text: 进阶
    variant: caution
---

> 适用版本：C++17。前置：4.2 二叉搜索树，4.9 中的旋转。什么时候需要学它：题目要求"动态维护有序集合并支持排名、第 k 小"，而 `set` 做不到（`set` 不能在 O(log n) 内求排名），或者要对序列做区间翻转、区间插入删除。竞赛里最常用的是 Treap；Splay 码量稍大，但它是后面学习动态树（LCT）的基础。

## 要点

- **Treap = Tree + Heap**：每个结点有键值（满足二叉搜索树）和随机优先级（满足大根堆）。随机优先级使树的形状等价于"按随机顺序插入的 BST"，期望高度 O(log n)。
- 无旋 Treap 只靠两个操作：`split`（按键值把树劈成两棵）和 `merge`（把两棵树接成一棵），插入、删除、排名全部由它们组合而成，代码最短。
- **序列版 Treap** 按位置而不是键值分裂，加上懒标记就能 O(log n) 做区间翻转。
- **Splay** 不记录任何平衡信息，每访问一个结点就用旋转把它搬到根。单次操作可能是 O(n)，但任意 m 次操作总共 O(m log n)（均摊）。
- 两者都能实现"插入、删除、排名、第 k 小、前驱、后继"，选一种写熟即可。

## Treap

### 结构

每个结点存键值 `val`、优先级 `pri` 和子树大小 `sz`。左子树键值更小，右子树键值更大（BST 性质）；父亲的优先级不小于孩子（堆性质）。

给定一组键值和一组不同的优先级，满足这两条性质的树是**唯一**的：优先级最大的结点必须是根，其余按键值分到左右。所以优先级随机，就等于把键按随机顺序插入 BST，而随机顺序下 BST 的期望高度是 O(log n)。

### split 与 merge

![split(root, 3)：沿一条路径把树劈成键值 <= 3 和 > 3 的两棵树](/qmx-Gameknowledge/assets/algo/c4-10-treap-split.svg)

**split(t, k)**：把树 t 分成 a 和 b，a 中全是键值 <= k 的结点，b 中全是 > k 的结点。看根 t：

- 若 `val[t] <= k`：t 和它的左子树都属于 a。右子树里还可能有该归 a 的，递归 `split(rs[t], k)`，结果的左半接到 t 的右边。
- 否则对称：t 和它的右子树属于 b，递归 `split(ls[t], k)`。

每一步深度加 1，只走一条路径，所以是 O(高度)。堆性质自然保持：结果树里每个结点的孩子都是原来它的后代，优先级仍不大于它。

**merge(a, b)**：要求 a 的所有键值不大于 b 的所有键值。比较两个根的优先级：优先级大的做根，比如 `pri[a] > pri[b]`，则 a 做根，它的左子树不变，右子树变成 `merge(rs[a], b)`。

### 用 split 与 merge 组合操作

- **插入 v**：`split(root, v)` 得到 a、b，把新结点夹在中间：`merge(merge(a, 新结点), b)`。
- **删除一个 v**：先 `split(root, v)` 分出 a、b，再 `split(a, v-1)` 分出 a、c，c 里全是等于 v 的结点。去掉 c 的根（把它的两个孩子 merge 起来），再接回去。
- **排名**：`split(root, v-1)`，左树大小加 1 就是比 v 小的个数加 1。
- **第 k 小**：按 `sz` 从根往下找，不需要分裂。
- **前驱 / 后继**：在 `split` 出的左树里取最大，或在右树里取最小。

### 代码

```cpp
#include <bits/stdc++.h>
using namespace std;

// 分裂合并式 Treap（可重复元素的有序多重集）：键值满足二叉搜索树，随机优先级满足大根堆
const int N = 100005;
int ls[N], rs[N], val[N], sz[N], tot, root;
unsigned pri[N];
mt19937 rng(20240601);

int newNode(int v) {
    ++tot;
    val[tot] = v;
    pri[tot] = rng();
    ls[tot] = rs[tot] = 0;
    sz[tot] = 1;
    return tot;
}
void pull(int t) { sz[t] = sz[ls[t]] + sz[rs[t]] + 1; }   // 0 号结点是空结点，sz[0] = 0

// 按值分裂：a 里全是 <= k 的，b 里全是 > k 的
void split(int t, int k, int& a, int& b) {
    if (!t) { a = b = 0; return; }
    if (val[t] <= k) {
        a = t;
        split(rs[t], k, rs[a], b);
        pull(a);
    } else {
        b = t;
        split(ls[t], k, a, ls[b]);
        pull(b);
    }
}
// 合并：要求 a 中所有键 <= b 中所有键；优先级大的做根
int merge(int a, int b) {
    if (!a || !b) return a | b;
    if (pri[a] > pri[b]) {
        rs[a] = merge(rs[a], b);
        pull(a);
        return a;
    }
    ls[b] = merge(a, ls[b]);
    pull(b);
    return b;
}

void insert(int v) {
    int a, b;
    split(root, v, a, b);
    root = merge(merge(a, newNode(v)), b);
}
void erase(int v) {                      // 删除一个值为 v 的结点（不存在则什么也不做）
    int a, b, c;
    split(root, v, a, b);
    split(a, v - 1, a, c);               // c 里全是等于 v 的
    c = merge(ls[c], rs[c]);             // 去掉 c 的根（c 为空时 ls、rs 都是 0，仍然正确）
    root = merge(merge(a, c), b);
}
int rankOf(int v) {                      // 比 v 小的个数 + 1
    int a, b;
    split(root, v - 1, a, b);
    int r = sz[a] + 1;
    root = merge(a, b);
    return r;
}
int kth(int t, int k) {                  // 第 k 小，要求 1 <= k <= sz[t]
    while (true) {
        if (k <= sz[ls[t]]) t = ls[t];
        else if (k == sz[ls[t]] + 1) return val[t];
        else k -= sz[ls[t]] + 1, t = rs[t];
    }
}
int pre(int v) {                         // 严格小于 v 的最大值（要求存在）
    int a, b;
    split(root, v - 1, a, b);
    int r = kth(a, sz[a]);
    root = merge(a, b);
    return r;
}
int nxt(int v) {                         // 严格大于 v 的最小值（要求存在）
    int a, b;
    split(root, v, a, b);
    int r = kth(b, 1);
    root = merge(a, b);
    return r;
}

int main() {
    for (int x : {5, 3, 8, 3, 10, 1}) insert(x);
    printf("5 的排名 = %d\n", rankOf(5));            // 1 3 3 5 8 10 -> 排名 4
    printf("第 3 小 = %d\n", kth(root, 3));          // 3
    printf("5 的前驱 = %d，后继 = %d\n", pre(5), nxt(5));
    erase(3);
    printf("删一个 3 后，第 3 小 = %d\n", kth(root, 3));   // 1 3 5 ... -> 5
    return 0;
}
```

输出：

```text
5 的排名 = 4
第 3 小 = 3
5 的前驱 = 3，后继 = 8
删一个 3 后，第 3 小 = 5
```

插入的序列是 5 3 8 3 10 1，排序后 1 3 3 5 8 10，5 排第 4，第 3 小是 3，和手算一致。注意 `newNode` 里要把 `ls`、`rs` 清零，否则在多组数据复用数组时会带着旧的孩子指针。

### 例题：洛谷 P3369【模板】普通平衡树

操作 1 插入 x，2 删除一个 x，3 查 x 的排名，4 查排名为 k 的数，5 求前驱，6 求后继。直接套上面的函数：

```cpp
#include <bits/stdc++.h>
using namespace std;

// 分裂合并式 Treap（可重复元素的有序多重集）：键值满足二叉搜索树，随机优先级满足大根堆
const int N = 100005;
int ls[N], rs[N], val[N], sz[N], tot, root;
unsigned pri[N];
mt19937 rng(20240601);

int newNode(int v) {
    ++tot;
    val[tot] = v;
    pri[tot] = rng();
    ls[tot] = rs[tot] = 0;
    sz[tot] = 1;
    return tot;
}
void pull(int t) { sz[t] = sz[ls[t]] + sz[rs[t]] + 1; }   // 0 号结点是空结点，sz[0] = 0

// 按值分裂：a 里全是 <= k 的，b 里全是 > k 的
void split(int t, int k, int& a, int& b) {
    if (!t) { a = b = 0; return; }
    if (val[t] <= k) {
        a = t;
        split(rs[t], k, rs[a], b);
        pull(a);
    } else {
        b = t;
        split(ls[t], k, a, ls[b]);
        pull(b);
    }
}
// 合并：要求 a 中所有键 <= b 中所有键；优先级大的做根
int merge(int a, int b) {
    if (!a || !b) return a | b;
    if (pri[a] > pri[b]) {
        rs[a] = merge(rs[a], b);
        pull(a);
        return a;
    }
    ls[b] = merge(a, ls[b]);
    pull(b);
    return b;
}

void insert(int v) {
    int a, b;
    split(root, v, a, b);
    root = merge(merge(a, newNode(v)), b);
}
void erase(int v) {                      // 删除一个值为 v 的结点（不存在则什么也不做）
    int a, b, c;
    split(root, v, a, b);
    split(a, v - 1, a, c);               // c 里全是等于 v 的
    c = merge(ls[c], rs[c]);             // 去掉 c 的根（c 为空时 ls、rs 都是 0，仍然正确）
    root = merge(merge(a, c), b);
}
int rankOf(int v) {                      // 比 v 小的个数 + 1
    int a, b;
    split(root, v - 1, a, b);
    int r = sz[a] + 1;
    root = merge(a, b);
    return r;
}
int kth(int t, int k) {                  // 第 k 小，要求 1 <= k <= sz[t]
    while (true) {
        if (k <= sz[ls[t]]) t = ls[t];
        else if (k == sz[ls[t]] + 1) return val[t];
        else k -= sz[ls[t]] + 1, t = rs[t];
    }
}
int pre(int v) {                         // 严格小于 v 的最大值（要求存在）
    int a, b;
    split(root, v - 1, a, b);
    int r = kth(a, sz[a]);
    root = merge(a, b);
    return r;
}
int nxt(int v) {                         // 严格大于 v 的最小值（要求存在）
    int a, b;
    split(root, v, a, b);
    int r = kth(b, 1);
    root = merge(a, b);
    return r;
}

// 洛谷 P3369【模板】普通平衡树：
// 1 x 插入 x；2 x 删除一个 x；3 x 查 x 的排名；4 k 查排名为 k 的数；5 x 前驱；6 x 后继
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int q;
    cin >> q;
    while (q--) {
        int op, x;
        cin >> op >> x;
        if (op == 1) insert(x);
        else if (op == 2) erase(x);
        else if (op == 3) cout << rankOf(x) << "\n";
        else if (op == 4) cout << kth(root, x) << "\n";
        else if (op == 5) cout << pre(x) << "\n";
        else cout << nxt(x) << "\n";
    }
    return 0;
}
```

用官方样例前几行的输入：

```text
10
1 106465
4 1
1 317721
1 460929
1 644985
1 84185
1 89851
6 81968
1 492737
5 493598
```

得到

```text
106465
84185
492737
```

### 序列版 Treap：区间翻转

把"键值"换成"位置"：不存键值，按子树大小分裂，`split(t, k)` 表示前 k 个结点归 a。这样 Treap 就变成一个可以任意切开、拼接的序列。

区间翻转 `[l, r]`：把序列切成 `[1, l-1]`、`[l, r]`、`[r+1, n]` 三段，对中间那段打一个"翻转"标记，再拼回去。标记含义是"这棵子树还欠一次翻转，孩子尚未交换"，需要用到孩子之前（`split`、`merge`、输出时）先**下放**：交换左右孩子，并把标记传给两个孩子。

```cpp
#include <bits/stdc++.h>
using namespace std;

// 序列版 Treap（隐式键）：按"位置"而不是键值分裂，支持区间翻转
// 洛谷 P3391【模板】文艺平衡树：初始序列 1..n，m 次操作"翻转区间 [l, r]"，输出最终序列
const int N = 100005;
int ls[N], rs[N], sz[N], val[N];
unsigned pri[N];
bool rev[N];                             // rev[t] = true：t 的整棵子树还欠一次翻转（孩子尚未交换）
int root, tot;
mt19937 rng(12345);

void pull(int t) { sz[t] = sz[ls[t]] + sz[rs[t]] + 1; }
void flip(int t) { if (t) rev[t] ^= 1; }
void push(int t) {                       // 把翻转标记下放一层
    if (!rev[t]) return;
    swap(ls[t], rs[t]);
    flip(ls[t]);
    flip(rs[t]);
    rev[t] = false;
}
void split(int t, int k, int& a, int& b) {   // 前 k 个结点归 a，其余归 b
    if (!t) { a = b = 0; return; }
    push(t);
    if (sz[ls[t]] + 1 <= k) {
        a = t;
        split(rs[t], k - sz[ls[t]] - 1, rs[a], b);
        pull(a);
    } else {
        b = t;
        split(ls[t], k, a, ls[b]);
        pull(b);
    }
}
int merge(int a, int b) {
    if (!a || !b) return a | b;
    if (pri[a] > pri[b]) {
        push(a);
        rs[a] = merge(rs[a], b);
        pull(a);
        return a;
    }
    push(b);
    ls[b] = merge(a, ls[b]);
    pull(b);
    return b;
}
void reverse(int l, int r) {
    int a, b, c;
    split(root, r, a, c);                // a = 前 r 个，c = 其余
    split(a, l - 1, a, b);               // a = 前 l-1 个，b = 第 l..r 个
    flip(b);                             // 只打标记，O(1)
    root = merge(merge(a, b), c);
}
void output(int t) {                     // 中序输出；经过时顺手下放标记
    if (!t) return;
    push(t);
    output(ls[t]);
    printf("%d ", val[t]);
    output(rs[t]);
}

int main() {
    int n, m;
    if (scanf("%d %d", &n, &m) != 2) return 0;
    for (int i = 1; i <= n; i++) {       // 依次合并 1..n，得到初始序列
        ++tot;
        val[tot] = i;
        pri[tot] = rng();
        sz[tot] = 1;
        root = merge(root, tot);
    }
    while (m--) {
        int l, r;
        if (scanf("%d %d", &l, &r) != 2) return 0;
        reverse(l, r);
    }
    output(root);
    printf("\n");
    return 0;
}
```

输入 `5 3` 加三次操作 `1 3`、`1 3`、`1 4`：

```text
4 3 2 1 5 
```

先翻转 [1,3] 得到 3 2 1 4 5，再翻转一次回到 1 2 3 4 5，最后翻转 [1,4] 得到 4 3 2 1 5。

## Splay

### 思想

Splay（伸展树）不维护高度、优先级之类的平衡信息，只遵守一条规则：**每访问一个结点（查找、插入、删除都算），就用旋转把它搬到根**。

为什么这样有效：最近访问过的结点靠近根，再次访问很快（局部性）；而搬运过程中路径上的其他结点深度大致减半，一次很贵的访问会"修好"沿途的树，把代价摊给之前的操作。

### 双旋规则

只用单旋（每次把 x 转到父亲的位置，转到根为止）不行：在一条链上依次访问最深的结点，每次代价 O(n)，总代价仍是 O(n²)。关键是用**双旋**，按 x、父亲 y、祖父 z 的方向关系分两类：

![Splay 的 zig-zig 和 zig-zag：同向先转父亲再转自己，异向把自己转两次](/qmx-Gameknowledge/assets/algo/c4-10-splay-rotate.svg)

- **同向（zig-zig）**：x 和 y 都是左孩子（或都是右孩子）。先旋转 y，再旋转 x。这一步把路径压扁，是均摊分析成立的关键。
- **异向（zig-zag）**：x 是 y 的右孩子而 y 是 z 的左孩子（或相反）。把 x 连续旋转两次。
- 只剩父亲没有祖父时，旋转 x 一次（zig）。

均摊分析用势能法：以子树大小的对数之和为势能，每次 splay 的均摊代价是 O(log n)（见 0.4）。所以任意 m 次操作总代价是 O(m log n)，但**单次**操作可能达到 O(n)。

### 代码

结点存键值 `key`、重复个数 `cnt` 和子树大小 `sz`。`rotate` 先判断 x 是父亲的哪一侧，再统一处理；`splay` 里的 `dir(x) == dir(f)` 就是同向判断。

```cpp
#include <bits/stdc++.h>
using namespace std;

// Splay：每次访问结点 x，就把 x 旋转到根。可重复元素用 cnt 记录个数。
const int N = 100005;
int ch[N][2], fa[N], key[N], cnt[N], sz[N], tot, root;

void pull(int x) { sz[x] = sz[ch[x][0]] + sz[ch[x][1]] + cnt[x]; }
int dir(int x) { return ch[fa[x]][1] == x; }     // x 是父亲的哪个孩子

void rotate(int x) {
    int y = fa[x], z = fa[y], k = dir(x);
    ch[y][k] = ch[x][k ^ 1];
    if (ch[x][k ^ 1]) fa[ch[x][k ^ 1]] = y;
    ch[x][k ^ 1] = y;
    fa[y] = x;
    fa[x] = z;
    if (z) ch[z][ch[z][1] == y] = x;
    pull(y);
    pull(x);
}
// 把 x 伸展到根：同向用 zig-zig（先转父亲），异向用 zig-zag（转两次 x）
void splay(int x) {
    for (int f; (f = fa[x]); rotate(x)) {
        if (fa[f]) rotate(dir(x) == dir(f) ? f : x);
    }
    root = x;
}
int newNode(int k, int f) {
    ++tot;
    key[tot] = k;
    cnt[tot] = sz[tot] = 1;
    ch[tot][0] = ch[tot][1] = 0;
    fa[tot] = f;
    return tot;
}

void insert(int k) {
    if (!root) { root = newNode(k, 0); return; }
    int cur = root, f = 0;
    while (true) {
        if (key[cur] == k) { cnt[cur]++; pull(cur); splay(cur); return; }
        f = cur;
        cur = ch[f][key[f] < k];
        if (!cur) {
            cur = newNode(k, f);
            ch[f][key[f] < k] = cur;
            pull(f);
            splay(cur);
            return;
        }
    }
}
// 找到值为 k 的结点并伸展到根；不存在则把最后访问的结点伸展上来，返回 0
int find(int k) {
    int cur = root, last = 0;
    while (cur && key[cur] != k) {
        last = cur;
        cur = ch[cur][key[cur] < k];
    }
    if (cur) { splay(cur); return cur; }
    if (last) splay(last);
    return 0;
}
void erase(int k);
int rankOf(int k) {                      // 比 k 小的个数 + 1
    insert(k);                           // 先插入，k 到根，左子树就是所有更小的
    int r = sz[ch[root][0]] + 1;
    erase(k);                            // 再撤销（erase 在下面定义，先声明）
    return r;
}
int kth(int k) {                         // 第 k 小，要求 1 <= k <= sz[root]
    int cur = root;
    while (true) {
        if (k <= sz[ch[cur][0]]) cur = ch[cur][0];
        else if (k <= sz[ch[cur][0]] + cnt[cur]) { splay(cur); return key[cur]; }
        else k -= sz[ch[cur][0]] + cnt[cur], cur = ch[cur][1];
    }
}
void erase(int k) {                      // 删除一个 k（不存在则什么也不做）
    int x = find(k);
    if (!x) return;
    if (cnt[x] > 1) { cnt[x]--; pull(x); return; }
    int l = ch[x][0], r = ch[x][1];
    if (!l || !r) { root = l | r; fa[root] = 0; return; }
    int p = l;
    while (ch[p][1]) p = ch[p][1];       // 左子树最大值
    fa[l] = 0; root = l;
    splay(p);                            // 它上到根后没有右孩子，把原右子树接上
    ch[p][1] = r; fa[r] = p; pull(p);
}

int main() {
    for (int x : {5, 3, 8, 3, 10, 1}) insert(x);
    printf("5 的排名 = %d\n", rankOf(5));
    printf("第 3 小 = %d\n", kth(3));
    erase(3);
    int third = kth(3);
    printf("删一个 3 后，第 3 小 = %d，此时根的键 = %d\n", third, key[root]);
    return 0;
}
```

输出：

```text
5 的排名 = 4
第 3 小 = 3
删一个 3 后，第 3 小 = 5，此时根的键 = 5
```

最后一行体现了 Splay 的特点：`kth` 找到结点后把它伸展到了根。

几个必须遵守的细节：

- **查找失败也要 splay**：`find` 里没找到时，把最后访问到的结点伸展上来。否则反复查一个不存在的深结点，每次都是 O(n)。
- **删除**：把要删的结点 x 伸展到根，在左子树里找最大结点 p，把 p 伸展到左子树的根（此时 p 没有右孩子），再把原来的右子树接到 p 的右边。
- **求排名**：这里的做法是"先插入再查，再删除"，简单但多做了两次操作；也可以直接 `find` 之后读左子树大小。
- 自底向上的 `splay` 是迭代的，不会爆栈；但 `find` 之类沿路径向下找的循环要写成循环，不要用递归。

Splay 比 Treap 强的地方是可以做"把某个区间单独切成一棵子树"：把 l-1 伸展到根，再把 r+1 伸展到根的右孩子，那么 r+1 的左子树恰好就是区间 [l, r]。区间翻转、区间加等操作都靠这个技巧加懒标记完成。

## Treap 与 Splay 的选择

| 项目 | Treap（分裂合并） | Splay |
| --- | --- | --- |
| 平衡方式 | 随机优先级 | 访问后旋到根 |
| 复杂度 | 期望 O(log n) | 均摊 O(log n)，单次最坏 O(n) |
| 代码量 | 短，几乎不会写错 | 长，旋转细节多 |
| 常数 | 较小 | 较大 |
| 能做的事 | 排名、第 k 小、区间翻转（序列版） | 同上，另可做 LCT 的基础 |
| 持久化 | 容易（split/merge 不修改旧结点即可） | 困难 |

练习时先把 Treap 写熟；Splay 是 LCT（动态树）的前置，要往那个方向走再学。

## 常见坑

- Treap 优先级用了 `rand()`，在 Windows 下范围只有 32767，会出现大量相同优先级使树变形；用 `mt19937`。
- `split` 的参数用了引用而结点在函数内被改写，要明确 `a`、`b` 是输出参数，传入的 `t` 按值接收。
- 序列版 Treap 在 `split` 和 `merge` 之前忘记下放标记，翻转结果错乱。
- Splay 删除后没处理 `root` 为空的情况，或没把 `fa[root]` 置 0。
- Splay 的 `rotate` 更新 `sz` 的顺序：先更新下面的 y，再更新上面的 x。
- 键值有重复时，Treap 要明确是"允许重复，各占一个结点"，Splay 要用 `cnt` 合并。

## 练习

**入门**

- 洛谷 P3369【模板】普通平衡树（本篇例题，Treap 和 Splay 各写一遍）
- [LeetCode 295 数据流的中位数](https://leetcode.cn/problems/find-median-from-data-stream/)（困难）：可以用堆，也可以用 Treap 练手

**进阶**

- 洛谷 P3391【模板】文艺平衡树（本篇序列版 Treap，另用 Splay 写一次）
- 洛谷 P6136【模板】普通平衡树（数据加强版，注意在线和常数）
- [LeetCode 315 计算右侧小于当前元素的个数](https://leetcode.cn/problems/count-of-smaller-numbers-after-self/)（困难）：Treap 求排名，也可用树状数组

**挑战**

- 用 Splay 的区间切分技巧实现区间翻转加区间求和。
- 给 Treap 加持久化：`split` 和 `merge` 每次复制路径上的结点，使旧版本保持不变。

下一篇：4.11 ⭐线段树合并与动态开点。
