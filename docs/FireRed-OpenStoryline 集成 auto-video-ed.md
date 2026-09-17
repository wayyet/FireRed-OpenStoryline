# FireRed-OpenStoryline 集成 auto-video-editor：设计评审与落地方案文档

> **文档状态**：完成
> **面向对象**：中级软件工程师 / DevOps 工程师
> **编写时间**：2026-09-17
> **参考资料**：`FireRed-OpenStoryline-Integration-Design.md` 及 `FireRed-OpenStoryline-auto-video-editor-集成评审.md`
> 
> 

---

## 1. 项目背景与集成目标

### 1.1 两个项目的职责划分

* **`auto-video-editor`（确定性处理引擎）**：负责低成本、高效率的底层信号处理，包括音视频导入、VAD 静音切除、场景切分（SceneDetect）、ASR 转写以及导出 OTIO/EDL/MP4。


* **`FireRed-OpenStoryline`（智能大脑）**：负责上层语义理解、多模态内容分析、脚本创作、BGM 与配音推荐、自然语言精剪及 Skill 模板化沉淀。



### 1.2 目标形态

将两者结合为 **Auto Video Editor Pro**：实现“自动化信号粗剪 -> 语义故事线生成 -> 自然语言对话精剪 -> 技能归档复用”的闭环。

---

## 2. 附件设计合理性验证与优缺点分析

基于附件中的设计方案 与评审意见，对集成设计进行深入验证与分析：

### 2.1 方案合理性验证

| 设计点 | 验证结果 | 诊断说明 |
| --- | --- | --- |
| **“确定性引擎 + 智能 Agent”分层** | **合理**<br> | 规则裁剪（高帧率要求、确定性）与 LLM 创作（非确定性、高延时）解耦，符合高可用流水线设计。

 |
| **引入 Adapter 层与统一时间线契约** | **合理**<br> | 避免主项目直接强依赖第三方内部代码。隔离数据格式差异（如 EDL 与 JSON 时间线）。

 |
| **默认关闭 AI 转场** | **合理**<br> | 第三方 AIGC 转场成功率低、耗时长且成本高，默认关闭可保障主流程稳定性。

 |
| **直接 `import third_party.FireRed-OpenStoryline...**` | **不合理（严重）**<br> | **语法错误**：Python 模块名不可包含连字符 `-`。直接 import 会破坏类隔离。

 |
| **大文件直接通过 MCP 参数传输** | **不合理（严重）**<br> | MCP 通信主要传递文本和 JSON 元数据。音视频文件必须通过标准 URIs 或本地绝对路径传输。

 |
| **混用秒（float）作为跨进程时间单位** | **不合理**<br> | 浮点数在序列化/反序列化时会产生微小累积误差，导致切片卡点错位。应统一使用**整数毫秒（int ms）**。

 |

### 2.2 方案优点分析

1. **优势互补**：发挥了 `auto-video-editor` 在信号处理上的速度优势，又补齐了缺乏创意与故事线的痛点。


2. **渐进式演进**：保留了沉淀为 Skill（技能）的能力，便于批量化生成同风格短视频。


3. **松耦合契约**：使用 JSON 契约代替对象硬绑定，便于后续微服务化拆分。



### 2.3 方案缺点分析

1. **依赖极其臃肿**：同时包含 PyTorch、torchaudio、faster-whisper、MoviePy 2.x、LangChain 等，单环境构建与维护成本极高，极易产生依赖冲突。


2. **网络与模型强依赖**：生成环节依赖大模型 API Key 及本地大型模型权重文件（Models >2GB），运维和部署复杂度增加。


3. **渲染非幂等风险**：若没有基于 Job ID 的临时隔离目录，任务失败重试容易覆盖覆盖旧文件。



---

## 3. 架构决策（轻量化决策）

为了在最小化开发成本的同时保障系统稳定性，提供以下两个选项供决定：

* **选项 A（推荐）：方案 B (Direct Adapter) 启动，演进为 独立 Storyline Worker**

* **第一阶段（开发验证）**：使用包隔离的 Direct Adapter 本地调用。


* **第二阶段（生产部署）**：将 FireRed 部署为独立 Worker（HTTP/FastAPI），主程序通过 HTTP API 提交任务，大文件共享磁盘挂载。


* **优点**：避免 MCP 进程间大文件传输问题，部署与日志排查极简。




* **选项 B：纯 MCP 通信驱动**

* **优点**：符合 Anthropic MCP 标准生态。


* **缺点**：控制流与数据流未分离，长时间渲染任务超时管理困难。





> **决定：采用选项 A**。第一阶段优先完成本地 Adapter 调通，第二阶段服务化。
> 
> 

---

## 4. 数据契约与关键代码实现

为保证技术内容**零误差**，所有路径、数据结构和调用脚本严格按照生产规范编写。

### 4.1 数据契约：`contracts/timeline_schema.json`

