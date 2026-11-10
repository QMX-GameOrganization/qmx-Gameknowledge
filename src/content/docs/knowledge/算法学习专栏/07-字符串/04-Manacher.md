---
title: "7.4 ⭐Manacher：线性求所有回文半径"
description: "插入分隔符统一奇偶回文，用镜像复用已知半径，在 O(n) 内求出以每个位置为中心的最长回文。"
sidebar:
  order: 704
  badge:
    text: 进阶
    variant: caution
---

> 适用版本：C++17。前置知识：回文串的概念；7.3 Z 函数里的“窗口复用”思想对理解本篇有帮助。**什么时候学**：题目要求“以每个位置为中心的最长回文”“回文子串总数”“最长回文子串”并且 n 达到 10^5 以上时。n 在几千以内，中心扩展 O(n²) 就够了。

## 要点

- 朴素的中心扩展，对 `aaaa…a` 这类串是 O(n²)。
- 在字符之间和两端插入分隔符 `#`，所有回文长度都变成奇数，不用再分奇偶讨论。
- 维护当前覆盖最靠右的回文 `[c - p[c] + 1, r)`。新位置 i 在它里面时，镜像点 `2c - i` 的半径可以直接借用。
- 时间 O(n)，原串回文长度 = `p[i] - 1`。

## 分隔符技巧

回文有奇偶两种：`aba` 的中心是一个字符，`abba` 的中心在两个字符之间。在每个字符两侧都插入 `#`：

```
s = abaaba
t = #a#b#a#a#b#a#
```

此时 t 里的任何回文都以某个字符为中心：原串的奇回文，中心是字母；原串的偶回文，中心是 `#`。

![abaaba 变换后的串及 p 数组：p[6]=7，对应原串长度 6 的回文](/qmx-Gameknowledge/assets/algo/c7-manacher-transform.svg)

定义 `p[i]` 为 t 中以 i 为中心的最大回文**半径**（包含中心自己，所以至少为 1）。则回文覆盖 `t[i - p[i] + 1 .. i + p[i] - 1]`，这个区间的长度是 `2·p[i] - 1`，其中 `#` 比字母多一个，所以对应的**原串回文长度是 `p[i] - 1`**，起点是 `(i - p[i] + 1) / 2`。

## 镜像复用

设当前找到的、右端最靠右的回文中心是 c，半径 `p[c]`，右边界（不含）`r = c + p[c]`。处理新位置 i：

- 如果 `i < r`，i 在这个大回文内部。大回文关于 c 对称，所以 i 关于 c 的镜像点是 `j = 2c - i`，且 `p[i] >= min(p[j], r - i)` 一定成立：镜像点那边的回文，在大回文范围内，会原样出现在 i 这边。因此直接令 `p[i] = min(p[j], r - i)`。
- 在此基础上继续尝试往两边扩展。
- 如果 `i + p[i] > r`，更新 `c = i, r = i + p[i]`。

![以 c=6 为中心的大回文内，i=9 的镜像点是 j=3：p[3]=4 且 r-i=4，所以 p[9] 初值就是 4](/qmx-Gameknowledge/assets/algo/c7-manacher-mirror.svg)

真正需要往外比较的只有两种情形：i 不在大回文内部（`i >= r`），或者 `p[j]` 恰好等于 `r - i`，此时镜像回文刚好顶到大回文的边界，边界之外的字符没有比较过。如果 `p[j] < r - i`，则 `p[i] = p[j]`；如果 `p[j] > r - i`，则 `p[i] = r - i`，两种情形的答案都已精确，扩展循环的第一次比较就会失败。每次成功的比较都会让 r 增大，所以总比较次数不超过 t 的长度 2n + 1，整个算法 O(n)。

## 代码

