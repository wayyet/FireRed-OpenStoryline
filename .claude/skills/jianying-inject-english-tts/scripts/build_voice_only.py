# -*- coding: utf-8 -*-
"""双 JSON 注入模板：只给已有剪映草稿挂一条英文配音音轨（读 tts_meta.json），
不触碰任何贴纸轨/贴纸素材/字幕/转场特效/BGM。
由姊妹技能 jianying-inject-tts-sticker 的 build_voice_sticker.py 裁剪而来——
删掉了"贴纸重排"整段（那段会清空 sticker 轨重建，跳过即保留原样），
并新增"贴纸素材数量前后一致"断言防误伤。
以 draft_content.json 为准读取，注入后同步给 draft_info.json 修复剪映 8.9 分叉。

依赖：仅标准库。
用法：
  $env:PYTHONIOENCODING = 'utf-8'
  & "C:\\Program Files\\Python313\\python.exe" .\\build_voice_only.py          # dry-run 校验
  & "C:\\Program Files\\Python313\\python.exe" .\\build_voice_only.py --apply  # 备份并写入双 JSON

改这里：DRAFT_DIR、TOTAL_US（必须等于 draft_content.json 的 duration）。
2026-07-11 在 吉隆坡柏威年广场（35.4s / 7句英文配音 / 原10个贴纸零触碰）验证成功。
"""
import json
import os
import shutil
import sys
import time
import uuid

sys.stdout.reconfigure(encoding="utf-8")

DRAFT_DIR = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>"
CONTENT = os.path.join(DRAFT_DIR, "draft_content.json")
INFO = os.path.join(DRAFT_DIR, "draft_info.json")
META = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_meta.json")

TOTAL_US = 35_400_000  # 必须等于 draft_content.json 的 duration


def nid():
    return uuid.uuid4().hex


def build(d):
    log = []
    mats = d["materials"]

    # ===== 配音音轨（extract_music 极简结构 + speed material）=====
    tts = json.load(open(META, encoding="utf-8"))
    audio_segments = []
    for item in tts:
        path = (DRAFT_DIR + "\\textReading\\" + item["file"]).replace("\\", "/")
        assert os.path.exists(path), path
        mat_id, speed_id, seg_id = nid(), nid(), nid()
        mats["audios"].append({
            "app_id": 0, "category_id": "", "category_name": "local",
            "check_flag": 3, "copyright_limit_type": "none",
            "duration": item["audio_us"], "effect_id": "", "formula_id": "",
            "id": mat_id, "local_material_id": mat_id, "music_id": mat_id,
            "name": "配音-" + item["text"][:12], "path": path,
            "source_platform": 0, "type": "extract_music", "wave_points": [],
        })
        mats["speeds"].append({
            "curve_speed": None, "id": speed_id, "mode": 0, "speed": 1.0, "type": "speed",
        })
        audio_segments.append({
            "clip": None, "hdr_settings": None,
            "enable_adjust": True, "enable_color_correct_adjust": False,
            "enable_color_curves": True, "enable_color_match_adjust": False,
            "enable_color_wheels": True, "enable_lut": True,
            "enable_smart_color_adjust": False,
            "last_nonzero_volume": 1.0, "reverse": False,
            "track_attribute": 0, "track_render_index": 0, "visible": True,
            "id": seg_id, "material_id": mat_id,
            "target_timerange": {"start": item["sub_start"], "duration": item["audio_us"]},
            "source_timerange": {"start": 0, "duration": item["audio_us"]},
            "speed": 1.0, "volume": 1.0,
            "extra_material_refs": [speed_id], "is_tone_modify": False,
            "common_keyframes": [], "keyframe_refs": [],
        })
        log.append(f"配音 {item['file']} @{item['sub_start']/1e6:.2f}s +{item['audio_us']/1e6:.2f}s 《{item['text']}》")

    d["tracks"].append({
        "attribute": 0, "flag": 0, "id": nid(), "is_default_name": True,
        "name": "", "type": "audio", "segments": audio_segments,
    })
    return log


def validate(d):
    errs = []
    mats = d["materials"]
    all_mat_ids = set()
    for k, v in mats.items():
        if isinstance(v, list):
            for m in v:
                if isinstance(m, dict) and "id" in m:
                    all_mat_ids.add(m["id"])
    for t in d["tracks"]:
        segs = sorted(t["segments"], key=lambda s: s["target_timerange"]["start"])
        prev_end = -1
        for s in segs:
            tr = s["target_timerange"]
            if tr["start"] < prev_end:
                errs.append(f"{t['type']} 轨片段重叠 @{tr['start']}")
            prev_end = tr["start"] + tr["duration"]
            if prev_end > TOTAL_US:
                errs.append(f"{t['type']} 轨片段越界 end={prev_end}")
            if s["material_id"] not in all_mat_ids:
                errs.append(f"{t['type']} 轨 segment 引用不存在的素材 {s['material_id']}")
            for r in s.get("extra_material_refs") or []:
                if r not in all_mat_ids:
                    errs.append(f"segment 引用不存在的附加素材 {r}")
    # 素材反向引用检查（仅 audios；本 skill 不动 stickers）
    ref_ids = set()
    for t in d["tracks"]:
        for s in t["segments"]:
            ref_ids.add(s["material_id"])
            ref_ids.update(s.get("extra_material_refs") or [])
    for m in mats["audios"]:
        if m["id"] not in ref_ids:
            errs.append(f"audios 素材未被引用: {m.get('name')}")
    if d.get("duration") != TOTAL_US:
        errs.append(f"总时长异常: {d.get('duration')}(应为 {TOTAL_US})")
    return errs


def main():
    apply = "--apply" in sys.argv
    d = json.load(open(CONTENT, encoding="utf-8"))  # 以 content 为准
    n_tracks_before = len(d["tracks"])
    n_stickers_before = len(d["materials"]["stickers"])
    log = build(d)
    errs = validate(d)
    n_stickers_after = len(d["materials"]["stickers"])
    print(f"轨道 {n_tracks_before} -> {len(d['tracks'])}")
    for line in log:
        print(" +", line)
    print(f"贴纸素材数量核对(应不变): {n_stickers_before} -> {n_stickers_after}")
    assert n_stickers_before == n_stickers_after, "贴纸素材数量变了，本 skill 不该动贴纸！"
    if errs:
        print("\n校验失败:")
        for e in errs:
            print(" !", e)
        sys.exit(1)
    print("\n校验通过: audios", len(d["materials"]["audios"]), "| speeds", len(d["materials"]["speeds"]))
    if not apply:
        print("(dry-run,未写入。--apply 执行写入)")
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(CONTENT, CONTENT + f".pre_voiceonly_{ts}.bak")
    shutil.copy2(INFO, INFO + f".pre_voiceonly_{ts}.bak")
    txt = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    open(CONTENT, "w", encoding="utf-8").write(txt)
    open(INFO, "w", encoding="utf-8").write(txt)  # content 同步给 info，修复剪映 8.9 分叉
    print(f"已写入 draft_content.json 并同步 draft_info.json(备份 *_{ts}.bak)")


main()
