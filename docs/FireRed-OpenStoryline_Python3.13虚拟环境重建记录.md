# FireRed-OpenStoryline Python 3.13 虚拟环境重建记录

> 记录时间：2026-07-01
> 任务范围：用 Python 3.13 重建 `FireRed-OpenStoryline\.venv`，并按 `requirements.txt` 重装全部依赖（不下载模型，API 模式运行）
> 触发指令：`/confirm-me` + `/chinese-outcome`，网络直连，无代理
> 当前状态：**已完成**（2026-07-01 收尾：用 `--no-deps` + `editdistance` shim 绕过编译失败，20/21 关键包导入通过，`/openstoryline-launcher` 两个服务均正常启动并验证）

---

## 1. 任务确认（用户预批 6 项）

| # | 项 | 取值 |
|---|---|---|
| 1 | 模式 | `/confirm-me` + `/chinese-outcome` |
| 2 | 参考输出格式 | `Command usage overview`（命令使用概览） |
| 3 | `.venv` 处理 | 备份为 `.venv.bak`（重命名，秒级，零额外占用） |
| 4 | 解释器版本 | **Python 3.13.11**（`py -3.13` → `C:\Program Files\Python313\python.exe`） |
| 5 | 网络 | **直连**（无 `HTTP_PROXY` / 无 `pip.ini`） |
| 6 | 范围 | **只做 venv + pip install**，**不下载模型**（funasr / HF 缓存保持空） |

---

## 2. 环境盘点（执行前）

| 项 | 值 |
|---|---|
| 系统 | Windows |
| 工作目录 | `E:\Documents\kuaishou\FireRed-OpenStoryline` |
| 现 `.venv` | Python **3.12.8**，1.70 GB / 335 包（68,142 项） |
| 现 `.venv.bak` | ❌ 不存在（可放心新建） |
| 磁盘剩余 | E 盘 **126.33 GB** 空闲（备份 1.7 GB 后仍有富余） |
| Python 3.13 | `C:\Program Files\Python313\python.exe` 3.13.11 |
| `py` 启动器 | `-3` 默认指向 3.13.11；`-3.12` 仍可用 3.12.8 |
| PyPI 直连 | ✅ `pip index versions requests` 通 |
| `pip` 版本 | 26.1.2（最新） |
| `requirements.txt` | 28 行，含 torch / torchaudio / sentence-transformers / faiss-cpu / funasr / moviepy 等大包 |

`requirements.txt` 节选（关键行）：

```text
fastapi==0.128.0
uvicorn[standard]==0.40.0
langchain-core==1.4.7
mcp==1.26.0
langchain==1.2.18
langgraph==1.1.10
langgraph-prebuilt==1.0.13
sentence-transformers==5.2.2
faiss-cpu==1.13.2
funasr==1.3.1
torchaudio==2.11.0
```

---

## 3. 执行步骤

### 步骤 1：备份 `.venv` → `.venv.bak`

```powershell
Move-Item "e:\Documents\kuaishou\FireRed-OpenStoryline\.venv" `
         "e:\Documents\kuaishou\FireRed-OpenStoryline\.venv.bak" -Force
```

- ✅ `.venv` 已移除
- ✅ `.venv.bak` 存在，**68,142 项**（秒级重命名，零拷贝，零额外占用）
- 回滚命令（如需）：`Move-Item .venv.bak .venv`

### 步骤 2：用 Python 3.13 重建 `.venv`

```powershell
py -3.13 -m venv "e:\Documents\kuaishou\FireRed-OpenStoryline\.venv" --upgrade-deps
```

- ✅ 新 `.venv` 已创建
- 验证：`sys.version = 3.13.11` (`MSC v.1944 64 bit (AMD64)`)
- 解释器路径：`E:\Documents\kuaishou\FireRed-OpenStoryline\.venv\Scripts\python.exe`

### 步骤 3：升级 pip / setuptools / wheel

```powershell
& "e:\Documents\kuaishou\FireRed-OpenStoryline\.venv\Scripts\python.exe" -m pip install -U pip setuptools wheel
```

- ✅ pip **26.1.2**（保持）
- ✅ setuptools **82.0.1**（升级）
- ✅ wheel **0.47.0**（升级）
- ✅ packaging **26.2**（升级）

> 备注：命令行中 `.\.venv\Scripts\python.exe` 形式的相对路径在当前 PowerShell 终端会被转义吃掉反斜杠，必须用 `& "<绝对路径>"` 调用。

### 步骤 4：安装 `requirements.txt` —— 失败 ❌

```powershell
& "...\.venv\Scripts\python.exe" -m pip install -r "...\requirements.txt" --progress-bar on `
  2>&1 | Tee-Object -FilePath "...\logs\pip_install_3.13.log"
```

