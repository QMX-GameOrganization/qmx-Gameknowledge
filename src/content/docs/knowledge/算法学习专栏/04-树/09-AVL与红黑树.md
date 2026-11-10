---
title: "4.9 ⭐AVL 与红黑树"
description: "为什么二叉搜索树需要自平衡，旋转如何不破坏中序，AVL 的四种失衡情形，以及红黑树的性质和插入修复。"
sidebar:
  order: 409
  badge:
    text: 进阶
    variant: caution
---

> 适用版本：C++17。前置：4.2 二叉搜索树（知道 BST 顺序插入会退化成链）。什么时候需要学它：想弄清 `std::set` / `std::map` 为什么能保证 O(log n)，或者面试、考试里要求讲出平衡树的原理。做题时直接用 `set` / `map` 即可，一般不需要手写 AVL 或红黑树。

## 要点

- 二叉搜索树的操作代价是树高。顺序插入 1..n 会得到高度为 n 的链，平衡树通过在修改时调整形状，把树高控制在 O(log n)。
- **旋转**只改变结点之间的连接，不改变中序序列，所以旋转之后仍然是合法的二叉搜索树。
- **AVL 树**要求每个结点左右子树高度差不超过 1，失衡时用单旋或双旋修复，树最矮，查找最快。
- **红黑树**用颜色规则代替高度差，规则更松，树高不超过 2·log2(n+1)，插入和删除时旋转次数更少。`std::set` 与 `std::map` 的常见实现就是红黑树。
- 本篇手写 AVL 的插入删除，红黑树只写插入（理解修复情形比背删除代码更有价值）。

## 为什么需要平衡

二叉搜索树的查找、插入、删除都沿着一条从根往下的路径走，代价是树高 h。随机数据下 h 大约是 O(log n)，但如果输入本身有序，每次都插到最右边，树就退化成一条链，h = n。

平衡树的做法是：每次插入或删除之后，检查有没有哪里"过高"，有的话就局部调整，让树高始终是 O(log n)。调整用到的唯一工具就是旋转。

## 旋转

![右旋 rotR(y)：y 的左孩子 x 升到根，x 的右子树 B 转给 y；中序始终是 A x B y C](/qmx-Gameknowledge/assets/algo/c4-09-rotate.svg)

右旋 `rotR(y)` 做三件事：

1. x = y 的左孩子。
2. x 的右子树 B 变成 y 的左子树。
3. y 变成 x 的右孩子，x 代替 y 的位置。

B 里的键值都在 x 和 y 之间，所以挂到 y 的左边仍然满足"左小右大"。左旋是镜像。旋转只改常数个指针，代价 O(1)。

## AVL 树

**定义**：每个结点的左右子树高度之差（平衡因子）的绝对值不超过 1。

**高度上界**：设高度为 h 的 AVL 树最少有 N(h) 个结点。根的两棵子树高度分别至少是 h-1 和 h-2，所以 N(h) = N(h-1) + N(h-2) + 1，和斐波那契数列同阶，增长是指数级的。反过来，n 个结点的 AVL 树高度不超过约 1.44·log2(n+2)，所以操作都是 O(log n)。

### 四种失衡情形

插入或删除之后，沿着回溯路径找到最低的失衡结点（平衡因子变成 ±2），按"重的一侧"和"重孙在哪一边"分四类：

![AVL 失衡的四种情形 LL、RR、LR、RL，以及各自的修复旋转](/qmx-Gameknowledge/assets/algo/c4-09-avl-cases.svg)

| 情形 | 含义 | 修复 |
| --- | --- | --- |
| LL | 左孩子的左子树偏高 | 对失衡结点右旋 |
| RR | 右孩子的右子树偏高 | 对失衡结点左旋 |
| LR | 左孩子的右子树偏高 | 先对左孩子左旋（变成 LL），再对失衡结点右旋 |
| RL | 右孩子的左子树偏高 | 先对右孩子右旋（变成 RR），再对失衡结点左旋 |

