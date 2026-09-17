import json, sys
sys.stdout.reconfigure(encoding='utf-8')
path = r'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\吉隆坡武吉免登_纯视频\draft_content.json'
with open(path, encoding='utf-8') as f:
    d = json.load(f)
tracks = d.get('tracks', [])
print(f"总时长: {d.get('duration',0)//1000}ms")
print(f"总轨数: {len(tracks)}")
print(f"已有音频轨: {any(t.get('type')=='audio' for t in tracks)}")
print(f"已有贴纸轨: {any(t.get('type')=='sticker' for t in tracks)}")
print()
for t in tracks:
    if t.get('type') == 'text':
        segs = t.get('segments', [])
        for s in segs:
            mid = s.get('material_id','')
            tr = s.get('target_timerange', {})
            text_content = ''
            for txt in d['materials'].get('texts', []):
                if txt.get('id') == mid:
                    j = json.loads(txt.get('content','{}'))
                    text_content = j.get('text','')[:25]
                    break
            start = tr.get('start', 0)
            dur = tr.get('duration', 0)
            print(f"字幕: {text_content} | start={start//1000}ms dur={dur//1000}ms")
