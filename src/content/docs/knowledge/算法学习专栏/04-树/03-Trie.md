---
title: "4.3 Trie：字典树"
description: "用多叉树存字符串集合：插入、查找、前缀统计，以及 01 字典树求最大异或。"
sidebar:
  order: 403
---

> 适用版本：C++17。前置知识：4.1 二叉树遍历，会用数组表示树。

## 要点

- Trie（字典树，前缀树）把一组字符串按字符逐层存进一棵多叉树，**有公共前缀的字符串共用同一条路径**。
- 从根到某个节点的路径就是一个前缀。节点上记录“有多少单词经过这里”和“有多少单词在这里结束”，就能回答单词计数和前缀计数。
- 插入和查找都只与字符串长度 L 有关，是 O(L)，和字符串个数无关。
- 把整数拆成二进制位，每位当作一个字符，就得到 01 Trie，可以在 O(31) 内找到和 x 异或最大的数。
- 缺点是占内存：每个节点要存 26 个孩子指针。

## 结构

![字典树：to、tea、ted、ten、i、in、inn，te 前缀只存一份，绿色节点表示单词结尾](/qmx-Gameknowledge/assets/algo/c4-03-trie.svg)

每条边对应一个字符（图里把字符写在了孩子节点上）。要判断 `tea` 是否在集合里，从根开始依次走 `t`、`e`、`a`，中途无路可走就不存在，走完还要看最后一个节点是不是某个单词的结尾。图里 `te` 能走到，但不是单词；`i` 既是单词，又是 `in`、`inn` 的前缀，所以“走得通”和“是单词”要分开记录。

用数组实现：`ch[u][c]` 表示节点 `u` 沿字符 `c` 到达的孩子编号，0 表示不存在。根是 1 号节点。

## 实现与前缀统计

```cpp
#include <bits/stdc++.h>
using namespace std;

const int N = 100005;                 // 节点数上限：所有单词长度之和 + 1
int ch[N][26], cntPass[N], cntEnd[N], tot = 1;   // 根是 1 号节点

void insert(const string& s) {
    int u = 1;
    cntPass[u]++;                     // 经过该节点的单词数（根也计入，方便查空前缀）
    for (char c : s) {
        int x = c - 'a';
        if (!ch[u][x]) ch[u][x] = ++tot;
        u = ch[u][x];
        cntPass[u]++;
    }
    cntEnd[u]++;                      // 恰好在这里结束的单词数
}

int find(const string& s) {           // 返回路径终点，走不通返回 0
    int u = 1;
    for (char c : s) {
        u = ch[u][c - 'a'];
        if (!u) return 0;
    }
    return u;
}

int countWord(const string& s)   { int u = find(s); return u ? cntEnd[u] : 0; }
int countPrefix(const string& s) { int u = find(s); return u ? cntPass[u] : 0; }

int main() {
    for (string w : {"to", "tea", "ted", "ten", "i", "in", "inn", "tea"}) insert(w);
    printf("%d %d %d\n", countWord("tea"), countWord("te"), countPrefix("te"));
    printf("%d %d %d\n", countPrefix("i"), countPrefix("x"), countPrefix(""));
}
```

```output
2 0 4
3 0 8
```

`tea` 插入了两次，所以 `countWord("tea")` 是 2；`te` 只是前缀，不是单词，结果为 0；以 `te` 开头的有两个 `tea`、一个 `ted`、一个 `ten`，共 4 个。

**复杂度与内存**：插入、查找都是 O(L)。节点数不超过所有单词长度之和加 1，每个节点 26 个 `int`，约 104 字节，一百万个字符大约占 100 MB。字符集更大（大小写加数字共 62 种）时要把第二维开大；字符集很大时改用 `map<char,int>` 或排序后的孩子列表，换取内存。

## 01 Trie：求最大异或

把整数写成 31 位二进制（从高位到低位），每一位当作一个字符，只有 `0`、`1` 两种，就是 01 Trie。

问题：给定一组数，对于给定的 `x`，找出集合中使 `x ^ y` 最大的 `y`。

贪心思路：异或结果的高位权重大于所有低位之和，所以**从高位开始，每一位都尽量走与 `x` 当前位相反的边**，这一位的异或结果就是 1。相反的边不存在才被迫走相同的边。

![01 字典树：集合 {2,5,6}，查询 x=3，每一位尽量走与 x 相反的边，最终到达 5，异或结果为 6](/qmx-Gameknowledge/assets/algo/c4-03-xor-trie.svg)