判断时看两个平衡因子：失衡结点的平衡因子 > 1 说明左边高，此时左孩子的平衡因子 < 0 就是 LR，否则是 LL；右边同理。

### 代码

每个结点存高度 `h`。`fix` 在回溯时被每一层调用：先更新高度，再检查平衡因子。

```cpp
#include <bits/stdc++.h>
using namespace std;

// AVL 树：每个结点记录以它为根的子树高度 h，平衡因子 = 左高 - 右高，要求 |平衡因子| <= 1
struct Node {
    int key, h;
    Node *l, *r;
    explicit Node(int k) : key(k), h(1), l(nullptr), r(nullptr) {}
};

int H(Node* t) { return t ? t->h : 0; }
void upd(Node* t) { t->h = max(H(t->l), H(t->r)) + 1; }
int bal(Node* t) { return H(t->l) - H(t->r); }

// 右旋：y 的左孩子 x 上来，x 的右子树挂到 y 的左边（中序不变）
Node* rotR(Node* y) {
    Node* x = y->l;
    y->l = x->r;
    x->r = y;
    upd(y);
    upd(x);
    return x;
}
// 左旋：与右旋镜像
Node* rotL(Node* x) {
    Node* y = x->r;
    x->r = y->l;
    y->l = x;
    upd(x);
    upd(y);
    return y;
}

// 更新 t 的高度；若失衡就按 LL / LR / RR / RL 四种情形旋转，返回新的子树根
Node* fix(Node* t) {
    upd(t);
    int b = bal(t);
    if (b > 1) {                         // 左边太高
        if (bal(t->l) < 0) t->l = rotL(t->l);   // LR：先把左孩子转成 LL
        return rotR(t);
    }
    if (b < -1) {                        // 右边太高
        if (bal(t->r) > 0) t->r = rotR(t->r);   // RL：先把右孩子转成 RR
        return rotL(t);
    }
    return t;
}

Node* insert(Node* t, int k) {
    if (!t) return new Node(k);
    if (k < t->key) t->l = insert(t->l, k);
    else if (k > t->key) t->r = insert(t->r, k);
    else return t;                       // 已存在，忽略
    return fix(t);
}

Node* erase(Node* t, int k) {
    if (!t) return t;
    if (k < t->key) t->l = erase(t->l, k);
    else if (k > t->key) t->r = erase(t->r, k);
    else {
        if (!t->l || !t->r) {            // 至多一个孩子：直接用孩子顶替
            Node* c = t->l ? t->l : t->r;
            delete t;
            return c;
        }
        Node* m = t->r;                  // 两个孩子：用右子树最小值（后继）替换
        while (m->l) m = m->l;
        t->key = m->key;
        t->r = erase(t->r, m->key);
    }
    return fix(t);
}

void inorder(Node* t, vector<int>& out) {
    if (!t) return;
    inorder(t->l, out);
    out.push_back(t->key);
    inorder(t->r, out);
}

int main() {
    Node* root = nullptr;
    for (int i = 1; i <= 7; i++) root = insert(root, i);   // 顺序插入：普通 BST 会退化成链
    printf("插入 1..7 后高度 = %d，根 = %d\n", H(root), root->key);
    root = erase(root, 4);
    vector<int> v;
    inorder(root, v);
    printf("删除 4 后中序：");
    for (int x : v) printf("%d ", x);
    printf("\n高度 = %d\n", H(root));
    return 0;
}
```

运行结果：

```text
插入 1..7 后高度 = 3，根 = 4
删除 4 后中序：1 2 3 5 6 7 
高度 = 3
```

顺序插入 1..7 时，每次插入都触发右边偏高（RR），自动左旋，最后根是 4，和手算一致。

删除时，如果被删结点有两个孩子，就用右子树最小结点（后继）的值覆盖它，再到右子树里删那个后继。回溯途中同样调用 `fix`。插入最多触发一次修复（一次单旋或双旋后整棵树恢复平衡），删除可能沿路径多处触发，但总共仍是 O(log n)。

