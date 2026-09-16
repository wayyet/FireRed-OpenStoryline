---
name: jianying-inject-english-tts
description: 给"已存在"的剪映 (JianYing Pro) 5.9 草稿注入英文 AI 配音（English TTS 旁白音轨），只加配音、不动贴纸/字幕/转场特效——适用于中文字幕已翻译成英文字幕（jianying-translate-subtitles 之后）需要配套英文人声解说的场景。配音走剪映客户端同款 SAMI 接口，英文音色没有公开文档（官方音色页 JS 渲染抓不到），走"候选 ID 批量探测→转 mp3 用户试听拍板→逐句生成→只挂音频轨注入双 JSON"的套路；字幕里的排版符号（+/=/—）先改写成自然口语再配音。dry-run 校验后带备份写入，写入前后断言贴纸素材数量不变确保零误伤。适用于"给剪映草稿加英文配音""英文旁白""English TTS""英文字幕配英文人声""只加配音不加贴纸"等场景。触发词：英文配音、英文旁白、English TTS、剪映英文配音、注入英文配音、jianying inject english tts。
---

# 给已有剪映草稿注入英文 AI 配音（只配音，不动贴纸）

对**已存在**的剪映 5.9 草稿（通常是 `jianying-translate-subtitles` 已把字幕换成英文之后），
加一条**英文 TTS 旁白音轨**。核心原则：
**直接改双 JSON，只新增一条音频轨，其余一切（贴纸/字幕/转场/特效/BGM）零触碰**——
用系统 Python 生成音频 + 手写 JSON 注入，绕开损坏的 venv。

> 适用前提：草稿已存在且字幕是英文。
> - 中文配音 + 贴纸 → 用姊妹技能 `jianying-inject-tts-sticker`（本 skill 从它裁剪而来）。
> - 中文字幕翻英文 / 删旧中文配音 → 先走 `jianying-translate-subtitles`。
> 本 skill 专注"英文音色选型 + 只挂配音音轨"。

相关记忆：[[jianying-tts-sticker-inject]]（SAMI 接口与音色实测总表）、[[kuaishou-fx-used-history]]（音色零复用黑名单）、
[[kuaishou-actual-paths]]、[[kuaishou-venv-broken-py313]]。

2026-07-11 在 吉隆坡柏威年广场（英文字幕版，35.4s / 7 句字幕）上验证成功。

---

## 0. 先启用的工作流

`/chinese-outcome`（全程中文汇报）、`/confirm-me`（音色试听拍板、文案改写方式需用户确认）、
`/windows-shell-commands`（PowerShell + 系统 python，命令内禁用中文引号）。

## 1. 环境

- 解释器：`C:\Program Files\Python313\python.exe`（项目 venv 已坏，别用）。
- 依赖：仅 TTS 生成需要 `websockets`（先 `python -c "import websockets"` 验一下，没有就 pip 装）。
- 脚本首行：`import sys; sys.stdout.reconfigure(encoding='utf-8')`。
- 试听转码需要 ffmpeg（winget 装的 8.1.2 在用户 PATH；老会话 PATH 快照过期时先刷新，见 [[ffmpeg-winget-path-stale]]）。

## 2. 侦查草稿现状（只读）

草稿目录：`C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>`

读 `draft_content.json`（以 content 为准，info 可能落后），确认：
- 总时长 `duration`（微秒）——注入后必须不变。
- 英文字幕轨（`type=="text"`）每句的 `text` 与 `target_timerange`——配音逐句照念、起点对齐字幕。
  字幕 content 是嵌套 JSON 字符串，`json.loads` 后取 `text` 字段。
