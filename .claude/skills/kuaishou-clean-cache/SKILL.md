---
name: kuaishou-clean-cache
description: 扫描并清理 kuaishou 项目（快手旅游视频 AI 自动剪辑：剪映 JianYing + FireRed-OpenStoryline）的缓存与临时文件——OpenStoryline 服务端缓存、__pycache__、Playwright 调试产物、服务日志、tmp 临时帧、剪映草稿注入 .bak 备份等。剪映 AppData 的 Cache\ 与 Log\ 目录属于禁删项，绝不清理。流程是"先扫描出报告→用户确认→再删除→汇总回收体积"，绝不先删后报。适用于"清理缓存""清理临时文件""释放磁盘空间""清理项目缓存""清理剪映缓存""磁盘满了"等场景。触发词：清理缓存、清理临时文件、清理项目、释放磁盘、清理剪映缓存、clean cache、kuaishou clean。
---

# kuaishou 项目缓存与临时文件清理

## 强制前置规则

1. **强制启用 `/chinese-outcome`**：全程中文输出结果。
2. **强制启用 `/confirm-me`**：任何删除动作前，必须先展示"将删除的路径 + 体积"清单并等用户确认；不明确的条目单独停下来问。
3. **强制启用 `/windows-shell-commands`**：只用 PowerShell / Windows CMD 命令，禁止 Linux 语法；命令 description 与字符串内禁用中文引号。

## 口径定义

"缓存/临时文件" **仅指删除后不影响项目运行、可自动重建或纯过程产物的内容**。成果（成片、会话输出）、运行依赖（模型、素材、健康的虚拟环境）、程序本体一律不算，见下文"三类·禁止删除"。

## 关键路径（以实测为准，警惕路径漂移）

- 项目根：`e:\Documents\kuaishou`（历史文档写过 `c:\Users\wayye\Downloads\媒体剪辑\kuaishou`、其他 skill 写过 `d:\Documents\kuaishou`，**均已过期**；用户名是 `wayyet` 不是 `wayye`）
- FireRed 子项目：`e:\Documents\kuaishou\FireRed-OpenStoryline`
- 剪映草稿目录（AppData，项目外但由本项目技能写入）：`C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft`
- 剪映应用缓存（AppData，**禁删项**，路径仅用于识别）：`C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Cache`、`...\User Data\Log`

## 执行流程（固定四步）

1. **扫描**：按下文清单逐项 `Test-Path` + 测体积，输出"分类 / 路径 / 体积 / 建议"报告。基线快照仅作对照，**不要照抄**——以本次实测为准。
2. **确认**：把报告给用户，一类可整批确认一次；二类必须逐项单独确认；三类只展示不删。
3. **删除**：只删用户确认过的条目，命令模板见下；每条带 `-ErrorAction SilentlyContinue` 并先 `Test-Path`。
4. **汇总**：报告实际回收体积；如有较大变化，顺手更新 `docs\缓存与临时文件分析.md` 的基线（需用户同意）。

---

## 一类·常规再生缓存（低风险，整批确认后可删）

这些会随运行反复再生，删了下次运行自动重建：

| 项 | 来源 | 历史体积参考 |
|---|---|---|
| `FireRed-OpenStoryline\.storyline\.server_cache\` | OpenStoryline 服务端缓存 | 最大头，曾达 1.1 GB |
| `__pycache__\`（项目源码处，排除两个 venv 内部） | 系统 Python 跑脚本 | < 1 MB |
| `.playwright-cli\`（根 & FireRed） | playwright 调试快照/截图 | ~1 MB |
| `web.out.log / web.err.log / mcp.out.log / mcp.err.log`（FireRed） | openstoryline-launcher 启服务 | ~60 KB |
| `install_log.txt / test_result.txt / test_tts_result.txt / config.toml.bak.*`（FireRed） | 安装与测试 | 小 |
| `env_check_report.txt`（根） | env_check.py | ~14 KB |
| `tmp\` 下的**子目录**（cover、cover_frames、frames、scenes 等） | 封面/抽帧临时产物 | ~2 MB |
| `JianyingPro\5.9.0.11632\log\*` | 剪映程序日志 | 小 |
| `剪艾（剪辑agent）\win-unpacked\boot.log` | 剪艾 agent 日志 | 小 |
| `.DS_Store`（全项目） | macOS 垃圾 | 极小 |
| 剪映草稿注入 .bak 备份（`<草稿>\*.bak`、`<草稿>\.backup\`） | jianying-inject-* / jianying-make-cover 写草稿前的备份 | 随注入次数增长，曾 26 个 2.4 MB |

⚠️ **tmp 根下 4 个模板 json 必须保留**（脚本依赖，只删 tmp 的子目录）：`cover_wrapper_template.json`、`text_material_template.json`、`text_segment_template.json`、`text_track_shell.json`。

### 一类清理命令模板

```powershell
$root = 'e:\Documents\kuaishou'
$fr   = "$root\FireRed-OpenStoryline"

