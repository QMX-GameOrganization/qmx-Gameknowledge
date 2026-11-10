---
title: "8.6 ⭐Miller-Rabin 与 Pollard's Rho"
description: "判断一个 64 位整数是不是质数，以及把它分解成质因数：Miller-Rabin 素性测试和 Pollard's Rho 分解。"
sidebar:
  order: 806
  badge:
    text: 进阶
    variant: caution
---

> 适用版本：C++17，需要 GCC/Clang 的 `__uint128_t`。前置：8.1 快速幂，8.2 试除与质数。什么时候需要学：数据范围到 10¹⁸，试除的 O(√n) 不再可行；筛法也无法覆盖这么大的范围。

## 要点

- **Miller-Rabin**：对一个奇数 n 做概率性（选定底数后是确定性）素性测试，单次 O(log n) 次乘法，对 64 位整数只要用固定的 12 个底数就能保证不误判。
- **Pollard's Rho**：随机化找出合数 n 的一个非平凡因子，期望 O(n^(1/4)) 次乘法。
- 两者合起来：先判质数，是就返回；不是就用 Rho 找因子递归分解。
- 乘法 `a·b mod n` 在 n 接近 2⁶⁴ 时必须用 128 位整数，否则溢出。

## Miller-Rabin

### 从费马小定理出发

n 是质数时，对任意 `gcd(a, n) = 1` 的 a 有 `a^(n-1) ≡ 1 (mod n)`。反过来测试：若 `a^(n-1) ≢ 1`，n 一定是合数。但有些合数（卡迈克尔数，如 561）对所有互质的 a 都通过这个测试，需要更强的判断。

### 二次探测

n 是奇质数时，方程 `x² ≡ 1 (mod n)` 只有 `x ≡ ±1` 两个解（因为 `(x-1)(x+1) ≡ 0`，质数 n 必须整除其中一个因子）。把 `n - 1` 写成 `d · 2^s`（d 为奇数），则 `a^(n-1)` 是对 `a^d` 连续平方 s 次得到的。如果 n 是质数，这个序列

```text
a^d,  a^(2d),  a^(4d),  …,  a^(2^s · d) = a^(n-1)
```

必须满足下面两种情况之一：

1. `a^d ≡ 1`：序列从头到尾全是 1。
2. 序列中某个位置（在最后一项之前）出现 `-1`（即 `n - 1`）：因为此后的一项是 `(-1)² = 1`，再往后都是 1。

若两者都不满足，n 一定是合数，说明 a 是 n 合数的"证人"。

![n=13是质数，a=2时 2的3次方是8，再平方得12即-1，通过；n=21是合数，a=2时 2的5次方是11，再平方得16，既不是1也不是-1，判为合数](/qmx-Gameknowledge/assets/algo/c8-miller-rabin.svg)

对合数 n，至少有 3/4 的底数是证人，所以随机选 k 个底数，误判概率不超过 4^(-k)。更方便的做法是用已知的固定底数集合：

- 用前 12 个质数 `2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37` 做底数，对所有 `n < 318665857834031151167461` 都不会误判。64 位无符号整数的最大值约 1.8×10¹⁹，被完全覆盖。

## Pollard's Rho

### 生日悖论的用法

n 的最小质因子是 p。取一个伪随机序列 `x0, x1 = f(x0), x2 = f(x1), …`，其中 `f(x) = (x² + c) mod n`。这个序列在**模 p 意义下**也是一个伪随机序列，取值范围只有 p 个，根据生日悖论，大约 √p 步之后就会出现 `xi ≡ xj (mod p)`，即模 p 成环。而模 n 意义下的序列范围大得多，此时通常 `xi ≢ xj (mod n)`。

于是 `gcd(|xi - xj|, n)` 是 p 的倍数、又不等于 n，即 n 的非平凡因子。因为 p ≤ √n，期望 √p ≤ n^(1/4) 步。

