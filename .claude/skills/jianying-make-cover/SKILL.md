---
name: jianying-make-cover
description: 给"已存在"的剪映 (JianYing Pro) 5.9 视频草稿制作吸睛封面——流程按固定顺序走三段：①先本地出 9:16 竖屏底图（ffmpeg 抽帧裁比例，封面原始图）；②9:16 成品封面走"人机协作"：用户手动进草稿→点「封面」→上传底图→切「模板」页签（无需确认 VIP 登录，不点模板筛选器，默认已是「全部」），然后 jy_ui.py 才从「模板」页签接手（截图校准坐标→按匹配度挑最适合的模板，免费/VIP 皆可不强求 VIP→逐行 paste-at 替换文案→保存退出），搜模板的每张截图都存档到本地固定目录方便日后翻查；花字只做推荐不代点：自动化截图对比后告诉用户哪款最合适，由用户手动应用；复杂/卡壳步骤直接交回用户手动；可用 build_cover_fix.py 直改封面 mini-draft 双 JSON 校对文案+克隆已验证花字；③9:16 封面定稿后，最后本地合成 4:3 横版封面成品（ffmpeg 裁 4:3 + System.Drawing 画大字/描边/角标，全程不进剪映），风格参照已完成的 9:16 封面来设计（同文案、同配色、同字体），两张封面尽量保持一致性。适用于"给剪映草稿做封面""竖屏横屏封面""4:3 封面""封面模板花字""参考抖音小红书做吸睛封面""封面本地生成"等场景。触发词：剪映封面、做封面、竖屏封面、横屏封面、4:3 封面、封面模板、封面花字、jianying make cover。
---

# 给已有剪映草稿制作 4:3 横版 + 9:16 竖屏封面

对**已存在**的剪映 5.9 视频草稿，产出两样东西，**顺序固定：先 9:16，后 4:3**：

- **9:16 竖屏封面（先做）** —— **人机协作，不搞全自动**：本地先抽帧出 9:16 底图
  （封面原始图），**用户手动**进草稿 → 点「封面」→ 上传底图 → 切「模板」页签，
  之后自动化才接手挑**最适合**的模板 + 替换文案，并**推荐**花字给用户手动应用，
  成品写进草稿封面槽（`materials.drafts[0].draft` 这个嵌套 mini-draft）。
- **4:3 横版封面成品（后做）** —— **全程本地生成，不进剪映**：等 9:16 封面定稿后，
  ffmpeg 从同一帧裁 4:3 做底图，PowerShell + System.Drawing 画大字/描边/角标，
  **风格参照已完成的 9:16 封面来设计**（同文案、同配色、同字体、版式呼应），
  复用剪映缓存里的 VIP 字体，让两张封面尽量保持一致性。

> **分工铁律**（用户定的，不要改回全自动）：
> 1. 进草稿、点「封面」、上传底图、切「模板」页签这四步**由用户手动完成**，自动化不碰。
> 2. **不需要确认/校验 VIP 账号登录状态**，用户自行保证已登录。
> 3. **不要点开模板筛选器**——默认已是「全部」，点开只会多一步还遮挡模板网格。
> 4. 自动化过程中任何一步复杂、点不中、连错两次 → 停下来**直接让用户手动操作**
>    （/confirm-me），用户做完后 `shot` 校验再继续，别硬啃。
> 5. **模板/花字选型以"最适合"为准，不强求 VIP**——按与底图色调、文案版式的匹配度挑，
>    免费款合适就用免费款，VIP 只是加分项不是硬指标。
> 6. **搜模板时每一张截图都要存档到本地固定目录**（见「产出约定」），不要只丢
>    scratchpad，方便日后直接翻看候选模板不用重新截。
> 7. **花字只推荐、不代点**：自动化负责搜索/截图/对比并说清"推荐哪一款、为什么、
>    在界面哪个位置"，由**用户手动**点选应用，自动化只在事后 `shot` 校验。

> 适用前提：草稿**已经存在**（有 `draft_content.json`）。加转场/特效/字幕动画/配音贴纸
> 请分别用 `jianying-inject-fx` / `jianying-inject-text-fx` / `jianying-inject-tts-sticker`；
> 从零生成草稿用 `openstoryline-to-jianying`。本 skill 只管"做封面"。