```cpp
#include <bits/stdc++.h>
using namespace std;

// 在每个字符两侧插入 '#'，奇偶回文统一成奇回文。
// 返回 p：p[i] = 变换串 t 中以 i 为中心的最大回文半径（含中心），
// 对应的原串回文长度恰好是 p[i] - 1。
vector<int> manacher(const string& s, string& t) {
    t = "#";
    for (char c : s) { t += c; t += '#'; }
    int n = t.size();
    vector<int> p(n, 1);
    int c = 0, r = 0;                            // 右边界最靠右的回文：中心 c，覆盖 [c-p[c]+1, r)，r = c + p[c]
    for (int i = 0; i < n; i++) {
        if (i < r) p[i] = min(r - i, p[2 * c - i]);        // 镜像点 2c-i 的半径，且不超过 r
        while (i - p[i] >= 0 && i + p[i] < n && t[i - p[i]] == t[i + p[i]]) p[i]++;
        if (i + p[i] > r) { c = i; r = i + p[i]; }
    }
    return p;
}

// 最长回文子串
string longestPalindrome(const string& s) {
    string t;
    vector<int> p = manacher(s, t);
    int best = 0, center = 0;
    for (int i = 0; i < (int)p.size(); i++)
        if (p[i] - 1 > best) { best = p[i] - 1; center = i; }
    int start = (center - p[center] + 1) / 2;    // 变换串下标 -> 原串下标
    return s.substr(start, best);
}

// 回文子串个数（按位置区分）：每个中心贡献 p[i] / 2 个
long long countPalindromes(const string& s) {
    string t;
    vector<int> p = manacher(s, t);
    long long total = 0;
    for (int x : p) total += x / 2;
    return total;
}

int main() {
    string s = "abaaba";
    string t;
    vector<int> p = manacher(s, t);
    cout << "t = " << t << "\np = ";
    for (int x : p) cout << x << ' ';
    cout << "\n";
    cout << "最长回文子串: " << longestPalindrome("babad") << "\n";
    cout << "最长回文子串: " << longestPalindrome("cbbd") << "\n";
    cout << "abaaba 的回文子串个数: " << countPalindromes(s) << "\n";
    return 0;
}
```

运行结果：

```text
t = #a#b#a#a#b#a#
p = 1 2 1 4 1 2 7 2 1 4 1 2 1 
最长回文子串: bab
最长回文子串: bb
abaaba 的回文子串个数: 11
```

`countPalindromes` 里每个中心贡献 `p[i] / 2` 个回文子串。t 中的回文要对应原串里的一个完整子串，两端必须落在 `#` 上。中心是字母时，`p[i]` 是偶数，合法半径是 2, 4, …, `p[i]`，共 `p[i] / 2` 个；中心是 `#` 时，`p[i]` 是奇数，合法半径是 3, 5, …, `p[i]`（半径 1 对应空串，不计），共 `(p[i] - 1) / 2` 个，等于整数除法 `p[i] / 2`。`abaaba` 一共有 11 个回文子串，与输出一致。

## 例题

### 例：最短回文串（LeetCode 214）

