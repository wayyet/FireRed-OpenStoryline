# -*- coding: utf-8 -*-
"""封面 mini-draft 文案校对 + VIP 花字克隆（模板，改常量后使用）。

背景：剪映的封面不是独立文件，而是**嵌套 mini-draft**，挂在主草稿
draft_content.json 的 `materials.drafts[0].draft` 里，结构和主草稿一样有自己的
materials.texts / tracks / effects。用 UI 自动化套完 VIP 模板后，若某几行文字没
在客户端里改干净、或想把主草稿里已验证的 VIP 花字克隆到封面副标题上，就用本脚本
直接改这段 mini-draft 的 JSON —— 比在客户端里一个字一个字抠更稳。

用法: python build_cover_fix.py [--apply]
  默认 dry-run 只打印计划; --apply 时先备份 draft_content.json 再写入并回读校验。

先决：剪映必须**已退出**(否则写入会被客户端覆盖/冲突)。
校准步骤：先跑一次 dry-run 看命中的 text_id / 文字是否对得上，再 --apply。

如何拿到下面的常量：
  用系统 Python 读 draft_content.json，打印
  data['materials']['drafts'][0]['draft']['materials']['texts'] 里每条的
  id 和 json.loads(content)['text']，据此填 TEXT_PLAN。
  VIP_FLOWER_RES 是主草稿字幕里已验证可用的 VIP 花字 resource_id（见记忆
  jianying-text-anim-flower）；OLD_EFFECT_PREFIX 是模板自带、要被替换掉的
  text_effect material id 前缀（从封面 segment 的 extra_material_refs 里找）。
"""
import json, sys, copy, uuid, shutil, datetime
sys.stdout.reconfigure(encoding='utf-8')

# ==== 按草稿实际情况改这几行 ====
DRAFT = r'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\大岭村_治愈系Vlog'
VIP_FLOWER_RES = '7617081886048914712'    # 已验证的 VIP 花字 resource_id
OLD_EFFECT_PREFIX = '51B4FEF5'            # 模板自带、待替换的花字 material id 前缀
# text_id -> 新文字 (None = 只保留原文字, 不改)
TEXT_PLAN = {
    '710FF4E0-F870-4c22-9F42-7AC468FF35BE': None,                   # 主标题 保持
    'E43817FF-191E-4750-91E0-61919EC8418B': 'Daling Village',       # 手写体点缀
    '6B759CB4-BA0D-4787-921B-296F2F56C11D': '蚝壳墙·青石巷·满塘荷花',   # 副标题(挂 VIP 花字)
    '29662A92-4E55-4cbc-A18D-03FAA26A7372': '0门票',                 # 角标
    'C387222E-8010-4b66-A32C-E2EF4EFAE40F': 'VLOG / 2026',          # 左上角
}
VIP_TARGET = '6B759CB4-BA0D-4787-921B-296F2F56C11D'   # 要挂 VIP 花字的那行 text_id
# ================================

CONTENT = DRAFT + r'\draft_content.json'


def main(apply=False):
    data = json.load(open(CONTENT, encoding='utf-8'))

    # 1. 从主草稿取一条已验证的 VIP 花字样本(effect material + text 样式)
    sample_eff = next(e for e in data['materials']['effects']
                      if e.get('type') == 'text_effect' and e.get('resource_id') == VIP_FLOWER_RES)
    sample_text = next(t for t in data['materials']['texts']
                       if VIP_FLOWER_RES in t.get('content', ''))
    sample_style = json.loads(sample_text['content'])['styles'][0]
    print('VIP 花字样本: resource_id=%s path=...%s' % (
        sample_eff['resource_id'], sample_eff['path'][-40:]))

    d = data['materials']['drafts'][0]['draft']          # 封面 mini-draft
    texts = {t['id']: t for t in d['materials']['texts']}

    # 2. 改封面各行文字
    for tid, new_text in TEXT_PLAN.items():
        t = texts[tid]
        c = json.loads(t['content'])
        old = c['text']
        if new_text is not None and new_text != old:
            c['text'] = new_text
            for st in c['styles']:
                st['range'] = [0, len(new_text)]          # range 必须跟文字长度同步
            print('文字: %r -> %r' % (old, new_text))
        # 3. 副标题克隆 VIP 花字样式(保留封面原字体/字号, 只换花字效果)
        if tid == VIP_TARGET:
            new_style = copy.deepcopy(sample_style)
            keep = c['styles'][0]
            new_style['range'] = [0, len(c['text'])]
            if 'font' in keep:
                new_style['font'] = keep['font']
            new_style['size'] = keep.get('size', new_style.get('size'))
            c['styles'] = [new_style]
            t['border_color'] = sample_text.get('border_color', t.get('border_color'))
            t['check_flag'] = sample_text.get('check_flag', t.get('check_flag'))
            print('副标题已挂 VIP 花字 effectStyle id=%s' % new_style['effectStyle']['id'])
        t['content'] = json.dumps(c, ensure_ascii=False)

    # 4. 把花字 effect material 克隆进封面 mini-draft, 并替换 segment 的 refs
    new_id = str(uuid.uuid4()).upper()
    clone = copy.deepcopy(sample_eff)
    clone['id'] = new_id
    d['materials']['effects'].append(clone)
    print('克隆花字 material 新 id=%s' % new_id)

    replaced = 0
    for tr in d['tracks']:
        if tr['type'] != 'text':
            continue
        for seg in tr['segments']:
            if seg['material_id'] != VIP_TARGET:
                continue
            refs = seg.get('extra_material_refs') or []
            new_refs = [new_id if r.startswith(OLD_EFFECT_PREFIX) else r for r in refs]
            replaced += sum(1 for a, b in zip(refs, new_refs) if a != b)
            seg['extra_material_refs'] = new_refs
    print('segment refs 替换数: %d' % replaced)
    assert replaced >= 1, '未替换到任何 refs, 检查 OLD_EFFECT_PREFIX'

    # 5. 校验: 副标题 content 可解析且花字生效, 克隆 material 已在 effects 里
    c_check = json.loads(texts[VIP_TARGET]['content'])
    assert c_check['styles'][0]['effectStyle']['id'] == VIP_FLOWER_RES
    assert any(e['id'] == new_id for e in d['materials']['effects'])
    print('校验通过')

    if not apply:
        print('== dry-run, 未写入 ==')
        return
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = CONTENT + '.pre_coverfix_%s.bak' % ts
    shutil.copy2(CONTENT, bak)
    print('备份:', bak)
    with open(CONTENT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    json.load(open(CONTENT, encoding='utf-8'))            # 回读校验
    print('已写入并回读校验成功')


if __name__ == '__main__':
    main('--apply' in sys.argv)
