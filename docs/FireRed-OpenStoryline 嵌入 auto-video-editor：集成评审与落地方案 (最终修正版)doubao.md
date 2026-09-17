# FireRed-OpenStoryline 嵌入 auto-video-editor：集成评审与落地方案 (最终修正版)

**评审日期**：2026-09-17  
**核验对象**：

- `wayyet/FireRed-OpenStoryline` (AI 驱动短视频叙事 Agent)
- `wayyet/auto-video-editor` (LangGraph 剪映草稿自动化工作流)
**参考文档**：
- 《FireRed-OpenStoryline-Integration-Design.md》（原设计 v1.0）
- 《FireRed-OpenStoryline-auto-video-editor-集成评审.md》（评审 v1）
- 《FireRed-OpenStoryline 集成 auto-video-editor：设计评审与落地方案文档》（落地方案 v1）

---

## 1. 执行摘要 (TL;DR)

经过对两个 GitHub 仓库源码的公网核验，**前序三份附件文档的核心立论前提已被证伪**，集成方向需要从"Direct Adapter 优先"反转至"MCP-first 进程隔离"。

### 核心事实纠正

1. **定位纠正**：`auto-video-editor` 并非文档假设的"VAD 静音切除/SceneDetect 确定性粗剪引擎"，而是一个 **LangGraph 驱动的剪映草稿自动化编排器**（13+1 节点 StateGraph、三处人工 interrupt/resume 关卡、SqliteSaver/Postgres 持久化），输出物为剪映 `draft_content.json`，而非 EDL/OTIO。
2. **集成基础纠正**：`auto-video-editor` **已经内建了 OpenStoryline 的集成点**（`node_02_launch_openstoryline.py`、`mcp_clients/openstoryline_client.py`、`jy_common/asr_client.py`），集成并非从零开始。
3. **技术约束纠正**：存在 Python 版本硬冲突（FireRed 要求 3.11，主项目实测 3.13.11），前序文档推荐的"单进程 Direct Adapter"方案为否决项，**MCP-first（进程隔离）才是唯一可行路线**。
4. **数据终点纠正**：数据契约的最终目标不是 EDL/OTIO，而是剪映的 `draft_content.json`；整数毫秒 Canonical Timeline 仅作为中间契约。

### 最终结论

保留附件文档中"分层架构、契约先行、整数毫秒、幂等安全"的工程纪律；但必须推翻其接口虚构、环境合并与路线顺序，**以主项目既有的 MCP 客户端为起点进行加固**，将已有集成链路从"可用"升级为"生产级"。

---

## 2. 仓库真实形态核验

### 2.1 FireRed-OpenStoryline (智能大脑)

- **定位**：AI 驱动的短视频编辑 Pipeline (MCP + LLM)，核心是语义理解与创意生成。
- **核心能力**：智能搜素材、脚本生成 (Few-shot 风格迁移)、BGM/配音推荐、对话式精剪、Skill 归档、AI 转场、ASR 粗剪。
- **真实技术栈**：Python 3.11 (Conda)、MoviePy、FFmpeg、LangChain、FastAPI (端口 8005)、MCP Server。
- **真实目录结构**：
  - 核心节点位于 `src/open_storyline/nodes/core_nodes/`，包括 `understand_clips.py`、`generate_script.py`、`plan_timeline.py`、`select_bgm.py`、`render_video.py` 等函数式模块；
  - MCP 工具经 `mcp/register_tools.py` 注册，无独立 `mcp/tools/` 目录与 `mcp/client.py`；
  - Skill 机制原生支持 `.storyline/skills/<name>/SKILL.md` 格式。
- **版本锚点**：无 GitHub Release，但存在官方 Docker 镜像 `openstoryline/openstoryline:v1.0.1`。

### 2.2 auto-video-editor (编排中枢)

