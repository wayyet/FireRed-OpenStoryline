# -*- coding: utf-8 -*-
"""
替换模式：剔除旧注入 → 注入新 VIP 转场/特效（双 JSON 等价注入，共用同一套 uuid）。
- dry-run（默认）：黑名单/VIP/时长约束校验 + 剔除与注入概览，不写文件。
- --apply     ：先给两个 JSON 打时间戳备份，再剔除+注入一次写盘，逐文件自校验。

改这五处即可复用：
  1) DRAFT        —— 目标草稿目录
  2) BANNED_*     —— 历史所有轮次已用的转场/特效名并集（查记忆 kuaishou-fx-used-history），新方案不得撞
  3) STRIP_*      —— 本草稿当前要剔除的上一轮注入名单（通常 = 历史清单里该草稿的现行配置）
  4) TRANS_PLAN   —— 新转场名，按视频轨片段顺序；第 i 个挂到第 i 个片段(衔接 seg[i]->seg[i+1])
  5) EFF_PLAN     —— (特效名, 起始秒, 结束秒, 轨号)；end=None 到片尾，start=None 片尾前 3.5s 起
校验红线：每份文件只和它自己注入前的状态比（draft_info 与 draft_content 的
duration/refs 基数天生不同，跨文件套数字必出误报）。
"""
import ast, sys, os, json, uuid, shutil, time
sys.stdout.reconfigure(encoding='utf-8')

META  = r"e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor\pyJianYingDraft\metadata"
DRAFT = r"C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>"
APPLY = '--apply' in sys.argv

# ---- 历史黑名单（所有轮次并集，选型不得复用；查记忆 kuaishou-fx-used-history）----
BANNED_TRANS = {"复古漏光 II", "亮点模糊", "珠光模糊", "春日光斑", "横移模糊", "时光穿梭",
                "金色光斑", "星光叠化", "流光", "聚光灯", "金沙", "发光变焦", "虹光旋入", "星光"}
BANNED_EFFS  = {"胶片暖棕", "竖向开幕", "花瓣环绕", "辉光开幕", "金粉飘落",
                "金色辉光", "拉镜开幕", "聚光灯金粉", "绚丽光斑"}

# ---- 本草稿要剔除的上一轮注入（名字精确匹配）----
STRIP_TRANS = {"聚光灯", "金沙", "发光变焦", "虹光旋入", "星光"}
STRIP_EFFS  = {"金色辉光", "拉镜开幕", "聚光灯金粉", "绚丽光斑"}

# ---- 新方案（改这里；每个名字都不得出现在 BANNED_* 里）----
TRANS_PLAN = ["<转场1>", "<转场2>"]
# (特效名, 起始秒, 结束秒, 轨号)  end=None 表示到片尾；start=None 表示片尾前 3.5s 起
EFF_PLAN = [
    ("<铺底特效>", 0.0, None, 0),
    ("<开幕钩子>", 0.0, 3.0, 1),
    ("<结尾氛围>", None, None, 1),
]

def parse_meta(fname, ctor):
    """ast 解析 metadata：第1参=name，第2参=is_vip，第3参=resource_id，第4参=effect_id，第6参=default_duration_s，第7参=is_overlap(转场)。"""
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

def us(s):
    return int(round(s * 1e6))

# ---- 新方案核对：存在 + VIP + 不撞历史黑名单 ----
print("=== 新方案素材核对（须 VIP 且不在历史黑名单） ===")
for n in TRANS_PLAN:
    m = TRANS.get(n)
    assert m, f"转场未找到: {n}"
    assert m[1] is True, f"非VIP转场: {n}"
    assert n not in BANNED_TRANS, f"转场撞历史黑名单: {n}"
    print(f"  转场 {n:<8} VIP dur={m[5]}s overlap={m[6]} rid={m[2]}")
