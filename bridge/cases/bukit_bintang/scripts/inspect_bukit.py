import sys; sys.stdout.reconfigure(encoding='utf-8')
import json

draft_dir = r'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\吉隆坡武吉免登_纯视频'
with open(f'{draft_dir}\\draft_content.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print('=== 基本信息 ===')
print(f"画幅: {d.get('width','?')}x{d.get('height','?')}")
print(f"总时长(微秒): {d.get('duration','?')}")
print(f"总时长(秒): {d.get('duration',0)/1000000:.3f}")

vtracks = [t for t in d.get('tracks',[]) if t.get('type')=='video']
print(f"\n视频轨数: {len(vtracks)}")
for t in vtracks:
    print(f"  轨 {t.get('track_index')} [{t.get('id','?')}] clips={len(t.get('segments',[]))}")
    for seg in t.get('segments',[]):
        print(f"    clip_id={seg.get('id','?')} duration={seg.get('duration','?')}ms target_timerange={seg.get('target_timerange','?')}")

stracks = [t for t in d.get('tracks',[]) if t.get('type')=='text']
print(f"\n字幕轨数: {len(stracks)}")
for t in stracks:
    print(f"  轨 {t.get('track_index')} clips={len(t.get('segments',[]))}")
    for seg in t.get('segments',[]):
        print(f"    text={seg.get('content','?')[:30]}")

trans = d.get('materials',{}).get('transitions',[])
print(f"\n已有转场数: {len(trans)}")
for t in trans:
    print(f"  {t.get('name','?')} id={t.get('id','?')} duration={t.get('duration','?')}ms")

effs = d.get('materials',{}).get('video_effects',[])
print(f"\n已有特效数: {len(effs)}")
for e in effs:
    print(f"  {e.get('name','?')} id={e.get('id','?')}")

etracks = [t for t in d.get('tracks',[]) if t.get('type')=='effect']
print(f"\n特效轨数: {len(etracks)}")
for t in etracks:
    print(f"  轨 {t.get('track_index')} [{t.get('id','?')}] segs={len(t.get('segments',[]))}")
    for seg in t.get('segments',[]):
        print(f"    seg_id={seg.get('id','?')} mat_id={seg.get('material_id','?')} timerange={seg.get('target_timerange','?')}")

print('\n=== 全部轨道 ===')
for t in d.get('tracks',[]):
    print(f"  type={t.get('type')} track_index={t.get('track_index')} id={t.get('id','?')} segs={len(t.get('segments',[]))}")
