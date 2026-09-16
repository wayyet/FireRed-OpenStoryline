---
name: jianying-translate-subtitles
description: 把"已存在"的剪映 (JianYing Pro) 5.9 草稿的中文字幕翻译改写成口语化英文字幕并整轨替换——先只读侦查现有字幕与分镜、抽帧核对画面、上网核实英文官方名称，再写单行不超 38 字符的英文短句，用 inject_subtitles.py --replace 对齐分镜边界替换注入；可选同轮删除中文 TTS 配音轨（按 textReading 路径识别，不误伤 BGM）、把字幕字号双字段统一到定稿值。流程固定为"侦查→抽帧→核实→写英文文案→确认→dry-run→替换注入→校验"，绝不先写后报。适用于"中文字幕翻译成英文""英文口语化字幕""字幕换成英文""双语视频改英文版""删除中文配音"等场景。触发词：字幕翻译英文、英文字幕、translate subtitles、中文字幕换英文、剪映英文字幕、删中文配音。
---

# 把剪映草稿的中文字幕翻译成口语化英文字幕（替换式）

对**已存在**且**已有中文字幕轨**的剪映 5.9 草稿：读懂旧字幕与分镜 → 抽帧核对画面 →
核实英文官方名称/事实 → 写口语化英文短句 → `--replace` 整轨替换注入。本 skill 是
`jianying-add-subtitles` 的**翻译替换变体**——继承它的全部黄金法则与脚本，并把
2026-07-11 会话「吉隆坡柏威年广场中文字幕→英文」验证过的完整流程沉淀为可复用工具
（实测：7 分镜 35.167s，7 条英文字幕逐镜对齐替换，同轮删中文 TTS 配音轨 + 字号统一 10，
load_template 校验通过）。

> 只做"英文文案 + 替换注入 +（可选）删配音/调字号"。要 VIP 文字动画/花字请随后跑
> `jianying-inject-text-fx`；要英文 AI 配音请跑 `jianying-inject-tts-sticker`。
> 本文件内的路径是**真实路径**（`wayyet` / `e:` 盘）。

## 关键路径（真实，勿用旧文档路径）

