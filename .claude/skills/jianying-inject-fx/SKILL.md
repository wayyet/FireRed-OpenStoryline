---
name: jianying-inject-fx
description: 给"已存在"的剪映 (JianYing Pro) 5.9 草稿就地注入 VIP 转场与 VIP 特效，做成吸引眼球、适配抖音/小红书的成片。做法是直接改 draft_content.json / draft_info.json 双 JSON，从 pyJianYingDraft 的 metadata 里取官方素材的 resource_id/effect_id，转场挂到前一片段、特效走独立 effect 轨，dry-run 校验后带备份写入，绕开损坏的 venv。支持「历史已用黑名单」防撞车（每轮方案不得与之前重复）与「剔除旧注入再替换」模式。适用于"给剪映草稿加转场""加特效""加 VIP 转场/特效""换一套新转场特效""做治愈系/卡点 Vlog 转场""参考抖音小红书优化成片"等场景。触发词：剪映加转场、剪映加特效、注入 VIP 转场特效、剪映转场方案、替换转场特效、jianying inject fx。
---

# 给已有剪映草稿注入 VIP 转场 + 特效

对**已存在**的剪映 5.9 草稿，就地加入 VIP 转场与 VIP 特效。核心原则：
**直接改双 JSON，只新增/追加，不破坏已调好的轨道与片段**——不经 pyJianYingDraft 运行时（本机 venv 已坏），用系统 Python 解析元数据 + 手写 JSON 注入。

> 适用前提：草稿**已经存在**（有 `draft_content.json`）。
> - 只做变速/删减/加标题 → 用 `jianying-draft-edit`。
> - 从零把素材生成草稿 → 用 `openstoryline-to-jianying` / `jianying-editor`。
> 本 skill 专注"往已有片段上挂转场 + 加特效轨"，含"剔除上一轮注入、整体换新方案"。

相关记忆：真实路径 [[kuaishou-actual-paths]]、venv 坑 [[kuaishou-venv-broken-py313]]、
本 skill 的原始沉淀 [[jianying-inject-transition-effect]]、
**已用转场/特效历史清单 [[kuaishou-fx-used-history]]（选型前必查）**。

---

## 0. 先启用的工作流

本项目默认配套：`/chinese-outcome`（全程中文）、`/confirm-me`（审美取向等需用户拍板的点先确认）、
`/windows-shell-commands`（只用 PowerShell / 系统 python，命令内禁用中文引号）。

## 1. 环境：绕开损坏的 venv

项目 `e:\Documents\kuaishou\venv` 的基础解释器 Python312 已被删，**不要用它**。
一律用系统解释器：

```
C:\Program Files\Python313\python.exe
```

只用到标准库（`json` / `ast` / `uuid` / `shutil`），无需装依赖。脚本首行务必：

```python
import sys; sys.stdout.reconfigure(encoding='utf-8')   # 防中文乱码
```

## 2. 定位草稿并摸清现状

草稿根目录（注意真实盘符/用户名 = e盘 / wayyet）：

```
C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>
```

用系统 python 读 `draft_content.json`，先搞清楚：画幅（竖屏 1080×1920 才适配抖音/小红书）、
总时长、**视频轨片段数与各段时长**、字幕文案（判断主题）、**是否已有转场/特效（列出名字）**。
片段的衔接点数 = 片段数 − 1，就是可加转场的位置数。

已有转场/特效的名单决定走哪条路：草稿干净 → **全新注入**（§8 用 `build_fx.py`）；
草稿里有上一轮注入 → **剔除再注入**替换模式（§8 用 `build_fx_strip.py`）。

## 3. 定位 VIP 素材 ID 库

素材元数据在 pyJianYingDraft 的 metadata 里（本机真实路径）：

```
e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor\pyJianYingDraft\metadata\
    transition_meta.py       # 转场 TransitionMeta（共 433，VIP 303）
    video_scene_effect.py    # 视频特效 EffectMeta（共 1097，VIP 462）
```

