# `E:/Documents/kuaishou` 与 FireRed-OpenStoryline 相关性分析

> 分析日期：2026-09-16
> 目标：列出 `E:/Documents/kuaishou`（不含 `FireRed-OpenStoryline/` 子目录本体）中，与当前项目 **FireRed-OpenStoryline** 在"启动 / 配置 / 缓存 / 集成 / 文档"五个维度上存在关联的文件与目录，标注关系强度与用途。
>
> 关系强度分级：
> - **🔴 强相关** — 直接为 FireRed-OpenStoryline 服务，或其官方衍生。
> - **🟡 中等相关** — 围绕同一工作流（旅游视频 AI 剪辑路线 D / D-B）编写，明文引用 OpenStoryline。
> - **🔵 弱相关** — 上下游依赖（剪映客户端、LangGraph、auto-video-editor），但不是为 OpenStoryline 写的。

---

## 0. 总体结构速览

`E:/Documents/kuaishou` 是一个"快手旅游视频 AI 自动剪辑"项目工作区，**核心大脑是 FireRed-OpenStoryline**，整体采用「OpenStoryline 出决策 → 桥接脚本翻译 → 剪映出成片」的两段式 D-B 路线。除 FireRed-OpenStoryline 本体目录外，其它 27 个目录/文件几乎全部围绕这一条主线展开。

按角色划分：

| 类别 | 数量 | 代表 |
|---|---|---|
| 🔴 OpenStoryline 本体与官方衍生 | 3 项 | `OpenStoryline安装/`、`.claude/skills/openstoryline-launcher/`、`.claude/skills/openstoryline-to-jianying/` |
| 🟡 桥接 / 路线 D 业务脚本 | 17 项 | `os_to_spec.py`、`pipeline.py`、`jy_build.py`、`config.yaml`、`build_jianying_draft_from_storyline.py` 等 |
| 🟡 Claude 技能层（含 OpenStoryline 调用） | 13 项 | `.claude/skills/` 下 13 个 SKILL，其中 4 个明文提到 OpenStoryline |
| 🟡 规划与运行文档 | 3 项 | `docs/` 下三份实施计划文档 |
| 🔵 上游 / 下游依赖 | 5 项 | `JianyingPro/`、`langgraph-main/`、`auto-video-editor/`、`剪艾（剪辑agent）/`、`tts_voice_preview/` |
| ⚪ 仅 IDE / 缓存 | 4 项 | `.vscode/`、`.cursor/`、`.claude/settings*.json`、`--out`、`@AutomationLog.txt`、`debug-1e0587.log`、`*.ps1`(tmp_* 系列) |

---

## 1. 🔴 直接相关：OpenStoryline 本体与官方衍生

### 1.1 `OpenStoryline安装/` （目录）

| 文件 | 关系 | 说明 |
|---|---|---|
| `安装说明.md` (6.5 KB, 2026-06-14) | 🔴 官方衍生 | 为 FireRed-OpenStoryline 量身写的 Windows 安装指南，章节"2. 建环境 + 拉代码"明确写到 `git clone https://github.com/FireRedTeam/FireRed-OpenStoryline.git` |
| `download_resources.ps1` (3.0 KB, 2026-06-14) | 🔴 官方衍生 | 把官方仅 Linux/Mac 的 `download.sh` 改写成 Windows 版，从腾讯 COS 下载 `models.zip` / `resource.zip` 到 `.storyline/models/` 与 `resource/`，落点即 FireRed-OpenStoryline 的目录 |

### 1.2 `.claude/skills/openstoryline-launcher/` （SKILL.md，3.5 KB）

🔴 **强相关**。封装 FireRed-OpenStoryline 两个本地服务的启动流程：
- MCP 服务：`python -m open_storyline.mcp.server`
- 网页界面：`python -m uvicorn agent_fastapi:app --host 127.0.0.1 --port 7860`

> 注：本机对应的人工启动入口是 `FireRed-OpenStoryline/scripts/启动MCP服务.bat` 与 `启动网页界面.bat`。

### 1.3 `.claude/skills/openstoryline-to-jianying/` （目录）

🔴 **强相关**。把 FireRed-OpenStoryline 的会话时间线编排重建为剪映草稿。
- `SKILL.md` (11.4 KB)
- `scripts/build_draft.py` (11.1 KB)

读取 `<session_id>/plan_timeline_pro/plan_timeline_pro_*.json`，依赖兄弟 skill `jianying-editor` 的 `JyProject` / `pyJianYingDraft`。

---

## 2. 🟡 桥接 / 路线 D-B 业务脚本（明文提到 OpenStoryline）

