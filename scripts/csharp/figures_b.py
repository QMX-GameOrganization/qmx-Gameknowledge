"""第 5、6 章与 Unity 引导章用到的配图。"""
from svglib import Fig, GREY, SUB, INK, PALETTE


def object_pool():
    f = Fig("object-pool", "对象池：用完放回去，下次直接复用", "子弹、特效、伤害数字每秒创建销毁很多次，复用比反复 new 省得多。", 570,
            "对象池的代价：取出来的对象要重置状态，否则会带着上一次的数据。")
    f.rect(32, 110, 380, 290, "blue")
    f.text(48, 142, "池（Stack<Bullet>）：空闲的子弹", 18, PALETTE["blue"][1], "700")
    for i in range(3):
        f.chip(222, 200 + i * 62, 220, 46, "white", f"空闲子弹 #{i + 1}", 16)
    f.text(48, 380, "用 Stack 保存，后放回的先取出。", 15, SUB)
    f.rect(588, 110, 380, 290, "green")
    f.text(604, 142, "场景中：正在使用的子弹", 18, PALETTE["green"][1], "700")
    for i in range(3):
        f.chip(778, 200 + i * 62, 220, 46, "white", f"飞行中的子弹 #{i + 4}", 16)
    f.text(604, 380, "命中目标或飞出屏幕后就回收。", 15, SUB)
    f.arrow(414, 215, 586, 215, PALETTE["blue"][1])
    f.text(500, 200, "Get()", 17, PALETTE["blue"][1], "700", "middle", mono=True)
    f.text(500, 238, "弹出一个", 14, SUB, anchor="middle")
    f.arrow(586, 330, 414, 330, PALETTE["green"][1])
    f.text(500, 315, "Release()", 17, PALETTE["green"][1], "700", "middle", mono=True)
    f.text(500, 353, "放回池里", 14, SUB, anchor="middle")
    f.box(32, 420, 380, 70, "red", None, ["池是空的才 new Bullet()", "新建一个，会产生垃圾"], 16)
    f.arrow(414, 455, 640, 402, PALETTE["red"][1], dash=True)
    return f.save()


def event_flow():
    f = Fig("event-flow", "事件：发布者只管通知，不认识订阅者", "血量变化时，血条、音效、成就各自响应，Player 的代码一行都不用改。", 640,
            "订阅用 +=，不用时必须用 -= 取消订阅。")
    f.chip(120, 250, 170, 80, "grey", "子弹命中\nTakeDamage(30)", 15)
    f.arrow(205, 250, 330, 250, GREY)
    f.rect(335, 160, 290, 190, "blue")
    f.text(480, 192, "Player（发布者）", 19, PALETTE["blue"][1], "700", "middle")
    f.text(350, 226, "public event Action<int,int>", 13, INK, mono=True, maxw=262)
    f.text(350, 248, "    OnHpChanged;", 13, INK, mono=True)
    f.text(350, 286, "hp 变化后调用：", 15, SUB)
    f.text(350, 312, "OnHpChanged?.Invoke(old, hp);", 13, INK, mono=True, maxw=262)
    subs = [("HpBar（血条）", "刷新血条长度", "green"), ("AudioPlayer（音效）", "播放受伤音效", "orange"),
            ("Achievements（成就）", "统计累计受伤", "purple")]
    for i, (name, what, kind) in enumerate(subs):
        y = 118 + i * 112
        f.rect(700, y, 268, 92, kind)
        f.text(714, y + 30, name, 17, PALETTE[kind][1], "700", maxw=240)
        f.text(714, y + 58, what, 15, INK)
        f.text(714, y + 80, "OnEnable：+=  OnDisable：-=", 12, SUB, mono=True, maxw=240)
        f.arrow(627, 255, 698, y + 46, PALETTE[kind][1])
    f.box(32, 462, 450, 130, "green", "好处：解耦", [
        "Player 不知道有血条存在。", "新增订阅者，不用改 Player。"], 16)
    f.box(518, 462, 450, 130, "red", "陷阱：忘记取消订阅", [
        "订阅者销毁后，事件仍持有它的引用。", "下次触发会调用到已销毁的对象。"], 16)
    return f.save()


