---
title: "7.2 KMP：前缀函数与线性匹配"
description: "弄懂前缀函数 pi 的含义和构造过程，用它在线性时间内做单模式串匹配、求最小周期。"
sidebar:
  order: 702
---

> 适用版本：C++17。前置知识：无。这一篇是 7.5 AC 自动机的基础，建议把前缀函数的含义弄透。

## 要点

- **border**：字符串的一个真前缀，同时也是它的后缀。`ababa` 的 border 有 `aba` 和 `a`。
- **前缀函数** `pi[i]`：`s[0..i]` 的最长 border 的长度。其余更短的 border 可以沿 `pi[i] → pi[pi[i]-1] → …` 一路找到。
- KMP 匹配失配时，不回退文本指针，只让“已匹配长度” `j` 沿 border 链回退，总时间 O(n + m)。
- 一个串的最小周期是 `n - pi[n-1]`。

## 朴素匹配慢在哪里

在文本 `text`（长 n）里找模式串 `pat`（长 m）。朴素做法是对每个起点逐字符比较，失配就把起点右移一位、从头比。文本 `aaaa…ab`（n 个字符）里找 `aaab`，几乎每个起点都要比到第 m 个字符才失配，总共 O(nm)。

浪费在哪里：比较过的字符，其实已经告诉了我们很多信息。如果 `pat` 的前 4 个字符已经和文本匹配，第 5 个失配，那么文本这一段的内容是已知的（就是 `pat` 的前 4 个字符），不用再看，可以直接算出模式串应该右移多少。

## 前缀函数与 border

![ababa 的最长 border 是 aba，更短的 border a 是 aba 自己的 border，沿 pi 往回跳就能枚举全部](/qmx-Gameknowledge/assets/algo/c7-kmp-border.svg)

**定义**：`pi[i]` = `s[0..i]` 的最长真前缀的长度，要求这个前缀同时是 `s[0..i]` 的后缀。“真”表示长度小于 i + 1。

例子：`s = aabaaab`，`pi = 0 1 0 1 2 2 3`。比如 `pi[5] = 2`：`s[0..5] = aabaaa`，最长 border 是 `aa`。

> 许多教材把这个数组叫 **next 数组**，且常把它整体右移一位（`next[i]` 是 `s[0..i-1]` 的最长 border，`next[0] = -1`）。两种写法本质相同，本文统一用 `pi`，数组含义一目了然。

**核心性质（border 链）**：设 `s[0..i]` 有一个长度为 k 的 border，那么这个 border 自己的 border（长度 `pi[k-1]`）也是 `s[0..i]` 的 border。所以 `s[0..i]` 的所有 border 长度依次是 `pi[i]`、`pi[pi[i]-1]`、`pi[pi[pi[i]-1]-1]`……直到 0。

## 构造 pi

递推：已知 `pi[i-1] = j`，即 `s[0..i-1]` 的最长 border 是 `s[0..j-1]`。要求 `pi[i]`：

1. 如果 `s[i] == s[j]`，border 可以延长一位，`pi[i] = j + 1`。
2. 否则这个 border 不能延长，换成次长的 border：`j = pi[j-1]`，再试。重复直到匹配或 j 退到 0。

为什么只需要沿 border 链试：`s[0..i]` 的任何一个 border，去掉最后一个字符后，就是 `s[0..i-1]` 的一个 border。所以候选长度都在 `s[0..i-1]` 的 border 链上，从长到短试，第一个能延长的就是最长的。

![s=aabaaab 的构造：i=5 时 j=2 失配，退到 pi[1]=1 后匹配，pi[5]=2](/qmx-Gameknowledge/assets/algo/c7-kmp-build.svg)

**时间 O(n)**：每处理一个 i，j 最多加 1；每次退回 `j = pi[j-1]` 都让 j 严格减小，而 j 不会小于 0。所以退回的总次数不超过加 1 的总次数 n。

## 匹配

把 `pat` 的 `pi` 算好后，扫描文本，用 j 记录“当前文本末尾已匹配到 `pat` 的前 j 个字符”：