> 这批文件是"旅游视频 AI 自动剪辑"项目的业务脚本（路线 D / D-B 模式），把 OpenStoryline 当作大脑（只跑决策），渲染仍交剪映。`config.yaml` 中 `[openstoryline]` 段直接以 OpenStoryline 为开关。

### 2.1 启动 / 配置类

| 文件 | 大小 | 修改时间 | 关系 | 关键内容 |
|---|---|---|---|---|
| `config.yaml` | 6.7 KB | 2026-06-14 | 🟡 核心配置 | 含 `[openstoryline]` 段：启用 D-B、会话目录、`session_dir` 默认指向 `FireRed-OpenStoryline/outputs` |
| `setup.bat` | 1.6 KB | 2026-06-14 | 🟡 启动 | 创建 venv、装依赖，验证 `scenedetect / cv2 / anthropic / yaml` 等模块 |
| `检查环境.bat` | 615 B | 2026-06-14 | 🟡 启动 | 调 `env_check.py`，询问是否补装剪映 skill 依赖 |
| `自动安装并检查.bat` | 304 B | 2026-06-14 | 🟡 启动 | 调 `env_check.py --install`，写 `env_check_report.txt` |
| `提醒音.vbs` | 492 B | 2026-06-14 | 🟡 启动 | 任务完成/需要操作时播放提示音，与 OpenStoryline 间接相关 |
| `requirements.txt` | 156 B | 2026-06-13 | 🟡 依赖清单 | `anthropic / opencv-python-headless / pysrt / PyYAML / scenedetect / Pillow` 等 |

### 2.2 桥接类（OpenStoryline ↔ 剪映）

| 文件 | 大小 | 修改时间 | 关系 | 关键内容 |
|---|---|---|---|---|
| `os_to_spec.py` | 29.0 KB | 2026-06-19 | 🟡 **核心桥接** | 把 OpenStoryline 的 `plan_timeline` / `select_bgm` / `split_shots` 决策产物翻译成 `edit_spec.json`（含 ★`beat_marks` 卡点）。数据源即 `FireRed-OpenStoryline/outputs/<sid>/` |
| `build_jianying_draft_from_storyline.py` | 4.5 KB | 2026-06-27 | 🟡 桥接 | 把 OpenStoryline 的 `plan_timeline_pro.json` 重建为剪映草稿写入 `C:/Users/wayyet/AppData/Local/JianyingPro/...` |
| `jy_build.py` | 16.5 KB | 2026-06-14 | 🟡 桥接 | 读 `edit_spec.json` → 装配剪映草稿（镜头/旁白/字幕/BGM/转场/片头） |
| `jy_build_60s.py` | 9.4 KB | 2026-06-20 | 🟡 桥接 | 把 OpenStoryline 决策压成 ~60s 版（赤松宫案例） |
| `jy_build_fengjian_60s.py` | 11.5 KB | 2026-06-21 | 🟡 桥接 | 逢简水乡 60s 版（OpenStoryline 出 20 个镜头精选 10 个） |
| `revoice_ziwei.py` | 10.9 KB | 2026-06-20 | 🟡 桥接 | 给赤松宫_DB_60s 草稿重配"紫薇"音色旁白 |
| `cover_build_fengjian.py` | 12.3 KB | 2026-06-21 | 🟡 桥接 | 给逢简水乡 60s 草稿做"端午 + 中国风"封面 |
| `add_clip_anim.py` | 5.2 KB | 2026-06-20 | 🟡 桥接 | 给赤松宫_DB_60s 加"轻微放大"入场动画 |
| `add_fengjian_anim_trans.py` | 9.5 KB | 2026-06-21 | 🟡 桥接 | 给逢简水乡 60s 加 VIP 转场 + 入场动画 |
| `add_fengjian_scene_effect.py` | 8.6 KB | 2026-06-21 | 🟡 桥接 | 逢简水乡 60s 全片柔性氛围特效 |
| `add_scene_effect.py` | 7.5 KB | 2026-06-20 | 🟡 桥接 | 赤松宫_DB_60s 全片柔性氛围特效 |
| `apply_fengjian_44s.py` | 4.2 KB | 2026-06-21 | 🟡 桥接 | 把逢简水乡 60s 收到 44.4s（替换 TTS + 字幕重排） |
| `pipeline.py` | 26.7 KB | 2026-06-14 | 🟡 桥接 | 路线 A 主入口；`--render jianying` 时与 OpenStoryline 间接关联 |
| `env_check.py` | 10.5 KB | 2026-06-14 | 🟡 桥接 | 环境自检脚本；可 `--install` 补装剪映 skill 依赖 |
| `tmp_recon_bukit.py` | 2.3 KB | 2026-07-25 | 🟡 临时脚本 | 一次性调试脚本，读取剪映 `draft_content.json` 反查 OpenStoryline 输出字段（武吉免登案例） |
| `stop_openstoryline.ps1` | 2.1 KB | 2026-07-20 | 🔴 **直关** | 按 7860 端口 + 命令行匹配 `open_storyline\|uvicorn` 强杀 OpenStoryline 进程 |
| `--out` | 871 KB | 2026-07-21 | 🔵 缓存/产物 | PNG 封面图；推测来自封面生成流水线 |

