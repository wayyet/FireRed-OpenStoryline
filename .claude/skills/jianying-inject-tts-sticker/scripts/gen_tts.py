# -*- coding: utf-8 -*-
"""配音生成模板：走剪映同款 SAMI 接口，为每句文案生成 ogg_opus 旁白，
落到草稿 textReading 目录，并量真实时长、逐句报是否溢出字幕窗口，产出 tts_meta.json 供注入脚本读取。

依赖：系统 Python 3.13 + websockets（pip install websockets）。
用法：
  $env:PYTHONIOENCODING = 'utf-8'
  & "C:\\Program Files\\Python313\\python.exe" .\\gen_tts.py

改这里：DRAFT_DIR（草稿名）、SPEAKER（见 SKILL.md 可用音色表）、LINES（每句照字幕文案与窗口）。
"""
import asyncio
import json
import os
import re
import ssl
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")

import websockets  # noqa: E402  第三方依赖，仅生成配音时需要

APP_KEY = "IZjhUeAYwP"
APP_ID = "3704"
# SPEAKER：每轮从 SKILL.md §3 可用音色表里挑一个"没用过"的新款（换音色前先跑 probe_speakers.py）。
# 下面是示例默认（故事女声，适合旁白）——按当轮视频主题/性别改，别沿用上一轮。
SPEAKER = "en_female_emotional"

# ---- 历史零复用（用户硬规则，详见 SKILL.md §3）----
# 历史已用音色黑名单（中文音色池）；英文音色是独立池，本轮 en_female_emotional 不在其中。
# 注入成功后把本轮实际用的音色补进来并回写记忆 kuaishou-fx-used-history。
BANNED_SPEAKERS = {
    "zh_female_zhixing",   # 2026-07-03 大岭村_治愈系Vlog（知性女声）
    "zh_male_chunhou",     # 2026-07-05 广州永华艺术馆（醇厚男声）
    "BV700_streaming",     # 2026-07-07 吉隆坡EXCHANGE TRX商场（灿灿）
    "BV701_streaming",     # 2026-07-07 吉隆坡柏威年广场 中文版（擎苍，已随中文配音删除）
}
assert SPEAKER not in BANNED_SPEAKERS, f"音色 {SPEAKER} 之前已用过, 禁止复用(见 SKILL.md §3)!"

DRAFT_DIR = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\吉隆坡柏威年广场"
OUT_DIR = os.path.join(DRAFT_DIR, "textReading")

# (文件名, 文本, 字幕起点us, 字幕窗口us) —— 照英文字幕轨文案与 target_timerange 逐句填
# 第3/5句原字幕含"+"/"="排版符号，已按用户确认改写为自然口语（不字面照读符号）
LINES = [
    ("voice_en_01.ogg", "Giant golden rooster at this KL mall!", 0, 5_033_333),
    ("voice_en_02.ogg", "Flowers everywhere — every pic pops!", 5_033_333, 5_033_333),
    ("voice_en_03.ogg", "Blossoms and lanterns bring the Chinese vibes!", 10_066_666, 5_000_000),
    ("voice_en_04.ogg", "Every corner is a photo spot!", 15_066_666, 4_566_667),
    ("voice_en_05.ogg", "Lattice and red lanterns, so photogenic!", 19_633_333, 4_500_000),
    ("voice_en_06.ogg", "Even stumbled on a bonsai show!", 24_133_333, 5_500_000),
    ("voice_en_07.ogg", "Pavilion Bukit Jalil — don't miss it!", 29_633_333, 5_533_333),
]


def get_jy_local_config():
    """从本机剪映配置提取 device_id / iid，失败用兜底默认值。"""
    defaults = ("1053764930506284", "2314914062247833")
    jy_user_data = os.path.join(os.getenv("LOCALAPPDATA"), "JianyingPro", "User Data")
    cfg = {"device_id": defaults[0], "iid": defaults[1]}
    ttnet_path = os.path.join(jy_user_data, "TTNet", "tt_net_config.config")
    if os.path.exists(ttnet_path):
        try:
            content = open(ttnet_path, "r", encoding="utf-8", errors="ignore").read()
            m = re.search(r"device_id\&#\*(\d+)", content)
            if m:
                cfg["device_id"] = m.group(1)
        except Exception:
            pass
    log_dir = os.path.join(jy_user_data, "Log")
    if os.path.exists(log_dir):
        logs = sorted(
            [os.path.join(log_dir, x) for x in os.listdir(log_dir) if x.endswith(".log")],
            key=os.path.getmtime, reverse=True)
        for p in logs[:5]:
            try:
                chunk = open(p, "r", encoding="utf-8", errors="ignore").read(1_000_000)
                m = re.search(r"iid=(\d+)", chunk)
                if m:
                    cfg["iid"] = m.group(1)
                    break
            except Exception:
                continue
    return cfg["device_id"], cfg["iid"]


