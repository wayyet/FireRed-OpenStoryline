---
name: jianying-inject-text-fx
description: 给"已存在"的剪映 (JianYing Pro) 5.9 草稿的字幕批量注入 VIP 文字动画（入场/循环/出场）与 VIP 花字，做成治愈系/卡点 Vlog 那种精致字幕。做法是直接改 draft_content.json / draft_info.json 双 JSON：文字动画从 pyJianYingDraft 的 text_intro/text_loop/text_outro 元数据取 resource_id/effect_id 挂到 material_animations；花字没有公开 ID 库，走"让用户在剪映客户端手挑一条样本→从草稿提取样本→批量克隆到其余字幕"的套路。内置「历史已用黑名单」防复用——每轮动画/花字方案不得与之前视频重复，选型前查记忆 kuaishou-fx-used-history 并集排除、脚本 BANNED+assert 硬校验、注入后回写记忆；附带批量统一字幕字号能力。dry-run 校验后带备份写入，绕开损坏的 venv。适用于"给剪映字幕加动画""字幕加入场出场动画""给字幕加花字""治愈系 Vlog 字幕美化""批量给字幕套同一花字""换一套新的字幕动画""统一字幕字号"等场景。触发词：剪映字幕动画、剪映花字、字幕加动画、注入文字动画花字、剪映字幕字号、jianying inject text fx。
---

# 给已有剪映草稿的字幕注入 VIP 文字动画 + 花字

对**已存在**的剪映 5.9 草稿，给字幕轨的每条字幕批量加 **VIP 文字动画**（入场 in / 循环 loop / 出场 out）与 **VIP 花字**（text_effect）。核心原则：
**直接改双 JSON，只往字幕轨的 segment 和 materials 上追加，不破坏已调好的画面/转场/特效**——不经 pyJianYingDraft 运行时（本机 venv 已坏），用系统 Python 解析元数据 + 手写 JSON 注入。

> 适用前提：草稿**已经存在**（有 `draft_content.json`）且**已经有字幕轨**（text track）。
> - 加转场 / 视频特效 → 用 `jianying-inject-fx`。
> - 变速 / 删减 / 加主副标题文字 → 用 `jianying-draft-edit`。
> - 从零生成草稿 → 用 `openstoryline-to-jianying` / `jianying-editor`。
> 本 skill 专注"往已有字幕上挂文字动画 + 花字"（附带批量调字号）。

相关记忆：真实路径 [[kuaishou-actual-paths]]、venv 坑 [[kuaishou-venv-broken-py313]]、
原始沉淀 [[jianying-text-anim-flower]]、**历史已用黑名单 [[kuaishou-fx-used-history]]**、姊妹技能思路 [[jianying-inject-transition-effect]]。

---

## 0. 先启用的工作流

本项目默认配套：`/chinese-outcome`（全程中文）、`/confirm-me`（花字/动画的审美取向、以及"是否手挑样本"等需用户拍板的点先确认）、
`/windows-shell-commands`（只用 PowerShell / 系统 python，命令内禁用中文引号）。

## 1. 环境：绕开损坏的 venv

项目 `e:\Documents\kuaishou\venv` 的基础解释器 Python312 已被删，**不要用它**。一律用系统解释器：

```
C:\Program Files\Python313\python.exe
```

只用标准库（`json` / `ast` / `uuid` / `copy` / `shutil`），无需装依赖。脚本首行务必：

```python
import sys; sys.stdout.reconfigure(encoding='utf-8')   # 防中文乱码
```

## 2. 定位草稿并摸清字幕轨

草稿根目录（注意真实盘符/用户名 = e盘 / wayyet）：

```
C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>
```

用系统 python 读 `draft_content.json`，先搞清楚：
- **字幕轨（`type=="text"`）有几条、每条几段**——本 skill 假设 1 条字幕轨；把 segment 按 `target_timerange.start` 排序，段数就是要处理的字幕数。
- 每段的 `target_timerange.duration`（微秒），决定动画的 start/duration。
- `materials.texts` 里每段对应的文案（判断主题、给花字定基调）。
- **是否已经有 `material_animations` / `type=="text_effect"` 的 effects**（避免重复注入；脚本里对此要 `assert` 硬拦，见 §9）。

## 3. 定位 VIP 文字动画 ID 库

文字动画元数据在 pyJianYingDraft 的 metadata 里（本机真实路径）：

```
e:\Documents\kuaishou\.claude\skills\jianying-editor\scripts\vendor\pyJianYingDraft\metadata\
    text_intro.py    # 入场动画  AnimationMeta（VIP 78）
    text_loop.py     # 循环动画  AnimationMeta（VIP 52）
    text_outro.py    # 出场动画  AnimationMeta（VIP 46）
```

