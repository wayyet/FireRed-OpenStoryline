import sys; sys.stdout.reconfigure(encoding='utf-8')
import ast, inspect

# ========== 历史黑名单（从记忆 kuaishou-fx-used-history 提取）==========
BANNED_TRANS = {
    '复古漏光 II','亮点模糊','珠光模糊','春日光斑','横移模糊','时光穿梭','金色光斑','星光叠化',
    '聚光灯','金沙','发光变焦','虹光旋入','星光',
    '霓虹闪光','信号故障','蓝光扫描','炫光扫描','快速缩放','未来光谱','电光 II',
    '波光粼粼','镜头速移','暧昧光晕','旋焦','扫光','曝光摇镜',
}
BANNED_EFF = {
    '胶片暖棕','竖向开幕','花瓣环绕',
    '辉光开幕','金粉飘落',
    '紫光夜','故障开幕','霓虹光线',
    '水光影','泛光扫描','精致辉光',
    '金色辉光','拉镜开幕','聚光灯金粉','绚丽光斑',
}

# ========== 解析 transition_meta.py ==========
trans_path = r'e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor\pyJianYingDraft\metadata\transition_meta.py'
with open(trans_path, 'r', encoding='utf-8') as f:
    src = f.read()

tree = ast.parse(src)
vip_trans = []
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.value.elts if isinstance(node.value, ast.List) else []:
            if isinstance(t, ast.Call):
                args = t.args
                if len(args) >= 2 and isinstance(args[1], ast.Constant):
                    if args[1].value is True:
                        name = args[0].value if isinstance(args[0], ast.Constant) else None
                        rid  = args[2].value if len(args)>2 and isinstance(args[2], ast.Constant) else None
                        eid  = args[3].value if len(args)>3 and isinstance(args[3], ast.Constant) else None
                        dur  = args[5].value if len(args)>5 and isinstance(args[5], ast.Constant) else None
                        ovlp = args[6].value if len(args)>6 and isinstance(args[6], ast.Constant) else None
                        if name and name not in BANNED_TRANS:
                            vip_trans.append({'name':name,'resource_id':rid,'effect_id':eid,'default_duration_s':dur,'is_overlap':ovlp})

# 直接枚举 TransitionType 的成员（更可靠）
import importlib.util, sys
vendor_dir = r'e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor'
sys.path.insert(0, vendor_dir)
# 构造虚包让 relative import 能找到
import pathlib
pkg = pathlib.Path(vendor_dir)
pkg.joinpath('pyJianYingDraft','__init__.py').touch()
pkg.joinpath('pyJianYingDraft','metadata','__init__.py').touch()
spec = importlib.util.spec_from_file_location('transition_meta', trans_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TT = module.TransitionType
vip_trans2 = []
for item in TT:
    meta = item.value
    if meta.is_vip and meta.name not in BANNED_TRANS:
        vip_trans2.append({'name':meta.name,'resource_id':meta.resource_id,'effect_id':meta.effect_id,
                           'default_duration_s':meta.default_duration_s,'is_overlap':meta.is_overlap})

print(f'=== VIP 转场（黑名单过滤后）共 {len(vip_trans2)} 款 ===')
for t in sorted(vip_trans2, key=lambda x: x['name']):
    print(f"  {t['name']} | dur={t['default_duration_s']}s | overlap={t['is_overlap']} | rid={t['resource_id']}")

# ========== 解析 video_scene_effect.py ==========
eff_path = r'e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor\pyJianYingDraft\metadata\video_scene_effect.py'
spec2 = importlib.util.spec_from_file_location('video_scene_effect', eff_path)
module2 = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(module2)
VS = module2.VideoSceneEffect
vip_eff2 = []
for item in VS:
    meta = item.value
    if meta.is_vip and meta.name not in BANNED_EFF:
        vip_eff2.append({'name':meta.name,'resource_id':meta.resource_id,'effect_id':meta.effect_id})

print(f'\n=== VIP 特效（黑名单过滤后）共 {len(vip_eff2)} 款 ===')
for e in sorted(vip_eff2, key=lambda x: x['name']):
    print(f"  {e['name']} | rid={e['resource_id']}")