构造签名（**第 2 个位置参数就是 is_vip**，别数错）：

- `TransitionMeta(name, is_vip, resource_id, effect_id, md5, default_duration_s, is_overlap)`
- `EffectMeta(name, is_vip, resource_id, effect_id, md5, params)`

用 `ast` 解析最稳（别用正则/inline `-c`，见踩坑 #2）。只挑 `is_vip is True` 的项。
详细字段定义在同目录 `effect_meta.py`，拿不准先读它确认参数顺序。
用户问"一共有多少 VIP 素材"之类的统计问题时，**现场跑脚本实测**，别背文档数字。

## 4. 硬规则：不复用历史已用配置（每轮必查）

用户明确要求：**每个新视频 / 每轮新方案的转场与特效，不得与之前任何一轮重复**。流程：

1. 先读记忆 [[kuaishou-fx-used-history]]，把**所有轮次**的转场/特效名**取并集**做黑名单 `BANNED_*`。
2. 若本次是替换同一草稿的上一轮注入，上一轮的名单同时就是"剔除清单" `STRIP_*`。
3. 选型只从 `VIP 全集 − 黑名单` 里挑；脚本里对每个新素材 `assert name not in BANNED` 双保险。
4. **注入成功后滚动更新该记忆**（追加本轮配置 + 日期 + 草稿名），下轮自动排除。

## 5. 调研审美取向（用户明确要参考抖音/小红书时）

`WebSearch` 关键词如「治愈系 vlog 剪映 转场 特效 古村 citywalk」「新中式 国风 短视频 吸睛 特效」。落到可执行的原则：

- 慢节奏 / 风景 / 治愈类 → 用**模糊·光斑·漏光·叠化**类**柔转场**，时长 0.3–1.1s，切换自然不突兀。
- 中式古典 / 艺术馆 / 国风题材 → 抖音「新中式」搜索量同比 +230%、国风词条 4.3 亿次搜索，
  **鎏金·光影·聚光**类质感是这类内容的吸睛主流（如：聚光灯、金沙、发光变焦、金色辉光）。
- 前 3 秒是**黄金钩子**（完播率生死线）：开幕类特效（"竖向开幕""拉镜开幕"）+ 悬念文案。
- 结尾加**氛围特效 + 互动提问**提评论/转发；叙事转折点（如"推开门"）可加点缀特效强调。
- 全片铺一层**统一色调特效**（如"胶片暖棕""金色辉光"）让画面高级不杂乱。
- 转场时长可直接用 metadata 的 `default_duration_s`（如"金沙"1.74s），不必都压到 1s，只要满足 §7 的时长约束。

## 6. 出方案 → 让用户拍板（confirm-me）

从 VIP 库筛候选（先过 §4 黑名单），组 2–3 套完整方案（每套：全部衔接点转场 + 铺底/钩子/点缀特效），
用 `AskUserQuestion` 让用户选。**审美是用户的决定，不要替他定**。

每套方案给**叙事映射表**：哪个衔接点/时间段 → 用什么素材 → 对应什么画面叙事意图
（例：衔接点 4"推开云龙木门"→ 转场"虹光旋入"→ 开门瞬间的光影旋转）。
调研得到的数据依据（搜索热度、趋势）一并列出，用户更好拍板。

## 7. 确认挂载写法（写入前的关键）

**转场**：写进 `materials.transitions`，字段见 `Transition.export_json`：
`category_id/category_name`(空)、`duration`(微秒)、`effect_id`、`id`(32位hex)、`is_overlap`、
`name`、`platform="all"`、`resource_id`、`type="transition"`。
再把该 `id` 追加到**前一个**视频片段的 `extra_material_refs`（**勿动**已有的 speed/canvas 等 ref）。
约束：**转场时长 ≤ 相邻两片段较短者**。最后一个片段不加转场。

