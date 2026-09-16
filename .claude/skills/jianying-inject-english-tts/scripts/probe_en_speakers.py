# -*- coding: utf-8 -*-
"""英文音色探测：批量试候选英文 speaker 是否可用（剪映同款 SAMI 接口）。
官方文档页是 JS 渲染抓不到英文 voice_type 表，唯一路径就是这里批量实测。
OK 的候选会在脚本目录存 probe_en_<speaker>.ogg —— 再用 ffmpeg 转 mp3 给用户试听拍板（AI 自己听不了）。

依赖：系统 Python 3.13 + websockets。
用法：
  $env:PYTHONIOENCODING = 'utf-8'
  & "C:\\Program Files\\Python313\\python.exe" .\\probe_en_speakers.py
"""
import asyncio
import json
import os
import re
import ssl
import sys

sys.stdout.reconfigure(encoding="utf-8")

import websockets  # noqa: E402

APP_KEY = "IZjhUeAYwP"
APP_ID = "3704"

# 2026-07-11 实测结论（吉隆坡柏威年广场英文字幕版那轮）：
#   OK  : en_female_emotional（唯一命中的 en_*，女声情感风格，英文配音首推）
#   OK  : BV138_streaming / BV503_streaming / BV504_streaming（有音频但语言/性别不明，用前必须试听确认是英语）
#   真死: en_female_story / en_male_story / en_female_common / en_male_common / en_male_emotional
#         —— TTSInvalidSpeaker (40402004)，别再试
#   授权不可合成: BV027_streaming / BV502_streaming / BV505_streaming —— SynthesisFail (50000001) 两轮均复现
# 扩池思路：① en_female_xxx / en_male_xxx 命名模式外推（命中率低但直白）；② 补更多 BV 编号（探到也要试听验语种）。
CANDIDATES = [
    # ---- 哨兵（确认接口本身正常）----
    "en_female_emotional",
    # ---- 2026-07-11 第二批（已测出结论，注释存档）：en_* 外推全部真死(40402004)：
    #      en_female_narrator / en_male_narrator / en_female_sweet / en_female_warm /
    #      en_female_lively / en_female_gentle / en_male_gentle / en_male_deep /
    #      en_female_energetic / en_female_cute
    #      BV 扫段命中：BV137 / BV139 / BV506 / BV511（均 _streaming，语种待试听）
    #      BV 扫段失败：BV140/BV507/BV508/BV510/BV512/BV516/BV518/BV520/BV521/
    #      BV522/BV524/BV525(50000001 授权不可合成)、BV509(40402004 真死)
    # ---- 2026-07-12 第三批（已测出结论，注释存档）：全军覆没 ----
    #      授权不可合成(50000001)：BV421 / BV040 / BV530 / BV531（多语种聚集区编号）
    #      真死(40402004)：BV702、以及全部 V2 变体外推
    #      BV503_V2 / BV504_V2 / BV138_V2 / BV506_V2 / BV511_V2
    # 结论：当前授权下英文池边界已探明 = en_female_emotional + BV137/138/139/503/504/506/511 共 8 款。
    # 网络佐证(xwean.com/1976.html)：BV503=活力女声Ariana·美式英语、BV504=活力男声Jackson·美式英语。
]

TEST_TEXT = "Every corner here is a great photo spot, don't miss it!"


def get_jy_local_config():
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


async def try_speaker(speaker, dev_id, iid, out_dir):
    ws_url = f"wss://sami.bytedance.com/internal/api/v2/ws?device_id={dev_id}&iid={iid}"
    headers = {"User-Agent": f"JianyingPro/5.9.0.11632 (Windows 10.0.19045; app_id:3704; device_id:{dev_id})"}
    ctx = ssl.create_default_context()
    try:
        async with websockets.connect(ws_url, additional_headers=headers, ssl=ctx, open_timeout=20) as ws:
            task_id = f"ai_gen_{os.urandom(4).hex()}"
            start_msg = {
                "app_id": APP_ID, "appkey": APP_KEY, "event": "StartTask",
                "namespace": "TTS", "task_id": task_id, "message_id": task_id + "_0",
                "payload": json.dumps({
                    "text": TEST_TEXT,
                    "speaker": speaker,
                    "audio_config": {"format": "ogg_opus", "sample_rate": 24000, "bit_rate": 64000},
                }, ensure_ascii=False, separators=(",", ":")),
            }
            await ws.send(json.dumps(start_msg, ensure_ascii=False, separators=(",", ":")))
            await ws.send(json.dumps({"appkey": APP_KEY, "event": "FinishTask", "namespace": "TTS"}))
            audio = bytearray()
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=15)
                except asyncio.TimeoutError:
                    return False, "timeout"
                if isinstance(raw, str):
                    resp = json.loads(raw)
                    ev = resp.get("event")
                    if ev == "TaskFailed":
                        return False, f"{resp.get('status_text')} ({resp.get('status_code')})"
                    if ev == "TaskFinished":
                        break
                else:
                    audio.extend(raw)
            if audio:
                out = os.path.join(out_dir, f"probe_en_{speaker}.ogg")
                open(out, "wb").write(bytes(audio))
                return True, f"{len(audio)} bytes"
            return False, "no audio"
    except Exception as e:
        return False, repr(e)


async def main():
    dev_id, iid = get_jy_local_config()
    print(f"device_id={dev_id} iid={iid}")
    out_dir = os.path.dirname(os.path.abspath(__file__))
    for sp in CANDIDATES:
        ok, msg = await try_speaker(sp, dev_id, iid, out_dir)
        # timeout / SynthesisFail(50000001) 重试一次再判死；40402004 / 40000022 真死不必重试
        if not ok and ("timeout" in msg or "50000001" in msg):
            await asyncio.sleep(1.5)
            ok, msg = await try_speaker(sp, dev_id, iid, out_dir)
        print(f"{'OK  ' if ok else 'FAIL'} {sp}: {msg}")

asyncio.run(main())
