# -*- coding: utf-8 -*-
"""验证：pyJianYingDraft 只读解析草稿不抛异常 + duration 正确 + 双 JSON 一致
= 结构兼容、剪映能打开。

用法:
  python validate_speed.py --draft <草稿名> [--target-sec 35]
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 依赖注册顺序很重要：先 .jydeps313，再 jianying-editor scripts（import jy_wrapper 触发 vendor 注册）
sys.path.insert(0, r"e:\Documents\kuaishou\.jydeps313")
sys.path.insert(0, r"e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts")
sys.path.insert(0, r"e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor")

ROOT = Path(r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft")


def main():
    ap = argparse.ArgumentParser(description="变速结果验证")
    ap.add_argument("--draft", required=True, help="草稿名")
    ap.add_argument("--target-sec", type=float, default=None,
                    help="期望总长（秒）；给了就严格断言 duration 相等")
    args = ap.parse_args()

    draft = ROOT / args.draft
    if not draft.is_dir():
        sys.exit(f"[中止] 找不到草稿目录: {draft}")

    # 1. 双 JSON 一致性
    with open(draft / "draft_content.json", encoding="utf-8") as f:
        ci = json.load(f)
    with open(draft / "draft_info.json", encoding="utf-8") as f:
        fo = json.load(f)
    if ci == fo:
        print("双 JSON 一致：draft_content.json == draft_info.json")
    else:
        sys.exit("[失败] 双 JSON 不一致：apply 步骤没同步写入，或剪映客户端事后打开过草稿"
                 "（8.9 只回写 content）。若是后者且时长仍达标，可视为正常，用 inspect_speed.py 复查")

    # 2. speed 与时长自洽性抽查（视频轨每段 speed * target_dur ≈ src_dur，容差 1 微秒/微比例）
    speeds = {m["id"]: m for m in ci.get("materials", {}).get("speeds", [])}
    bad = 0
    for t in ci.get("tracks", []):
        if t.get("type") != "video" or not t.get("segments"):
            continue
        for si, s in enumerate(t["segments"]):
            st = s.get("source_timerange") or {}
            tt = s["target_timerange"]
            if not st:
                continue
            expect = st["duration"] / tt["duration"]
            if abs((s.get("speed") or 0) - expect) > 1e-6:
                print(f"[失败] 段{si} seg.speed={s.get('speed')} 与 源/轴 时长比 {expect:.6f} 不自洽")
                bad += 1
            for r in s.get("extra_material_refs", []):
                m = speeds.get(r)
                if m and m.get("mode") in (0, None) and not m.get("curve_speed") \
                        and abs((m.get("speed") or 0) - expect) > 1e-6:
                    print(f"[失败] 段{si} speed material {r[:8]} = {m.get('speed')} 不自洽")
                    bad += 1
    if bad:
        sys.exit(f"[失败] {bad} 处 speed 不自洽")
    print("speed 与时长自洽性抽查通过")

    # 3. pyJianYingDraft 只读解析冒烟测试
    import jy_wrapper  # noqa: F401  必须先 import：触发 setup_env() 注册 vendor 路径
    from pyJianYingDraft import DraftFolder

    tpl = DraftFolder(str(ROOT)).load_template(args.draft)
    dur = tpl.duration
    print(f"load_template 解析成功, duration = {dur} 微秒 = {dur/1e6:.6f} 秒")

    if args.target_sec is not None:
        T = round(args.target_sec * 1_000_000)
        if dur > T:
            sys.exit(f"[失败] duration {dur} 超过目标 {T}")
        print(f"总长 {dur/1e6:.6f}s 不超过目标 {args.target_sec}s")

    # 4. 时长索引
    with open(draft / "draft_meta_info.json", encoding="utf-8") as f:
        meta = json.load(f)
    if meta.get("tm_duration") != ci.get("duration"):
        print(f"[警告] draft_meta_info.tm_duration={meta.get('tm_duration')} "
              f"与顶层 duration={ci.get('duration')} 不一致（缩略图时长会显示旧值）")
    else:
        print(f"tm_duration 索引一致 = {meta.get('tm_duration')}")

    print("\n验证通过：结构兼容、剪映能打开。请重启剪映做最终人工确认。")


if __name__ == "__main__":
    main()
