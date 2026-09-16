---
name: jianying-inject-tts-sticker
description: 给"已存在"的剪映 (JianYing Pro) 5.9 草稿注入 AI 配音（TTS 旁白音轨）与 VIP 贴纸，做成治愈系/卡点 Vlog 那种有人声解说 + 动态贴纸点缀的成片。配音走剪映客户端同款 SAMI 接口（离线用系统 Python + websockets 直接生成 ogg_opus，落到草稿 textReading 目录，再手写 audios/speed material + 音频轨）；贴纸没有公开 ID 库，走"让用户在剪映客户端手挑样本→从草稿提取样本 material/segment→深拷贝克隆并按吸睛节奏重排到多条 sticker 轨"的套路。最后直接改 draft_content.json / draft_info.json 双 JSON，dry-run 校验后带备份写入，绕开损坏的 venv。适用于"给剪映草稿加配音""加旁白/解说""AI 配音""给视频加贴纸""治愈系 Vlog 配音贴纸美化""批量排布贴纸"等场景。触发词：剪映配音、剪映加旁白、剪映 TTS、剪映贴纸、注入配音贴纸、jianying inject tts sticker。
---

# 给已有剪映草稿注入 AI 配音 + VIP 贴纸

对**已存在**的剪映 5.9 草稿，加入 **AI 配音音轨**（SAMI TTS 旁白）与 **VIP 贴纸**（按吸睛节奏排布）。核心原则：
**直接改双 JSON，只往草稿新增音频轨 / 重排 sticker 轨，不破坏已调好的画面/转场/特效/字幕**——不经 pyJianYingDraft 运行时（本机 venv 已坏），用系统 Python 生成音频 + 手写 JSON 注入。

> 适用前提：草稿**已经存在**（有 `draft_content.json`）。
> - 加转场 / 视频特效 → 用 `jianying-inject-fx`。
> - 给字幕加文字动画 / 花字 → 用 `jianying-inject-text-fx`。
> - 变速 / 删减 / 加主副标题文字 → 用 `jianying-draft-edit`。
> - 从零把素材生成草稿 → 用 `openstoryline-to-jianying` / `jianying-editor`。
> - **英文字幕配英文配音（只配音、不动贴纸）→ 用 `jianying-inject-english-tts`**（2026-07-11 从本 skill 裁剪固化：英文音色探测+试听拍板、排版符号改写口语、贴纸数量断言）。
> 本 skill 专注"往已有草稿挂一条配音音轨 + 重排贴纸轨"。

相关记忆：真实路径 [[kuaishou-actual-paths]]、venv 坑 [[kuaishou-venv-broken-py313]]、
本 skill 的原始沉淀 [[jianying-tts-sticker-inject]]；姊妹技能 [[jianying-inject-transition-effect]]、[[jianying-text-anim-flower]]。

---

## 0. 先启用的工作流

本项目默认配套：`/chinese-outcome`（全程中文）、`/confirm-me`（音色取向、贴纸审美/排布、"是否手挑样本"等需用户拍板的点先确认）、
`/windows-shell-commands`（只用 PowerShell / 系统 python，命令内禁用中文引号）。

## 1. 环境：绕开损坏的 venv

项目 `e:\Documents\kuaishou\venv` 的基础解释器 Python312 已被删，**不要用它**。一律用系统解释器：

```
C:\Program Files\Python313\python.exe
```

- **配音生成**要联网走 WebSocket，需要 `websockets`（唯一的第三方依赖）。没有就先装到系统 python：
  ```powershell
  & "C:\Program Files\Python313\python.exe" -m pip install websockets
  ```
- **贴纸克隆 + 双 JSON 注入**只用标准库（`json` / `copy` / `uuid` / `shutil` / `struct`），无需装依赖。

脚本首行务必：

```python
import sys; sys.stdout.reconfigure(encoding='utf-8')   # 防中文乱码
```

## 2. 定位草稿并摸清现状

