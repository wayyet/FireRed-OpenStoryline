# bridge/ — kuaishou 业务层

> 迁移与重组织：把 `E:/Documents/kuaishou/` 根下与 FireRed-OpenStoryline 相关的脚本、配置、文档、案例工作区、静态资源、瞬态日志，全部收纳到本目录。
> 计划文档：`docs/workflow/week3-detailed-plan.md`。

`bridge/` 与上游官方目录（`src/`、`web/`、`prompts/`、`resource/`、`scripts/`、`config.toml`、`agent_fastapi.py` 等）**平级**，互不污染；上游 `git pull` 不会触碰本目录。

---

## 1. 4 条路线（业务入口）

| 路线 | 目录 | 角色 | 主要脚本 |
|---|---|---|---|
| A | `bridge/route_a/` | Claude 直跑 pipeline（业务素材 → 剪映草稿） | `pipeline.py` |
| D-B | `bridge/route_db/` | OpenStoryline 大脑 + JianYing 渲染（OS session → edit_spec → 剪映草稿） | `os_to_spec.py`、`build_jianying_draft_from_storyline.py` |
| OS | `bridge/openstoryline/` | OS 服务管理（启动 / 强杀 / Win 资源下载） | `stop.ps1`、`install_guide.md` |
| 案例 | `bridge/cases/bukit_bintang/` | 单案例工作区（脚本、模板、中间产物、封面） | `scripts/`、`tmp/`、`scratchpad/` |

> 另外 4 个**留在工作区根**的大体积外部依赖（`JianyingPro/`、`剪艾（剪辑agent）/`、`auto-video-editor/`、`langgraph-main/`）→ 见 [`EXTERNAL_DEPS.md`](EXTERNAL_DEPS.md)。

---

## 2. 子目录一览

| 目录 | 内容 |
|---|---|
| `route_a/` | 路线 A 业务层：主入口 pipeline.py、配置 config.yaml、env_check.py、3 个 .bat/.vbs |
| `route_db/` | 路线 D-B 桥接脚本：OS → edit_spec → 剪映草稿 共 12 个 .py |
| `openstoryline/` | OS 服务管理：Win 版安装指南、资源下载 ps1、强杀 ps1、debug 日志、Py 3.13 隔离依赖 |
| `cases/bukit_bintang/` | 武吉免登案例：9 个一次性脚本、4 个 JSON 模板、scratchpad 中间产物、cover_out.png |
| `assets/bgm/` | 4 段候选 BGM（约 7.95 MB） |
| `assets/tts_preview/` | 6 段 TTS 音色样本（约 100 KB） |
| `input/` | 业务素材待处理（`6688/` 武吉免登 4 段 MOV 视频） |
| `output/` | 业务输出（`tts_probe_en/` 8 个英文 TTS 探针 mp3） |
| `tmp/` | 跨案例模板（4 个 JSON）+ 清理脚本（clean_scan.ps1 / clean_delete.ps1） |
| `logs/` | 业务层日志（`automation.log`） |

---

## 3. 启动指南

### 3.1 路线 A（Claude 直跑 pipeline）

```powershell
cd E:/Documents/kuaishou/FireRed-OpenStoryline/bridge/route_a
.\setup.bat           # 建 venv + pip install requirements.txt
.\check_env.bat       # 验证环境（不安装）
.\auto_install_check.bat  # 自动安装缺失依赖并验证
python pipeline.py    # 启动主流程
```

### 3.2 路线 D-B（OpenStoryline 大脑 + JianYing 渲染）

```powershell
# 1) 启动 OS 服务（MCP + Web UI 在 7860）
cd E:/Documents/kuaishou/FireRed-OpenStoryline
.\scripts\start_web.bat          # 见项目根 scripts/（官方）

# 2) OS 跑完一个 session 后，导出 edit_spec
cd bridge/route_db
python os_to_spec.py --session-dir "../outputs/<session_id>" --theme "赤松宫"

# 3) 用 edit_spec 重建剪映草稿
python build_jianying_draft_from_storyline.py --spec edit_spec.json
```

### 3.3 OS 服务管理

```powershell
# 强杀 OS 服务（端口 7860 + 命令行匹配 open_storyline|uvicorn）
cd E:/Documents/kuaishou/FireRed-OpenStoryline/bridge/openstoryline
powershell -File stop.ps1

# 查看 Win 版安装指南
notepad install_guide.md

# 资源下载（与官方 scripts/download_resources.ps1 内容相同，作为归档副本）
powershell -File download_resources.ps1
```

### 3.4 案例工作区（武吉免登）

```powershell
cd E:/Documents/kuaishou/FireRed-OpenStoryline/bridge/cases/bukit_bintang
# 查看案例 README
notepad README.md
# 跑一次性脚本（每个脚本独立完成一个原子操作）
python scripts/build_fx_bukit.py
python scripts/check_buk_item.py
# ...
```

---

## 4. 与上游官方目录的关系

`bridge/` 是新增的业务层，**不动**任何上游文件。具体边界：

| 上游官方（不碰） | bridge/ 业务层（本次迁移） |
|---|---|
| `src/`、`web/`、`prompts/`、`resource/`、`scripts/` | `bridge/route_a/`、`bridge/route_db/`、`bridge/openstoryline/` |
| `config.toml`、`agent_fastapi.py`、`cli.py` | `bridge/route_a/config.yaml`、`bridge/route_a/pipeline.py` |
| `build_env.sh`、`Dockerfile`、`hf_space.sh` | — |
| `.claude/`（含全部 skills） | — |
| `docs/`（18 份官方文档） | `docs/workflow/`（3 份工作流计划） |
| `outputs/`（OS 会话产物） | — |

`scripts/install_all.ps1` 是官方安装入口，不要从 `bridge/` 调它；`bridge/openstoryline/install_guide.md` 仅作 Win 版说明归档。

---

## 5. 关键代码路径常量（搬迁后）

| 文件 | 常量 | 搬迁后取值 |
|---|---|---|
| `route_a/pipeline.py` | `ROOT = Path(__file__).parent` | 自动 = `bridge/route_a/` |
| `route_db/os_to_spec.py` | `OS_REPO` | `ROOT.parent.parent / "FireRed-OpenStoryline"`（OS 项目是 bridge/ 的爷爷目录） |
| `route_db/jy_build.py` | `find_skill_root()` 候选列表 | 追加 `../.claude/skills/jianying-editor` |
| `route_db/build_jianying_draft_from_storyline.py` | 同上 | 同上 |
| `route_a/config.yaml` | `paths.{input,output,tmp,bgm}` | 全部改为 `../xxx`（指 `bridge/xxx/`） |

详见 `docs/workflow/week3-detailed-plan.md` §4.1-4.2。
