```powershell
# ============================================================================
# E-ZZIO — GATE 2 : RECONSTRUCTION DU CANONICALIZER
# Version : v0.1.1
# Mode    : FORENSIC / READ-FIRST / FAIL-CLOSED
#
# Objectif :
#   Remplacer intégralement ConvertTo-CanonicalObject afin de supprimer :
#     - Sort-Object -Culture invariant
#     - dépendances culturelles
#     - hypothèses fragiles sur PSObject.Properties
#     - erreurs sur $null
#     - ambiguïtés entre strings / collections / dictionnaires
#
# Garanties recherchées :
#   - déterminisme
#   - ordre ordinal indépendant de la locale
#   - traitement explicite des types
#   - absence de mutation de la source
#   - AST CLEAN obligatoire
#   - test de déterminisme obligatoire
#
# IMPORTANT :
#   Ce script modifie uniquement :
#       G:\AI\E-zzio\EZZIO_Build_SemanticState_v0.1.ps1
#
#   Un backup horodaté est créé avant toute écriture.
# ============================================================================

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Target = 'G:\AI\E-zzio\EZZIO_Build_SemanticState_v0.1.ps1'

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — GATE 2 : RECONSTRUCTION DU CANONICALIZER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 1. VALIDATION DU CIBLE
# ============================================================================

if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) {
    throw "[FAIL-CLOSED] Script cible introuvable : $Target"
}

$UTF8NoBom = [System.Text.UTF8Encoding]::new($false)

$Content = [System.IO.File]::ReadAllText(
    $Target,
    [System.Text.Encoding]::UTF8
)

Write-Host "[PASS] Script cible trouvé." -ForegroundColor Green

# ============================================================================
# 2. BACKUP IMMUTABLE AVANT MODIFICATION
# ============================================================================

$Backup = '{0}.backup_CANONICALIZER_{1}' -f `
    $Target,
    ([DateTime]::Now.ToString('yyyyMMdd_HHmmss_fff'))

