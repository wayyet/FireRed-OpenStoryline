# 英文版 9:16 封面本地合成（不进剪映）：底图 + TRX 样式排版
# 版式参照 EXCHANGE TRX 中文封面：左侧三段大字 + 中部两行小字 + 底部衬线 logo 大字 + 蓝色圆点
Add-Type -AssemblyName System.Drawing

# ==== 配置 ====
$base = 'e:\Documents\kuaishou\output\covers\cover_v_base.jpg'                # 底图（只读，不覆盖）
$out  = 'e:\Documents\kuaishou\output\covers\吉隆坡柏威年广场EN-封面.jpg'      # 输出
$fontBlack = 'C:\Windows\Fonts\ariblk.ttf'                                    # Arial Black：三段大字
$fontSmall = 'C:\Windows\Fonts\arialbd.ttf'                                   # Arial Bold：小字
$fontSerif = 'C:\Users\wayyet\AppData\Local\JianyingPro\User Data\Cache\effect\643593\e02d50dc998334eb230ccf6abd8703d2\Prata-Regular.ttf'  # Prata：PAVILION

$line1 = "COME TO KL"        # 主标题（蓝）   ← 對應「來吉隆坡」
$line2 = "DON'T JUST SEE"    # 第二行（白描边）← 對應「別祇逛」
$line3 = "TWIN TOWERS"       # 第三行（白+蓝光）← 對應「雙子塔」
$small1 = 'Golden rooster fountain x flower wonderland'
$small2 = 'Free entry · Photo heaven'
$logo  = 'PAVILION'          # 底部衬线大字   ← 對應 T•RX
# =============

$pfc = New-Object System.Drawing.Text.PrivateFontCollection
$pfc.AddFontFile($fontBlack); $pfc.AddFontFile($fontSmall); $pfc.AddFontFile($fontSerif)
$famBlack = $pfc.Families | Where-Object { $_.Name -match 'Arial Black' } | Select-Object -First 1
$famSmall = $pfc.Families | Where-Object { $_.Name -match '^Arial$' } | Select-Object -First 1
$famSerif = $pfc.Families | Where-Object { $_.Name -match 'Prata' } | Select-Object -First 1
if (-not $famSmall) { $famSmall = $famBlack }
Write-Output ('已加载字体: ' + (($pfc.Families | ForEach-Object { $_.Name }) -join ' | '))

$img = [System.Drawing.Image]::FromFile($base)
$W = $img.Width; $H = $img.Height
$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$g.DrawImage($img, 0, 0, $W, $H)

$sf = [System.Drawing.StringFormat]::GenericTypographic