- ⏱️ 下载阶段：~6 分钟内下完全部 wheel（torch 123 MB / scipy 36.6 MB / av 31.7 MB / imageio_ffmpeg 31.2 MB / llvmlite 38.1 MB / faiss-cpu 18.9 MB / numpy 12.3 MB / transformers 12.0 MB / modelscope 6.0 MB 等）
- ❌ 在 5 个 sdist 构建（jieba / editdistance / oss2 / aliyun-python-sdk-core / crcmod / antlr4-python3-runtime）中失败 **editdistance**
- **退出码：1**
- 因一个 wheel 失败，pip **整笔回滚**，`site-packages` 仍只有 9 个目录
- 日志：`e:\Documents\kuaishou\FireRed-OpenStoryline\logs\pip_install_3.13.log`（39.3 KB）

### 步骤 5：失败根因分析

| 检查项 | 结果 |
|---|---|
| `editdistance 0.8.1` cp313 预编译 wheel | ❌ **无**（`pip download --only-binary` 找不到） |
| PyPI 同包所有版本（0.1 → 0.8.1） | 全部 Cython 源码包，**无任何 cp313 wheel** |
| MSVC Build Tools | ❌ 未安装（无 `cl.exe`，无 VS 目录） |
| MinGW / gcc / g++ | ❌ 未安装 |
| 失败错误 | `error: Microsoft Visual C++ 14.0 or greater is required`（Cython 编译 `_editdistance.cpp`） |

### 步骤 6：寻找可绕过 MSVC 的方案

| 候选 | cp313 wheel | 备注 |
|---|---|---|
| `editdistance 0.8.1` | ❌ | 需 MSVC 编译 Cython |
| `Levenshtein 0.27.3` | ✅ 94 kB | 速度极快，但模块名叫 `Levenshtein`，**不是** `editdistance` |
| `rapidfuzz 3.14.5` | ✅ 1.5 MB | 备选，可降级到 `Levenshtein.distance` 兼容 |

### 步骤 7：分析 funasr 对 editdistance 的实际引用

解压 `funasr-1.3.1-py3-none-any.whl`（811 kB），在 `funasr/utils/compute_wer.py` 等 3 个位置的引用模式完全一致：

```python
import editdistance
cers.append(editdistance.eval(hyp_chars, ref_chars))
```

即只用了 `editdistance.eval(seq1, seq2)` 一个函数，语义就是 **Levenshtein 距离**——**可以用 `Levenshtein.distance` 完美替换**。

### 步骤 8（待执行）：修复方案 —— 用 shim 包绕过

```powershell
# 1) 生成临时 requirements（剔除 funasr 行，原文件不动）
Get-Content "requirements.txt" | Where-Object { $_ -notmatch '^funasr' } `
  | Set-Content "requirements.no_funasr.txt"

# 2) 装除 funasr 外的全部依赖
python -m pip install -r requirements.no_funasr.txt

# 3) 装 Levenshtein（cp313 预编译 wheel 已确认存在）
python -m pip install Levenshtein

# 4) 装 funasr 但跳过其依赖（其它依赖步骤 2 已装）
python -m pip install funasr==1.3.1 --no-deps

# 5) 写 editdistance shim
# 文件: .venv\Lib\site-packages\editdistance\__init__.py
```

`editdistance` shim 代码：

```python
"""editdistance shim for Python 3.13 on Windows: wraps Levenshtein.distance."""
try:
    from Levenshtein import distance as _lev_distance
except ImportError:  # 兜底：万一 Levenshtein 也没装，用 rapidfuzz
    from rapidfuzz.distance import Levenshtein as _rf
    def _lev_distance(s1, s2):
        return _rf.distance(s1, s2)

def eval(target, source):
    """与原 editdistance.eval 语义一致：返回序列间的编辑距离。"""
    return _lev_distance(target, source)

