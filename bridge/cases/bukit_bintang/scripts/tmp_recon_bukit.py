# -*- coding: utf-8 -*-
import json

path = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\吉隆坡武吉免登_纯视频\draft_content.json"
info_path = path.replace("draft_content.json", "draft_info.json")

with open(path, encoding="utf-8") as f:
    content = json.load(f)
with open(info_path, encoding="utf-8") as f:
    info = json.load(f)

print(f"双 JSON 完全一致: {content == info}")
d = content
mats = d.get("materials", {})
texts = {t["id"]: t for t in mats.get("texts", [])}
videos = {v["id"]: v for v in mats.get("videos", [])}
audios = mats.get("audios", [])

print(f"总时长: {round(d['duration']/1e6, 3)}s   画布: {d['canvas_config']['width']}x{d['canvas_config']['height']}")
print(f"materials: texts={len(texts)} videos={len(videos)} audios={len(audios)}")

for ti, tr in enumerate(d.get("tracks", [])):
    segs = tr.get("segments", [])
    print(f"\n轨道[{ti}] type={tr.get('type')} name={tr.get('name')!r} render_index={tr.get('render_index')} segments={len(segs)}")
    for si, seg in enumerate(segs):
        t = seg.get("target_timerange", {})
        s, dur = t.get("start", 0), t.get("duration", 0)
        mid = seg.get("material_id")
        line = f"  seg[{si}] {round(s/1e6,3)}s -> {round((s+dur)/1e6,3)}s (时长 {round(dur/1e6,3)}s) speed={seg.get('speed')}"
        if tr.get("type") == "text" and mid in texts:
            content_text = json.loads(texts[mid].get("content", "{}")).get("text", "")
            fs = texts[mid].get("font_size")
            styles = texts[mid].get("styles", [{}])[0].get("size")
            print(line + f"  文本: {content_text!r} font_size={fs} styles.size={styles}")
        elif tr.get("type") == "video" and mid in videos:
            v = videos[mid]
            st = seg.get("source_timerange") or {}
            ss, sd = st.get("start", 0), st.get("duration", 0)
            print(line)
            print(f"         素材: {v.get('path', '')}")
            print(f"         源区间: {round(ss/1e6,3)}s + {round(sd/1e6,3)}s  抽帧建议 -ss {round((ss+sd//2)/1e6,3)}")
        elif tr.get("type") == "audio":
            au = next((a for a in audios if a.get("id") == mid), {})
            print(line + f"  audio type={au.get('type')} path={au.get('path', '')}")
