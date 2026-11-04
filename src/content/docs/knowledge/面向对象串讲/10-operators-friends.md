---
title: "10. 自定义值怎样使用：运算符重载与 friend"
description: "用格子坐标相加、比较和输出，学习成员与非成员运算符、友元及封装取舍。"
sidebar:
  order: 11
---

## 应用：坐标是一个值，想像整数一样自然组合

角色移动到相邻格子时，写 `position + offset` 比零散修改 x/y 更能表达意图。不是每个业务动作都适合运算符：坐标相加含义明确，“两个角色相加”通常不明确。

```cpp
#include <iostream>

// 小型坐标值类型；示例输入限定在不会发生整数溢出的范围。
class Position {
public:
    Position(int x, int y) : x_(x), y_(y) {}
    Position operator+(const Position& other) const {
        return Position{x_ + other.x_, y_ + other.y_};
    }
    bool operator==(const Position& other) const {
        return x_ == other.x_ && y_ == other.y_;
    }
    friend std::ostream& operator<<(std::ostream& out, const Position& value);
private:
    int x_;
    int y_;
};

// 非成员输出运算符：通过 friend 获准读取私有坐标。
std::ostream& operator<<(std::ostream& out, const Position& value) {
    return out << '(' << value.x_ << ',' << value.y_ << ')';
}

int main() {
    Position start{2, 3};
    Position offset{1, -1};
    Position result = start + offset;
    std::cout << result << '\n';
    std::cout << (result == Position{3, 2}) << '\n';
}
```

输出 `(3,2)` 和 `1`，各一行。C++17 中这里的 `operator==` 不自动生成 `operator!=`；想支持它需要明确提供。不要将 C++20 的比较重写规则当成 C++17 行为。

## operator+ 本质上仍是函数

成员形式 `a + b` 可理解为 `a.operator+(b)`，左操作数是当前对象，因此只显式接收一个参数。非成员形式通常接收两个操作数。重载不能创建全新运算符，不能改变运算符的优先级、结合性和操作数数量，也不能只为两个内置类型重新定义加法。

加法返回值而非局部引用：`Position result{...}; return result;` 可以按值返回；`return result;` 若函数返回类型是 `Position&` 则会留下悬空引用。小值类型适合明确的值语义，不应为“避免复制”牺牲正确性。

## 为什么输出用非成员函数

`std::cout << position` 的左边是标准库流对象，不是 Position，不能把它自然写成 Position 的普通左操作数成员调用。常见写法是非成员 `operator<<(ostream&, const Position&)`。返回 `ostream&` 让 `cout << a << b` 可以接着使用同一输出流。

非成员运算符还可以改善某些对称操作的转换选择。例如希望标量乘法支持 `2 * position`，只写 Position 的普通成员版本并不够。具体允许何种隐式转换仍应审慎设计，不能为了便利取消全部 explicit。

## friend 给权限，不改变函数身份

friend 声明授权特定函数或类访问私有/受保护成员。上面的输出函数仍是非成员，没有 this；它不因为 friend 就成为 Position 的成员函数。

友元不是自动互相授权，不传递，也不自动继承给派生类。声明某个类为 friend 会给该类成员较广的权限；只需要一个操作时，授权单个函数通常更清晰。

如果公开只读 `x()`、`y()` 已经是合理接口，输出函数也可以通过它们工作，不使用 friend。反之，为了一个运算符把所有字段公开，会把实现细节暴露给更多调用方。选择取决于边界，而不是 friend 一律好或一律坏。

## 相关语法顺便分清

`operator=` 是赋值，`==` 是比较，两者不同；`Position p = q` 是初始化，不是给一个已存在对象执行普通赋值。前置 `++x` 常返回对象引用，后置 `x++` 的重载用一个占位 int 参数区分，并通常返回旧值副本。不是任何返回类型都能保持读者熟悉的语义。

不应为了炫技重载逻辑与/逻辑或来模拟普通布尔短路：重载调用不提供内置短路行为。让运算符符合使用者预期，比少写几个字更重要。

**练习：** 增加 `operator!=`，再将输出函数改为通过只读查询实现，比较授权范围。最后解释为什么 `takeDamage(20)` 比一个奇怪的 `actor -= anotherActor` 更适合本专题角色。

下一章：[继承语法与访问规则](../11-inheritance-syntax/)。