- 读到 `text[i]`，如果 `text[i] != pat[j]`，则 `j = pi[j-1]`，直到匹配或 j = 0。
- 匹配则 j 加 1。
- j 到达 m 说明找到一次完整匹配，起点是 `i - m + 1`。接着继续扫描时，j 也按失配处理（先回退到 `pi[m-1]`）。

![text=abababcab, pat=ababc：偏移 0 时在 text[4] 失配，j 从 4 退到 pi[3]=2，模式串右移 2 位，前两个字符不用再比](/qmx-Gameknowledge/assets/algo/c7-kmp-match.svg)

文本指针 i 只增不减，j 的回退总量被它的增长量限制，所以整个匹配 O(n + m)。

## 代码

```cpp
#include <bits/stdc++.h>
using namespace std;

// 前缀函数：pi[i] = s[0..i] 的“最长相等真前后缀”的长度
vector<int> prefixFunction(const string& s) {
    int n = s.size();
    vector<int> pi(n, 0);
    for (int i = 1; i < n; i++) {
        int j = pi[i - 1];                       // 上一个位置的最长 border
        while (j > 0 && s[i] != s[j]) j = pi[j - 1];   // 失配：退到更短的 border
        if (s[i] == s[j]) j++;                   // 匹配：border 长度加一
        pi[i] = j;
    }
    return pi;
}

// 返回 pat 在 text 中所有出现位置的起点（允许重叠）
vector<int> kmpFind(const string& text, const string& pat) {
    int n = text.size(), m = pat.size();
    vector<int> res;
    if (m == 0) return res;
    vector<int> pi = prefixFunction(pat);
    int j = 0;                                   // 当前已匹配的长度
    for (int i = 0; i < n; i++) {
        while (j > 0 && (j == m || text[i] != pat[j])) j = pi[j - 1];
        if (text[i] == pat[j]) j++;
        if (j == m) res.push_back(i - m + 1);
    }
    return res;
}

// 最小周期：s 能写成某个长度为 p 的串重复若干次（最后一次可不完整）时的最小 p
int minPeriod(const string& s) {
    return s.size() - prefixFunction(s).back();
}

int main() {
    string s = "aabaaab";
    vector<int> pi = prefixFunction(s);
    cout << "pi(aabaaab) = ";
    for (int x : pi) cout << x << ' ';
    cout << "\n";

    string text = "abababcabab", pat = "abab";
    cout << "abab 在 " << text << " 中的起点: ";
    for (int p : kmpFind(text, pat)) cout << p << ' ';
    cout << "\n";

    cout << "abcabcabcab 的最小周期 = " << minPeriod("abcabcabcab") << "\n";
    string t = "abcabcabc";
    int p = minPeriod(t);
    cout << t << " 最小周期 " << p << (t.size() % p == 0 ? "，能被完整重复" : "，不能被完整重复") << "\n";
    return 0;
}
```

运行结果：

```text
pi(aabaaab) = 0 1 0 1 2 2 3 
abab 在 abababcabab 中的起点: 0 2 7 
abcabcabcab 的最小周期 = 3
abcabcabc 最小周期 3，能被完整重复
```

`kmpFind` 里有一处细节：`while (j > 0 && (j == m || text[i] != pat[j]))` 把“上一轮已完整匹配（j == m）”和“失配”合并处理，避免访问 `pat[m]` 越界。

## 用 pi 求周期

如果 `s` 有一个长度为 k 的 border，那么 `s` 以 `n - k` 为周期（`s[i] == s[i + n - k]`）。最长的 border 对应最小的周期，所以

```
最小周期 = n - pi[n-1]
```

若这个最小周期 p 满足 `p < n` 且 `n % p == 0`，则 s 恰好由长度为 p 的串重复 `n / p` 次构成。可以证明：如果存在整除 n 的周期 d < n，则 d ≤ n/2，它和最小周期 p（p ≤ d）满足 Fine–Wilf 定理的条件，所以 p 整除 d，进而整除 n。

## 例题

### 例 1：KMP 模板（洛谷 P3375）

输出模式串在文本中每次出现的起点（从 1 开始），再输出模式串每个前缀的最长 border 长度。