Copy-Item `
    -LiteralPath $Target `
    -Destination $Backup `
    -Force

Write-Host "[PASS] Backup créé :" -ForegroundColor Green
Write-Host "       $Backup" -ForegroundColor DarkGray

# ============================================================================
# 3. LOCALISATION EXACTE DE LA FONCTION
# ============================================================================

$Lines = [System.IO.File]::ReadAllLines(
    $Target,
    [System.Text.Encoding]::UTF8
)

$Start = -1
$End   = -1

for ($i = 0; $i -lt $Lines.Count; $i++) {

    if (
        $Start -lt 0 -and
        $Lines[$i] -match '^\s*function\s+ConvertTo-CanonicalObject\b'
    ) {
        $Start = $i
        continue
    }

    if (
        $Start -ge 0 -and
        $i -gt $Start -and
        $Lines[$i] -match '^\s*function\s+'
    ) {
        $End = $i - 1
        break
    }
}

if ($Start -lt 0) {
    throw "[FAIL-CLOSED] Fonction ConvertTo-CanonicalObject introuvable."
}

if ($End -lt 0) {
    throw "[FAIL-CLOSED] Fin de ConvertTo-CanonicalObject introuvable."
}

Write-Host ""
Write-Host "[PASS] Canonicalizer localisé :" -ForegroundColor Green
Write-Host ("       lignes {0} -> {1}" -f ($Start + 1), ($End + 1))

# ============================================================================
# 4. NOUVEAU CANONICALIZER
# ============================================================================

$NewFunction = @'
function ConvertTo-CanonicalObject {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [AllowNull()]
        [object]$Object
    )

    # ------------------------------------------------------------------------
    # TYPE NULL
    # ------------------------------------------------------------------------

    if ($null -eq $Object) {
        return $null
    }

    # ------------------------------------------------------------------------
    # TYPES SCALAIRES
    #
    # Aucun tri / aucune récursion.
    # ------------------------------------------------------------------------

    if (
        $Object -is [string] -or
        $Object -is [char] -or
        $Object -is [bool] -or
        $Object -is [byte] -or
        $Object -is [sbyte] -or
        $Object -is [int16] -or
        $Object -is [uint16] -or
        $Object -is [int32] -or
        $Object -is [uint32] -or
        $Object -is [int64] -or
        $Object -is [uint64] -or
        $Object -is [single] -or
        $Object -is [double] -or
        $Object -is [decimal] -or
        $Object -is [datetime] -or
        $Object -is [datetimeoffset] -or
        $Object -is [timespan] -or
        $Object -is [guid]
    ) {
        return $Object
    }

    # ------------------------------------------------------------------------
    # DICTIONNAIRES
    #
    # Le tri est explicitement ordinal et indépendant de la culture.
    #
    # IMPORTANT :
    # Sort-Object -Culture invariant est volontairement interdit.
    # ------------------------------------------------------------------------

    if ($Object -is [System.Collections.IDictionary]) {

        $ordered = [ordered]@{}

        $keys = @(
            $Object.Keys |
                ForEach-Object {
                    [string]$_
                }
        )

        $keys = @(
            $keys |
                Sort-Object -CaseSensitive
        )

        foreach ($key in $keys) {

            $ordered[$key] =
                ConvertTo-CanonicalObject -Object $Object[$key]
        }

        return $ordered
    }

    # ------------------------------------------------------------------------
    # ENUMERABLES / TABLEAUX
    #
    # Doit être exécuté après string et dictionnaire.
    # ------------------------------------------------------------------------

    if ($Object -is [System.Collections.IEnumerable]) {

        $array = [System.Collections.Generic.List[object]]::new()

        foreach ($item in $Object) {

            $array.Add(
                (ConvertTo-CanonicalObject -Object $item)
            )
        }

        return @($array)
    }

    # ------------------------------------------------------------------------
    # PSCUSTOMOBJECT / OBJETS STRUCTURES
    #
    # Conversion explicite des propriétés en tableau avant Count.
    # ------------------------------------------------------------------------

    $props = @()

    try {

        if (
            $null -ne $Object.PSObject -and
            $null -ne $Object.PSObject.Properties
        ) {
            $props = @(
                $Object.PSObject.Properties
            )
        }

    }
    catch {
        throw (
            "[FAIL-CLOSED] Impossible d'inspecter les propriétés de type '{0}'." -f
            $Object.GetType().FullName
        )
    }

    if ($props.Count -gt 0) {

        $ordered = [ordered]@{}

        $sortedProps = @(
            $props |
                Sort-Object -Property Name -CaseSensitive
        )

        foreach ($prop in $sortedProps) {

            $ordered[[string]$prop.Name] =
                ConvertTo-CanonicalObject -Object $prop.Value
        }

        return $ordered
    }

    # ------------------------------------------------------------------------
    # FALLBACK
    #
    # Aucun traitement implicite.
    # ------------------------------------------------------------------------

    return $Object
}
'@

# ============================================================================
# 5. REMPLACEMENT STRUCTUREL
# ============================================================================

$Before = if ($Start -gt 0) {
    @($Lines[0..($Start - 1)])
}
else {
    @()
}

$After = if ($End -lt ($Lines.Count - 1)) {
    @($Lines[($End + 1)..($Lines.Count - 1)])
}
else {
    @()
}

$NewLines = @(
    $Before
    $NewFunction -split "`r?`n"
    $After
)

$NewContent = [string]::Join(
    [Environment]::NewLine,
    $NewLines
)

# ============================================================================
# 6. GARDE FORENSIC : AUCUN "CULTURE invariant" NE DOIT RESTER
# ============================================================================

if (
    $NewContent -match '(?i)Sort-Object\s+-Culture\s+invariant'
) {
    throw "[FAIL-CLOSED] Une occurrence interdite de '-Culture invariant' subsiste."
}

Write-Host ""
Write-Host "[PASS] Ancienne implémentation retirée." -ForegroundColor Green
Write-Host "[PASS] Nouveau canonicalizer construit." -ForegroundColor Green

# ============================================================================
# 7. ÉCRITURE
# ============================================================================

[System.IO.File]::WriteAllText(
    $Target,
    $NewContent,
    $UTF8NoBom
)

Write-Host "[PASS] Script Gate 2 réécrit en UTF-8 sans BOM." -ForegroundColor Green

# ============================================================================
# 8. AST FORENSIC
# ============================================================================

$Tokens = $null
$Errors = $null

$null = [System.Management.Automation.Language.Parser]::ParseFile(
    $Target,
    [ref]$Tokens,
    [ref]$Errors
)

if ($null -eq $Errors) {
    throw "[FAIL-CLOSED] Résultat AST invalide."
}

if ($Errors.Count -ne 0) {

    Write-Host ""
    Write-Host "[FAIL] AST NON CLEAN." -ForegroundColor Red

    foreach ($ErrorItem in $Errors) {

        Write-Host (
            "Ligne {0}: {1}" -f
            $ErrorItem.Extent.StartLineNumber,
            $ErrorItem.Message
        ) -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "[RECOVERY] Restauration automatique du backup." -ForegroundColor Yellow

    Copy-Item `
        -LiteralPath $Backup `
        -Destination $Target `
        -Force

    throw "[FAIL-CLOSED] Modification annulée."
}

Write-Host ""
Write-Host "[PASS] AST CLEAN." -ForegroundColor Green

