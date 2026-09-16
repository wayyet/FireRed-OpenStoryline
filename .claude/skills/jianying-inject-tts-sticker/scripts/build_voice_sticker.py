# -*- coding: utf-8 -*-
"""双 JSON 注入模板：给已有剪映草稿挂一条配音音轨(读 tts_meta.json) + 手挑贴纸克隆重排。
以 draft_content.json 为准(剪映 8.9 保存只写它，含用户新挑的贴纸样本)，注入后同步给 draft_info.json 修复分叉。

依赖：仅标准库。
用法：
  $env:PYTHONIOENCODING = 'utf-8'
  python build_voice_sticker.py          # dry-run 校验
  python build_voice_sticker.py --apply  # 备份并写入双 JSON

改这里：DRAFT_DIR、TOTAL_US(草稿总时长，须与 draft_content.json 的 duration 一致)、
TRACK_A / TRACK_B(贴纸排布计划)。贴纸样本需用户先在剪映客户端手挑每一款并保存关闭。
"""
import copy
import json
import os
import shutil
import sys
import time
import uuid

sys.stdout.reconfigure(encoding="utf-8")

DRAFT_DIR = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\大岭村_治愈系Vlog"
CONTENT = os.path.join(DRAFT_DIR, "draft_content.json")
INFO = os.path.join(DRAFT_DIR, "draft_info.json")
META = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_meta.json")

TOTAL_US = 28_000_000  # 必须等于 draft_content.json 的 duration


def nid():
    return uuid.uuid4().hex


# ---------- 历史零复用（用户硬规则，详见 SKILL.md §3）----------
# 历史已用贴纸黑名单（并集）；本轮 TRACK 里的贴纸名不得出现在这里，build() 会硬校验。
# 注入成功后把本轮贴纸补进来并回写记忆 kuaishou-fx-used-history。
BANNED_STICKERS = {
    # 2026-07-03 大岭村_治愈系Vlog
    "推荐", "win赢", "夏天的浪漫", "世界杯庆祝啤酒", "颠球的豹子", "戴王冠的足球",
    # 2026-07-05 广州永华艺术馆（国风印章打卡）
    "打卡", "红色印章传统文化", "祥云 云朵 蓝色 粉色", "盖碗茶实物 古风", "人间值得 人生感悟 手写字",
}

# ---------- 贴纸排布计划 ----------
# (贴纸名, start_us, dur_us, scale, tx, ty, 用途)  贴纸名须与用户在客户端手挑的样本 name 一致
# 同一条轨(TRACK_A / TRACK_B)内时间不可重叠；要并排就分到不同轨
# ⚠️ 下面默认值是「大岭村那轮」的示例（贴纸名已在 BANNED 里，仅展示节奏 / scale / 四角坐标格式）：
#    每轮必须整体替换成用户在客户端新挑的贴纸名，否则 build() 的零复用 assert 会拦下。
TRACK_A = [
    ("推荐",          500_000, 3_000_000, 0.60, -0.45,  0.62, "开头钩子·左上"),
    ("win赢",       4_800_000, 3_000_000, 0.55,  0.45,  0.58, "惊叹强调·右上"),
    ("夏天的浪漫",   9_000_000, 4_000_000, 0.65,  0.45,  0.40, "荷花治愈点缀·右上"),
    ("夏天的浪漫",  17_300_000, 2_700_000, 0.50, -0.45,  0.45, "心静氛围·左上"),
    ("世界杯庆祝啤酒", 20_500_000, 3_500_000, 0.40,  0.48, -0.42, "夜晚小酌·右下"),
    ("推荐",       24_800_000, 2_800_000, 0.55,  0.45,  0.58, "结尾互动·右上"),
]
TRACK_B = [
    ("颠球的豹子",  13_500_000, 3_300_000, 0.42,  0.48, -0.42, "趣味点缀·右下"),
    ("戴王冠的足球", 24_800_000, 2_800_000, 0.40, -0.48, -0.40, "结尾庆祝·左下"),
]


