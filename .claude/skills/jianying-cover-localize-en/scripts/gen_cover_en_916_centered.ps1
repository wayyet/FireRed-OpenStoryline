# 英文版 9:16 封面本地合成（不进剪映）：复刻中文版「居中三段式」排版
# 底图与中文封面像素级同帧 → 角标带/霓虹带直接从中文封面整行拷贝，只重画两段英文
Add-Type -AssemblyName System.Drawing

# ==== 配置 ====
$base = 'e:\Documents\kuaishou\output\covers\cover_v_base.jpg'                      # 底图（只读）
$zhCover = 'e:\Documents\kuaishou\output\吉隆坡柏威年广场\吉隆坡柏威年广场-封面.jpg' # 中文成品（只读，取角标/霓虹带）
$out  = 'e:\Documents\kuaishou\output\covers\吉隆坡柏威年广场EN-封面.jpg'            # 输出
$fontBlack = 'C:\Windows\Fonts\ariblk.ttf'      # Arial Black：金色大字（对齐中文粗黑体量感）
$fontSerif = 'C:\Windows\Fonts\georgiab.ttf'    # Georgia Bold：红色标题（对齐中文衬线笔锋感）

$lineTop  = 'WHO KNEW KL HIDES'      # 对应「吉隆坡竟藏着」
$lineG1   = 'GIANT GOLDEN'           # 对应「巨型金鸡喷泉」第一行
$lineG2   = 'ROOSTER FOUNTAIN'       # 第二行

# 中文封面文字带实测（行差分析）：角标 y79-104 / 红字 y427-497 / 霓虹 y591-758 / 金字 y1411-1520
$bandCorner = @(70, 115)    # 角标带拷贝范围
$bandNeon   = @(580, 770)   # 霓虹带拷贝范围
# =============

foreach ($f in @($base, $zhCover, $fontBlack, $fontSerif)) {
    if (-not (Test-Path -LiteralPath $f)) { throw ('缺少文件: ' + $f) }
}

$pfc = New-Object System.Drawing.Text.PrivateFontCollection
$pfc.AddFontFile($fontBlack); $pfc.AddFontFile($fontSerif)
$famBlack = $pfc.Families | Where-Object { $_.Name -match 'Arial Black' } | Select-Object -First 1
$famSerif = $pfc.Families | Where-Object { $_.Name -match 'Georgia' } | Select-Object -First 1
Write-Output ('已加载字体: ' + (($pfc.Families | ForEach-Object { $_.Name }) -join ' | '))

$img = [System.Drawing.Image]::FromFile($base)
$zh  = [System.Drawing.Image]::FromFile($zhCover)
$W = $img.Width; $H = $img.Height
$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$g.DrawImage($img, 0, 0, $W, $H)

# ── 角标带 + 霓虹带：从中文封面整行拷贝（保真保留 VLOG/2026、PAVILION、彩虹 Kuala Lumpur）──
foreach ($band in @($bandCorner, $bandNeon)) {
    $y0 = $band[0]; $h0 = $band[1] - $band[0]
    $dst = New-Object System.Drawing.Rectangle(0, $y0, $W, $h0)
    $src = New-Object System.Drawing.Rectangle(0, $y0, $W, $h0)
    $g.DrawImage($zh, $dst, $src, [System.Drawing.GraphicsUnit]::Pixel)
}