```cpp
#include <bits/stdc++.h>
using namespace std;

// 前缀函数：pi[i] = s[0..i] 的“最长相等真前后缀”的长度
vector<int> prefixFunction(const string& s) {
    int n = s.size();
    vector<int> pi(n, 0);
    for (int i = 1; i < n; i++) {
        int j = pi[i - 1];                       // 上一个位置的最长 border
        while (j > 0 && s[i] != s[j]) j = pi[j - 1];   // 失配：退到更短的 border
        if (s[i] == s[j]) j++;                   // 匹配：border 长度加一
        pi[i] = j;
    }
    return pi;
}

// 返回 pat 在 text 中所有出现位置的起点（允许重叠）
vector<int> kmpFind(const string& text, const string& pat) {
    int n = text.size(), m = pat.size();
    vector<int> res;
    if (m == 0) return res;
    vector<int> pi = prefixFunction(pat);
    int j = 0;                                   // 当前已匹配的长度
    for (int i = 0; i < n; i++) {
        while (j > 0 && (j == m || text[i] != pat[j])) j = pi[j - 1];
        if (text[i] == pat[j]) j++;
        if (j == m) res.push_back(i - m + 1);
    }
    return res;
}

// 最小周期：s 能写成某个长度为 p 的串重复若干次（最后一次可不完整）时的最小 p
int minPeriod(const string& s) {
    return s.size() - prefixFunction(s).back();
}

// 洛谷 P3375：输出 pat 在 text 中每次出现的起点（从 1 开始），再输出 pat 的 pi 数组
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string text, pat;
    cin >> text >> pat;
    for (int p : kmpFind(text, pat)) cout << p + 1 << "\n";
    for (int x : prefixFunction(pat)) cout << x << " ";
    cout << "\n";
    return 0;
}
```

示例：

输入：

```text
ABABABC
ABA
```

输出：

```text
1
3
0 0 1 
```

### 例 2：重复的子字符串（LeetCode 459）

