---
title: "8.8 ⭐FFT 与 NTT"
description: "用快速傅里叶变换和数论变换在 O(n log n) 内做多项式乘法，附带大整数乘法示例。"
sidebar:
  order: 808
  badge:
    text: 进阶
    variant: caution
---

> 适用版本：C++17。前置：8.1 快速幂与逆元；需要知道复数的基本运算和"单位根"的概念。什么时候需要学：两个长度各约 10⁵ 的数组做卷积、多项式乘法、大整数乘法，朴素的 O(n²) 超时时。

## 要点

- 两个多项式相乘等价于它们系数序列的**卷积**，朴素 O(n·m)。
- 多项式有两种表示：系数表示和点值表示。**点值表示下相乘只需逐点相乘**，O(n)。
- FFT 在复数的 n 次单位根处求值，把"系数 → 点值"和"点值 → 系数"都做到 O(n log n)。
- NTT 把复数单位根换成模质数下的原根，全程整数运算，结果精确。常用模数 998244353，原根 3。

## 卷积与点值表示

两个多项式 `A(x) = Σ a_i x^i`，`B(x) = Σ b_j x^j`，乘积 `C(x) = Σ c_k x^k` 满足

```text
c_k = Σ_{i + j = k} a_i · b_j
```

即卷积。一个次数小于 n 的多项式可以由它在 n 个不同点的取值唯一确定。如果在**同样的 n 个点**上知道 `A` 和 `B` 的值，则 `C` 在这些点的值就是 `A(x) · B(x)`，只需 n 次乘法。

![多项式乘法的流程：系数形式的 A 和 B，经过 NTT 得到点值，逐点相乘，再经逆 NTT 得到 C 的系数；两次变换各需要 O(n log n)，中间逐点相乘需要 O(n)](/qmx-Gameknowledge/assets/algo/c8-poly-pipeline.svg)

难点在于：选哪 n 个点，才能让"系数 → 点值"这个变换快速完成？答案是 n 次单位根。

## 单位根与分治

取 n 为 2 的幂。n 次单位根 `ω_n^k`（k = 0 … n-1）是方程 `x^n = 1` 的所有复数解，`ω_n = e^(2πi/n)`。它有两个性质：

- 折半引理：`(ω_n^k)² = ω_(n/2)^k`。
- 对称性：`ω_n^(k + n/2) = -ω_n^k`。

把 `A(x)` 按下标奇偶拆开：

```text
A(x) = E(x²) + x · O(x²)
```

其中 E 的系数是 a 的偶数下标项，O 是奇数下标项，各有 n/2 项。代入 `x = ω_n^k`：

```text
A(ω_n^k)         = E(ω_(n/2)^k) + ω_n^k · O(ω_(n/2)^k)
A(ω_n^(k + n/2)) = E(ω_(n/2)^k) - ω_n^k · O(ω_(n/2)^k)
```

两个子问题 `E`、`O` 的规模都是 n/2，且只需要在 n/2 个单位根上求值，得到后合并成 n 个值只要 O(n)。递推式 `T(n) = 2T(n/2) + O(n)`，解为 O(n log n)。上面一对式子叫作**蝶形运算**。

### 逆变换

点值 → 系数：只需把变换里的 `ω_n` 换成它的逆 `ω_n^(-1)`，做完后每个值除以 n。

## 迭代实现

递归版常数大。迭代版先做**位反转置换**（把下标的二进制位反转，得到递归到最底层后叶子的顺序），然后自底向上依次合并长度为 2、4、8、…的块。

![n=8 的迭代 NTT：输入先按位反转重排成 a0 a4 a2 a6 a1 a5 a3 a7，随后三层蝶形，每层把距离 len/2 的两个元素配对运算](/qmx-Gameknowledge/assets/algo/c8-ntt-butterfly.svg)

## NTT：把复数换成整数

浮点数 FFT 有精度损失。NTT 用同样的算法，只是把单位根换成模质数 p 下的原根：

- 取 `p = 998244353 = 119 · 2^23 + 1`，原根 `g = 3`。
- n 次单位根为 `ω_n = g^((p-1)/n) mod p`，n 必须整除 `p - 1`，所以 n 是 2 的幂且 `n ≤ 2^23`。
- 折半引理和对称性在模 p 下依然成立。逆变换用 `ω_n^(-1)` 和 `n^(-1)`（8.1 的逆元）。

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

const int MOD = 998244353, G = 3;      // 998244353 = 119 * 2^23 + 1，原根 3

ll power(ll a, ll e) {
    ll r = 1;
    for (a %= MOD; e; e >>= 1, a = a * a % MOD)
        if (e & 1) r = r * a % MOD;
    return r;
}