### 2.3 缓存 / 日志

| 文件 | 大小 | 时间 | 说明 |
|---|---|---|---|
| `@AutomationLog.txt` | 108 B | 2026-07-20 | Claude 自动操作日志片段（"Find Control Timeout"） |
| `debug-1e0587.log` | 279 B | 2026-07-17 | OpenStoryline `group_clips` 节点的 token 预算调试日志（含 `sessionId/runId/hypothesisId`） |

---

## 3. 🟡 Claude 技能层（13 个 SKILL，与 OpenStoryline 同流水线）

`.claude/skills/` 下分两类：

### 3.1 直关 OpenStoryline

| Skill | 类型 | 与 OpenStoryline 的关系 |
|---|---|---|
| `openstoryline-launcher/` | 🔴 | 启动 OpenStoryline 两个服务 |
| `openstoryline-to-jianying/` | 🔴 | OpenStoryline 时间线 → 剪映草稿 |
| `kuaishou-clean-cache/` | 🟡 | description 明文写「快手旅游视频 AI 自动剪辑：剪映 JianYing + FireRed-OpenStoryline 的缓存与临时文件」 |

### 3.2 围绕同一工作流（剪映端 Skills）

| Skill | 用途 |
|---|---|
| `jianying-editor/` | 完整开源 skill，自带 `pyJianYingDraft` 作为 vendor 库 |
| `jianying-add-subtitles/` | 添加字幕 |
| `jianying-cover-localize-en/` | 封面本地化（英文） |
| `jianying-draft-edit/` | 草稿编辑 |
| `jianying-inject-english-tts/` | 注入英文 TTS |
| `jianying-inject-fx/` | 注入转场/特效 |
| `jianying-inject-text-fx/` | 注入花字特效 |
| `jianying-inject-tts-sticker/` | 注入 TTS + 贴纸 |
| `jianying-make-cover/` | 制作封面 |
| `jianying-speed-fit-35s/` | 速度适配 35s |
| `jianying-translate-subtitles/` | 翻译字幕 |

> 这些技能不直接调用 OpenStoryline，但在 `OpenStoryline → 剪映` 流水线里被同一组 agent 顺序触发，是工作流的"剪映后处理段"。

---

## 4. 🟡 规划与运行文档（`docs/`）

| 文件 | 大小 | 时间 | 关系 |
|---|---|---|---|
| `AI视频剪辑自动化工作流_第三周详细实施计划.md` | 27.2 KB | 2026-09-16 | 🟡 第 3 周实施计划，多次引用 `OpenStoryline` 启动、`plan_timeline`、节点 2 `launch_openstoryline` |
| `AI视频剪辑自动化工作流第2周分阶段实施计划.md` | 22.5 KB | 2026-09-16 | 🟡 第 2 周实施计划，含 `openstoryline_pid` / `openstoryline_mcp_endpoint` / `openstoryline_web_url` / `openstoryline_ready` State 字段 |
| `AI视频剪辑自动化工作流第2周实施计划制定总结.md` | 3.9 KB | 2026-09-16 | 🟡 第 2 周总结，引用 `pyJianYingDraft/OpenStoryline` 真实 API |

---

## 5. 🔵 上下游依赖（间接相关）

| 路径 | 关系 | 说明 |
|---|---|---|
| `JianyingPro/` | 🔵 下游 | 剪映 5.9.0.11632 安装目录 + `JianYing_Visualizer.exe` + "禁止剪映自动更新"补丁目录。OpenStoryline 产物的最终渲染端 |
| `JianyingPro/5.9.0.11632/` | 🔵 | 剪映程序目录（草稿不入此目录，写到 AppData） |
| `langgraph-main/` | 🔵 上游依赖 | LangGraph 源码包，`langgraph-main.zip` (压缩包)，被 OpenStoryline 的 MCP 服务使用 |
| `auto-video-editor/` | 🔵 旁系 | Week 2+3 实施代码实现（13+1 节点 LangGraph 图），README 明文说"由 OpenStoryline 启动为第 2 个节点" |
| `auto-video-editor/README.md` | 🔵 | 详细说明节点 1-13，OpenStoryline 启动命令/端口被引用 |
| `剪艾（剪辑agent）/` | 🔵 下游 | Quicker 自动化平台 + 自定义 JianAI.exe（`win-unpacked` 是 Electron 解包）+ `openclaw-jianai-control` SKILL.md（通过 47821 端口控制 JianAI 客户端） |
| `tts_voice_preview/` | 🔵 资源 | 6 段 .ogg 音色样本（知性/清新/故事/甜美/励志/醇厚），被 `config.yaml` 的 `[tts]` 段引用 |