相关记忆：真实路径 [[kuaishou-actual-paths]]、venv 坑 [[kuaishou-venv-broken-py313]]、
VIP 花字 ID 与克隆套路 [[jianying-text-anim-flower]]、FX 历史黑名单 [[kuaishou-fx-used-history]]。
姊妹技能同在 `e:\Documents\kuaishou\.claude\skills\` 下。

---

## 开工前必读（真实环境 / 坑）

1. **路径盘符/用户名**（[[kuaishou-actual-paths]]）：本机是 `e:\Documents\kuaishou\...`、
   用户名 `wayyet`。skill 文档里若出现 `D:\...` / `wayye` 一律换成 e 盘 / wayyet。
   - 剪映草稿目录：`C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft`
   - 剪映程序：`e:\Documents\kuaishou\JianyingPro\5.9.0.11632\JianyingPro.exe`
   - OpenStoryline 产物：`e:\Documents\kuaishou\FireRed-OpenStoryline\outputs\<会话id>\`
   - ffmpeg：`e:\Documents\kuaishou\FireRed-OpenStoryline\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`
2. **venv 已坏**（[[kuaishou-venv-broken-py313]]）：用**系统 Python 3.13**
   （`C:\Program Files\Python313\python.exe`）跑脚本；`jy_ui.py` 需要 `uiautomation` +
   `comtypes`（已装到用户 site，若缺再从旧 venv `Lib\site-packages` 拷到 `<deps>` 目录并
   `$env:PYTHONPATH='<deps>'`），运行时 `$env:PYTHONIOENCODING='utf-8'`。
3. **中文/编码**：PowerShell 里读写含中文的 JSON/输出前先
   `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)`，Python 侧
   `sys.stdout.reconfigure(encoding='utf-8')`，否则乱码。别反复重跑同一条乱码命令。
4. **命令风格**：全程 PowerShell / Windows 原生命令（`/windows-shell-commands`），不用 Linux 语法。
5. 全程默认中文输出（`/chinese-outcome`），拿不准就停下确认（`/confirm-me`）——
   **选底图、定文案、挑模板/花字**这类审美决策用 `AskUserQuestion` 给用户拍板；
   **复杂/卡壳的客户端操作**直接让用户手动做，别自动化硬啃。

---

## 整体流程

```
①选题/文案（搜抖音小红书爆款套路，给用户选）
      │
      ▼【第 1 步：本地出 9:16 底图 = 不进剪映】
        a. ffmpeg 从分镜抽候选帧 → 用户选帧
        b. 裁出 9:16 底图 cover_v_base.jpg（1080x1920，封面"原始图"，之后交用户上传）
      │
      ▼【第 2 步：9:16 成品 = 人机协作】
        a.（用户手动）进剪映草稿 → 点「封面」→ 本地上传 9:16 底图 → 切「模板」页签
        b.（自动化接手）jy_ui.py：shot 校验界面 → 逐屏截图存档 → 选最适合的模板
          （免费/VIP 均可）→ 应用
        c.（自动化）逐行 paste-at 替换模板文字（中文用粘贴，别逐字输）
        d.（自动化推荐+用户手动）花字：截图对比 → 推荐最合适的一款给用户 →
          用户手动应用 → shot 校验 → 保存 → home → 退出剪映
        e.（可选=第 3 步）build_cover_fix.py 直改封面 mini-draft JSON 校对文案+克隆花字
        ※ b–d 任何一步复杂/点不中 → 停下，交用户手动做完再继续
      │
      ▼【第 4 步：本地出 4:3 封面成品 = 不进剪映，风格向 9:16 对齐】
        a. Read 定稿的 9:16 封面（退出剪映后草稿目录的 draft_cover.jpg），
           记下配色/字体/版式/花字质感
        b. ffmpeg 从同一选定帧裁出 4:3 底图 cover_43_base.jpg（1440x1080）
        c. gen_cover_local.ps1 画大字/描边/角标 → 4:3 封面成品
           （文案/配色/字体与 9:16 保持一致，本地完工）