- **定位**：LangGraph 驱动的剪映草稿自动化工作流，核心是确定性流程编排与剪映草稿生成。
- **核心能力**：13+1 节点 StateGraph、三处人工关卡（①重排/②BGM/③版式）、心跳监控、Postgres/Sqlite 持久化、原子写入与版本策略。
- **真实技术栈**：Python 3.13.11、LangGraph、Windows/PowerShell 优先、剪映草稿生成 (`draft_content.json`)。
- **已有 OpenStoryline 集成点**：
  - `node_02_launch_openstoryline.py`：工作流中启动 OpenStoryline 的节点；
  - `mcp_clients/openstoryline_client.py`：Week 2 已交付的 MCP 客户端实现；
  - `jy_common/asr_client.py`：FireRedASR2S 客户端，对接端点 `127.0.0.1:8009`；
  - Week 5 已为 `node_17_inject_english_tts` 预留 FireRedTTS2 能力桩。
- **测试基线**：单元测试 60 条 + 集成测试 24 条 = 84 条全部通过。

---

## 3. 附件设计合理性验证与优缺点分析

### 3.1 设计合理部分（应保留的资产）

| 设计点 | 验证结果 | 诊断说明 |
| --- | --- | --- |
| **"确定性引擎 + 智能 Agent"分层** | ✅ 合理 | 规则处理与 LLM 创作解耦，符合高可用流水线设计。 |
| **引入 Adapter 层与统一时间线契约** | ✅ 合理 | 隔离数据格式差异，主项目内部采用整数毫秒 Canonical Timeline。 |
| **默认关闭 AI 转场** | ✅ 合理 | 官方明示 AIGC 转场成本高、结果不可控，默认关闭保障主流程稳定性。 |
| **整数毫秒 (int ms) 作为时间单位** | ✅ 合理 | 避免浮点数序列化累积误差导致卡点错位。 |
| **Skill 复用与批量化生产** | ✅ 合理 | 有产品价值，FireRed 原生支持 `.storyline/skills/SKILL.md`，无需自造格式。 |
| **幂等性与 Job 隔离** | ✅ 合理 | 同 `job_id` 重跑不污染旧结果，可复用主项目 `draft_ops/atomic_writer.py`。 |

### 3.2 设计严重缺陷（必须推翻的证伪项）

| 附件设计断言 | 判定 | 真实源码事实与修正 |
| --- | --- | --- |
| **auto-video-editor 是 VAD/SceneDetect 粗剪器** | ❌ **重大错误** | 实为 LangGraph 剪映编排器，输出物是 `draft_content.json` 而非 EDL。 |
| **推荐"先单进程 Direct Adapter MVP"** | ❌ **需反转** | Python 3.11 vs 3.13 硬冲突，单进程合并环境是否决项。必须 **MCP-first**。 |
| **直接 `import third_party.FireRed-OpenStoryline...`** | ❌ **语法错误** | Python 模块名不可包含连字符 `-`，且跨版本 import 会破坏环境隔离。 |
| **虚构接口名 (UnderstandingNode / generate_storyline)** | ❌ **无源码依据** | 真实节点为 `understand_clips.py` 等，MCP 工具名需运行时 `list_tools()` 发现。 |
| **大文件直接通过 MCP 参数传输** | ❌ **严重不合理** | 音视频必须通过 URI (如 `file:///E:/...`) 或 artifact ID 传递，禁止进参数。 |
| **EDL/OTIO 作为主要交换格式** | ❌ **终点错位** | 一等公民是剪映草稿，EDL 仅作为可选导出器。 |

### 3.3 三份附件文档逐条验证

#### 原设计 v1.0 验证

| 断言 | 判定 | 说明 |
| --- | --- | --- |
| MCP 子进程嵌入为推荐方案 | ✅ 方向正确 | 与仓库既成事实一致，为本方案核心路线 |
| 方案 B：Python 包直接导入 | ❌ 不可行 | 类名虚构 + Python 版本硬冲突 |
| 合并 requirements.txt，MoviePy 锁 2.x | ❌ 否决 | 两个环境根本不该合并 |
| Docker 构建期执行 `download.sh` | ❌ 不合理 | 网络依赖破坏构建缓存 |
| Skill 沉淀/复用 | ✅ 合理 | FireRed 原生支持 |

#### 评审 v1 验证

