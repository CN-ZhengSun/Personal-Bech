# 测试工作台守护进程：每 20 秒检测后端/前端，挂了自动拉起
while ($true) {
    Start-Sleep -Seconds 20
    & "D:\Test-Bench\start-services.ps1" *> $null
}
