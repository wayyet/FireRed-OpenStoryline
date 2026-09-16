# -*- coding: utf-8 -*-
"""给"已存在"的剪映 5.9 草稿注入逐句字幕——一条字幕对应一个视频分镜，时间严格对齐
draft_content.json（真相）的分镜边界。默认 dry-run 只报告不写入，--apply 才落盘。

流程: 进程守卫 -> 读 content 分镜边界 -> (--replace 时摘除旧字幕轨) -> 临时草稿生成字幕结构
      -> 对齐校验 -> [dry-run 到此为止] -> 整目录备份 -> 注入 content -> content 全量覆盖 info
      -> load_template 冒烟校验 + 双 JSON 一致性校验

用法:
  python inject_subtitles.py --draft <草稿名> --subs-file <subs.txt> [--apply] [--replace]
      [--track-name Subtitles] [--size 5.0] [--transform-y -0.8] [--border-width 40.0]
      [--work-dir <备份与临时草稿目录>] [--draft-root <草稿根目录>]

subs.txt: UTF-8 文本，一行一条字幕，行数必须等于视频分镜数（中文别走命令行参数，防引号/编码坑）。
"""
import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import time

DEFAULT_ROOT = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"
DEPS = [
    r"e:\Documents\kuaishou\.jydeps313",
    r"e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts",
]
RENDER_INDEX_BASE = 14000  # 高于视频层，与历史注入惯例一致


