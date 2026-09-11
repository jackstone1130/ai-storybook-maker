#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插画批量后处理：备份原图 → 去平台水印 → 压缩成网页尺寸。

用法：
    python3 prep_images.py <图片目录> [更多目录...]

    # 常见结构：每个故事一个子目录
    python3 prep_images.py 插画样片/s1_xx 插画样片/s2_yy ...

参数在下方「可调常量」区。
"""
import sys, pathlib
from PIL import Image

# ---------- 可调常量 ----------
WATERMARK_X = 1385      # 水印区左上角 X（1536×1024 图适用；其它尺寸需自行校准）
WATERMARK_Y = 940       # 水印区左上角 Y
TARGET_W, TARGET_H = 900, 600    # 网页显示尺寸（容器约 520px 宽，900 兼顾 2x 屏）
JPEG_QUALITY = 86
BACKUP_DIRNAME = 'raw'
# -----------------------------


def log(*a): print(*a, flush=True)


def strip_watermark(im, x0, y0):
    """去水印：取水印区左侧等宽区域横向镜像后原样粘贴。
    镜像保证接缝处天然连续；不要做整块模糊（会留明显色块）。
    """
    W, H = im.size
    w = W - x0
    if w <= 0 or y0 >= H:
        return im
    patch = im.crop((x0 - w, y0, x0, H)).transpose(Image.FLIP_LEFT_RIGHT)
    im.paste(patch, (x0, y0))
    return im


def main():
    if len(sys.argv) < 2:
        log(__doc__); return 1
    total = 0
    for arg in sys.argv[1:]:
        dr = pathlib.Path(arg).resolve()
        if not dr.is_dir():
            log('跳过（不是目录）：', dr); continue

        files = sorted([p for p in dr.iterdir()
                        if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')])
        if not files:
            log('跳过（没有图片）：', dr); continue

        backup = dr.parent / BACKUP_DIRNAME / dr.name
        try:
            backup.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        for i, f in enumerate(files, 1):
            im = Image.open(f).convert('RGB')

            # ① 先备份原图（带水印版）—— 务必在修改前
            if backup.is_dir():
                bk = backup / f.name
                if not bk.exists():
                    im.save(bk)

            # ② 去水印
            im = strip_watermark(im, WATERMARK_X, WATERMARK_Y)

            # ③ 压缩成网页尺寸
            out = dr.parent / f'web_{dr.name}_{i:02d}.jpg'
            im.resize((TARGET_W, TARGET_H), Image.LANCZOS).save(
                out, 'JPEG', quality=JPEG_QUALITY, optimize=True)
            total += out.stat().st_size
            log(f'  {dr.name} #{i}  {out.stat().st_size/1024:5.1f} KB  → {out.name}')

    log(f'\n合计 {total/1024/1024:.2f} MB（base64 内嵌后约 {total*1.34/1024/1024:.2f} MB）')
    log('提示：若水印位置不同，先裁出右下角放大看一眼，再调 WATERMARK_X/Y。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