草稿根目录（注意真实盘符/用户名 = e盘 / wayyet）：

```
C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<草稿名>
```

用系统 python 读 `draft_content.json`，先搞清楚：
- **总时长** `duration`（微秒）——配音各段不能越界，注入后总时长必须不变。
- **字幕轨（`type=="text"`）的文案与 target_timerange**——配音旁白通常照字幕文案逐句念，起点/窗口对齐字幕。
- **是否已经有音频轨 / 贴纸轨**（避免重复注入；本 skill 的贴纸步骤会先清空旧 sticker 轨再重排）。
- 画幅（竖屏 1080×1920 适配抖音/小红书），决定贴纸的 `transform` 归一化坐标摆放。

## 3. 历史零复用：音色 / 贴纸选型前先过黑名单（用户硬规则）

用户明确要求：**每个新视频草稿的配音音色与贴纸都不得与之前任何一轮重复**（"每次都不重复使用上次用过的"）。
复用旧款会被直接打回重做，所以这一步在出方案**之前**做，流程：

1. **读记忆 [[kuaishou-fx-used-history]]**，取**全部历史轮次**的已用音色并集 + 已用贴纸名并集。截至 2026-07-05 时点：

   | 轮次 | 已用音色 | 已用贴纸 |
   |---|---|---|
   | 2026-07-03 大岭村_治愈系Vlog | `zh_female_zhixing`（知性女声） | 推荐 / win赢 / 夏天的浪漫 / 世界杯庆祝啤酒 / 颠球的豹子 / 戴王冠的足球 |
   | 2026-07-05 广州永华艺术馆 | `zh_male_chunhou`（醇厚男声） | 打卡 / 红色印章传统文化 / 祥云 云朵 蓝色 粉色 / 盖碗茶实物 古风 / 人间值得 人生感悟 手写字 |

2. 两个生成脚本顶部各写死黑名单并**硬校验**（别靠人眼核对）：
   - `gen_tts.py`：`BANNED_SPEAKERS = {…}` + `assert SPEAKER not in BANNED_SPEAKERS`。
   - `build_voice_sticker.py`：`BANNED_STICKERS = {…}` + 对 `TRACK_A/TRACK_B` 里每个贴纸名 `assert name not in BANNED_STICKERS`。
   撞历史直接中止，请用户换款。
3. **每轮都挑新的**：音色从可用音色表里选没用过的（34 款可用 − 已用 2 款 = 还剩 32 款）；贴纸让用户在客户端手挑时，名字不能落在历史名单里。
4. 注入成功后，把本轮用的**音色 + 全部贴纸名**（附主题）**回写进记忆 [[kuaishou-fx-used-history]]**，供下一轮排除。

与姊妹技能 `jianying-inject-fx`（转场/特效）、`jianying-inject-text-fx`（文字动画/花字）的 `BANNED_*` + `assert` 思路一致——这边管**配音音色 + 贴纸**。

## 4. 配音（TTS）：剪映同款 SAMI 接口

**不依赖剪映客户端，离线直接生成**。走剪映客户端同款字节 SAMI WebSocket 接口：

```
wss://sami.bytedance.com/internal/api/v2/ws?device_id=<dev>&iid=<iid>
APP_ID  = 3704
APP_KEY = IZjhUeAYwP
```

- `device_id` / `iid` 从本机剪映配置提取（提取失败有兜底默认值，一般也能用）：
  - `device_id` ← `%LOCALAPPDATA%\JianyingPro\User Data\TTNet\tt_net_config.config`（正则 `device_id\&#\*(\d+)`）。
  - `iid` ← `%LOCALAPPDATA%\JianyingPro\User Data\Log\*.log` 里最近的 `iid=(\d+)`。