| 断言 | 判定 | 说明 |
| --- | --- | --- |
| 固定 Git commit 而非 main 分支 | ✅ 正确 | 补充：Docker tag `v1.0.1` 亦可作锚点 |
| 工具名/类名未证实，需 `list_tools()` 后生成客户端 | ✅ 完全正确 | 已被源码验证 |
| **推荐"先单进程 Adapter MVP，MCP 不作第一阶段核心链路"** | ❌ **需反转** | 主项目已交付 MCP client + Python 版本硬冲突，该结论与事实相反 |
| EDL 表达力不足，改用内部 JSON 时间线 | ✅ 方向正确 | 进一步明确下游落点是 `draft_content.json` |
| Windows 也应优先 Worker | ⚠️ 部分采纳 | 采纳"FireRed 进程隔离"；但主项目 Windows 优先是既定事实 |

#### 落地方案 v1 验证

| 断言 | 判定 | 说明 |
| --- | --- | --- |
| 采用"选项 A：Direct Adapter → Worker" | ❌ 不可行 | 与仓库既成 MCP 路线冲突 + 版本错配 |
| 时间线 JSON Schema（整数毫秒） | ✅ 可沿用 | 本版补充剪映映射字段 |
| `StorylineWorkerClient`（HTTP 8005） | ✅ 采纳为生产形态 | 与 FireRed 既有端口约定一致 |
| 渲染防重写测试、音画同步 < 50ms 验收 | ✅ 采纳 | 主项目已有原子写入库可直接复用 |
| 未验证 FireRed 侧真实接口即写出 adapter 代码 | ❌ 缺陷 | `media_list`/`segments` payload 为单方面假设 |

### 3.4 综合优缺点分析

#### 优点

1. **优势互补的顶层设计**：`auto-video-editor` 负责"变短"和"剪映编排"，`FireRed` 负责"变好"和"语义创作"，职责边界清晰。
2. **契约先行的工程思想**：使用 JSON Schema 约束时间线，便于后续微服务化与校验。
3. **防御性的质量纪律**：提出了版本锁定、双依赖锁、运行时接口发现、幂等输出等高质量工程实践。

#### 缺点

1. **目标对象失焦**：前序文档作者未做源码审计，为想象中的"粗剪器"编写了不可运行的代码，存在模块名/布局/输出格式三重错位。
2. **环境模型错误**：忽略 Python 3.11 与 3.13.11 的硬边界，把"依赖冲突"降格为"风险较高"而非"否决项"。
3. **路线顺序颠倒**：在主项目已交付 MCP 客户端的事实下，仍推荐从 Direct Adapter 起步，等于推翻既有代码重做。
4. **数据契约终点错位**：以 EDL/OTIO 为一等公民；实际一等公民是剪映 `draft_content.json`（含加密检测/版本策略/原子写入约束）。
5. **平台假设偏差**：评审建议 docker-compose 优先；但主项目为 Windows/PowerShell-native，容器化只能是 FireRed 侧的可选项。

---

## 4. 修正后的集成方案 (v2.0 MCP-First)

### 4.1 架构决策记录 (ADR)

- **ADR-001 进程隔离是硬性要求**：FireRed (3.11) 与主项目 (3.13) 解释器永不合并，集成仅通过 MCP stdio 子进程或 HTTP。
- **ADR-002 MCP-first 路线**：开发期使用 stdio 启动 MCP Server 子进程；生产期使用 FastAPI(8005) HTTP Worker。
- **ADR-003 契约三层映射**：`Canonical JSON(ms)` ↔ `MCP payload` ↔ `draft_content.json`。
- **ADR-004 接口运行时发现**：禁止硬编码未证实工具名，客户端启动时 `list_tools()` 动态匹配意图。
- **ADR-005 默认关闭 AI 转场**：config 中 `enable_ai_transition=false`，仅显式 `--pro` 开启。

### 4.2 目标架构图

