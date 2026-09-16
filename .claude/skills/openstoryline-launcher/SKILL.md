---
name: openstoryline-launcher
description: 一键启动 FireRed-OpenStoryline 的两个本地服务——MCP 服务（open_storyline.mcp.server）与网页界面（agent_fastapi:app，默认 http://127.0.0.1:7860），并在网页端口就绪后用浏览器打开。适用于"启动 OpenStoryline""启动 MCP 服务""打开网页界面""启动这两个程序""把 FireRed 跑起来"等场景。触发词：启动 OpenStoryline、启动 MCP 服务、打开网页界面、openstoryline launcher、启动 FireRed。
---

# 一键启动 OpenStoryline（MCP 服务 + 网页界面）

封装 FireRed-OpenStoryline 项目的两个本地服务的启动流程，免去手动双击两个 .bat、再手动开浏览器。

## 项目位置与关键参数

- 项目根目录：`E:\Documents\kuaishou\FireRed-OpenStoryline`
- 虚拟环境 Python：`<项目根>\.venv\Scripts\python.exe`
- 必须设置 `PYTHONPATH=src`（两个服务都依赖）
- MCP 服务：`python -m open_storyline.mcp.server`
- 网页界面：`python -m uvicorn agent_fastapi:app --host 127.0.0.1 --port 7860`
- 网页地址：http://127.0.0.1:7860
- 对应的人工双击入口（给人用）：`启动MCP服务.bat`、`启动网页界面.bat`、`一键安装.bat`

## 前置检查

1. 确认 `<项目根>\.venv\Scripts\python.exe` 存在；不存在时先运行 `一键安装.bat`（或 `install_all.ps1`）创建虚拟环境。
2. 确认 7860 端口未被占用（如已占用说明网页界面可能已在运行，直接打开网页即可）。

## 启动步骤（PowerShell，后台常驻）

```powershell
$proj = "E:\Documents\kuaishou\FireRed-OpenStoryline"
$py   = Join-Path $proj ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "未找到 .venv，请先运行 一键安装.bat" }
$env:PYTHONPATH = "src"

# 1) 启动 MCP 服务（后台窗口，常驻）
Start-Process -FilePath $py -ArgumentList "-m","open_storyline.mcp.server" -WorkingDirectory $proj

# 2) 启动网页界面（后台窗口，常驻）
Start-Process -FilePath $py `
  -ArgumentList "-m","uvicorn","agent_fastapi:app","--host","127.0.0.1","--port","7860" `
  -WorkingDirectory $proj
```

> 说明：两个服务都是常驻前台阻塞进程，必须用 `Start-Process`（或独立窗口）后台启动，不要直接在当前会话前台运行，否则会卡住后续操作。在自动化场景下，应直接调用上面的 python 命令，而不要走 .bat（.bat 末尾的 `pause` 会阻塞）。

## 等待网页就绪并打开

启动后等待 uvicorn 把 7860 端口拉起来（一般几秒，首次加载模型可能更久），端口可访问后再打开浏览器：

```powershell
$ok = $false
1..30 | ForEach-Object {
  if (-not $ok) {
    try {
      Invoke-WebRequest -Uri "http://127.0.0.1:7860" -UseBasicParsing -TimeoutSec 2 | Out-Null
      $ok = $true
    } catch { Start-Sleep -Seconds 1 }
  }
}
Start-Process "http://127.0.0.1:7860"
```

## 停止服务

```powershell
# 按端口找到并结束网页界面进程
Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force }
# MCP 服务可在其独立窗口中 Ctrl+C，或按命令行匹配结束 python -m open_storyline.mcp.server 进程
```

## 验收

- MCP 服务窗口出现 `Starting OpenStoryline MCP server ...` 且未报错退出。
- 网页界面窗口出现 uvicorn 的 `Uvicorn running on http://127.0.0.1:7860`。
- 浏览器能正常打开 http://127.0.0.1:7860 页面。
