# -*- coding: utf-8 -*-
"""只读试算：把视频轨全部分镜按比例常规变速到总长恰好 T 的方案表。不写任何文件。

用法:
  python plan_speed.py --draft <草稿名> [--target-sec 35] [--track-index N]

输出末尾会给出 --expect-src-total 守卫值，写入时传给 apply_speed.py 防草稿被中途改动。
"""
import argparse
import json
import sys
from pathlib import Path

from speed_common import compute_plan

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft")


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
    ap = argparse.ArgumentParser(description="只读试算常规变速方案")
    ap.add_argument("--draft", required=True, help="草稿名")
    ap.add_argument("--target-sec", type=float, default=35.0, help="目标总长（秒），默认 35")
    ap.add_argument("--track-index", type=int, default=None, help="多视频轨时指定轨序号")
    ap.add_argument("--no-frame-align", action="store_true",
                    help="关闭帧对齐（默认开启；关闭后总长精确等于目标，但客户端打开可能按帧回弹超标）")
    args = ap.parse_args()

    T = round(args.target_sec * 1_000_000)
    draft = ROOT / args.draft
    if not draft.is_dir():
        sys.exit(f"[中止] 找不到草稿目录: {draft}")

    with open(draft / "draft_content.json", encoding="utf-8") as f:
        d = json.load(f)

    ti, track = pick_video_track(d, args.track_index)
    segs = sorted(track["segments"], key=lambda s: s["target_timerange"]["start"])
    vids = {m["id"]: m for m in d["materials"].get("videos", [])}
    speeds = {m["id"]: m for m in d["materials"].get("speeds", [])}

    # 曲线变速检测：已有曲线的段不能按常规公式改
    for si, s in enumerate(segs):
        for r in s.get("extra_material_refs", []):
            m = speeds.get(r)
            if m and (m.get("mode") not in (0, None) or m.get("curve_speed")):
                sys.exit(f"[中止] 段{si} 已带曲线变速（mode={m.get('mode')}），"
                         f"请先在客户端还原常规变速，或整体走曲线变速人机协作路线")

    src = [s["source_timerange"]["duration"] for s in segs]
    total_src = sum(src)

    cur_end = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"] for s in segs)
    if cur_end <= T:
        print(f"视频轨当前末端 {cur_end/1e6:.3f}s 已不超过目标 {T/1e6:.3f}s，无需变速。")
        return

    fps = d.get("fps") or 30.0
    tgt, note = compute_plan(src, T, fps=fps, frame_align=not args.no_frame_align)
    if tgt is None:
        sys.exit(f"[中止] {note}")

    print(f"[视频轨 轨{ti}] 源总长 {total_src} 微秒 = {total_src/1e6:.3f}s "
          f"-> 目标 {T} 微秒 = {T/1e6:.3f}s（整体约 {total_src/T:.4f}x）")
    print(f"[分配] {note}\n")
    print(f"{'分镜':<4} {'素材':<20} {'源时长s':>9} {'新时长s':>9} {'速度x':>9} {'新起点s':>9}")
    start = 0
    spd_list = []
    for i, s in enumerate(segs):
        speed = src[i] / tgt[i]
        spd_list.append(speed)
        name = (vids.get(s["material_id"], {}).get("material_name") or "?")[:20]
        print(f"段{i:<3} {name:<20} {src[i]/1e6:>9.3f} {tgt[i]/1e6:>9.3f} {speed:>9.4f} {start/1e6:>9.3f}")
        start += tgt[i]
    print(f"\n校验: 新时长合计 = {sum(tgt)} 微秒 = {sum(tgt)/1e6:.6f}s（不超过目标: {sum(tgt) <= T}）")
    print(f"速度区间: {min(spd_list):.4f}x ~ {max(spd_list):.4f}x（剪映常规变速允许 0.1~100x）")
    if max(spd_list) > 100 or min(spd_list) < 0.1:
        print("[警告] 超出剪映 0.1~100x 硬上限，方案不可行，需先删减镜头")
    elif max(spd_list) > 3:
        print("[警告] 速度超过 3x，快进感明显，建议和用户确认是否改走「删减+温和变速」组合")

    # 非视频轨悬出预警
    overhang = []
    for oi, t in enumerate(d.get("tracks", [])):
        if oi == ti or not t.get("segments"):
            continue
        end = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"]
                  for s in t["segments"])
        if end > T:
            overhang.append(f"  轨{oi} type={t.get('type')} 末端 {end/1e6:.3f}s")
    if overhang:
        print(f"\n[警告] 以下非视频轨末端超过目标 {T/1e6:.3f}s，视频压短后总时长仍会超标：")
        print("\n".join(overhang))
        print("  处理方式需用户确认（裁剪这些轨 / apply 时加 --allow-overhang 保留）")

    print(f"\n写入守卫值: --expect-src-total {total_src}")


if __name__ == "__main__":
    main()
