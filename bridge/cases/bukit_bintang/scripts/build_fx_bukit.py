# -*- coding: utf-8 -*-
"""
吉隆坡武吉免登_纯视频  - 方案A 霓虹迷醉·都市夜游
- 7个转场（7个衔接点）+ 开幕钩子(0-3s) + 全片铺底 + 结尾收束
"""
import ast, sys, os, json, uuid, shutil, time
sys.stdout.reconfigure(encoding='utf-8')

META  = r"e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor\pyJianYingDraft\metadata"
DRAFT = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\吉隆坡武吉免登_纯视频"
APPLY = '--apply' in sys.argv

def parse_meta(fname, ctor):
    tree = ast.parse(open(os.path.join(META, fname), encoding='utf-8').read())
    by_name = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            c = node.value
            fn = getattr(c.func, 'id', getattr(c.func, 'attr', None))
            if fn != ctor:
                continue
            a = [x.value if isinstance(x, ast.Constant) else None for x in c.args]
            by_name[a[0]] = a
    return by_name

TRANS = parse_meta('transition_meta.py', 'TransitionMeta')
EFF   = parse_meta('video_scene_effect.py', 'EffectMeta')

# ========== 方案 A：霓虹迷醉·都市夜游 ==========
# 7个衔接点 → 7个转场（按片段顺序挂前段）
TRANS_PLAN = [
    "闪光灯 III",    # clip1→clip2  (衔接点1)
    "信号故障 II",   # clip2→clip3  (衔接点2)
    "故障扫描",      # clip3→clip4  (衔接点3)
    "闪光灯 III",    # clip4→clip5  (衔接点4)
    "信号故障 II",   # clip5→clip6  (衔接点5)
    "故障扫描",      # clip6→clip7  (衔接点6)
    "闪光灯 III",    # clip7→clip8  (衔接点7)
]
# 特效：(name, start_s, end_s, track_index)
# track_index 0=铺底全片, 1=钩子首尾(首3s+尾3s拆两条)
EFF_PLAN = [
    ("动感光束",   0.0, 36.2, 0),   # 全片铺底（统一光束节奏感）
    ("霓虹闪切",   0.0,  3.0, 1),   # 黄金3秒钩子
    ("光线扫描",  33.0, 36.2, 2),   # 结尾收束
]

def us(s):
    return int(round(s * 1e6))

# ---- 双 JSON 共用同一套 uuid ----
TRANS_IDS    = [uuid.uuid4().hex for _ in TRANS_PLAN]
EFF_MAT_IDS  = [uuid.uuid4().hex for _ in EFF_PLAN]
EFF_SEG_IDS  = [uuid.uuid4().hex for _ in EFF_PLAN]
TRACK_IDS    = {ti: uuid.uuid4().hex for ti in sorted({e[3] for e in EFF_PLAN})}

# ---- 校验 ----
print("=== 转场(VIP)核对 ===")
for n in TRANS_PLAN:
    m = TRANS.get(n)
    assert m, f"转场未找到: {n}"
    assert m[1] is True, f"非VIP转场: {n}"
    print(f"  {n:<12} VIP dur={m[5]}s is_overlap={m[6]} rid={m[2]}")

print("=== 特效(VIP)核对 ===")
for n, a, b, t in EFF_PLAN:
    m = EFF.get(n)
    assert m, f"特效未找到: {n}"
    assert m[1] is True, f"非VIP特效: {n}"
    print(f"  {n:<10} VIP {a}-{b}s 轨{t} rid={m[2]}")

