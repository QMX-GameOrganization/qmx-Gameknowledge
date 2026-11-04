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
            [("C++ 语义", ["值复制 / 移动", "构造 / 析构 / RAII", "拥有 / 借用"]), ("用需求检验", ["添加治疗技能", "保持战斗循环不变", "检查成本和失败边界"]), ("迁移到 C#", ["class 赋值复制引用", "GC 与 Dispose 分开", "再连接 Unity 与 ECS"])],
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
        ("csharp", "迁移到 C#：相似语法，先核对语义", "尤其区分类赋值、结构体字段复制与资源释放。", [
            [("C++ Actor b = a", ["构造一个新 Actor", "按成员复制语义处理", "是否共享看成员类型"]), ("C# class：b = a", ["复制引用", "a 和 b 指向同一角色", "b 修改后 a 能看到"]), ("C# struct：b = a", ["复制字段", "List 字段仍是共享引用", "不保证全部数据独立"])],
            [("C++", ["作用域析构 / RAII", "unique_ptr 独占拥有", "析构不是自动 GC"]), ("C#", ["GC 按可达性管理内存", "using 安排 Dispose", "终结器不是作用域析构"]), ("Unity", ["还存在引擎原生对象", "Destroy 与 GC 分开", "注意事件解绑和池化复位"])],
        ], "封装和契约的思考可以迁移；复制与生命周期规则必须重新确认。"),
    ]
    for fig in figures:
        diagram(*fig)
    # 目录页本身也占一个路由段，跳转同级文章需要先返回父级。
    index = DOCS / "目录.md"
    index.write_text(index.read_text(encoding="utf-8").replace("](./", "](../"), encoding="utf-8")
    for chapter, source, marker, lang in [
        ("09-battle-lab.md", "battle.cpp", "OOP_CPP_SOURCE", "cpp"),
        ("10-csharp-bridge.md", "Battle.cs", "OOP_CS_SOURCE", "csharp"),
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
    print(f"generated {len(figures)} SVG figures; synchronized 2 complete examples")


if __name__ == "__main__":
    main()
