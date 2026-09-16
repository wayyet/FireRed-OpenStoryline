---
name: jianying-draft-edit
description: 对已有的剪映 (JianYing Pro) 5.9 草稿做"就地"二次编辑与优化——变速到目标总长、删减重排镜头、看画面挑镜头剔瑕疵、注入主/副标题文字。做法是直接改 draft_info.json / draft_content.json 双 JSON，只动目标轨，不破坏已调好的内容，比 load_template 全量往返更安全。适用于"编辑剪映草稿""把视频变速压到 XX 秒""删掉某些镜头并重排""剔除穿帮/游客入镜的片段""给视频加标题文字""优化剪映成片"等场景。触发词：编辑剪映草稿、剪映变速、剪映就地编辑、剪映删减重排、剪映挑镜头、剪映加标题、jianying draft edit。
---

# 就地编辑 / 优化剪映草稿

对**已存在**的剪映 5.9 草稿做二次编辑（变速、删减、重排、加标题）。核心原则：
**直接改 JSON，只动目标轨道，不碰已调好的内容**——比 `load_template` 全量往返更安全。

> 适用前提：草稿**已经存在**。若是从零把素材/时间线生成草稿，请改用 `openstoryline-to-jianying`
> 或底层库 `jianying-editor`，不要用本 skill。

## 关键路径

