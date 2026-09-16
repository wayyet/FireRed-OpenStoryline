---
name: jianying-speed-fit-35s
description: 用剪映 (JianYing Pro) 5.9 的常规变速或曲线变速，把"已存在"草稿的视频时间轴压到不超过 35 秒（目标时长可参数化）。做法是直接改 draft_info.json / draft_content.json 双 JSON：常规变速走精确脚本路线（按比例+整帧对齐分配时长，防客户端按帧上取整回弹，总长严格不超过目标）；曲线变速走人机协作路线（客户端手挑样本曲线→克隆缩放，留安全余量）。流程固定为"侦查→试算→确认→备份写入→验证"，绝不先写后报。适用于"视频分镜变速处理不超过35秒""把时间轴压到 35 秒""视频太长了变速压短""常规变速/曲线变速到目标时长"等场景。触发词：变速不超过35秒、时间轴35秒、分镜变速、常规变速、曲线变速、变速压时长、speed fit 35s、jianying speed fit。
---

# 剪映变速压时长（默认 ≤35 秒）

对**已存在**的剪映 5.9 草稿做整体变速，使视频时间轴**不超过目标时长 T**（默认 35 秒）。
本 skill 是 `jianying-draft-edit` 操作 A（变速到目标总长）的**固化专用版**——继承它的全部黄金法则，
并把 2026-07-07 会话「视频分镜变速处理不超过35秒」验证过的完整脚本沉淀为可复用工具
（实测：草稿「吉隆坡柏威年广场」7 个分镜 64.981s → 精确 35.000000s @ ≈1.8566x，剪映正常解析）。

> 只做"变速压时长"这一件事。要删减/重排镜头、加标题请用 `jianying-draft-edit`；
> 本文件内的路径是**真实路径**（`wayyet` / `e:` 盘），旧 skill 文档里的 `wayye` / `D:` 盘已过期。

## 关键路径（真实，勿用旧文档路径）

- 剪映草稿目录：`C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>\`
  - `draft_info.json` / `draft_content.json`：草稿内容双 JSON（**两个都读、两个同步写**）
  - `draft_meta_info.json`：本草稿元信息（`tm_duration`）
  - 草稿根目录 `root_meta_info.json`：草稿箱索引（`all_draft_store[].tm_duration`）
- 解释器：系统 Python 3.13 `C:\Program Files\Python313\python.exe`（根 venv 已删除，勿用）
- 依赖：`e:\Documents\kuaishou\.jydeps313` + `e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts`（`jy_wrapper` / `pyJianYingDraft`）
- 本 skill 脚本：`e:\Documents\kuaishou\.claude\skills\jianying-speed-fit-35s\scripts\`

所有时间单位为**微秒**（剪映内部单位）；T = 35 秒 = 35_000_000 微秒。

## 决策树（先判断再动手）

1. **视频轨总长已 ≤ T** → 不动文件，直接汇报"已达标"。
2. **超长且整体速度 ≤ 3x 能达标** → **常规变速（默认推荐）**：总长可精确等于 T，结构简单可脚本化。
3. **需要 >3x 才能达标** → 快进感太强，先用 AskUserQuestion 和用户确认是否改走
   "删减镜头（`jianying-draft-edit` 操作 B/C）+ 温和变速"组合；>100x 是剪映硬上限，直接不可行。
4. **用户点名要节奏感/忽快忽慢** → **曲线变速（人机协作路线）**：总长只能≈T（留余量），见下文专节。
5. 分镜里**已有曲线变速**（speed material 的 `mode != 0` 或 `curve_speed` 非空）→ 脚本会中止；
   请用户先在客户端还原常规变速，或整体走曲线路线。

## 标准流程（五步，绝不先写后报）

### ① 前置检查

```powershell
# 剪映进程只读检测（不强杀）；列出草稿目录锁定目标草稿
Get-Process JianyingPro -ErrorAction SilentlyContinue | Select-Object Id, ProcessName
Get-ChildItem 'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft' -Directory | Sort-Object LastWriteTime -Descending | Select-Object Name, LastWriteTime -First 8
```

草稿名以用户指定为准；未指定时取最近修改的草稿，**报给用户核对**。

### ② 只读侦查

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$py = 'C:\Program Files\Python313\python.exe'
$sk = 'e:\Documents\kuaishou\.claude\skills\jianying-speed-fit-35s\scripts'
& $py "$sk\inspect_speed.py" --draft '<草稿名>'
```

看清：双 JSON 是否分叉（剪映 8.9 只写 content 的坑）、视频轨段数与源时长、speed material
是否共用/是否已带曲线、非视频轨（字幕/贴纸/配音）末端位置。

### ③ 只读试算

```powershell
& $py "$sk\plan_speed.py" --draft '<草稿名>' --target-sec 35
```

输出方案表（每段 源时长→新时长@速度、新起点）、速度区间、非视频轨悬出预警，以及
`--expect-src-total` 守卫值（写入时校验草稿没被中途改动）。

### ④ 确认（/confirm-me）

用 AskUserQuestion 出三选一：**常规变速执行（推荐）** / **改用曲线变速** / **先别动文件**。
方案表必须先展示给用户再问。

### ⑤ 备份写入 + 验证

```powershell
# 外层先挡剪映进程，再执行（备份目录用当前会话 scratchpad）
if (Get-Process JianyingPro -ErrorAction SilentlyContinue) { Write-Output '剪映正在运行，中止写入' } else { & $py "$sk\apply_speed.py" --draft '<草稿名>' --target-sec 35 --backup-dir '<scratchpad目录>' --expect-src-total <试算给的值> }
& $py "$sk\validate_speed.py" --draft '<草稿名>' --target-sec 35
```

