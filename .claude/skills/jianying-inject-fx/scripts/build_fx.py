# -*- coding: utf-8 -*-
"""
给已有剪映 5.9 草稿注入 VIP 转场 + VIP 特效（双 JSON 等价注入）。
- dry-run（默认）：校验素材存在且为 VIP、转场时长约束，打印注入后概览，不写文件。
- --apply     ：先给两个 JSON 打时间戳备份，再写入。

改这三处即可复用：
  1) DRAFT      —— 目标草稿目录
  2) TRANS_PLAN —— 转场名，按视频轨片段顺序排列；第 i 个转场挂到第 i 个片段(衔接 seg[i]->seg[i+1])
  3) EFF_PLAN   —— (特效名, 起始秒, 结束秒, 轨号)；同一轨号内片段不能时间重叠
素材名必须能在 metadata 里找到且 is_vip=True，否则 assert 卡住。
"""
import ast, sys, os, json, uuid, shutil, time
sys.stdout.reconfigure(encoding='utf-8')

# metadata 目录（本机真实路径；VIP 素材 ID 库）
META  = r"e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor\pyJianYingDraft\metadata"
# 目标草稿目录（改成你的草稿）
DRAFT = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>"
APPLY = '--apply' in sys.argv

def parse_meta(fname, ctor):
    """用 ast 解析 metadata：ctor 第 1 个位置参数=name，第 2 个=is_vip，第 3 个=resource_id，第 4 个=effect_id，第 6 个=default_duration_s，第 7 个=is_overlap(转场)。"""
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

TRANS = parse_meta('transition_meta.py', 'TransitionMeta')   # name -> [name,is_vip,rid,eid,md5,dur_s,is_overlap]
EFF   = parse_meta('video_scene_effect.py', 'EffectMeta')    # name -> [name,is_vip,rid,eid,md5,...]

# ---- 方案（改这里）----
# 转场：第 i 个挂到视频轨第 i 个片段(前段)，衔接 seg[i]->seg[i+1]。数量应 <= 片段数-1。
TRANS_PLAN = [
    "复古漏光 II", "亮点模糊", "珠光模糊", "春日光斑",
    "横移模糊", "时光穿梭", "金色光斑", "星光叠化",
]
# 特效：(name, start_s, end_s, track_index)  同一 track_index 内不能时间重叠
EFF_PLAN = [
    ("胶片暖棕", 0.0, 28.0, 0),   # 全片铺底
    ("竖向开幕", 0.0, 2.5, 1),    # 开头钩子（放另一轨，避免与铺底重叠）
    ("花瓣环绕", 24.5, 28.0, 1),  # 结尾氛围
]

def us(s):
    return int(round(s * 1e6))

# ---- 双 JSON 共用同一套 uuid（必须模块级生成一次，勿挪进 inject，否则两份文件 id 分叉）----
TRANS_IDS   = [uuid.uuid4().hex for _ in TRANS_PLAN]
EFF_MAT_IDS = [uuid.uuid4().hex for _ in EFF_PLAN]
EFF_SEG_IDS = [uuid.uuid4().hex for _ in EFF_PLAN]
TRACK_IDS   = {ti: uuid.uuid4().hex for ti in sorted({e[3] for e in EFF_PLAN})}

# ---- 校验元数据存在 + VIP ----
print("=== 转场(VIP)核对 ===")
for n in TRANS_PLAN:
    m = TRANS.get(n)
    assert m, f"转场未找到: {n}"
    assert m[1] is True, f"非VIP转场: {n}"
    print(f"  {n:<10} VIP dur={m[5]}s is_overlap={m[6]} rid={m[2]} eid={m[3]}")
print("=== 特效(VIP)核对 ===")
for n, a, b, t in EFF_PLAN:
    m = EFF.get(n)
    assert m, f"特效未找到: {n}"
    assert m[1] is True, f"非VIP特效: {n}"
    print(f"  {n:<8} VIP {a}-{b}s 轨{t} rid={m[2]} eid={m[3]}")

def inject(path):
    d = json.load(open(path, encoding='utf-8'))
    mats = d['materials']
    vtrack = next(t for t in d['tracks'] if t['type'] == 'video')
    segs = vtrack['segments']
    assert len(TRANS_PLAN) <= len(segs) - 1, \
        f"转场数({len(TRANS_PLAN)}) 超过衔接点数({len(segs)-1})"
    seg_durs = [s['target_timerange']['duration'] for s in segs]

    # ---- 转场：挂到前一片段的 extra_material_refs ----
    for i, n in enumerate(TRANS_PLAN):
        m = TRANS[n]
        dur = us(m[5])
        limit = min(seg_durs[i], seg_durs[i + 1])   # 时长 <= 相邻两片段较短者
        assert dur <= limit, f"转场[{n}] {dur} 超过相邻较短片段 {limit}"
        gid = TRANS_IDS[i]
        mats.setdefault('transitions', []).append({
            "category_id": "", "category_name": "",
            "duration": dur, "effect_id": m[3], "id": gid,
            "is_overlap": bool(m[6]), "name": m[0], "platform": "all",
            "resource_id": m[2], "type": "transition",
        })
        segs[i].setdefault('extra_material_refs', []).append(gid)  # 追加，勿覆盖已有 ref

    # ---- 特效：独立 effect 轨 + materials.video_effects ----
    eff_tracks = {}
    for j, (n, a, b, ti) in enumerate(EFF_PLAN):
        m = EFF[n]
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

    # 每个 track_index 一条独立特效轨，插到视频轨之后
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
    for fn in ['draft_content.json', 'draft_info.json']:   # 双 JSON 等价注入
        p = os.path.join(DRAFT, fn)
        bak = p + f'.pre_fx_{ts}.bak'
        shutil.copy2(p, bak)
        d = inject(p)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        print(f"已写入 {fn} (备份: {os.path.basename(bak)})  "
              f"transitions={len(d['materials']['transitions'])} "
              f"video_effects={len(d['materials']['video_effects'])} "
              f"tracks={[(t['type'], len(t['segments'])) for t in d['tracks']]}")
    print("APPLY 完成")
else:
    d = inject(os.path.join(DRAFT, 'draft_content.json'))
    print("\n[DRY-RUN] 注入后 draft_content 概览：")
    print("  transitions:", len(d['materials']['transitions']))
    print("  video_effects:", len(d['materials']['video_effects']))
    print("  tracks:", [(t['type'], len(t['segments'])) for t in d['tracks']])
    vseg = next(t for t in d['tracks'] if t['type'] == 'video')['segments']
    print("  视频轨各片段 extra_material_refs 数量:", [len(s.get('extra_material_refs', [])) for s in vseg])
    print("\n未写入文件（加 --apply 才写）。")