- 现有 audio 轨情况——BGM（`type=="music"`）保留不动；若还残留旧中文 TTS
  （`type=="extract_music"` 且 path 在 `textReading\` 下）说明 translate-subtitles 那步没删干净，先问用户。
- 贴纸轨（`type=="sticker"`）与 `materials.stickers` 数量——**本 skill 全程不碰**，记下数量供写入后断言。

## 3. 英文音色选型（本 skill 的核心难点）

### 3.1 已实测结论（2026-07-11 首轮 + 2026-07-12 扩池三批，SAMI 接口）

| speaker | 结果 | 备注 |
|---|---|---|
| `en_female_emotional` | **OK，已用（2026-07-11 柏威年英文版），进零复用黑名单** | 唯一命中的 en_* 音色；女声、情感风格、语速偏慢（约 0.48s/词） |
| `BV503_streaming` | OK，待试听 | 网络佐证（xwean.com/1976.html）＝活力女声 Ariana·美式英语；语速快（3.55s/11词） |
| `BV504_streaming` | OK，待试听 | 网络佐证＝活力男声 Jackson·美式英语（另一来源写"贝儿"，以试听为准）；语速最快（3.49s/11词） |
| `BV137_streaming` / `BV138_streaming` / `BV139_streaming` | OK，待试听 | 语种/性别不明，**用前必须试听确认是英语** |
| `BV506_streaming` | OK，待试听 | 语速偏慢（4.21s/11词），节奏最接近 en_female_emotional；语种不明须试听 |
| `BV511_streaming` | OK，待试听 | 语速快（3.53s/11词）；语种不明须试听 |
| `en_*` 外推共 15 款（story/common/emotional/narrator/sweet/warm/lively/gentle/deep/energetic/cute 等男女配对） | FAIL | TTSInvalidSpeaker (40402004)，真死，别再试——en_* 命名空间基本只有 en_female_emotional 一款 |
| 英文款 V2 变体（BV503_V2/BV504_V2/BV138_V2/BV506_V2/BV511_V2，均 _streaming） | FAIL | TTSInvalidSpeaker (40402004)，真死 |
| `BV702_streaming` / `BV509_streaming` | FAIL | TTSInvalidSpeaker (40402004)，真死 |
| `BV027/BV040/BV140/BV421/BV502/BV505/BV507/BV508/BV510/BV512/BV516/BV518/BV520/BV521/BV522/BV524/BV525/BV530/BV531`（均 _streaming） | FAIL | SynthesisFail (50000001)，重试复现（当前授权不可合成） |

> **池边界结论（2026-07-12）**：当前授权下英文候选池共 8 款＝已用 1 款 + 待试听 7 款；en_* 外推、
> V2 外推、CSDN feeday 127 ID 总表英语聚集区未测编号三条路都已探到头。下轮再扩池只能等剪映客户端
> 升级换授权，或从新的第三方代码仓库挖到从未出现过的 BV 编号。试听 mp3 统一存
> `e:\Documents\kuaishou\output\tts_probe_en\`。

### 3.2 为什么要靠实测（踩过的坑）

- 火山引擎官方音色文档页（`volcengine.com/docs/6561/97465`）是 **JS 渲染页**，WebFetch / WebSearch / curl 都拿不到英文 voice_type 表；
  第三方整理站（pyvideotrans 等）也只列中文音色。公开渠道**查不到**精确英文 ID。
- 唯一可行路径 = 对 SAMI 接口**批量探测**候选 ID（几秒一个，成本极低）：
  用 `scripts/probe_en_speakers.py`，候选来源两类——
  ① 仿照已确认的 `zh_female_story` → `en_female_story` 命名模式外推 `en_*`；
  ② 抄零星资料出现过的 BV 编号。命中率必须靠实测，不能只信文档（与中文音色扩池经验一致）。
- 探测报错分类同中文：TTSInvalidSpeaker(40402004)/IllegalSpeaker(40000022)=真死；
  SynthesisFail(50000001)/timeout=重试一次再判死。

### 3.3 用户试听拍板（/confirm-me 必做）

探测 OK 的候选**AI 自己听不了**，必须交用户耳朵拍板：

1. 每个 OK 候选的 `probe_en_*.ogg` 用 ffmpeg 转 mp3，落到 `e:\Documents\kuaishou\output\tts_probe_en\`。
2. 附上每款的客观信息（同一句测试文案的时长→语速对比、命名含义）。
3. 用 AskUserQuestion 让用户试听后选定音色，推荐项放第一个。

### 3.4 音色零复用黑名单

选型前查 [[kuaishou-fx-used-history]] 取历史已用音色并集写进 `gen_tts.py` 的 `BANNED_SPEAKERS` + `assert`。
英文音色与中文音色是**独立池**，但同样受零复用规则约束——本轮用过 `en_female_emotional` 后，下轮英文视频要换款（池子不够就先探测扩池）。

## 4. 配音文案：排版符号先改写成自然口语（/confirm-me）

英文字幕为了排版好看常带符号，**直接照读会生硬**，生成前逐句过一遍：

- `+` / `=`：改写成自然句式（实例：`Blossoms + lanterns \n= Chinese vibes!` → 配音念
  `Blossoms and lanterns bring the Chinese vibes!`），**不要**字面读成 plus/equals。
- `—`（破折号）/ `\n`（换行）：TTS 天然当停顿处理，保留即可。
- 改写方案先用 AskUserQuestion 给用户过目（改写 vs 字面照读符号），拍板后才生成。
- 字幕**本体不改**，只有送 TTS 的文案改写——字幕排版是给眼睛的，配音是给耳朵的。

## 5. 生成配音（scripts/gen_tts.py）

改顶部 `DRAFT_DIR` / `SPEAKER` / `LINES`（文件名、送 TTS 的文案、字幕起点us、字幕窗口us），跑完：
- ogg_opus 落草稿 `textReading\`（文件名带 `voice_en_` 前缀区别于历史中文配音残留）。
- 逐句打印"语音时长 vs 字幕窗口"——英文口语句短（实测 2.0~3.8s vs 窗口 4.5~5.5s，全 OK），
  一般不会溢出；真溢出时提示用户变速或改短文案。
- 产出 `tts_meta.json` 供注入脚本读取真实时长。

```powershell
$env:PYTHONIOENCODING = 'utf-8'
& "C:\Program Files\Python313\python.exe" .\scripts\gen_tts.py
```

时长测量：ogg_opus 最后一页 granulepos / **48000**（恒定 48kHz 时基，不是请求里的 24000）。

## 6. 只注入配音的双 JSON 写法（scripts/build_voice_only.py）

从姊妹技能 `build_voice_sticker.py` 裁剪：**只保留"步骤1 配音音轨"，整段删掉"步骤2 贴纸重排"**
（那段会先清空所有 sticker 轨再重建——跳过它就是贴纸原样保留，这正是"只配音"的正确做法）。

- `materials.audios`：`extract_music` 极简结构（id/local_material_id/music_id 同值、path 正斜杠绝对路径且 assert 存在、duration=真实音频us）。
- `materials.speeds`：每条配一个 `{speed:1.0, mode:0, curve_speed:null}`。
- 新增一条 `type=="audio"` 轨：每段 `target_timerange={start:字幕起点, duration:音频us}`、
  `source_timerange={start:0,...}`、`volume:1.0`、`extra_material_refs:[speed_id]`。
- **防误伤断言**：写入前后 `len(materials.stickers)` 必须相等（本 skill 专属校验，2026-07-11 验证 10→10）。
- 常规校验：轨内不重叠不越界、material 引用闭环、总时长不变。
- 写入：双 JSON 各打时间戳 `.bak`（`.pre_voiceonly_<ts>.bak`）→ content 写入 → **content 原样同步给 info**（修复剪映 8.9 只写 content 的分叉）。

```powershell
$env:PYTHONIOENCODING = 'utf-8'
& "C:\Program Files\Python313\python.exe" .\scripts\build_voice_only.py            # dry-run
& "C:\Program Files\Python313\python.exe" .\scripts\build_voice_only.py --apply    # 备份并写入
```

## 7. 写入后独立复核 + 回写记忆

1. 重新读双 JSON 复核：content == info（完全等价）、audio 轨应为 2 条（BGM 1 段 + 配音 N 段）、
   贴纸轨名单与写入前逐一比对一致、总时长不变。
2. **回写记忆 [[kuaishou-fx-used-history]]**：本轮音色 + "贴纸未改动沿用上轮" 记一条，供下轮零复用排除。
3. 新探测到的可用/不可用英文音色补进 [[jianying-tts-sticker-inject]] 与本 SKILL.md §3.1 的表。

## 8. 收尾告知用户

1. 配音是**本地 ogg 文件**，不需要客户端联网下载（区别于 VIP 贴纸/花字）。
2. 剪映若正开着该草稿，**先关闭再重开**，否则内存旧版本保存时会覆盖注入结果。
3. 备份可回滚：`draft_content.json.pre_voiceonly_<时间戳>.bak` / `draft_info.json.pre_voiceonly_<时间戳>.bak`。

---

## 踩坑清单（2026-07-11 实战沉淀）

1. **英文音色查不到文档**：官方音色页 JS 渲染，WebFetch/WebSearch/curl 全扑空 → 唯一路径是对 SAMI 接口批量探测（§3.2）。
2. **en_* 命名模式命中率低**：6 个 en_* 候选只中 1 个（`en_female_emotional`）；`en_male_emotional` 也是 FAIL，别想当然配对。
3. **BV 数字系列语言不明**：探测 OK ≠ 是英语，必须转 mp3 让用户试听后才能用。
4. **AI 听不了音频**：音色好坏/口音地道与否只能用户拍板 → 转 mp3 + AskUserQuestion 试听流程（§3.3）。
5. **字幕排版符号直读生硬**：`+`/`=` 要改写成自然口语；改写只作用于 TTS 文案，字幕本体不动（§4）。
6. **"只配音"就是跳过贴纸段落**：`build_voice_sticker.py` 的贴纸重排段会清空 sticker 轨重建，只配音时整段不跑 + 前后断言贴纸数量不变。
7. **inline `python -c` 转义翻车**（复发确认）：含引号/反斜杠的验证代码写 `.py` 文件再跑，别塞 `-c`。
8. **英文句普遍比窗口短**：口语化英文短句 2~4s，5s 左右的字幕窗口很宽裕，不必预留变速方案；但仍要逐句打印核对。
9. **文件名带 `voice_en_` 前缀**：与历史中文配音 `voice_NN.ogg` 残留区分开，textReading 目录里一眼可辨。
10. **零复用同样管英文池**：英文音色独立于中文 34 款池，但每轮英文视频音色也不得与历史英文轮次重复。

## 参考脚本

- `scripts/probe_en_speakers.py` — 英文音色探测（候选 = en_* 模式外推 + BV 编号；OK 的存 `probe_en_*.ogg` 供转码试听）。
- `scripts/gen_tts.py` — 英文配音生成（`BANNED_SPEAKERS` 零复用硬校验；逐句报时长是否溢出；产出 `tts_meta.json`）。
- `scripts/build_voice_only.py` — 只注入配音的双 JSON 模板（dry-run + `--apply` 备份写入并同步 info；贴纸数量不变断言）。