构造签名（**第 2 个位置参数就是 is_vip**，别数错）：

```
AnimationMeta(title, is_vip, duration_s, resource_id, effect_id, md5)
```

用 `ast` 解析最稳（别用正则 / inline `-c`，见踩坑 #2）。只挑 `is_vip is True` 的项，记下 `title / resource_id / effect_id / duration_s`。

## 4. 历史零复用：选型前先过黑名单（用户硬规则）

用户明确要求：**每个新视频草稿的文字动画与花字都不得与之前任何一轮重复**（"不重复使用上次用过的"）。
复用旧款会被直接打回重做，所以这一步在出方案**之前**做，流程：

1. **读记忆 [[kuaishou-fx-used-history]]**，取**全部历史轮次**的文字动画标题并集 + 花字 resource_id 并集
   （2026-07-05 时点已有：大岭村 10 款动画、永华 19 款动画、花字 7160597532043644174 潮酷白色发光立体）。
2. 注入脚本顶部写死黑名单并**硬校验**（别靠人眼核对）：

   ```python
   BANNED = {"星光闪闪 II", "消散", "模糊发光", ...}   # 历史全部轮次并集
   for entry in ANIM_PLAN:
       for a in entry["anims"]:
           assert a["title"] not in BANNED, f"动画 {a['title']} 之前已用过, 禁止复用!"
   ```
3. **花字同样零复用**：历史样本的 resource_id 也在禁用之列 → 让用户在客户端**重新挑一款新的**做样本；
   脚本探测到样本后核对其 `resource_id` 不在历史名单里，撞了就中止并请用户换款。
4. 注入成功后，把本轮全部动画标题 + 花字（名称 + resource_id）**回写进记忆 [[kuaishou-fx-used-history]]**，供下一轮排除。

与姊妹技能 `jianying-inject-fx` 的 `BANNED_*` / strip 思路一致（那边管转场/特效，这边管文字动画/花字）。

## 5. 出方案 → 让用户拍板（confirm-me）

**先做功课再配动画**（2026-07-05 永华艺术馆一轮验证的打法）：

1. **搜主题资料 + 平台趋势**：到网上搜草稿主题（景点背景、题材）与抖音/小红书当期吸睛玩法
   （如"黄金 3 秒钩子""新中式国风热"），设计有依据、汇报时带来源。
2. **叙事映射**：把字幕按叙事段落分组（开场钩子 / 主体展品 / 氛围慢境 / 种草 CTA），每组配动画并写明"为什么"——
   例：`激光雕刻` 呼应木雕主题、开场 1-2 条给强入场+循环抓黄金 3 秒、结尾 `放大震动`+`强调三遍` 做 CTA 重锤。
3. **调性对齐**：与草稿现有转场/特效方案同一气质（如转场是「鎏金聚光」，字幕就配「鎏金雕刻」）。
4. **给 2-3 套带叙事映射的候选**，用 `AskUserQuestion` 让用户选。**审美是用户的决定，不要替他定。**

治愈系 Vlog 的经验取向：入场用"打字机/渐显/弹入"这类柔和款，循环用轻微呼吸/波动，出场用渐隐；花字选暖色描边、不抢画面的款。
（以上仅是取向，具体款式仍要先过 §4 黑名单。）

## 6. 文字动画的挂载写法（关键）

给每条字幕 segment 挂一个 `material_animations` 条目，再把它的 id 追加到该 segment 的 `extra_material_refs`：

```jsonc
// materials.material_animations 里新增一条
{
  "id": "<新 uuid hex>",
  "type": "sticker_animation",
  "multi_language_current": "none",
  "animations": [
    { "anim_adjust_params": null, "platform": "all", "panel": "",
      "material_type": "sticker", "name": "<title>", "id": "<effect_id>",
      "type": "in", "resource_id": "<resource_id>", "start": 0, "duration": <微秒> }
    // out / loop 各再来一个对象，放进同一个 animations 数组
  ]
}
```

**start / duration 规则**（与 pyJianYingDraft 一致，`seg_dur` = 该段 duration，微秒）：
- 入场 `in`：`start=0`，`duration=min(动画时长, seg_dur)`。
- 出场 `out`：`start=seg_dur - dur`，`duration=min(动画时长, seg_dur)`。
- 循环 `loop`：`start=0`，`duration=seg_dur - 出场时长`（有出场就要扣掉，否则填满整段）。
- 数组顺序：**先入/出场，后循环**（脚本里 `sorted(... 0 if type in (in,out) else 1)`）。

一条 segment 只挂**一个** `material_animations` 条目，多种动画共存于它的 `animations` 数组。

## 7. 花字（text_effect）的套路：手挑样本 → 批量克隆