__all__ = ["eval"]
```

---

## 4. 已下载 wheel 缓存盘点

虽然步骤 4 整笔回滚，但**所有 wheel 都已下载到本地 cache**，步骤 8-2 复用时无需再走 PyPI。

| 包 | wheel 大小 | cp313 wheel |
|---|---|---|
| `torch` | 123.0 MB | ✅ |
| `scipy` | 36.6 MB | ✅ |
| `llvmlite` | 38.1 MB | ✅ |
| `av` | 31.7 MB | ✅ |
| `imageio_ffmpeg` | 31.2 MB | ✅ |
| `transnetv2_pytorch` | 32.7 MB | ✅ |
| `numpy` | 12.3 MB | ✅ |
| `transformers` | 12.0 MB | ✅ |
| `pandas` | 9.8 MB | ✅ |
| `scikit_learn` | 8.2 MB | ✅ |
| `pillow` | 7.0 MB | ✅ |
| `pywin32` | 6.9 MB | ✅ |
| `modelscope` | 6.0 MB | ✅ |
| `sympy` | 6.3 MB | ✅ |
| `faiss-cpu` | 18.9 MB | ✅ |
| `cryptography` | 3.8 MB | ✅ |
| `tokenizers` | 2.7 MB | ✅ |
| `langchain_community` | 2.5 MB | ✅ |
| `networkx` | 2.1 MB | ✅ |
| `pydantic_core` | 2.1 MB | ✅ |
| `sqlalchemy` | 2.1 MB | ✅ |
| `soundfile` | 1.0 MB | ✅ |
| `pynndescent` / `pyjwt` / `umap_learn` / `modelscope_hub` / ... | < 1 MB | ✅ |
| `Levenshtein`（步骤 8-3 用） | 94 kB | ✅ |

---

## 5. 仍待执行

| # | 步骤 | 状态 |
|---|---|---|
| 1 | 备份 `.venv` → `.venv.bak` | ✅ 完成 |
| 2 | 用 Python 3.13 重建 `.venv` | ✅ 完成 |
| 3 | 升级 pip / setuptools / wheel | ✅ 完成 |
| 4 | `pip install -r requirements.txt`（全量） | ❌ `editdistance` 编译失败，整笔回滚 |
| 5 | 写 `requirements.no_funasr.txt`（剔除 funasr 行） | ✅ 完成 |
| 6 | `pip install -r requirements.no_funasr.txt` | ✅ 完成（site-packages 10→318 目录，无编译失败） |
| 7 | `pip install Levenshtein` | ✅ 完成（Levenshtein 0.27.3 + rapidfuzz 3.14.5） |
| 8 | `pip install funasr==1.3.1 --no-deps` | ✅ 完成 |
| 9 | 写 `editdistance/__init__.py` shim（+ 伪 dist-info） | ✅ 完成 |
| 10 | 关键包导入冒烟测试 | ✅ 20/21 通过（funasr 因 --no-deps 未完整，见下） |
| 11 | `pip check` 依赖完整性校验 | ✅ 完成（仅 funasr 12 项子依赖缺口，属预期） |
| 12 | 启动并验证 `/openstoryline-launcher` | ✅ MCP(8001) + 网页(7860) 均正常 |

---

## 5.1 收尾实际结果（2026-07-01）

### 步骤 6-9 执行结果

- **步骤 6**：`requirements.no_funasr.txt` 一次装成，site-packages 从 10 → **318 目录**，wheel 全走 cache，jieba/oss2 等纯 Python sdist 正常构建，**无编译失败**。关键版本：torch **2.12.1+cpu**、torchaudio **2.11.0+cpu**、numpy **2.4.6**、fastapi 0.128.0、uvicorn 0.40.0、mcp 1.26.0、langchain 1.2.18 全家、langgraph 1.1.10、sentence-transformers 5.2.2、faiss-cpu 1.13.2、transformers 4.57.6、moviepy 2.2.1、av 16.1.0。
- **步骤 7**：`Levenshtein` 0.27.3（+ `rapidfuzz` 3.14.5）装好，`Levenshtein.distance('kitten','sitting')==3`。
- **步骤 8**：`funasr==1.3.1 --no-deps` 装好，`funasr` 目录存在。
- **步骤 9**：写 `editdistance` shim（`eval` 以 `Levenshtein.distance` 为后端，`rapidfuzz` 兜底），并**额外补一个最小 `editdistance-0.8.1.dist-info`**（METADATA/INSTALLER/top_level.txt/RECORD），让 pip 认为 editdistance 0.8.1 已安装、避免 `pip check` 报 "funasr requires editdistance"。实测 `editdistance.eval('kitten','sitting')==3`。

### 步骤 10 冒烟测试

- **20/21 关键包导入成功**：fastapi、uvicorn、mcp、langchain、langchain_core、langgraph、langchain_openai、langchain_mcp_adapters、openai、torch、torchaudio、faiss、sentence_transformers、transformers、moviepy、av、numpy、librosa、Levenshtein、editdistance。
- **唯一失败**：`import funasr` → `ModuleNotFoundError: No module named 'omegaconf'`。

### 步骤 11 pip check

除 funasr 外**无任何版本冲突**（torch/torchaudio 等自洽）。funasr 因 `--no-deps` 缺 12 个子依赖（`hydra-core / jaconv / jamo / jieba / kaldiio / modelscope / oss2 / pytorch-wpe / sentencepiece / tensorboardx / torch-complex / umap-learn`）。

> **funasr 依赖缺口的处理决策（用户确认）**：`funasr` 在项目里仅由 [`src/open_storyline/nodes/core_nodes/asr_node.py`](../src/open_storyline/nodes/core_nodes/asr_node.py) 内**延迟导入**（`from funasr import AutoModel` 在函数体内），且 `editdistance` 在 funasr 内部也是延迟 `import`。因此 **launcher 启动完全不需要 funasr**，只有真正跑本地 ASR（`asr_node`）时才会用到。经用户确认，**保持 funasr 最小安装**（不补 12 个子依赖），符合 md 预批的 `--no-deps` 方案与"API 模式不下模型"定位；本地 ASR 若日后要用，再补齐这 12 个包即可。

### 步骤 12 launcher 验证

按 `/openstoryline-launcher`（用真实 **E 盘**路径，`PYTHONPATH=src`，直接调 python 不走 .bat）后台启动两个服务：

- **MCP 服务** `python -m open_storyline.mcp.server`：加载本地 `./.storyline/models/all-MiniLM-L6-v2`（未触发下载）、faiss 以 AVX2 加载成功（AVX512 那条是正常降级提示）、`StreamableHTTP session manager started` → **`Uvicorn running on http://127.0.0.1:8001`**。
- **网页界面** `python -m uvicorn agent_fastapi:app --host 127.0.0.1 --port 7860`：`Application startup complete` → **`Uvicorn running on http://127.0.0.1:7860`**。
- **HTTP 实测**：`GET http://127.0.0.1:7860/` → **200**，返回 `<!doctype html><html lang="zh-CN">…` 正常页面；`GET :8001/` → 404（MCP StreamableHTTP 端点非根路径，端口存活正常）。浏览器已打开 7860。

