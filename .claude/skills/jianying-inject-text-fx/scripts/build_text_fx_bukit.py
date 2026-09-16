"""给剪映 5.9 草稿「吉隆坡武吉免登_纯视频」批量注入 VIP 文字动画 + VIP 花字.

不经 pyJianYingDraft 运行时，直接改 draft_content.json / draft_info.json 双 JSON。

用法(系统 Python 3.13):
  & "C:\Program Files\Python313\python.exe" .\build_text_fx_bukit.py            # dry-run
  & "C:\Program Files\Python313\python.exe" .\build_text_fx_bukit.py --apply    # 备份后写入

花字样本: 用户已在剪映客户端手挑「上下错落发光花字」resource_id=7368866329337580851
          (第1条字幕 d9b034a4802f420e92e73271d07a8699 已有，跳过克隆，其余7条应用)
"""
import sys, json, uuid, os, shutil, copy, datetime
sys.stdout.reconfigure(encoding='utf-8')

# ============ 配置 ============
DRAFT = r"C:\Users\wayyet\AppData\Local\JianYingPro\User Data\Projects\com.lveditor.draft\吉隆坡武吉免登_纯视频"

# 历史已用动画标题黑名单（全部历史轮次并集）
BANNED = {
    # 大岭村 2026-07-02
    "星光闪闪 II", "模糊发光", "向下溶解", "发光闪入", "弹入跳动",
    "消散", "向左模糊", "漂浮", "心跳",
    # 永华艺术馆 2026-07-05
    "辉光扫描", "流光扩散", "汇聚", "激光雕刻", "描边填充", "环绕滑入",
    "背景滑入", "预览打字", "逐字旋入", "生长 II", "向上弹入", "放大震动",
    "流光", "文字泛光", "飘起", "强调三遍",
    "闪烁散开", "逐字虚影",
    # EXCHANGE TRX 2026-07-06
    "电光", "电光 II", "二段缩放", "旋转缩放", "星光闪闪", "闪烁集合",
    "声波震动", "波浪",
    # Pavilion KL 中文 2026-07-07
    "心动瞬间", "喷绘", "新年打字机", "镂空跳入", "缤纷冲屏", "慢速放大",
    "金粉飘落",
    "渐变拖尾", "波浪 III", "福袋炸开", "放大缩小", "竖向渐变", "摇摆 I", "悸动",
    "镂空跳出", "向上飞出", "逐字旋出", "顶出", "向下翻转", "折叠", "炸开 Ⅲ",
    # Pavilion KL 英文 2026-07-11
    "色散拖影", "发光模糊", "叠影并入", "模糊缩小", "雪光模糊", "随机上升", "缩放 III",
    "彩色切换", "影像叠加", "空间翻转 II", "放大镜", "环形滚动", "尾巴摇摆", "逐字放大",
    "叠影并出", "向左模糊 II", "环绕滑出", "模糊滚动", "螺旋下降", "波浪弹跳", "吸出",
}

# 历史已用花字 resource_id 黑名单
BANNED_FLOWER_RIDS = {
    "7160597532043644174",  # 潮酷白色发光立体（永华）
    "7339056253777284361",  # 蓝底黄色（TRX）
    "7127664822887419143",  # 美食综艺黄色（Pavilion KL中文）
    "7371124565839301925",  # 蓝色渐变立体（Pavilion KL英文）
}