**特效**：用独立 `effect` 轨（`type="effect"`，`render_index` 从 10000 起，`attribute=0`、`flag=0`），
每段引用 `materials.video_effects` 里的 `video_effect`（`apply_target_type=2` 全局、`type="video_effect"`）。
EffectSegment 只有 BaseSegment 字段（无 source_timerange/clip/speed）。
**同一特效轨的片段不能时间重叠**——全片铺底 + 首尾点缀就得**分多条特效轨**（render_index 10000, 10001…）。

## 8. 替换模式：剔除旧注入再注入（strip → inject）

草稿里已有上一轮注入时，**同一脚本内先剔除再注入、一次写盘**（模板 `scripts/build_fx_strip.py`）：

- **转场剔除**：按名字从 `materials.transitions` 删条目，并把对应 `id` 从视频片段
  `extra_material_refs` 中移除（其余 speed/canvas 等 ref 原样保留）。
- **特效剔除**：按名字从 `materials.video_effects` 删条目；**整条轨的 segments 全部属于旧特效才删整轨**
  （`mat_ids <= old_eids`），混有别的素材就不能整轨删（需段级处理，避免误删用户自己加的特效）。
- 剔除后 `duration` 必须不变；剔除统计（转场 n 个 / 片段引用 n 处 / 特效 n 个 / 特效轨 n 条）打进 dry-run 报告。

## 9. 双 JSON 等价注入

草稿有 `draft_content.json`（剪映最近保存的**活文件**，修改时间通常更新）和 `draft_info.json`。
两者结构一致、`id` 相同，但 md5 不同。**两份都要做等价注入**（按同样的片段位置、共用同一套 uuid），
以防剪映回退读取到未改的那份。

**uuid 必须在脚本模块级生成一次、两份文件共用**——若写在 `inject()` 函数里每个文件调用时现生成，
两份 JSON 的 id 就分叉了（模板已按模块级写法固定）。

## 10. 写入前：确认剪映客户端未运行

写入前先查进程，未运行才动手；在跑就请用户先关闭：

```powershell
Get-Process -Name JianyingPro -ErrorAction SilentlyContinue
```

比事后提醒可靠——客户端开着时其内存里的旧版本会在保存时直接覆盖注入结果。

## 11. dry-run → 备份 → 写入 → 校验

用脚本模板（全新注入 `scripts/build_fx.py`；替换模式 `scripts/build_fx_strip.py`）：

1. **dry-run**（默认，不带参数）：核对每个转场/特效存在且 `is_vip=True`、不撞黑名单、时长约束满足，
   打印（剔除与）注入后概览。
2. **写入**（`--apply`）：先给两个 JSON 各打时间戳 `.bak` 备份，再写入（`json.dump(..., ensure_ascii=False)`）。
3. **完整性校验**：JSON 合法 + 转场 id 全部被片段引用 + 特效 segment 的 material_id 全部存在 +
   总时长不变 + 轨道结构符合预期（video / effect… / text）。

```powershell
& "C:\Program Files\Python313\python.exe" .\scripts\build_fx_strip.py            # dry-run
& "C:\Program Files\Python313\python.exe" .\scripts\build_fx_strip.py --apply    # 备份并写入
```

**校验红线：每份文件只和"它自己"的备份/注入前状态比**。draft_info.json 的 `duration`
（如 50688000 vs draft_content 的 50700000）和片段 `extra_material_refs` 基数与 draft_content
天生不同——把 draft_content 的数字硬编码去套 draft_info 必出**误报 FAIL**。正确姿势：
每份文件各自 assert「duration 注入前后不变」「旧 refs 是新 refs 的子集」「新增 id 恰好是本轮注入的」。

## 12. 收尾必须告知用户的 4 件事

1. **VIP 素材需客户端下载**：脚本只写入官方素材的 `resource_id` 引用；实际渲染文件要在
   **剪映客户端（VIP 已登录 + 联网）打开草稿时自动下载**后才生效。
2. **剪映若正开着该草稿，先关闭再重开**，否则内存里的旧版本会在保存时覆盖注入结果
   （写入前本就该按 §10 查过进程）。