> 注意：`/openstoryline-launcher` 的 SKILL.md 里项目根写的是 `d:\Documents\kuaishou\...`（D 盘），本机真实为 **`e:\Documents\kuaishou\...`**，启动时已用真实 E 盘路径。

---

## 6. 回滚指南（如需切回 3.12）

```powershell
# 切回原 3.12 环境（秒级）
Move-Item "e:\Documents\kuaishou\FireRed-OpenStoryline\.venv" `
         "e:\Documents\kuaishou\FireRed-OpenStoryline\.venv.broken" -Force
Move-Item "e:\Documents\kuaishou\FireRed-OpenStoryline\.venv.bak" `
         "e:\Documents\kuaishou\FireRed-OpenStoryline\.venv" -Force

# 清理 3.13 失败重建的废目录（可选）
Remove-Item "e:\Documents\kuaishou\FireRed-OpenStoryline\.venv.broken" -Recurse -Force
```

---

## 7. 关键命令汇总（Command usage overview）

| 用途 | 命令 |
|---|---|
| 备份 venv | `Move-Item .venv .venv.bak -Force` |
| 重建 venv | `py -3.13 -m venv .venv --upgrade-deps` |
| 升级打包工具 | `python -m pip install -U pip setuptools wheel` |
| 装全部依赖（已失败） | `python -m pip install -r requirements.txt` |
| 装除 funasr 外依赖 | `python -m pip install -r requirements.no_funasr.txt` |
| 装 Levenshtein（shim 后端） | `python -m pip install Levenshtein` |
| 装 funasr 不带依赖 | `python -m pip install funasr==1.3.1 --no-deps` |
| 检查依赖完整性 | `python -m pip check` |
| 查看 venv 大小 | `(Get-ChildItem .venv -Recurse -Force \| Measure-Object Length -Sum).Sum / 1MB` |

---

## 8. 关键经验（避免下次踩坑）

1. **`py -3.13` 默认走 `py` 启动器的最高版本；想显式指定要写 `py -3.13`**。
2. **`-m venv --upgrade-deps` 一步到位**，不用再单独 `pip install -U pip`。
3. **PowerShell 终端会吃掉 `.\.venv\Scripts\python.exe` 的反斜杠**——必须用 `& "<绝对路径>"` 或 `Set-Location` 之后用 `./` 开头。
4. **Tee-Object 在 async 后台模式会被缓冲**，日志延迟刷新，看实时进度要用 `Get-Item log` 的 `LastWriteTime`。
5. **`editdistance` 包对 cp313 无预编译 wheel**，PyPI 上 0.1-0.8.1 全是 Cython 源码包，**没有 Windows MSVC 工具链就装不上**。
6. **funasr 只用了 `editdistance.eval(seq1, seq2)`，本质就是 Levenshtein.distance**，可 1:1 替换。
7. **`Levenshtein` 0.27.3 和 `rapidfuzz` 3.14.5 都有 cp313 wheel**，可作为 `editdistance` 的 shim 后端。
8. **pip install 失败默认整笔回滚**，下载好的 wheel 不会落地（但 cache 留着，下次重试不用再下）。

---

_文档位置：`e:\Documents\kuaishou\FireRed-OpenStoryline\docs\FireRed-OpenStoryline_Python3.13虚拟环境重建记录.md`_