```
graph TD
    subgraph AVE["auto-video-editor（Windows，Python 3.13，LangGraph）"]
        G[StateGraph 13+1 节点] --> N02[node_02_launch_openstoryline]
        N02 --> MCSVC[OpenStorylineMCPClient<br/>mcp_clients/openstoryline_client.py<br/>扩展点]
        G --> N04[node_04_import_and_plan]
        G --> N05[node_05_generate_draft]
        G --> CK1[关卡① human_reorder]
        G --> CK2[关卡② human_add_bgm]
        G --> CK3[关卡③ layout_review]
        DOPS[draft_ops: 原子写入/加密检测/版本策略]
        CTL[Canonical Timeline JSON<br/>整数毫秒]
        ASRC[jy_common/asr_client.py<br/>FireRedASR2S :8009]
    end
    subgraph PROC["集成边界（进程隔离）"]
        MCP["FireRed MCP Server（stdio 子进程）<br/>python 3.11 · open_storyline.mcp.server<br/>list_tools() 动态发现"]
        WK["FireRed FastAPI Worker（可选，生产）<br/>agent_fastapi.py :8005"]
        ASRS["FireRedASR2S 服务 :8009"]
    end
    MCSVC -->|list_tools + call_tool| MCP
    MCSVC -.->|HTTP 提交，生产路径| WK
    ASRC --> ASRS
    MCP --> CTX[FireRed 内部：load_media → understand_clips<br/>→ generate_script → plan_timeline<br/>→ select_bgm/generate_voiceover → render_video]
    CTX --> PLAN[计划/时间线结果]
    PLAN --> CTL --> DOPS
```

### 4.3 数据契约 v2（修订版）

#### Canonical Timeline（主项目内部契约，整数毫秒）

```
{
  "$schema": "[http://json-schema.org/draft-07/schema](http://json-schema.org/draft-07/schema)#",
  "title": "CanonicalTimeline",
  "type": "object",
  "required": ["job_id", "source_media", "clips"],
  "properties": {
    "job_id":       { "type": "string" },
    "created_at_ms":{ "type": "integer" },
    "source_media": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["media_id", "file_path", "duration_ms"],
        "properties": {
          "media_id":   { "type": "string" },
          "file_path":  { "type": "string" },
          "sha256":     { "type": "string" },
          "duration_ms":{ "type": "integer" }
        }
      }
    },
    "clips": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["clip_id","source_media_id","source_in_ms",
                     "source_out_ms","timeline_in_ms","timeline_out_ms"],
        "properties": {
          "clip_id":         { "type": "string" },
          "source_media_id": { "type": "string" },
          "source_in_ms":    { "type": "integer" },
          "source_out_ms":   { "type": "integer" },
          "timeline_in_ms":  { "type": "integer" },
          "timeline_out_ms": { "type": "integer" },
          "transcript":      { "type": "string" },
          "scene_id":        { "type": "string" },
          "quality_score":   { "type": "number" },
          "semantic_tags":   { "type": "array", "items": { "type": "string" } },
          "content_hash":    { "type": "string" }
        }
      }
    },
    "audio": {
      "type": "object",
      "properties": {
        "bgm_ref":   { "type": ["string","null"] },
        "voiceover": { "type": ["string","null"] }
      }
    },
    "subtitles": {
      "type": "object",
      "properties": {
        "zh": { "type": ["string","null"] },
        "en": { "type": ["string","null"] }
      }
    }
  }
}
```

#### MCP payload 规则

- 大文件只传绝对路径 URI / artifact id，**不进 MCP 参数**；
- payload 模型用 Pydantic 定义，**字段名以 `list_tools()` 返回的 inputSchema 为准反向生成**，禁止手写臆测字段；
- 返回结果统一落盘为 artifact，Canonical Timeline 更新后交 `draft_ops` 写草稿。

### 4.4 集成点映射与改造

| 现有资产 | 改造内容 |
| --- | --- |
| `mcp_clients/openstoryline_client.py` | ① 启动时 `list_tools()` 并缓存工具目录；② 按意图映射工具；③ 增加 per-call 超时与取消；④ 结果 artifact 化 |
| `node_02_launch_openstoryline.py` | 增加：FireRed conda env 检测（3.11）、`config.toml` 存在性/Key 检测、子进程存活心跳、崩溃重拉 |
| `node_04_import_and_plan.py` | 输入侧接入 Canonical Timeline；增加 schema 校验 |
| `node_05_generate_draft.py` | 输出侧对接 `draft_ops/atomic_writer.py`；生成 `outputs/{job_id}/manifest.json` |
| `jy_common/asr_client.py` | 保持 `FIRERED_ASR_ENDPOINT` 注入；补连接错误分类重试 |
| `state.py` | 新增 `NotRequired` 字段：`canonical_timeline`、`storyline_plan`、`storyline_artifacts` |
| `config.py` | 新增 `[storyline]` 段：conda env 路径、MCP 启动命令、`enable_ai_transition=false`、超时/重试参数 |
| 新增 `storyline/contract.py` | Canonical Timeline Pydantic 模型 + JSON Schema 导出 |
| 新增 `storyline/mapper.py` | Canonical ↔ draft_content.json 双向映射（含毫秒→微秒换算与帧对齐） |