def closure():
    f = Fig("closure", "闭包捕获的是变量，不是当时的值", "for 循环里的 lambda 全共享同一个循环变量 i。", 520,
            "修正办法：在循环体内复制一份局部变量，让每个 lambda 捕获自己的那一份。")
    f.rect(32, 105, 450, 360, "red")
    f.text(48, 137, "直接捕获 i：只有一个 i", 19, PALETTE["red"][1], "700")
    f.text(48, 166, "actions.Add(() => Console.WriteLine(i));", 13, mono=True, maxw=420)
    for k in range(3):
        f.chip(110, 215 + k * 58, 130, 42, "white", f"lambda {k}", 15)
        f.arrow(176, 215 + k * 58, 318, 290, PALETTE["red"][1])
    f.rect(320, 250, 130, 80, "white")
    f.text(385, 280, "变量 i", 15, SUB, anchor="middle")
    f.text(385, 314, "= 3", 26, PALETTE["red"][1], "700", "middle")
    f.text(48, 410, "循环结束时 i 已经是 3，", 16)
    f.text(48, 436, "三个 lambda 都输出：3 3 3", 17, PALETTE["red"][1], "700")
    f.rect(518, 105, 450, 360, "green")
    f.text(534, 137, "每轮复制一份：int copy = i;", 19, PALETTE["green"][1], "700")
    f.text(534, 166, "actions.Add(() => Console.WriteLine(copy));", 13, mono=True, maxw=420)
    for k in range(3):
        y = 215 + k * 58
        f.chip(600, y, 130, 42, "white", f"lambda {k}", 15)
        f.arrow(666, y, 780, y, PALETTE["green"][1])
        f.chip(850, y, 120, 42, "white", f"copy = {k}", 16, mono=True)
    f.text(534, 410, "每轮都有一个新的 copy，", 16)
    f.text(534, 436, "三个 lambda 分别输出：0 1 2", 17, PALETTE["green"][1], "700")
    return f.save()


def variance():
    f = Fig("variance", "协变与逆变：什么时候子类的泛型能当父类用", "判断依据：T 在这个类型里是“只出来”还是“只进去”。", 560,
            "List<T> 既能读又能写，所以不允许互换；只读的 IEnumerable<T> 允许。")
    f.chip(120, 125, 120, 40, "blue", "Entity", 17, mono=True, bold=True)
    f.chip(300, 125, 120, 40, "green", "Player", 17, mono=True, bold=True)
    f.arrow(238, 125, 182, 125, GREY)
    f.arrow(240, 125, 182, 125, GREY) if False else None
    f.text(378, 131, "Player 是一种 Entity", 15, SUB, anchor="start")
    rows = [("green", "IEnumerable<Player>  →  IEnumerable<Entity>", "允许：协变（out）",
             "T 只用来返回（读出），不能放入，所以安全。"),
            ("red", "List<Player>  →  List<Entity>", "不允许：不变",
             "否则能 Add(new Enemy()) 把敌人塞进玩家列表。"),
            ("blue", "Action<Entity>  →  Action<Player>", "允许：逆变（in）",
             "能处理任何 Entity 的函数，当然能处理 Player。")]
    for i, (kind, types, verdict, why) in enumerate(rows):
        y = 170 + i * 120
        ink = PALETTE[kind][1]
        f.rect(32, y, 936, 104, kind)
        f.text(52, y + 36, types, 19, INK, "700", mono=True, maxw=560)
        f.text(52, y + 70, why, 16, INK, maxw=620)
        f.chip(840, y + 52, 190, 50, "white", verdict, 16, bold=True)
    return f.save()