**本机缓存与 pyJianYingDraft 都没有花字 ID 库，网上也查不到成规模列表。** 所以走这个可靠套路：

1. **让用户在剪映客户端**：打开该草稿 → 给**任意一条**字幕挑好想要的 VIP 花字 → **保存并关闭剪映**。
   （`/confirm-me`：这一步必须用户亲自操作，脚本无法凭空造花字 id。**每一轮都要挑新款**——旧款 resource_id 已进 §4 黑名单。）
2. 脚本从草稿里提取样本：`materials.effects` 中 `type=="text_effect"` 的条目（`effect_id==resource_id`，
   缓存实体在 `...\Cache\artistEffect\<resource_id>\<md5>`）。找到引用它的那条 segment，并核对 resource_id 不在历史黑名单。
3. **批量克隆到其余字幕**：
   - 每条目标字幕**深拷贝**样本 material（换新 uuid）→ append 到 `materials.effects` → 该 segment 的 `extra_material_refs` 追加新 id。
   - **同步文字样式**：样本字幕 `materials.texts` 里 content 内嵌 JSON 的 `styles[0]`（含 `effectStyle: {id, path}`）
     整个复制给目标字幕，`range` 改成 `[0, len(该字幕 text)]`；顶层字段的 diff（实测是 `check_flag: 15→7`、`border_color`）也同步过去。
4. 样本那条**跳过**（它自己已经有花字了）。

## 8. 双 JSON 等价注入

草稿有 `draft_content.json`（剪映最近保存的**活文件**）和 `draft_info.json`，两者结构一致、`id` 相同。
**两份都要做等价注入**（同样片段位置、共用同一套新 uuid），以防剪映回退读取到未改的那份。
实测旧 `draft_info.json` 可能已分叉/含悬空引用 → 直接写入与 content 等价的内容即可修复。

## 9. dry-run → 备份 → 写入 → 校验

用脚本模板 `scripts/build_text_fx.py`（见本目录）：

1. **dry-run**（默认，不带参数）：核对字幕段数 == 方案条数、每个动画存在且 VIP、**方案全员通过 §4 黑名单 assert**、
   **草稿里没有已注入的 `material_animations`**（有则先确认是二次注入还是要剔除重做）、探测到花字样本且不撞历史款、打印每条字幕的注入预览。
2. **写入**（`--apply`）：先给两个 JSON 各打时间戳 `.bak`，再写入（`json.dump(..., ensure_ascii=False, separators=(",",":"))`）。
3. **完整性校验**：JSON 可序列化 + 每个新 `material_animations` / `text_effect` 都被某段引用 + **总时长不变** + 段数不变。

```powershell
& "C:\Program Files\Python313\python.exe" .\scripts\build_text_fx.py            # dry-run
& "C:\Program Files\Python313\python.exe" .\scripts\build_text_fx.py --apply    # 备份并写入
```

## 10. 必须执行：批量统一字幕字号

**本节是强制步骤，不是可选的附带能力**——只要涉及字幕字号调整（无论用户是在注入完成后追加"把字号统一调成 N"，
还是单独提出调字号需求），以下步骤**必须全部执行，不可省略、不可简化**（2026-07-05 永华一轮实测：8 太小 → 最终 10；16:9 横屏建议 10 起步）：

1. **必须先重新读取草稿现值、逐条 diff**：禁止直接照方案盲写。用户很可能在两轮脚本之间又在客户端手改过个别条
   （实测同一草稿两次调字号之间，用户手改了第 1、2、4 条），已达标的条目跳过，不得拿上一轮结果当现状。
2. **字号必须双字段同步修改，缺一不可**，否则会出现客户端显示与面板数值不一致：
   - text material 顶层 `font_size`（float，如 `10.0`）；
   - `content` 内嵌 JSON 的 `styles[*].size`（int，如 `10`）。
3. **必须依次完成 dry-run → `pre_fontsize_<时间戳>.bak` 备份 → 双 JSON 等价写入 → 写入后逐条复核两个字段**，任何一步都不得跳过。
4. **写入前必须确认剪映已关闭**（哪怕只是改字号这种小动作），否则内存里的旧版本会在保存时覆盖写入结果。
5. 模板：`scripts/set_fontsize.py`（改顶部 `DRAFT` / `TARGET_SIZE`）。已注入的动画/花字不受影响。

## 11. 收尾必须告知用户的 4 件事

1. **VIP 素材需客户端下载**：脚本只写入 `resource_id` 引用；实际动画/花字渲染文件要在
   **剪映客户端（VIP 已登录 + 联网）打开草稿时自动下载**后才生效（下载完成前字幕可能短暂显示为普通样式）。
2. **剪映若正开着该草稿，先关闭再重开**，否则内存里的旧版本会在保存时覆盖注入结果。
   （花字样本那一步本来就要求用户关闭剪映，注入后再重开即可。）
