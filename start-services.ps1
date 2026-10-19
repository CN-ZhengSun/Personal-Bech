# 测试工作台服务启动脚本（幂等：已运行则不重复启动）
$ErrorActionPreference = "SilentlyContinue"
$logDir = "D:\Test-Bench\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-Port($hostName, $port) {
    try {
        $c = New-Object Net.Sockets.TcpClient
        $c.Connect($hostName, $port)
        $c.Close()
        return $true
    } catch {
        return $false
    }
}

# 后端 8000
if (-not (Test-Port "127.0.0.1" 8000)) {
    Start-Process -FilePath "D:\Test-Bench\backend\.venv\Scripts\python.exe" `
        -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" `
        -WorkingDirectory "D:\Test-Bench\backend" `
        -WindowStyle Hidden `
        -RedirectStandardOutput "$logDir\backend.log" `
        -RedirectStandardError "$logDir\backend.err.log"
    Write-Output "[$(Get-Date -Format 'HH:mm:ss')] backend restarted"
} else {
    Write-Output "[$(Get-Date -Format 'HH:mm:ss')] backend already running"
}

# 前端 5173
if (-not (Test-Port "127.0.0.1" 5173)) {
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c","npm run dev > `"$logDir\frontend.log`" 2>&1" `
        -WorkingDirectory "D:\Test-Bench\frontend" `
        -WindowStyle Hidden
    Write-Output "[$(Get-Date -Format 'HH:mm:ss')] frontend restarted"
} else {
    Write-Output "[$(Get-Date -Format 'HH:mm:ss')] frontend already running"
}
