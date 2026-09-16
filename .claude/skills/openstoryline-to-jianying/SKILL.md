---
name: openstoryline-to-jianying
description: 把 OpenStoryline (FireRed-OpenStoryline) 某个会话生成的视频草稿（plan_timeline_pro 时间线编排）重建为剪映 (JianYing Pro) 草稿，写入剪映草稿目录，便于在剪映里二次编辑。默认自动选最新且含有效时间线的会话，也可指定会话id；尽力重建视频/字幕/配音/BGM 四轨。适用于"把 OpenStoryline 的草稿导入剪映""导入到剪映""把生成的视频导进剪映""OpenStoryline 转剪映草稿"等场景。触发词：导入剪映、OpenStoryline 转剪映、导入到剪映、剪映草稿、storyline to jianying。
---

# 把 OpenStoryline 视频草稿导入剪映

OpenStoryline 默认只把成片渲染成 MP4，**不生成剪映草稿**。本 skill 读取某个会话的时间线编排
`plan_timeline_pro_*.json`，用 jianying-editor (JyProject) 把它重建成一个剪映草稿写进草稿目录，
之后在剪映草稿箱即可打开二次编辑。

> ⚠️ **本机真实环境已修正（2026-07 实测，「广州永华艺术馆」导入验证通过）**：
> 早期文档写的是 `D:\…` 盘、用户名 `wayye`、以及一个已删除的根 `venv`，均已过时。
> **真实值是 `E:\…` 盘、用户名 `wayyet`、运行环境改用系统 Python 3.13 + 隔离依赖目录**。
> 下文命令按真实环境编写，可直接照抄执行。相关记忆：`kuaishou-actual-paths`、`kuaishou-venv-broken-py313`。

## 关键路径（本机真实值）

- OpenStoryline 产物根：`E:\Documents\kuaishou\FireRed-OpenStoryline\outputs\<会话id>\`
  - 时间线编排：`<会话id>\plan_timeline_pro\plan_timeline_pro_*.json`（一个会话可能有多个，取**最新修改**的）
  - 切片缓存：plan 里每段的 `source_path`（指向 `.storyline\.server_cache\...\split_shots_*\clip_*.mp4`）
- 剪映**程序**目录：`E:\Documents\kuaishou\JianyingPro\5.9.0.11632\JianyingPro.exe`（不是草稿目录，剪映不从这里列草稿）
- 剪映**草稿**目录：`C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft`
  （草稿写到这里，剪映启动时读 `root_meta_info.json` 列出草稿；草稿目录由 `expanduser` 自动解析到 `wayyet`，脚本无需硬编码）
- 转换脚本：`E:\Documents\kuaishou\.claude\skills\openstoryline-to-jianying\scripts\build_draft.py`
  - ⚠️ 脚本内 `DEFAULT_OUTPUTS_ROOT` 仍写死为 **D 盘**，运行时**必须**用 `--outputs-root` 覆盖成 E 盘，否则找不到会话。
- 依赖来源：兄弟 skill `jianying-editor`（提供 `JyProject` 及 vendor 里的 `pyJianYingDraft`）。
  `build_draft.py` 会**自动定位** `jianying-editor\scripts` 并注入 `sys.path`，`jy_wrapper.setup_env()` 再注入 vendor 的 `pyJianYingDraft`，这两者**无需**手动加进 `PYTHONPATH`。
- 运行环境：**系统 Python 3.13**（`C:\Program Files\Python313\python.exe`）。
  ⚠️ 旧文档写的 `E:\Documents\kuaishou\venv` **已于 2026-07-04 删除**，不要再用；依赖改用下面「环境准备」的隔离目录方案。

## 重建范围（尽力而为）

| 轨道 | 处理方式 |
| --- | --- |
| video | 确定性重建：按 `timeline_window` 落点拼接，`source_window` 决定源内截取，缺失切片跳过并告警 |
| subtitles | 确定性重建：用 `text` + `timeline_window`（无 duration 时取 `end-start`） |
| voiceover | 尽力：检测到 `source_path` 音频文件就加，字段不符/文件缺失则跳过并告警 |
| bgm | 尽力：同上 |

时间换算：所有时间一律以 `毫秒 * 1000` 的**整数微秒**传入（`safe_tim()` 把 int 当微秒）。

## 环境准备（根 venv 已删 → 系统 Python 3.13 + 隔离依赖）

根 `venv` 已删除，建草稿只需**纯 Python 依赖**（不需要 numpy/cv2/pillow）。用 `pip install --target` 装进一个
**隔离目录**（创建一次即可复用，无需每次重装），运行时用 `PYTHONPATH` 注入。

必需依赖：`pymediainfo`（带 bundled `MediaInfo.dll`）、`uiautomation`、`comtypes`、`typing_extensions`。
> 为什么 `uiautomation/comtypes` 也要装：Windows 下 `import pyJianYingDraft` 会连带
> `jianying_controller → uiautomation → comtypes`，缺一即 ImportError。

```powershell
# 编码兜底（每个新终端都设一次，防中文乱码）
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$py   = "C:\Program Files\Python313\python.exe"   # 根 venv 已删，用系统 3.13
$deps = "E:\Documents\kuaishou\.jydeps313"        # 隔离依赖目录，创建一次可复用