$sf = [System.Drawing.StringFormat]::GenericTypographic
function New-TextPath([string]$text, $family, [int]$style, [single]$size, [single]$x, [single]$y) {
    $p = New-Object System.Drawing.Drawing2D.GraphicsPath
    $p.AddString($text, $family, $style, $size, (New-Object System.Drawing.PointF($x, $y)), $sf)
    return $p
}
function Fit-Size([string]$text, $family, [int]$style, [single]$targetW) {
    $p = New-TextPath $text $family $style 100 0 0
    $w = $p.GetBounds().Width; $p.Dispose()
    return [single](100 * $targetW / $w)
}
# 平移 path：水平居中 + 垂直中心对齐到 cy
function Center-Path($path, [single]$cy) {
    $b = $path.GetBounds()
    $m = New-Object System.Drawing.Drawing2D.Matrix
    $m.Translate((($W - $b.Width) / 2 - $b.X), ($cy - $b.Height / 2 - $b.Y))
    $path.Transform($m)
}
function Draw-Shadow($path, [single]$dx, [single]$dy, $color) {
    $m = New-Object System.Drawing.Drawing2D.Matrix; $m.Translate($dx, $dy)
    $sp = $path.Clone(); $sp.Transform($m)
    $sb = New-Object System.Drawing.SolidBrush($color)
    $g.FillPath($sb, $sp); $sp.Dispose(); $sb.Dispose()
}
function Draw-Stroke($path, $color, [single]$w) {
    $pen = New-Object System.Drawing.Pen($color, $w)
    $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
    $g.DrawPath($pen, $path); $pen.Dispose()
}
# 三段渐变填充（按 path 包围盒纵向）
function Draw-GradFill($path, $cTop, $cMid, $cBot) {
    $b = $path.GetBounds()
    $rect = New-Object System.Drawing.RectangleF($b.X, ($b.Y - 1), $b.Width, ($b.Height + 2))
    $br = New-Object System.Drawing.Drawing2D.LinearGradientBrush($rect, $cTop, $cBot, [System.Drawing.Drawing2D.LinearGradientMode]::Vertical)
    $cb = New-Object System.Drawing.Drawing2D.ColorBlend(3)
    $cb.Colors = @($cTop, $cMid, $cBot); $cb.Positions = @([single]0, [single]0.55, [single]1)
    $br.InterpolationColors = $cb
    $g.FillPath($br, $path); $br.Dispose()
}

$bold = [int][System.Drawing.FontStyle]::Bold

# ── 顶部红字 WHO KNEW KL HIDES：暖色外发光 + 深红描边 + 红橙渐变（中心 y≈462，同中文红字带）──
$szT = Fit-Size $lineTop $famSerif $bold 900
$pT = New-TextPath $lineTop $famSerif $bold $szT 0 0
Center-Path $pT 462
Draw-Stroke $pT ([System.Drawing.Color]::FromArgb(70, 255, 120, 40)) 30    # 外层暖光
Draw-Stroke $pT ([System.Drawing.Color]::FromArgb(130, 255, 70, 20)) 16    # 内层光晕
Draw-Stroke $pT ([System.Drawing.Color]::FromArgb(255, 150, 12, 8)) 6      # 深红描边
Draw-GradFill $pT ([System.Drawing.Color]::FromArgb(255, 255, 105, 45)) ([System.Drawing.Color]::FromArgb(255, 240, 55, 28)) ([System.Drawing.Color]::FromArgb(255, 222, 18, 16))
$pT.Dispose()

# ── 底部金字两行：深投影 + 深棕描边 + 金色渐变 + 细亮边（整体中心 y≈1465，同中文金字带）──
$goldTop = [System.Drawing.Color]::FromArgb(255, 255, 242, 184)
$goldMid = [System.Drawing.Color]::FromArgb(255, 245, 198, 79)
$goldBot = [System.Drawing.Color]::FromArgb(255, 214, 140, 30)
$brown   = [System.Drawing.Color]::FromArgb(255, 92, 58, 14)
$shadowC = [System.Drawing.Color]::FromArgb(140, 40, 26, 8)

$szG1 = Fit-Size $lineG1 $famBlack $bold 840
$szG2 = Fit-Size $lineG2 $famBlack $bold 980
$pG1 = New-TextPath $lineG1 $famBlack $bold $szG1 0 0
$pG2 = New-TextPath $lineG2 $famBlack $bold $szG2 0 0
Center-Path $pG1 1420
Center-Path $pG2 1530
foreach ($p in @($pG1, $pG2)) {
    Draw-Shadow $p 5 7 $shadowC
    Draw-Stroke $p $brown 8
    Draw-GradFill $p $goldTop $goldMid $goldBot
    Draw-Stroke $p ([System.Drawing.Color]::FromArgb(120, 255, 250, 220)) 2  # 细亮边提立体感
    $p.Dispose()
}

# 保存 JPEG 质量 92
$enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
$ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]92)
$bmp.Save($out, $enc, $ep)
$g.Dispose(); $bmp.Dispose(); $img.Dispose(); $zh.Dispose()
Write-Output ('已生成: ' + $out)
