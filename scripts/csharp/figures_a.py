"""第 1~4 章用到的配图。"""
from svglib import Fig, GREY, SUB, INK, PALETTE


def value_vs_ref():
    f = Fig("value-vs-ref", "值类型与引用类型：赋值时复制的东西不同", "同样写 b = a，复制的内容不一样。", 520,
            "值类型变量里装数据本身；引用类型变量里装指向对象的引用。")
    f.rect(32, 105, 450, 360, "blue")
    f.text(48, 137, "值类型（int、float、struct…）", 19, PALETTE["blue"][1], "700")
    f.text(48, 168, "int a = 10;  int b = a;  b = 99;", 15, mono=True)
    f.text(155, 232, "变量 a", 16, SUB, anchor="middle")
    f.text(365, 232, "变量 b", 16, SUB, anchor="middle")
    f.rect(85, 244, 140, 76, "white")
    f.rect(295, 244, 140, 76, "white")
    f.text(155, 294, "10", 30, INK, "700", "middle")
    f.text(365, 294, "99", 30, INK, "700", "middle")
    f.arrow(228, 282, 292, 282, PALETTE["blue"][1], dash=True)
    f.text(260, 350, "b = a 时复制了一份内容", 15, SUB, anchor="middle")
    f.text(48, 410, "改 b 只影响 b，a 仍然是 10。", 17, PALETTE["blue"][1], "700")
    f.text(48, 438, "两个变量各自拥有独立的数据。", 17)

    f.rect(518, 105, 450, 360, "green")
    f.text(534, 137, "引用类型（class、数组、string…）", 19, PALETTE["green"][1], "700")
    f.text(534, 168, "int[] x = {1,2,3};  int[] y = x;  y[0] = 99;", 14, mono=True)
    f.chip(630, 235, 120, 52, "white", "x（引用）")
    f.chip(850, 235, 120, 52, "white", "y（引用）")
    f.text(534, 318, "堆上的同一个对象", 15, SUB)
    f.rect(590, 330, 290, 78, "orange")
    f.text(735, 360, "int[] 数组对象", 16, PALETTE["orange"][1], "700", "middle")
    f.text(735, 392, "[ 99, 2, 3 ]", 20, INK, "700", "middle", mono=True)
    f.arrow(640, 262, 690, 328, PALETTE["green"][1])
    f.arrow(840, 262, 780, 328, PALETTE["green"][1])
    f.text(534, 440, "改 y[0]，通过 x 读出来也是 99。", 17, PALETTE["green"][1], "700")
    return f.save()


def param_pass():
    f = Fig("param-pass", "引用类型传参：传的是引用的副本", "函数能改对象的内容，但换不掉调用方手里的那份引用。", 560,
            "想让函数真的替换调用方的变量，要用 ref 或 out。")
    # 左：改内容
    f.rect(32, 105, 450, 380, "green")
    f.text(48, 137, "Fill(bag)：修改内容", 19, PALETTE["green"][1], "700")
    f.text(48, 166, "static void Fill(int[] arr) { arr[0] = 50; }", 14, mono=True)
    f.chip(150, 235, 130, 50, "white", "调用方 bag")
    f.chip(150, 330, 130, 50, "white", "形参 arr")
    f.rect(310, 255, 150, 100, "orange")
    f.text(385, 290, "数组对象", 16, PALETTE["orange"][1], "700", "middle")
    f.text(385, 326, "[ 50, 0 ]", 20, INK, "700", "middle", mono=True)
    f.arrow(216, 238, 308, 285, PALETTE["green"][1])
    f.arrow(216, 326, 308, 328, PALETTE["green"][1])
    f.text(48, 420, "两个引用指向同一个数组，", 17)
    f.text(48, 446, "改 arr[0]，bag[0] 也变成 50。", 17, PALETTE["green"][1], "700")
    # 右：换引用
    f.rect(518, 105, 450, 380, "red")
    f.text(534, 137, "Replace(bag)：换引用", 19, PALETTE["red"][1], "700")
    f.text(534, 166, "arr = new int[] { 7 };", 14, mono=True)
    f.chip(630, 235, 130, 50, "white", "调用方 bag")
    f.chip(630, 330, 130, 50, "white", "形参 arr")
    f.rect(790, 205, 160, 70, "orange")
    f.text(870, 232, "原数组", 15, PALETTE["orange"][1], "700", "middle")
    f.text(870, 258, "[ 50, 0 ]", 17, INK, "700", "middle", mono=True)
    f.rect(790, 300, 160, 70, "purple")
    f.text(870, 327, "新数组", 15, PALETTE["purple"][1], "700", "middle")
    f.text(870, 353, "[ 7 ]", 17, INK, "700", "middle", mono=True)
    f.arrow(696, 235, 788, 240, PALETTE["red"][1])
    f.arrow(696, 330, 788, 335, PALETTE["red"][1])
    f.text(534, 420, "只是把形参 arr 改指向新数组，", 17)
    f.text(534, 446, "调用方的 bag 仍指向原数组。", 17, PALETTE["red"][1], "700")
    return f.save()