### 对比：普通 BST 与 AVL 的树高

下面这段接在上面 AVL 代码的函数之后（替换其 `main`），顺序插入 1..1000：

```cpp
// 接在 avl.cpp 的函数定义之后，替换原来的 main
// 对比：顺序插入 1..n，普通 BST 与 AVL 的树高
struct B { int key; B *l, *r; explicit B(int k) : key(k), l(nullptr), r(nullptr) {} };
B* bstInsert(B* t, int k) {
    if (!t) return new B(k);
    B** p = &t;                          // 用二级指针迭代插入，避免递归爆栈
    while (*p) p = k < (*p)->key ? &(*p)->l : &(*p)->r;
    *p = new B(k);
    return t;
}
int bstHeight(B* t) {                    // 迭代求高度（层序）
    if (!t) return 0;
    int h = 0;
    vector<B*> cur{t};
    while (!cur.empty()) {
        vector<B*> nxt;
        for (B* x : cur) {
            if (x->l) nxt.push_back(x->l);
            if (x->r) nxt.push_back(x->r);
        }
        cur.swap(nxt);
        h++;
    }
    return h;
}

int main() {
    int n = 1000;
    B* b = nullptr;
    Node* a = nullptr;
    for (int i = 1; i <= n; i++) {
        b = bstInsert(b, i);
        a = insert(a, i);
    }
    printf("顺序插入 1..%d\n普通 BST 高度 = %d\nAVL 高度 = %d\n", n, bstHeight(b), H(a));
    return 0;
}
```

输出：

```text
顺序插入 1..1000
普通 BST 高度 = 1000
AVL 高度 = 10
```

## 红黑树

AVL 要求高度差不超过 1，每次修改都可能触发较多旋转。红黑树放宽了条件：只要求"最长路径不超过最短路径的两倍"，用颜色来表达。

### 四条性质

![一棵合法的红黑树及其四条性质，黑高为 2](/qmx-Gameknowledge/assets/algo/c4-09-rb-example.svg)

1. 每个结点是红色或黑色。
2. 根是黑色。
3. 红结点的孩子都是黑色（不能连续两个红）。
4. 从任一结点到它下面所有空位置（NIL）的路径，经过的黑结点数相同，这个数叫**黑高**。

**为什么树高是 O(log n)**：设根的黑高为 b。性质 4 保证前 b 层是满的，所以至少有 2^b - 1 个结点，即 b ≤ log2(n+1)。性质 3 保证一条路径上红结点不会相邻，红结点最多和黑结点一样多，所以树高 h ≤ 2b ≤ 2·log2(n+1)。

### 插入与修复

新结点先按 BST 规则插入，**染成红色**。染红的好处是不会破坏性质 4（黑高不变），只可能违反性质 2（新结点是根）或性质 3（父亲也是红）。性质 2 最后把根染黑即可。

父亲 p 是红色时，p 一定不是根（根是黑色），所以祖父 g 存在且是黑色。看叔叔 u 的颜色（空指针算黑）：

![红黑树插入修复的三种情形：叔叔红只染色，叔叔黑且 z 是内侧孩子先旋转，叔叔黑且 z 是外侧孩子染色后旋转](/qmx-Gameknowledge/assets/algo/c4-09-rb-insert.svg)

- **情形 1（叔叔红）**：p、u 染黑，g 染红。g 的黑高不变，但 g 变红后可能和它的父亲冲突，所以把 g 当作新的 z 继续向上检查。
- **情形 2（叔叔黑，z 是内侧孩子）**：对 p 旋转，让两个红结点排在同一侧，变成情形 3。
- **情形 3（叔叔黑，z 是外侧孩子）**：p 染黑，g 染红，对 g 向另一侧旋转。子树根变黑，黑高不变，结束。