# 只在缺失时安装（已装过则跳过）
if (-not (Test-Path (Join-Path $deps 'pymediainfo'))) {
  & $py -m pip install --target $deps pymediainfo uiautomation comtypes typing_extensions
}

# 自检：确认 pymediainfo 的 bundled DLL 可用（返回 True 才算 OK）
$env:PYTHONPATH = $deps
& $py -c "from pymediainfo import MediaInfo; print('can_parse:', MediaInfo.can_parse())"
```

## 会话定位（同名关键词可能命中多个会话）

同一主题词可能匹配到**多个会话**，其中只有**含有效 `plan_timeline_pro` 时间线**的那个能重建。
先筛出候选，再挑「有时间线=True」且主题正确的那个：

```powershell
$outputsRoot = "E:\Documents\kuaishou\FireRed-OpenStoryline\outputs"
$kw = "永华"   # 目标主题关键词

Get-ChildItem $outputsRoot -Directory | ForEach-Object {
  $ss = Join-Path $_.FullName 'session_state.json'
  if ((Test-Path $ss) -and (Select-String -LiteralPath $ss -Pattern $kw -Encoding utf8 -Quiet)) {
    $hasTL = Test-Path (Join-Path $_.FullName 'plan_timeline_pro\plan_timeline_pro_*.json')
    "{0}  有时间线={1}" -f $_.Name, $hasTL
  }
}
```

- 只选「有时间线=True」的会话。若仍有多个，读最新时间线首条字幕 `text` 核对主题
  （如「广州永华艺术馆」会话首句是「在老广州的骑楼街背后」）。
- **先确认切片是否还在**：老会话的 `source_path` 可能指向已删除的旧路径（如 C 盘 Downloads 或已清空的
  `.storyline` 缓存）。当天新生成的会话切片一般齐全；跨天老会话务必先核对，缺失的切片会被跳过。

```powershell
# 核对目标会话每段切片是否存在（OK / MISS）
$sid = "c8e9f76277a24b72bcce15369c096b4f"
$env:PYTHONPATH = $deps
& $py -c @"
import json, glob, os
base = r'$outputsRoot\$sid'
f = max(glob.glob(os.path.join(base,'plan_timeline_pro','plan_timeline_pro_*.json')), key=os.path.getmtime)
d = json.load(open(f, encoding='utf-8'))
for v in d['payload']['tracks']['video']:
    sp = v['source_path']
    print(('OK  ' if os.path.exists(sp) else 'MISS'), v.get('clip_id'), sp)
"@
```

## 运行步骤（PowerShell，本次实测通过的完整流程）

```powershell
# ---- 0. 编码 + 关键路径（本机真实值）----
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$py          = "C:\Program Files\Python313\python.exe"
$script      = "E:\Documents\kuaishou\.claude\skills\openstoryline-to-jianying\scripts\build_draft.py"
$outputsRoot = "E:\Documents\kuaishou\FireRed-OpenStoryline\outputs"
$deps        = "E:\Documents\kuaishou\.jydeps313"

# ---- 1. 隔离依赖只需补进 PYTHONPATH（jianying-editor\scripts 与 vendor 由脚本自动注入，勿手动加）----
$env:PYTHONPATH = $deps