def position_copy():
    f = Fig("position-copy", "为什么改 transform.position.y 不生效", "position 是属性，取出来的 Vector3 是一份副本。", 500,
            "Vector3 是值类型：改副本不会改原物体，必须写回。")
    cols = [("① 取出", "Vector3 p = transform.position;", "(0, 0, 0)", "(0, 0, 0)", "blue"),
            ("② 改副本", "p.y = 5;", "(0, 0, 0)", "(0, 5, 0)", "orange"),
            ("③ 写回", "transform.position = p;", "(0, 5, 0)", "(0, 5, 0)", "green")]
    for i, (head, code, tv, pv, kind) in enumerate(cols):
        x = 32 + i * 326
        ink = PALETTE[kind][1]
        f.rect(x, 105, 284, 330, kind)
        f.text(x + 14, 137, head, 20, ink, "700")
        f.text(x + 14, 166, code, 13, mono=True, maxw=258)
        f.text(x + 142, 214, "物体的 position", 15, SUB, anchor="middle")
        f.chip(x + 142, 248, 220, 46, "white", tv, 18, mono=True)
        f.text(x + 142, 322, "局部变量 p（副本）", 15, SUB, anchor="middle")
        f.chip(x + 142, 356, 220, 46, "white", pv, 18, mono=True, bold=(i == 1))
        if i == 2:
            f.arrow(x + 232, 333, x + 232, 273, ink)
            f.text(x + 222, 297, "set：写回", 14, ink, anchor="end")
        elif i == 0:
            f.arrow(x + 232, 273, x + 232, 333, ink, dash=True)
            f.text(x + 222, 297, "get：复制一份", 14, ink, anchor="end")
        else:
            f.text(x + 142, 412, "物体没有动", 15, PALETTE["red"][1], "700", "middle")
    return f.save()


def boxing():
    f = Fig("boxing", "装箱与拆箱：值类型进出堆上的盒子", "值类型赋给 object 时，要在堆上新建一个对象保存副本。", 560,
            "频繁装箱会在堆上留下大量小对象，是 GC 卡顿的常见来源。")
    f.chip(120, 195, 160, 70, "blue", "int hp\n100", 18)
    f.text(120, 150, "局部变量（值类型）", 15, SUB, anchor="middle")
    f.rect(390, 140, 220, 120, "orange")
    f.text(500, 172, "堆上的盒子（对象）", 16, PALETTE["orange"][1], "700", "middle")
    f.text(500, 205, "类型信息：Int32", 15, INK, anchor="middle")
    f.text(500, 235, "值：100", 20, INK, "700", "middle", mono=True)
    f.chip(880, 195, 160, 70, "blue", "int back\n100", 18)
    f.text(880, 150, "局部变量（值类型）", 15, SUB, anchor="middle")
    f.path("M202 180C260 150 310 150 388 170", PALETTE["orange"][1])
    f.text(300, 128, "装箱：object boxed = hp;", 15, PALETTE["orange"][1], "700", "middle")
    f.path("M612 190C680 150 740 150 796 178", PALETTE["green"][1])
    f.text(705, 128, "拆箱：(int)boxed", 15, PALETTE["green"][1], "700", "middle")
    f.text(300, 232, "分配堆内存，拷贝值", 15, SUB, anchor="middle")
    f.text(705, 232, "类型必须精确匹配", 15, SUB, anchor="middle")
    f.box(32, 310, 450, 190, "red", "(long)boxed 会失败", [
        "盒子里装的是 int，不是 long。", "拆箱只能拆成原来的类型，", "否则抛 InvalidCastException。"])
    f.box(518, 310, 450, 190, "green", "正确写法：先拆再转", [
        "long ok = (int)boxed;", "先拆成 int，再隐式转换成 long。"], mono=False)
    return f.save()


