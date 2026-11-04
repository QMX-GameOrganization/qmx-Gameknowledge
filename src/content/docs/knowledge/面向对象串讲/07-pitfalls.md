---
title: "7. 重载、重写与对象模型陷阱"
description: "用短代码识别隐藏、切片、默认参数、构造期虚调用、悬空对象和错误向下转换。"
sidebar:
  order: 8
---

## 先把三个词分开

重载（overload）是在同一名字下提供不同参数列表，调用时参与重载决议。重写（override）是派生类提供基类虚函数的实现，需要匹配相关签名规则。隐藏（hiding）是名字查找阶段，派生类同名声明遮住基类名字，未必与虚函数有关。

```cpp
struct Base {
    void log(int) const {}
    virtual void tick() const {}
};

struct Derived : Base {
    using Base::log; // 把基类重载引入查找范围。
    void log(const char*) const {}
    void tick() const override {} // const 也必须匹配。
    // void tick() override {}    // 错误：少 const，没有重写基类函数。
};
```

删除 `using Base::log` 后，`Derived d; d.log(3);` 不会自动“再去基类找 int 版”，而会因可见候选不合适而失败。`using` 恢复候选集合，不会自动把非虚函数变成虚函数。

## 坑一：按值保存基类导致切片

```cpp
#include <iostream>

struct Base {
    virtual ~Base() = default;
    virtual const char* name() const { return "Base"; }
};
struct Derived : Base {
    const char* name() const override { return "Derived"; }
};

int main() {
    Derived d;
    Base sliced = d;
    const Base& borrowed = d;
    std::cout << sliced.name() << '\n';   // Base
    std::cout << borrowed.name() << '\n'; // Derived
}
```

`sliced` 是一个新的完整 `Base`，只从原对象的基类部分构造，不再包含派生部分。`vector<Base>` 同样不能保留不同派生对象。需要多态所有权时可用 `vector<unique_ptr<Base>>`；需要复制多态对象时应明确设计 `clone` 等协议，不能偷偷共享替代独立复制。

## 坑二：默认参数与虚调用不是同一套绑定规则

```cpp
struct Base {
    virtual ~Base() = default;
    virtual int cost(int n = 1) const { return n; }
};
struct Derived : Base {
    int cost(int n = 2) const override { return n * 10; }
};
// Derived d; const Base& b = d;
// b.cost() == 10；d.cost() == 20。
```

默认参数按调用点的静态类型选择，虚实现按动态分派选择。于是通过 `b` 调用时，把基类默认值 1 传给派生实现。建议把默认值放在稳定的非虚入口，或在调用处显式传参，避免上下文改变行为。

## 坑三：构造和析构阶段不是完整派生对象的普通运行期

基类构造函数内的虚调用不会进入尚未构造完成的派生层实现；基类析构期间，也不会像完整派生对象仍活着那样分派。不要依靠构造函数调用 `initVirtual()` 初始化派生字段。若需要分阶段创建，使用明确工厂或构造完成后的显式操作，并定义失败时如何清理。

在构造或析构中对当前对象进行纯虚调用存在严格规则和未定义行为风险，本专题不运行这种反例。先遵守更清楚的设计约束：构造只建立自身有效状态，不调用需要完整派生状态的可重写行为。

## 坑四：多态不延长对象寿命

虚函数再正确，也不能对已经销毁的对象调用。`Skill*` 指向局部技能，函数返回后再施放，是悬空访问；技能缓存了 `Actor&`，角色先销毁，同样危险。下一次调用能“碰巧成功”不证明它合法。

构造/析构顺序、容器失效规则和所有权图应该一起检查。异常安全也不能只看是否释放内存：若施放扣了魔法值却抛异常，效果尚未生效，是否要退还？这是业务事务契约，需要另行设计。

## 坑五：强制转换掩盖错误抽象

`static_cast<Derived*>` 不会替你验证运行时对象确实匹配；错误向下转换并使用会造成未定义行为。对多态类型使用 `dynamic_cast<Derived*>` 可以在失败时得到空指针；引用形式失败会抛 `std::bad_cast`。这些操作需要适合的多态基类和 RTTI 配置。

如果每次拿到 `Skill&` 都先判断它是什么子类，再分支调用独有函数，说明你可能没有把调用方真正需要的行为放进契约。类型转换偶尔合理，但不应成为统一接口名义下的新一轮 switch。

## 坑六：空指针、引用返回与整数边界

`unique_ptr` 也可以为空；`vector<unique_ptr<T>>` 中有槽位不代表每个槽位都有对象。`const string&` 返回值的有效期受原对象约束；`string_view` 不拥有字符存储。`max(0, hp - damage)` 也不能修复减法已经发生的溢出。接口要定义空值、寿命和合法数值范围。

**练习：** 为本章每个坑写一句“编译能否发现 / 运行可能怎样 / 推荐修复”。不要用执行未定义行为来证明哪一种现象“必然发生”。

下一章：[从需求变化判断设计好坏](../08-design/)。
