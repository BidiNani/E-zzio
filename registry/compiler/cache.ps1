param(
    $ManifestPath,
    $RegistryIndex,
    $CachePath,
    $CompilerVersion,
    $BuildProfile = "all"
)

$manifestHash = (Get-FileHash $ManifestPath -Algorithm SHA256).Hash
$moduleHash = ($RegistryIndex.Values | Sort-Object path | ForEach-Object { $_.sha256 }) -join ""

$raw = "$CompilerVersion|$BuildProfile|$manifestHash|$moduleHash"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($raw)
$hashBytes = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
$globalHash = [BitConverter]::ToString($hashBytes) -replace "-"

$changed = $true
if (Test-Path $CachePath) {
    $old = Get-Content $CachePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($old.registry_hash -eq $globalHash -and $old.profile -eq $BuildProfile -and $old.manifest_hash -eq $manifestHash) {
        $changed = $false
    }
}

return @{
    Changed      = $changed
    GlobalHash   = $globalHash
    ManifestHash = $manifestHash
}