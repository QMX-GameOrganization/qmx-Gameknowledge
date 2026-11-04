"""生成面向对象专题的语义图，并同步完整示例，避免正文与下载代码漂移。"""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "public/assets/oop"
DOCS = ROOT / "src/content/docs/knowledge/面向对象串讲"


def diagram(name, title, subtitle, rows, footer):
    """用固定网格呈现概念关系；限制每格行数以保证手机放大后仍可读。"""
    height = 180 + 176 * len(rows)
    colors = [("#eaf2ff", "#285caa"), ("#e8f7f1", "#176951"), ("#fff2df", "#8c5315")]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle + "。" + footer)}</desc>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10" fill="#66758d"/></marker></defs>',
        f'<rect width="1000" height="{height}" rx="18" fill="#f6f8fc"/>',
        '<g font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
        f'<text x="32" y="44" font-size="27" font-weight="700" fill="#15263e">{escape(title)}</text>',
        f'<text x="32" y="77" font-size="17" fill="#495b73">{escape(subtitle)}</text>',
    ]
    for ri, row in enumerate(rows):
        for ci, (heading, lines) in enumerate(row):
            x, y = 32 + ci * 326, 105 + ri * 176
            bg, ink = colors[ci]
            parts.extend([
                f'<rect x="{x}" y="{y}" width="284" height="144" rx="12" fill="{bg}" stroke="{ink}" stroke-opacity=".3"/>',
                f'<text x="{x+16}" y="{y+32}" font-size="20" font-weight="700" fill="{ink}">{escape(heading)}</text>',
            ])
            for li, line in enumerate(lines):
                parts.append(f'<text x="{x+16}" y="{y+65+li*26}" font-size="17" fill="#23364e">{escape(line)}</text>')
            if ci < len(row) - 1:
                parts.append(f'<path d="M{x+290} {y+72}H{x+318}" stroke="#66758d" stroke-width="2" marker-end="url(#arrow)"/>')
    parts.append(f'<text x="32" y="{height-20}" font-size="16" fill="#495b73">{escape(footer)}</text></g></svg>')
    (ASSETS / f"{name}.svg").write_text("\n".join(parts), encoding="utf-8")