def race():
    f = Fig("race", "数据竞争：counter++ 不是一步完成的", "它分三步：读、加、写。两个线程交错执行时，会互相覆盖。", 660,
            "lock 保证同一时刻只有一个线程执行这一段代码。")
    cols = [330, 490, 650, 810]
    # 上：无保护
    f.rect(32, 105, 936, 230, "red")
    f.text(48, 135, "不加锁：期望 counter 变成 7，实际只是 6", 18, PALETTE["red"][1], "700")
    for y, name in ((175, "线程 A"), (225, "线程 B"), (280, "counter")):
        f.text(64, y + 5, name, 16, INK, "700")
    f.chip(cols[0], 172, 140, 36, "white", "读到 5", 15)
    f.chip(cols[2], 172, 140, 36, "white", "写入 6", 15)
    f.chip(cols[1], 222, 140, 36, "white", "读到 5（旧值）", 14)
    f.chip(cols[3], 222, 140, 36, "white", "写入 6", 15)
    for c, v in zip(cols, ("5", "5", "6", "6")):
        f.chip(c, 280, 70, 36, "grey", v, 17, mono=True, bold=True)
    f.text(480, 322, "B 读的时候 A 还没写回，两次加 1 变成了一次。", 15, PALETTE["red"][1], anchor="middle")
    # 下：lock
    f.rect(32, 355, 936, 245, "green")
    f.text(48, 385, "加 lock：B 等 A 做完再进去", 18, PALETTE["green"][1], "700")
    for y, name in ((425, "线程 A"), (475, "线程 B"), (530, "counter")):
        f.text(64, y + 5, name, 16, INK, "700")
    f.rect(260, 407, 300, 36, "white", r=8)
    f.text(410, 431, "持锁：读 5 → 写 6", 15, INK, anchor="middle")
    f.rect(260, 457, 300, 36, "grey", r=8, dash=True)
    f.text(410, 481, "等待锁……", 15, SUB, anchor="middle")
    f.rect(580, 457, 300, 36, "white", r=8)
    f.text(730, 481, "持锁：读 6 → 写 7", 15, INK, anchor="middle")
    for c, v in zip((330, 490, 650, 810), ("5", "6", "6", "7")):
        f.chip(c, 530, 70, 36, "grey", v, 17, mono=True, bold=True)
    f.text(480, 576, "结果是 7，每次都对。", 15, PALETTE["green"][1], "700", "middle")
    return f.save()


def lifecycle():
    f = Fig("lifecycle", "MonoBehaviour 生命周期：引擎按这个顺序调用你的函数", "你只负责写函数，调用时机由引擎决定。", 710,
            "Awake 管自己，Start 管别人；每帧的逻辑写在 Update。")
    # 第一行：初始化
    f.rect(32, 100, 936, 150, "green")
    f.text(48, 128, "创建与启用（每个脚本只发生一次，OnEnable 每次启用都会再调用）", 16, PALETTE["green"][1], "700")
    steps = [("Awake", "脚本实例刚创建时", "初始化自己、缓存 GetComponent"),
             ("OnEnable", "脚本被启用时", "订阅事件"),
             ("Start", "第一次 Update 之前", "依赖别的对象的初始化")]
    for i, (n, when, use) in enumerate(steps):
        x = 52 + i * 302
        f.rect(x, 146, 270, 92, "white")
        f.text(x + 14, 172, n, 18, PALETTE["green"][1], "700", mono=True)
        f.text(x + 14, 198, when, 14, INK)
        f.text(x + 14, 222, use, 14, SUB, maxw=245)
        if i < 2:
            f.arrow(x + 272, 192, x + 298, 192, PALETTE["green"][1])
    f.arrow(500, 252, 500, 280, GREY)
    # 第二行：每帧循环
    f.rect(32, 282, 936, 232, "blue")
    f.text(48, 310, "每一帧重复（直到物体被禁用或销毁）", 16, PALETTE["blue"][1], "700")
    loop = [("FixedUpdate", "固定间隔，默认 0.02 秒", "物理：加力、刚体"),
            ("Update", "每帧一次", "输入、移动、游戏逻辑"),
            ("LateUpdate", "所有 Update 之后", "相机跟随"),
            ("渲染", "引擎画出这一帧", "你不需要写代码")]
    for i, (n, when, use) in enumerate(loop):
        x = 52 + i * 227
        f.rect(x, 328, 205, 120, "white")
        f.text(x + 12, 356, n, 16 if i < 3 else 17, PALETTE["blue"][1], "700", mono=(i < 3))
        f.text(x + 12, 384, when, 13, INK, maxw=182)
        f.text(x + 12, 410, use, 13, SUB, maxw=182)
        if i < 3:
            f.arrow(x + 207, 388, x + 225, 388, PALETTE["blue"][1])
    f.path("M850 450C850 476 150 476 150 450", PALETTE["blue"][1], dash=True)
    f.text(500, 496, "下一帧，回到开头", 14, SUB, anchor="middle")
    f.arrow(500, 516, 500, 546, GREY)
    # 第三行：结束
    f.rect(32, 548, 936, 120, "orange")
    f.text(48, 576, "禁用与销毁", 16, PALETTE["orange"][1], "700")
    ends = [("OnDisable", "脚本被禁用或物体停用", "取消订阅事件"), ("OnDestroy", "物体被销毁时", "释放资源、清理")]
    for i, (n, when, use) in enumerate(ends):
        x = 52 + i * 302
        f.rect(x, 590, 270, 66, "white")
        f.text(x + 14, 614, n, 17, PALETTE["orange"][1], "700", mono=True)
        f.text(x + 14, 636, when + "，" + use, 12, SUB, maxw=245)
    f.arrow(324, 623, 350, 623, PALETTE["orange"][1])
    return f.save()


