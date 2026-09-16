# -*- coding: utf-8 -*-
"""常规变速写入：把视频轨全部分镜按比例变速，总长精确压到 T。
步骤：整目录快照备份 -> 改 draft_content.json -> 双 JSON 全量覆盖同步（修复 8.9 分叉）
     -> 更新 draft_meta_info.json / root_meta_info.json 的 tm_duration。

用法（外层 PowerShell 必须先确认 JianyingPro 进程不在运行）:
  python apply_speed.py --draft <草稿名> --backup-dir <scratchpad目录>
                        [--target-sec 35] [--expect-src-total <微秒>]
                        [--track-index N] [--allow-overhang]

所有时间单位：微秒。speed_i = src_dur_i / target_dur_i 严格自洽。
"""
import argparse
import copy
import json
import shutil
import sys
import time
import uuid
from pathlib import Path

from speed_common import compute_plan

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft")


def dump(obj, path):
    # 剪映双 JSON 均为紧凑单行格式，保持一致；UTF-8 无 BOM
    with open(path, "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def pick_video_track(d: dict, track_index):
    tracks = [(i, t) for i, t in enumerate(d.get("tracks", []))
              if t.get("type") == "video" and t.get("segments")]
    if not tracks:
        sys.exit("[中止] 草稿里没有非空视频轨")
    if track_index is not None:
        hit = [(i, t) for i, t in tracks if i == track_index]
        if not hit:
            sys.exit(f"[中止] 轨{track_index} 不是非空视频轨，可选: {[i for i, _ in tracks]}")
        return hit[0]
    if len(tracks) > 1:
        sys.exit(f"[中止] 有多条非空视频轨 {[i for i, _ in tracks]}，请用 --track-index 指定要变速的一条")
    return tracks[0]


def main():
    ap = argparse.ArgumentParser(description="常规变速写入（带整目录备份）")
    ap.add_argument("--draft", required=True, help="草稿名")
    ap.add_argument("--target-sec", type=float, default=35.0, help="目标总长（秒），默认 35")
    ap.add_argument("--backup-dir", required=True, help="备份目录（用当前会话 scratchpad）")
    ap.add_argument("--expect-src-total", type=int, default=None,
                    help="试算时记下的源总长（微秒），不一致说明草稿被中途改动，中止")
    ap.add_argument("--track-index", type=int, default=None, help="多视频轨时指定轨序号")
    ap.add_argument("--allow-overhang", action="store_true",
                    help="允许非视频轨末端超过目标时长（顶层 duration 取真实最大末端）")
    ap.add_argument("--no-frame-align", action="store_true",
                    help="关闭帧对齐（默认开启；关闭后总长精确等于目标，但客户端打开可能按帧回弹超标）")
    args = ap.parse_args()

    T = round(args.target_sec * 1_000_000)
    draft = ROOT / args.draft
    if not draft.is_dir():
        sys.exit(f"[中止] 找不到草稿目录: {draft}")
    backup_root = Path(args.backup_dir)
    if not backup_root.is_dir():
        sys.exit(f"[中止] 备份目录不存在: {backup_root}")

    # ---------- 1. 读取 + 全部前置校验（任何文件写入之前） ----------
    with open(draft / "draft_content.json", encoding="utf-8") as f:
        d = json.load(f)

    ti, track = pick_video_track(d, args.track_index)
    segs = sorted(track["segments"], key=lambda s: s["target_timerange"]["start"])
    track["segments"] = segs  # 落盘顺序与时间轴顺序一致
    speeds = d["materials"].setdefault("speeds", [])
    speeds_by_id = {m["id"]: m for m in speeds}

    src = [s["source_timerange"]["duration"] for s in segs]
    total_src = sum(src)
    if args.expect_src_total is not None and total_src != args.expect_src_total:
        sys.exit(f"[中止] 源总长 {total_src} 与守卫值 {args.expect_src_total} 不一致，"
                 f"草稿状态与试算时不同，请重新试算")

    cur_end = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"] for s in segs)
    if cur_end <= T:
        print(f"[跳过] 视频轨当前末端 {cur_end/1e6:.3f}s 已不超过目标 {T/1e6:.3f}s，未做任何写入。")
        return

    # 曲线变速守卫
    for si, s in enumerate(segs):
        for r in s.get("extra_material_refs", []):
            m = speeds_by_id.get(r)
            if m and (m.get("mode") not in (0, None) or m.get("curve_speed")):
                sys.exit(f"[中止] 段{si} 已带曲线变速（mode={m.get('mode')}），本脚本只处理常规变速")

    # 方案计算：按比例分配（默认帧对齐，防客户端按帧上取整回弹超标）
    fps = d.get("fps") or 30.0
    tgt, note = compute_plan(src, T, fps=fps, frame_align=not args.no_frame_align)
    if tgt is None:
        sys.exit(f"[中止] {note}")
    assert sum(tgt) <= T
    print(f"[分配] {note}")
    for i in range(len(segs)):
        spd = src[i] / tgt[i]
        if spd > 100 or spd < 0.1:
            sys.exit(f"[中止] 段{i} 速度 {spd:.2f}x 超出剪映 0.1~100x 硬上限")

    # 非视频轨悬出检查
    overhang = []
    for oi, t in enumerate(d.get("tracks", [])):
        if oi == ti or not t.get("segments"):
            continue
        end = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"]
                  for s in t["segments"])
        if end > T:
            overhang.append((oi, t.get("type"), end))
    if overhang and not args.allow_overhang:
        for oi, typ, end in overhang:
            print(f"[悬出] 轨{oi} type={typ} 末端 {end/1e6:.3f}s > 目标 {T/1e6:.3f}s")
        sys.exit("[中止] 非视频轨末端超过目标时长，视频压短后总长仍超标。"
                 "先裁剪这些轨道，或确认保留后加 --allow-overhang 重跑")

    # speed material 共用检测：统计全草稿引用次数
    ref_count = {}
    for t in d.get("tracks", []):
        for s in t.get("segments", []):
            for r in s.get("extra_material_refs", []):
                if r in speeds_by_id:
                    ref_count[r] = ref_count.get(r, 0) + 1

    # ---------- 2. 整目录快照备份（黄金法则 1） ----------
    stamp = time.strftime("%H%M%S")
    backup = backup_root / f"backup_{args.draft}_{stamp}"
    shutil.copytree(draft, backup)
    shutil.copy2(ROOT / "root_meta_info.json", backup_root / f"backup_root_meta_info_{stamp}.json")
    print(f"[备份] 草稿整目录 -> {backup}")
    print(f"[备份] root_meta_info.json -> backup_root_meta_info_{stamp}.json")

    # ---------- 3. 应用变速 ----------
    start = 0
    for i, s in enumerate(segs):
        speed = src[i] / tgt[i]  # 与时长严格自洽
        s["speed"] = speed
        s["target_timerange"]["start"] = start
        s["target_timerange"]["duration"] = tgt[i]

        refs = s.setdefault("extra_material_refs", [])
        spd_refs = [r for r in refs if r in speeds_by_id]
        if len(spd_refs) > 1:
            sys.exit(f"[中止] 段{i} 关联了 {len(spd_refs)} 个 speed material，结构异常")
        if not spd_refs:
            # 无 speed material 的段：按 pyJianYingDraft 的固定速度结构补一个
            m = {"curve_speed": None, "id": uuid.uuid4().hex, "mode": 0,
                 "speed": speed, "type": "speed"}
            speeds.append(m)
            speeds_by_id[m["id"]] = m
            refs.append(m["id"])
            print(f"[补建] 段{i} 无 speed material，已新建 {m['id'][:8]}")
        else:
            rid = spd_refs[0]
            if ref_count.get(rid, 0) > 1:
                # 共用的 speed material：克隆独立副本再改，避免互相污染
                clone = copy.deepcopy(speeds_by_id[rid])
                clone["id"] = uuid.uuid4().hex
                speeds.append(clone)
                speeds_by_id[clone["id"]] = clone
                refs[refs.index(rid)] = clone["id"]
                ref_count[rid] -= 1
                rid = clone["id"]
                print(f"[克隆] 段{i} 的 speed material 被共用，已克隆独立副本 {rid[:8]}")
            speeds_by_id[rid]["speed"] = speed
        print(f"[变速] 段{i}: {src[i]/1e6:.3f}s -> {tgt[i]/1e6:.3f}s @ {speed:.6f}x, "
              f"新起点 {start/1e6:.3f}s")
        start += tgt[i]

    # 顶层 duration = 实际时间轴末端（帧对齐后视频末端可能略小于 T）
    video_end = sum(tgt)
    new_total = video_end if not overhang else max([video_end] + [end for _, _, end in overhang])
    d["duration"] = new_total
    print(f"[顶层] duration = {new_total} ({new_total/1e6:.3f}s)"
          + ("（含悬出轨道）" if overhang else ""))

    # ---------- 4. 双 JSON 同步写入 + 更新时长索引 ----------
    dump(d, draft / "draft_content.json")
    dump(d, draft / "draft_info.json")  # 全量覆盖，顺手修复 8.9 客户端只写 content 造成的分叉
    print("[写入] draft_content.json + draft_info.json 已同步")

    with open(draft / "draft_meta_info.json", encoding="utf-8") as f:
        meta = json.load(f)
    meta["tm_duration"] = new_total
    dump(meta, draft / "draft_meta_info.json")
    print(f"[索引] draft_meta_info.tm_duration = {new_total}")

    with open(ROOT / "root_meta_info.json", encoding="utf-8") as f:
        root = json.load(f)
    hit = 0
    for item in root.get("all_draft_store", []):
        if item.get("draft_name") == args.draft or \
                item.get("draft_fold_path", "").rstrip("/\\").endswith(args.draft):
            item["tm_duration"] = new_total
            hit += 1
    if hit < 1:
        print("[警告] root_meta_info.json 里没找到该草稿条目，草稿箱缩略图时长可能显示旧值")
    else:
        dump(root, ROOT / "root_meta_info.json")
        print(f"[索引] root_meta_info.all_draft_store 命中 {hit} 条, tm_duration = {new_total}")

    print("\n[完成] 全部写入成功，请运行 validate_speed.py 验证")


if __name__ == "__main__":
    main()