def jianying_running():
    out = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq JianyingPro.exe"],
        capture_output=True, text=True,
    ).stdout
    return "JianyingPro.exe" in out


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True, help="草稿名")
    ap.add_argument("--subs-file", required=True, help="UTF-8 字幕文件，一行一条")
    ap.add_argument("--apply", action="store_true", help="真正写入；缺省为 dry-run")
    ap.add_argument("--replace", action="store_true",
                    help="摘除同名旧字幕轨后再注入（默认草稿已有任何文字素材即中止）")
    ap.add_argument("--track-name", default="Subtitles")
    ap.add_argument("--size", type=float, default=5.0, help="字号（本项目字幕惯例 5.0）")
    ap.add_argument("--transform-y", type=float, default=-0.8, help="纵向位置（-0.8=底部居中）")
    ap.add_argument("--border-width", type=float, default=40.0, help="黑描边宽度")
    ap.add_argument("--work-dir", default=os.path.join(os.environ.get("TEMP", "."), "jy_add_subs"))
    ap.add_argument("--draft-root", default=DEFAULT_ROOT)
    a = ap.parse_args()

    draft_dir = f"{a.draft_root}\\{a.draft}"
    with open(a.subs_file, encoding="utf-8-sig") as f:
        subs = [ln.strip() for ln in f if ln.strip()]
    assert subs, "字幕文件为空"

    # ---------- 1. 读双 JSON，content 为真相 ----------
    content = load_json(f"{draft_dir}\\draft_content.json")
    info = load_json(f"{draft_dir}\\draft_info.json")
    if content != info:
        print("[警告] 双 JSON 已分叉（剪映 8.9 只写 content 的坑），以 content 为真相，写入时覆盖 info")

    video_track = next(t for t in content["tracks"] if t["type"] == "video")
    spans = [(s["target_timerange"]["start"], s["target_timerange"]["duration"])
             for s in video_track["segments"]]
    assert len(spans) == len(subs), f"分镜数 {len(spans)} != 字幕数 {len(subs)}，请先核对文案"

    # ---------- 2. 已有文字的守卫 / --replace 摘除旧字幕轨 ----------
    old_texts = content["materials"].get("texts") or []
    if a.replace:
        victims = [t for t in content["tracks"]
                   if t["type"] == "text" and t.get("name") == a.track_name]
        assert victims, (f"--replace 未找到 name={a.track_name!r} 的文字轨；"
                         f"现有文字轨: {[t.get('name') for t in content['tracks'] if t['type'] == 'text']}")
        dead_mid = {s["material_id"] for t in victims for s in t["segments"]}
        dead_refs = {r for t in victims for s in t["segments"]
                     for r in (s.get("extra_material_refs") or [])}
        content["tracks"] = [t for t in content["tracks"] if t not in victims]
        content["materials"]["texts"] = [t for t in old_texts if t.get("id") not in dead_mid]
        for key in ("material_animations",):  # 顺带清掉旧字幕挂的动画素材，防悬空
            if content["materials"].get(key):
                content["materials"][key] = [m for m in content["materials"][key]
                                             if m.get("id") not in dead_refs]
        print(f"[replace] 已摘除 {len(victims)} 条旧字幕轨、{len(dead_mid)} 条文字素材")
    else:
        assert not old_texts, (f"草稿已有 {len(old_texts)} 条文字素材，中止以免覆盖；"
                               "确认要替换请加 --replace，或先用 jianying-draft-edit 清理")

    for i, (st, du) in enumerate(spans):
        print(f"[对齐] 字幕{i + 1}: {st / 1e6:.3f}s + {du / 1e6:.3f}s  {subs[i]!r}")

    # ---------- 3. 临时草稿生成字幕结构（不碰真实草稿） ----------
    for p in DEPS:
        sys.path.insert(0, p)
    import jy_wrapper  # noqa: F401  先 import 触发 setup_env() 注册 vendor 路径
    from jy_wrapper import JyProject
    from pyJianYingDraft import TextStyle, TextBorder, ClipSettings

    ts = time.strftime("%Y%m%d_%H%M%S")
    os.makedirs(a.work_dir, exist_ok=True)
    tmp_root = f"{a.work_dir}\\tmp_subs_{ts}"
    canvas = content["canvas_config"]
    proj = JyProject("subs_tmp", width=canvas["width"], height=canvas["height"],
                     drafts_root=tmp_root, overwrite=True)
    style = TextStyle(size=a.size, bold=True, color=(1.0, 1.0, 1.0), align=1)
    border = TextBorder(color=(0.0, 0.0, 0.0), alpha=1.0, width=a.border_width)
    for (st, du), text in zip(spans, subs):
        proj.add_text_simple(text, start_time=st, duration=du, track_name=a.track_name,
                             style=style, border=border,
                             clip_settings=ClipSettings(transform_y=a.transform_y))
    proj.save()

    src_json = next(p for p in (f"{tmp_root}\\subs_tmp\\draft_info.json",
                                f"{tmp_root}\\subs_tmp\\draft_content.json")
                    if os.path.exists(p))
    tmp = load_json(src_json)
    texts = tmp["materials"].get("texts") or []
    text_tracks = [t for t in tmp["tracks"] if t["type"] == "text"]
    assert len(texts) == len(subs) and len(text_tracks) == 1, \
        f"临时草稿结构异常: texts={len(texts)} text_tracks={len(text_tracks)}"

    new_track = copy.deepcopy(text_tracks[0])
    for si, seg in enumerate(new_track["segments"]):
        seg["extra_material_refs"] = []              # 纯文字无动画/花字，清悬空引用
        seg["render_index"] = RENDER_INDEX_BASE + si
        tr = seg["target_timerange"]
        assert (tr["start"], tr["duration"]) == spans[si], f"段{si}时间与分镜不一致"

    content["materials"]["texts"] = (content["materials"].get("texts") or []) + copy.deepcopy(texts)
    content["tracks"].append(new_track)
    sub_end = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"]
                  for s in new_track["segments"])
    assert sub_end <= content["duration"], f"字幕末端 {sub_end} 超过总时长 {content['duration']}"

    if not a.apply:
        print(f"[dry-run] 校验通过：{len(subs)} 条字幕可注入，顶层时长 "
              f"{content['duration'] / 1e6:.3f}s 不变。未写入任何文件；加 --apply 落盘")
        return

    # ---------- 4. --apply: 进程守卫 + 整目录备份 + 写入 ----------
    assert not jianying_running(), "剪映正在运行，中止写入（关闭 JianyingPro 后重试）"
    backup = f"{a.work_dir}\\backup_{a.draft}_{ts}"
    shutil.copytree(draft_dir, backup)
    print(f"[备份] {backup}")

    with open(f"{draft_dir}\\draft_content.json", "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, separators=(",", ":"))
    # content 全量覆盖 info，顺带修复分叉
    shutil.copyfile(f"{draft_dir}\\draft_content.json", f"{draft_dir}\\draft_info.json")
    print(f"[写入] 双 JSON 完成，texts={len(subs)} 顶层时长 {content['duration'] / 1e6:.3f}s（未变）")

    # ---------- 5. 校验 ----------
    from pyJianYingDraft import DraftFolder
    tpl = DraftFolder(a.draft_root).load_template(a.draft)
    print(f"[校验] load_template 通过, duration={tpl.duration / 1e6:.3f}s")
    assert load_json(f"{draft_dir}\\draft_info.json") == content, "双 JSON 不一致"
    print("[校验] 双 JSON 完全一致；字幕注入成功")


if __name__ == "__main__":
    main()