def main():
    """生成可直接由静态站点发布的 SVG，不依赖前端图表插件。"""
    ASSETS.mkdir(parents=True, exist_ok=True)
    figures = [
        ("first-types", "先分清名字、类型与对象", "从熟悉的变量出发，一次只增加一层语法。", [
            [("int hp = 100", ["int：类型", "hp：变量", "100：初始值"]), ("namespace Game", ["给名字划分区域", "Game::Score 指定来源", "不创建游戏对象"]), ("enum class RoundState", ["定义有限选项的类型", "RoundState::Ready 是值", "不自动实现状态行为"])],
            [("class Score", ["定义自己的类型", "public：可用的操作", "private：内部状态"]), ("Score a; Score b;", ["创建两个独立对象", "a.addOne() 修改 a", "b 的分数不受影响"]), ("再学习生命周期", ["构造：建立初始状态", "析构：结束对象寿命", "后续逐步引入，不预设基础"])],
        ], ":: 限定名字所属范围；. 访问某个对象的成员。"),
        ("roadmap", "面向对象：把规则、变化与寿命串起来", "贯穿例子：角色受伤 → 多种技能 → 统一施放 → 安全释放。", [
            [("已有基础", ["vector：保存一组数据", "map：按键查询", "算法：完成计算"]), ("对象边界", ["哪些状态必须合法？", "谁可以修改它？", "调用方需要知道什么？"]), ("变化与协作", ["角色维护数值规则", "技能提供可替换行为", "流程控制施放顺序"])],
            [("C++ 语法", ["访问控制 / this / const", "构造 / 析构 / static", "复制 / 移动 / 继承"]), ("应用层层推进", ["先写明白一个角色", "再用不同技能统一调用", "比较相近写法与坑"]), ("用需求检验", ["添加治疗或护盾", "分析合理修改范围", "测量前不声称性能提升"])],
        ], "目标：说清每个类为何存在，而不只记住三大特性。"),
        ("boundary", "封装：让不变量有一个负责的边界", "不变量示例：0 ≤ hp ≤ maxHp；非法输入不能悄悄破坏状态。", [
            [("规则分散", ["攻击代码直接写 hp", "陷阱代码直接写 hp", "UI 调试也能写 hp"]), ("调用方各自检查", ["治疗上限可能漏掉", "负伤害可能变成治疗", "修改规则要到处搜索"]), ("维护成本增长", ["每个写入点都要懂内部", "语法能通过不代表合法", "Bug 随修改点扩散"])],
            [("外部只表达意图", ["takeDamage(amount)", "heal(amount)", "hp() 只读查询"]), ("Actor 维护规则", ["private hp_ / maxHp_", "校验输入", "先比较，再做有界运算"]), ("得到可靠结果", ["返回实际扣血 / 治疗量", "日志与 UI 使用同一结果", "规则变化集中验证"])],
        ], "private 只是访问控制；真正的封装还需要操作维护业务约束。"),
        ("lifetime", "生命周期：先构造，后使用，逆序清理", "作用域退出和异常展开，都应由已构造的资源对象承担清理。", [
            [("进入外层", ["构造 outer", "资源开始由它负责", "进入内部作用域"]), ("进入内层", ["构造 inner", "执行 work", "准备离开内部作用域"]), ("正常退出", ["先析构 inner", "执行 after", "最后析构 outer"])],
            [("某成员构造失败", ["当前完整对象尚未完成", "不会执行其完整析构", "异常向外传播"]), ("已构造部分清理", ["已完成的成员逆序析构", "已完成的基类析构", "成员 RAII 接管资源"]), ("调用方处理失败", ["catch 决定是否恢复", "不要依赖手工 delete", "强制终止不是普通退出"])],
        ], "局部 vector 的控制对象与动态元素存储可能在不同区域。"),
        ("ownership", "所有权与借用：先问谁负责释放", "箭头表达语义关系，不代表某个 ABI 的字段布局。", [
            [("值复制", ["Inventory a", "Inventory b = a", "各自拥有 vector<string>"]), ("独占移动", ["unique_ptr first 拥有对象", "second = move(first)", "此后 first 为空"]), ("非拥有借用", ["Actor& / const Actor&", "不负责 delete", "原对象必须仍然存活"])],
            [("vector<Actor>", ["扩容可搬移元素", "旧地址可能失效", "不能只看下标没变化"]), ("vector<unique_ptr<Actor>>", ["扩容搬移拥有指针", "角色本体通常不搬移", "删除所有者仍让借用失效"]), ("共享也有契约", ["shared_ptr 延长寿命", "weak_ptr 只观察", "引用计数不保护对象内容"])],
        ], "有地址 ≠ 有所有权；能访问 ≠ 可以释放；只读 ≠ 自动延长寿命。"),
        ("composition", "继承与组合：按契约和变化维度判断", "不要仅为了复用字段，把所有特性塞进一棵继承树。", [
            [("继承堆特性", ["Enemy → FlyingEnemy", "→ FireFlyingEnemy", "→ RangedFireFlyingEnemy"]), ("组合数量增长", ["再加冰属性怎么办？", "地面远程又要复制分支", "共同规则容易散落"]), ("先拆变化维度", ["移动方式", "技能与装备", "属性配置"])],
            [("Actor has-an Armor", ["角色组合护甲", "拥有或借用要说明", "角色不是护甲的一种"]), ("Actor has Skills", ["同一角色替换技能", "独立配置数值", "不靠深继承扩展特性"]), ("Fireball is-a Skill", ["满足施放契约", "可被调用方当技能使用", "不能偷偷加强前置要求"])],
        ], "可替换性支持公共继承；独立组合的能力通常适合成员协作。"),
        ("dispatch", "动态多态：同一个调用点，不同实现", "静态类型决定可见接口；虚分派选择实际对象的实现。", [
            [("perform(const Skill&)", ["只知道 Skill 的契约", "调用 skill.cast(target)", "不检查具体技能名字"]), ("引用真实 Fireball", ["动态类型：Fireball", "进入火球的 cast", "使用目标的受伤规则"]), ("或引用 HealSkill", ["动态类型：HealSkill", "进入治疗的 cast", "使用目标的治疗规则"])],
            [("virtual", ["声明可重写行为", "= 0 表示纯虚函数", "抽象类不能直接实例化"]), ("override", ["检查是否确实重写", "参数和 const 要匹配", "不是同名就一定重写"]), ("virtual ~Skill()", ["支持通过基类删除", "unique_ptr<Skill> 可拥有", "分派不能修复悬空访问"])],
        ], "虚表是常见实现解释；精确布局、开销与优化必须依实现分析。"),
        ("architecture", "稳定流程与变化点分开", "注册处认识具体类型，使用处依赖行为契约。", [
            [("组装 main", ["选择 DamageSkill", "选择 HealSkill", "用 unique_ptr 持有"]), ("调度 runRound", ["顺序借用每个 Skill", "不按技能名字分支", "不拥有目标和日志流"]), ("契约 Skill", ["cast(Actor&, ostream&)", "具体技能提供效果", "公开虚析构负责正确销毁"])],
            [("数值变化", ["20 → 50", "修改配置参数", "不新建一个伤害子类"]), ("行为变化", ["攻击 → 治疗", "新增实现 + 组装注册", "不修改稳定调度循环"]), ("领域规则变化", ["生命值上限 / 护甲", "修改 Actor 的规则", "更新规则相关验证"])],
        ], "开闭原则保护稳定边界，不承诺新增功能零修改。"),
        ("battle-flow", "一回合：用真实数值追踪调用链", "目标：最大生命值 100，护甲 8；治疗不受护甲影响。", [
            [("开始：hp = 100", ["Slash 原始伤害 20", "护甲减去 8", "实际伤害 12"]), ("斩击后：hp = 88", ["Fireball 原始伤害 35", "护甲减去 8", "实际伤害 27"]), ("火球后：hp = 61", ["Heal 请求恢复 25", "空间 100 - 61 = 39", "实际恢复 25"])],
            [("技能：表达效果", ["DamageSkill / HealSkill", "不直接写生命值字段", "取得实际生效量"]), ("角色：维护合法状态", ["takeDamage / heal", "边界和溢出检查", "最终 hp = 86"]), ("流程：负责次序", ["不区分具体技能类别", "输出施放日志", "断言验证输出与边界"])],
        ], "护甲规则是本例的教学约定；真实项目先明确需求再实现。"),
        ("static", "static：实例独立，共享数据集中一份", "累计创建数不是存活数；静态成员函数没有隐含 this。", [
            [("Actor a", ["独立 id_ = 1", "独立 hp_ = 100", "a 的生命值可单独改变"]), ("Actor 类型共享", ["inline static created_ = 2", "a 与 b 使用同一份计数", "不存入每个实例各一份"]), ("Actor b", ["独立 id_ = 2", "独立 hp_ = 100", "b 销毁不减少累计数"])],
            [("普通成员函数", ["有隐含 this", "通过当前对象访问成员", "可声明为 const 成员"]), ("静态成员函数", ["Actor::totalCreated()", "没有隐含 this", "不能是 const 或 virtual"]), ("其他位置的 static", ["局部：跨调用保留对象", "文件作用域：内部链接", "不要与类共享成员混淆"])],
        ], "初始化线程安全不等于修改共享计数线程安全。"),
        ("inheritance", "构造先准备依赖，析构反向结束", "普通单继承示例：Elite : public Actor，并组合 Equipment。", [
            [("① Actor 基类", ["先执行基类构造", "初始化基类状态", "派生体还没开始工作"]), ("② Equipment 成员", ["按成员声明顺序构造", "不按初始化列表排列", "成员已经准备好"]), ("③ Elite 构造体", ["最后执行派生函数体", "可使用基类与成员", "完整派生对象建立"])],
            [("④ Elite 析构体", ["先执行派生清理代码", "此时成员尚在", "然后进入自动清理"]), ("⑤ Equipment 析构", ["成员按声明逆序销毁", "结束其资源责任", "不手工重复析构成员"]), ("⑥ Actor 析构", ["最后结束基类部分", "基类指针删除另有契约", "需要时使用虚析构"])],
        ], "存在虚基类或多基类时，应继续按对应规则展开。"),
        ("members", "this 与 const：函数操作哪一个对象", "相同成员函数定义可被不同实例使用，各自访问对应状态。", [
            [("hero.setLevel(3)", ["this 指向 hero", "参数 level = 3", "this->level 是成员"]), ("hero 的成员状态", ["level 变为 3", "不是修改所有 Actor", "不是给参数自身赋值"]), ("enemy 的成员状态", ["仍保留自己的 level", "没有被这次调用修改", "除非明确共享或别名"])],
            [("const Actor& view", ["借用同一个 hero", "不创建角色副本", "通过该视图只读"]), ("view.getLevel()", ["调用 const 成员函数", "可以读取普通成员", "不承诺线程安全"]), ("view.setLevel(9)", ["非 const 修改操作", "编译器拒绝这次调用", "对象其他别名另有规则"])],
        ], "Actor& 返回当前对象可链式调用；返回局部引用会悬空。"),
        ("construction", "初始化与赋值：时间和约束不同", "创建成功就应得到合法角色，不依赖调用方记住 init。", [
            [("① 参数进入构造", ["Actor(name, maxHp)", "输入表示创建需求", "构造函数没有返回类型"]), ("② 初始化成员", ["name_(name)", "maxHp_(maxHp)", "hp_(maxHp)"]), ("③ 执行函数体", ["校验业务条件", "成功则完成对象创建", "失败抛异常，不交付对象"])],
            [("初始化列表", ["直接建立成员初始状态", "适合 const / 引用成员", "顺序按成员声明"]), ("函数体赋值", ["成员已先按规则初始化", "再执行已有对象赋值", "不能补绑引用成员"]), ("explicit", ["保留显式创建", "阻止不希望的隐式转换", "不等于禁止正常复制"])],
        ], "类成员未提供所需初始化时，不应指望进入函数体再补救。"),
    ]
    for fig in figures:
        diagram(*fig)
    # 目录页本身也占一个路由段，跳转同级文章需要先返回父级。
    index = DOCS / "目录.md"
    index.write_text(index.read_text(encoding="utf-8").replace("](./", "](../"), encoding="utf-8")
    for chapter, source, marker, lang in [
        ("18-battle-lab.md", "battle.cpp", "OOP_CPP_SOURCE", "cpp"),
    ]:
        path = DOCS / chapter
        text = path.read_text(encoding="utf-8")
        code = (ROOT / "public/examples/oop" / source).read_text(encoding="utf-8").rstrip()
        block = f"<!-- {marker} -->\n\n```{lang}\n{code}\n```\n\n<!-- END_{marker} -->"
        text = re.sub(rf"<!-- {marker} -->(?:.*?<!-- END_{marker} -->)?", lambda _: block, text, flags=re.S)
        path.write_text(text, encoding="utf-8")
    # 目录排第一，其后按编号排序，避免 00 与 01 同序。
    for path in DOCS.glob("[0-9][0-9]-*.md"):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"order: \d+", f"order: {int(path.name[:2])+1}", text, count=1)
        path.write_text(text, encoding="utf-8")
    print(f"generated {len(figures)} SVG figures; synchronized 1 complete example")


if __name__ == "__main__":
    main()