for n, a, b, t in EFF_PLAN:
    m = EFF.get(n)
    assert m, f"特效未找到: {n}"
    assert m[1] is True, f"非VIP特效: {n}"
    assert n not in BANNED_EFFS, f"特效撞历史黑名单: {n}"
    print(f"  特效 {n:<8} VIP 轨{t} rid={m[2]}")

# ---- 双 JSON 共用同一套 uuid（必须模块级生成一次，勿挪进 inject）----
TRANS_IDS   = [uuid.uuid4().hex for _ in TRANS_PLAN]
EFF_MAT_IDS = [uuid.uuid4().hex for _ in EFF_PLAN]
EFF_SEG_IDS = [uuid.uuid4().hex for _ in EFF_PLAN]
TRACK_IDS   = {ti: uuid.uuid4().hex for ti in sorted({e[3] for e in EFF_PLAN})}

def strip_old(d):
    """剔除旧注入：转场(含片段引用)、特效素材、整条 effect 轨。返回剔除统计。"""
    mats = d['materials']
    old_tids = {t['id'] for t in mats.get('transitions', []) if t.get('name') in STRIP_TRANS}
    mats['transitions'] = [t for t in mats.get('transitions', []) if t['id'] not in old_tids]
    n_ref = 0
    for tr in d['tracks']:
        if tr['type'] != 'video':
            continue
        for s in tr['segments']:
            refs = s.get('extra_material_refs', [])
            keep = [r for r in refs if r not in old_tids]
            n_ref += len(refs) - len(keep)
            s['extra_material_refs'] = keep
    old_eids = {e['id'] for e in mats.get('video_effects', []) if e.get('name') in STRIP_EFFS}
    mats['video_effects'] = [e for e in mats.get('video_effects', []) if e['id'] not in old_eids]
    n_trk = 0
    kept_tracks = []
    for tr in d['tracks']:
        if tr['type'] == 'effect':
            mat_ids = {s.get('material_id') for s in tr['segments']}
            if mat_ids <= old_eids:   # 整条轨全是旧特效 → 删轨；混轨不整删，避免误删用户素材
                n_trk += 1
                continue
        kept_tracks.append(tr)
    d['tracks'] = kept_tracks
    return len(old_tids), n_ref, len(old_eids), n_trk

def inject(d):
    mats = d['materials']
    vtrack = next(t for t in d['tracks'] if t['type'] == 'video')
    segs = vtrack['segments']
    assert len(TRANS_PLAN) <= len(segs) - 1, "转场数超过衔接点数"
    seg_durs = [s['target_timerange']['duration'] for s in segs]
    total_us = d['duration']
    total_s = total_us / 1e6

    # ---- 转场：挂到前一片段的 extra_material_refs（追加，勿覆盖）----
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
        segs[i].setdefault('extra_material_refs', []).append(gid)

    # ---- 特效：独立 effect 轨 + materials.video_effects ----
    eff_tracks = {}
    for j, (n, a, b, ti) in enumerate(EFF_PLAN):
        m = EFF[n]
        a_s = (total_s - 3.5) if a is None else a       # 结尾氛围：片尾前 3.5s 起
        b_s = total_s if b is None else b
        assert 0 <= a_s < b_s <= total_s + 1e-6, f"特效[{n}]时间范围异常 {a_s}-{b_s}"
        gid = EFF_MAT_IDS[j]
        mats.setdefault('video_effects', []).append({
            "adjust_params": [], "apply_target_type": 2, "apply_time_range": None,
            "category_id": "", "category_name": "", "common_keyframes": [],
            "disable_effect_faces": [], "effect_id": m[3], "formula_id": "",
            "id": gid, "name": m[0], "platform": "all", "render_index": 11000,
            "resource_id": m[2], "source_platform": 0, "time_range": None,
            "track_render_index": 0, "type": "video_effect", "value": 1.0, "version": "",
        })
        start_us = us(a_s)
        dur_us = min(us(b_s), total_us) - start_us
        eff_tracks.setdefault(ti, []).append({
            "enable_adjust": True, "enable_color_correct_adjust": False,
            "enable_color_curves": True, "enable_color_match_adjust": False,
            "enable_color_wheels": True, "enable_lut": True,
            "enable_smart_color_adjust": False, "last_nonzero_volume": 1.0,
            "reverse": False, "track_attribute": 0, "track_render_index": 0,
            "visible": True, "id": EFF_SEG_IDS[j], "material_id": gid,
            "target_timerange": {"start": start_us, "duration": dur_us},
            "common_keyframes": [], "keyframe_refs": [], "render_index": 10000 + ti,
        })

    # 同一轨内不重叠校验
    for ti, ss in eff_tracks.items():
        spans = sorted((x['target_timerange']['start'],
                        x['target_timerange']['start'] + x['target_timerange']['duration']) for x in ss)
        for k in range(1, len(spans)):
            assert spans[k][0] >= spans[k-1][1], f"特效轨{ti}片段重叠: {spans}"

    # 每个轨号一条独立特效轨，插到视频轨之后
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

