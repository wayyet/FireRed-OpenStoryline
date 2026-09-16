# 差分定位文字带：对比"底图"与"成品封面"，输出成品上每段文字的行范围（y 带）
# 用法: .\locate_text_bands.ps1 -Base <底图.jpg> -Cover <成品封面.jpg> [-PixelThreshold 16] [-MinBandHeight 2]
# 原理: ffmpeg 转 RGB(gbrp) 后做 difference 混合 → 灰度 → 按阈值二值化 → 每行面积平均压成 1 列
#       → rawvideo 逐行字节 → PowerShell 扫描连续非零行段
# 两个坑（勿改回去）:
#   ① 必须先 format=gbrp 再 blend，否则差分在 YUV 上做、format=gray 只剩亮度差，
#      彩色霓虹字/白色角标与亮背景亮度接近会整段漏检
#   ② 必须先 lut 二值化再 scale 行平均，否则细笔画被 1080 像素平均稀释成 0，带宽严重偏窄
param(
    [Parameter(Mandatory = $true)][string]$Base,
    [Parameter(Mandatory = $true)][string]$Cover,
    [int]$PixelThreshold = 16,   # 单像素差判"热"阈值(0-255)
    [int]$MinBandHeight  = 2     # 小于此高度的带忽略
)

# 旧 VS Code 会话 PATH 快照可能过期，先刷新再找 ffmpeg（见记忆 ffmpeg-winget-path-stale）
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

foreach ($f in @($Base, $Cover)) { if (-not (Test-Path -LiteralPath $f)) { throw ('缺少文件: ' + $f) } }
Add-Type -AssemblyName System.Drawing
$ia = [System.Drawing.Image]::FromFile($Base); $ib = [System.Drawing.Image]::FromFile($Cover)
$W = $ia.Width; $H = $ia.Height
if ($ib.Width -ne $W -or $ib.Height -ne $H) { $ia.Dispose(); $ib.Dispose(); throw ('两图尺寸不一致: ' + $W + 'x' + $H + ' vs ' + $ib.Width + 'x' + $ib.Height) }
$ia.Dispose(); $ib.Dispose()
Write-Output ('尺寸: ' + $W + 'x' + $H)

$raw = Join-Path $env:TEMP ('rowdiff_' + [guid]::NewGuid().ToString('N').Substring(0, 8) + '.raw')
$filter = "[0]format=gbrp[a];[1]format=gbrp[b];[a][b]blend=all_mode=difference,format=gray,lut=y=if(gte(val\,$PixelThreshold)\,255\,0),scale=1:${H}:flags=area"
ffmpeg -hide_banner -loglevel error -y -i $Base -i $Cover -filter_complex $filter -f rawvideo -pix_fmt gray $raw
if ($LASTEXITCODE -ne 0) { throw 'ffmpeg 差分失败' }

$b = [IO.File]::ReadAllBytes($raw)
Remove-Item -LiteralPath $raw -Force -Confirm:$false
$zeroRows = ($b | Where-Object { $_ -eq 0 }).Count
Write-Output ('全零行占比: ' + [math]::Round(100.0 * $zeroRows / $b.Length, 1) + '%  （越高说明两图越可能同帧，>90% 才建议整行像素带拷贝）')

Write-Output '--- 文字带 ---'
$inBand = $false; $start = 0
for ($y = 0; $y -lt $b.Length; $y++) {
    $hot = $b[$y] -ge 1
    if ($hot -and -not $inBand) { $start = $y; $inBand = $true }
    if (-not $hot -and $inBand) {
        if (($y - $start) -ge $MinBandHeight) {
            Write-Output ('文字带: y ' + $start + ' - ' + ($y - 1) + '  高 ' + ($y - $start) + 'px  峰值 ' + (($b[$start..($y - 1)] | Measure-Object -Maximum).Maximum))
        }
        $inBand = $false
    }
}
if ($inBand) { Write-Output ('文字带: y ' + $start + ' - ' + ($b.Length - 1)) }
