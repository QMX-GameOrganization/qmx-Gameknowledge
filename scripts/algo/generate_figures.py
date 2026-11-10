"""生成「算法学习专栏」的配图到 public/assets/algo/。用法：python3 scripts/algo/generate_figures.py
自动加载同目录下所有 figures_*.py，各模块提供 build_all() 返回警告列表。"""
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def main():
    warnings = []
    for p in sorted(HERE.glob("figures_*.py")):
        warnings += importlib.import_module(p.stem).build_all()
    for w in warnings:
        print("警告:", w)
    print("完成，警告数:", len(warnings))


if __name__ == "__main__":
    main()
