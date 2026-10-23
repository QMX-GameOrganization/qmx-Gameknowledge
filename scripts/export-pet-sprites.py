#!/usr/bin/env python3
"""把 dsh-pet 的透明 webm 动画导出成精灵图序列，供 AI 助手的鲸鱼形象使用。

用法：
    python3 scripts/export-pet-sprites.py                 # 默认：原始 24 帧、单格 200px
    python3 scripts/export-pet-sprites.py --fps 12        # 想让总体积减半：降低帧率
    python3 scripts/export-pet-sprites.py --cell 160      # 或者缩小单格

依赖：Python 3、Pillow、带 libvpx-vp9 解码器的 ffmpeg（解出 webm 的透明通道要用它，
ffmpeg 自带的 vp9 解码器会丢掉 alpha）。

输出到 public/ai-pet/：
    clips/<id>.webp   每个动作一张精灵图（行优先排列的网格）
    still.webp        待机第一帧，加载前和「减少动态效果」时显示
    pack.json         清单：每个动作的网格、帧数、帧率、是否循环，以及状态到动作的对应

素材来源：https://github.com/PC2005-cloud/dsh-pet （代码 MIT；动画素材允许开源使用、禁止商用，
二创须附上原仓库地址，见 public/ai-pet/NOTICE.txt）。
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

SOURCE = "https://raw.githubusercontent.com/PC2005-cloud/dsh-pet/HEAD/dsh-pet/assets/webm/"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "ai-pet"

# id → (源文件名, 是否循环)。循环的是「一直在做」的动作；其余播一遍就回到待机。
CLIPS: dict[str, tuple[str, bool]] = {
    "idle": ("待机呼吸休闲", True),
    "look": ("东张西望", False),
    "yawn": ("哈欠连天", False),
    "stretch": ("超大伸懒腰", False),
    "hum": ("悠闲哼歌", False),
    "pace": ("工作状态-原地踱步张望", True),
    "thinking": ("工作状态-思考冒泡", True),
    "working": ("工作状态-忙碌点按", True),
    "coding": ("写代码", True),
    "filing": ("工作状态-清点归档", True),
    "cheer": ("工作状态-雀跃庆祝", False),
    "sigh": ("工作状态-垂头叹气冒汗", False),
    "poke_happy": ("点击回应-开心跃动", False),
    "poke_shy": ("点击回应-害羞惊讶", False),
    "poke_angry": ("点击回应-傲娇生气", False),
    "poke_tickle": ("点击回应-挠痒咯咯笑", False),
    "poke_wave": ("点击回应-元气挥手", False),
    "curtsy": ("女仆屈膝礼仪", False),
    "nap": ("原地小憩沉眠", True),
    "wake": ("打瞌睡被惊醒", False),
    "drag": ("被鼠标拖拽悬空反馈", True),
    "scare": ("被吓一跳", False),
}

# 状态 → 候选动作。播放器从候选里挑一个，尽量不连续重复。
MOODS: dict[str, list[str]] = {
    "idle": ["idle"],
    "thinking": ["thinking"],
    "talking": ["working", "coding", "filing"],
    "happy": ["cheer"],
    "sad": ["sigh"],
    "wave": ["curtsy"],
    "sleep": ["nap"],
    "wake": ["wake"],
    "drag": ["drag"],
    "scare": ["scare"],
    "poke": ["poke_happy", "poke_shy", "poke_angry", "poke_tickle", "poke_wave"],
    "waiting": ["pace"],
}
# 待机时偶尔做的小动作
EXTRAS = ["look", "yawn", "stretch", "hum", "pace", "wake"]

ALPHA_THRESHOLD = 8  # 透明度高于它才算角色的一部分，用来求裁剪范围
MARGIN = 6


def download(name: str, cache: Path) -> Path:
    dst = cache / f"{name}.webm"
    if not dst.exists():
        url = SOURCE + urllib.parse.quote(name) + ".webm"
        print(f"  下载 {name}")
        urllib.request.urlretrieve(url, dst)
    return dst


def decode(webm: Path, frames_dir: Path) -> list[Path]:
    """用 libvpx-vp9 解码并保留透明通道，逐帧存成 png。"""
    frames_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-c:v", "libvpx-vp9", "-i", str(webm), "-pix_fmt", "rgba", str(frames_dir / "%04d.png")]
    subprocess.run(cmd, check=True)
    return sorted(frames_dir.glob("*.png"))


def union_bbox(all_frames: list[list[Path]]) -> tuple[int, int, int, int]:
    box = None
    for frames in all_frames:
        for f in frames:
            with Image.open(f) as im:
                bb = im.getchannel("A").point(lambda v: 255 if v > ALPHA_THRESHOLD else 0).getbbox()
                size = im.size
            if bb:
                box = bb if box is None else (min(box[0], bb[0]), min(box[1], bb[1]), max(box[2], bb[2]), max(box[3], bb[3]))
    if box is None:
        sys.exit("没有找到任何不透明像素，解码可能丢了透明通道")
    return (max(0, box[0] - MARGIN), max(0, box[1] - MARGIN), min(size[0], box[2] + MARGIN), min(size[1], box[3] + MARGIN))


def build_sheet(frames: list[Path], crop, cell_w: int, cell_h: int) -> tuple[Image.Image, int, int]:
    n = len(frames)
    cols = max(1, round(math.sqrt(n * cell_h / cell_w)))  # 接近正方形的网格，避免过宽或过高
    rows = math.ceil(n / cols)
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        with Image.open(f) as im:
            cell = im.convert("RGBA").crop(crop).resize((cell_w, cell_h), Image.LANCZOS)
        sheet.paste(cell, ((i % cols) * cell_w, (i // cols) * cell_h))
    return sheet, cols, rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fps", type=int, default=24, help="输出帧率，源是 24；12 表示隔帧取一（默认 24）")
    ap.add_argument("--cell", type=int, default=200, help="单格宽度（像素，默认 200）")
    ap.add_argument("--quality", type=int, default=70, help="WebP 质量（默认 70）")
    ap.add_argument("--alpha-quality", type=int, default=75, help="透明通道质量（默认 75）")
    ap.add_argument("--cache", default=str(Path(tempfile.gettempdir()) / "qmx-pet-cache"), help="下载和解码的缓存目录")
    args = ap.parse_args()

    if 24 % args.fps:
        sys.exit("--fps 需要能整除 24（24、12、8、6……）")
    step = 24 // args.fps
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)

    print("1/3 下载并解码")
    decoded: dict[str, list[Path]] = {}
    for cid, (name, _) in CLIPS.items():
        decoded[cid] = decode(download(name, cache), cache / "frames" / cid)

    print("2/3 计算统一的裁剪范围（所有动作共用一个，脚底和位置才对得齐）")
    crop = union_bbox(list(decoded.values()))
    cw, ch = crop[2] - crop[0], crop[3] - crop[1]
    cell_w = args.cell
    cell_h = round(cell_w * ch / cw)
    print(f"   裁剪 {crop}，原尺寸 {cw}×{ch} → 单格 {cell_w}×{cell_h}")

    print("3/3 生成精灵图")
    (OUT / "clips").mkdir(parents=True, exist_ok=True)
    clips: dict[str, dict] = {}
    total = 0
    for cid, (_, loop) in CLIPS.items():
        frames = decoded[cid][::step]
        sheet, cols, rows = build_sheet(frames, crop, cell_w, cell_h)
        dst = OUT / "clips" / f"{cid}.webp"
        sheet.save(dst, "WEBP", quality=args.quality, alpha_quality=args.alpha_quality, method=4)
        size = dst.stat().st_size
        total += size
        clips[cid] = {"src": f"clips/{cid}.webp", "cols": cols, "rows": rows, "frames": len(frames), "fps": args.fps, "loop": loop}
        print(f"   {cid:12s} {len(frames):3d} 帧  {sheet.size[0]}×{sheet.size[1]}  {size // 1024:5d} KB")

    with Image.open(decoded["idle"][0]) as im:
        still = im.convert("RGBA").crop(crop).resize((cell_w, cell_h), Image.LANCZOS)
    still.save(OUT / "still.webp", "WEBP", quality=80, alpha_quality=90, method=4)

    pack = {
        "version": 1,
        "name": "DeepSeek 大肥鱼",
        "cell": [cell_w, cell_h],
        "still": "still.webp",
        "clips": clips,
        "moods": MOODS,
        "extras": EXTRAS,
        "credit": "https://github.com/PC2005-cloud/dsh-pet",
    }
    (OUT / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"完成：{len(clips)} 个动作，精灵图合计 {total / 1024 / 1024:.1f} MB（用户只会按需下载其中用到的几个）")


if __name__ == "__main__":
    main()
