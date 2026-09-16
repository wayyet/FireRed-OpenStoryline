# -*- coding: utf-8 -*-
"""只读侦查：分析目标草稿的双 JSON 分叉、视频轨分镜时长/速度现状、speed material 共用与曲线情况、
非视频轨末端位置。不写任何文件。

用法:
  python inspect_speed.py --draft <草稿名>
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft")


def load(draft: Path, name: str):
    with open(draft / name, encoding="utf-8") as f:
        return json.load(f)


def summarize(tag: str, d: dict):
    print(f"===== {tag} =====")
    print(f"顶层 duration = {d.get('duration')} 微秒 = {(d.get('duration') or 0)/1e6:.3f} 秒, "
          f"fps={d.get('fps')}, 画布={d.get('canvas_config')}")
    mats = d.get("materials", {})
    non_empty = {k: len(v) for k, v in mats.items() if isinstance(v, list) and v}
    print(f"materials 非空项: {non_empty}")
    for ti, t in enumerate(d.get("tracks", [])):
        segs = t.get("segments", [])
        if not segs:
            print(f"  轨{ti} type={t.get('type')} 空轨")
            continue
        end = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"] for s in segs)
        print(f"  轨{ti} type={t.get('type'):8s} 段数={len(segs):2d} 轨道末端={end/1e6:8.3f}s "
              f"flag={t.get('flag')} name={t.get('name', '')!r}")
    print()


def video_detail(tag: str, d: dict):
    mats = d.get("materials", {})
    vids = {m["id"]: m for m in mats.get("videos", [])}
    speeds = {m["id"]: m for m in mats.get("speeds", [])}
    # 统计 speed material 被全部轨道（含音频）引用的次数，检测共用
    ref_count = {}
    for t in d.get("tracks", []):
        for s in t.get("segments", []):
            for r in s.get("extra_material_refs", []):
                if r in speeds:
                    ref_count[r] = ref_count.get(r, 0) + 1
    print(f"----- {tag} 视频轨分镜明细 -----")
    for ti, t in enumerate(d.get("tracks", [])):
        if t.get("type") != "video" or not t.get("segments"):
            continue
        print(f"[视频轨 轨{ti}] 段数={len(t['segments'])}")
        for si, s in enumerate(t["segments"]):
            tt = s["target_timerange"]
            st = s.get("source_timerange") or {}
            v = vids.get(s.get("material_id"), {})
            spd_ids = [r for r in s.get("extra_material_refs", []) if r in speeds]
            spd_vals = [speeds[r].get("speed") for r in spd_ids]
            modes = [speeds[r].get("mode") for r in spd_ids]
            curves = [bool(speeds[r].get("curve_speed")) for r in spd_ids]
            name = (v.get("material_name") or v.get("path", ""))[-40:]
            print(f"  段{si}: 时间轴[{tt['start']/1e6:8.3f}s +{tt['duration']/1e6:7.3f}s] "
                  f"源[{st.get('start', 0)/1e6:8.3f}s +{st.get('duration', 0)/1e6:7.3f}s] "
                  f"seg.speed={s.get('speed')} speedMat={spd_vals} mode={modes} 曲线={curves} 素材={name!r}")
    shared = {k: c for k, c in ref_count.items() if c > 1}
    print(f"共用的 speed material: {shared if shared else '无'}")
    print()


def main():
    ap = argparse.ArgumentParser(description="只读侦查剪映草稿的变速现状")
    ap.add_argument("--draft", required=True, help="草稿名（草稿目录下的文件夹名）")
    args = ap.parse_args()

    draft = ROOT / args.draft
    if not draft.is_dir():
        sys.exit(f"[中止] 找不到草稿目录: {draft}")

    ci = load(draft, "draft_content.json")
    fo = load(draft, "draft_info.json")
    summarize("draft_content.json", ci)
    summarize("draft_info.json", fo)
    video_detail("draft_content.json", ci)

    # 双 JSON 分叉检测（剪映 8.9 只写 content 的坑）
    if ci == fo:
        print("双 JSON 一致：draft_content.json == draft_info.json")
    else:
        print("[警告] 双 JSON 分叉：draft_content.json 与 draft_info.json 不一致（以 content 为基准处理）")
        for key in sorted(set(ci.get("materials", {})) | set(fo.get("materials", {}))):
            a = ci.get("materials", {}).get(key) or []
            b = fo.get("materials", {}).get(key) or []
            if isinstance(a, list) and isinstance(b, list) and len(a) != len(b):
                print(f"  materials.{key}: content={len(a)} vs info={len(b)}")
        if ci.get("duration") != fo.get("duration"):
            print(f"  duration: content={ci.get('duration')} vs info={fo.get('duration')}")

    meta = load(draft, "draft_meta_info.json")
    print(f"\ndraft_meta_info.tm_duration = {meta.get('tm_duration')} "
          f"({(meta.get('tm_duration') or 0)/1e6:.3f}s)")


if __name__ == "__main__":
    main()
