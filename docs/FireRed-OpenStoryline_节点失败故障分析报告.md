# FireRed-OpenStoryline 节点失败故障分析报告

**分析日期**：2026-07-06
**分析对象**：`http://127.0.0.1:7860` 网页会话中「吉隆坡 EXCHANGE TRX 商场旅行 Vlog」剪辑任务
**结论一句话**：模型 API 本身是通的（实测 HTTP 200），页面上「内部模型出了点小问题」的猜测不成立。真正的根因是本地抽帧库 moviepy 崩溃、MiniMax-M3 推理模型的 `<think>` 思考段吃光 token 预算、以及两处错误处理代码自身的 bug 把真实错误掩盖了。

---

## 1. 系统架构：一次「理解素材」要经过几道手

OpenStoryline 运行时是两个进程协作：

```
用户在网页上聊天
   ↓
[进程A] 网页服务 agent_fastapi (端口 7860)
   │  聊天代理（Agent）住在这里，决定调用哪个工具
   ↓  MCP 协议调用工具
[进程B] MCP 服务 (端口 8001)
   │  understand_clips、generate_script 等"节点"住在这里
   ↓  节点想调大模型时不能自己调，而是通过 MCP 的
   │  sampling 机制"反向"发请求回进程A
[进程A] sampling_callback 收到请求：
   │  1. 用 moviepy 从视频里抽几帧图，转成 base64
   │  2. 把图 + 提示词发给 MiniMax-M3 API
   ↓
MiniMax 云端 API
```

关键点：节点自己不直接碰模型 API，而是喊一嗓子"帮我问下模型"，真正抽帧、发 HTTP 请求的是网页服务进程里的回调函数。这个"绕一圈"的设计是后续错误信息层层失真的根源。

---

## 2. 报错①：understand_clips「画面理解失败 / 服务持续异常」

**结论：模型根本没被问到，请求在抽帧阶段就已经崩溃。**

### 故障链（三个 bug 叠罗汉）

**第一环：moviepy 读不了 iPhone 视频的元数据**

素材是 iPhone 拍的 HEVC 视频（Main 10 / bt2020 / -90° 旋转），文件里带一行少见的元数据：

```
Ambient Viewing Environment, ambient_illuminance=314.000000, ...
```

moviepy 2.1.2 解析 ffmpeg 输出时有个兼容性 bug：跨行元数据做字符串拼接时执行了 `float + str`：

```python
# moviepy 内部 ffmpeg_reader.py:548
value = self._current_stream["metadata"][field] + "\n" + value
#       ↑ 这是个 float                            ↑ 这是 str  → TypeError
```

`VideoFileClip(path)` 一打开文件就炸——抽帧第一步就失败。已用真实的 `clip_0001.mp4` 在项目 `.venv` 中复现，几乎瞬间崩溃（解释了为什么页面上两次失败间隔只有十几秒，而非网络超时的量级）。

**第二环：sampling_handler 的错误处理自身有 bug**

```python
try:
    media_blocks = build_media_blocks(...)     # 第354行，moviepy 在这里炸了
    ...
    model_name = getattr(model, "model", ...)  # 第397行，还没执行到
    resp = await bound.ainvoke(...)
except Exception as e:
    return CreateMessageResult(
        text=f"{type(e)}: {e}",
        model=str(model_name),   # model_name 从未被赋值 → UnboundLocalError
    )
```

except 块引用了只在 try 块后半段才赋值的变量。异常发生在赋值之前时，except 块自己再抛一次 `UnboundLocalError`，导致整个 sampling 请求以硬错误告终，而不是把真实错误文本传回去。

**第三环：understand_clips 节点的错误分支引用了不存在的变量**

```python
if raw is None:
    out_item["caption"] = "Error: VLM request failed"
    try:
        raw_score = obj.get("aes_score")   # obj 在这个循环里从未被赋值！
        ...
    except (ValueError, TypeError, AttributeError):  # 捕不到 UnboundLocalError
        ...
```

`obj` 是解析成功后才会赋值的变量，错误分支里根本不存在该变量；且 `UnboundLocalError` 是 `NameError` 的子类，不在 except 捕获列表内。本来只想记一笔"这个片段理解失败"，结果整个节点崩溃。`session_state.json` 中的堆栈原文：

```
File ".../understand_clips.py", line 144, in process
    raw_score = obj.get("aes_score")
UnboundLocalError: cannot access local variable 'obj' where it is not associated with a value
```

### 小结

真凶是 moviepy 兼容性 bug，但两层错误处理各自翻车，把真实错误信息层层吞掉，最后页面上只剩语义完全跑偏的"内部模型出了点小问题"。