题目链接：[LeetCode 214 最短回文串](https://leetcode.cn/problems/shortest-palindrome/)。只能在串首添加字符，把 s 变成回文，求最短的结果。

思路：设 s 的最长回文前缀长度为 L，那么剩下的后缀 `s[L..]` 反转后补到前面，就得到最短的回文串。问题化为求最长回文前缀。在 Manacher 里，回文前缀对应的中心 i 满足 `i - p[i] + 1 == 0`（回文左端碰到 t 的起点），此时原串长度是 `p[i] - 1`，取最大值。

```cpp
#include <bits/stdc++.h>
using namespace std;

// 在每个字符两侧插入 '#'，奇偶回文统一成奇回文。
// 返回 p：p[i] = 变换串 t 中以 i 为中心的最大回文半径（含中心），
// 对应的原串回文长度恰好是 p[i] - 1。
vector<int> manacher(const string& s, string& t) {
    t = "#";
    for (char c : s) { t += c; t += '#'; }
    int n = t.size();
    vector<int> p(n, 1);
    int c = 0, r = 0;                            // 右边界最靠右的回文：中心 c，覆盖 [c-p[c]+1, r)，r = c + p[c]
    for (int i = 0; i < n; i++) {
        if (i < r) p[i] = min(r - i, p[2 * c - i]);        // 镜像点 2c-i 的半径，且不超过 r
        while (i - p[i] >= 0 && i + p[i] < n && t[i - p[i]] == t[i + p[i]]) p[i]++;
        if (i + p[i] > r) { c = i; r = i + p[i]; }
    }
    return p;
}

// 最长回文子串
string longestPalindrome(const string& s) {
    string t;
    vector<int> p = manacher(s, t);
    int best = 0, center = 0;
    for (int i = 0; i < (int)p.size(); i++)
        if (p[i] - 1 > best) { best = p[i] - 1; center = i; }
    int start = (center - p[center] + 1) / 2;    // 变换串下标 -> 原串下标
    return s.substr(start, best);
}

// 回文子串个数（按位置区分）：每个中心贡献 p[i] / 2 个
long long countPalindromes(const string& s) {
    string t;
    vector<int> p = manacher(s, t);
    long long total = 0;
    for (int x : p) total += x / 2;
    return total;
}

// LeetCode 214：只能在串首添加字符，让 s 变成回文，求最短的结果
int main() {
    string s;
    cin >> s;
    string t;
    vector<int> p = manacher(s, t);
    int best = 0;                                    // 最长回文前缀的长度
    for (int i = 0; i < (int)p.size(); i++)
        if (i - p[i] + 1 == 0) best = max(best, p[i] - 1);   // 回文左端碰到 t 的开头
    string add = s.substr(best);                     // 剩下的后缀反转后补到前面
    reverse(add.begin(), add.end());
    cout << add + s << "\n";
    return 0;
}
```

示例（最长回文前缀是 `aacecaa`，只需要把剩下的 `a` 补到串首）：

输入：

```text
aacecaaa
```

输出：

```text
aaacecaaa
```

## 适用与不适用

- 适用：所有位置的最长回文半径、最长回文子串、回文子串个数、需要“某个区间是否是回文”的预处理（对区间 `[l, r]`，取中心的 p 值，判断半径是否够大）。
- 不适用：需要统计**本质不同**的回文子串个数时（用回文自动机，7.7）；回文带“允许改 k 个字符”之类的变形，需要哈希加二分。
- 哈希加二分也能求最长回文半径，复杂度 O(n log n)，写法更直接，但需要正反各一套哈希。

## 常见坑

- **分隔符与字符冲突**：本文用 `#`，要保证它不出现在原串里。
- **半径的定义**：`p[i]` 包含中心，所以长度是 `p[i] - 1`，容易写成 `p[i]`。
- **越界**：扩展循环里要同时判断 `i - p[i] >= 0` 和 `i + p[i] < n`，或者在 t 两端加上不同的哨兵字符（如 `^` 和 `$`）省去判断。
- 起点公式 `(i - p[i] + 1) / 2` 使用整数除法，推导时先确认左端点落在 `#` 上（偶数下标）。

## 练习

**入门**

- [LeetCode 5 最长回文子串](https://leetcode.cn/problems/longest-palindromic-substring/)（中等）
- [LeetCode 647 回文子串](https://leetcode.cn/problems/palindromic-substrings/)（中等）

**进阶**

- [LeetCode 214 最短回文串](https://leetcode.cn/problems/shortest-palindrome/)（困难，本文例题）
- 洛谷 P3805 【模板】manacher

**挑战**

- 洛谷 P4555 [国家集训队] 最长双回文串
- 洛谷 P1659 [国家集训队] 拉拉队排练

下一篇：7.5 ⭐AC 自动机：多模式串匹配。
