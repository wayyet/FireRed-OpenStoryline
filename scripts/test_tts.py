# -*- coding: utf-8 -*-
"""
OpenStoryline TTS（语音生成）连通性测试
完全复刻 src/open_storyline/nodes/core_nodes/generate_voiceover.py 的 minimax 逻辑：
  base_url = secrets["base_url"] or "https://api.minimax.chat"
  api_url  = base_url.rstrip("/") + "/v1/t2a_v2"   (当不以 /v1/t2a_v2 结尾)
  POST api_url  body={model, text, voice_setting, audio_setting, ...}
仅用标准库 (urllib)，不依赖 venv。
结果写入 test_tts_result.txt 并打印；成功则把音频落盘到 outputs/_tts_probe.wav。
"""
import json, sys, io, time, binascii, os
import urllib.request, urllib.error

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = __file__.rsplit("\\", 1)[0] if "\\" in __file__ else "."
OUT_LINES = []

def log(s=""):
    print(s, flush=True)
    OUT_LINES.append(s)

# ---------- 读取 config.toml 的 minimax TTS 配置 ----------
def load_minimax_cfg():
    cfg_path = HERE + "\\config.toml"
    try:
        import tomllib
        with open(cfg_path, "rb") as f:
            data = tomllib.load(f)
        return (((data.get("generate_voiceover") or {}).get("providers") or {}).get("minimax") or {})
    except Exception:
        # 兜底：手工抓 [generate_voiceover.providers.minimax]
        sect, data = None, {}
        with open(cfg_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.split("#", 1)[0].strip()
                if not line:
                    continue
                if line.startswith("[") and line.endswith("]"):
                    sect = line[1:-1]; data.setdefault(sect, {}); continue
                if "=" in line and sect:
                    k, v = line.split("=", 1)
                    data[sect][k.strip()] = v.strip().strip('"').strip("'")
        return data.get("generate_voiceover.providers.minimax", {})

def build_api_url(base_url):
    """复刻 generate_voiceover.py 第 549-550 行的拼接逻辑。"""
    base_url = base_url or "https://api.minimax.chat"
    if not base_url.endswith("/v1/t2a_v2"):
        return base_url.rstrip("/") + "/v1/t2a_v2"
    return base_url

def short_key(k):
    return (k[:10] + "..." + k[-4:]) if k and len(k) > 18 else (k or "<空>")

def call_tts(api_url, api_key, text, voice_id="female-shaonv-jingpin", model="speech-02-hd"):
    body = {
        "model": model,
        "text": text,
        "stream": False,
        "language_boost": "auto",
        "output_format": "hex",
        "voice_setting": {"voice_id": voice_id, "speed": 1.0, "vol": 1.0, "pitch": 0},
        "audio_setting": {"sample_rate": 24000, "bitrate": 128000, "format": "wav"},
    }
    req = urllib.request.Request(
        api_url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = r.read().decode("utf-8", "replace")
            dt = time.time() - t0
            try:
                rj = json.loads(txt)
            except Exception:
                return ("BAD_JSON", r.status, txt[:400], dt, None)
            base_resp = (rj or {}).get("base_resp") or {}
            sc = base_resp.get("status_code")
            if sc not in (0, None):
                return ("API_ERR_%s" % sc, r.status, json.dumps(base_resp, ensure_ascii=False)[:400], dt, None)
            audio = ((rj or {}).get("data") or {}).get("audio")
            if not audio:
                return ("NO_AUDIO", r.status, txt[:400], dt, None)
            return ("OK", r.status, "audio len(hex)=%d" % len(audio), dt, audio)
    except urllib.error.HTTPError as e:
        dt = time.time() - t0
        try:
            err = e.read().decode("utf-8", "replace")[:500]
        except Exception:
            err = ""
        return ("HTTP_%d" % e.code, e.code, err, dt, None)
    except urllib.error.URLError as e:
        return ("CONN_FAIL", 0, str(e.reason), time.time() - t0, None)
    except Exception as e:
        return ("ERROR", 0, repr(e)[:400], time.time() - t0, None)

def save_audio(hexstr, name):
    try:
        out_dir = HERE + "\\outputs"
        os.makedirs(out_dir, exist_ok=True)
        p = out_dir + "\\" + name
        with open(p, "wb") as f:
            f.write(binascii.unhexlify(hexstr))
        return p
    except Exception as e:
        return "<落盘失败: %r>" % e

def run():
    cfg = load_minimax_cfg()
    base_url = (cfg.get("base_url") or "").strip()
    api_key = (cfg.get("api_key") or "").strip()
    text = "你好，这是一段语音生成的测试。"

    log("=" * 64)
    log(" OpenStoryline TTS（语音生成）连通性测试 — minimax")
    log("=" * 64)
    log("[配置读取] generate_voiceover.providers.minimax")
    log("  base_url(原样) = %s" % (base_url or "<空>"))
    log("  api_key        = %s" % short_key(api_key))
    log("  测试文本       = %s" % text)
    log("")

    if not api_key:
        log("  ❌ 未配置 minimax api_key，无法测试。")
        flush(); return

    # ---- 1) 按 config 现状测（复刻代码拼接，base_url 不改） ----
    url_asis = build_api_url(base_url)
    log("-" * 64)
    log("[1] 按 config.toml 现状测（代码实际会请求的地址）")
    log("    -> POST %s" % url_asis)
    st, code, info, dt, audio = call_tts(url_asis, api_key, text)
    log("    结果: %s (HTTP %s, %.1fs)" % (st, code, dt))
    log("    详情: %s" % info)
    if st == "OK":
        p = save_audio(audio, "_tts_probe_asis.wav")
        log("    ✅ 语音生成成功，音频已保存: %s" % p)
        log("")
        log("=" * 64)
        log(" 总结：TTS ✅ 可用（现状配置即可）")
        log("=" * 64)
        flush(); return
    log("    ⚠️ 现状失败。")

    # ---- 2) 诊断：尝试“修正后地址”，但不改动 config ----
    log("")
    log("  [自动诊断] 现状失败，尝试常见修正地址（仅探测，不改 config）……")
    candidates = []
    # 去掉结尾 /v1 的修正版
    if base_url.endswith("/v1"):
        candidates.append(base_url[:-3])  # https://api.minimaxi.com
    candidates += ["https://api.minimaxi.com", "https://api.minimax.chat", "https://api.minimax.io"]
    seen, found = set(), None
    for b in candidates:
        u = build_api_url(b)
        if u in seen:
            continue
        seen.add(u)
        st2, code2, info2, dt2, audio2 = call_tts(u, api_key, text)
        tag = "✓" if st2 == "OK" else "✗"
        log("    %s POST %s  -> %s (HTTP %s) %s" % (tag, u, st2, code2, info2[:120]))
        if st2 == "OK" and not found:
            found = (b, u, audio2)
    log("")
    if found:
        p = save_audio(found[2], "_tts_probe_fixed.wav")
        log("  >>> 建议把 base_url 改为：%s" % found[0])
        log("  >>> 该地址实际请求 %s 可成功生成语音，音频已保存: %s" % (found[1], p))
        log("")
        log("=" * 64)
        log(" 总结：TTS ❌ 现状不可用，但改 base_url 后 ✅ 可用")
        log("=" * 64)
    else:
        log("  >>> 所有候选地址均失败。最可能：key 无 TTS 权限/未充值，或该 key 不支持 t2a_v2，或需要 GroupId。")
        log("")
        log("=" * 64)
        log(" 总结：TTS ❌ 不可用")
        log("=" * 64)
    flush()

def flush():
    with open(HERE + "\\test_tts_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(OUT_LINES))

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        import traceback
        msg = "TTS 测试脚本异常:\n" + traceback.format_exc()
        print(msg)
        OUT_LINES.append(msg)
        try:
            flush()
        except Exception:
            pass