情形 1 可能连续发生并一路上移，但每次只是染色；情形 2、3 合起来最多旋转两次，之后不再继续。所以插入的旋转次数是 O(1)，总代价 O(log n)。

### 代码（插入）

```cpp
#include <bits/stdc++.h>
using namespace std;

// 红黑树插入（不含删除）。性质：
// 1) 结点红或黑  2) 根是黑  3) 红结点的孩子都是黑（不能连续两个红）
// 4) 任一结点到其后代空指针的所有路径，经过的黑结点数相同（黑高相等）
struct Node {
    int key;
    bool red;
    Node *l, *r, *p;
    explicit Node(int k) : key(k), red(true), l(nullptr), r(nullptr), p(nullptr) {}  // 新结点先染红
};
Node* root = nullptr;

void rotL(Node* x) {
    Node* y = x->r;
    x->r = y->l;
    if (y->l) y->l->p = x;
    y->p = x->p;
    if (!x->p) root = y;
    else if (x == x->p->l) x->p->l = y;
    else x->p->r = y;
    y->l = x;
    x->p = y;
}
void rotR(Node* x) {
    Node* y = x->l;
    x->l = y->r;
    if (y->r) y->r->p = x;
    y->p = x->p;
    if (!x->p) root = y;
    else if (x == x->p->l) x->p->l = y;
    else x->p->r = y;
    y->r = x;
    x->p = y;
}

// 新结点 z 为红，只可能违反性质 2 或 3。z 的父亲是红色时就要修复
void fixInsert(Node* z) {
    while (z->p && z->p->red) {
        Node* g = z->p->p;               // 父亲是红，所以父亲不是根，祖父一定存在
        if (z->p == g->l) {
            Node* u = g->r;              // 叔叔
            if (u && u->red) {           // 情形 1：叔叔红 —— 父、叔变黑，祖父变红，问题上移
                z->p->red = false;
                u->red = false;
                g->red = true;
                z = g;
            } else {                     // 叔叔黑（或空）
                if (z == z->p->r) {      // 情形 2：z 是右孩子（LR）—— 先左旋成情形 3
                    z = z->p;
                    rotL(z);
                }
                z->p->red = false;       // 情形 3：（LL）父染黑，祖父染红，对祖父右旋
                z->p->p->red = true;
                rotR(z->p->p);
            }
        } else {                         // 镜像
            Node* u = g->l;
            if (u && u->red) {
                z->p->red = false;
                u->red = false;
                g->red = true;
                z = g;
            } else {
                if (z == z->p->l) {
                    z = z->p;
                    rotR(z);
                }
                z->p->red = false;
                z->p->p->red = true;
                rotL(z->p->p);
            }
        }
    }
    root->red = false;                   // 性质 2：根永远染黑
}

void insert(int k) {
    Node *y = nullptr, *x = root;
    while (x) {
        y = x;
        if (k == x->key) return;         // 已存在
        x = k < x->key ? x->l : x->r;
    }
    Node* z = new Node(k);
    z->p = y;
    if (!y) root = z;
    else if (k < y->key) y->l = z;
    else y->r = z;
    fixInsert(z);
}

void inorder(Node* t, vector<int>& out) {
    if (!t) return;
    inorder(t->l, out);
    out.push_back(t->key);
    inorder(t->r, out);
}

int height(Node* t) { return t ? 1 + max(height(t->l), height(t->r)) : 0; }

int main() {
    for (int i = 1; i <= 15; i++) insert(i);     // 顺序插入 1..15
    vector<int> v;
    inorder(root, v);
    printf("中序是否有序：%s\n", is_sorted(v.begin(), v.end()) ? "是" : "否");
    printf("结点数 15，树高 %d（完全平衡是 4，红黑树上界 2*log2(n+1) = 8）\n", height(root));
    printf("根 = %d，颜色 = %s\n", root->key, root->red ? "红" : "黑");
    return 0;
}
```

运行结果：