![序列 x0 到 x9 像希腊字母 rho：先是一段尾巴，然后进入环；x9 与 x4 在模 p 下相同，用 gcd(|x9-x4|, n) 得到因子](/qmx-Gameknowledge/assets/algo/c8-pollard-rho.svg)

### 如何发现环

不需要存下所有 `xi`。用 Floyd 判圈法：慢指针每次走一步 `x = f(x)`，快指针每次走两步 `y = f(f(y))`，每轮计算 `gcd(|x - y|, n)`，值大于 1 时就找到了。

### 批量 gcd 优化

每轮都算 gcd 比较慢（gcd 本身要 O(log n)）。常用技巧是把 `|x - y|` 连乘（模 n），每 128 轮才算一次 gcd。如果这次的 gcd 等于 n（说明这一批里同时碰到了几个因子），再从这一批的起点逐步重来，找到第一个 gcd 大于 1 的位置。

### 失败的情况

`gcd` 可能等于 n（序列在模 p 和模 n 下同时成环）。这时换一个 c 重新来。

## 完整代码

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long ull;
typedef __uint128_t u128;

ull mulmod(ull a, ull b, ull m) { return (u128)a * b % m; }

ull powmod(ull a, ull e, ull m) {
    ull r = 1 % m;
    for (a %= m; e; e >>= 1, a = mulmod(a, a, m))
        if (e & 1) r = mulmod(r, a, m);
    return r;
}

