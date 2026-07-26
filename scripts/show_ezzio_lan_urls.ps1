$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Get-EzzioLanIPs {
    $ips = New-Object System.Collections.Generic.List[string]

    try {
        $interfaces = [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() |
            Where-Object {
                $_.OperationalStatus -eq [System.Net.NetworkInformation.OperationalStatus]::Up -and
                $_.NetworkInterfaceType -ne [System.Net.NetworkInformation.NetworkInterfaceType]::Loopback -and
                $_.NetworkInterfaceType -ne [System.Net.NetworkInformation.NetworkInterfaceType]::Tunnel
            }

        foreach ($iface in $interfaces) {
            foreach ($addr in $iface.GetIPProperties().UnicastAddresses) {
                $ip = [string]$addr.Address.IPAddressToString

                if ($ip -match '^\d{1,3}(\.\d{1,3}){3}$' -and
                    $ip -notlike '127.*' -and
                    $ip -notlike '169.254.*' -and
                    $ip -ne '0.0.0.0') {
                    $ips.Add($ip)
                }
            }
        }
    }
    catch {}

    try {
        $netIps = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object {
                $_.IPAddress -match '^\d{1,3}(\.\d{1,3}){3}$' -and
                $_.IPAddress -notlike '127.*' -and
                $_.IPAddress -notlike '169.254.*' -and
                $_.IPAddress -ne '0.0.0.0' -and
                $_.AddressState -eq 'Preferred'
            } |
            Select-Object -ExpandProperty IPAddress

        foreach ($ip in $netIps) {
            if ($ip) { $ips.Add([string]$ip) }
        }
    }
    catch {}

    $clean = @(
        $ips |
            Where-Object {
                $_ -and
                $_.Trim().Length -gt 0 -and
                $_ -match '^\d{1,3}(\.\d{1,3}){3}$'
            } |
            Sort-Object -Unique
    )

    $preferred = @(
        $clean | Where-Object { $_ -like '192.168.*' -or $_ -like '10.*' -or $_ -like '172.16.*' -or $_ -like '172.17.*' -or $_ -like '172.18.*' -or $_ -like '172.19.*' -or $_ -like '172.2*' -or $_ -like '172.30.*' -or $_ -like '172.31.*' }
    )

    if ($preferred.Count -gt 0) {
        return $preferred
    }

    return $clean
}

$ips = @(Get-EzzioLanIPs)

Write-Host ""
Write-Host "=== E-ZZIO LAN URLs ===" -ForegroundColor Cyan

if ($ips.Count -eq 0) {
    Write-Warning "Aucune IP LAN détectée."
    Write-Host "Essaie manuellement l'IP déjà vue : http://192.168.1.10:8000/supervisor/mobile-home" -ForegroundColor Yellow
    return
}

foreach ($ip in $ips) {
    if ($ip -and $ip.Trim().Length -gt 0) {
        Write-Host "http://$ip:8000/supervisor/mobile-home"
        Write-Host "http://$ip:8000/status"
        Write-Host "http://$ip:8000/omni-bridge/mobile/config"
        Write-Host ""
    }
}