def coroutine_timeline():
    f = Fig("coroutine-timeline", "协程：被引擎每帧推进一小段的函数", "它不是新线程，仍然在主线程里一段一段地运行。", 520,
            "yield return 就是“先暂停，等条件满足再从这里继续”。")
    cx = [110 + 156 * i for i in range(6)]
    heads = ["第 1 帧", "第 2 帧", "第 3 帧", "第 4 帧", "第 5 帧", "第 n 帧"]
    f.rect(32, 105, 936, 140, "grey")
    f.text(48, 133, "主线程：每帧都在做的事", 16, PALETTE["grey"][1], "700")
    for c, h in zip(cx, heads):
        f.text(c, 168, h, 15, SUB, anchor="middle")
        f.chip(c, 206, 136, 44, "white", "Update\n渲染", 14)
    f.rect(32, 262, 936, 170, "green")
    f.text(48, 290, "协程 CooldownRoutine（StartCoroutine 启动）", 16, PALETTE["green"][1], "700")
    texts = ["执行到\nyield return\nnull", "继续执行\n遇到 yield\nWaitFor-\nSeconds(2)", "休眠", "休眠", "休眠", "2 秒到了\n继续往下执行"]
    for i, (c, t) in enumerate(zip(cx, texts)):
        if t == "休眠":
            f.rect(c - 68, 312, 136, 100, "white", r=8, dash=True)
            f.text(c, 368, "休眠", 16, GREY, anchor="middle")
        else:
            f.chip(c, 362, 136, 100, "white", t, 14, bold=(i in (0, 5)))
    f.text(32, 470, "休眠期间协程几乎不占用时间，引擎每帧只检查一下条件是否满足。", 16, SUB)
    return f.save()


