param(
    [switch]$Lan,
    [switch]$OpenFirewall,
    [switch]$StartComfy,
    [switch]$IncludeComfyStop
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptsRoot = "G:\AI\E-zzio\scripts"

& (Join-Path $ScriptsRoot "stop_ezzio_all.ps1") -IncludeComfy:$IncludeComfyStop
& (Join-Path $ScriptsRoot "start_ezzio_all.ps1") -Lan:$Lan -OpenFirewall:$OpenFirewall -StartComfy:$StartComfy
