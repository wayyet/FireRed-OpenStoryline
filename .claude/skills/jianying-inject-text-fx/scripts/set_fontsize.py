"""把剪映 5.9 草稿字幕轨的全部字幕字号统一为 TARGET_SIZE.

字号是双字段, 两处都改才与剪映客户端手改行为一致:
  1. text material 顶层 font_size (float)
  2. content 内嵌 JSON 的 styles[*].size (int)

要点(2026-07-05 广州永华艺术馆 实测):
  - 用户可能在两轮脚本之间又在客户端手改过个别条 —— 本脚本每次运行都重读草稿现值
    逐条 diff, 已达标的跳过, 不拿上一轮结果当现状.
  - 双 JSON 等价写入 + pre_fontsize_<时间戳>.bak 备份 + 写入后逐条复核.
  - 写入前照例确认剪映已关闭(否则内存旧版本会覆盖).
  - 已注入的动画/花字不受影响.
  - 16:9 横屏经验: 字号 8 偏小, 建议 10 起步.

用法(用系统 Python 3.13, 改顶部 DRAFT / TARGET_SIZE):
  & "C:\\Program Files\\Python313\\python.exe" .\\set_fontsize.py            # dry-run
  & "C:\\Program Files\\Python313\\python.exe" .\\set_fontsize.py --apply    # 备份后写入双 JSON
"""
import sys, json, os, shutil, datetime
sys.stdout.reconfigure(encoding='utf-8')

# ============ 改这里 ============
DRAFT = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>"
TARGET_SIZE = 10
# ================================

APPLY = "--apply" in sys.argv
content_path = os.path.join(DRAFT, "draft_content.json")
info_path = os.path.join(DRAFT, "draft_info.json")

def fix(data):
    text_tracks = [t for t in data["tracks"] if t.get("type") == "text"]
    assert len(text_tracks) == 1, f"期望 1 条字幕轨, 实际 {len(text_tracks)}"
    segs = sorted(text_tracks[0]["segments"], key=lambda s: s["target_timerange"]["start"])
    texts_by_id = {t["id"]: t for t in data["materials"]["texts"]}
    report, changed = [], 0
    for i, s in enumerate(segs):
        mat = texts_by_id[s["material_id"]]
        c = json.loads(mat["content"])
        old_sizes = [st.get("size") for st in c.get("styles", [])]
        old_fs = mat.get("font_size")
        # 重读现值逐条 diff: 用户可能在客户端手改过, 已达标就跳过
        if old_fs == float(TARGET_SIZE) and all(x == TARGET_SIZE for x in old_sizes):
            report.append("  [%02d] %-12r 已是 %s, 跳过" % (i, c.get("text", "?")[:6], TARGET_SIZE))
            continue
        for st in c.get("styles", []):
            st["size"] = TARGET_SIZE
        mat["content"] = json.dumps(c, ensure_ascii=False)
        mat["font_size"] = float(TARGET_SIZE)
        changed += 1
        report.append("  [%02d] %-12r styles.size %s->%s, font_size %s->%s" % (
            i, c.get("text", "?")[:6], old_sizes, TARGET_SIZE, old_fs, float(TARGET_SIZE)))
    return report, changed, len(segs)

data = json.load(open(content_path, encoding="utf-8"))
orig_duration = data["duration"]
report, changed, total = fix(data)
print("\n".join(report))
print("\n共修改 %d/%d 条 (目标字号=%s), 总时长不变: %s" % (changed, total, TARGET_SIZE, data["duration"] == orig_duration))
json.dumps(data)  # 可序列化

if not APPLY:
    print("\n[dry-run] 未写入。确认无误后加 --apply 执行(执行前先确认剪映已关闭)。")
    sys.exit(0)

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
for p in (content_path, info_path):
    bak = p + f".pre_fontsize_{ts}.bak"
    shutil.copy2(p, bak)
    print("备份:", bak)

with open(content_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
# draft_info 与 content 等价写入(同一草稿), 防剪映回退读旧份
with open(info_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
print("已写入双 JSON")

# 写入后逐条复核两个字段
for p in (content_path, info_path):
    d2 = json.load(open(p, encoding="utf-8"))
    assert d2["duration"] == orig_duration, "总时长被改动!"
    tt = next(t for t in d2["tracks"] if t.get("type") == "text")
    tb = {t["id"]: t for t in d2["materials"]["texts"]}
    for s in tt["segments"]:
        m = tb[s["material_id"]]
        assert m["font_size"] == float(TARGET_SIZE)
        for st in json.loads(m["content"]).get("styles", []):
            assert st.get("size") == TARGET_SIZE
print("写入后复核通过: 全部 %d 条字幕字号均为 %s" % (total, TARGET_SIZE))
