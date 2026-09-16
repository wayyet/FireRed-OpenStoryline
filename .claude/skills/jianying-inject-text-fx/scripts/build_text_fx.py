"""给剪映 5.9 草稿的字幕批量注入 VIP 文字动画(入场/循环/出场) + 批量应用用户手选的 VIP 花字.

不经 pyJianYingDraft 运行时(本机 venv 已坏), 直接改 draft_content.json / draft_info.json 双 JSON.

用法(在本 scripts 目录下, 用系统 Python 3.13):
  & "C:\\Program Files\\Python313\\python.exe" .\\build_text_fx.py            # dry-run: 只校验和预览, 不写入
  & "C:\\Program Files\\Python313\\python.exe" .\\build_text_fx.py --apply    # 备份后写入双 JSON

使用前改三处:
  1. DRAFT       —— 目标草稿根目录
  2. BANNED / BANNED_FLOWER_RIDS —— 历史已用黑名单(硬规则: 每轮动画/花字不得与之前视频重复):
       从记忆 kuaishou-fx-used-history 取"全部历史轮次"的动画标题并集 / 花字 resource_id 并集填入,
       脚本会 assert 硬校验, 撞名直接中止; 注入成功后记得把本轮清单回写进该记忆.
  3. ANIM_PLAN   —— 按字幕轨 segment 的时间顺序, 每条一个字典:
       {"label": "备注", "anims": [
           {"type": "in|loop|out", "title": "动画名",
            "resource_id": "...", "effect_id": "...", "duration_s": 0.8},
           ...   # 一条字幕可同时有 in / loop / out
       ]}
     resource_id / effect_id / duration_s 从 pyJianYingDraft metadata 的
     text_intro.py / text_loop.py / text_outro.py 里取 (只挑 is_vip 的).
     段数必须与字幕轨 segment 数相等.

花字: 无需在这里写 id —— 让用户先在剪映客户端给任意一条字幕挑好 VIP 花字并保存关闭,
      脚本会自动从草稿提取该样本 (materials.effects 里 type==text_effect), 克隆到其余每条字幕;
      草稿里没有样本时, 本次只注入动画, 花字自动跳过.
"""
import sys, json, uuid, os, shutil, copy, datetime
sys.stdout.reconfigure(encoding='utf-8')

# ============ 改这里 ============
DRAFT = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\大岭村_治愈系Vlog"

# 历史已用动画标题黑名单(全部历史轮次并集, 出处: 记忆 kuaishou-fx-used-history)
# 例: {"星光闪闪 II", "消散", "模糊发光", "激光雕刻", "强调三遍", ...}
BANNED = set()

# 历史已用花字 resource_id 黑名单(探测到的样本撞上则中止, 请用户在客户端重新挑一款)
# 例: {"7160597532043644174"}  # 潮酷白色发光立体(2026-07-05 永华已用)
BANNED_FLOWER_RIDS = set()

ANIM_PLAN = [
    # 示例(按字幕段顺序, 段数必须 == 字幕轨 segment 数):
    # {"label": "第1条", "anims": [
    #     {"type": "in",   "title": "打字机 II", "resource_id": "xxx", "effect_id": "xxx", "duration_s": 0.8},
    #     {"type": "out",  "title": "渐隐",      "resource_id": "yyy", "effect_id": "yyy", "duration_s": 0.5},
    # ]},
]
# ================================

APPLY = "--apply" in sys.argv
content_path = os.path.join(DRAFT, "draft_content.json")
info_path = os.path.join(DRAFT, "draft_info.json")
data = json.load(open(content_path, encoding="utf-8"))

# ---------- 定位字幕轨 ----------
text_tracks = [t for t in data["tracks"] if t.get("type") == "text"]
assert len(text_tracks) == 1, f"期望 1 条字幕轨, 实际 {len(text_tracks)}"
segs = sorted(text_tracks[0]["segments"], key=lambda s: s["target_timerange"]["start"])
assert len(segs) == len(ANIM_PLAN), f"字幕段数 {len(segs)} != 方案条数 {len(ANIM_PLAN)} (请补全 ANIM_PLAN)"

texts_by_id = {t["id"]: t for t in data["materials"]["texts"]}
orig_duration = data["duration"]

