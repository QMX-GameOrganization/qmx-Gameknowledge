"""第 4 章 4.1~4.8 的配图：具体绘制拆在 s4a_p1 ~ s4a_p5 中，这里汇总。"""
import importlib


def build_all():
    warnings = []
    for name in ("s4a_p1", "s4a_p2", "s4a_p3", "s4a_p4", "s4a_p5"):
        try:
            mod = importlib.import_module(name)
        except ImportError:  # 分批编写期间允许缺失
            continue
        warnings += mod.build_all()
    return warnings
