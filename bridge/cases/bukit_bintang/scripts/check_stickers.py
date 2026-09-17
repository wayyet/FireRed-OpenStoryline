import json, sys
sys.stdout.reconfigure(encoding='utf-8')
path = r'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\吉隆坡武吉免登_纯视频\draft_content.json'
with open(path, encoding='utf-8') as f:
    d = json.load(f)

stickers = d['materials'].get('stickers', [])
tracks = [t for t in d.get('tracks', []) if t.get('type') == 'sticker']
print(f'sticker materials: {len(stickers)}')
for s in stickers:
    print(f'  - {s.get("name","")} | rid={s.get("resource_id","")}')
print(f'sticker tracks: {len(tracks)}')
for t in tracks:
    print(f'  track render_index={t.get("render_index","")} segs={len(t.get("segments",[]))}')
    for seg in t.get('segments', []):
        mid = seg.get('material_id', '')
        tr = seg.get('target_timerange', {})
        start = tr.get('start', 0)
        dur = tr.get('duration', 0)
        name = next((s.get('name','') for s in stickers if s.get('id') == mid), mid)
        print(f'    seg material={name[:30]} start={start//1000}ms dur={dur//1000}ms')
