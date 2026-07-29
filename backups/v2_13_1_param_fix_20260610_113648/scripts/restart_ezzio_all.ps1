$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [switch]$Lan,
    [switch]$OpenFirewall,
    [switch]$StartComfy,
    [switch]$IncludeComfyStop
)

$ScriptsRoot = "G:\AI\E-zzio\scripts"

& (Join-Path $ScriptsRoot "stop_ezzio_all.ps1") -IncludeComfy:$IncludeComfyStop
& (Join-Path $ScriptsRoot "start_ezzio_all.ps1") -Lan:$Lan -OpenFirewall:$OpenFirewall -StartComfy:$StartComfy
