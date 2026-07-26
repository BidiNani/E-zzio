[CmdletBinding()]
param(
    $Manifest,
    $RegistryDir
)

Write-Verbose "🧩 [Resolver] Résolution topologique avec détection de cycles..."

$modules = @(
    $Manifest.modules |
    Where-Object { $_.enabled -eq $true }
)

$resolved = [System.Collections.Generic.List[object]]::new()
$visiting = @{}
$visited = @{}

function Resolve-Node($module) {
    $path = $module.path

    if ([string]::IsNullOrWhiteSpace($path)) {
        return
    }

    if ($visiting.ContainsKey($path)) {
        throw [System.Exception]::new("CYCLE::$path")
    }

    if ($visited.ContainsKey($path)) {
        return
    }

    $visiting[$path] = $true

    foreach ($dep in @($module.depends_on)) {
        $depModule = @(
            $modules |
            Where-Object { $_.path -eq $dep }
        )

        if ($depModule.Count -ne 1) {
            throw "❌ Erreur de dépendance : Le module '$path' dépend de '$dep', mais ce dernier est absent ou désactivé dans le manifeste."
        }

        $depFullPath = Join-Path $RegistryDir $dep
        if (-not (Test-Path $depFullPath)) {
            throw "❌ Erreur physique : Le module '$path' dépend de '$dep', mais le fichier est introuvable sur le disque."
        }

        Resolve-Node $depModule[0]
    }

    $visiting.Remove($path)
    $visited[$path] = $true
    $resolved.Add($module)
}

foreach ($module in ($modules | Sort-Object priority)) {
    Resolve-Node $module
}

return $resolved.ToArray()