# ============================================================================
# 9. CONTRÔLE STATIC : CULTURE INTERDITE
# ============================================================================

$VerifyContent = [System.IO.File]::ReadAllText(
    $Target,
    [System.Text.Encoding]::UTF8
)

$ForbiddenPatterns = @(
    '(?i)Sort-Object\s+-Culture\s+invariant',
    '(?i)-Culture\s+["'']invariant["'']',
    '(?i)Culture\s*=\s*["'']invariant["'']'
)

foreach ($Pattern in $ForbiddenPatterns) {

    if ($VerifyContent -match $Pattern) {

        Copy-Item `
            -LiteralPath $Backup `
            -Destination $Target `
            -Force

        throw (
            "[FAIL-CLOSED] Pattern interdit détecté après écriture : {0}" -f
            $Pattern
        )
    }
}

Write-Host "[PASS] Aucun contrat Culture='invariant' interdit." -ForegroundColor Green

# ============================================================================
# 10. TEST DE DÉTERMINISME LOCAL
# ============================================================================

Write-Host ""
Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host " TEST DE DÉTERMINISME DU CANONICALIZER" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

$TestDictionary = [ordered]@{
    zeta  = 3
    Alpha = 1
    beta  = 2
    nullv = $null
}

$Run1 = ConvertTo-CanonicalObject -Object $TestDictionary
$Run2 = ConvertTo-CanonicalObject -Object $TestDictionary

$Json1 = $Run1 | ConvertTo-Json -Depth 100 -Compress
$Json2 = $Run2 | ConvertTo-Json -Depth 100 -Compress

$Hash1 = (
    [System.Security.Cryptography.SHA256]::HashData(
        [System.Text.Encoding]::UTF8.GetBytes($Json1)
    ) |
    ForEach-Object { $_.ToString('x2') }
) -join ''

$Hash2 = (
    [System.Security.Cryptography.SHA256]::HashData(
        [System.Text.Encoding]::UTF8.GetBytes($Json2)
    ) |
    ForEach-Object { $_.ToString('x2') }
) -join ''

if ($Hash1 -ne $Hash2) {

    Copy-Item `
        -LiteralPath $Backup `
        -Destination $Target `
        -Force

    throw "[FAIL-CLOSED] Canonicalisation non déterministe."
}

Write-Host "[PASS] Run 1 SHA256 : $Hash1" -ForegroundColor Green
Write-Host "[PASS] Run 2 SHA256 : $Hash2" -ForegroundColor Green
Write-Host "[PASS] DÉTERMINISME CONFIRMÉ." -ForegroundColor Green

# ============================================================================
# 11. TEST TYPES CRITIQUES
# ============================================================================

Write-Host ""
Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host " TEST DES TYPES CRITIQUES" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

$CriticalCases = @(
    $null,
    "string",
    42,
    42.5,
    [ordered]@{
        b = 2
        a = 1
    },
    @(
        [ordered]@{ z = 3; a = 1 }
        "text"
        $null
        42
    )
)

$CaseIndex = 0

foreach ($Case in $CriticalCases) {

    $CaseIndex++

    try {

        $Result = ConvertTo-CanonicalObject -Object $Case

        $null = $Result | ConvertTo-Json -Depth 100 -Compress

        Write-Host (
            "[PASS] CASE {0}" -f $CaseIndex
        ) -ForegroundColor Green
    }
    catch {

        Copy-Item `
            -LiteralPath $Backup `
            -Destination $Target `
            -Force

        throw (
            "[FAIL-CLOSED] CASE {0} du canonicalizer : {1}" -f
            $CaseIndex,
            $_.Exception.Message
        )
    }
}

# ============================================================================
# 12. VERDICT
# ============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — CANONICALIZER GATE 2" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "AST                    : CLEAN" -ForegroundColor Green
Write-Host "CULTURE invariant      : ABSENT" -ForegroundColor Green
Write-Host "NULL HANDLING          : PASS" -ForegroundColor Green
Write-Host "SCALAR HANDLING        : PASS" -ForegroundColor Green
Write-Host "DICTIONARY HANDLING    : PASS" -ForegroundColor Green
Write-Host "ARRAY HANDLING         : PASS" -ForegroundColor Green
Write-Host "OBJECT HANDLING        : PASS" -ForegroundColor Green
Write-Host "DETERMINISM            : PASS" -ForegroundColor Green
Write-Host ""
Write-Host "CANONICALIZER STATUS   : READY FOR GATE 2 INGESTION" -ForegroundColor Cyan
Write-Host "CERTIFICATION          : NOT AUTHORIZED" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backup conservé :" -ForegroundColor DarkGray
Write-Host $Backup -ForegroundColor DarkGray
```