```

三个脚本都在 `scripts/`：
- `jy_ui.py` —— 剪映 UI 自动化分步驱动（第 2 步竖屏 b–d 段；`launch`/`open-draft` 保留备用，默认不用）
- `build_cover_fix.py` —— 封面 mini-draft 双 JSON 文案校对 + VIP 花字克隆（第 3 步，可选）
- `gen_cover_local.ps1` —— 本地 System.Drawing 合成封面（第 4 步 4:3 成品，风格照抄 9:16）

---

## 第 0 步：选题与文案（吸睛套路）

参考抖音/小红书爆款封面，先 `WebSearch` 找当下的标题公式，再用 `AskUserQuestion`
让用户在几套方向里选。治愈系乡村 Vlog 实测好用的是**悬念反差式**：
> 地点 + 数字反差 + 免费/隐藏钩子，例：「广州竟藏着 / 600年古村」+「0门票·番禺大岭村」。

排版三段式：主标题(超大字，双色，白+金)、副标题(利益点/关键词并列)、角标(0门票/地点)。
两张封面**共用同一套文案与配色**，只是版式按 9:16 / 4:3 重排；**4:3 在 9:16 定稿后
再做**，风格向 9:16 成品对齐。

## 第 1 步：本地出图——9:16 底图

从 OpenStoryline 原始分镜（`outputs\<会话id>\media\media_XXXX.mp4`）或草稿素材抽帧，
挑画面最干净、主体最突出的一帧。**不要**在剪映成片里截（会带字幕/水印）：

```powershell
$ff = 'e:\Documents\kuaishou\FireRed-OpenStoryline\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
# 抽多个候选帧（不同秒数）
& $ff -ss 7 -i 'media_0004.mp4' -frames:v 1 -q:v 2 'cand_1.jpg' -y -loglevel error

# 9:16 底图（封面"原始图"，之后由用户手动上传进剪映）：
#   素材本身是 1080x1920 竖屏时直接存帧即可；横屏素材才需要 crop 竖条再 scale
& $ff -i 'cand_1.jpg' -vf "scale=1080:1920:flags=lanczos" 'cover_v_base.jpg' -y -loglevel error
```

把候选帧 `Read` 出来肉眼比对，用 `AskUserQuestion` 让用户选底图。底图存到
`e:\Documents\kuaishou\output\covers\`（`cover_v_base.jpg`）。**选定的候选帧留着别删**，
第 4 步做 4:3 底图要从同一帧裁，保证两张封面画面一致。

## 第 2 步：9:16 竖屏——人机协作（用户手动开路，自动化只做模板段）

### 2a. 用户手动段（自动化全程不碰剪映）

把 9:16 底图路径告诉用户（如 `e:\Documents\kuaishou\output\covers\cover_v_base.jpg`），
请用户在剪映客户端里手动完成，并提醒**做完后屏幕保持解锁、不碰鼠标键盘**：

1. 打开剪映，进入目标**草稿**；
2. 点**「封面」**按钮，进封面编辑器；
3. 选**本地上传**，把 9:16 底图传进去（裁剪框确认 → 去编辑）；
4. 切到**「模板」页签**，停在这里即可。

**不需要确认 VIP 账号登录**；**不要点开模板筛选器**（默认已是「全部」）。
用户说"好了"之后，先 `shot` 一张校验当前界面确实停在「模板」页签，再接手。

### 2b. 自动化接手段（从「模板」页签开始）

**核心心法：一步一截图，坐标现场校准。** 剪映版本/分辨率/DPI 不同，写死一整套坐标
必翻车。用 `jy_ui.py shot` + `dump` 看清当前界面，再决定下一步点哪。

```powershell
# 截图统一落到本地存档目录（不是 scratchpad），方便日后直接翻看候选模板
$shotDir = 'e:\Documents\kuaishou\output\covers\template_shots\<草稿名>_<yyyyMMdd>'
New-Item -ItemType Directory -Force $shotDir | Out-Null
$env:PYTHONIOENCODING = 'utf-8'; $env:JY_SHOT_DIR = $shotDir
# 若系统 Python 缺 uiautomation/comtypes，再补 $env:PYTHONPATH = '<deps>'
$py = 'C:\Program Files\Python313\python.exe'
$jy = '<本 skill>\scripts\jy_ui.py'