3. **备份可回滚**：草稿目录下已生成 `draft_content.json.pre_textfx_<时间戳>.bak` 等，随时可还原。
4. **本轮清单已回写记忆**：把本轮用的动画全名单 + 花字（名称 + resource_id）写入 [[kuaishou-fx-used-history]]，
   并告诉用户"下个视频选型时会自动并集排重"。

不擅自启动剪映去"可视化确认"（可能覆盖草稿），需要时先问用户。

---

## 踩坑清单（真实教训：2026-07-02 大岭村_治愈系Vlog、2026-07-05 广州永华艺术馆 两轮验证）

1. **venv 已损坏**：`e:\Documents\kuaishou\venv` 基础解释器 Python312 被删。用 `C:\Program Files\Python313\python.exe`。
2. **inline `python -c` 反斜杠转义翻车**：Windows 路径里的 `\` 会 `SyntaxError`。一律 `Write` 一个 `.py` 文件再运行，别塞 `-c` / heredoc。
3. **AnimationMeta is_vip 位置数错**：`AnimationMeta(title, is_vip, duration_s, resource_id, effect_id, md5)`——**第 2 个**位置参数才是 is_vip，拿不准先读 `effect_meta.py` 确认签名。
4. **动画时长 / start 算错**：出场 `start=seg_dur-dur`；循环要**扣掉出场时长**再填满；动画 duration 不能超过 seg_dur。数组要先 in/out 后 loop。
5. **花字没有 ID 库**：别去猜/搜花字 id。唯一可靠路径 = 让用户在客户端手挑一条样本，脚本再从草稿提取克隆。
6. **剪映把样本写重复**：客户端手动加花字保存后，样本 material 可能在 `materials.effects` 里**重复 2 条**、segment ref 也重复 2 次——这是剪映自身行为，**不要"修复"**，注入时把样本段整体跳过即可。校验"素材全部被引用"时注意同 id 可能多条。
7. **花字不止是加 effect**：还要把样本字幕的 content `styles[0]`（含 `effectStyle`）克隆给目标字幕并改 `range`，否则花字样式不生效；顶层 `check_flag` / `border_color` 等 diff 也要同步。
8. **只改一份 JSON 被回退**：必须对 `draft_content.json` 和 `draft_info.json` **双份等价注入**。
9. **VIP 只是 id 引用**：不写入实际素材文件，需剪映客户端 VIP + 联网打开自动下载；否则界面里空白。
10. **剪映内存覆盖**：草稿开着时改 JSON，保存会被覆盖 → **每一轮写入（包括调字号这类小改）都要先确认剪映已关闭**。
11. **中文乱码**：脚本 `sys.stdout.reconfigure(encoding='utf-8')`；PowerShell 侧 `$env:PYTHONIOENCODING='utf-8'`，命令内禁用中文引号。
12. **复用旧动画/旧花字会被用户打回**：零复用是硬规则不是建议。选型前先读 [[kuaishou-fx-used-history]] 取历史并集，
    脚本 `BANNED` 集合 + `assert` 硬校验（永华一轮 19 款动画全部为新款就是这么保证的）；花字样本 resource_id 同样核对；注入后回写记忆。
13. **两轮脚本之间用户会在客户端手改**：实测两次调字号之间用户手改了第 1、2、4 条的字号——写入前必须**重读草稿现值逐条 diff**、跳过已达标项，不要拿上一轮脚本的结果当现状盲写。
14. **字号是双字段**：`font_size`（float，material 顶层）与 `styles[*].size`（int，content 内嵌 JSON）必须同时改，只改一个客户端显示与面板数值会不一致。
15. **防重复注入**：注入动画前 `assert not materials.material_animations`；已有注入时停下来向用户确认（是补注入、还是剔除重做——剔除思路参考 `jianying-inject-fx` 的 strip 模式）。

## 参考脚本

- `scripts/build_text_fx.py` — 注入脚本模板（dry-run 校验 + `--apply` 双 JSON 备份写入）。
  用时改顶部 `DRAFT` 路径、`ANIM_PLAN`（按字幕轨 segment 顺序，每条列 in/loop/out 的 title+resource_id+effect_id+duration_s）、
  `BANNED` / `BANNED_FLOWER_RIDS`（从 [[kuaishou-fx-used-history]] 取历史并集）；
  花字自动探测草稿里用户手挑的样本并克隆到其余字幕，无样本时自动只注入动画。
- `scripts/set_fontsize.py` — 批量统一字幕字号模板（dry-run + `--apply`，双字段、跳过已达标、备份复核）。
  用时改顶部 `DRAFT` / `TARGET_SIZE`。