# 1) OpenStoryline 服务端缓存（最大头）
if (Test-Path "$fr\.storyline\.server_cache") { Remove-Item -Recurse -Force "$fr\.storyline\.server_cache" }

# 2) 源码字节码缓存（排除两个 venv 内部）
Get-ChildItem -Recurse -Force -Directory $root -Filter '__pycache__' -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch '\\venv\\|\\\.venv\\' } | Remove-Item -Recurse -Force

# 3) Playwright 调试产物
Remove-Item -Recurse -Force "$root\.playwright-cli","$fr\.playwright-cli" -ErrorAction SilentlyContinue

# 4) 日志 / 安装记录 / 测试输出 / 配置备份 / 环境报告
Remove-Item -Force "$fr\web.out.log","$fr\web.err.log","$fr\mcp.out.log","$fr\mcp.err.log","$fr\install_log.txt","$fr\test_result.txt","$fr\test_tts_result.txt","$root\env_check_report.txt" -ErrorAction SilentlyContinue
Remove-Item -Force "$fr\config.toml.bak.*" -ErrorAction SilentlyContinue

# 5) tmp 临时帧——只删子目录，绝不动 tmp 根下的 4 个模板 json
Get-ChildItem -Force "$root\tmp" -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

# 6) 应用运行日志
Remove-Item -Force "$root\JianyingPro\5.9.0.11632\log\*" -ErrorAction SilentlyContinue
Remove-Item -Force "$root\剪艾（剪辑agent）\win-unpacked\boot.log" -ErrorAction SilentlyContinue

# 7) macOS 垃圾
Get-ChildItem -Recurse -Force -File $root -Filter '.DS_Store' -ErrorAction SilentlyContinue | Remove-Item -Force