# 修正版方案A「霓虹炫动·故障脉冲」——8条字幕全部为历史全新款
ANIM_PLAN = [
    {
        "label": "段1 武吉免登夜景开场钩子",
        "anims": [
            # 入场: 乱码故障 - 科技感故障霓虹，呼应「太绝了」
            {"type": "in",  "title": "乱码故障",   "resource_id": "7325648367747338802", "effect_id": "40877554", "duration_s": 1.0},
            # 循环: 加字符 - 字符叠加累积，都市科技感
            {"type": "loop","title": "加字符",     "resource_id": "7441532971082846758", "effect_id": "93688629", "duration_s": 0.8},
            # 出场: 故障 - 统一故障主题
            {"type": "out", "title": "故障",       "resource_id": "7091567288385540622", "effect_id": "1789138",  "duration_s": 0.5},
        ]
    },
    {
        "label": "段2 棕榈树橙光氛围",
        "anims": [
            # 入场: 倒数 - 悬念递增
            {"type": "in",  "title": "倒数",      "resource_id": "7314303157360661018", "effect_id": "35401566", "duration_s": 1.8},
            # 循环: 喷涌 - 能量散发，呼应橙光温暖感
            {"type": "loop","title": "喷涌",      "resource_id": "7134190113780666887", "effect_id": "4175399",  "duration_s": 0.5},
            # 出场: 随机弹跳 - 弹跳离场，俏皮收尾
            {"type": "out", "title": "随机弹跳",  "resource_id": "7026617357300666893", "effect_id": "1644665", "duration_s": 0.5},
        ]
    },
    {
        "label": "段3 地点宣告飞轮海",
        "anims": [
            # 入场: 呐喊声波 - 冲击波感+都市宣告
            {"type": "in",  "title": "呐喊声波",   "resource_id": "7199943069385364005", "effect_id": "9432429",  "duration_s": 0.5},
            # 循环: 打字机IV - 打字累积感，都市节奏
            {"type": "loop","title": "打字机IV",   "resource_id": "7237411448303915557", "effect_id": "14235853", "duration_s": 2.0},
            # 出场: 空翻 - 翻转发光离场
            {"type": "out", "title": "空翻",       "resource_id": "6865176065514410503", "effect_id": "1644641",  "duration_s": 0.5},
        ]
    },
    {
        "label": "段4 摩天大楼天际线",
        "anims": [
            # 入场: 圆柱体滚动 - 立体机械感，呼应建筑
            {"type": "in",  "title": "圆柱体滚动", "resource_id": "7179035729043919397", "effect_id": "7548913",  "duration_s": 1.2},
            # 循环: 彩色火焰 - 炫彩能量
            {"type": "loop","title": "彩色火焰",   "resource_id": "7308278472541999654", "effect_id": "32283417", "duration_s": 0.5},
            # 出场: 打字光标 - 打字发光离场
            {"type": "out", "title": "打字光标",   "resource_id": "7237411357514011192", "effect_id": "14235878", "duration_s": 2.0},
        ]
    },
    {
        "label": "段5 标志塔森林背景",
        "anims": [
            # 入场: 兔子弹跳 - 俏皮活力
            {"type": "in",  "title": "兔子弹跳",   "resource_id": "7187785892382118461", "effect_id": "8398145",  "duration_s": 0.5},
            # 循环: 扩音器 - 放大强调
            {"type": "loop","title": "扩音器",    "resource_id": "7277870806552547895", "effect_id": "22619881", "duration_s": 1.2},
            # 出场: 发光闪出 - 闪亮离场
            {"type": "out", "title": "发光闪出",   "resource_id": "7308275717505028617", "effect_id": "32281161", "duration_s": 1.8},
        ]
    },
    {
        "label": "段6 俯视城景伊顿大厦",
        "anims": [
            # 入场: 倒数 - 悬念钩子
            {"type": "in",  "title": "倒数",      "resource_id": "7314303157360661018", "effect_id": "35401566", "duration_s": 1.8},
            # 循环: 打字光标 - 打字累积紧迫感
            {"type": "loop","title": "打字光标",   "resource_id": "7237411357514011192", "effect_id": "14235878", "duration_s": 2.0},
            # 出场: 弹出跳动 - 弹跳离场
            {"type": "out", "title": "弹出跳动",  "resource_id": "7184797189627974200", "effect_id": "8058215",  "duration_s": 0.5},
        ]
    },
    {
        "label": "段7 单轨夜景",
        "anims": [
            # 入场: 冰雪飘动 - 冰凉霓虹折射，呼应夜景灯光
            {"type": "in",  "title": "冰雪飘动",   "resource_id": "7314291622525538843", "effect_id": "35395178", "duration_s": 1.5},
            # 循环: 加字符 - 循环字符累积
            {"type": "loop","title": "加字符",    "resource_id": "7441532971082846758", "effect_id": "93688629", "duration_s": 0.8},
            # 出场: 渐隐 - 柔和淡出
            {"type": "out", "title": "渐隐",       "resource_id": "6724919382104871427", "effect_id": "1644600", "duration_s": 0.5},
        ]
    },
    {
        "label": "段8 CTA结尾",
        "anims": [
            # 入场: 呐喊声波 - 最后冲击
            {"type": "in",  "title": "呐喊声波",   "resource_id": "7199943069385364005", "effect_id": "9432429",  "duration_s": 0.5},
            # 循环: 涂鸦手绘 - 手绘涂鸦质感，都市俏皮
            {"type": "loop","title": "涂鸦手绘",   "resource_id": "7276407256965452346", "effect_id": "22361305", "duration_s": 0.5},
            # 出场: 故障 - 回归故障主题收束
            {"type": "out", "title": "故障",       "resource_id": "7091567288385540622", "effect_id": "1789138",  "duration_s": 0.5},
        ]
    },
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
assert len(segs) == len(ANIM_PLAN), f"字幕段数 {len(segs)} != 方案条数 {len(ANIM_PLAN)}"

texts_by_id = {t["id"]: t for t in data["materials"]["texts"]}
orig_duration = data["duration"]

# ---------- 历史零复用黑名单硬校验 ----------
for entry in ANIM_PLAN:
    for a in entry["anims"]:
        assert a["title"] not in BANNED, \
            f"动画 {a['title']} 之前的视频已用过, 禁止复用! 请换新款"

# ---------- 防重复注入 ----------
existing_anims = data["materials"].get("material_animations", [])
assert not existing_anims, \
    f"草稿已存在 {len(existing_anims)} 条 material_animations —— 请确认是补注入还是剔除重做"

# ---------- 找花字样本 ----------
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
    print(f"[花字] 样本: name={flower_tpl.get('name','?')} "
          f"resource_id={flower_tpl.get('resource_id')} "
          f"(挂在 segment {flower_seg_id[:8] if flower_seg_id else '?'})")
    if flower_tpl and str(flower_tpl.get("resource_id")) in BANNED_FLOWER_RIDS:
        raise SystemExit(f"[花字] 样本 resource_id={flower_tpl.get('resource_id')} 历史已用, 请重新挑一款!")
else:
    print("[花字] 草稿中未发现 text_effect 样本 —— 本次只注入动画")

# 花字样式模板
style_tpl = None
diff_keys = {}
if flower_tpl and flower_seg_id:
    sample_seg = next(s for s in segs if s["id"] == flower_seg_id)
    sample_mat = texts_by_id[sample_seg["material_id"]]
    c = json.loads(sample_mat["content"])
    if c.get("styles") and "effectStyle" in c["styles"][0]:
        style_tpl = copy.deepcopy(c["styles"][0])
        print(f"[花字] effectStyle: {json.dumps(style_tpl.get('effectStyle'), ensure_ascii=False)}")
    other_mat = next(texts_by_id[s["material_id"]] for s in segs if s["id"] != flower_seg_id)
    for k in sample_mat:
        if k in ("id", "content", "words", "recognize_task_id"):
            continue
        if sample_mat.get(k) != other_mat.get(k):
            diff_keys[k] = sample_mat[k]
    print(f"[花字] 顶层字段差异: {list(diff_keys.keys())}")

# ---------- 注入函数 ----------
def inject(data, shared_uuids):
    mats = data["materials"]
    anims_list = mats.setdefault("material_animations", [])
    effects_list = mats.setdefault("effects", [])
    tts = [t for t in data["tracks"] if t.get("type") == "text"]
    assert len(tts) == 1
    ssegs = sorted(tts[0]["segments"], key=lambda s: s["target_timerange"]["start"])
    t_by_id = {t["id"]: t for t in mats["texts"]}

    report = []
    for i, (seg, entry) in enumerate(zip(ssegs, ANIM_PLAN)):
        seg_dur = seg["target_timerange"]["duration"]

        # --- 动画 ---
        anim_objs = []
        ordered = sorted(entry["anims"], key=lambda a: 0 if a["type"] in ("in", "out") else 1)
        outro_dur = 0
        for a in ordered:
            dur = min(int(round(a["duration_s"] * 1e6)), seg_dur)
            if a["type"] == "in":
                start = 0
            elif a["type"] == "out":
                start = seg_dur - dur
                outro_dur = dur
            else:
                start = 0
                dur = seg_dur - outro_dur
            anim_objs.append({
                "anim_adjust_params": None, "platform": "all", "panel": "",
                "material_type": "sticker", "name": a["title"],
                "id": a["effect_id"], "type": a["type"],
                "resource_id": a["resource_id"],
                "start": start, "duration": dur,
            })

        if anim_objs:
            anim_id = shared_uuids.setdefault(f"anim{i}", uuid.uuid4().hex)
            anims_list.append({
                "id": anim_id, "type": "sticker_animation",
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
            already = any(isinstance(e, dict) and e.get("type") == "text_effect"
                          and e["id"] in seg.get("extra_material_refs", [])
                          for e in effects_list)
            if already:
                fdesc = " | 花字: 已有(样本段), 跳过"
            else:
                fid = shared_uuids.setdefault(f"flower{i}", uuid.uuid4().hex)
                fmat = copy.deepcopy(flower_tpl)
                fmat["id"] = fid
                effects_list.append(fmat)
                seg.setdefault("extra_material_refs", []).append(fid)
                mat = t_by_id[seg["material_id"]]
                c = json.loads(mat["content"])
                if style_tpl is not None:
                    new_style = copy.deepcopy(style_tpl)
                    new_style["range"] = [0, len(c.get("text", ""))]
                    c["styles"] = [new_style]
                    mat["content"] = json.dumps(c, ensure_ascii=False)
                for k, v in diff_keys.items():
                    mat[k] = copy.deepcopy(v)
                fdesc = f" | 花字: {flower_tpl.get('name','?')}({flower_tpl.get('resource_id')})"

        report.append(f"  {entry['label']} ({seg['target_timerange']['start']/1e6:.1f}s+{seg_dur/1e6:.1f}s): {desc}{fdesc}")
    return report

shared = {}
report = inject(data, shared)
print()
print("=== 注入预览 ===")
for line in report:
    print(line)

# ---------- 校验 ----------
assert data["duration"] == orig_duration, "总时长被改动!"
all_refs = set()
for tr in data["tracks"]:
    for s in tr["segments"]:
        all_refs.update(s.get("extra_material_refs", []))
ref_ok = 0
for a in data["materials"].get("material_animations", []):
    assert a["id"] in all_refs, f"动画 {a['id']} 未被引用"
    ref_ok += 1
for e in data["materials"].get("effects", []):
    if isinstance(e, dict) and e.get("type") == "text_effect":
        assert e["id"] in all_refs, f"花字 {e['id']} 未被引用"
        ref_ok += 1
json.dumps(data)
print(f"\n校验通过: {ref_ok} 个素材全部被引用, 总时长不变 ({orig_duration/1e6}s)")

if not APPLY:
    print("\n[dry-run] 未写入。确认后加 --apply 执行。")
    sys.exit(0)

# ---------- 写入 ----------
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
for p in (content_path, info_path):
    bak = p + f".pre_textfx_{ts}.bak"
    shutil.copy2(p, bak)
    print("备份:", bak)

with open(content_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
with open(info_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
print("已写入双 JSON (等价内容)")

for p in (content_path, info_path):
    d2 = json.load(open(p, encoding="utf-8"))
    assert d2["duration"] == orig_duration
print("写入后复核通过。")
