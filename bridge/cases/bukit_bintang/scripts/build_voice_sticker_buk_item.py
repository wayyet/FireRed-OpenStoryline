# -*- coding: utf-8 -*-
"""配音音轨 + 贴纸克隆重排注入：吉隆坡武吉免登_纯视频
dry-run（默认）→ 预览注入方案
--apply → 备份并写入双 JSON
"""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import json, copy, os, uuid
from pathlib import Path

DRAFT_DIR = Path(r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\吉隆坡武吉免登_纯视频")
CONTENT_PATH = DRAFT_DIR / "draft_content.json"
INFO_PATH = DRAFT_DIR / "draft_info.json"
META_PATH = DRAFT_DIR / "textReading" / "tts_meta.json"

# ===== 历史黑名单（按 resource_id）=====
BANNED_RIDS = {
    # 贴纸历史并集（resource_id）
    "7160597532043644174",  # 打卡（广州永华）
    "7324834813670624550",  # 灯笼…祥云…（柏威年）
    "7621895804437073214",  # 清明踏青-桃花
    "7569506496774524185",  # 手绘水墨冬日节气 贴年红
    "7582107859966676249",  # 古风水墨BLING纸扇
    "6979449894960434439",  # 盆栽盆景 绿萝
    "7324678307365129526",  # 福牌
    # 配音音色（不在这里管，由 gen_tts.py BANNED_SPEAKERS 管）
}
# 名字→rid 映射，用于报错
NAME_TO_HISTORICAL_RID = {
    "定位": "原EXCHANGE TRX款（非本轮rid）",
}

# 本轮新贴纸（校验用）
TRACK_A = [
    # 轨A：钩子 + 中段 + 结尾
    {"name": "霓虹灯箭头",   "rid": "7209167775032528143", "start_us": 0,       "dur_us": 3_000_000, "scale": 0.55, "tx": -0.45, "ty": 0.60},
    {"name": "氛围感绝了",   "rid": "7562785814883781913", "start_us": 19_500_000, "dur_us": 3_000_000, "scale": 0.60, "tx": 0.45,  "ty": 0.55},
    {"name": "惊讶表情",     "rid": "7531750617274961214", "start_us": 25_000_000, "dur_us": 3_000_000, "scale": 0.50, "tx": -0.40, "ty": -0.40},
]
TRACK_B = [
    # 轨B：商业街 + 地标 + 打卡
    {"name": "霓虹灯灯牌夏日", "rid": "7356172910022642954", "start_us": 4_466_000, "dur_us": 3_000_000, "scale": 0.50, "tx": 0.45,  "ty": 0.50},
    {"name": "定位",           "rid": "7495226539202858302", "start_us": 9_233_000, "dur_us": 3_000_000, "scale": 0.45, "tx": -0.45, "ty": 0.45},
    {"name": "good太棒了",     "rid": "7646347519785471257", "start_us": 14_100_000, "dur_us": 3_000_000, "scale": 0.55, "tx": 0.40,  "ty": -0.42},
]

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

def uuid4():
    return str(uuid.uuid4()).replace("-", "")

def inject(draft, tts_meta, dry_run=True):
    mats = draft["materials"]
    tracks = draft["tracks"]

    # ---- 1. 加载 tts_meta ----
    tts_entries = {e["file"]: e for e in tts_meta}

    # ---- 2. 配音：找/建 audio 轨 ----
    audio_track = next((t for t in tracks if t["type"] == "audio"), None)
    if audio_track is None:
        audio_track = {"type": "audio", "render_index": 3, "segments": []}
        tracks.append(audio_track)
    else:
        audio_track["segments"] = []
    audio_track["keyframes"] = {"segments": []}

    # materials.audios + speeds（每条一个 speed material）
    speed_ids = []
    for entry in tts_meta:
        audio_id = uuid4()
        speed_id = uuid4()
        speed_ids.append((audio_id, speed_id, entry))

        path_str = str(DRAFT_DIR / "textReading" / entry["file"]).replace("\\", "/")
        mat = {
            "id": audio_id, "local_material_id": audio_id,
            "music_id": audio_id, "type": "extract_music",
            "path": path_str, "duration": entry["audio_us"],
            "name": entry["text"][:20], "check_flag": 3,
            "source_platform": 0, "category_name": "local", "wave_points": [],
        }
        mats["audios"].append(mat)

        speed_mat = {
            "id": speed_id, "type": "speed",
            "speed": 1.0, "mode": 0, "curve_speed": None,
        }
        mats["speeds"].append(speed_mat)

        # segment
        seg = {
            "id": uuid4(), "material_id": audio_id,
            "target_timerange": {"start": entry["sub_start"], "duration": entry["audio_us"]},
            "source_timerange": {"start": 0, "duration": entry["audio_us"]},
            "volume": 1.0, "track_render_index": 0,
            "extra_material_refs": [speed_id],
            "keyframes": {"segments": []},
        }
        audio_track["segments"].append(seg)

    # ---- 3. 贴纸：清旧轨 + 克隆新轨 ----
    # 收集样本 material 和 segment 模板（从草稿现有 sticker 轨）
    sticker_mats = {s["name"]: s for s in mats.get("stickers", [])}
    sticker_tracks = [t for t in tracks if t["type"] == "sticker"]
    if not sticker_tracks:
        print("ERROR: 草稿没有 sticker 轨，请先在剪映客户端手挑贴纸样本")
        return False
    # 任选一条轨作 segment 模板
    seg_template = copy.deepcopy(sticker_tracks[0]["segments"][0])
    track_render_index = sticker_tracks[0].get("track_render_index", 4)

    # 清旧贴纸轨和 materials.stickers
    tracks[:] = [t for t in tracks if t["type"] != "sticker"]
    mats["stickers"] = []

    def clone_sticker(plan, track_render_idx, render_idx_start):
        track = {"type": "sticker", "render_index": render_idx_start,
                 "track_render_index": track_render_idx, "segments": []}
        for i, item in enumerate(plan):
            name = item["name"]
            # 校验黑名单
            assert item["rid"] not in BANNED_RIDS, f"贴纸 {name}(rid={item['rid']}) 在历史黑名单中!"
            # 找样本
            sample = sticker_mats.get(name)
            if not sample:
                print(f"  警告: 样本 '{name}' 不在草稿中，跳过")
                continue
            # 克隆 material
            new_mat = copy.deepcopy(sample)
            new_mat["id"] = uuid4()
            mats["stickers"].append(new_mat)
            # 克隆 segment
            new_seg = copy.deepcopy(seg_template)
            new_seg["id"] = uuid4()
            new_seg["material_id"] = new_mat["id"]
            new_seg["target_timerange"] = {"start": item["start_us"], "duration": item["dur_us"]}
            # scale / transform
            if "clip" not in new_seg:
                new_seg["clip"] = {}
            new_seg["clip"]["scale"] = item["scale"]
            new_seg["clip"]["transform"] = {"x": item["tx"], "y": item["ty"], "rotation": 0, "scale_x": 1.0, "scale_y": 1.0}
            new_seg["track_render_index"] = track_render_idx
            new_seg["render_index"] = render_idx_start + i
            track["segments"].append(new_seg)
        tracks.append(track)
        return track

    # 轨A → render_index=4, 轨B → render_index=5
    ta = clone_sticker(TRACK_A, track_render_index, 4)
    tb = clone_sticker(TRACK_B, track_render_index, 5)

    # ---- 4. 打印预览 ----
    print(f"\n=== 注入预览 ===")
    print(f"配音轨 segments: {len(audio_track['segments'])} 条")
    for seg in audio_track["segments"]:
        tr = seg["target_timerange"]
        print(f"  [{tr['start']//1000}ms +{tr['duration']//1000}ms] {seg['material_id'][:8]}...")
    print(f"贴纸轨A (render_index=4): {len(ta['segments'])} 个")
    for s in ta["segments"]:
        tr = s["target_timerange"]
        mid = s["material_id"]
        name = next((m.get("name","") for m in mats["stickers"] if m["id"]==mid), mid)
        print(f"  [{tr['start']//1000}ms +{tr['duration']//1000}ms] {name}")
    print(f"贴纸轨B (render_index=5): {len(tb['segments'])} 个")
    for s in tb["segments"]:
        tr = s["target_timerange"]
        mid = s["material_id"]
        name = next((m.get("name","") for m in mats["stickers"] if m["id"]==mid), mid)
        print(f"  [{tr['start']//1000}ms +{tr['duration']//1000}ms] {name}")
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    draft = load_json(CONTENT_PATH)
    tts_meta = load_json(META_PATH)
    total_us = draft["duration"]

    ok = inject(draft, tts_meta, dry_run=not args.apply)
    if not ok:
        sys.exit(1)

    if args.apply:
        # 备份
        for p in [CONTENT_PATH, INFO_PATH]:
            if p.exists():
                bak = p.with_suffix(p.suffix + f".pre_voicesticker_{len(list(DRAFT_DIR.glob('*.bak')))+1}.bak")
                bak.write_bytes(p.read_bytes())
                print(f"备份: {bak.name}")
        # 写 content
        save_json(CONTENT_PATH, draft)
        print(f"写入: {CONTENT_PATH.name}")
        # 同步 info
        content_txt = CONTENT_PATH.read_bytes()
        INFO_PATH.write_bytes(content_txt)
        print(f"同步: {INFO_PATH.name}")
        # 校验总时长不变
        draft2 = load_json(CONTENT_PATH)
        assert draft2["duration"] == total_us, f"总时长被改变! {total_us} -> {draft2['duration']}"
        print(f"总时长校验: {total_us//1000}ms 不变")
    else:
        print("\n[dry-run] 加上 --apply 执行写入")

if __name__ == "__main__":
    main()
