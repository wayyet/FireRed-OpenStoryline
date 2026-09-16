# -*- coding: utf-8 -*-
"""只读侦查剪映草稿结构：时长、轨道、分镜、已有文字、素材源时间（供抽帧看画面）。

用法:
  python recon_draft.py --draft <草稿名> [--draft-root <草稿根目录>]

输出要点:
  - 双 JSON (draft_info / draft_content) 时长与内容是否分叉（content 为真相）
  - 每条轨道的 type / name / render_index / 段数
  - 视频轨每段: 时间轴区间、speed、素材路径、源时间区间、抽帧建议时刻（源中点）
  - 文字轨每段: 时间轴区间 + 文本内容（判断是否已有字幕）
"""
import argparse
import json

DEFAULT_ROOT = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"


def us2s(us):
    return round(us / 1_000_000, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True, help="草稿名（草稿根目录下的文件夹名）")
    ap.add_argument("--draft-root", default=DEFAULT_ROOT)
    a = ap.parse_args()
    draft_dir = f"{a.draft_root}\\{a.draft}"

    loaded = {}
    for fname in ("draft_info.json", "draft_content.json"):
        with open(f"{draft_dir}\\{fname}", encoding="utf-8") as f:
            loaded[fname] = json.load(f)

    # 分叉检测：剪映 8.9 起可能只写 content —— content 为真相
    same = loaded["draft_info.json"] == loaded["draft_content.json"]
    print(f"双 JSON 完全一致: {same}"
          + ("" if same else "  ←—— 已分叉！以 draft_content.json 为真相，写入时用 content 覆盖 info"))

    d = loaded["draft_content.json"]
    mats = d.get("materials", {})
    videos = {v.get("id"): v for v in (mats.get("videos") or [])}
    texts = {t.get("id"): t for t in (mats.get("texts") or [])}

    print(f"总时长: {us2s(d['duration'])}s   画布: "
          f"{d['canvas_config']['width']}x{d['canvas_config']['height']}")
    print(f"materials: texts={len(texts)} videos={len(videos)} "
          f"audios={len(mats.get('audios') or [])} stickers={len(mats.get('stickers') or [])} "
          f"effects={len(mats.get('video_effects') or [])} transitions={len(mats.get('transitions') or [])}")

    for ti, tr in enumerate(d.get("tracks", [])):
        segs = tr.get("segments", [])
        print(f"\n轨道[{ti}] type={tr.get('type')} name={tr.get('name')!r} "
              f"render_index={tr.get('render_index')} segments={len(segs)}")
        for si, seg in enumerate(segs):
            t = seg.get("target_timerange", {})
            s, dur = t.get("start", 0), t.get("duration", 0)
            info = f"  seg[{si}] {us2s(s)}s -> {us2s(s + dur)}s (时长 {us2s(dur)}s) speed={seg.get('speed')}"
            mid = seg.get("material_id")
            if tr.get("type") == "text" and mid in texts:
                try:
                    content = json.loads(texts[mid].get("content", "{}")).get("text", "")
                except Exception:
                    content = str(texts[mid].get("content"))[:50]
                info += f"  文本: {content!r}"
            elif tr.get("type") == "video" and mid in videos:
                v = videos[mid]
                st = seg.get("source_timerange") or {}
                ss, sd = st.get("start", 0), st.get("duration", 0)
                info += (f"\n         素材: {v.get('path', '')}"
                         f"\n         源区间: {us2s(ss)}s + {us2s(sd)}s"
                         f"  抽帧建议 -ss {us2s(ss + sd // 2)}")
            print(info)


if __name__ == "__main__":
    main()