---

## 6. ⚪ 仅 IDE / 通用缓存（与本项目无直接内容耦合）

| 路径 | 说明 |
|---|---|
| `.vscode/launch.json` | Edge Tools 调试器配置：打开 OpenStoryline `http://127.0.0.1:7860/`。**有项目耦合**，但只是 IDE 配置 |
| `.cursor/` | 空目录，IDE 配置残留 |
| `.claude/settings.json` | 旧版权限白名单（指向 D 盘与旧用户名 `wayye`，已过期） |
| `.claude/settings.local.json` | 当前版本权限白名单，路径已是 `E:/Documents/kuaishou/FireRed-OpenStoryline` |
| `.claude/scheduled_tasks.lock` | 91 字节锁文件 |
| `.jydeps313/` | Python 3.13 隔离依赖目录（`pymediainfo / uiautomation / comtypes`），被 `openstoryline-to-jianying` 用 `--target` 安装复用 |
| `input/` | 仅一个子目录 `6688/`（旅游素材待处理） |
| `output/` | 业务产出：covers、subs_en_bukitbintang_20260721、tts_probe_en、若干临时探查 ps1 |
| `bgm/` | 4 段候选 BGM 资源（候选 1-4 mp3） |
| `tmp/` | 工作模板：`cover_wrapper_template.json` / `text_*_template.json` 等 |
| `scripts/` | 9 个一次性脚本（`build_fx_bukit.py` / `gen_tts_buk_item.py` 等），围绕武吉免登案例 |
| `scratchpad/` | 武吉免登案例的中间产物（图片帧、备份目录、`restore_backup.py`） |
| `--out` | 871 KB PNG 封面图（详见 §2.3） |

---

## 7. 文件清单速查表（去重 + 排序）

> 列出 `E:/Documents/kuaishou` **根目录**下与 OpenStoryline 相关的全部条目（不含 `FireRed-OpenStoryline/` 子目录本体）。

### 7.1 🔴 强相关（建议保留并定期同步）

```
OpenStoryline安装/                                  OpenStoryline 官方衍生（Windows 适配）
├── 安装说明.md                                     安装指南（Win 版）
└── download_resources.ps1                          Win 版资源下载脚本

.claude/skills/openstoryline-launcher/SKILL.md      OpenStoryline MCP + Web 启动 skill
.claude/skills/openstoryline-to-jianying/           OpenStoryline → 剪映草稿
├── SKILL.md
└── scripts/build_draft.py

stop_openstoryline.ps1                              OpenStoryline 服务停止脚本
```

### 7.2 🟡 中等相关（核心业务 + 技能层 + 文档）

业务脚本（17 个 .py/.bat/.ps1）：
```
os_to_spec.py                            ★ 桥接：OpenStoryline → edit_spec.json
build_jianying_draft_from_storyline.py   ★ 桥接：OpenStoryline plan → 剪映草稿
jy_build.py                              装配剪映草稿
jy_build_60s.py                          赤松宫 60s 版
jy_build_fengjian_60s.py                 逢简水乡 60s 版
revoice_ziwei.py                         赤松宫重配旁白
cover_build_fengjian.py                  逢简水乡封面
add_clip_anim.py                         赤松宫入场动画
add_fengjian_anim_trans.py               逢简水乡动画 + 转场
add_fengjian_scene_effect.py             逢简水乡特效
add_scene_effect.py                      赤松宫特效
apply_fengjian_44s.py                    逢简水乡收到 44.4s
pipeline.py                              路线 A 主入口
env_check.py                             环境自检
tmp_recon_bukit.py                       武吉免登草稿反查（一次性）
config.yaml                              含 [openstoryline] 段
setup.bat                                venv 安装
检查环境.bat                             调 env_check.py
自动安装并检查.bat                       装 + 检查
提醒音.vbs                               提示音
requirements.txt                         依赖清单
```