// 迭代式 NTT。invert=true 时做逆变换。a.size() 必须是 2 的幂
void ntt(vector<int> &a, bool invert) {
    int n = a.size();
    for (int i = 1, j = 0; i < n; i++) {                // 位反转置换：把输入重排成递归后的叶子顺序
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) swap(a[i], a[j]);
    }
    for (int len = 2; len <= n; len <<= 1) {            // 自底向上合并长度为 len 的块
        ll w = power(G, (MOD - 1) / len);               // len 次单位根
        if (invert) w = power(w, MOD - 2);
        for (int i = 0; i < n; i += len) {
            ll cur = 1;
            for (int j = 0; j < len / 2; j++) {
                int u = a[i + j], v = (ll)a[i + j + len / 2] * cur % MOD;
                a[i + j] = u + v >= MOD ? u + v - MOD : u + v;
                a[i + j + len / 2] = u - v < 0 ? u - v + MOD : u - v;
                cur = cur * w % MOD;
            }
        }
    }
    if (invert) {
        ll inv_n = power(n, MOD - 2);
        for (int &x : a) x = (ll)x * inv_n % MOD;
    }
}

vector<int> multiply(vector<int> a, vector<int> b) {
    int need = a.size() + b.size() - 1, n = 1;
    while (n < need) n <<= 1;
    a.resize(n); b.resize(n);
    ntt(a, false); ntt(b, false);
    for (int i = 0; i < n; i++) a[i] = (ll)a[i] * b[i] % MOD;
    ntt(a, true);
    a.resize(need);
    return a;
}

int main() {
    // (1 + 2x + 3x^2) * (4 + 5x) = 4 + 13x + 22x^2 + 15x^3
    vector<int> c = multiply({1, 2, 3}, {4, 5});
    for (int x : c) printf("%d ", x);
    puts("");
    return 0;
}
```

运行结果：

```text
4 13 22 15
```

`(1 + 2x + 3x²)(4 + 5x) = 4 + 13x + 22x² + 15x³`，与手算一致。

注意事项：

- 所有结果都是**模 998244353 的**。如果真实的卷积系数可能超过这个模数，结果会被取模，需要换用其它模数（再用 8.4 的中国剩余定理合并）。
- 长度必须补到 2 的幂，且至少 `deg(A) + deg(B) + 1`。

## FFT（复数版）

当系数可能很大、又不能取模时，用复数 FFT，并在最后四舍五入。

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef complex<double> cd;
const double PI = acos(-1.0);

// 与 NTT 结构完全相同，只是把模意义下的单位根换成复数单位根
void fft(vector<cd> &a, bool invert) {
    int n = a.size();
    for (int i = 1, j = 0; i < n; i++) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) swap(a[i], a[j]);
    }
    for (int len = 2; len <= n; len <<= 1) {
        double ang = 2 * PI / len * (invert ? -1 : 1);
        cd wl(cos(ang), sin(ang));
        for (int i = 0; i < n; i += len) {
            cd w(1);
            for (int j = 0; j < len / 2; j++) {
                cd u = a[i + j], v = a[i + j + len / 2] * w;
                a[i + j] = u + v;
                a[i + j + len / 2] = u - v;
                w *= wl;
            }
        }
    }
    if (invert) for (cd &x : a) x /= n;
}

vector<long long> multiply(const vector<int> &a, const vector<int> &b) {
    int need = a.size() + b.size() - 1, n = 1;
    while (n < need) n <<= 1;
    vector<cd> fa(a.begin(), a.end()), fb(b.begin(), b.end());
    fa.resize(n); fb.resize(n);
    fft(fa, false); fft(fb, false);
    for (int i = 0; i < n; i++) fa[i] *= fb[i];
    fft(fa, true);
    vector<long long> res(need);
    for (int i = 0; i < need; i++) res[i] = llround(fa[i].real());   // 四舍五入消除浮点误差
    return res;
}

int main() {
    auto c = multiply({1, 2, 3}, {4, 5});
    for (long long x : c) printf("%lld ", x);
    puts("");
    return 0;
}
```

运行结果：

```text
4 13 22 15
```

FFT 的精度与卷积结果的大小有关：结果系数可以估计为 `n · max(a) · max(b)`，超过约 10¹⁴ 到 10¹⁵ 时 `double` 的误差会让四舍五入出错。本篇的随机测试中系数在 0 到 99，结果完全精确。需要更高精度时用 `long double`，或者改用 NTT。

## 例题：大整数乘法