```cpp
#include <bits/stdc++.h>
using namespace std;

const int N = 1000;                   // 实际使用时开 31 * 数字个数 + 2
int ch[N][2], tot = 1;

void insert(int x) {
    int u = 1;
    for (int b = 30; b >= 0; b--) {   // 从高位到低位；这里假定 x >= 0
        int c = x >> b & 1;
        if (!ch[u][c]) ch[u][c] = ++tot;
        u = ch[u][c];
    }
}

int query(int x) {                    // 返回 x 与集合中某个数的最大异或值
    int u = 1, res = 0;
    for (int b = 30; b >= 0; b--) {
        int c = x >> b & 1;
        if (ch[u][c ^ 1]) {           // 有相反的边：这一位异或得 1
            res |= 1 << b;
            u = ch[u][c ^ 1];
        } else {
            u = ch[u][c];
        }
    }
    return res;
}

int main() {
    vector<int> a = {3, 10, 5, 25, 2, 8};
    for (int x : a) insert(x);
    int best = 0;
    for (int x : a) best = max(best, query(x));   // 数组内任意两数异或的最大值
    printf("%d\n", best);

    memset(ch, 0, sizeof ch); tot = 1;
    for (int x : {2, 5, 6}) insert(x);
    printf("%d\n", query(3));         // 对应上图
}
```

```output
28
6
```

第一个答案是 `5 ^ 25 = 28`，即 [LeetCode 421](https://leetcode.cn/problems/maximum-xor-of-two-numbers-in-an-array/)。每次插入和查询都走 31 步，处理 n 个数总共 O(31n)，比两两枚举的 O(n²) 快得多。

## 例题

### 例 1：点名（洛谷 P2580 类型）

先给 n 个名字，再有 m 次点名：名字不在名单里输出 `WRONG`，第一次点到输出 `OK`，之前已经点过输出 `REPEAT`。用 Trie 存名单，用节点上的 `cntEnd` 同时当作“是否点过”的标记：

```cpp
#include <bits/stdc++.h>
using namespace std;

const int N = 100005;
int ch[N][26], tot = 1;
int state[N];                         // 0：不是名字；1：是名字，没点过；2：已点过

int main() {
    int n, m;
    cin >> n;
    for (int i = 0; i < n; i++) {
        string s; cin >> s;
        int u = 1;
        for (char c : s) {
            if (!ch[u][c - 'a']) ch[u][c - 'a'] = ++tot;
            u = ch[u][c - 'a'];
        }
        state[u] = 1;
    }
    cin >> m;
    while (m--) {
        string s; cin >> s;
        int u = 1;
        for (char c : s) { u = ch[u][c - 'a']; if (!u) break; }
        if (!u || !state[u]) puts("WRONG");
        else if (state[u] == 1) { puts("OK"); state[u] = 2; }
        else puts("REPEAT");
    }
}
```

```input
3
alice
bob
carol
4
bob
bob
dave
carol
```

```output
OK
REPEAT
WRONG
OK
```

用 `map<string,int>` 也能做，但 Trie 查找与名字个数无关，且天然支持前缀题型，适合记住这个模板。

## 常见坑

- 数组大小：节点数上限是所有字符串总长度加 1，不是字符串个数。
- 多组数据时，不要每次 `memset` 整个大数组。只需要把 `tot` 复位，并在新建节点时顺手清空它的孩子。
- 区分“路径存在”和“单词结尾”，否则 `te` 会被误判为单词。
- 字符集比小写字母多时，下标要先做映射，不能直接用 `c - 'a'`。
- 01 Trie 的位数要覆盖所有输入：数值小于 2^30 时从第 29 位开始；负数需要先做偏移。

## 练习

**入门**

- [LeetCode 14 最长公共前缀](https://leetcode.cn/problems/longest-common-prefix/)（简单）：既能用逐列比较，也能用 Trie。
- [LeetCode 208 实现 Trie (前缀树)](https://leetcode.cn/problems/implement-trie-prefix-tree/)（中等）：本篇模板。

**进阶**

- [LeetCode 648 单词替换](https://leetcode.cn/problems/replace-words/)（中等）。
- LeetCode 211 添加与搜索单词 - 数据结构设计：带通配符 `.` 的查找，用 DFS 加 Trie。
- [LeetCode 421 数组中两个数的最大异或值](https://leetcode.cn/problems/maximum-xor-of-two-numbers-in-an-array/)（中等）：01 Trie。
- 洛谷 P2580 于是他错误的点名开始了。

**挑战**

- LeetCode 212 单词搜索 II：Trie 加回溯。
- 洛谷 P4551 最长异或路径：先用 4.4 的 DFS 算出每个点到根的异或值，再套 01 Trie。
- LeetCode 1707 与数组中元素的最大异或值：离线排序后分批插入。

下一篇：4.4 一般树与树的直径。