### 4.5 双环境隔离与版本锁定

**严禁合并 `requirements.txt`**。

```
# 1. FireRed 侧 (独立 Conda 环境)
conda create -n storyline python=3.11 -y
conda activate storyline
git submodule add [https://github.com/wayyet/FireRed-OpenStoryline.git](https://github.com/wayyet/FireRed-OpenStoryline.git) third_party/FireRed-OpenStoryline
cd third_party/FireRed-OpenStoryline && git checkout <KNOWN_GOOD_COMMIT>
pip install -r requirements.txt
# Windows 需手动下载 models.zip 和 resource.zip

# 2. 主项目侧 (保持现有 venv 3.13)
.\.venv\Scripts\Activate.ps1
python -m pip install -e <langgraph-main libs> ...   # 既有安装方式不动
```

### 4.6 关键代码骨架

```
# storyline/contract.py —— Canonical Timeline 模型（毫秒）
from pydantic import BaseModel, Field

class Clip(BaseModel):
    clip_id: str
    source_media_id: str
    source_in_ms: int = Field(ge=0)
    source_out_ms: int = Field(ge=0)
    timeline_in_ms: int = Field(ge=0)
    timeline_out_ms: int = Field(ge=0)
    transcript: str = ""

class CanonicalTimeline(BaseModel):
    job_id: str
    source_media: list[dict]
    clips: list[Clip]
```

```
# mcp_clients/openstoryline_client.py 扩展骨架（运行时发现工具）
class OpenStorylineMCPClient:
    async def __aenter__(self):
        self._session = ...                      # 既有 stdio 启动逻辑
        self._tools = {t.name: t for t in await self._session.list_tools()}
        self._require_tools("load_media", "understand_clips",
                            "generate_script", "plan_timeline",
                            "select_bgm", "render_video")
        # 若缺工具 → fail-fast，打印 list_tools 全量帮助诊断
        return self

    async def build_plan(self, canonical: dict, intent: str) -> dict:
        # payload 字段名以 self._tools[...].inputSchema 为准，禁止臆测
        ...
```

### 4.7 幂等与安全机制

- **输出隔离**：`outputs/{job_id}/`（manifest.json / timeline.json / draft_content.json / logs/）；
- **原子写入**：复用 `draft_ops/atomic_writer.py` + `version_strategy.py`，先写临时目录，成功后原子替换；
- **幂等键**：`job_id + input_hash + config_hash`；同键重跑命中缓存；
- **API Key 管理**：FireRed 侧进 `config.toml`，主项目进 `.env`，严禁入库、禁止入 MCP 日志。

---

## 5. 分阶段实施 Roadmap

| 阶段 | 核心任务 | 交付物 | 与前序文档差异 |
| --- | --- | --- | --- |
| **Phase 0: 源码审计（1~2 天）** | 锁定双仓 commit；在 3.11 环境启动 MCP Server，`list_tools()` 导出工具清单与 inputSchema；跑通 FireRed Web 端最小 demo | `storyline_tools_inventory.md`、锁定后的 submodule 指针 | 评审文档的 Phase 0 保留，本版已完成部分源码核验 |
| **Phase 1: 契约与客户端加固（1 周）** | 实现 Canonical Timeline Pydantic 模型；加固 MCP 客户端（动态发现/超时/取消/artifact 化）；schema 校验接入 node_04/05 | `contract.py` + `schema.json` + 84 条既有测试全绿 | 原"Phase 1 实现 Direct Adapter"删除 |
| **Phase 2: 幂等与观测（1 周）** | Job 隔离目录、manifest、防重写；心跳/超时看门狗覆盖 MCP 子进程；失败分类与重试 | 防重写/取消/超时集成测试 | 新增（评审提出，前文档未落地） |
| **Phase 3: 对话式精剪 + Skill（1~2 周）** | refine 链路走关卡①②③ 的 resume；FireRed Skill 与主项目 checkpoint 联动；版本 diff | 精剪 E2E 测试 + Skill 模板 2 个 | Skill 用 FireRed 原生格式，弃 skill.json 自造格式 |
| **Phase 4: 产品化（1~2 周）** | 生产 Worker 化（FastAPI :8005 + HTTP 提交）；Windows 部署文档；EDL/OTIO 可选导出器；指标面板 | 部署手册 + 指标面板 | Worker 化从"第一阶段"移到生产阶段 |

