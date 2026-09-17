import sys; sys.stdout.reconfigure(encoding='utf-8')
import re

# ========== 历史黑名单 ==========
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

# ========== 解析转场 ==========
trans_path = r'e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor\pyJianYingDraft\metadata\transition_meta.py'
with open(trans_path, 'r', encoding='utf-8') as f:
    src = f.read()

# 找所有 TransitionMeta(...) 调用，第2个参数是 is_vip
# 格式: TransitionMeta("name", False/True, "rid", "eid", "md5", 1.23, True/False)
pattern = re.compile(r'TransitionMeta\s*\(\s*"([^"]+)"\s*,\s*(True|False)\s*,')
vip_trans = []
for m in pattern.finditer(src):
    name, is_vip = m.group(1), m.group(2)
    if is_vip == 'True' and name not in BANNED_TRANS:
        vip_trans.append(name)

print(f'=== VIP 转场（黑名单过滤后）共 {len(vip_trans)} 款 ===')
for n in sorted(vip_trans):
    print(f'  {n}')

# ========== 解析特效 ==========
eff_path = r'e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor\pyJianYingDraft\metadata\video_scene_effect.py'
with open(eff_path, 'r', encoding='utf-8') as f:
    src2 = f.read()

pattern2 = re.compile(r'=\s*EffectMeta\s*\(\s*"([^"]+)"\s*,\s*(True|False)\s*,')
vip_eff = []
for m in pattern2.finditer(src2):
    name, is_vip = m.group(1), m.group(2)
    if is_vip == 'True' and name not in BANNED_EFF:
        vip_eff.append(name)

print(f'\n=== VIP 特效（黑名单过滤后）共 {len(vip_eff)} 款 ===')
for n in sorted(vip_eff):
    print(f'  {n}')