# ---- 2. 构建草稿：指定会话 + 可读草稿名 + 覆盖 outputs 根（不覆盖会走 D 盘找不到会话）----
& $py $script `
  --session c8e9f76277a24b72bcce15369c096b4f `
  --name "广州永华艺术馆" `
  --outputs-root $outputsRoot

# ---- 其它用法 ----
# 自动选最新且 video 非空的会话（省略 --session）：
# & $py $script --outputs-root $outputsRoot
# 只重建视频轨：
# & $py $script --session <id> --outputs-root $outputsRoot --only-video
```

脚本参数：
- `--session <会话id>`：指定会话；省略则自动挑 outputs 下**最新且 video 非空**的会话
- `--name <草稿名>`：自定义草稿名；省略则用 `OpenStoryline_<会话id前8位>`
- `--outputs-root <路径>`：覆盖内置的 D 盘默认值（**本机必传**，指向 E 盘）
- `--only-video`：只重建视频轨

## 让草稿在剪映里可见（本 skill 只生成草稿，不操作剪映进程）

草稿写入后，检测剪映是否在运行并给出提示（**只读检测，不强制关闭/重启**，避免丢失你正在编辑的内容）：

```powershell
if (Get-Process JianyingPro -ErrorAction SilentlyContinue) {
  Write-Host "剪映正在运行：草稿箱在启动时读取，请【重启剪映】后才能看到新草稿。"
} else {
  Write-Host "剪映未运行：下次启动剪映，在草稿箱即可看到新草稿。"
  # 如需打开剪映可手动执行：
  # Start-Process "E:\Documents\kuaishou\JianyingPro\5.9.0.11632\JianyingPro.exe"
}
```

## 验收

- 脚本结尾打印 `完成`，`视频片段 N/N` 全部成功（缺失切片会单独列出），并给出 `草稿目录` 绝对路径。
- 在 `...\com.lveditor.draft\<草稿名>\` 下存在 `draft_info.json`（草稿内容以此为准）。

```powershell
$D = "C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\广州永华艺术馆"
Get-Item "$D\draft_info.json" | Select-Object FullName, @{n='KB';e={[math]::Round($_.Length/1KB,1)}}
```

- 打开/重启剪映 → 草稿箱出现该草稿，可正常打开编辑。

**参考：本次「广州永华艺术馆」导入结果**（会话 `c8e9f762…`，当天生成，切片完整）：

| 轨道 | 结果 |
| --- | --- |
| 视频 | 6/6 全部拼接成功 |
| 字幕 | 18/18（「在老广州的骑楼街背后…这一趟真的值了」）|
| 配音 | 0（该会话时间线本无配音轨）|
| BGM | 0（该会话时间线本无 BGM 轨）|

分辨率 1080×1920 竖屏，时间线总长约 50.69s，`draft_info.json` 约 83 KB。

## 已知坑

- **路径盘符/用户名漂移**：早期文档写 `D:\…\wayye`，本机真实是 `E:\…\wayyet`。跑脚本必传
  `--outputs-root E:\…\outputs`（脚本内 `DEFAULT_OUTPUTS_ROOT` 仍是 D 盘），否则找不到会话。
  草稿目录靠 `expanduser` 自动解析到 `wayyet`，无需改脚本。
- **根 venv 已删（2026-07-04）**：旧文档的 `E:\Documents\kuaishou\venv` 不存在。改用系统 Python 3.13
  + 隔离依赖目录（`pip install --target`），运行时 `PYTHONPATH` 只补该目录即可。
- **依赖不止 pymediainfo**：Windows 下 `import pyJianYingDraft` 会连带 `uiautomation → comtypes`，
  务必一起装；`pymediainfo` 需带 bundled `MediaInfo.dll`，装完先 `MediaInfo.can_parse()` 自检。
- **同名关键词命中多个会话**：只有含有效 `plan_timeline_pro` 的会话能重建；先筛「有时间线=True」再核对首句字幕。
- **老会话切片缺失**：跨天老会话的 `source_path` 可能指向已删除路径（旧盘符 / 已清空的 `.storyline` 缓存），
  这些切片会被跳过，草稿只保留可用片段与字幕；导入前先按上面「会话定位」核对 OK/MISS。
- **剪映正开着时看不到新草稿**：草稿列表在启动时读 `root_meta_info.json`，需**重启剪映**。
- **缩略图偶尔显示 `00:00`**：索引里 `tm_duration` 写成 0，但打开草稿内容完整，以 `draft_info.json` 为准。
