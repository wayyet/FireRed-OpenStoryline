# -*- coding: utf-8 -*-
"""
把 OpenStoryline (FireRed-OpenStoryline) 某个会话的时间线编排
(plan_timeline_pro_*.json) 重建为一个剪映 (JianYing Pro) 草稿，写进剪映草稿目录，
便于在剪映里二次编辑。

支持的轨道（"尽力而为"）：
  - video      : 确定性重建（按时间线落点拼接切片）
  - subtitles  : 确定性重建（用 plan 里的 text + timeline_window）
  - voiceover  : 尽力重建（检测到音频路径就加，字段不符/文件缺失则跳过并告警）
  - bgm        : 尽力重建（同上）

用法示例：
  python build_draft.py                      # 自动选最新且含有效时间线的会话
  python build_draft.py --session <会话id>   # 指定会话
  python build_draft.py --name 我的草稿       # 自定义草稿名
  python build_draft.py --only-video         # 只重建视频轨

设计参考记忆 openstoryline-to-jianying-bridge：safe_tim() 把 int 当微秒，
所以所有时间一律以 "毫秒 * 1000" 的整数微秒传入，最精确无歧义。
"""
import os
import sys
import json
import argparse

DEFAULT_OUTPUTS_ROOT = r"D:\Documents\kuaishou\FireRed-OpenStoryline\outputs"


# ============ 1. Bootstrap：定位 jianying-editor skill 并导入 JyProject ============
def _find_jy_scripts():
    """定位 jianying-editor/scripts（内含 jy_wrapper.py），用于导入 JyProject。
    jy_wrapper 顶部的 setup_env() 会把 vendor 下的 pyJianYingDraft 注入 sys.path。"""
    cands = []
    env_root = os.getenv("JY_SKILL_ROOT", "").strip()
    if env_root:
        cands += [env_root, os.path.join(env_root, "scripts")]
    here = os.path.dirname(os.path.abspath(__file__))
    # 兄弟 skill：.../skills/jianying-editor/scripts
    cands.append(os.path.join(here, "..", "..", "jianying-editor", "scripts"))
    # 逐级向上回溯，匹配 .claude/skills 或 skills 布局
    d = here
    for _ in range(8):
        cands.append(os.path.join(d, ".claude", "skills", "jianying-editor", "scripts"))
        cands.append(os.path.join(d, "skills", "jianying-editor", "scripts"))
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    tried = []
    for c in cands:
        c = os.path.abspath(c)
        tried.append(c)
        if os.path.isfile(os.path.join(c, "jy_wrapper.py")):
            return c
    raise ImportError("找不到 jianying-editor/scripts/jy_wrapper.py，尝试过：\n- " + "\n- ".join(tried))


_scripts_path = _find_jy_scripts()
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)
from jy_wrapper import JyProject  # noqa: E402


# ============ 2. 工具函数 ============
def ms_to_us(ms):
    """毫秒 -> 微秒（safe_tim 把 int 当微秒，转整数微秒最精确）。"""
    return int(round(float(ms) * 1000))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def tw_duration(window):
    """从 timeline_window / source_window 取时长（ms）。优先 duration，否则 end-start。"""
    if not window:
        return 0
    d = window.get("duration")
    if d is not None:
        return d
    return (window.get("end", 0) or 0) - (window.get("start", 0) or 0)


def latest_plan(ptp_dir):
    """返回会话 plan_timeline_pro 目录下按修改时间最新的 plan json，没有则 None。"""
    if not os.path.isdir(ptp_dir):
        return None
    files = [
        os.path.join(ptp_dir, f)
        for f in os.listdir(ptp_dir)
        if f.startswith("plan_timeline_pro") and f.endswith(".json")
    ]
    return max(files, key=os.path.getmtime) if files else None


def pick_session(outputs_root, session=None):
    """选会话目录：指定则用之；否则自动挑'含有效时间线(video 非空)且最新'的会话。
    返回 (会话目录, plan_json 路径)。"""
    if session:
        sdir = os.path.join(outputs_root, session)
        if not os.path.isdir(sdir):
            raise FileNotFoundError(f"会话目录不存在: {sdir}")
        plan = latest_plan(os.path.join(sdir, "plan_timeline_pro"))
        if not plan:
            raise FileNotFoundError(f"会话 {session} 下没有 plan_timeline_pro_*.json（可能尚未编排时间线）")
        return sdir, plan

    best = None  # (mtime, sdir, plan)
    for name in os.listdir(outputs_root):
        sdir = os.path.join(outputs_root, name)
        plan = latest_plan(os.path.join(sdir, "plan_timeline_pro"))
        if not plan:
            continue
        try:
            data = load_json(plan)
            videos = data["payload"]["tracks"].get("video", [])
        except Exception:
            continue
        if not videos:
            continue
        mt = os.path.getmtime(plan)
        if best is None or mt > best[0]:
            best = (mt, sdir, plan)
    if not best:
        raise RuntimeError(f"在 {outputs_root} 下未找到任何含有效时间线(video 非空)的会话")
    return best[1], best[2]


# ============ 3. 各轨道重建 ============
def add_videos(project, videos):
    added, missing, failed = 0, [], []
    for v in videos:
        src = v.get("source_path")
        sw = v.get("source_window", {}) or {}
        tw = v.get("timeline_window", {}) or {}
        if not src or not os.path.exists(src):
            missing.append((v.get("clip_id"), src))
            print(f"  ⚠ 缺失切片，跳过: {v.get('clip_id')} -> {src}")
            continue
        dur = sw.get("duration") if sw.get("duration") is not None else tw_duration(tw)
        seg = project.add_media_safe(
            src,
            start_time=ms_to_us(tw.get("start", 0)),
            duration=ms_to_us(dur),
            source_start=ms_to_us(sw.get("start", 0)),
        )
        if seg is None:
            failed.append(v.get("clip_id"))
            print(f"  ❌ 视频导入失败: {v.get('clip_id')}")
        else:
            added += 1
            print(f"  ✓ 视频 {v.get('clip_id')}  时间线 {tw.get('start')}~{tw.get('end')}ms")
    return added, missing, failed