def inherit_ctor():
    f = Fig("inherit-ctor", "继承：成员的组成与构造顺序", "子类 = 父类的成员 + 自己新增的成员；构造时父类先于子类。", 560,
            "父类没有无参构造函数时，子类必须用 : base(...) 指定。")
    # 左：继承树
    f.rect(32, 105, 450, 400, "blue")
    f.text(48, 137, "继承关系（箭头：子类 → 父类）", 19, PALETTE["blue"][1], "700")
    f.rect(130, 170, 250, 110, "white")
    f.text(255, 198, "class Entity", 18, PALETTE["blue"][1], "700", "middle", mono=True)
    f.text(255, 226, "name、protected hp", 15, INK, anchor="middle")
    f.text(255, 252, "Describe()", 15, INK, anchor="middle", mono=True)
    f.rect(52, 360, 205, 110, "green")
    f.text(154, 388, "class Player", 17, PALETTE["green"][1], "700", "middle", mono=True)
    f.text(154, 416, "新增：gold", 15, INK, anchor="middle")
    f.text(154, 442, "新增：Hurt()", 15, INK, anchor="middle", mono=True)
    f.rect(272, 360, 195, 110, "orange")
    f.text(370, 388, "class Enemy", 17, PALETTE["orange"][1], "700", "middle", mono=True)
    f.text(370, 416, "新增：Roar()", 15, INK, anchor="middle", mono=True)
    f.text(370, 442, "同时拥有 Entity 的全部", 13, INK, anchor="middle")
    f.arrow(154, 358, 220, 283, GREY)
    f.arrow(370, 358, 300, 283, GREY)
    # 右：构造顺序
    f.rect(518, 105, 450, 400, "green")
    f.text(534, 137, "new Player(\"勇者\") 的执行顺序", 19, PALETTE["green"][1], "700")
    steps = [("1", "进入 Player 构造函数", "public Player(string name) : base(name, 100)"),
             ("2", "先执行 Entity 构造函数", "this.name = name; this.hp = hp;"),
             ("3", "回到 Player 构造函数体", "Console.WriteLine(\"Player 构造完成\");")]
    for i, (n, head, code) in enumerate(steps):
        y = 170 + i * 105
        f.rect(534, y, 418, 88, "white")
        f.chip(566, y + 44, 36, 36, "green", n, 18, bold=True)
        f.text(596, y + 34, head, 17, INK, "700", maxw=350)
        f.text(596, y + 62, code, 12, SUB, mono=True, maxw=350)
        if i < 2:
            f.arrow(566, y + 90, 566, y + 103, GREY)
    f.text(534, 490, "先打好地基（父类），再盖楼（子类）。", 16, SUB)
    return f.save()


def polymorphism():
    f = Fig("polymorphism", "多态：调用点不变，实际执行谁由对象决定", "foreach 里只写 s.Damage(10)，三个对象各走各的版本。", 600,
            "变量的声明类型决定能调用什么，对象的真实类型决定执行谁的版本。")
    f.text(32, 118, "Skill[] book（元素类型是父类 Skill）", 17, PALETTE["blue"][1], "700")
    kinds = [("blue", "book[0]"), ("green", "book[1]"), ("orange", "book[2]")]
    objs = [("new Fireball()", "override Damage", "atk * 3", "30"),
            ("new Slash()", "override Damage", "atk * 2 + 5", "25"),
            ("new Skill()", "virtual Damage（默认）", "atk", "10")]
    for i, ((kind, slot), (cls, ov, expr, res)) in enumerate(zip(kinds, objs)):
        x = 32 + i * 326
        ink = PALETTE[kind][1]
        f.chip(x + 142, 160, 150, 40, "white", slot + "（引用）", 15, mono=False)
        f.arrow(x + 142, 182, x + 142, 232, ink)
        f.rect(x, 234, 284, 150, kind)
        f.text(x + 14, 264, cls, 17, ink, "700", mono=True)
        f.text(x + 14, 296, ov, 15, INK, maxw=256)
        f.text(x + 14, 326, "返回 " + expr, 16, INK, mono=True)
        f.text(x + 14, 360, "真实类型决定执行哪一份代码", 13, SUB)
        f.arrow(x + 142, 386, x + 142, 440, ink)
        f.text(x + 154, 418, "s.Damage(10)", 14, SUB, mono=True)
        f.chip(x + 142, 480, 150, 50, "white", "结果 " + res, 20, bold=True)
    f.text(32, 560, "新增一种技能，只需新增一个子类，上面的遍历代码一行都不用改。", 17, SUB)
    return f.save()


