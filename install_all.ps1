# =============================================================================
#  OpenStoryline · Windows 一键安装（venv 版，无需 conda / git）
#  双击同目录的「一键安装.bat」即可触发本脚本。
#  做的事：找/装 Python3.11 → 建 .venv → 下模型资源 → pip 装依赖。停在「填 Key」前。
# =============================================================================
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
try { Start-Transcript -Path ".\install_log.txt" -Append | Out-Null } catch {}
Write-Host "================ OpenStoryline 一键安装 ================" -ForegroundColor Cyan

# --- 1) 找 Python >=3.11（优先用已装的，避免再装一个）-----------------------
$pyCmd = $null; $pyArgs = @()
$cands = @(
    @{ c = "py";      a = @("-3.12") },
    @{ c = "py";      a = @("-3.11") },
    @{ c = "py";      a = @("-3.13") },
    @{ c = "python";  a = @() },
    @{ c = "python3"; a = @() }
)
foreach ($cand in $cands) {
    if (Get-Command $cand.c -ErrorAction SilentlyContinue) {
        $v = & $cand.c @($cand.a + "--version") 2>$null
        if ($LASTEXITCODE -eq 0 -and $v -match "Python (\d+)\.(\d+)") {
            $maj = [int]$Matches[1]; $min = [int]$Matches[2]
            if ($maj -eq 3 -and $min -ge 11) {
                $pyCmd = $cand.c; $pyArgs = $cand.a
                Write-Host "[OK] 使用 $v  ($($cand.c) $($cand.a -join ' '))" -ForegroundColor Green
                break
            }
        }
    }
}
if (-not $pyCmd) {
    Write-Host "[!] 未找到 Python>=3.11，尝试用 winget 安装 3.11..." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        if (Get-Command py -ErrorAction SilentlyContinue) {
            $v = & py -3.11 --version 2>$null
            if ($LASTEXITCODE -eq 0 -and $v -match "Python 3\.11") { $pyCmd = "py"; $pyArgs = @("-3.11"); Write-Host "[OK] 已安装 $v" -ForegroundColor Green }
        }
    }
}
if (-not $pyCmd) {
    Write-Host "[X] 没有可用的 Python>=3.11 且自动安装失败。" -ForegroundColor Red
    Write-Host "    手动装 3.11：https://www.python.org/downloads/release/python-3119/（勾选 Add to PATH），装完重跑。" -ForegroundColor Red
    try { Stop-Transcript | Out-Null } catch {}; Read-Host "按回车退出"; exit 1
}

# --- 2) 建虚拟环境 .venv ------------------------------------------------------
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "[i] 创建虚拟环境 .venv ..." -ForegroundColor Blue
    & $pyCmd @($pyArgs + @("-m", "venv", ".venv"))
} else { Write-Host "[OK] .venv 已存在，复用" -ForegroundColor Green }
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "[X] venv 创建失败" -ForegroundColor Red; Read-Host "按回车退出"; exit 1 }

# --- 3) 升级 pip -------------------------------------------------------------
& $venvPy -m pip install --upgrade pip

# --- 4) 下载模型与资源（调用同目录脚本）-------------------------------------
if (Test-Path ".\download_resources.ps1") {
    Write-Host "[i] 下载模型与资源(腾讯 COS，约数百 MB)..." -ForegroundColor Blue
    & powershell -NoProfile -ExecutionPolicy Bypass -File ".\download_resources.ps1"
} else {
    Write-Host "[!] 缺 download_resources.ps1，跳过资源下载（之后需手动下 models/resource）" -ForegroundColor Yellow
}

# --- 5) 安装 Python 依赖 -----------------------------------------------------
Write-Host "[i] 安装依赖(清华镜像，含 torch 等，约几 GB，请耐心)..." -ForegroundColor Blue
& $venvPy -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] 镜像源失败，改用默认源重试..." -ForegroundColor Yellow
    & $venvPy -m pip install -r requirements.txt
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] 依赖安装未完全成功，请把 install_log.txt 发我，我来定位。" -ForegroundColor Red
    try { Stop-Transcript | Out-Null } catch {}; Read-Host "按回车退出"; exit 1
}

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "  环境与软件已装好！只差最后一步——填 API Key" -ForegroundColor Green
Write-Host "  1) 拿到 Key 后，编辑本目录 config.toml 的 [llm] 和 [vlm]" -ForegroundColor Green
Write-Host "     （照抄 ..\OpenStoryline安装\安装说明.md 第 5 节）" -ForegroundColor Green
Write-Host "  2) 然后双击 启动网页界面.bat（浏览器开 http://127.0.0.1:7860）" -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
try { Stop-Transcript | Out-Null } catch {}
Read-Host "按回车退出"