时间单位统一采用**整数毫秒 (ms)**。

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CanonicalTimeline",
  "type": "object",
  "properties": {
    "job_id": { "type": "string" },
    "source_media": {
      "type": "array",
      "items": {
        "properties": {
          "media_id": { "type": "string" },
          "file_path": { "type": "string" },
          "duration_ms": { "type": "integer" }
        },
        "required": ["media_id", "file_path", "duration_ms"]
      }
    },
    "clips": {
      "type": "array",
      "items": {
        "properties": {
          "clip_id": { "type": "string" },
          "source_media_id": { "type": "string" },
          "source_in_ms": { "type": "integer" },
          "source_out_ms": { "type": "integer" },
          "timeline_in_ms": { "type": "integer" },
          "timeline_out_ms": { "type": "integer" },
          "transcript": { "type": "string" }
        },
        "required": ["clip_id", "source_media_id", "source_in_ms", "source_out_ms", "timeline_in_ms", "timeline_out_ms"]
      }
    }
  },
  "required": ["job_id", "source_media", "clips"]
}

```

### 4.2 模块实现：适配器与接口防腐层

创建 `src/auto_video_editor/storyline/adapter.py`，负责将粗剪结果转换为 FireRed 的输入格式：

```python
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# 动态解决包含连字符目录的 Python 包导入问题
FIRERED_DIR = Path(__file__).resolve().parents[3] / "third_party" / "FireRed-OpenStoryline" / "src"
if str(FIRERED_DIR) not in sys.path:
    sys.path.insert(0, str(FIRERED_DIR))

class StorylineAdapter:
    def __init__(self, config_path: str):
        self.config_path = config_path

    def adapt_rough_cut_to_plan_request(
        self, 
        canonical_timeline: Dict[str, Any], 
        user_prompt: str
    ) -> Dict[str, Any]:
        """
        将 auto-video-editor 的粗剪时间线转化为 FireRed 接收的结构化 Request
        """
        formatted_clips: List[Dict[str, Any]] = []
        
        for clip in canonical_timeline.get("clips", []):
            formatted_clips.append({
                "id": clip["clip_id"],
                "start_time_sec": clip["source_in_ms"] / 1000.0,
                "end_time_sec": clip["source_out_ms"] / 1000.0,
                "duration_sec": (clip["source_out_ms"] - clip["source_in_ms"]) / 1000.0,
                "text": clip.get("transcript", "")
            })

        return {
            "job_id": canonical_timeline.get("job_id"),
            "prompt": user_prompt,
            "media_list": canonical_timeline.get("source_media", []),
            "segments": formatted_clips,
            "config_override": {
                "enable_ai_transition": False
            }
        }

```

### 4.3 独立 Storyline Worker 客户端：`src/auto_video_editor/storyline/client.py`

跨服务调用 Client 接口：

```python
import requests
from typing import Dict, Any

class StorylineWorkerClient:
    def __init__(self, worker_base_url: str = "http://127.0.0.1:8005"):
        self.base_url = worker_base_url

    def submit_storyline_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/storyline/generate"
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()

    def query_job_status(self, job_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/storyline/status/{job_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

```

---

## 5. 项目安装与依赖部署规范

### 5.1 子模块拉取与 Git 提交锁定

严禁直接跟随 `main` 分支。执行以下脚本拉取子模块并锁定 Commit：

```bash
# 1. 添加子模块
git submodule add https://github.com/wayyet/FireRed-OpenStoryline.git third_party/FireRed-OpenStoryline

# 2. 切换并锁定到验证过的 Commit ID (替换 <KNOWN_GOOD_COMMIT_HASH> 为实际 Hash)
cd third_party/FireRed-OpenStoryline
git checkout <KNOWN_GOOD_COMMIT_HASH>
cd ../..

# 3. 提交子模块更改
git add .gitmodules third_party/FireRed-OpenStoryline
git commit -m "build: pin FireRed-OpenStoryline submodule version"

```

### 5.2 隔离环境搭建命令

推荐使用 `conda` 或 `uv` 进行环境隔离，避免 Python 依赖重叠冲突：

```bash
# 创建统一基础环境
conda create -n ave_pro python=3.11 -y
conda activate ave_pro

# 安装主程序及核心依赖
pip install --upgrade pip
pip install -r requirements.txt

# 安装 FireRed 独立依赖 (可采用可编辑模式)
pip install -e third_party/FireRed-OpenStoryline

```

---

## 6. 分阶段实施 Roadmap 与测试验证清单

### 6.1 实施 Roadmap

```text
Phase 0: 隔离准备
  ├── 锁定固定 Commit
  └── 梳理导出的基础 Python API

Phase 1: 契约与适配器 (开发阶段)
  ├── 编写 Canonical Timeline JSON Schema (整数毫秒)
  ├── 实现 StorylineAdapter
  └── 单元测试验证粗剪转换

Phase 2: 服务化 (Worker 架构)
  ├── 部署独立的 FireRed FastAPI 节点
  ├── 实现 StorylineWorkerClient
  └── 实现 Job 级独立输出隔离目录

Phase 3: 业务整合与 Skill 积累
  ├── 支持自然语言对话修剪 (Refine Prompt)
  └── 固化常用模版为 JSON Skill 存入 config/styles

```

### 6.2 测试与验证清单

| 测试类型 | 测试用例 / 命令 | 期望结果 |
| --- | --- | --- |
| **Schema 校验** | `pytest tests/test_schema.py` | Timeline 数据格式符合毫秒级规范 |
| **适配器转换** | `pytest tests/test_adapter.py` | 粗剪切片无缝转换为 FireRed 输入 |
| **渲染防重写** | 提交同 `job_id` 重复执行 | 旧任务输出不被损坏，新结果存入对应隔离目录 |
| **音画同步测试** | 播放导出的 `outputs/{job_id}/final.mp4` | 语音与剪辑画面对齐无漂移，误差 < 50ms |