def add_subtitles(project, subtitles, track_name="Subtitles"):
    added = 0
    for s in subtitles:
        text = (s.get("text") or "").strip()
        tw = s.get("timeline_window") or {}
        if not text or not tw:
            continue
        dur = tw_duration(tw)
        if dur <= 0:
            dur = 1000  # 兜底最小 1s，避免零时长
        try:
            project.add_text_simple(
                text,
                start_time=ms_to_us(tw.get("start", 0)),
                duration=ms_to_us(dur),
                track_name=track_name,
            )
            added += 1
            print(f"  ✓ 字幕 {tw.get('start')}ms: {text[:16]}")
        except Exception as e:
            print(f"  ❌ 字幕失败({text[:12]}…): {e}")
    return added


def add_audio(project, segs, label, track_name):
    """voiceover / bgm 的尽力重建：每段独立 try，失败只告警跳过，绝不让整体崩。"""
    added = 0
    for a in segs:
        try:
            path = a.get("source_path") or a.get("path") or a.get("audio_path")
            tw = a.get("timeline_window") or {}
            if not path or not os.path.exists(path) or not tw:
                print(f"  ⚠ {label} 跳过（无可用音频路径或时间线）: {str(path)[:60]}")
                continue
            sw = a.get("source_window", {}) or {}
            dur = sw.get("duration") if sw.get("duration") is not None else tw_duration(tw)
            seg = project.add_audio_safe(
                path,
                start_time=ms_to_us(tw.get("start", 0)),
                duration=ms_to_us(dur),
                track_name=track_name,
            )
            if seg is not None:
                added += 1
                print(f"  ✓ {label} {tw.get('start')}ms -> {os.path.basename(path)}")
        except Exception as e:
            print(f"  ❌ {label} 失败，跳过: {e}")
    return added


# ============ 4. 主流程 ============
def main():
    ap = argparse.ArgumentParser(description="把 OpenStoryline 时间线重建为剪映草稿")
    ap.add_argument("--session", default=None, help="OpenStoryline 会话id；省略则自动选最新且含有效时间线的会话")
    ap.add_argument("--name", default=None, help="生成的剪映草稿名；省略则用 OpenStoryline_<短id>")
    ap.add_argument("--outputs-root", default=DEFAULT_OUTPUTS_ROOT, help="OpenStoryline outputs 根目录")
    ap.add_argument("--only-video", action="store_true", help="只重建视频轨")
    args = ap.parse_args()

    sdir, plan_path = pick_session(args.outputs_root, args.session)
    session_id = os.path.basename(sdir.rstrip("\\/"))
    draft_name = args.name or f"OpenStoryline_{session_id[:8]}"

    plan = load_json(plan_path)
    tracks = plan["payload"]["tracks"]
    videos = tracks.get("video", []) or []
    subtitles = tracks.get("subtitles", []) or []
    voiceover = tracks.get("voiceover", []) or []
    bgm = tracks.get("bgm", []) or []

    if not videos:
        print("❌ plan 里没有视频片段，终止。")
        sys.exit(2)

    first_size = videos[0].get("size") or [1920, 1080]
    width, height = int(first_size[0]), int(first_size[1])

    print(f"会话       : {session_id}")
    print(f"plan       : {os.path.basename(plan_path)}")
    print(f"草稿名     : {draft_name}   分辨率: {width}x{height}")
    print(f"轨道统计   : 视频{len(videos)} / 字幕{len(subtitles)} / 配音{len(voiceover)} / BGM{len(bgm)}")
    print("-" * 40)

    # overwrite=True：同名草稿覆盖重建（也会触发 v5.9+ 自修复）
    project = JyProject(draft_name, width=width, height=height, overwrite=True)

    v_added, v_missing, v_failed = add_videos(project, videos)
    s_added = vo_added = bgm_added = 0
    if not args.only_video:
        if subtitles:
            s_added = add_subtitles(project, subtitles)
        if voiceover:
            vo_added = add_audio(project, voiceover, "配音", "Voiceover")
        if bgm:
            bgm_added = add_audio(project, bgm, "BGM", "BGM")

    result = project.save()
    draft_path = result.get("draft_path") if isinstance(result, dict) else None

    total_ms = max((v.get("timeline_window", {}).get("end", 0) for v in videos), default=0)
    print("\n================ 完成 ================")
    print(f"草稿名     : {draft_name}")
    print(f"视频片段   : {v_added}/{len(videos)}")
    if not args.only_video:
        print(f"字幕       : {s_added}/{len(subtitles)}")
        print(f"配音       : {vo_added}/{len(voiceover)}")
        print(f"BGM        : {bgm_added}/{len(bgm)}")
    print(f"时间线总长 : {total_ms / 1000:.2f}s")
    if v_missing:
        print(f"缺失切片   : {[c for c, _ in v_missing]}")
    if v_failed:
        print(f"导入失败   : {v_failed}")
    if draft_path:
        print(f"草稿目录   : {draft_path}")
    print("提示：剪映若已打开，需重启剪映才能在草稿箱看到该草稿（草稿列表在启动时读取）。")


if __name__ == "__main__":
    main()