function New-TextPath([string]$text, $family, [int]$style, [single]$size, [single]$x, [single]$y) {
    $p = New-Object System.Drawing.Drawing2D.GraphicsPath
    $p.AddString($text, $family, $style, $size, (New-Object System.Drawing.PointF($x, $y)), $sf)
    return $p
}
# 按目标宽度自适应字号
function Fit-Size([string]$text, $family, [int]$style, [single]$targetW) {
    $p = New-TextPath $text $family $style 100 0 0
    $w = $p.GetBounds().Width; $p.Dispose()
    return [single](100 * $targetW / $w)
}
# 把 path 平移到 (x, top)
function Move-Path($path, [single]$x, [single]$top) {
    $b = $path.GetBounds()
    $m = New-Object System.Drawing.Drawing2D.Matrix
    $m.Translate(($x - $b.X), ($top - $b.Y)); $path.Transform($m)
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
function Draw-Fill($path, $color) {
    $br = New-Object System.Drawing.SolidBrush($color)
    $g.FillPath($br, $path); $br.Dispose()
}

$bold = [int][System.Drawing.FontStyle]::Bold
$reg  = [int][System.Drawing.FontStyle]::Regular
$blue    = [System.Drawing.Color]::FromArgb(255, 32, 62, 228)    # TRX 主标题蓝
$white   = [System.Drawing.Color]::White
$iceWhite= [System.Drawing.Color]::FromArgb(255, 234, 246, 255)  # 「別祇逛」字面浅蓝白
$shadowC = [System.Drawing.Color]::FromArgb(150, 30, 34, 46)

# ── 1. COME TO KL：纯蓝大字 + 白细描边（對應「來吉隆坡」，y≈17.5%）──
$sz1 = Fit-Size $line1 $famBlack $bold 1000
$p1 = New-TextPath $line1 $famBlack $bold $sz1 0 0
Move-Path $p1 42 336
Draw-Shadow $p1 5 7 ([System.Drawing.Color]::FromArgb(90, 20, 24, 40))
Draw-Stroke $p1 $white 5
Draw-Fill   $p1 $blue
$p1.Dispose()

# ── 2. DON'T JUST SEE：浅蓝白字 + 厚白描边 + 深灰投影（對應「別祇逛」，y≈37.5%）──
$sz2 = Fit-Size $line2 $famBlack $bold 920
$p2 = New-TextPath $line2 $famBlack $bold $sz2 0 0
Move-Path $p2 42 720
Draw-Shadow $p2 10 13 ([System.Drawing.Color]::FromArgb(185, 26, 30, 44))
Draw-Stroke $p2 ([System.Drawing.Color]::FromArgb(140, 36, 42, 58)) 26   # 白边外一圈深晕
Draw-Stroke $p2 $white 15
Draw-Fill   $p2 $iceWhite
$p2.Dispose()

# ── 3. 两行小字：白字细深描边（y≈50%）──
$pS1 = New-TextPath $small1 $famSmall $bold 31 0 0
Move-Path $pS1 250 962
Draw-Stroke $pS1 ([System.Drawing.Color]::FromArgb(200, 30, 34, 46)) 3
Draw-Fill   $pS1 $white
$pS1.Dispose()
$pS2 = New-TextPath $small2 $famSmall $bold 31 0 0
Move-Path $pS2 250 1018
Draw-Stroke $pS2 ([System.Drawing.Color]::FromArgb(200, 30, 34, 46)) 3
Draw-Fill   $pS2 $white
$pS2.Dispose()

# ── 4. TWIN TOWERS：白字 + 蓝描边 + 蓝色外发光（對應「雙子塔」，y≈57.5%）──
$sz3 = Fit-Size $line3 $famBlack $bold 840
$p3 = New-TextPath $line3 $famBlack $bold $sz3 0 0
Move-Path $p3 42 1104
Draw-Stroke $p3 ([System.Drawing.Color]::FromArgb(55, 60, 110, 255)) 30   # 外层柔光
Draw-Stroke $p3 ([System.Drawing.Color]::FromArgb(110, 50, 95, 250)) 18   # 中层光晕
Draw-Stroke $p3 ([System.Drawing.Color]::FromArgb(255, 36, 66, 232)) 9    # 蓝描边
Draw-Fill   $p3 $white
$p3.Dispose()

# ── 5. PAVILION：Prata 白色衬线大字 + 蓝色圆点悬于第二个 I 上方（對應 T•RX，y≈75%）──
$szL = Fit-Size $logo $famSerif $reg 880
$pL = New-TextPath $logo $famSerif $reg $szL 0 0
$logoX = 60; $logoTop = 1442
Move-Path $pL $logoX $logoTop
Draw-Shadow $pL 5 7 ([System.Drawing.Color]::FromArgb(110, 20, 24, 40))
Draw-Fill   $pL $white
$pL.Dispose()
# 蓝点定位：测 "PAVIL" 与 "PAVILI" 的宽度差，找到第二个 I 的中心
$pa = New-TextPath 'PAVIL'  $famSerif $reg $szL 0 0; $wA = $pa.GetBounds().Width; $pa.Dispose()
$pb = New-TextPath 'PAVILI' $famSerif $reg $szL 0 0; $wB = $pb.GetBounds().Width; $pb.Dispose()
$dotCx = $logoX + ($wA + $wB) / 2
$dotR = 26
$dotCy = $logoTop - $dotR - 14   # 悬于字母上方
$db = New-Object System.Drawing.SolidBrush($blue)
$g.FillEllipse($db, ($dotCx - $dotR), ($dotCy - $dotR), ($dotR * 2), ($dotR * 2))
$db.Dispose()

# 保存 JPEG 质量 92
$enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
$ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]92)
$bmp.Save($out, $enc, $ep)
$g.Dispose(); $bmp.Dispose(); $img.Dispose()
Write-Output ('已生成: ' + $out)