# ---------- 历史零复用黑名单硬校验(用户硬规则: 不得与之前视频重复) ----------
for entry in ANIM_PLAN:
    for a in entry["anims"]:
        assert a["title"] not in BANNED, f"动画 {a['title']} 之前的视频已用过, 禁止复用! 请换新款"

# ---------- 防重复注入 ----------
existing_anims = data["materials"].get("material_animations", [])
assert not existing_anims, (
    f"草稿已存在 {len(existing_anims)} 条 material_animations —— 疑似已注入过。"
    "请先向用户确认: 是补注入还是剔除重做(剔除思路参考 jianying-inject-fx 的 strip 模式)")

# ---------- 找用户手动加的花字样本 ----------
mats = data["materials"]
effects_list = mats.setdefault("effects", [])
flower_samples = [e for e in effects_list if isinstance(e, dict) and e.get("type") == "text_effect"]
flower_tpl = None
flower_seg_id = None
if flower_samples:
    sample_ids = {e["id"] for e in flower_samples}
    for s in segs:
        hit = [r for r in s.get("extra_material_refs", []) if r in sample_ids]
        if hit:
            flower_tpl = next(e for e in flower_samples if e["id"] == hit[0])
            flower_seg_id = s["id"]
            break
    print(f"[花字] 发现样本: name={flower_tpl.get('name','?') if flower_tpl else '?'} "
          f"resource_id={flower_tpl.get('resource_id') if flower_tpl else '?'} "
          f"(挂在 segment {flower_seg_id[:8] if flower_seg_id else '?'})")
    # 花字同样零复用: 样本撞历史款则中止, 请用户重新挑
    if flower_tpl and str(flower_tpl.get("resource_id")) in BANNED_FLOWER_RIDS:
        raise SystemExit(f"[花字] 样本 resource_id={flower_tpl.get('resource_id')} 之前的视频已用过, "
                         "禁止复用! 请让用户在剪映客户端重新挑一款新花字后再跑")
else:
    print("[花字] 草稿中未发现 text_effect 样本 —— 本次只注入动画, 花字跳过")

# 花字样本所在 text material 的 styles[0] (含 effectStyle / 配色), 作为其余字幕的样式模板
style_tpl = None
diff_keys = {}
if flower_tpl and flower_seg_id:
    sample_seg = next(s for s in segs if s["id"] == flower_seg_id)
    sample_mat = texts_by_id[sample_seg["material_id"]]
    c = json.loads(sample_mat["content"])
    if c.get("styles") and "effectStyle" in c["styles"][0]:
        style_tpl = copy.deepcopy(c["styles"][0])
        print(f"[花字] 样式模板 effectStyle: {json.dumps(style_tpl.get('effectStyle'), ensure_ascii=False)}")
    else:
        print("[花字][警告] 样本字幕 content 里没有 effectStyle, 只复制素材引用")
    # 顶层字段 diff(供参考/同步): 与另一条未改字幕比较
    other_mat = next(texts_by_id[s["material_id"]] for s in segs if s["id"] != flower_seg_id)
    for k in sample_mat:
        if k in ("id", "content", "words", "recognize_task_id"):
            continue
        if sample_mat.get(k) != other_mat.get(k):
            diff_keys[k] = sample_mat[k]
    print("[花字] 样本与普通字幕的顶层字段差异(将同步):", json.dumps(diff_keys, ensure_ascii=False)[:400])

