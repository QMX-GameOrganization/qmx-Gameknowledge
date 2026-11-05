"""生成「C# 速通」专栏的配图到 public/assets/csharp/。用法：python scripts/csharp/generate_figures.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import figures_a
try:
    import figures_b
except ImportError:  # 分批编写期间允许缺失
    figures_b = None


def main():
    warnings = figures_a.build_all()
    if figures_b:
        warnings += figures_b.build_all()
    for w in warnings:
        print("警告:", w)
    print("完成，警告数:", len(warnings))


if __name__ == "__main__":
    main()