def static_members():
    f = Fig("static-members", "实例成员与静态成员：谁拥有这份数据", "每个对象各有一份实例字段；static 字段只有一份，属于类。", 520,
            "静态方法里没有“当前对象”，所以不能直接访问实例字段。")
    f.rect(260, 105, 480, 150, "purple")
    f.text(280, 137, "class Enemy（类本身）", 19, PALETTE["purple"][1], "700")
    f.text(280, 172, "public static int aliveCount = 2;", 16, INK, mono=True)
    f.text(280, 200, "全体共享，只有一份，用 Enemy.aliveCount 访问", 15, SUB)
    f.text(280, 228, "public static void PrintAlive()", 15, INK, mono=True)
    for i, (name, kind) in enumerate([("史莱姆", "blue"), ("哥布林", "green")]):
        x = 140 + i * 460 - 60 if False else (110 if i == 0 else 600)
        ink = PALETTE[kind][1]
        f.rect(x, 330, 290, 130, kind)
        f.text(x + 14, 360, f"对象：new Enemy(\"{name}\")", 17, ink, "700", maxw=262)
        f.text(x + 14, 394, f"name = \"{name}\"", 16, INK, mono=True)
        f.text(x + 14, 424, "每个对象各有一份 name", 15, SUB)
        f.arrow(x + 145, 328, 500 if i else 500, 257, ink, dash=True)
    f.text(500, 303, "构造时都执行 aliveCount++", 14, SUB, anchor="middle")
    return f.save()


def layermask():
    f = Fig("layermask", "LayerMask 就是一个整数：每一位对应一层", "以第 8 层 Enemy、第 9 层 Wall 为例，只画低 12 位。", 520,
            "射线检测的最后一个参数传 1 << 层编号，正是因为 mask 是按位表示的。")
    rows = [("1 << 8", "只包含 Enemy 层", "000100000000", "blue"),
            ("(1 << 8) | (1 << 9)", "Enemy 和 Wall 两层", "001100000000", "green"),
            ("~(1 << 8)", "除了 Enemy 之外的所有层", "111011111111", "orange")]
    x0, cw = 330, 50
    for b in range(12):
        f.text(x0 + (11 - b) * cw + cw / 2, 118, str(b), 14, SUB, anchor="middle")
    f.text(x0 - 12, 118, "位：", 14, SUB, anchor="end")
    for i, (expr, desc, bits, kind) in enumerate(rows):
        y = 150 + i * 105
        ink = PALETTE[kind][1]
        f.text(32, y + 28, expr, 17, ink, "700", mono=True, maxw=285)
        f.text(32, y + 56, desc, 15, SUB, maxw=285)
        for k, ch in enumerate(bits):
            on = ch == "1"
            f.rect(x0 + k * cw, y, cw - 4, 44, kind if on else "white", r=6, opacity="1" if on else ".35")
            f.text(x0 + k * cw + (cw - 4) / 2, y + 29, ch, 20, ink if on else GREY, "700" if on else None, "middle", mono=True)
    f.text(32, 462, "8 号位是 Enemy，9 号位是 Wall；1 表示“包含这一层”。", 16, SUB)
    return f.save()


def build_all():
    out = []
    for fn in (value_vs_ref, param_pass, position_copy, boxing, inherit_ctor, polymorphism, static_members, layermask):
        out += fn()
    return out
