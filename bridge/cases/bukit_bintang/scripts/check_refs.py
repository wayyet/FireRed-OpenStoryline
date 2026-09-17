import sys; sys.stdout.reconfigure(encoding='utf-8')
import json

draft_dir = r'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\吉隆坡武吉免登_纯视频'
with open(f'{draft_dir}\\draft_content.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

vtrack = next(t for t in d['tracks'] if t['type'] == 'video')
print('片段 extra_material_refs 详情：')
for i, seg in enumerate(vtrack['segments']):
    refs = seg.get('extra_material_refs', [])
    print(f'  seg[{i}] id={seg["id"][:8]} refs({len(refs)}): {refs}')
print(f'\n总 materials.transitions: {len(d["materials"].get("transitions",[]))}')
print(f'总 materials.video_effects: {len(d["materials"].get("video_effects",[]))}')
