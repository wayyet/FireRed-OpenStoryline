# -*- coding: utf-8 -*-
"""删除剪映草稿里的中文 TTS 配音轨（text_to_audio），保留 BGM。
约定与 inject_subtitles.py 一致：content 为真相，dry-run 默认，--apply 才写入，
写入前进程守卫 + 整目录备份，写入后 content 全量覆盖 info + load_template 校验。
"""
import argparse
import json
import shutil
import subprocess
import sys
import time

DEFAULT_ROOT = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"
DEPS = [
    r"e:\Documents\kuaishou\.jydeps313",
    r"e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts",
]


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
    ap.add_argument("--draft", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--draft-root", default=DEFAULT_ROOT)
    a = ap.parse_args()

    draft_dir = f"{a.draft_root}\\{a.draft}"
    content = load_json(f"{draft_dir}\\draft_content.json")
    info = load_json(f"{draft_dir}\\draft_info.json")
    if content != info:
        print("[警告] 双 JSON 已分叉，以 content 为真相，写入时覆盖 info")

    audios = {m["id"]: m for m in (content["materials"].get("audios") or [])}

    # 只删“全部分段素材都落在 textReading 目录”的音频轨（本草稿 TTS 手写为
    # extract_music 类型，不能按 type 识别），BGM(音乐)轨不动
    def is_tts(m):
        return m is not None and "textReading" in (m.get("path") or "")

    victims = []
    for t in content["tracks"]:
        if t["type"] != "audio":
            continue
        mats = [audios.get(s["material_id"]) for s in t["segments"]]
        flags = {is_tts(m) for m in mats}
        print(f"[侦查] 音频轨 segs={len(t['segments'])} 全部为textReading素材={flags == {True}}")
        if flags == {True}:
            victims.append(t)

    assert victims, "未找到 textReading 配音轨，中止（请人工核对）"
    assert len(victims) == 1, f"找到 {len(victims)} 条配音轨，预期 1 条，中止（请人工核对）"

    dead_mid = {s["material_id"] for t in victims for s in t["segments"]}
    dead_refs = {r for t in victims for s in t["segments"]
                 for r in (s.get("extra_material_refs") or [])}
    n_seg = sum(len(t["segments"]) for t in victims)
    print(f"[计划] 删除 1 条配音轨（{n_seg} 段旁白）、{len(dead_mid)} 条 TTS 音频素材、"
          f"{len(dead_refs)} 条附属素材引用；BGM 与其他轨不动")
    for mid in sorted(dead_mid):
        m = audios[mid]
        print(f"        - {m.get('name', '?')!r} {m.get('duration', 0) / 1e6:.2f}s")

    content["tracks"] = [t for t in content["tracks"] if t not in victims]
    content["materials"]["audios"] = [m for m in content["materials"]["audios"]
                                      if m["id"] not in dead_mid]
    # 清附属素材（speeds/beats/声道映射等散在各分类里，按 id 全表扫）
    removed_extra = 0
    for key, arr in content["materials"].items():
        if isinstance(arr, list) and arr and isinstance(arr[0], dict) and "id" in arr[0]:
            keep = [m for m in arr if m["id"] not in dead_refs]
            removed_extra += len(arr) - len(keep)
            content["materials"][key] = keep
    print(f"[清理] 已移除 {removed_extra} 条附属素材")

    # 顶层时长不因删配音而变（视频轨 35.167s，BGM 35.4s 仍在）
    print(f"[时长] 顶层 duration 保持 {content['duration'] / 1e6:.3f}s")

    if not a.apply:
        print("[dry-run] 校验通过，未写入任何文件；加 --apply 落盘")
        return

    assert not jianying_running(), "剪映正在运行，中止写入"
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = f"{a.work_dir}\\backup_{a.draft}_rmtts_{ts}"
    shutil.copytree(draft_dir, backup)
    print(f"[备份] {backup}")

    with open(f"{draft_dir}\\draft_content.json", "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, separators=(",", ":"))
    shutil.copyfile(f"{draft_dir}\\draft_content.json", f"{draft_dir}\\draft_info.json")

    for p in DEPS:
        sys.path.insert(0, p)
    import jy_wrapper  # noqa: F401
    from pyJianYingDraft import DraftFolder
    tpl = DraftFolder(a.draft_root).load_template(a.draft)
    print(f"[校验] load_template 通过, duration={tpl.duration / 1e6:.3f}s")
    assert load_json(f"{draft_dir}\\draft_info.json") == content, "双 JSON 不一致"
    print("[校验] 双 JSON 完全一致；配音轨删除成功")


if __name__ == "__main__":
    main()
