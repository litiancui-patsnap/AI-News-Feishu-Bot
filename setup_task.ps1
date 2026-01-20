$action = New-ScheduledTaskAction -Execute "e:\projects\scrapegraph_demo\run_bot.bat" -WorkingDirectory "e:\projects\scrapegraph_demo"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:50AM
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName "AI资讯日报" -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "定时任务创建成功！每天8:50自动运行"
