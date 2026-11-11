from pathlib import Path
import importlib.util, json
spec=importlib.util.spec_from_file_location('draw','artifacts/ue-movement/draw_diagrams.py'); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
s=m.canvas('GASP 滑行转换：迟滞区避免反复切换','按实际 Evaluate 引脚绘制 · 比较的是 ProposedMove 的水平速度',670)
m.box(s,40,140,460,125,'Walking → Sliding',['水平提案速度 > 380','AND 蹲伏 Gameplay Tag 为真'])
m.box(s,620,140,460,125,'Sliding → Walking',['水平提案速度 <= 200','OR CharacterMover.IsCrouching() 为假'])
m.arrow(s,500,200,620,200)
m.box(s,40,330,1040,120,'200 < 速度 <= 380：进入和退出不是同一个阈值',['保持蹲伏时，刚进入这个区间不会仅因速度条件立即触发相反转换。','转换是否被调用，还取决于模式实例的 Transitions 配置和状态机执行。'],'#e1f2eb')
m.box(s,40,490,1040,115,'蓝图定位',['BP_MovementTransition_ToSlide.Evaluate / BP_MovementTransition_FromSlide.Evaluate','阈值来自未连接的常量引脚；连接引脚上的默认值不代表运行时输入。'],'#ffffff')
m.save('slide-transitions.svg',s)
