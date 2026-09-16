# -*- coding: utf-8 -*-
"""音色探测：批量试一组 speaker 是否可用（剪映同款 SAMI 接口）。选音色前先跑。
无效音色报 TTSInvalidSpeaker (40402004)。OK 的会在脚本目录存一个 probe_<speaker>.ogg 试听。

依赖：系统 Python 3.13 + websockets。
用法：
  $env:PYTHONIOENCODING = 'utf-8'
  & "C:\\Program Files\\Python313\\python.exe" .\\probe_speakers.py
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

# 已实测可用（治愈系 vlog 首推 zh_female_zhixing）；2026-07-05 两批扩池后共 34 款。
# 扩池经验：
#   1) 火山引擎 voice_type 文档名命中率最高——zh_*（zhubo/rap/sichuan 系）+ BV 系列全靠抄文档名；
#      风格拼音瞎猜（wenrou/yujie/keai/xinwen/yueyu 等）几乎全灭。
#   2) BV 系列走 `BVxxx_streaming` 格式，命中率远高于 zh_* 风格词；下批可补 BV 更多编号试。
#   3) timeout 是网络抖动的误报（BV700/BV426 首轮 timeout、重试即 OK），failed 款务必重试一次再判死。
#   4) 报错分三类：IllegalSpeaker(40000022)=ID 不存在、TTSInvalidSpeaker(40402004)=音色无效——都是真死；
#      SynthesisFail(50000001)=服务端合成失败，重试仍复现则判当前授权不可合成（区别于前两者）。
CANDIDATES = [
    # ---- 哨兵（确认接口本身正常）----
    "zh_female_zhixing",
    # ==== zh_* 系列实测可用（14 款）====
    "zh_female_qingxin", "zh_female_tianmei", "zh_female_story",
    "zh_female_inspirational", "zh_female_xiaopengyou", "zh_male_chunhou",
    "zh_male_huoli", "zh_male_xionger_stream_gpu", "zh_male_inspirational",
    "zh_male_zhubo", "zh_female_zhubo", "zh_male_rap", "zh_female_sichuan",
    # ==== BV 系列实测可用（20 款；2026-07-05 第二批）====
    "BV700_streaming",   # 灿灿（多情感，抖音爆款女声）
    "BV701_streaming",   # 擎苍（浑厚古风男声/旁白）
    "BV406_streaming", "BV407_streaming",  # 超自然音色（梓梓/燃燃）
    "BV001_streaming", "BV002_streaming",  # 通用女声 / 通用男声
    "BV005_streaming", "BV007_streaming",  # 活泼女声 / 亲切女声
    "BV051_streaming",   # 奶气萌娃
    "BV056_streaming",   # 阳光青年
    "BV102_streaming",   # 儒雅青年
    "BV104_streaming",   # 甜美小源
    "BV119_streaming",   # 通用赘婿
    "BV064_streaming", "BV115_streaming", "BV123_streaming", "BV063_streaming",  # 通用/特色（试听 probe_*.ogg 为准）
    "BV213_streaming",   # 广东女声（粤语，贴广州/岭南主题）
    "BV426_streaming",   # 东北老铁（方言趣味）
    "BV419_streaming",   # 重庆小伙（方言趣味）
    # ---- 下批待补候选（自行补充新音色名到这里探测）----
    # 更多 BV 编号，如 "BV009_streaming", "BV113_streaming"(第一轮 SynthesisFail 可再探)…
]
# 已知无效（别再试）：
# [TTSInvalidSpeaker 40402004] *nvsheng/*nansheng 全拼后缀系、zh_female_wenrouxiaoya、zh_female_wenroushunv、
#   zh_female_roumeinvyou、zh_male_zhixing、zh_male_qingxin、zh_male_story、zh_female_huoli、zh_female_chunhou、
#   zh_male_wennuan、zh_female_kailangjiejie、zh_male_yangguang、zh_female_wenrou、zh_female_qinqie、
#   zh_female_yujie、zh_female_luoli、zh_male_shaonian、zh_female_keai、zh_female_gaoleng、
#   zh_male_guanggao、zh_male_jieshuo、zh_male_xinwen、zh_female_xinwen、zh_male_dongbeilaotie、
#   zh_female_yueyu、zh_male_yueyu、zh_male_guangtouqiang_stream_gpu、BV702_streaming
# [IllegalSpeaker 40000022 = ID 不存在] BV003_streaming、BV004_streaming、BV704_streaming
# [SynthesisFail 50000001 = 当前授权不可合成，两轮重试均复现] BV705_streaming、BV113_streaming、
#   BV120_streaming、BV421_streaming（湾湾小何）


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
                    "text": "走着走着，心就静了",
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
                out = os.path.join(out_dir, f"probe_{speaker}.ogg")
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
        # 经验③：timeout / SynthesisFail(50000001) 多是网络抖动或瞬时失败，重试一次再判死；
        # 真死码 IllegalSpeaker(40000022) / TTSInvalidSpeaker(40402004) 不必重试，省时间。
        if not ok and ("timeout" in msg or "50000001" in msg):
            await asyncio.sleep(1.5)
            ok, msg = await try_speaker(sp, dev_id, iid, out_dir)
        print(f"{'OK  ' if ok else 'FAIL'} {sp}: {msg}")

asyncio.run(main())
