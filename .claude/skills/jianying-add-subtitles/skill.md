---
name: jianying-add-subtitles
description: 给"已存在"的剪映 (JianYing Pro) 5.9 视频草稿加逐句口语化字幕——先看懂画面（ffmpeg 逐分镜抽帧）、再上网搜小红书/抖音同主题资料写文案，最后把字幕严格对齐分镜边界注入 draft_content.json / draft_info.json 双 JSON。流程固定为"侦查→抽帧看画面→搜资料→写文案→确认→注入→校验"，脚本默认 dry-run，绝不先写后报。适用于"给剪映草稿加字幕""视频配逐句字幕""写口语化旅游文案并配字幕""参考小红书抖音写字幕文案"等场景。触发词：剪映加字幕、逐句字幕、口语化字幕、旅游文案字幕、字幕对齐分镜、看画面写文案、jianying add subtitles。
---

# 给剪映视频草稿加逐句字幕（口语化文案）

对**已存在**的剪映 5.9 草稿：看懂每个分镜画面 → 上网搜同主题资料 → 写口语化逐句文案 →
时间严格对齐分镜边界注入。本 skill 是 `jianying-draft-edit` 操作 D
（注入文字）的**固化专用版**——继承它的全部黄金法则，并把 2026-07-07 会话
「给剪映视频添加字幕和旅游文案」验证过的完整流程沉淀为可复用工具
（实测：草稿字幕逐镜对齐，load_template 校验通过）。

> 只做"写文案 + 注入纯文字字幕"这一件事。要 VIP 文字动画/花字请随后跑
> `jianying-inject-text-fx`；要 AI 配音请跑 `jianying-inject-tts-sticker`；
> 要改镜头/变速请先用 `jianying-draft-edit` / `jianying-speed-fit-35s`。
> 本文件内的路径是**真实路径**（`wayyet` / `e:` 盘），旧 skill 文档里的 `wayye` / `D:` 盘已过期。

## 关键路径（真实，勿用旧文档路径）

- 剪映草稿目录：`C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>\`
  - `draft_info.json` / `draft_content.json`：草稿内容双 JSON（**content 为真相**，写入时 content 全量覆盖 info）
- 解释器：系统 Python 3.13 `C:\Program Files\Python313\python.exe`（根 venv 已删除，勿用）
- 依赖：`e:\Documents\kuaishou\.jydeps313` + `e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts`（`jy_wrapper` / `pyJianYingDraft`）
- 本 skill 脚本：`e:\Documents\kuaishou\.claude\skills\jianying-add-subtitles\scripts\`
- ffmpeg：winget 版在用户 PATH，旧会话需先刷新 PATH（见 §③）

所有时间单位为**微秒**（剪映内部单位）。

## 黄金法则（继承 jianying-draft-edit）

1. **剪映进程运行时禁止写入**——PowerShell 先查 `Get-Process JianyingPro`，脚本内 `--apply` 还有第二道 tasklist 守卫。
2. **备份先行**——`--apply` 自动整目录快照到 `--work-dir`，回退=整目录覆盖回去。
3. **双 JSON 同步**——只写 content 再全量覆盖 info（顺带修复剪映 8.9"只写 content"的分叉）。
4. **绝不先写后报**——脚本默认 dry-run，AskUserQuestion 确认文案后才 `--apply`。
5. **字幕注入放在变速/删减之后**——字幕对齐的是"当前"分镜边界，先动视频轨再注字幕。

## 标准流程（七步）

### ① 前置检查

```powershell
Get-Process JianyingPro -ErrorAction SilentlyContinue | Select-Object Id, ProcessName
Get-ChildItem 'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft' -Directory | Sort-Object LastWriteTime -Descending | Select-Object Name, LastWriteTime -First 8
```

草稿名以用户指定为准；未指定时取最近修改的草稿，**报给用户核对**。

### ② 只读侦查

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$py = 'C:\Program Files\Python313\python.exe'
$sk = 'e:\Documents\kuaishou\.claude\skills\jianying-add-subtitles\scripts'
& $py "$sk\recon_draft.py" --draft '<草稿名>'
```

看清：双 JSON 是否分叉、视频轨分镜数与边界、**是否已有文字素材**（已有 → 停下问用户是
替换还是保留，替换走 `--replace`）、每个分镜的素材路径与"抽帧建议 -ss 时刻"（源区间中点）。

### ③ 抽帧看懂画面（写文案的前提，不可跳过）

```powershell
# 旧 VS Code 会话 PATH 快照过期，先刷新再找 ffmpeg
$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
$ff = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
# 对每个分镜执行（-ss 用②输出的"抽帧建议"时刻，素材路径也来自②）
& $ff -ss <中点秒> -i '<素材路径>' -frames:v 1 -q:v 3 '<scratchpad>\f<N>.jpg' -y
```

