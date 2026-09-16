---
name: jianying-cover-localize-en
description: 把"已完成"的中文版 9:16 竖屏封面成品（剪映导出的 jpg）本地化成英文版封面——全程不进剪映，纯本地 ffmpeg + PowerShell System.Drawing 处理。核心套路：先用差分定位中文封面每段文字的行范围，若成品与底图像素级同帧，则本来就是英文的元素（霓虹英文字、VLOG/PAVILION 角标等）整行像素带拷贝 100% 保真，只把中文文字段翻译后按原样式（描边/发光/渐变/投影）重画。流程固定为"侦查→差分定位→同帧判定→确认文案→合成→放大校验→固化"，文案翻译、排布、落盘方式必须先经用户确认（/confirm-me）。适用于"制作英文版封面""封面翻译成英文""参考中文封面做英文版""直接改本地封面图不进剪映"等场景。触发词：英文版封面、封面本地化、封面翻译英文、English cover、cover localize、不进剪映改封面。
---

# 中文封面 → 英文版封面（纯本地合成，不进剪映）

## 适用前提

- 已有**中文版 9:16 封面成品**（通常是剪映封面编辑器导出/渲染的 jpg）作为样式参考；
- 有对应的**无字底图**（当初上传剪映的封面原始图，如 `output\covers\cover_v_base.jpg`）；
- 用户点名**不使用剪映**，直接对本地图片处理。

产出：英文版封面新文件（默认 `output\covers\<草稿名>EN-封面.jpg`，**底图只读不覆盖**，
除非用户明确要求原地覆盖——覆盖前必须留 `.bak` 并 /confirm-me）。

## 固定流程（绝不先写后报）

### ① 侦查（只读）

1. `Read` 中文成品封面 + 底图，肉眼记下版式结构（每段文字的位置/颜色/字体气质/特效层次）；
2. 核对两图尺寸必须一致（`System.Drawing.Image::FromFile` 取宽高）；
3. 查记忆（[[jianying-make-cover]]、[[kuaishou-fx-used-history]]）和本 skill `scripts\`，优先复用已有脚本改配置。

### ② 差分定位文字带

跑 `scripts\locate_text_bands.ps1 -Base <底图> -Cover <中文封面>`，输出：

- **全零行占比**：>90% 说明两图像素级同帧（剪映渲染封面不缩放不调色），可走带拷贝；
- **每段文字的 y 行范围**（含峰值），用于规划"哪些带保留拷贝、哪些带重画、互不侵入"。

实测样例（柏威年广场 1080x1920）：角标 y79-104、红字 y427-497、霓虹 y591-758、金字 y1411-1520。

### ③ 分带规划

| 元素类型 | 处理 |
|----------|------|
| 本来就是英文/数字的元素（霓虹英文、VLOG/年份、地标名角标） | **整行像素带拷贝**（DrawImage 同位 src/dst 矩形，带外扩 10~15px 余量），100% 保真、无接缝 |
| 中文文字段 | 擦都不用擦——以**底图为画布**，中文自然不存在；翻译后按原样式重画 |

规划时确认重画区域的外发光/投影不会侵入保留带。

### ④ 确认文案（/confirm-me，必须）

用 AskUserQuestion 让用户拍板，一次问齐：

1. 每段中文的**英文译文**（给 2-3 个候选：直译悬念感 / 口语社媒感 / 换主语）；
2. **排布**（单行贴原版 vs 拆两行更大更吸睛——英文天然比中文长，大字号常需拆行）；
3. **落盘方式**（新文件推荐 / 原地覆盖留 .bak）。

### ⑤ 合成（scripts\gen_cover_en_916_centered.ps1 改配置）

画布 = 底图 → DrawImage 拷贝保留带 → GraphicsPath 逐层画英文字 → JPEG 质量 92 存新文件。

**字体映射**（中文气质 → 英文字体，均走 PrivateFontCollection 加载 ttf）：

| 中文样式 | 英文字体 |
|----------|----------|
| 衬线/书法笔锋感标题 | Georgia Bold（`georgiab.ttf`）；更秀气可用剪映缓存 Prata-Regular |
| 粗黑体量感大字 | Arial Black（`ariblk.ttf`） |

**样式配方**（画层顺序从下到上，实测还原度高）：

- 红色发光标题：外层暖光 stroke(α70,橙红,w30) → 内层光晕 stroke(α130,w16) → 深红描边 stroke(255,150,12,8, w6) → 红橙纵向三段渐变填充（255,105,45 → 240,55,28 → 222,18,16）；
- 金色立体大字：深投影 shadow(α140, 偏移5,7) → 深棕描边 stroke(92,58,14, w8) → 金色三段渐变（255,242,184 → 245,198,79 → 214,140,30）→ 细亮边 stroke(α120,255,250,220, w2) 提立体感；
- 定位用"包围盒水平居中 + 垂直中心对齐到中文原带中心 y"，字号用 Fit-Size 按目标宽度反推。

### ⑥ 放大校验

1. `Read` 成品全图，与中文版对照版式；
2. ffmpeg `crop` 裁出每个文字区 + 拷贝带边界区，`Read` 放大核对：描边/发光质感、
   带拷贝有无接缝、手写体下降笔画（如 p 的圈）是否被带边界截断、角标是否完好。

### ⑦ 固化与记忆

脚本改动回写本 skill `scripts\`；关键新经验更新记忆 [[jianying-make-cover]]。

## 踩过的坑（先读再动手）

1. **差分必须在 RGB 域做**：ffmpeg `blend=all_mode=difference` 对 yuv 输入按 YUV 平面做差，
   接 `format=gray` 后只剩亮度差——彩色霓虹字、白色角标与亮背景亮度接近，会**整段漏检**。
   先 `format=gbrp` 再 blend。
2. **细笔画先二值化再行平均**：直接 `scale=1:H` 平均，手写体细笔画被 1080 像素摊薄成 0，
   带宽偏窄几十像素。先 `lut=y=if(gte(val,16),255,0)` 再 scale。
3. **PS7/.NET10 下别用 Add-Type 编 System.Drawing 的 C#**：Bitmap/LockBits 会连环缺
   `System.Drawing.Common`、`System.Private.Windows.GdiPlus` 等私有程序集引用，编译必败。
   像素统计一律交给 ffmpeg，PowerShell 只读 rawvideo 字节。
4. **旧 VS Code 会话 PATH 快照过期**：跑 ffmpeg 前先
   `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`
   （见记忆 [[ffmpeg-winget-path-stale]]）。
5. **复杂 PowerShell 逻辑写 .ps1 再执行**：塞一行内联跑，报错输出会爆到几百 KB 且难定位
   （/windows-shell-commands 也有此要求）。
6. **英文比中文长**：中文 6 字方块单行的位置，英文常放不下同字号单行——要么缩字号保单行，
   要么拆两行做大，让用户选（本次用户选了拆两行）。

## 脚本清单

| 脚本 | 用途 |
|------|------|
| `scripts\locate_text_bands.ps1` | 差分定位文字带 + 同帧判定（参数化，任意两图可用） |
| `scripts\gen_cover_en_916_centered.ps1` | 柏威年广场定稿合成脚本（居中三段式：红发光标题 + 霓虹带拷贝 + 金字两行），换项目改头部配置区即可 |

## 协同 skill

- `/chinese-outcome`：全程中文汇报；
- `/confirm-me`：文案/排布/落盘三件事动笔前必须确认；覆盖任何已有文件前必须确认；
- `/windows-shell-commands`：PowerShell 语法、UTF-8 修复、复杂逻辑落 .ps1。
