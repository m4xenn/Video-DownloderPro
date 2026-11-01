param([Parameter(Mandatory=$true)][ValidatePattern('^[a-p]{32}$')][string]$ExtensionId,[ValidateSet('All','Chrome','Edge','Brave')][string]$Browser='All',[switch]$Unregister)
$ErrorActionPreference = 'Stop'
$hostName = 'com.videodownloaderpro.bridge'
$targetDir = Join-Path $env:LOCALAPPDATA 'VideoDownloaderPro\BrowserBridge'
$manifestPath = Join-Path $targetDir "$hostName.json"
$browserKeys = @{
    Chrome = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$hostName"
    Edge = "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$hostName"
    # Brave on Windows uses the Chrome-compatible host registration (verified in native acceptance).
    Brave = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$hostName"
}
$keys = if ($Browser -eq 'All') { @($browserKeys.Values | Select-Object -Unique) } else { @($browserKeys[$Browser]) }
if ($Unregister) {
    foreach ($key in $keys) { if (Test-Path -LiteralPath $key) { Remove-Item -LiteralPath $key } }
    Write-Output 'Native host registration removed. Extension can be removed in browser settings.'
    exit
}
$projectDir = Split-Path $PSScriptRoot -Parent
$exePath = Join-Path $projectDir 'dist\BrowserBridge\VDPBrowserBridge.exe'
if (!(Test-Path -LiteralPath $exePath)) { throw 'Build the native host first; see docs/BROWSER_EXTENSION.md.' }
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
Copy-Item -LiteralPath $exePath -Destination (Join-Path $targetDir 'VDPBrowserBridge.exe') -Force
$origins = @("chrome-extension://$ExtensionId/")
if (Test-Path -LiteralPath $manifestPath) {
    $existing = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($existing.name -ne $hostName) { throw 'Existing native host manifest has an unexpected identity.' }
    $origins += @($existing.allowed_origins | Where-Object { $_ -match '^chrome-extension://[a-p]{32}/$' })
}
$manifestJson = @{ name=$hostName; description='Video Downloader Pro companion'; path=(Join-Path $targetDir 'VDPBrowserBridge.exe'); type='stdio'; allowed_origins=@($origins | Select-Object -Unique) } | ConvertTo-Json
[System.IO.File]::WriteAllText($manifestPath, $manifestJson, [System.Text.UTF8Encoding]::new($false))
foreach ($key in $keys) { New-Item -Path $key -Force | Out-Null; Set-Item -LiteralPath $key -Value $manifestPath }
Write-Output 'Registered for this Windows user only. Restart the extension connection with the app open.'