---

## 6. 测试与验收清单

| 测试层级 | 验证用例 | 通过标准 |
| --- | --- | --- |
| **既有回归** | `python -m pytest -v` | 84 条全绿，不因集成破坏既有逻辑 |
| **Contract** | Canonical Timeline schema 校验（越界/负数/媒体缺失） | 非法输入 100% 拒绝 |
| **Contract** | MCP `list_tools()` 快照测试 | 工具集变化 → 测试报警（防上游静默升级） |
| **Integration** | node_02 启动 → list_tools → 生成计划 → node_05 落草稿 | 生成的 `draft_content.json` 可被剪映正常打开 |
| **Integration** | FireRedASR2S :8009 | 连接失败分类（ECONNREFUSED/TIMEOUT）可重试 |
| **Rendering** | draft → 剪映导出成片 | 音画偏差 < 50ms |
| **Retry** | 同 `job_id` 重跑 | 旧输出不被污染（atomic_writer 生效） |
| **Cancel** | 关卡①挂起后 cancel | MCP 子进程与 ASR 请求被回收 |
| **Security** | 路径穿越 / Key 泄漏扫描 | 零命中 |
| **Skill** | 保存 → 换素材复用 | 风格一致、毫秒时间线合法 |

---

## 7. 风险与对策

| 风险 | 等级 | 对策 |
| --- | --- | --- |
| MCP 工具名/schema 与预期不符 | 高 | ADR-004 运行时发现 + 快照测试；Phase 0 完成 inventory |
| FireRed 无 GitHub Release，上游漂移 | 中 | 锁 commit + Docker `v1.0.1` 双锚点；fork 内可自行打 tag |
| Python 3.11/3.13 双环境维护 | 中 | ADR-001 硬隔离；CI 分两个 job 各自验证 |
| Windows stdio 子进程编码/路径问题 | 中 | UTF-8 显式声明；`file:///E:/` URI 规范；冒烟脚本纳入 heartbeat |
| 剪映客户端逆向字段未回填 | 高（既有） | 与本次集成解耦，按 README 仍需用户行动项推进 |
| LLM 不确定性输出 | 中 | 计划→Canonical 校验→draft_ops 三道闸 |
| AI 转场成本失控 | 低 | 默认关闭，`--pro` 显式开启 |
| 版权（BGM/字体/素材） | 中 | 沿用 FireRed Restricted Mode + 自定义资源库教程 + manifest 留痕 |

---

## 8. 最终结论

1. **保留**：分层思想、契约先行、整数毫秒、幂等、安全、测试分层——三份文档的工程纪律全部有效。
2. **推翻**：①"auto-video-editor 是确定性粗剪器"的前提；②Direct Adapter 优先的路线；③全部虚构接口名；④EDL 一等公民地位；⑤"合并环境/合并 requirements"。
3. **确立**：以**主项目既有的 MCP 集成点为起点**，按 `Phase 0 工具清单 → Phase 1 契约加固 → Phase 2 幂等观测 → Phase 3 精剪与 Skill → Phase 4 Worker 化` 推进；FireRed 侧以 fork + 锁定 commit + 独立 3.11 环境接入，Windows 主进程零侵入。

> 
> 一句话总结：`auto-video-editor` 已经把"变短"和"剪映编排"做成了 LangGraph 流水线，**不要新开一条 Direct Adapter 路线**；FireRed-OpenStoryline 应该通过主项目**既有的 MCP 客户端**把"变好"的能力接进来——把已有的那条路修成高速公路。