def report(tag, d):
    mats = d['materials']
    print(f"[{tag}] transitions={[t['name'] for t in mats.get('transitions', [])]}")
    print(f"[{tag}] video_effects={[e['name'] for e in mats.get('video_effects', [])]}")
    print(f"[{tag}] tracks={[(t['type'], len(t['segments'])) for t in d['tracks']]}  时长={d['duration']/1e6:.2f}s")
    vseg = next(t for t in d['tracks'] if t['type'] == 'video')['segments']
    print(f"[{tag}] 视频轨各片段refs数={[len(s.get('extra_material_refs', [])) for s in vseg]}")

def verify(d):
    """逐文件自校验（只跟本文件自己比，不跨文件套基数）。"""
    mats = d['materials']
    tids = {t['id'] for t in mats.get('transitions', [])}
    ref_ids = set()
    for tr in d['tracks']:
        if tr['type'] == 'video':
            for s in tr['segments']:
                ref_ids |= set(s.get('extra_material_refs', []))
    assert tids <= ref_ids, "存在未被引用的转场"
    eids = {e['id'] for e in mats.get('video_effects', [])}
    seg_mids = set()
    for tr in d['tracks']:
        if tr['type'] == 'effect':
            for s in tr['segments']:
                seg_mids.add(s['material_id'])
    assert seg_mids == eids, f"特效引用不一致: 轨上{len(seg_mids)} vs 素材{len(eids)}"
    return True

files = ['draft_content.json', 'draft_info.json']   # 双 JSON 等价注入
if APPLY:
    ts = time.strftime('%Y%m%d_%H%M%S')
    for fn in files:
        p = os.path.join(DRAFT, fn)
        bak = p + f'.pre_fx_{ts}.bak'
        shutil.copy2(p, bak)
        d = json.load(open(p, encoding='utf-8'))
        dur0 = d['duration']                       # 本文件自己的基数
        st = strip_old(d)
        print(f"\n{fn}: 剔除转场{st[0]}个/片段引用{st[1]}处/特效{st[2]}个/特效轨{st[3]}条 (备份: {os.path.basename(bak)})")
        d = inject(d)
        assert d['duration'] == dur0, "总时长被改动!"
        verify(d)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        report(fn, d)
    print("\nAPPLY 完成: 双 JSON 已剔除旧注入并等价注入新方案(共用同一套 uuid)")
    print("提醒: 记得把本轮配置追加进记忆 kuaishou-fx-used-history")
else:
    for fn in files:
        p = os.path.join(DRAFT, fn)
        d = json.load(open(p, encoding='utf-8'))
        dur0 = d['duration']
        st = strip_old(d)
        print(f"\n[DRY-RUN] {fn}: 将剔除 转场{st[0]}个/片段引用{st[1]}处/特效{st[2]}个/特效轨{st[3]}条")
        d = inject(d)
        assert d['duration'] == dur0
        verify(d)
        report(fn, d)
    print("\n[DRY-RUN] 校验全部通过, 未写入文件(加 --apply 才写)。")