def build(d):
    log = []
    mats = d["materials"]

    # ===== 1. 配音音轨(extract_music 极简结构 + speed material) =====
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
            "name": "配音-" + item["text"][:8], "path": path,
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

    # ===== 2. 贴纸重排(从用户手挑的样本克隆) =====
    # 收集样本: 按名称取一份 material 模板 + 任一 sticker segment 作模板
    sample_mat = {}
    for m in mats["stickers"]:
        sample_mat.setdefault(m["name"], m)
    seg_template = None
    for t in d["tracks"]:
        if t["type"] == "sticker" and t["segments"]:
            seg_template = copy.deepcopy(t["segments"][0])
            break
    assert seg_template is not None, "找不到贴纸 segment 模板(先让用户在客户端手挑贴纸并保存关闭剪映)"
    for name in {n for n, *_ in TRACK_A + TRACK_B}:
        assert name not in BANNED_STICKERS, f"贴纸 {name} 之前已用过, 禁止复用(见 SKILL.md §3)!"
        assert name in sample_mat, f"缺贴纸样本: {name}(需用户在客户端手挑该款贴纸)"

    # 移除现有贴纸轨与素材(重排,不叠加)
    d["tracks"] = [t for t in d["tracks"] if t["type"] != "sticker"]
    mats["stickers"] = []

    render_index = 15000
    for plan, tri in ((TRACK_A, 4), (TRACK_B, 5)):
        segments = []
        for name, start, dur, scale, tx, ty, why in plan:
            mat = copy.deepcopy(sample_mat[name])
            mat["id"] = nid()
            seg = copy.deepcopy(seg_template)
            seg["id"] = nid()
            seg["material_id"] = mat["id"]
            seg["target_timerange"] = {"start": start, "duration": dur}
            seg["clip"]["scale"] = {"x": scale, "y": scale}
            seg["clip"]["transform"] = {"x": tx, "y": ty}
            seg["render_index"] = render_index
            seg["track_render_index"] = tri
            seg["extra_material_refs"] = []
            seg["common_keyframes"] = []
            seg["keyframe_refs"] = []
            render_index += 1
            mats["stickers"].append(mat)
            segments.append(seg)
            log.append(f"贴纸 {name} @{start/1e6:.2f}s +{dur/1e6:.2f}s scale={scale} pos=({tx},{ty}) {why}")
        d["tracks"].append({
            "attribute": 0, "flag": 0, "id": nid(), "is_default_name": True,
            "name": "", "type": "sticker", "segments": segments,
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
    # 素材反向引用检查(仅新增的 audios/stickers)
    ref_ids = set()
    for t in d["tracks"]:
        for s in t["segments"]:
            ref_ids.add(s["material_id"])
            ref_ids.update(s.get("extra_material_refs") or [])
    for k in ("audios", "stickers"):
        for m in mats[k]:
            if m["id"] not in ref_ids:
                errs.append(f"{k} 素材未被引用: {m.get('name')}")
    if d.get("duration") != TOTAL_US:
        errs.append(f"总时长异常: {d.get('duration')}(应为 {TOTAL_US})")
    return errs


def main():
    apply = "--apply" in sys.argv
    d = json.load(open(CONTENT, encoding="utf-8"))  # 以 content 为准(含用户手挑贴纸)
    n_tracks_before = len(d["tracks"])
    log = build(d)
    errs = validate(d)
    print(f"轨道 {n_tracks_before} -> {len(d['tracks'])}")
    for line in log:
        print(" +", line)
    if errs:
        print("\n校验失败:")
        for e in errs:
            print(" !", e)
        sys.exit(1)
    print("\n校验通过:", "audios", len(d["materials"]["audios"]),
          "| stickers", len(d["materials"]["stickers"]),
          "| speeds", len(d["materials"]["speeds"]))
    if not apply:
        print("(dry-run,未写入。--apply 执行写入)")
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(CONTENT, CONTENT + f".pre_voicesticker_{ts}.bak")
    shutil.copy2(INFO, INFO + f".pre_voicesticker_{ts}.bak")
    txt = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    open(CONTENT, "w", encoding="utf-8").write(txt)
    open(INFO, "w", encoding="utf-8").write(txt)  # content 同步给 info,修复剪映 8.9 分叉
    print(f"已写入 draft_content.json 并同步 draft_info.json(备份 *_{ts}.bak)")


main()