题目链接：[LeetCode 459 重复的子字符串](https://leetcode.cn/problems/repeated-substring-pattern/)。判断 s 能否由某个子串重复两次或更多次构成。直接用上一节的结论。

```cpp
#include <bits/stdc++.h>
using namespace std;

// 前缀函数：pi[i] = s[0..i] 的“最长相等真前后缀”的长度
vector<int> prefixFunction(const string& s) {
    int n = s.size();
    vector<int> pi(n, 0);
    for (int i = 1; i < n; i++) {
        int j = pi[i - 1];                       // 上一个位置的最长 border
        while (j > 0 && s[i] != s[j]) j = pi[j - 1];   // 失配：退到更短的 border
        if (s[i] == s[j]) j++;                   // 匹配：border 长度加一
        pi[i] = j;
    }
    return pi;
}

// 返回 pat 在 text 中所有出现位置的起点（允许重叠）
vector<int> kmpFind(const string& text, const string& pat) {
    int n = text.size(), m = pat.size();
    vector<int> res;
    if (m == 0) return res;
    vector<int> pi = prefixFunction(pat);
    int j = 0;                                   // 当前已匹配的长度
    for (int i = 0; i < n; i++) {
        while (j > 0 && (j == m || text[i] != pat[j])) j = pi[j - 1];
        if (text[i] == pat[j]) j++;
        if (j == m) res.push_back(i - m + 1);
    }
    return res;
}

// 最小周期：s 能写成某个长度为 p 的串重复若干次（最后一次可不完整）时的最小 p
int minPeriod(const string& s) {
    return s.size() - prefixFunction(s).back();
}

// LeetCode 459：s 能否由某个子串重复两次或更多次构成
int main() {
    string s;
    cin >> s;
    int n = s.size(), p = minPeriod(s);
    cout << (p < n && n % p == 0 ? "yes" : "no") << "\n";
    return 0;
}
```

示例：

输入：

```text
abcabcabc
```

输出：

```text
yes
```

### 例 3：前缀后缀统计（Codeforces 432D）

找出所有既是前缀又是后缀的子串（也就是整条 border 链加上整串），并统计每个子串在 s 中出现的次数。

思路：长度为 l 的前缀每出现一次（以某个位置结束），它的所有 border 也各出现一次。先统计 `cnt[l]`：最长 border 恰为 l 的位置个数；再从大到小把 `cnt[l]` 累加给 `cnt[pi[l-1]]`；最后每个前缀自己在串首还出现一次，所以答案是 `cnt[l] + 1`。

```cpp
#include <bits/stdc++.h>
using namespace std;

// 前缀函数：pi[i] = s[0..i] 的“最长相等真前后缀”的长度
vector<int> prefixFunction(const string& s) {
    int n = s.size();
    vector<int> pi(n, 0);
    for (int i = 1; i < n; i++) {
        int j = pi[i - 1];                       // 上一个位置的最长 border
        while (j > 0 && s[i] != s[j]) j = pi[j - 1];   // 失配：退到更短的 border
        if (s[i] == s[j]) j++;                   // 匹配：border 长度加一
        pi[i] = j;
    }
    return pi;
}

// 返回 pat 在 text 中所有出现位置的起点（允许重叠）
vector<int> kmpFind(const string& text, const string& pat) {
    int n = text.size(), m = pat.size();
    vector<int> res;
    if (m == 0) return res;
    vector<int> pi = prefixFunction(pat);
    int j = 0;                                   // 当前已匹配的长度
    for (int i = 0; i < n; i++) {
        while (j > 0 && (j == m || text[i] != pat[j])) j = pi[j - 1];
        if (text[i] == pat[j]) j++;
        if (j == m) res.push_back(i - m + 1);
    }
    return res;
}

// 最小周期：s 能写成某个长度为 p 的串重复若干次（最后一次可不完整）时的最小 p
int minPeriod(const string& s) {
    return s.size() - prefixFunction(s).back();
}

// Codeforces 432D：找出所有既是前缀又是后缀的子串，输出它们的长度和在 s 中的出现次数
int main() {
    string s;
    cin >> s;
    int n = s.size();
    vector<int> pi = prefixFunction(s);
    vector<long long> cnt(n + 1, 0);
    for (int i = 0; i < n; i++) cnt[pi[i]]++;       // 先统计：有多少个位置的最长 border 恰好是 l
    for (int l = n; l >= 1; l--) cnt[pi[l - 1]] += cnt[l];     // 长度 l 的前缀每出现一次，它的 border 也出现一次
    vector<int> lens;
    for (int l = n; l > 0; l = pi[l - 1]) lens.push_back(l);   // 沿 border 链收集所有 border
    reverse(lens.begin(), lens.end());
    cout << lens.size() << "\n";
    for (int l : lens) cout << l << " " << cnt[l] + 1 << "\n";   // +1：前缀自己在串首的那一次
    return 0;
}
```

示例：

输入：

```text
ABACABA
```

输出：

```text
3
1 4
3 2
7 1
```

## 常见坑

- **下标偏移**：`pi[j-1]` 而不是 `pi[j]`。j 是“已匹配长度”，对应的最后一个字符下标是 j - 1。
- **匹配成功后忘记回退**：j 到达 m 后如果不处理，下一轮会读 `pat[m]`。
- **用模式串长度当分隔**：另一种写法是把 `pat + '#' + text` 拼起来，对整串求 pi，pi 值等于 m 的位置就是匹配。分隔符必须是不在字母表里的字符。
- 空模式串要提前处理。
- 多个模式串不要对每个都跑一遍 KMP，用 AC 自动机（7.5）。

## 练习

**入门**

- 洛谷 P3375 KMP 字符串匹配（本文例 1）
- [LeetCode 28 找出字符串中第一个匹配项的下标](https://leetcode.cn/problems/find-the-index-of-the-first-occurrence-in-a-string/)（简单）

**进阶**

- [LeetCode 459 重复的子字符串](https://leetcode.cn/problems/repeated-substring-pattern/)（简单，本文例 2）
- [LeetCode 1392 最长快乐前缀](https://leetcode.cn/problems/longest-happy-prefix/)（困难）
- [LeetCode 686 重复叠加字符串匹配](https://leetcode.cn/problems/repeated-string-match/)（中等）
- 洛谷 P4391 [BOI2009] Radio Transmission 无线传输（最小周期）

**挑战**

- Codeforces 126B Password
- Codeforces 432D Prefixes and Suffixes（本文例 3）
- 洛谷 P3435 [POI2006] OKR-Periods of Words
- 洛谷 P5829 【模板】失配树

下一篇：7.3 Z 函数：每个位置与整串的最长公共前缀。