然后用 Read 逐张看图，记下每个分镜"画面里到底有什么"——文案必须贴画面，不写画面里没有的东西。

### ④ 搜主题资料

**到网上小红书或者抖音搜索相关的主题和资料**，用 WebSearch 搜 2 轮以上：`<地点/主题> + 旅游 攻略 小红书`、`<地标名> + 打卡 网红 抖音 vlog`。
提炼可用的事实点（如"全马最大金鸡雕塑""2021 年底开业"），**保留来源链接**，最终汇报时附上。
若 WebSearch 不可用，退路是 ddgs 库直连（见记忆 openstoryline-search-web-topic：裸 requests 会被全拦）。

### ⑤ 写口语化文案

- **条数 == 分镜数**，一条字幕对应一个分镜，时间自动继承分镜边界。
- 口语化短句 10~16 字为宜（竖屏一行放得下），别超 20 字；像和朋友说话，不要书面语。
- 第 1 条要有钩子（地点 + 惊叹点），最后一条点明地点 + 行动召唤（"别错过"）。
- 每条必须贴对应分镜画面（依据③的抽帧）；事实性表述要有④的资料支撑，不编造。
- 写入 scratchpad 的 `subs.txt`：**UTF-8、一行一条**（中文永远走文件传参，防命令行引号/编码坑）。

### ⑥ 确认（/confirm-me）

用 AskUserQuestion 展示完整字幕表（时间轴 | 文案 | 对应画面）+ 样式说明，等用户确认或改文案。
若视频总长超过目标（如 35s 要求），同时问是否先跑 `jianying-speed-fit-35s`（**先变速、后注字幕**）。

### ⑦ dry-run → 注入 → 校验

```powershell
# 先 dry-run（不写任何文件）
& $py "$sk\inject_subtitles.py" --draft '<草稿名>' --subs-file '<scratchpad>\subs.txt' --work-dir '<scratchpad>'
# 通过且用户已确认后，关剪映再 --apply（替换旧字幕加 --replace）
if (Get-Process JianyingPro -ErrorAction SilentlyContinue) { Write-Output '剪映正在运行，中止' } else {
  & $py "$sk\inject_subtitles.py" --draft '<草稿名>' --subs-file '<scratchpad>\subs.txt' --work-dir '<scratchpad>' --apply
}
```

脚本内部：整目录备份 → 临时草稿用 `jy_wrapper.add_text_simple` 生成字幕结构 → 深拷贝进
content（`extra_material_refs` 清空、`render_index` 从 14000 递增、逐段断言时间与分镜一致）→
content 覆盖 info → `load_template` 冒烟校验 + 双 JSON 一致性断言。

## 字幕样式惯例（本项目已验证）

| 项 | 值 | 说明 |
|----|----|------|
| 字号 | `size=5.0` | 本项目字幕惯例，`--size` 可调 |
| 字色/字重 | 白色加粗 | `TextStyle(bold=True, color=(1,1,1))` |
| 描边 | 黑色宽 40 | `TextBorder(color=(0,0,0), width=40.0)` |
| 位置 | 底部居中 | `ClipSettings(transform_y=-0.8)`，`--transform-y` 可调 |
| 对齐 | `align=1` 居中 | — |
| 动画/花字 | 无（纯文字） | 要动画后跑 `jianying-inject-text-fx` |
| 轨道名 | `Subtitles` | `--replace` 按此名摘除旧轨 |

## 已知坑

- **双 JSON 分叉**：剪映 8.9 客户端只写 content——侦查和注入都以 content 为真相，写入时自动覆盖 info 修复。
- **字幕不改总时长**：字幕末端 == 视频末端，`duration`/`tm_duration`/`root_meta_info.json` 都不用动。
- **草稿已有文字素材**：脚本默认中止（防覆盖标题等）；确认替换用 `--replace`（按轨道名摘除旧字幕轨及其动画素材）。
- **顺序**：变速/删减会改分镜边界，字幕必须最后注入；已有字幕再变速需用 `jianying-speed-fit-35s`（它会同步重排非视频轨）。
- **中文进命令行必炸**：字幕走 `subs.txt` 文件；PowerShell 层先做 UTF-8 修复块（/windows-shell-commands §4.2）。
- **ffmpeg 找不到**：旧会话 PATH 快照过期，先刷新 PATH（见记忆 ffmpeg-winget-path-stale）。

## 验收与后续

- 重启剪映 → 打开草稿 → 底部应出现 `Subtitles` 轨逐镜字幕。
- 汇报模板：字幕表（时间轴|文案|画面）+ 样式说明 + 备份位置 + 资料来源链接。
- 升级链路：`jianying-inject-text-fx`（VIP 动画/花字，自动避开历史已用款）→
  `jianying-inject-tts-sticker`（配音贴纸）→ `jianying-make-cover`（封面）。