def roadmap():
    f = Fig("roadmap", "C# 速通路线：先认识 Unity，再边写边学", "每一章都带着 Unity 里的用法，读完就可以动手做小项目。", 690,
            "时间紧：先读 0.3、2.3、3.3、4.3、5.2，再回头补其余。")
    cards = [("0 先认识 Unity", "游戏循环、物体与组件", "脚本为什么能“自己跑起来”", "purple"),
             ("1 入门", "类型、转换、字符串", "Debug.Log、LayerMask", "blue"),
             ("2 基础", "枚举、数组、值/引用类型", "Inspector 里的数据", "green"),
             ("3 封装", "类、属性、静态", "脚本就是类，物体上的组件", "orange"),
             ("4 继承与多态", "继承、接口、装箱", "IDamageable 统一受伤", "blue"),
             ("5 进阶", "泛型、事件、多线程", "对象池、事件、UI 回调", "green"),
             ("6 综合与速查", "协程与小项目", "做出会动会死的小角色", "orange")]
    pos = [(32, 110), (358, 110), (684, 110), (32, 290), (358, 290), (684, 290), (358, 470)]
    for (x, y), (title, a, b, kind) in zip(pos, cards):
        ink = PALETTE[kind][1]
        f.rect(x, y, 284, 148, kind)
        f.text(x + 14, y + 32, title, 20, ink, "700")
        f.text(x + 14, y + 66, "C#：" + a, 15, INK, maxw=256)
        f.text(x + 14, y + 94, "Unity：" + b, 15, INK, maxw=256)
    f.arrow(318, 184, 356, 184, GREY)
    f.arrow(644, 184, 682, 184, GREY)
    f.arrow(318, 364, 356, 364, GREY)
    f.arrow(644, 364, 682, 364, GREY)
    f.path("M826 260C826 275 175 270 175 288", GREY, dash=True)
    f.path("M826 440C826 455 500 452 500 468", GREY, dash=True)
    return f.save()


def game_loop():
    f = Fig("game-loop", "游戏是怎么跑起来的：一帧一帧地循环", "画面每秒刷新几十次，每刷新一次叫一帧，每一帧都重复同一套流程。", 600,
            "你写的脚本不是从头跑到尾，而是被这个循环一帧一帧地反复调用。")
    f.rect(32, 105, 936, 80, "green")
    f.text(48, 138, "启动一次：加载场景 → 创建场景里的物体 → 依次调用 Awake / OnEnable / Start", 17, PALETTE["green"][1], "700", maxw=900)
    f.text(48, 166, "这些只发生一次。之后进入下面的循环，直到你退出游戏。", 15, SUB)
    f.arrow(500, 187, 500, 214, GREY)
    f.rect(32, 216, 936, 212, "blue")
    f.text(48, 244, "每一帧（60 帧每秒时，一帧约 16.7 毫秒）", 17, PALETTE["blue"][1], "700")
    steps = [("① 读取输入", "键盘、鼠标、手柄"), ("② 物理更新", "FixedUpdate 固定步长"),
             ("③ 游戏逻辑", "Update：你的主要代码"), ("④ 收尾", "LateUpdate：相机跟随"), ("⑤ 渲染画面", "把这一帧画到屏幕上")]
    for i, (a, b) in enumerate(steps):
        x = 48 + i * 186
        f.rect(x, 262, 168, 100, "white")
        f.text(x + 84, 296, a, 16, PALETTE["blue"][1], "700", "middle", maxw=150)
        f.text(x + 84, 326, b, 13, INK, anchor="middle", maxw=156)
        if i < 4:
            f.arrow(x + 169, 312, x + 185, 312, PALETTE["blue"][1])
    f.path("M900 366C900 392 100 392 100 366", PALETTE["blue"][1], dash=True)
    f.text(500, 410, "下一帧：回到 ①", 14, SUB, anchor="middle")
    f.box(32, 448, 450, 100, "orange", "为什么移动要乘 Time.deltaTime", [
        "帧率不固定，每帧耗时不同。", "距离 = 速度 × 这一帧的耗时。"], 16)
    f.box(518, 448, 450, 100, "purple", "“每帧一次”意味着什么", [
        "Update 里的代码一秒会跑几十次，", "所以要避免在里面做重活。"], 16)
    return f.save()


