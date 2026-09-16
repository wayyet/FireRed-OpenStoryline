# -*- coding: utf-8 -*-
"""plan_speed.py / apply_speed.py 共用的时长分配算法。"""
import math


def compute_plan(src, T, fps=30.0, frame_align=True):
    """按源时长比例给各段分配轴上新时长，保证总和不超过 T（微秒）。

    frame_align=True（默认）：各段时长对齐到整帧。实测坑：写入非整帧时长后，
    剪映客户端打开草稿会把每段按帧"上取整"回写，总长回弹超标
    （例：7 段精确 35.000000s 被客户端弹成 35.167s）。整帧分配可避免回弹。

    返回 (tgt 列表, 说明字符串)；不可行时返回 (None, 原因)。
    """
    total_src = sum(src)
    if frame_align and fps and fps > 0:
        frame_us = 1_000_000 / fps
        n = math.floor(T * fps / 1_000_000)          # 总帧数预算
        f = [round(n * x / total_src) for x in src]
        f[-1] = n - sum(f[:-1])                      # 末段吸收帧数余数
        if min(f) < 1:
            return None, "有分镜被压到不足 1 帧，段数太多或目标太短，请改走删减路线"
        tgt = [round(k * frame_us) for k in f]
        over = sum(tgt) - T
        if over > 0:
            tgt[-1] -= over                          # 微秒级修正，严格保证总和 <= T
        note = (f"帧对齐 @ {fps:g}fps，总帧数 {n}，"
                f"总长 {sum(tgt)} 微秒 = {sum(tgt)/1e6:.6f}s（<= 目标 {T/1e6:.6f}s）")
    else:
        tgt = [round(T * x / total_src) for x in src]
        tgt[-1] = T - sum(tgt[:-1])                  # 末段吸收舍入余数，总和精确等于 T
        if min(tgt) <= 0:
            return None, "有分镜目标时长被压到 0，段数太多或目标太短，请改走删减路线"
        note = (f"精确模式，总长 {sum(tgt)} 微秒 = {sum(tgt)/1e6:.6f}s"
                f"（警告：剪映客户端打开后可能按帧上取整回弹超标）")
    return tgt, note
