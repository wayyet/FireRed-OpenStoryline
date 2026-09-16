# 本地合成封面（不进剪映）：底图 + 大字标题 + 花字描边/阴影 + 角标
# 纯 PowerShell + System.Drawing(GDI+)，Windows 自带，无需装 Pillow/venv。
# 典型用途：4:3 横版封面本地生成；或想快速出图不走剪映客户端时。
# 画布尺寸自动取底图宽高，比例无关（16:9 底图照样能跑）。
#
# 底图怎么来：用 OpenStoryline 原始分镜/剪映草稿素材抽帧再裁到目标比例，例如
#   $ff = '...\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
#   & $ff -ss 7 -i media_0004.mp4 -frames:v 1 -q:v 2 cand.jpg -y -loglevel error     # 抽帧
#   # 1080x1920 竖屏帧裁中部横条到 4:3（y 偏移按主体位置定，先 Read 原帧再定参数）
#   & $ff -i cand.jpg -vf "crop=1080:810:0:520,scale=1440:1080:flags=lanczos" cover_43_base.jpg -y
#
# 字体：直接复用剪映缓存里的 VIP 字体文件(TTF/OTF)，与客户端封面观感一致。位置：
#   C:\Users\<用户名>\AppData\Local\JianyingPro\User Data\Cache\effect\<id>\<hash>\*.TTF
#   （用 Get-ChildItem $cache -Recurse -Include *.TTF,*.ttf,*.otf 找）
#
# 用法：改下面 6 处配置常量后直接运行本 .ps1。

Add-Type -AssemblyName System.Drawing

# ==== 配置 ====
$base = 'e:\Documents\kuaishou\output\covers\cover_43_base.jpg'                       # 底图
$out  = 'e:\Documents\kuaishou\output\covers\吉隆坡柏威年广场_封面_4x3.jpg'              # 输出
$fontMain   = 'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Cache\effect\349467\8d34d3abe70f2c3c61f9a93b1f85c76b\综艺体.TTF'
$fontSerif  = 'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Cache\effect\14605249\e4387517f584be39bb2e1ca4ede6cbe3\SourceHanSerifCN-Heavy.otf'
$fontScript = 'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Cache\effect\349469\58bf5e7604fd305577dc7f31c342a8db\CapistranoBF.ttf'
$title1 = '吉隆坡竟藏着'        # 主标题(白) —— 悬念行
$title2 = '巨型金鸡喷泉'        # 主标题(金) —— 揭底行
$subtitle = '园林花艺·中式窗花·随手大片'
$scriptLine = 'Kuala Lumpur · Pavilion'  # 手写体点缀
$chipText = '0门票｜武吉加里尔'   # 左上角角标
# =============

$pfc = New-Object System.Drawing.Text.PrivateFontCollection
$pfc.AddFontFile($fontMain); $pfc.AddFontFile($fontSerif); $pfc.AddFontFile($fontScript)
$famMain   = $pfc.Families | Where-Object { $_.Name -match '综艺|Zong' } | Select-Object -First 1
$famSerif  = $pfc.Families | Where-Object { $_.Name -match 'Source|思源' } | Select-Object -First 1
$famScript = $pfc.Families | Where-Object { $_.Name -match 'Capistrano' } | Select-Object -First 1
if (-not $famMain) { $famMain = $pfc.Families[0] }
Write-Output ('已加载字体: ' + (($pfc.Families | ForEach-Object { $_.Name }) -join ' | '))

$img = [System.Drawing.Image]::FromFile($base)
$W = $img.Width; $H = $img.Height
$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$g.DrawImage($img, 0, 0, $W, $H)

# 底部渐变压暗，保证大字在任何底图上都可读
$rect = New-Object System.Drawing.Rectangle(0, [int]($H*0.40), $W, [int]($H*0.60))
$grad = New-Object System.Drawing.Drawing2D.LinearGradientBrush($rect, `
    [System.Drawing.Color]::FromArgb(0,0,0,0), [System.Drawing.Color]::FromArgb(185,10,20,8), 90)
$g.FillRectangle($grad, $rect)

$sf = [System.Drawing.StringFormat]::GenericTypographic

function New-TextPath([string]$text, $family, [single]$size, [single]$x, [single]$y) {
    $p = New-Object System.Drawing.Drawing2D.GraphicsPath
    $p.AddString($text, $family, [int][System.Drawing.FontStyle]::Bold, $size, `
        (New-Object System.Drawing.PointF($x, $y)), $sf)
    return $p
}
# 花字观感的核心：描边(outline) + 投影(shadow)，靠 GraphicsPath 描边+填充实现
function Draw-Styled($path, $fill, $outlineColor, [single]$outlineW, [bool]$shadow) {
    if ($shadow) {
        $m = New-Object System.Drawing.Drawing2D.Matrix; $m.Translate(6, 9)
        $sp = $path.Clone(); $sp.Transform($m)
        $sb = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(130,0,0,0))
        $g.FillPath($sb, $sp); $sp.Dispose(); $sb.Dispose()
    }
    if ($outlineW -gt 0) {
        $pen = New-Object System.Drawing.Pen($outlineColor, $outlineW)
        $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
        $g.DrawPath($pen, $path); $pen.Dispose()
    }
    $br = New-Object System.Drawing.SolidBrush($fill)
    $g.FillPath($br, $path); $br.Dispose()
}

