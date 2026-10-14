<#
CausaLab 桌面版一键打包（Windows / PowerShell）

用法：
    powershell -ExecutionPolicy Bypass -File desktop\build.ps1                # 全流程
    powershell -ExecutionPolicy Bypass -File desktop\build.ps1 -SkipWebBuild  # 跳过前端静态构建（out/ 已最新时）

产物：
    desktop\dist\CausaLab\CausaLab.exe
    （整个 desktop\dist\CausaLab 文件夹即绿色便携版，可整体拷贝分发；数据存放在 exe 同级的 data\ 下）
#>
[CmdletBinding()]
param([switch]$SkipWebBuild)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not $SkipWebBuild) {
    Write-Host "[1/3] 构建静态前端（npm run build:static）..."
    Push-Location (Join-Path $Root "frontend")
    try {
        npm run build:static
        if ($LASTEXITCODE -ne 0) { throw "npm run build:static 失败" }
    } finally { Pop-Location }
} else {
    Write-Host "[1/3] 跳过前端构建（-SkipWebBuild）"
}

Write-Host "[2/3] 安装桌面依赖组（uv sync --group desktop）..."
Push-Location (Join-Path $Root "backend")
try {
    uv sync --group desktop
    if ($LASTEXITCODE -ne 0) { throw "uv sync 失败" }
} finally { Pop-Location }

$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "未找到后端虚拟环境：$Py（请先运行 uv sync）" }

Write-Host "[3/3] PyInstaller 打包（onedir）..."
Push-Location $Root
try {
    & $Py -m PyInstaller "desktop\CausaLab.spec" --noconfirm `
        --distpath (Join-Path $Root "desktop\dist") `
        --workpath (Join-Path $Root "desktop\build")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败" }
} finally { Pop-Location }

$Exe = Join-Path $Root "desktop\dist\CausaLab\CausaLab.exe"
Write-Host ""
Write-Host "打包完成： $Exe"
Write-Host "提示：desktop\dist\CausaLab 整个文件夹即绿色便携版；数据存放在 exe 同级的 data\ 下。"