- `User-Agent` 要伪装成剪映：`JianyingPro/5.9.0.11632 (Windows 10.0.19045; app_id:3704; device_id:<dev>)`。
- 协议：连上后发 `StartTask`（payload 内含 `text` / `speaker` / `audio_config`）→ 再发 `FinishTask`；随后循环 `recv`，**二进制帧就是音频数据**，收到 `TaskFinished`（文本帧）结束；`TaskFailed` 抛错。
- 音频格式用 `ogg_opus`（`sample_rate:24000, bit_rate:64000`），产物落到草稿 `textReading\` 目录下。

### 实测可用音色表（2026-07-05 两批扩池共 34 款：zh 系 14 + BV 系 20；无效音色报 `TTSInvalidSpeaker (40402004)`）

| speaker | 风格 | 备注 |
|---|---|---|
| `zh_female_zhixing` | 知性女声 | **治愈系 Vlog 首推** |
| `zh_female_qingxin` | 清新女声 | |
| `zh_female_tianmei` | 甜美女声 | |
| `zh_female_story` | 故事女声 | 适合叙述/旁白 |
| `zh_female_inspirational` | 励志女声 | |
| `zh_female_xiaopengyou` | 小朋友 | |
| `zh_male_chunhou` | 醇厚男声 | |
| `zh_male_huoli` | 活力男声 | |
| `zh_male_xionger_stream_gpu` | 熊二 | 趣味 |
| `zh_male_inspirational` | 励志男声 | 2026-07-05 扩池新增 |
| `zh_male_zhubo` | 男主播 | 2026-07-05 扩池新增，播音腔 |
| `zh_female_zhubo` | 女主播 | 2026-07-05 扩池新增，播音腔 |
| `zh_male_rap` | 嘻哈男声 | 2026-07-05 扩池新增，卡点/潮流款 |
| `zh_female_sichuan` | 四川女声 | 2026-07-05 扩池新增，方言趣味款 |

**BV 系列（火山引擎 `BVxxx_streaming` 格式，2026-07-05 第二批扩池新增，实测可用 20 款）** —— 命中率远高于风格拼音款：

| speaker | 风格 | 备注 |
|---|---|---|
| `BV700_streaming` | 灿灿 | 多情感，抖音爆款女声，**通用首推** |
| `BV701_streaming` | 擎苍 | 浑厚古风男声，适合旁白/国风解说 |
| `BV406_streaming` | 超自然音色·梓梓 | 女声 |
| `BV407_streaming` | 超自然音色·燃燃 | 女声 |
| `BV001_streaming` | 通用女声 | |
| `BV002_streaming` | 通用男声 | |
| `BV005_streaming` | 活泼女声 | |
| `BV007_streaming` | 亲切女声 | |
| `BV051_streaming` | 奶气萌娃 | |
| `BV056_streaming` | 阳光青年 | 男声 |
| `BV102_streaming` | 儒雅青年 | 男声 |
| `BV104_streaming` | 甜美小源 | 女声 |
| `BV119_streaming` | 通用赘婿 | 男声 |
| `BV064_streaming` / `BV115_streaming` / `BV123_streaming` / `BV063_streaming` | 通用/特色 | 风格以试听 `probe_*.ogg` 为准 |
| `BV213_streaming` | 广东女声（粤语） | **贴广州/岭南主题** |
| `BV426_streaming` | 东北老铁 | 方言趣味 |
| `BV419_streaming` | 重庆小伙 | 方言趣味 |

**已知无效**（不要用）：`*nvsheng` / `*nansheng` 全拼后缀系（如 `zh_female_yuanqinvsheng`）、`zh_female_wenrouxiaoya`、`zh_female_wenroushunv`、`zh_female_roumeinvyou` 等；
2026-07-05 两批探测另排除：23 款 zh 风格拼音瞎猜款；BV 系列 `BV003`/`BV004`/`BV704`（IllegalSpeaker=ID 不存在）、`BV702`（TTSInvalidSpeaker）、`BV705`/`BV113`/`BV120`/`BV421`（SynthesisFail，两轮重试均失败，当前授权不可合成）——完整分类黑名单见 `probe_speakers.py` 尾注，别重复试。
**选候选的经验**：① 抄火山引擎 voice_type 文档名命中率最高（zhubo/rap/sichuan 系全中、BV 系列 20/29 命中），风格拼音瞎猜几乎全灭；② BV 走 `BVxxx_streaming` 格式，下批可补更多编号；③ `timeout` 多是网络抖动误报（BV700/BV426 首轮 timeout、重试即 OK），failed 款务必**重试一次**再判死，并区分 IllegalSpeaker(40000022)/TTSInvalidSpeaker(40402004)（真死）与 SynthesisFail(50000001)（授权不可合成）。
拿不准的新音色**先用 `scripts/probe_speakers.py` 探一遍**，别直接批量生成后才发现全 FAIL。
**选定音色还须先过 §3 历史零复用黑名单**（`gen_tts.py` 的 `BANNED_SPEAKERS`，别撞历史已用款）。

### 时长测量（对齐字幕的关键）

生成后要量每条 ogg_opus 的真实时长：解析 ogg 页，取**最后一页的 granulepos**，`时长(微秒) = granulepos / 48000 * 1e6`（opus 恒定 48kHz 时基，与请求的 24000 无关）。
逐句打印"语音时长 vs 字幕窗口"，**语音比字幕窗口长就会溢出**（提示需要给该句配音变速或延长字幕窗口，交给用户拍板）。

用脚本模板 `scripts/gen_tts.py`：改顶部 `DRAFT_DIR` / `SPEAKER` / `LINES`（每句：输出文件名、文案、字幕起点us、字幕窗口us），跑完在脚本目录产出 `tts_meta.json`（供注入脚本读取真实音频时长）。

```powershell
$env:PYTHONIOENCODING = 'utf-8'
& "C:\Program Files\Python313\python.exe" .\scripts\gen_tts.py
```

## 5. 配音音轨的注入写法（关键）

配音音频用 pyJianYingDraft 的 `extract_music` **极简结构**即可，不需要 beats / sound_channel_mapping：

- `materials.audios` 每条新增：`{id, local_material_id, music_id 同 id, type:"extract_music", path:<正斜杠绝对路径>, duration:<音频us>, name, check_flag:3, source_platform:0, category_name:"local", wave_points:[]}`。
- `materials.speeds` 每条配一个 speed material：`{id, type:"speed", speed:1.0, mode:0, curve_speed:null}`。
- 新增**一条** `type=="audio"` 轨，其 segments 每段：`material_id` 指向 audio，`extra_material_refs:[speed_id]`，
  `target_timerange={start:字幕起点, duration:音频us}`、`source_timerange={start:0, duration:音频us}`、`volume:1.0`、`track_render_index:0`。
- **路径写正斜杠绝对路径**（`DRAFT_DIR + "/textReading/" + 文件名`，`\` 全换 `/`），并 assert 文件存在。

## 6. 贴纸：手挑样本 → 克隆重排

**本机缓存与 pyJianYingDraft 都没有贴纸 ID 库（与花字同）**。所以走这个可靠套路：

1. **让用户在剪映客户端**：打开该草稿 → 把想用的**每一款**贴纸各拖一个到画面 → **保存并关闭剪映**。
   （`/confirm-me`：这一步必须用户亲自操作，脚本无法凭空造贴纸 id；用户挑几款、要哪些主题，先问清。
   **每一款都要是历史没用过的**——提醒用户避开 §3 黑名单里的旧贴纸，撞了就换。）
   贴纸 material 落在 `materials.stickers`，segment 落在 `type=="sticker"` 轨。
2. 脚本按**名称**收集样本：`materials.stickers` 里每个 `name` 取一份 material 模板；任取一条 sticker segment 作 segment 模板。
3. **按吸睛节奏重排**（审美/排布交用户拍板，见下）：
   - 先**清空**现有 sticker 轨与 `materials.stickers`（重排，不叠加）。
   - 对计划里每个贴纸：深拷贝样本 material（换新 uuid）→ append 到 `materials.stickers`；深拷贝 segment 模板（换新 uuid）→ 设 `material_id` / `target_timerange` / `clip.scale` / `clip.transform` / `render_index`（15000+ 递增）/ `track_render_index`（沿用样本轨的 4/5）。
   - **同一条 sticker 轨上贴纸时间不能重叠**——想同一时刻并排多个贴纸就得**拆成多条 sticker 轨**（如 TRACK_A→轨 4、TRACK_B→轨 5）。
4. 极简注入也可行（不走克隆）：一个 sticker material 只留 `{id, resource_id, sticker_id, source_platform:1, type:"sticker"}`（等价 `StickerSegment.export_material`），剪映客户端 VIP 登录联网时自动下载实体。但**优先用手挑克隆**，样式最稳。

排布经验（治愈系竖屏 Vlog）：`scale` 0.4–0.65；`transform` 归一化坐标四角错开（左上 `(-0.45, 0.6)`、右上 `(0.45, 0.55)`、右下 `(0.48, -0.42)`、左下 `(-0.48, -0.4)`）；
开头 0.5s 放钩子贴纸、结尾放互动/庆祝贴纸，中段点缀，避免遮挡主体与字幕。

## 7. 双 JSON 分叉坑（本 skill 的核心教训）

剪映 **8.9 客户端保存草稿时只写 `draft_content.json`**，`draft_info.json` 会落后——**用户手挑的贴纸只出现在 content**，info 里没有。
两文件顶层结构完全同构。所以：
- **以 `draft_content.json` 为准**读取（含用户新挑的贴纸样本）。
- 注入完成后**把 content 的完整内容原样写给 info**（`open(INFO,"w").write(同一串 txt)`），一次修复分叉。
- 写入前**两份都先备份**。

> 本机剪映实际是 8.9（`AppData\Local\JianyingPro\Apps\8.9.0.13361`），但草稿仍是 5.9 双 JSON 架构。

## 8. dry-run → 备份 → 写入 → 校验

用脚本模板 `scripts/build_voice_sticker.py`（见本目录）：

1. **dry-run**（默认，不带参数）：读 `tts_meta.json` + `draft_content.json`，构造音频轨与贴纸轨，打印每条配音/贴纸的注入预览，跑完整性校验。
2. **写入**（`--apply`）：先给两个 JSON 各打时间戳 `.bak`，再写入（`json.dump(..., ensure_ascii=False, separators=(",",":"))`），并把 content 同步给 info。
3. **完整性校验**：JSON 可序列化 + 每条轨内片段**不重叠、不越界**（≤ 总时长）+ 每个 segment 的 `material_id` / `extra_material_refs` 都存在 + 新增 audios/stickers 全部被引用 + **总时长不变**。

```powershell
$env:PYTHONIOENCODING = 'utf-8'
& "C:\Program Files\Python313\python.exe" .\scripts\build_voice_sticker.py            # dry-run
& "C:\Program Files\Python313\python.exe" .\scripts\build_voice_sticker.py --apply    # 备份并写入双 JSON
```

## 9. 收尾必须告知用户的 3 件事

1. **贴纸 VIP 素材需客户端下载**：脚本只写入 `resource_id` 引用；实际渲染文件要在
   **剪映客户端（VIP 已登录 + 联网）打开草稿时自动下载**后才生效（配音是本地 ogg 文件，不受此限）。
2. **剪映若正开着该草稿，先关闭再重开**，否则内存里的旧版本会在保存时覆盖注入结果。
   （挑贴纸样本那步本来就要求关闭剪映，注入后再重开即可。）
3. **备份可回滚**：草稿目录下已生成 `draft_content.json.pre_voicesticker_<时间戳>.bak` 等，随时可还原。

不擅自启动剪映去"可视化确认"（可能覆盖草稿），需要时先问用户。

---

## 踩坑清单（真实教训，2026-07-03 在 大岭村_治愈系Vlog 验证成功）

1. **venv 已损坏**：`e:\Documents\kuaishou\venv` 基础解释器 Python312 被删。用 `C:\Program Files\Python313\python.exe`；TTS 另需 `pip install websockets`。
2. **inline `python -c` 反斜杠转义翻车**：Windows 路径里的 `\` 会 `SyntaxError`。一律 `Write` 一个 `.py` 文件再运行，别塞 `-c` / heredoc。
3. **音色无效**：无效 speaker 报 `TTSInvalidSpeaker (40402004)`；`*nvsheng`/`*nansheng` 全拼后缀系普遍无效。新音色先用 `probe_speakers.py` 探测，别批量生成后才发现全 FAIL。
4. **opus 时长算错**：ogg_opus 时长 = 最后一页 granulepos / **48000**（恒定 48kHz 时基，**不是**请求里的 24000）。算错会导致音轨越界或对不齐字幕。
5. **配音溢出字幕窗口**：语音比字幕窗口长要提示用户（变速/延长窗口），别默默塞进去导致后一句被压。
6. **audio material 用错结构**：配音用 `extract_music` 极简结构 + 一个 speed material 即可，别硬套 music 的 beats/sound_channel_mapping。路径必须**正斜杠绝对路径**且文件真实存在。
7. **贴纸没有 ID 库**：别去猜/搜贴纸 id。唯一可靠路径 = 让用户在客户端手挑样本，脚本再从草稿提取克隆。
8. **同轨贴纸重叠**：同一 sticker 轨片段时间不能重叠；要并排多个贴纸就拆多条轨（render_index 15000+ 递增，track_render_index 沿用样本轨）。
9. **双 JSON 分叉（剪映 8.9 只写 content）**：客户端保存只更新 `draft_content.json`，`draft_info.json` 落后。以 content 为准读取与注入，写入时把 content 同步给 info 修复分叉。
10. **VIP 只是 id 引用**：贴纸不写入实际素材文件，需剪映客户端 VIP + 联网打开自动下载；否则界面里空白（配音是本地文件不受限）。
11. **剪映内存覆盖**：草稿开着时改 JSON，保存会被覆盖 → 让用户先关闭剪映（挑贴纸那步天然满足）。
12. **中文乱码**：脚本 `sys.stdout.reconfigure(encoding='utf-8')`；PowerShell 侧 `$env:PYTHONIOENCODING='utf-8'`，命令内禁用中文引号。
13. **零复用是硬规则不是建议**：配音音色 / 贴纸复用旧款会被用户直接打回（见 §3）。选型前读 [[kuaishou-fx-used-history]] 取历史并集，`gen_tts.py` 的 `BANNED_SPEAKERS`、`build_voice_sticker.py` 的 `BANNED_STICKERS` + `assert` 硬校验（广州永华一轮换醇厚男声 + 5 款国风印章贴纸全为新款就是这么保证的）；注入成功后把本轮音色 + 贴纸回写记忆。

## 参考脚本

- `scripts/gen_tts.py` — 配音生成（SAMI 接口，改 `DRAFT_DIR`/`SPEAKER`/`LINES`，产出 ogg + `tts_meta.json`，逐句报时长是否溢出；顶部 `BANNED_SPEAKERS` + `assert` 挡历史已用音色，见 §3）。
- `scripts/probe_speakers.py` — 音色探测（批量试一组 speaker 是否可用，OK/FAIL 一目了然，选音色前先跑）。
- `scripts/build_voice_sticker.py` — 双 JSON 注入模板（读 `tts_meta.json` 挂音频轨 + 手挑贴纸克隆重排；dry-run 校验 + `--apply` 备份写入并同步 info）。
  用时改顶部 `DRAFT_DIR`、`TOTAL_US`、`TRACK_A`/`TRACK_B`（贴纸名 + 起止 + scale + 归一化坐标）；顶部 `BANNED_STICKERS` + `assert` 挡历史已用贴纸，见 §3。