3. **备份可回滚**：草稿目录下已生成 `draft_content.json.pre_fx_<时间戳>.bak` 等，随时可还原。
4. **已用清单已入记忆**：本轮转场/特效已追加进 [[kuaishou-fx-used-history]]，下轮选型自动排除、不再撞车。

不擅自启动剪映去"可视化确认"（可能覆盖草稿），需要时先问用户。

---

## 踩坑清单（真实教训）

1. **venv 已损坏**：`e:\Documents\kuaishou\venv` 基础解释器 Python312 被删。用 `C:\Program Files\Python313\python.exe`。
2. **inline `python -c` 反斜杠转义翻车**：`path.split('\')` 会 `SyntaxError: unterminated string literal`。
   → 一律 `Write` 一个 `.py` 文件再运行，别塞 `-c` / heredoc。
3. **is_vip 位置数错**：`TransitionMeta`/`EffectMeta` 的**第 2 个**位置参数才是 is_vip，先读 `effect_meta.py` 确认签名再解析。
4. **转场挂错片段**：转场要挂在**前一个**片段的 `extra_material_refs`，且**追加**不覆盖（原有 speed/canvas ref 必须保留）。
5. **转场超时长**：转场 duration 必须 ≤ 相邻两片段中较短者，否则剪映异常；脚本里 assert 卡住。
6. **特效轨片段重叠**：同一 `effect` 轨上片段时间不能重叠，全片铺底 + 首尾点缀 → 拆成多条特效轨（render_index 递增）。
7. **只改一份 JSON 被回退**：必须对 `draft_content.json` 和 `draft_info.json` **双份等价注入**。
8. **VIP 只是 id 引用**：不写入实际素材文件，需剪映客户端 VIP + 联网打开自动下载；否则界面里空白。
9. **剪映内存覆盖**：草稿开着时改 JSON，保存会被覆盖 → 写入前 `Get-Process -Name JianyingPro` 查进程（§10）。
10. **中文乱码**：脚本 `sys.stdout.reconfigure(encoding='utf-8')`；PowerShell 侧 `$env:PYTHONIOENCODING='utf-8'`、命令内禁用中文引号。
11. **校验脚本跨文件硬编码基数 → 误报 FAIL**：draft_info.json 的 duration / refs 基数与 draft_content.json
    本来就不同；用 draft_content 的数字去校验 draft_info 必出假 FAIL，白排查半天。
    各文件只跟自己的备份差分对比（§11 校验红线）。
12. **双 JSON uuid 各自生成 → id 分叉**：uuid 要在模块级生成一次、两份文件共用；
    写在 `inject()` 里每文件调用就各是一套了（§9）。
13. **Write 工具覆盖已存在文件前必须先 Read**：复制模板到 scratchpad 改配置时直接 Write 会报
    `File has not been read yet`——先 Read 模板/目标文件再写（两轮会话都踩过）。
14. **新方案撞旧配置**：用户硬规则不许复用；选型前查 [[kuaishou-fx-used-history]] 并集黑名单，
    脚本 `assert name not in BANNED` 兜底（§4）。
15. **剔除删轨要整轨判断**：只有特效轨全部 segments 都属于旧注入才删整轨，混轨情况不能整删（§8）。

## 参考脚本

- `scripts/build_fx.py` — **全新注入**模板（草稿此前无注入）：dry-run 校验 + `--apply` 备份写入。
  用时改顶部 `DRAFT`、`TRANS_PLAN`（转场名，按视频轨片段顺序，挂前段）、`EFF_PLAN`（特效名 + 起止秒 + 轨号）。
- `scripts/build_fx_strip.py` — **替换模式**模板：历史黑名单断言 + 剔除旧注入（strip_old）+ 注入新方案，
  双 JSON 共用同一套 uuid、逐文件自校验。用时改顶部 `DRAFT`、`BANNED_*`（历史并集，查
  [[kuaishou-fx-used-history]]）、`STRIP_*`（本草稿要剔除的上一轮名单）、`TRANS_PLAN`、`EFF_PLAN`。