$white = [System.Drawing.Color]::White
$gold  = [System.Drawing.Color]::FromArgb(255,255,205,84)
$dark  = [System.Drawing.Color]::FromArgb(255,30,42,20)
$cx = $W / 2

# 手写体点缀
$pScript = New-TextPath $scriptLine $famScript 66 0 0
$b = $pScript.GetBounds()
$m = New-Object System.Drawing.Drawing2D.Matrix
$m.Translate(($cx - $b.Width/2 - $b.X), ([single]($H*0.425) - $b.Y)); $pScript.Transform($m)
Draw-Styled $pScript ([System.Drawing.Color]::FromArgb(235,255,240,200)) $dark 3 $false
$pScript.Dispose()

# 主标题两段配色(白 + 金)，两行堆叠、各自居中（悬念行白 / 揭底行金）
$size = 150
$p1 = New-TextPath $title1 $famMain $size 0 0
$p2 = New-TextPath $title2 $famMain $size 0 0
$b1 = $p1.GetBounds(); $b2 = $p2.GetBounds()
$y1 = [single]($H*0.50); $y2 = [single]($H*0.665)
$m1 = New-Object System.Drawing.Drawing2D.Matrix; $m1.Translate(($cx - $b1.Width/2 - $b1.X), ($y1 - $b1.Y)); $p1.Transform($m1)
$m2 = New-Object System.Drawing.Drawing2D.Matrix; $m2.Translate(($cx - $b2.Width/2 - $b2.X), ($y2 - $b2.Y)); $p2.Transform($m2)
Draw-Styled $p1 $white $dark 12 $true
Draw-Styled $p2 $gold  $dark 12 $true
$p1.Dispose(); $p2.Dispose()

# 副标题
$pSub = New-TextPath $subtitle $famSerif 60 0 0
$bs = $pSub.GetBounds()
$ms = New-Object System.Drawing.Drawing2D.Matrix
$ms.Translate(($cx - $bs.Width/2 - $bs.X), ([single]($H*0.88) - $bs.Y)); $pSub.Transform($ms)
Draw-Styled $pSub $white $dark 6 $true
$pSub.Dispose()

# 左上角角标：金底圆角条 + 深色字
$pcM = New-TextPath $chipText $famSerif 44 0 0; $bc = $pcM.GetBounds(); $pcM.Dispose()
$padX = 30; $padY = 20
$chipW = $bc.Width + $padX*2; $chipH = $bc.Height + $padY*2
$chipX = 46; $chipY = 42; $r = 18
$chip = New-Object System.Drawing.Drawing2D.GraphicsPath
$chip.AddArc($chipX, $chipY, $r*2, $r*2, 180, 90)
$chip.AddArc($chipX + $chipW - $r*2, $chipY, $r*2, $r*2, 270, 90)
$chip.AddArc($chipX + $chipW - $r*2, $chipY + $chipH - $r*2, $r*2, $r*2, 0, 90)
$chip.AddArc($chipX, $chipY + $chipH - $r*2, $r*2, $r*2, 90, 90)
$chip.CloseFigure()
$cb = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(235,255,205,84))
$g.FillPath($cb, $chip); $cb.Dispose(); $chip.Dispose()
$pChip = New-TextPath $chipText $famSerif 44 0 0
$mc = New-Object System.Drawing.Drawing2D.Matrix; $mc.Translate(($chipX + $padX - $bc.X), ($chipY + $padY - $bc.Y)); $pChip.Transform($mc)
Draw-Styled $pChip ([System.Drawing.Color]::FromArgb(255,34,30,10)) $dark 0 $false
$pChip.Dispose()

# 保存 JPEG 质量 92
$enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
$ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]92)
$bmp.Save($out, $enc, $ep)
$g.Dispose(); $bmp.Dispose(); $img.Dispose()
Write-Output ('已生成: ' + $out)