Claude 技能层（11 个 SKILL）：
```
.claude/skills/openstoryline-launcher/           (见 7.1)
.claude/skills/openstoryline-to-jianying/        (见 7.1)
.claude/skills/kuaishou-clean-cache/             缓存清理（明文含 OpenStoryline）
.claude/skills/jianying-editor/                  剪映编辑器
.claude/skills/jianying-add-subtitles/
.claude/skills/jianying-cover-localize-en/
.claude/skills/jianying-draft-edit/
.claude/skills/jianying-inject-english-tts/
.claude/skills/jianying-inject-fx/
.claude/skills/jianying-inject-text-fx/
.claude/skills/jianying-inject-tts-sticker/
.claude/skills/jianying-make-cover/
.claude/skills/jianying-speed-fit-35s/
.claude/skills/jianying-translate-subtitles/
```

文档：
```
docs/AI视频剪辑自动化工作流_第三周详细实施计划.md
docs/AI视频剪辑自动化工作流第2周分阶段实施计划.md
docs/AI视频剪辑自动化工作流第2周实施计划制定总结.md
```

IDE / 缓存 / 调试日志：
```
.vscode/launch.json                          Edge DevTools 调试 OpenStoryline
.claude/settings.json                        旧版权限白名单（已过期）
.claude/settings.local.json                  当前权限白名单
.claude/scheduled_tasks.lock
--out                                        871 KB PNG 封面图（缓存）
@AutomationLog.txt                           Claude 自动操作日志
debug-1e0587.log                             group_clips 节点调试日志
```

### 7.3 🔵 弱相关（上下游）

```
JianyingPro/                                剪映客户端 + 升级屏蔽
JianyingPro/5.9.0.11632/                    剪映程序目录
JianyingPro/禁止剪映自动更新/               hosts 补丁
JianyingPro/安装事项.txt
JianyingPro/JianYing_Visualizer.exe
JianyingPro/剪映5.9Windows.zip

langgraph-main/                             LangGraph 源码（含 zip 包）
langgraph-main/langgraph-main.zip

auto-video-editor/                          Week 2+3 LangGraph 实现（13+1 节点）
auto-video-editor/README.md                 明文引用 OpenStoryline

剪艾（剪辑agent）/                          Quicker + JianAI Electron app
剪艾（剪辑agent）/openclaw-jianai-control/  OpenClaw 控制 JianAI 的 SKILL.md
剪艾（剪辑agent）/win-unpacked/             JianAI.exe Electron 解包目录
剪艾（剪辑agent）/Quicker安装包.msi

tts_voice_preview/                          6 段 .ogg 音色样本（被 config.yaml 引用）

.jydeps313/                                 Python 3.13 隔离依赖（pymediainfo/uiautomation/comtypes）

input/, output/, bgm/, tmp/, scripts/, scratchpad/   工作目录与一次性脚本
.cursor/                                    空目录（IDE 残留）
```

---

## 8. 结论与建议

1. **核心圈（必保留）**：
   - `OpenStoryline安装/`、`.claude/skills/openstoryline-*`、`stop_openstoryline.ps1` —— 全部是 OpenStoryline 启动 / 集成 / 停止脚本。
   - `os_to_spec.py`、`build_jianying_draft_from_storyline.py` —— OpenStoryline → 剪映的核心桥接。

2. **业务圈（项目交付物，建议保留）**：
   - 17 个 .py/.bat/.ps1 + `config.yaml` + `requirements.txt`：构成路线 D-B 的完整业务脚本集。
   - 11 个 `jianying-*` SKILL：剪映端后处理的标准套件。
   - `docs/` 下 3 份实施计划：项目演进的真实档案。

3. **可清理或可选**：
   - `.cursor/` 空目录、`.claude/scheduled_tasks.lock`、`@AutomationLog.txt`、`debug-1e0587.log`、`tmp_recon_bukit.py` 属于过程产物。
   - `--out`（871 KB PNG）若已并入成片可清理。
   - `scratchpad/` 下 `吉隆坡武吉免登_*` 系列是单次案例的工作区，可归档或清理。
   - `.claude/settings.json` 内含过期路径（`D:/`、用户 `wayye`），建议替换为 `settings.local.json` 那份。

4. **必须保留但属外部依赖**：
   - `JianyingPro/`、`langgraph-main/`、`tts_voice_preview/`、`auto-video-editor/` 是 OpenStoryline 工作流的上下游，删了会让整个 D-B 流水线断掉。

> 建议下一次维护时优先处理 §8.3 中的过期内容（`settings.json`），再清理 `scratchpad/`、`--out` 等案例残留，以保持工作目录清爽。