// 确定性 Miller-Rabin：前 12 个质数做底数，对 n < 3.18e23 都不会误判，足以覆盖 64 位整数
bool is_prime(ull n) {
    if (n < 2) return false;
    for (ull p : {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37}) {
        if (n % p == 0) return n == p;
    }
    ull d = n - 1;
    int s = 0;
    while ((d & 1) == 0) d >>= 1, s++;           // n-1 = d * 2^s
    for (ull a : {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37}) {
        ull x = powmod(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool composite = true;
        for (int i = 1; i < s; i++) {
            x = mulmod(x, x, n);
            if (x == n - 1) { composite = false; break; }
        }
        if (composite) return false;
    }
    return true;
}

mt19937_64 rng(20240601);

// Pollard's Rho：返回 n 的一个非平凡因子（n 为合数）
ull pollard_rho(ull n) {
    if (n % 2 == 0) return 2;
    while (true) {
        ull c = rng() % (n - 1) + 1;
        auto f = [&](ull x) { return (ull)(((u128)x * x + c) % n); };   // 用 128 位相加，避免 n 接近 2^64 时溢出
        ull x = rng() % n, y = x, d = 1;
        // 每 128 步合并一次 gcd，减少 gcd 次数
        ull q = 1;
        while (d == 1) {
            ull sx = x, sy = y;
            for (int i = 0; i < 128; i++) {
                x = f(x);
                y = f(f(y));
                q = mulmod(q, x > y ? x - y : y - x, n);
            }
            d = std::__gcd(q, n);
            if (d == 0 || d == n) {            // 这一批可能越过了，回退逐步检查
                x = sx; y = sy; d = 1;
                for (int i = 0; i < 128 && d == 1; i++) {
                    x = f(x);
                    y = f(f(y));
                    d = std::__gcd(x > y ? x - y : y - x, n);
                }
                break;
            }
        }
        if (d != 1 && d != n) return d;        // 失败（d == n）就换一个 c 重来
    }
}

void factor(ull n, vector<ull> &res) {
    if (n == 1) return;
    if (is_prime(n)) { res.push_back(n); return; }
    ull d = pollard_rho(n);
    factor(d, res);
    factor(n / d, res);
}

int main() {
    for (ull x : {1000000007ULL, 561ULL, 1000000007ULL * 998244353ULL, 18446744073709551557ULL})
        printf("%llu 是质数吗: %d\n", x, (int)is_prime(x));
    ull n = 1000000007ULL * 998244353ULL;       // 约 1e18
    vector<ull> f;
    factor(n, f);
    sort(f.begin(), f.end());
    printf("%llu =", n);
    for (ull p : f) printf(" %llu", p);
    puts("");
    return 0;
}
```

运行结果：

```text
1000000007 是质数吗: 1
561 是质数吗: 0
998244359987710471 是质数吗: 0
18446744073709551557 是质数吗: 1
998244359987710471 = 998244353 1000000007
```

- `1000000007` 是质数；`561` 是最小的卡迈克尔数，被判为合数；两个大质数之积是合数；`18446744073709551557` 是小于 2⁶⁴ 的最大质数。
- 把 `998244359987710471` 分解得到 `998244353 × 1000000007`。

关于实现的几点：

- `mulmod` 用 `unsigned __int128` 计算 `a·b mod m`，避免溢出，对 64 位范围是最简单可靠的做法。
- `f` 里计算 `x² + c` 也必须在 128 位里做完再取模，下面的"常见坑"会说明为什么。
- 先用 12 个小质数做试除，既处理小数，又保证后面进入 Miller-Rabin 的数没有这些小因子。
- 本机一次测试里，对"两个 32 位质数之积"做 100 次分解大约用时 63 到 67 ms。

## 例题

### 例 1：分解大数（洛谷 P4718 的模板）

给出多个不超过 10¹⁸ 的整数，对每个输出它的最大质因子，如果它本身是质数则输出 `Prime`。用 `factor` 得到所有质因子，取最大值即可。

### 例 2：约数个数

求 n 的约数个数：用 `factor` 分解后统计各质因子的指数 `e1, e2, …`，约数个数为 `(e1+1)(e2+1)…`。

```cpp
// 片段：沿用上面的 factor 与 is_prime
vector<ull> f;
factor(n, f);
sort(f.begin(), f.end());
ull cnt = 1;
for (size_t i = 0; i < f.size();) {
    size_t j = i;
    while (j < f.size() && f[j] == f[i]) j++;
    cnt *= (j - i + 1);
    i = j;
}
```

## 适用与不适用

适用：n 在 10¹⁸ 以内的素性判断与分解。n 小于 10⁷ 时直接筛，更简单。需要对一大段连续区间分解时，用线性筛而不是对每个数调用 Rho。

## 常见坑

- **溢出**：`(x*x + c) % n` 在 n 接近 2⁶⁴ 时，`x*x` 本身用 128 位取模后小于 n，但再加 c 可能超过 2⁶⁴ 而发生回绕，序列看起来"随机"实则被破坏，Rho 可能一直找不到因子。本篇调试时就遇到了这一点：对 `4294967291²` 做分解一直不终止，原因就是这里。正确的做法是 `((u128)x * x + c) % n`。
- 只用少量底数（如 2、3）做 Miller-Rabin，会被强伪素数骗过去，比如 `3215031751` 同时是底数 2、3、5、7 的强伪素数。
- `n` 是质数的平方（如 `p²`）时 Rho 也可以工作，但前提是先排除 2 和能被小质数整除的情况。
- 对 `n = 1`、`n = 2` 的边界单独处理。
- 递归分解时 `factor(d)` 与 `factor(n / d)` 都要调用，漏了一边会丢掉质因子。

## 练习

**入门**

- 洛谷 P4718 【模板】Pollard's Rho 算法

**进阶**

- LeetCode 204 计数质数（对比筛法与逐个测试的适用范围）
- 把 8.2 的 `lp` 分解与本篇的 `factor` 在随机数据上对拍一次，验证结果相同

**挑战**

- 洛谷 P1075 [NOIP 2012] 质因数分解（先用试除理解，再用 Rho 做 10¹⁸ 的版本）
- 自行实现 Brent 版本的 Rho（用一个指针代替 Floyd 的快慢两个）并与本篇对比用时

下一篇：8.7 ⭐高斯消元与线性基。