- 剪映**草稿**目录：`C:\Users\wayye\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>\`
  - `draft_info.json`、`draft_content.json`：草稿内容（剪映 5.9 **两个都读**，内容几乎一致，差异在微秒级舍入）
  - `draft_meta_info.json`：本草稿的元信息（含 `tm_duration`）
  - 草稿根目录的 `root_meta_info.json`：草稿箱索引（`all_draft_store` 数组，每项有 `tm_duration`）
- 剪映**程序**目录：`D:\Documents\kuaishou\JianyingPro\5.9.0.11632\JianyingPro.exe`（不是草稿目录，剪映不从这里列草稿）
- 运行库的解释器：`D:\Documents\kuaishou\venv\Scripts\python.exe`
- 依赖来源：`.claude/skills/jianying-editor/scripts`（`jy_wrapper` / `pyJianYingDraft`）
- 系统 ffmpeg（venv 未装 imageio_ffmpeg）：`C:\Users\wayye\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe`

## 黄金法则（每次编辑必守）

1. **先快照**：`shutil.copytree` 把整个草稿目录复制到 scratchpad，任一步出错可整目录回退。
2. **改前彻底退出剪映**：若剪映正开着该草稿，退出时可能把内存里的旧版**回写覆盖**你的改动。
   改前/改后都要彻底退出再重启。**只读检测、不强杀进程**（强杀可能丢用户正在编辑的内容）：
   ```powershell
   Get-Process JianyingPro -ErrorAction SilentlyContinue
   ```
3. **双 JSON 同步**：`draft_info.json` 和 `draft_content.json` **必须同步改**，内容保持一致。
4. **更新时长索引**：改完同步更新 `draft_meta_info.json` 与 `root_meta_info.json` 里该草稿的
   `tm_duration`（否则草稿箱缩略图显示旧时长 / 00:00）。顶层 `duration` 也要设为新总长。
5. **改完验证**：用 `load_template` 只读解析不抛异常且 `duration` 正确（见末尾"验证"）。

所有时间单位为**微秒**（剪映内部单位）。

## 四类编辑操作

### A. 变速到目标总长 T（微秒）

把若干视频段整体变速，使总时长精确等于 T：

- 每段目标时长：`target_dur_i = round(T * src_dur_i / Σ src_dur)`，**最后一段吸收舍入余数**保证总和精确等于 T。
- 每段速度：`speed_i = src_dur_i / target_dur_i`（与时长**严格自洽**，否则剪映渲染异常）。
- 同步改这些字段：
  - `segment.target_timerange.duration = target_dur_i`
  - `segment.speed = speed_i`
  - 该段 `extra_material_refs` 指向的 `materials.speeds[].speed = speed_i`
  - 按顺序重算每段 `segment.target_timerange.start`（前一段 start + duration 累加）
  - 顶层 `duration = T`
- **若一个 speed material 被多段共用**：先复制出独立副本再分别改，避免互相污染。

### B. 删减 + 重排镜头

- 直接重排 video track 的 `segments` 数组顺序、删掉不要的段，**其余字段原样保留**。
- 重排/删减后，按 A 的规则重设每段 `speed` / `target_timerange.duration` / `start`，并更新顶层 `duration`。
- 被删段如有独占的 material 引用，可一并从 `materials` 清理（非必须，悬空不引用不影响渲染）。

### C. 看画面挑镜头（剔瑕疵）

用抽帧 + 多模态读图判断每段"出片度"，剔除游客入镜、梯子/穿帮、糊片等瑕疵段：

```powershell
$ff = "C:\Users\wayye\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
& $ff -ss <中点秒> -i <clip.mp4> -frames:v 1 -vf scale=420:-1 out.jpg
```

- 取每段**中点**抽一帧（避免转场首尾帧），缩到 420 宽即可。
- 把抽出的 jpg 交给多模态读图，逐段判断保留/剔除，再用 B 做删减重排。

### D. 注入主 / 副标题文字

用库**保证结构正确**，但只"搬运"不全量往返：

1. 生成只含文字的**临时草稿**（到 scratchpad 临时目录）：
   ```python
   proj = JyProject(name, width=1080, height=1920,        # 竖版必须显式传 1080x1920（默认是横版 1920x1080）
                    drafts_root=<scratchpad临时目录>, overwrite=True)
   proj.add_text_simple(text, start, dur, track_name,
                        style=TextStyle(size, bold, color, align=1),
                        border=TextBorder(...),
                        clip_settings=ClipSettings(transform_y=...))   # +上 / -下；字幕默认 -0.8 在底部
   ```
   - **主标题、副标题必须放不同 `track_name`**：同轨时间重叠会抛 `SegmentOverlap`。
2. 从临时草稿提取 `materials.texts`（N 个）+ N 条 text track，注入真实草稿的**两个 JSON**：
   - text material 追加进 `materials.texts`
   - text track 追加进 `tracks`，并设 `render_index` **高于视频**（视频 `render_index` 可能为 `None`，按 0 处理）
3. **清空每个 text segment 的 `extra_material_refs = []`**：无动画/气泡/花字时它指向不存在的 material（悬空），
   清空后纯文字照常渲染，避免剪映报错。

## 运行库的解释器约定

```powershell
$env:PYTHONIOENCODING = "utf-8"        # 防中文乱码
D:\Documents\kuaishou\venv\Scripts\python.exe <你的脚本>.py
```

脚本里 import 顺序**很重要**：

```python
import sys
sys.path.insert(0, r"D:\Documents\kuaishou\.claude\skills\jianying-editor\scripts")
import jy_wrapper                       # 必须先 import 它，触发 setup_env() 注册 vendor 路径
from pyJianYingDraft import (           # 再 import，否则 ModuleNotFoundError
    JyProject, TextStyle, TextBorder, ClipSettings,
)
```

## 验证

```python
from pyJianYingDraft import DraftFolder
DraftFolder(r"C:\Users\wayye\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft") \
    .load_template("<草稿名>")          # 只读解析不抛异常 + duration 正确 = 结构兼容、剪映能开
```

打开 / 重启剪映 → 草稿箱找到该草稿 → 时间轴变化符合预期、能正常播放导出。

## 已知坑

- **剪映回写覆盖**：改文件时若剪映正开着该草稿，退出时可能把内存旧版回写盖掉你的改动——改前/改后都彻底退出再重启；不强杀进程。
- **双 JSON 不同步**：只改一个文件会导致剪映读到不一致内容；务必两个一起改。
- **tm_duration 不更新**：草稿箱缩略图显示旧时长或 00:00，但打开草稿以 `draft_info.json` 为准、内容完整。
- **speed 与 duration 不自洽**：剪映渲染异常 / 卡顿；`speed_i = src_dur_i / target_dur_i` 必须严格成立。
- **共用 speed material**：多段共用同一个 `materials.speeds[]` 时直接改会互相污染，先复制独立副本。
- **text segment 悬空 ref**：不清空 `extra_material_refs` 会指向不存在的 material，剪映报错。

参考记忆：`jianying-draft-edit-inplace`、`openstoryline-to-jianying-bridge`。