def scene_components():
    f = Fig("scene-components", "场景、物体与组件：Unity 世界的三层结构", "物体本身什么都不会做，它的能力全部来自挂在上面的组件。", 640,
            "你写的脚本也是一种组件：C# 类的一个实例，挂在物体上。")
    f.rect(32, 105, 300, 440, "blue")
    f.text(48, 137, "场景 Scene", 19, PALETTE["blue"][1], "700")
    f.text(48, 162, "一个关卡里所有物体的集合", 14, SUB)
    objs = ["Main Camera", "Directional Light", "Player", "Enemy_1", "Enemy_2", "Ground"]
    for i, n in enumerate(objs):
        sel = n == "Player"
        f.rect(52, 184 + i * 56, 260, 44, "orange" if sel else "white", r=8)
        f.text(66, 212 + i * 56, ("▶ " if sel else "") + n, 16, PALETTE["orange"][1] if sel else INK, "700" if sel else None, mono=True)
    f.text(48, 530, "每一项是一个 GameObject（物体）", 14, SUB)
    f.arrow(314, 352, 388, 352, PALETTE["orange"][1])
    f.rect(390, 105, 578, 440, "orange")
    f.text(406, 137, "GameObject：Player（点开 Inspector 看到的组件）", 19, PALETTE["orange"][1], "700")
    comps = [("Transform", "位置、旋转、缩放。每个物体都有，不能删。", "blue"),
             ("MeshRenderer", "负责把模型画出来，决定外观。", "green"),
             ("Rigidbody + Collider", "物理：受重力、会碰撞。", "grey"),
             ("PlayerController（你的脚本）", "你写的 C# 类，决定它怎么动、怎么受伤。", "purple")]
    for i, (n, d, kind) in enumerate(comps):
        y = 168 + i * 92
        ink = PALETTE[kind][1]
        f.rect(410, y, 538, 78, kind, opacity="1" if kind == "purple" else ".3")
        f.text(426, y + 30, n, 18, ink, "700", maxw=500)
        f.text(426, y + 58, d, 15, INK, maxw=500)
    f.text(406, 538, "换一组组件，就是另一种物体：给它不同的脚本，它就有不同的行为。", 14, SUB)
    f.text(32, 590, "类比：GameObject 像空的手办底座，组件像可插拔的零件，脚本是你亲手做的那个零件。", 16, SUB)
    return f.save()


def script_engine():
    f = Fig("script-engine", "脚本与引擎：谁调用谁", "你不写 Main，也不写游戏循环：写好类，挂到物体上，剩下的交给引擎。", 650,
            "Inspector 里的字段值保存在场景里，运行时由引擎填进你的脚本。")
    f.rect(32, 105, 380, 380, "blue")
    f.text(48, 137, "Unity 引擎", 20, PALETTE["blue"][1], "700")
    f.text(48, 163, "持有场景、物体、游戏循环", 14, SUB)
    for i, t in enumerate(["游戏循环", "场景里的所有物体", "物理、渲染、输入", "Inspector 序列化数据"]):
        f.chip(222, 215 + i * 62, 300, 44, "white", t, 16)
    f.rect(588, 105, 380, 380, "purple")
    f.text(604, 137, "你的脚本 class Player : MonoBehaviour", 17, PALETTE["purple"][1], "700", maxw=350)
    f.text(604, 163, "你写的 C# 代码", 14, SUB)
    for i, t in enumerate(["void Awake() / Start()", "void Update()", "void OnCollisionEnter(...)", "[SerializeField] int hp"]):
        f.chip(778, 215 + i * 62, 320, 44, "white", t, 15, mono=True)
    f.arrow(414, 245, 586, 245, PALETTE["blue"][1])
    f.text(500, 228, "① 引擎调用", 15, PALETTE["blue"][1], "700", "middle")
    f.text(500, 270, "合适的时机", 13, SUB, anchor="middle")
    f.arrow(586, 345, 414, 345, PALETTE["purple"][1])
    f.text(500, 328, "② 你调用", 15, PALETTE["purple"][1], "700", "middle")
    f.text(500, 370, "引擎提供的 API", 13, SUB, anchor="middle")
    f.box(32, 505, 450, 70, "grey", None, ["transform、GetComponent、Instantiate、", "Debug.Log、Input、Time 都是引擎的 API"], 14)
    f.box(518, 505, 450, 70, "grey", None, ["Awake、Start、Update 这些名字固定，", "引擎靠名字找到并调用它们"], 14)
    return f.save()


def build_all():
    out = []
    for fn in (object_pool, event_flow, closure, variance, race, lifecycle, coroutine_timeline, roadmap,
               game_loop, scene_components, script_engine):
        out += fn()
    return out