& $py $jy shot template_tab.png               # 先截图确认已在「模板」页签
# —— 之后每步都是：click-xy/click-name 点一下 → shot → Read 看结果 → 定下一步 ——
```

接手后的操作顺序（坐标以你自己截图为准，别照抄数字）：
1. **挑最适合的模板（免费/VIP 均可，匹配度优先）**：在模板网格里逐屏滚动浏览，
   **每滚一屏都 `shot` 一张存进 `$shotDir`**（命名 `grid_01.png`、`grid_02.png`…顺序编号），
   必要时用 ffmpeg crop/scale 放大局部看清缩略图细节（放大图也存档，命名 `grid_01_zoom.png`）。
   选型标准：与底图**色调匹配**、版式为「大主标题+副标题」、文字槽数量贴合文案段数；
   **不强求 VIP**——免费款更合适就用免费款，VIP 标只是参考不是筛选条件。
   拿不准时 `AskUserQuestion` 附截图给用户挑 → 点击应用（会出现多行占位文字）。
2. **替换文案**：逐行点中模板占位文字 → `paste-at <x> <y> '<新文字>'`。
   **中文必须用 `paste-at`（走剪贴板粘贴）**，`type-at` 逐字发键会丢字/弹候选词。
   按模板实际行数分配三段文案（主标题/副标题/角标），多余行删掉或留空。
3. **推荐花字，用户手动应用**（主标题，可选）：切「文本→花字」→ 逐屏截图存档
   （命名 `flower_01.png`…）→ 放大对比候选款 → 先查记忆 [[kuaishou-fx-used-history]]
   **排除历史已用花字**（用户规则：不复用旧 FX）→ 用 `AskUserQuestion` 告诉用户
   **推荐哪一款、为什么合适（配色/质感与封面的关系）、在界面第几行第几个**，
   由**用户手动点选应用**；用户说"好了"后 `shot` 校验效果。自动化不代点花字。
4. **保存退出**：点「完成/保存」→ `home` 回目录页 → `Stop-Process -Name JianyingPro -Force`
   退出。**退出后**封面才稳定落进草稿 JSON 与 `draft_cover.jpg`。

**卡壳就换人**：以上任何一步点不中、看不清、连错两次，立即停下用 `AskUserQuestion`
说清楚"请帮我手动点 XXX"，用户做完后 `shot` 校验再继续下一步。

## 第 3 步（可选）：JSON 校对竖屏封面文案 + 克隆已验证花字

若客户端里某几行没改干净，或想把主草稿字幕已验证的花字（免费/VIP 皆可）精确套到副标题，
**剪映退出后**用 `build_cover_fix.py` 直改封面 mini-draft：

```powershell
$env:PYTHONIOENCODING = 'utf-8'
& 'C:\Program Files\Python313\python.exe' '<本 skill>\scripts\build_cover_fix.py'          # dry-run 先看计划
& 'C:\Program Files\Python313\python.exe' '<本 skill>\scripts\build_cover_fix.py' --apply   # 备份后写入
```

脚本里的 `TEXT_PLAN` / `VIP_FLOWER_RES` / `OLD_EFFECT_PREFIX` 需按草稿实际值改，
拿值方法见脚本头注释。**关键认知**：封面是嵌套 mini-draft，挂在
`draft_content.json` 的 `materials.drafts[0].draft`，结构与主草稿同构（有自己的
texts/tracks/effects）；改文字时 `styles[].range` 必须跟文字长度同步。

## 第 4 步：本地出图——4:3 封面成品（风格参照 9:16 成品）

**前提：9:16 封面已定稿、剪映已退出。** 4:3 不是独立设计，而是把定稿的 9:16 封面
"翻排"成横版，两张尽量保持一致性。

1. **先看 9:16 成品定风格**：`Read` 草稿目录下的 `draft_cover.jpg`（剪映退出后生成/更新），
   记下实际用到的：文案各行内容、主标题双色（哪几个字白/哪几个字金）、字体、
   花字质感（描边色/投影）、角标位置与配色。以**成品实际效果**为准，不以第 0 步的
   初稿文案为准（模板段可能按槽位删改过文案）。
2. **裁 4:3 底图**：从第 1 步**同一选定帧**裁中部横条，放大到 1440x1080：

```powershell
$ff = 'e:\Documents\kuaishou\FireRed-OpenStoryline\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
# 从竖屏帧裁中部 1080x810 横条，放大到 1440x1080
# y 偏移按画面主体位置定（先 Read 原帧再定 crop 参数，别瞎猜）；
# 尽量让 4:3 取景框住 9:16 封面里主体+文字所在的同一片画面
& $ff -i 'cand_1.jpg' -vf "crop=1080:810:0:520,scale=1440:1080:flags=lanczos" 'cover_43_base.jpg' -y -loglevel error
```

3. **本地合成成品**：改 `gen_cover_local.ps1` 顶部 6 个配置常量（底图、输出、字体、
   三段文案——全部按第 1 点从 9:16 成品抄下来的值填），直接运行（画布尺寸自动取
   底图宽高，比例无关）：

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
& '<本 skill>\scripts\gen_cover_local.ps1'
```

产物 `e:\Documents\kuaishou\output\covers\<草稿名>_封面_4x3.jpg`。`Read` 出来，
**和 `draft_cover.jpg` 并排比对**：文案、配色、字体观感是否一致，不一致就调常量重跑。
字体直接引用剪映缓存里的 VIP 字体文件（`...\User Data\Cache\effect\<id>\<hash>\*.TTF|otf`），
和竖屏封面同字同色，两张一套观感统一。花字质感靠 GraphicsPath 描边 + 投影模拟。