# 8) 剪映草稿注入 .bak 备份（全部删除，不再保留最新一份；删后注入不可回滚，删前提醒用户确认成片已导出）
$draft = 'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft'
Get-ChildItem -Recurse -Force -File $draft -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match '\.bak$' } | Remove-Item -Force
Get-ChildItem -Recurse -Force -Directory $draft -Filter '.backup' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
```

---

## 二类·大件与项目外关联缓存（逐项单独确认）

### 2.1 根 `venv\`（已于 2026-07-04 删除，回收 233 MB）

死重 venv（基础解释器 Python312 已删、venv 不可搬迁）已清除。删除时发现 `lib\site-packages\pip\_vendor` 存在 NTFS 目录索引损坏（列目录为空但删除报"非空"，`Repair-Volume -Scan` 报 NoErrorsFound），常规手段删不掉，残留空目录链已改名隔离为 `E:\Documents\kuaishou\venv._corrupt_remnant`（0 字节）——待用户运行 `Repair-Volume -DriveLetter E -SpotFix`（短暂卸载 E 盘）或 `chkdsk E: /f` 修复后手工删除。需要重建环境时用 `/python-venv-bootstrap`。**FireRed 的 `.venv` 是健康的（base 为 Python313，仍在用），禁止删除。**

### 2.2 `剪艾（剪辑agent）\win-unpacked.zip`（≈322 MB，与已解压目录重复）

`win-unpacked\` 目录（≈514 MB）已存在且在用时，zip 属重复归档。先验证解压目录完整（存在且非空、含 exe），再向用户确认删除 zip。

### 2.3 剪映草稿回收站（AppData 草稿目录）

- 草稿根下 `.recycle_bin\`：剪映草稿回收站，确认无需找回后可清。
- **绝不可动**：`Projects\com.lveditor.draft\<草稿名>\` 本体（含 textReading 配音、素材引用）。
- 变更说明（2026-07-04 用户指定）：草稿注入 .bak 备份已升为**一类常规清理项**（见一类命令模板第 8 条，全部删除）；剪映 AppData 的 `Cache\` 与 `Log\` 已移入**三类禁删项**。

### 2.4 建议"移动备份"而非删除的安装包

- `JianyingPro\剪映5.9Windows.zip`（≈735 MB）：剪映 5.9 官方渠道已不易下载，是版本钉死重装的唯一来源，**不算缓存**；空间紧张时建议移动到备份盘。
- `剪艾（剪辑agent）\Quicker安装包.msi`（≈23 MB）：同理。
- `tts_voice_preview\`（~0.1 MB）：SAMI 音色试听样本，可由 TTS 技能重新生成，体积可忽略，默认保留。

---

## 三类·禁止删除（只展示，不删）

| 路径 | 性质 |
|---|---|
| `FireRed-OpenStoryline\.venv\`（≈1.6 GB） | 健康虚拟环境，Python313，仍在用 |
| `FireRed-OpenStoryline\` 源码/config.toml/*.bat/prompts | MCP 插件本体 |
| `FireRed-OpenStoryline\.storyline\models\`（≈116 MB） | 模型权重 |
| `FireRed-OpenStoryline\resource\`（≈527 MB） | bgms/fonts/tts/模板素材 |
| `FireRed-OpenStoryline\outputs\`（≈458 MB）、根 `output\` | **会话/成片成果** |
| `tmp\` 根下 4 个模板 json | 脚本依赖模板 |
| `JianyingPro\5.9.0.11632\`、`禁止剪映自动更新\`、`安装事项.txt` | 剪映 5.9 程序本体与钉版本配置 |
| `剪艾（剪辑agent）\win-unpacked\`、`openclaw-jianai-control\` | 剪艾 agent 程序与 skill/agents |
| `.claude\`、`docs\`、`bgm\`、`input\`、根下 *.py / config.yaml / *.bat | 项目配置、文档、素材、脚本 |
| 剪映 AppData `Projects\com.lveditor.draft\<草稿名>\` 本体 | 草稿数据（含 textReading 配音） |
| 剪映 AppData `User Data\Cache\` | 剪映素材/特效下载缓存；删除后已注入的 VIP 转场/特效/花字/贴纸需重新联网下载才能渲染。**用户 2026-07-04 指定禁删** |
| 剪映 AppData `User Data\Log\` | 剪映日志。**用户 2026-07-04 指定禁删** |

---

## 基线快照（2026-07-04 实测，仅作对照）

- 一类项当时全部为 0（2026-06 迁盘时已清过一轮；`.server_cache`、`.playwright-cli`、FireRed 日志、`__pycache__`、`.DS_Store` 均不存在，`tmp` 只剩 4 个模板）。
- 二类项：死 `venv` 233 MB（2026-07-04 已删）、`win-unpacked.zip` 322 MB；草稿 .bak 曾 26 个 2.4 MB（现属一类）；剪映 Cache 1110 MB、剪映 Log 55 MB（现属三类禁删，体积仅作记录）。
- 历史单次最大回收记录：2026-06-26 约 1.13 GB（大头是 `.server_cache`）。

## 已知坑

1. **路径漂移**：历史文档/旧 skill 里的 `c:\Users\wayye\...`、`d:\Documents\kuaishou` 都是过期路径，动手前一律 `Test-Path` 实测 `e:\Documents\kuaishou`。
2. **`$home` 是 PowerShell 保留变量**，解析 pyvenv.cfg 时换名（如 `$base`）。
3. **PowerShell 5.1** 无 `utf8NoBOM`、无 `SkipCertificateCheck`，中文输出前先设 UTF-8 —— 详见 `/windows-shell-commands`。
4. **剪映 `Cache\` 与 `Log\` 是禁删项**（用户 2026-07-04 指定）：Cache 一旦删除，已注入的 VIP 素材要重新联网下载、弱网/离线时草稿暂不可渲染——即使磁盘紧张也不要清理，除非用户明确改口。
5. 删除大目录前先关掉占用进程（剪映客户端、OpenStoryline 两个服务、剪艾 agent），否则文件占用会导致半删状态。
