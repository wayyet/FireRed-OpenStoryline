# -*- coding: utf-8 -*-
"""
OpenStoryline API 连通性测试
完全模拟 src/open_storyline/agent.py 的 validate_api_key:
  POST {base_url}/chat/completions  body={"model":..,"messages":[{"role":"user","content":"hi"}],"max_tokens":1}
仅用标准库 (urllib)，不依赖 venv。
结果同时写入 test_result.txt 并打印到控制台。
"""
import json, sys, io, struct, zlib, base64, time
import urllib.request, urllib.error

# 让 Windows 控制台用 UTF-8
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = __file__.rsplit("\\", 1)[0] if "\\" in __file__ else "."
OUT_LINES = []

def log(s=""):
    print(s, flush=True)
    OUT_LINES.append(s)

# ---------- 读取 config.toml ----------
def load_config():
    cfg_path = HERE + "\\config.toml"
    try:
        import tomllib
        with open(cfg_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        # 极简手工解析兜底
        data, section = {}, None
        with open(cfg_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.split("#", 1)[0].strip()
                if not line:
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1]; data.setdefault(section, {}); continue
                if "=" in line and section:
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    data[section][k.strip()] = v
        return data

# ---------- 生成一张测试用 PNG (纯库) ----------
def make_png(w=32, h=32, rgb=(220, 60, 60)):
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(rgb) * w
    raw = row * h
    idat = zlib.compress(raw, 9)
    png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode()

# ---------- 发请求 (模拟 OpenStoryline) ----------
def call(base_url, api_key, model, messages, timeout=30.0, max_tokens=16):
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read().decode("utf-8", "replace")
            dt = time.time() - t0
            try:
                data = json.loads(txt)
            except Exception:
                return ("BAD_JSON", r.status, txt[:400], dt)
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                content = ""
                try:
                    content = (choices[0].get("message", {}) or {}).get("content", "") or ""
                except Exception:
                    pass
                return ("OK", r.status, (content or "<空content但有choices>")[:200], dt)
            return ("NO_CHOICES", r.status, txt[:400], dt)
    except urllib.error.HTTPError as e:
        dt = time.time() - t0
        try:
            err = e.read().decode("utf-8", "replace")[:500]
        except Exception:
            err = ""
        return ("HTTP_%d" % e.code, e.code, err, dt)
    except urllib.error.URLError as e:
        return ("CONN_FAIL", 0, str(e.reason), time.time() - t0)
    except Exception as e:
        return ("ERROR", 0, repr(e)[:400], time.time() - t0)

def short_key(k):
    return (k[:10] + "..." + k[-4:]) if k and len(k) > 18 else (k or "<空>")

def run():
    cfg = load_config()
    llm = cfg.get("llm", {})
    vlm = cfg.get("vlm", {})

    log("=" * 64)
    log(" OpenStoryline 大模型 API 连通性测试")
    log("=" * 64)
    log("[配置读取]")
    log("  LLM model    = %r" % llm.get("model"))
    log("  LLM base_url = %s" % llm.get("base_url"))
    log("  LLM api_key  = %s" % short_key(llm.get("api_key", "")))
    log("  VLM model    = %r" % vlm.get("model"))
    log("  VLM base_url = %s" % vlm.get("base_url"))
    log("  VLM api_key  = %s" % short_key(vlm.get("api_key", "")))
    log("")

    # ---- 1) LLM：完全按当前配置测 ----
    log("-" * 64)
    log("[1] 测试 LLM（按 config.toml 原样）")
    st, code, info, dt = call(llm.get("base_url", ""), llm.get("api_key", ""),
                              llm.get("model", ""), [{"role": "user", "content": "用一句话回答：你好"}],
                              timeout=float(llm.get("timeout", 30) or 30), max_tokens=32)
    log("  结果: %s (HTTP %s, %.1fs)" % (st, code, dt))
    log("  返回: %s" % info)
    llm_ok = st == "OK"

    # ---- 2) LLM 失败时，自动尝试修正变体 ----
    if not llm_ok:
        log("")
        log("  [自动诊断] 原配置失败，尝试常见修正组合……")
        cand_models = []
        m = (llm.get("model") or "").strip()
        # 规范化：minimax M2.7-highspeed -> MiniMax-M2.7-highspeed
        norm = m.replace(" ", "-")
        if norm.lower().startswith("minimax"):
            norm = "MiniMax" + norm[len("minimax"):]
        for cm in [norm, "MiniMax-M2.7-highspeed", "MiniMax-M2.7", "MiniMax-M2.5", "MiniMax-M3", "MiniMax-M2"]:
            if cm and cm not in cand_models and cm != m:
                cand_models.append(cm)
        cand_urls = []
        for u in [llm.get("base_url", ""), "https://api.minimax.io/v1", "https://api.minimaxi.com/v1"]:
            if u and u not in cand_urls:
                cand_urls.append(u)
        found = None
        for u in cand_urls:
            for cm in cand_models:
                st2, code2, info2, dt2 = call(u, llm.get("api_key", ""), cm,
                                              [{"role": "user", "content": "hi"}], timeout=20, max_tokens=8)
                tag = "✓" if st2 == "OK" else "✗"
                log("    %s base=%s  model=%s  -> %s (HTTP %s)" % (tag, u, cm, st2, code2))
                if st2 == "OK" and not found:
                    found = (u, cm)
                    log("       返回: %s" % info2)
            # 401/403 说明 key 本身的问题，换 url 没用
        if found:
            log("")
            log("  >>> 建议修正：base_url=%s  model=%s" % (found[0], found[1]))
        else:
            log("")
            log("  >>> 所有变体均失败。最可能是 API key 无效/未充值，或网络/域名被墙。")

    # ---- 3) VLM：带图片测视觉理解 ----
    log("")
    log("-" * 64)
    log("[2] 测试 VLM（视觉模型，带一张测试图片）")
    img = make_png()
    vlm_msg = [{"role": "user", "content": [
        {"type": "text", "text": "这张图主要是什么颜色？一个词回答。"},
        {"type": "image_url", "image_url": {"url": img}},
    ]}]
    st, code, info, dt = call(vlm.get("base_url", ""), vlm.get("api_key", ""),
                              vlm.get("model", ""), vlm_msg,
                              timeout=float(vlm.get("timeout", 30) or 30), max_tokens=32)
    log("  结果: %s (HTTP %s, %.1fs)" % (st, code, dt))
    log("  返回: %s" % info)
    vlm_ok = st == "OK"

    if not vlm_ok:
        log("")
        log("  [自动诊断] VLM 原配置失败，尝试多模态候选模型……")
        found_v = None
        for u in [vlm.get("base_url", ""), "https://api.minimax.io/v1"]:
            if not u:
                continue
            for cm in ["MiniMax-M3", "MiniMax-VL-01"]:
                st2, code2, info2, dt2 = call(u, vlm.get("api_key", ""), cm, vlm_msg, timeout=25, max_tokens=16)
                tag = "✓" if st2 == "OK" else "✗"
                log("    %s base=%s  model=%s  -> %s (HTTP %s)" % (tag, u, cm, st2, code2))
                if st2 == "OK" and not found_v:
                    found_v = (u, cm); log("       返回: %s" % info2)
        if found_v:
            log("")
            log("  >>> VLM 建议修正：base_url=%s  model=%s" % (found_v[0], found_v[1]))

    # ---- 总结 ----
    log("")
    log("=" * 64)
    log(" 总结： LLM %s    VLM %s" % ("✅可用" if llm_ok else "❌不可用",
                                      "✅可用" if vlm_ok else "❌不可用"))
    log("=" * 64)

    with open(HERE + "\\test_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(OUT_LINES))

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        import traceback
        msg = "测试脚本异常:\n" + traceback.format_exc()
        print(msg)
        try:
            with open(HERE + "\\test_result.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(OUT_LINES) + "\n" + msg)
        except Exception:
            pass
