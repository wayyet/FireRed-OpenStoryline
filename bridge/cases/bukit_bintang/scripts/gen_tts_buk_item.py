# -*- coding: utf-8 -*-
"""配音生成：吉隆坡武吉免登_纯视频
音色: zh_male_zhubo（主播腔·都市男声，历史全新）
"""
import asyncio, json, os, re, ssl, struct, sys
sys.stdout.reconfigure(encoding="utf-8")
import websockets

APP_KEY = "IZjhUeAYwP"
APP_ID = "3704"

# ===== 历史黑名单 =====
BANNED_SPEAKERS = {
    "zh_female_zhixing",   # 2026-07-03 大岭村
    "zh_male_chunhou",     # 2026-07-05 广州永华艺术馆
    "BV700_streaming",     # 2026-07-07 EXCHANGE TRX
    "BV701_streaming",     # 2026-07-07 柏威年广场 中文版
    "en_female_emotional", # 2026-07-11 柏威年广场 英文版
}
SPEAKER = "zh_male_zhubo"
assert SPEAKER not in BANNED_SPEAKERS, f"音色 {SPEAKER} 在历史黑名单中!"

DRAFT_DIR = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\吉隆坡武吉免登_纯视频"
OUT_DIR = os.path.join(DRAFT_DIR, "textReading")

# (文件名, 文本, 字幕起点us, 字幕窗口us)
LINES = [
    ("s01.ogg", "欢迎来星星之丘，武吉免登夜景太绝了", 0, 4_866_000),
    ("s02.ogg", "武吉免登商业街，棕榈树配橙光太美了", 4_866_000, 4_366_000),
    ("s03.ogg", "马来西亚吉隆坡武吉免登，飞轮海商场到了", 9_233_000, 4_366_000),
    ("s04.ogg", "蓝天下的摩天大楼，城市天际线绝了", 13_600_000, 4_366_000),
    ("s05.ogg", "仰望武吉免登标志塔，森林背景太特别了", 17_966_000, 4_866_000),
    ("s06.ogg", "换个角度俯视城景，伊顿大厦也在", 22_833_000, 4_900_000),
    ("s07.ogg", "武吉免登单轨穿过，十字路口夜景绝了", 27_733_000, 4_533_000),
    ("s08.ogg", "最后看一眼武吉免登，别错过这里啊", 32_266_000, 3_900_000),
]

def get_jy_config():
    defaults = ("1053764930506284", "2314914062247833")
    base = os.path.join(os.getenv("LOCALAPPDATA"), "JianyingPro", "User Data")
    dev_id, iid = defaults
    cfg_path = os.path.join(base, "TTNet", "tt_net_config.config")
    if os.path.exists(cfg_path):
        try:
            m = re.search(r"device_id\&#\*(\d+)", open(cfg_path, encoding="utf-8", errors="ignore").read())
            if m: dev_id = m.group(1)
        except: pass
    log_dir = os.path.join(base, "Log")
    if os.path.exists(log_dir):
        for fp in sorted([os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".log")],
                         key=os.path.getmtime, reverse=True)[:5]:
            try:
                m = re.search(r"iid=(\d+)", open(fp, encoding="utf-8", errors="ignore").read(1_000_000))
                if m: iid = m.group(1); break
            except: continue
    return dev_id, iid

def ogg_dur_us(path):
    data = open(path, "rb").read()
    last_gp = 0
    pos = 0
    while True:
        idx = data.find(b"OggS", pos)
        if idx < 0 or idx + 27 > len(data): break
        gp = struct.unpack_from("<q", data, idx + 6)[0]
        nsegs = data[idx + 26]
        body_len = sum(data[idx + 27: idx + 27 + nsegs])
        if gp > 0: last_gp = gp
        pos = idx + 27 + nsegs + body_len
    return int(last_gp / 48000 * 1_000_000)

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
    dev_id, iid = get_jy_config()
    print(f"speaker={SPEAKER} device_id={dev_id} iid={iid}")
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
        dur = ogg_dur_us(out)
        fit = "OK" if dur <= sub_dur else f"OVERFLOW +{(dur-sub_dur)/1e6:.2f}s"
        print(f"{fname}  语音 {dur/1e6:5.2f}s / 窗口 {sub_dur/1e6:5.2f}s  {fit}")
        result.append({"file": fname, "text": text, "audio_us": dur,
                       "sub_start": sub_start, "sub_dur": sub_dur})
    meta = os.path.join(OUT_DIR, "tts_meta.json")
    json.dump(result, open(meta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("meta ->", meta)

asyncio.run(main())