把大整数的每一位十进制数字当作多项式的一个系数，两个数相乘就是两个多项式相乘，最后统一进位。位数 L 时系数最大约 `81 · L`，只要小于 998244353，NTT 的取模就不会破坏结果。实际限制更早到来：变换长度不能超过 2²³，所以两个数加起来最多约 8×10⁶ 位。

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

const int MOD = 998244353, G = 3;      // 998244353 = 119 * 2^23 + 1，原根 3

ll power(ll a, ll e) {
    ll r = 1;
    for (a %= MOD; e; e >>= 1, a = a * a % MOD)
        if (e & 1) r = r * a % MOD;
    return r;
}

// 迭代式 NTT。invert=true 时做逆变换。a.size() 必须是 2 的幂
void ntt(vector<int> &a, bool invert) {
    int n = a.size();
    for (int i = 1, j = 0; i < n; i++) {                // 位反转置换：把输入重排成递归后的叶子顺序
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) swap(a[i], a[j]);
    }
    for (int len = 2; len <= n; len <<= 1) {            // 自底向上合并长度为 len 的块
        ll w = power(G, (MOD - 1) / len);               // len 次单位根
        if (invert) w = power(w, MOD - 2);
        for (int i = 0; i < n; i += len) {
            ll cur = 1;
            for (int j = 0; j < len / 2; j++) {
                int u = a[i + j], v = (ll)a[i + j + len / 2] * cur % MOD;
                a[i + j] = u + v >= MOD ? u + v - MOD : u + v;
                a[i + j + len / 2] = u - v < 0 ? u - v + MOD : u - v;
                cur = cur * w % MOD;
            }
        }
    }
    if (invert) {
        ll inv_n = power(n, MOD - 2);
        for (int &x : a) x = (ll)x * inv_n % MOD;
    }
}

vector<int> multiply(vector<int> a, vector<int> b) {
    int need = a.size() + b.size() - 1, n = 1;
    while (n < need) n <<= 1;
    a.resize(n); b.resize(n);
    ntt(a, false); ntt(b, false);
    for (int i = 0; i < n; i++) a[i] = (ll)a[i] * b[i] % MOD;
    ntt(a, true);
    a.resize(need);
    return a;
}

// 大整数乘法：把十进制每一位当作多项式的一个系数，卷积后统一进位
string big_multiply(const string &x, const string &y) {
    vector<int> a(x.rbegin(), x.rend()), b(y.rbegin(), y.rend());   // 低位在前
    for (int &d : a) d -= '0';
    for (int &d : b) d -= '0';
    vector<int> c = multiply(a, b);
    long long carry = 0;
    string res;
    for (size_t i = 0; i < c.size() || carry; i++) {
        long long cur = carry + (i < c.size() ? c[i] : 0);
        res.push_back('0' + cur % 10);
        carry = cur / 10;
    }
    while (res.size() > 1 && res.back() == '0') res.pop_back();
    reverse(res.begin(), res.end());
    return res;
}

int main() {
    printf("%s\n", big_multiply("123456789", "987654321").c_str());
    printf("%s\n", big_multiply("99999999999999999999", "99999999999999999999").c_str());
    return 0;
}
```

运行结果：

```text
121932631112635269
9999999999999999999800000000000000000001
```

第一行是 `123456789 × 987654321`，第二行是 `(10²⁰ - 1)² = 10⁴⁰ - 2·10²⁰ + 1`，两者都已用 Python 大整数核对。

## 适用与不适用

适用：n、m 约 10⁵ 到 10⁶ 的卷积类问题（多项式乘法、大整数乘法、字符串匹配的通配符变体等）。不适用：n 很小（几十以内）时朴素卷积更快；模数不是 NTT 友好模数（如 10⁹+7）时，需要三模数 NTT 或拆系数 FFT。

## 常见坑

- 数组长度没补到 2 的幂，或补得不够大（要不小于 `n + m - 1`）。
- 逆变换忘记除以 n。
- NTT 里 `u + v` 与 `u - v` 的取模要分别处理加减，不要直接 `%` 负数。
- 复数 FFT 的输出必须用 `llround` 而不是直接转 `long long`，截断会引入 ±1 的错误。
- 每次递归/循环里重复调用 `power` 计算单位根，会把 O(n log n) 拖慢，本实现按层算一次 `w`，层内用累乘。

## 练习

**入门**

- LeetCode 43 字符串相乘（先用普通竖式做，再用 NTT 做一遍）
- 洛谷 P3803 【模板】多项式乘法（FFT）

**进阶**

- 洛谷 P1919 【模板】A*B Problem 升级版（FFT 快速傅里叶）

**挑战**

- 洛谷 P4238 【模板】多项式乘法逆（在 NTT 基础上用倍增）

下一篇：8.9 ⭐博弈论与 SG 函数。