def ogg_opus_duration_us(path):
    """解析 ogg 页，取最后一页 granulepos(恒定 48kHz 时基)，换算微秒。"""
    data = open(path, "rb").read()
    last_granule = 0
    pos = 0
    while True:
        idx = data.find(b"OggS", pos)
        if idx < 0:
            break
        if idx + 27 > len(data):
            break
        granule = struct.unpack_from("<q", data, idx + 6)[0]
        nsegs = data[idx + 26]
        seg_table = data[idx + 27: idx + 27 + nsegs]
        body_len = sum(seg_table)
        if granule > 0:
            last_granule = granule
        pos = idx + 27 + nsegs + body_len
    return int(last_granule / 48000 * 1_000_000)


async def tts(text, out_path, dev_id, iid):
    ws_url = f"wss://sami.bytedance.com/internal/api/v2/ws?device_id={dev_id}&iid={iid}"
    headers = {"User-Agent": f"JianyingPro/5.9.0.11632 (Windows 10.0.19045; app_id:3704; device_id:{dev_id})"}
    ctx = ssl.create_default_context()
    async with websockets.connect(ws_url, additional_headers=headers, ssl=ctx, open_timeout=20) as ws:
        task_id = f"ai_gen_{os.urandom(4).hex()}"
        start_msg = {
            "app_id": APP_ID, "appkey": APP_KEY, "event": "StartTask",
            "namespace": "TTS", "task_id": task_id, "message_id": task_id + "_0",
            "payload": json.dumps({
                "text": text, "speaker": SPEAKER,
                "audio_config": {"format": "ogg_opus", "sample_rate": 24000, "bit_rate": 64000},
            }, ensure_ascii=False, separators=(",", ":")),
        }
        await ws.send(json.dumps(start_msg, ensure_ascii=False, separators=(",", ":")))
        await ws.send(json.dumps({"appkey": APP_KEY, "event": "FinishTask", "namespace": "TTS"}))
        audio = bytearray()
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=20)
            if isinstance(raw, str):
                resp = json.loads(raw)
                ev = resp.get("event")
                if ev == "TaskFailed":
                    raise RuntimeError(f"{resp.get('status_text')} ({resp.get('status_code')})")
                if ev == "TaskFinished":
                    break
            else:
                audio.extend(raw)
        if not audio:
            raise RuntimeError("no audio")
        open(out_path, "wb").write(bytes(audio))


async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    dev_id, iid = get_jy_local_config()
    print(f"speaker={SPEAKER} device_id={dev_id}")
    result = []
    for fname, text, sub_start, sub_dur in LINES:
        out = os.path.join(OUT_DIR, fname)
        for attempt in range(3):
            try:
                await tts(text, out, dev_id, iid)
                break
            except Exception as e:
                print(f"  retry {attempt+1} {fname}: {e}")
                await asyncio.sleep(1.5)
        else:
            raise SystemExit(f"FAILED: {fname}")
        dur = ogg_opus_duration_us(out)
        fit = "OK" if dur <= sub_dur else f"OVERFLOW +{(dur-sub_dur)/1e6:.2f}s (需变速 x{dur/sub_dur:.2f})"
        print(f"{fname}  语音 {dur/1e6:5.2f}s / 字幕窗口 {sub_dur/1e6:5.2f}s  {fit}")
        result.append({"file": fname, "text": text, "audio_us": dur,
                       "sub_start": sub_start, "sub_dur": sub_dur})
    meta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_meta.json")
    json.dump(result, open(meta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("meta ->", meta)

asyncio.run(main())