```text
中序是否有序：是
结点数 15，树高 6（完全平衡是 4，红黑树上界 2*log2(n+1) = 8）
根 = 4，颜色 = 黑
```

红黑树的树高允许比完全平衡高一些（这里是 6 对 4），这是它换来更少旋转的代价。

**删除**：删除黑结点会让一条路径少一个黑结点，需要处理"双黑"，分兄弟红、兄弟黑且侄子红/黑等 4 种情形，最多旋转 3 次。逻辑比插入长很多，面试通常只问思路，这里不展开。

## AVL 与红黑树对比

| 项目 | AVL | 红黑树 |
| --- | --- | --- |
| 平衡条件 | 左右高度差 <= 1 | 颜色规则，最长路径 <= 2 倍最短路径 |
| 树高 | 约 1.44·log2 n | 最多 2·log2 n |
| 查找 | 略快（树更矮） | 略慢 |
| 插入旋转 | 最多 2 次（一次单旋或双旋） | 最多 2 次 |
| 删除旋转 | 可能 O(log n) 次 | 最多 3 次 |
| 额外存储 | 高度或平衡因子 | 1 位颜色 |
| 典型使用 | 查询多、修改少的场景 | `std::set`、`std::map`、Java `TreeMap` |

## 例题

### 例 1：验证平衡

给定一棵二叉树，判断它是不是高度平衡的（每个结点左右子树高度差不超过 1）。这就是 AVL 的平衡条件，后序遍历自底向上同时算高度即可：

```cpp
#include <bits/stdc++.h>
using namespace std;

struct TreeNode {
    int val;
    TreeNode *left, *right;
    explicit TreeNode(int v) : val(v), left(nullptr), right(nullptr) {}
};

// 返回子树高度；若子树不平衡返回 -1，一路向上传递，整个过程 O(n)
int check(TreeNode* t) {
    if (!t) return 0;
    int l = check(t->left);
    if (l < 0) return -1;
    int r = check(t->right);
    if (r < 0 || abs(l - r) > 1) return -1;
    return max(l, r) + 1;
}

int main() {
    TreeNode a(1), b(2), c(3);
    a.left = &b;
    b.left = &c;                         // 1 -> 2 -> 3 的左斜链，不平衡
    printf("链：%s\n", check(&a) >= 0 ? "平衡" : "不平衡");
    b.left = nullptr;
    a.right = &c;                        // 1 有左孩子 2 和右孩子 3
    printf("三角：%s\n", check(&a) >= 0 ? "平衡" : "不平衡");
    return 0;
}
```

输出：

```text
链：不平衡
三角：平衡
```

## 常见坑

- 旋转之后忘记更新高度，且更新顺序错了：旋转时先更新下面的（原来的根），再更新上面的（新根）。
- AVL 双旋写成了两次同向旋转：LR 是先左旋再右旋，两次方向相反。
- 红黑树插入时没处理"根被染红"：循环结束后必须把根染黑。
- 把红黑树的"黑高相同"理解成"左右子树高度相同"。红黑树的高度可以相差很多，黑结点数才相等。
- 递归插入深度是树高，平衡树下很安全；但普通 BST 在有序输入下递归会爆栈。

## 练习

**入门**

- LeetCode 110 平衡二叉树
- LeetCode 108 将有序数组转换为二叉搜索树
- LeetCode 98 验证二叉搜索树

**进阶**

- LeetCode 1382 将二叉搜索树变平衡（中序展开再重建）
- 手写 AVL 的 `size` 维护，实现"第 k 小"和"排名"，再对照洛谷 P3369【模板】普通平衡树（需要处理重复值，可在结点里加 cnt）

**挑战**

- 给上面的红黑树补全删除操作，并用 `std::set` 随机对拍；每次操作后检查四条性质。
- 阅读 libstdc++ 的 `_Rb_tree` 实现，对照本篇的三种插入情形。

下一篇：4.10 ⭐Treap 与 Splay。