# ---------- 注入函数(对一份 JSON 数据操作) ----------
def inject(data, shared_uuids):
    """shared_uuids: 两份 JSON 共用同一套新 id"""
    mats = data["materials"]
    anims_list = mats.setdefault("material_animations", [])
    effects_list = mats.setdefault("effects", [])
    tts = [t for t in data["tracks"] if t.get("type") == "text"]
    assert len(tts) == 1
    ssegs = sorted(tts[0]["segments"], key=lambda s: s["target_timerange"]["start"])
    assert len(ssegs) == len(ANIM_PLAN)
    t_by_id = {t["id"]: t for t in mats["texts"]}

    report = []
    for i, (seg, entry) in enumerate(zip(ssegs, ANIM_PLAN)):
        seg_dur = seg["target_timerange"]["duration"]
        # --- 动画 ---
        anim_objs = []
        # 先入/出场后循环, 与 pyJianYingDraft 约束一致
        ordered = sorted(entry["anims"], key=lambda a: 0 if a["type"] in ("in", "out") else 1)
        outro_dur = 0
        for a in ordered:
            dur = min(int(round(a["duration_s"] * 1e6)), seg_dur)
            if a["type"] == "in":
                start = 0
            elif a["type"] == "out":
                start = seg_dur - dur
                outro_dur = dur
            else:  # loop: 填满除出场外的部分
                start = 0
                dur = seg_dur - outro_dur
            anim_objs.append({
                "anim_adjust_params": None,
                "platform": "all",
                "panel": "",
                "material_type": "sticker",
                "name": a["title"],
                "id": a["effect_id"],
                "type": a["type"],
                "resource_id": a["resource_id"],
                "start": start,
                "duration": dur,
            })
        desc = ""
        if anim_objs:
            anim_id = shared_uuids.setdefault(f"anim{i}", uuid.uuid4().hex)
            anims_list.append({
                "id": anim_id,
                "type": "sticker_animation",
                "multi_language_current": "none",
                "animations": anim_objs,
            })
            seg.setdefault("extra_material_refs", []).append(anim_id)
            desc = " + ".join(f"{o['type']}[{o['name']}]({o['start']/1e6:.2f}s~{(o['start']+o['duration'])/1e6:.2f}s)" for o in anim_objs)
        else:
            desc = "(无动画)"

        # --- 花字 ---
        fdesc = ""
        if flower_tpl:
            already = any(isinstance(e, dict) and e.get("type") == "text_effect" and e["id"] in seg.get("extra_material_refs", [])
                          for e in effects_list)
            if already:
                fdesc = " | 花字: 已有(样本), 跳过"
            else:
                fid = shared_uuids.setdefault(f"flower{i}", uuid.uuid4().hex)
                fmat = copy.deepcopy(flower_tpl)
                fmat["id"] = fid
                effects_list.append(fmat)
                seg.setdefault("extra_material_refs", []).append(fid)
                # content.styles 同步为样本样式(替换 range)
                mat = t_by_id[seg["material_id"]]
                c = json.loads(mat["content"])
                if style_tpl is not None:
                    new_style = copy.deepcopy(style_tpl)
                    new_style["range"] = [0, len(c.get("text", ""))]
                    c["styles"] = [new_style]
                    mat["content"] = json.dumps(c, ensure_ascii=False)
                for k, v in diff_keys.items():
                    mat[k] = copy.deepcopy(v)
                fdesc = f" | 花字: {flower_tpl.get('resource_id')}"
        report.append(f"  {entry['label']} ({seg['target_timerange']['start']/1e6:.1f}s+{seg_dur/1e6:.1f}s): {desc}{fdesc}")
    return report

shared = {}
report = inject(data, shared)
print()
print("=== 注入预览 (draft_content.json) ===")
for line in report:
    print(line)

# ---------- 校验 ----------
assert data["duration"] == orig_duration, "总时长被改动!"
ref_ok = 0
all_refs = set()
for tr in data["tracks"]:
    for s in tr["segments"]:
        all_refs.update(s.get("extra_material_refs", []))
for a in data["materials"].get("material_animations", []):
    assert a["id"] in all_refs, f"动画 {a['id']} 未被引用"
    ref_ok += 1
for e in data["materials"].get("effects", []):
    if isinstance(e, dict) and e.get("type") == "text_effect":
        assert e["id"] in all_refs, f"花字 {e['id']} 未被引用"
        ref_ok += 1
json.dumps(data)  # 可序列化
print(f"\n校验通过: {ref_ok} 个动画/花字素材全部被引用, 总时长不变 ({orig_duration/1e6}s)")

if not APPLY:
    print("\n[dry-run] 未写入。确认无误后加 --apply 执行。")
    sys.exit(0)

# ---------- 写入 ----------
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
for p in (content_path, info_path):
    bak = p + f".pre_textfx_{ts}.bak"
    shutil.copy2(p, bak)
    print("备份:", bak)

with open(content_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
# draft_info 与 draft_content 等价(同一草稿 id), 且旧 draft_info 可能已分叉/含悬空引用 -> 直接写入等价内容修复
with open(info_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
print("已写入 draft_content.json 与 draft_info.json (等价内容)")

# 复核
for p in (content_path, info_path):
    d2 = json.load(open(p, encoding="utf-8"))
    assert d2["duration"] == orig_duration
print("写入后复核通过。请在剪映(VIP已登录+联网)中打开草稿, 首次打开会自动下载 VIP 动画/花字素材。")