`apply_speed.py` 内置：整目录快照 + `root_meta_info.json` 备份 → 改 content → 双 JSON 全量同步覆盖
（顺手修复 8.9 分叉）→ 更新 `draft_meta_info.json` / `root_meta_info.json` 的 `tm_duration`。
`validate_speed.py` 用 `pyJianYingDraft.load_template` 只读解析当冒烟测试 + 断言 duration。
最后提示用户重启剪映，确认时间轴显示 T、速度标签正确、播放正常。

## 常规变速的核心公式（脚本已内置，改动时必守）

- **帧对齐分配（默认）**：总帧数预算 `N = floor(T * fps / 1e6)`，每段帧数
  `f_i = round(N * src_dur_i / Σ src_dur)`，**最后一段吸收帧数余数**；
  每段新时长 `target_dur_i = round(f_i * 1e6 / fps)`，总和严格 ≤ T。
  为什么必须帧对齐：写入非整帧时长后，剪映客户端打开草稿会把每段按帧**上取整**回写，
  总长回弹超标（实测：7 段精确 35.000000s 被客户端弹成 35.167s）。
  `--no-frame-align` 可切回"总和精确 == T"的旧模式，但扛不住客户端往返。
- 每段速度：`speed_i = src_dur_i / target_dur_i`——与时长**严格自洽**，同时写进
  `segment.speed` 和 `extra_material_refs` 指向的 `materials.speeds[].speed`（两处不一致剪映渲染异常）。
- 按顺序重算每段 `target_timerange.start`（累加），顶层 `duration = 视频轨实际末端`。
- speed material 被多段共用时**先克隆独立副本**再改（脚本自动处理）；
  段上没有 speed material 时按 pyJianYingDraft 固定速度结构补建。

## 曲线变速（人机协作路线）

`pyJianYingDraft` 的 `Speed` 类只支持固定速度（导出 `mode: 0, curve_speed: None`），**库不支持曲线**；
曲线数据落在 `materials.speeds[]` 的 `mode` 与 `curve_speed`（内含速度点列表）字段上，且
**轴上时长 = 源时长 ÷ 曲线平均速度**（由速度点积分决定），所以总长只能≈T。套本项目
"手挑样本再克隆"的成熟套路（同花字/贴纸）：

1. 让用户在剪映客户端对**一个**分镜手动挂目标曲线（如"蒙太奇"），保存退出。
2. 从草稿提取该段的 speed material 样本（`mode` / `curve_speed` 原样拿走）。
3. 克隆到其余分镜；每段实际 `target_timerange.duration` 以**客户端回读值为锚**推算缩放，
   总目标设为 T 的 97%（留 ≈3% 安全余量，保证"不超过"而不是"约等于"）。
4. **末段用常规变速兜底微调**：前 N-1 段挂曲线，最后一段用常规变速吸收全部误差，
   把总长精确凑到 ≤T。
5. 写入/验证与常规路线相同（备份、双 JSON 同步、tm_duration、load_template）。
6. 改完必须在客户端实测播放——曲线的实际渲染时长以剪映为准，偏差超 0.5 秒就回退重调。

## 已知坑

- **剪映回写覆盖**：剪映开着该草稿时改文件，退出时内存旧版会盖掉改动——改前/改后彻底退出；只读检测不强杀。
- **客户端帧回弹**（2026-07-07 实测新坑）：写入非整帧的段时长后，客户端打开草稿会把每段按帧
  **上取整**回写 content（30fps 下每段最多 +33ms，7 段弹了 +167ms 破 35s 上限），同时再次造成双 JSON 分叉。
  对策：默认帧对齐分配（见核心公式）；事后用 `inspect_speed.py` 复查客户端往返后的实际总长。
- **双 JSON 分叉**：剪映 8.9 客户端只写 `draft_content.json`；本 skill 以 content 为基准、写入时两个全量覆盖同步。
- **speed 与时长不自洽**：渲染卡顿异常；`speed_i = src_dur_i / target_dur_i` 必须逐段精确成立。
- **共用 speed material**：直接改会互相污染，必须先克隆（`apply_speed.py` 自动做）。
- **非视频轨悬出**：字幕/贴纸/配音轨末端超过 T 时，视频压短了总时长仍超标——`apply_speed.py`
  默认中止并列出悬出轨道；确需保留时加 `--allow-overhang`（顶层 duration 取真实最大末端）。
  悬出轨道的删减/重排交给 `jianying-inject-text-fx`（字幕）/ `jianying-inject-tts-sticker`（配音贴纸）处理。
- **tm_duration 不更新**：草稿箱缩略图显示旧时长 / 00:00（内容不受影响，但仍必须更新）。
- **旧文档路径过期**：`jianying-draft-edit` 里的 `wayye` / `D:` 盘 / venv 解释器都是旧的，以本文件为准。

## 验收清单

1. ☐ `validate_speed.py` 通过（load_template 不抛异常、duration == T）
2. ☐ 双 JSON 内容一致（validate 脚本会比对）
3. ☐ `draft_meta_info.json` / `root_meta_info.json` 的 `tm_duration` == 新总长
4. ☐ 备份目录存在且可整目录回退
5. ☐ 用户重启剪映后：时间轴显示 ≤35s、每段速度标签正确、播放/导出正常

参考记忆：`kuaishou-actual-paths`、`kuaishou-venv-broken-py313`、`jianying-tts-sticker-inject`（双 JSON 分叉坑）。