- 剪映草稿目录：`C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>\`
- 解释器：系统 Python 3.13 `C:\Program Files\Python313\python.exe`（根 venv 已删除，勿用）
- 复用脚本（不要复制，直接引用）：
  - 侦查/注入：`e:\Documents\kuaishou\.claude\skills\jianying-add-subtitles\scripts\`（`recon_draft.py` / `inject_subtitles.py`）
  - 字号统一：`e:\Documents\kuaishou\.claude\skills\jianying-inject-text-fx\scripts\set_fontsize.py`
- 本 skill 脚本：`e:\Documents\kuaishou\.claude\skills\jianying-translate-subtitles\scripts\remove_tts_track.py`（删中文配音轨）

所有时间单位为**微秒**。会话级默认启用 `/chinese-outcome` + `/confirm-me` + `/windows-shell-commands`。

## 黄金法则（继承 jianying-add-subtitles）

1. **剪映进程运行时禁止写入**——每次 `--apply` 前 `Get-Process JianyingPro` + 脚本内 tasklist 双守卫。
2. **备份先行**——每步写入都整目录快照或 `.bak`，回退=覆盖回去。
3. **双 JSON 同步**——content 为真相，写入时 content 全量覆盖 info（顺带修复分叉）。
4. **绝不先写后报**——默认 dry-run，AskUserQuestion 确认后才 `--apply`。
5. **只读操作（侦查/抽帧）可以在剪映开着时做**，写入必须等用户关闭。

## 标准流程（八步）

### ① 前置检查 + ② 只读侦查

同 `jianying-add-subtitles` §①②。侦查重点多三项：
- **现有中文字幕轨**的每条文本与时间轴（这是翻译的源文本，画面语义已在其中）；
- 是否存在**中文 TTS 配音轨**（`type=audio` 多段、与字幕起点对齐）→ 换英文字幕后会中英不一致，⑥ 必须问用户怎么处理；
- 字幕**字号现值**（上一轮定稿值可能与脚本默认 5.0 不同，见 §⑧）。

### ③ 抽帧核对画面

同 `jianying-add-subtitles` §③（刷新 PATH → ffmpeg 按"抽帧建议"逐镜抽帧 → Read 逐张看）。
翻译也不可跳过：英文文案要贴画面，且能发现中文旧字幕与画面的偏差。

### ④ 核实英文名称与事实

WebSearch 至少 2 轮：`<地标英文名> + 官方`、`<地标> + 卖点/活动 英文`。
翻译场景的重点是**专有名词的官方英文拼法**（如"武吉加里尔柏威年"= Pavilion Bukit Jalil）
与可引用的事实点（如金鸡喷泉获 Malaysia Book of Records）。保留来源链接，汇报时附上。

### ⑤ 写口语化英文文案（本 skill 核心约束）

- **条数 == 分镜数**，时间自动继承分镜边界（总长天然 ≤ 原视频长度）。
- **单行 ≤ 38 个 ASCII 字符（含空格标点）**：`subs.txt` 一行一条且 `strip()`，
  **不支持字幕内 `\n` 换行**；中文单行 15~16 字的版面宽度 ≈ 英文 32~38 字符（英文字形约半个汉字宽）。
- **不是逐字直译**：像美区博主说话——首条钩子（地点+惊叹点），末条地名全称 + CTA（don't miss it）；
  可用 `+`/`=`/`—` 压缩句式（Blossoms + lanterns = Chinese vibes!）。
- 专有名词用 ④ 核实过的官方英文名；事实性表述要有来源，不编造。
- 写入 scratchpad 的 `subs_en.txt`：**UTF-8、一行一条**（文案永远走文件传参）。

### ⑥ 确认（/confirm-me）

AskUserQuestion 展示中英对照表（时间轴 | 原中文 | 英文 | 画面）+ 三个连带决策：
1. 文案是否确认（并提醒：写入前需关闭剪映）；
2. **中文配音轨怎么处理**：保留（双语风）/ 删除（只留 BGM）/ 之后换英文 TTS；
3. **字号**：脚本默认 5.0 还是沿用本草稿上一轮定稿值（本项目 9:16 定稿 10）。

### ⑦ 先删配音（若用户选删）、后替换字幕

```powershell
$py = 'C:\Program Files\Python313\python.exe'
$me = 'e:\Documents\kuaishou\.claude\skills\jianying-translate-subtitles\scripts'
$sk = 'e:\Documents\kuaishou\.claude\skills\jianying-add-subtitles\scripts'
# 1) 删配音轨：dry-run 看清命中目标，再 --apply
& $py "$me\remove_tts_track.py" --draft '<草稿名>' --work-dir '<scratchpad>'
& $py "$me\remove_tts_track.py" --draft '<草稿名>' --work-dir '<scratchpad>' --apply
# 2) 替换字幕：--replace 摘旧轨再注入
& $py "$sk\inject_subtitles.py" --draft '<草稿名>' --subs-file '<scratchpad>\subs_en.txt' --work-dir '<scratchpad>'
& $py "$sk\inject_subtitles.py" --draft '<草稿名>' --subs-file '<scratchpad>\subs_en.txt' --work-dir '<scratchpad>' --replace --apply
```

每次 `--apply` 前先确认剪映已关闭。顺序建议先删配音后注字幕，让 inject 的
load_template 校验 + 双 JSON 同步收尾兜底。

### ⑧ 字号统一（若用户选了非默认值）

走 `jianying-inject-text-fx` §10 的**强制流程**：复制 `set_fontsize.py` 到 scratchpad、
改 `DRAFT`/`TARGET_SIZE` → dry-run（重读现值逐条 diff）→ `--apply`（`.pre_fontsize_*.bak`
备份 + 双 JSON + 写后逐条复核双字段）。注意 `inject_subtitles.py` 注入的字幕
`font_size` 字段缺失（None）、`styles.size=5.0`，统一后两字段都落到目标值。

## 已知坑（2026-07-11 实测教训）

1. **中文 TTS 素材的 type 是 `extract_music` 不是 `text_to_audio`**（本项目 TTS 注入时手写的类型）
   ——删配音轨**不能按 type 识别**，要按素材 `path` 含 `textReading` 识别；BGM 是 `music` 类型不受影响。
2. **`--replace` 只清 `material_animations`，不清 `text_effect` 花字**——旧字幕若挂过花字，
   替换后 materials.effects 里会留下悬空条目（剪映客户端手加的花字还会天然重复 ×2）。
   无引用不影响播放/导出，可顺手清也可留待下轮注入时处理，但要**告知用户**。
3. **换字幕 = 旧动画/花字全部消失**——旧字幕轨的动画随 dead_refs 一并摘除。要重新加动画/花字
   跑 `jianying-inject-text-fx`（历史已用黑名单 [[kuaishou-fx-used-history]] 仍然有效，零复用规则不变）。
4. **subs.txt 不支持字幕内换行**——英文长句不能靠 `\n` 折行，只能压进 38 字符（见 §⑤）。
5. **删配音要连带清附属素材**——segment 的 `extra_material_refs`（speeds/beats/声道映射等）
   散在 materials 各分类，按 id 全表扫清除，否则留悬空引用。
6. **textReading 下的 ogg 文件留在磁盘无害**——只删 JSON 引用即可，实体文件交给 `kuaishou-clean-cache`。
7. **中英不一致要主动暴露**——侦查发现配音/贴纸文字等其他中文元素时，在 ⑥ 一并问用户，不要装看不见。

## 验收与汇报

- 重启剪映 → 草稿底部 `Subtitles` 轨应为英文字幕（目标字号），配音按用户决定呈现。
- 汇报模板：中英对照表 + 样式/字号说明 + 各步备份位置 + 英文名称核实来源链接。
- 升级链路：`jianying-inject-text-fx`（动画/花字）→ `jianying-inject-tts-sticker`（英文配音）→
  `jianying-make-cover`（封面）。