def inject(path):
    d = json.load(open(path, encoding='utf-8'))
    mats  = d['materials']
    vtrack = next(t for t in d['tracks'] if t['type'] == 'video')
    segs   = vtrack['segments']
    assert len(TRANS_PLAN) <= len(segs) - 1, \
        f"转场数({len(TRANS_PLAN)}) > 衔接点数({len(segs)-1})"

    seg_durs = [s['target_timerange']['duration'] for s in segs]

    # ---- 转场：挂到前一片段的 extra_material_refs ----
    for i, n in enumerate(TRANS_PLAN):
        m  = TRANS[n]
        dur = us(m[5])
        limit = min(seg_durs[i], seg_durs[i + 1])
        assert dur <= limit, f"转场[{n}] {dur}us > 较短片段 {limit}us"
        gid = TRANS_IDS[i]
        mats.setdefault('transitions', []).append({
            "category_id": "", "category_name": "",
            "duration": dur, "effect_id": m[3], "id": gid,
            "is_overlap": bool(m[6]), "name": m[0], "platform": "all",
            "resource_id": m[2], "type": "transition",
        })
        segs[i].setdefault('extra_material_refs', []).append(gid)

    # ---- 特效：独立 effect 轨 ----
    eff_tracks = {}
    for j, (n, a, b, ti) in enumerate(EFF_PLAN):
        m   = EFF[n]
        gid = EFF_MAT_IDS[j]
        mats.setdefault('video_effects', []).append({
            "adjust_params": [], "apply_target_type": 2, "apply_time_range": None,
            "category_id": "", "category_name": "", "common_keyframes": [],
            "disable_effect_faces": [], "effect_id": m[3], "formula_id": "",
            "id": gid, "name": m[0], "platform": "all", "render_index": 11000,
            "resource_id": m[2], "source_platform": 0, "time_range": None,
            "track_render_index": 0, "type": "video_effect", "value": 1.0, "version": "",
        })
        eff_tracks.setdefault(ti, []).append({
            "enable_adjust": True, "enable_color_correct_adjust": False,
            "enable_color_curves": True, "enable_color_match_adjust": False,
            "enable_color_wheels": True, "enable_lut": True,
            "enable_smart_color_adjust": False, "last_nonzero_volume": 1.0,
            "reverse": False, "track_attribute": 0, "track_render_index": 0,
            "visible": True, "id": EFF_SEG_IDS[j], "material_id": gid,
            "target_timerange": {"start": us(a), "duration": us(b) - us(a)},
            "common_keyframes": [], "keyframe_refs": [], "render_index": 10000 + ti,
        })

    # 插入新特效轨（接在视频轨之后）
    new_tracks = []
    for ti in sorted(eff_tracks):
        new_tracks.append({
            "attribute": 0, "flag": 0, "id": TRACK_IDS[ti],
            "is_default_name": True, "name": "",
            "segments": eff_tracks[ti], "type": "effect",
        })
    vidx = d['tracks'].index(vtrack)
    d['tracks'][vidx + 1:vidx + 1] = new_tracks
    return d

if APPLY:
    ts = time.strftime('%Y%m%d_%H%M%S')
    for fn in ['draft_content.json', 'draft_info.json']:
        p   = os.path.join(DRAFT, fn)
        bak = p + f'.pre_fx_{ts}.bak'
        shutil.copy2(p, bak)
        d   = inject(p)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        print(f"已写入 {fn}  备份:{os.path.basename(bak)}  "
              f"transitions={len(d['materials']['transitions'])}  "
              f"video_effects={len(d['materials']['video_effects'])}  "
              f"tracks={[(t['type'], len(t['segments'])) for t in d['tracks']]}")
    print("APPLY 完成")
else:
    d = inject(os.path.join(DRAFT, 'draft_content.json'))
    print("\n[DRY-RUN] 注入后 draft_content 概览：")
    print(f"  transitions: {len(d['materials']['transitions'])}")
    print(f"  video_effects: {len(d['materials']['video_effects'])}")
    print(f"  tracks: {[(t['type'], len(t['segments'])) for t in d['tracks']]}")
    vseg = next(t for t in d['tracks'] if t['type'] == 'video')['segments']
    print(f"  各片段 extra_material_refs 数量: {[len(s.get('extra_material_refs',[])) for s in vseg]}")
    print("\n未写入文件（加 --apply 才写）。")
