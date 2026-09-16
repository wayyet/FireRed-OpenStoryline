# EXTERNAL_DEPS.md — 留在工作区根的外部依赖

> 这 4 个目录 **不在 bridge/ 内部**，而是停留在 `E:/Documents/kuaishou/` 根，与 `FireRed-OpenStoryline/` 平级。
> 原因：体积大、含系统级安装、git 历史独立、不能被项目 `git pull` 覆盖。

---

## 1. 引用路径表

| 依赖 | 绝对路径 | 体积 | bridge/ 中的引用方式 |
|---|---|---|---|
| JianyingPro | `E:/Documents/kuaishou/JianyingPro/` | 2.2 GB | OS 进程直接调剪映客户端；剪映草稿目录 `C:/Users/wayyet/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft/` 是硬编码系统路径，**不动** |
| 剪艾（剪辑agent） | `E:/Documents/kuaishou/剪艾（剪辑agent）/` | 757 MB | Electron 应用 + Quicker 安装包，独立运行 |
| auto-video-editor | `E:/Documents/kuaishou/auto-video-editor/` | 112 MB | 独立 Python 项目，自带 `.git/` 与 `.venv/`，有独立 git 历史 |
| langgraph-main | `E:/Documents/kuaishou/langgraph-main/` | 18 MB | Python 源码包，作为库被 `pip install -e` 引用 |

---

## 2. 为什么留在根

1. **JianyingPro/**：剪映客户端安装目录。剪映的草稿目录路径是系统级硬编码（`C:/Users/wayyet/AppData/Local/JianyingPro/...`），与 JianyingPro 安装目录本身解耦；hosts 屏蔽补丁与剪映快捷方式也指向原位置，移动会破坏这些引用。
2. **剪艾（剪辑agent）/**：Electron 应用 + Quicker 安装包（`win-unpacked/` + `Quicker安装包.msi`），属于用户级安装，不属于任何项目。
3. **auto-video-editor/**：独立 Python 项目，自带 `.git/` 和 `.venv/`，有自己的 git 历史与依赖清单；并入 FireRed-OpenStoryline 会污染 git 历史与依赖图。
4. **langgraph-main/**：Python 源码包（langgraph 主仓库快照），作为库被引用；并入项目子目录会让 langgraph 的源码版本受项目 `git pull` 影响。

---

## 3. bridge/ 引用外部依赖的方式

### 3.1 JianyingPro

`bridge/route_db/build_jianying_draft_from_storyline.py` 与 `bridge/route_db/jy_build*.py` 通过 **`jianying-editor` skill**（位于 `FireRed-OpenStoryline/.claude/skills/jianying-editor/`）调用剪映客户端；skill 内部用绝对路径访问 `C:/Users/wayyet/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft/`。

不直接读 `JianyingPro/` 安装目录本身。

### 3.2 剪艾（剪辑agent）

bridge/ 暂未引用。如未来要集成，从 `E:/Documents/kuaishou/剪艾（剪辑agent）/win-unpacked/` 启动 Electron 主进程。

### 3.3 auto-video-editor

bridge/ 暂未引用。如果作为对照参考，从 `E:/Documents/kuaishou/auto-video-editor/` 单独 git checkout。

### 3.4 langgraph-main

`E:/Documents/kuaishou/auto-video-editor/` 的 `requirements.txt` / `pyproject.toml` 可能用 `pip install -e E:/Documents/kuaishou/langgraph-main/`；bridge/ 暂未直接引用。

---

## 4. 跨平台提示

- 这 4 个目录都是 **Windows + 当前用户专属**。在新机器或新用户上，需要：
  1. 重新安装 JianyingPro 到 `JianyingPro/` 同名位置；
  2. 重新部署剪艾 Electron 应用；
  3. 重新 `git clone` auto-video-editor 与 langgraph-main。
- bridge/ 脚本中**不应硬编码**这 4 个目录的绝对路径；如需引用，应通过环境变量或 `config.yaml` 注入。

---

## 5. 不在本目录范围

- `E:/Documents/kuaishou/.vscode/`（已迁到 `FireRed-OpenStoryline/.vscode/`）
- `E:/Documents/kuaishou/docs/`（已迁到 `FireRed-OpenStoryline/docs/workflow/`）
- `E:/Documents/kuaishou/OpenStoryline安装/`（已迁到 `FireRed-OpenStoryline/bridge/openstoryline/`）
- `E:/Documents/kuaishou/scripts/`、`bgm/`、`tts_voice_preview/`、`input/`、`output/`、`tmp/`、`@AutomationLog.txt`、`--out`、`debug-1e0587.log`、`.jydeps313/`（均已迁到 `bridge/` 各子目录）
- `E:/Documents/kuaishou/*.py` 业务脚本（已迁到 `bridge/route_a/` 或 `bridge/route_db/`）