---

## 3. 报错②：generate_script「LLM did not generate any content」

**结论：推理模型把 token 预算全部吃在了"思考"上，真正的答案没有生成空间。**

### 背景知识：推理模型（reasoning model）

MiniMax-M3 这类模型回答前会先"思考"，且思考过程直接混在返回正文里：

```
<think>用户问这张图主要是什么颜色，要求一个词回答……</think>

红色
```

`<think>` 里的内容同样计入 output token，计入 `max_tokens` 预算。用项目自带的 `test_api.py` 实测，`max_tokens=32` 时：

```
<think>用户问这张图主要是什么颜色……从描述来看，"红"</think>
（后面什么都没有）
```

思考到一半预算用完，真正的答案一个字没出来。

### 对照 generate_script 节点

节点任务是"为 34 个片段写文案，返回严格 JSON"，固定 `max_tokens=4096`：

```python
raw_text = (group_text_map.get(gid) or "").strip()
if not raw_text:
    raise ValueError("LLM did not generate any content, please retry")
```

M3 面对这种任务思考段很长，4096 全被 `<think>` 吃掉或 JSON 写到一半被截断，解析函数找不到任何 group 文案，抛出上述报错。会话记录显示每次尝试跑了 60~80 秒才失败——模型确实在认真"思考"，只是产出全是"想法"没有"答案"。重试 4 次、换模式、缩短 prompt 均无效，因为问题不在 prompt，而在 token 预算的分配方式。`group_clips`"分组失败走默认兜底"是同一根因。

### 为什么网页聊天一直正常

| | 聊天代理 | 工具节点 |
|---|---|---|
| 调用方式 | streaming（流式） | 非流式 |
| 对输出的要求 | 自由文本 | 严格 JSON |
| `<think>` 的下场 | 当"思考过程"展示给用户 | 污染/挤占 JSON 输出 |

同一个模型，两种用法，导致"聊天很聪明、干活全失败"的现象。

---

## 4. 报错③：search_media 搜索失败

`config.toml` 中 `[search_media] pexels_api_key = ""` 未配置 key，搜图失败属预期行为，代理已正确识别并跳过。

隐藏关联问题：`[vlm] timeout = 20` 秒且非流式——即使修好抽帧，推理模型带图出 JSON 大概率超 20 秒，仍会失败。

---

## 5. 排查方法说明

- playwright-cli 本地 shim（`npx --no-install` 转发）因全局未装包而失败，改用 Edge Tools 已开启的 CDP 调试端口 9222，通过系统 Python + `websockets` 直连读取 `http://127.0.0.1:7860` 页面全文。
- 用 `test_api.py` 独立验证 MiniMax-M3 的 LLM/VLM 连通性，均返回 HTTP 200，排除"API 本身不可用"的猜测。
- 在项目 `.venv` 中直接调用 `_build_media_blocks()` 复现 moviepy 崩溃。
- 从 `outputs/<session_id>/session_state.json` 中提取完整异常堆栈，确认两处 `UnboundLocalError`。

---

## 6. 修复建议

| 序号 | 修什么 | 怎么修 |
|------|--------|--------|
| 1 | 抽帧崩溃 | 首选：`sampling_handler` 抽帧改用 ffmpeg 命令直抽，绕开 moviepy 的元数据解析器；备选：升级 moviepy 版本验证是否修复 |
| 2 | 两处错误处理 bug | `model_name` 提前初始化为默认值；`understand_clips.py:144` 的 `obj` 改为直接赋值 `-1.0`，不再引用未定义变量 |
| 3 | `<think>` 吃预算 | 节点调用 `max_tokens` 提升至 8192+，解析 JSON 前先剥离 `<think>...</think>`；或结构化输出任务改用非推理模型 |
| 4 | VLM 超时 | 20 秒 → 120 秒 |
| 5 | Pexels | 补配 `pexels_api_key`，或维持当前跳过逻辑 |

**给中级工程师的三条经验**：

1. 错误信息穿过的每一层都可能失真，排查多进程系统时应直取最内层原始堆栈（本例中藏在 `session_state.json`），不要只信最外层文案。
2. except 块本身也是代码，也会有 bug。写兜底逻辑时应自问：若异常发生在 try 的第一行，这个 except 是否还能安全执行？
3. 接入推理模型需要改变旧契约：`max_tokens ≈ 答案长度` 的假设失效，预算 = 思考 + 答案。要么调大预算并剥离 `<think>` 再解析，要么为结构化输出任务换非推理模型，要么改用流式 + 宽松超时。

---

*相关记忆条目：`openstoryline-minimax-m3-moviepy-bugs`（已存入项目记忆库）*