## 第 5 步：验收与收尾

- **回写记忆**：本次用掉的封面模板/花字（不论免费还是 VIP）追加进
  [[kuaishou-fx-used-history]] 已用清单；踩到新坑更新本 skill 相关记忆。
- **截图存档留存**：`template_shots\` 下本次的模板/花字截图**不删**，作为素材库
  留给下次选型直接翻看（清缓存 skill 也不清它）。


---

## 已知坑 & 应对

| 现象 | 原因 / 应对 |
|------|------|
| `jy_ui.py` 报缺 uiautomation/comtypes | venv 坏，包已装用户 site；若仍缺，从旧 venv site-packages 拷这两个包到 `<deps>` 并进 `PYTHONPATH`（[[kuaishou-venv-broken-py313]]） |
| 截图/JSON 中文乱码 | 先设 UTF-8（Console.OutputEncoding / PYTHONIOENCODING），别重复跑失败命令 |
| 坐标点不中 / 界面漂了 | 每一步先 `shot`+`Read` 再点；VIP 标/小缩略图看不清就用 ffmpeg crop+scale 放大局部再 Read；连错两次 → 交用户手动 |
| 进草稿/点封面/上传底图想自动化 | **别**。这段就是设计成用户手动的（文件对话框/上传按钮偶发点不中，人工最快最稳） |
| 想先确认 VIP 登录状态 | 不需要，用户自行保证已登录，直接开工 |
| 想点模板筛选器缩小范围 | **别点**。默认已是「全部」，点开只会遮挡模板网格多绕一步 |
| 中文文字输进去缺字 | 用 `paste-at`（剪贴板粘贴），不要 `type-at` 逐字发键 |
| 替换后长文本左溢出画布 / 想挪文字位置 | 模板单字槽粘贴多字后会向左扩展溢出画布；封面编辑器里**方向键微移和 uia.DragDrop 都无效**（2026-07-07 实测），移动位置必须交用户手动拖 |
| 想找 VIP 花字/模板 | **先记住不强求 VIP，匹配度优先**。若确实要看 VIP 款：花字「全部」网格全是免费款，VIP 款要靠**搜索颜色词**（如"蓝色"/"金色"）才出来（带金色 VIP 角标）；模板缩略图 VIP 标是右上角粉色小标，全库可能只有个别几款 |
| 想代点花字 | **别**。花字环节自动化只推荐（截图+说明推荐理由和位置），应用由用户手动点，事后 `shot` 校验 |
| 截图只存 scratchpad 用完就丢 | **别**。搜模板/花字的截图全部落 `output\covers\template_shots\<草稿名>_<日期>\`，顺序编号，留作下次选型直接翻看 |
| JSON 改完客户端没生效/被覆盖 | 改 `draft_content.json` 前必须**先退出剪映**；写入前自动备份、写入后回读校验 |
| 找不到封面文字节点 | 封面在 `materials.drafts[0].draft` 这个嵌套 mini-draft 里，不在主 texts |
| **电脑锁屏** | UI 自动化直接卡死（无法操作前台）。接手自动化前提醒用户**屏幕解锁、勿锁屏、勿碰鼠标键盘**；卡住就 `AskUserQuestion` 让用户解锁后继续 |
| 剪映正在运行时接手 | 先确认目标草稿没在别处被打开编辑，避免保存冲突 |

## 产出约定

- 底图与 4:3 成品统一放 `e:\Documents\kuaishou\output\covers\`：
  `cover_v_base.jpg`（9:16 封面原始图，交用户上传）、`cover_43_base.jpg`（4:3 底图）、
  `<草稿名>_封面_4x3.jpg`（4:3 成品）。**4:3 成品在 9:16 封面定稿后才做**，
  文案/配色/字体照 9:16 成品（`draft_cover.jpg`）对齐，两张保持一致性。
- **模板/花字搜索截图存档**：`e:\Documents\kuaishou\output\covers\template_shots\<草稿名>_<yyyyMMdd>\`，
  模板网格 `grid_NN.png`（局部放大 `grid_NN_zoom.png`）、花字网格 `flower_NN.png`；
  **长期保留不清理**，供下次做封面直接翻看候选款。
- 竖屏封面成品在草稿内部（`materials.drafts[0].draft`），JSON 校对前带
  `.pre_coverfix_<时间戳>.bak` 备份。
- 交付时把两张封面 `Read` 出来给用户验收，并说明竖屏在草稿里、4:3 是本地文件。
