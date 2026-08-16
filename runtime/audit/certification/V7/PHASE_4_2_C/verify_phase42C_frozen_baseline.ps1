# ==============================================================================
# E-ZZIO V7 — PHASE 4.2-C
# FROZEN BASELINE — SURGICAL INTEGRITY VERIFIER
# VERSION : 2.0.0
# STRICT / FAIL-CLOSED / ZERO-WRITE
# ==============================================================================

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = "G:\AI\E-zzio"

$Baseline = Join-Path `
    $Root `
    "runtime\audit\certification\V7\PHASE_4_2_C\PHASE_4_2_C_CERTIFIED_BASELINE.json"

$ExpectedBaselineHash =
    "FEAEB40115CD21BCDEE0DEC71922A6D3C8ADD7518257E469FBC555CBF71EA36F"

$Pass = 0
$Fail = 0

function PASS {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    $script:Pass++

    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function CHECK {
    param(
        [Parameter(Mandatory)]
        [bool]$Condition,

        [Parameter(Mandatory)]
        [string]$Message
    )

    if (-not $Condition) {
        $script:Fail++
        throw "[FAIL-CLOSED] $Message"
    }

    PASS $Message
}

function GET-PROPERTY {
    param(
        [Parameter(Mandatory)]
        [object]$Object,

        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [string]$Description
    )

    $Property = $Object.PSObject.Properties[$Name]

    CHECK `
        ($null -ne $Property) `
        $Description

    return $Property.Value
}

function HASH-FILE {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    CHECK `
        (Test-Path -LiteralPath $Path -PathType Leaf) `
        "Présence artefact : $Path"

    $Result = Get-FileHash `
        -LiteralPath $Path `
        -Algorithm SHA256 `
        -ErrorAction Stop

    CHECK `
        ($null -ne $Result) `
        "SHA256 calculé : $Path"

    $Hash = $Result.Hash.ToUpperInvariant()

    CHECK `
        ($Hash -match '^[A-F0-9]{64}$') `
        "SHA256 syntaxiquement valide : $Path"

    return $Hash
}

function CHECK-EXACT-PROPERTIES {
    param(
        [Parameter(Mandatory)]
        [object]$Object,

        [Parameter(Mandatory)]
        [string[]]$Expected,

        [Parameter(Mandatory)]
        [string]$Scope
    )

    $Actual = @(
        $Object.PSObject.Properties.Name
    )

    foreach ($Name in $Expected) {
        CHECK `
            ($Actual -contains $Name) `
            "$Scope : propriété '$Name' présente"
    }

    foreach ($Name in $Actual) {
        CHECK `
            ($Expected -contains $Name) `
            "$Scope : aucune propriété inattendue '$Name'"
    }
}

try {

    # ==========================================================================
    # HEADER
    # ==========================================================================

    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host " E-ZZIO V7 — PHASE 4.2-C — SURGICAL FROZEN BASELINE VERIFICATION"
    Write-Host ("=" * 100)
    Write-Host ""

    Write-Host "POWERSHELL : $($PSVersionTable.PSVersion)"
    Write-Host "MODE       : READ-ONLY"
    Write-Host "POLICY     : FAIL-CLOSED"
    Write-Host "WRITE      : 0"
    Write-Host ""

    CHECK `
        ($PSVersionTable.PSVersion.Major -ge 7) `
        "PowerShell 7+"

    # ==========================================================================
    # 1 — BASELINE EXISTENCE + CRYPTOGRAPHIC HASH
    # ==========================================================================

    Write-Host ("=" * 100)
    Write-Host " 1/8 — BASELINE CRYPTOGRAPHIC INTEGRITY"
    Write-Host ("=" * 100)

    CHECK `
        (Test-Path -LiteralPath $Baseline -PathType Leaf) `
        "Baseline présente"

    $BaselineHash = (
        Get-FileHash `
            -LiteralPath $Baseline `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToUpperInvariant()

    Write-Host ""
    Write-Host "EXPECTED : $ExpectedBaselineHash"
    Write-Host "ACTUAL   : $BaselineHash"
    Write-Host ""

    CHECK `
        ($BaselineHash -eq $ExpectedBaselineHash) `
        "Baseline SHA256 intact"

    # ==========================================================================
    # 2 — JSON PARSE
    # ==========================================================================

    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host " 2/8 — JSON STRUCTURAL VALIDATION"
    Write-Host ("=" * 100)

    $Raw = Get-Content `
        -LiteralPath $Baseline `
        -Raw `
        -ErrorAction Stop

    CHECK `
        (-not [string]::IsNullOrWhiteSpace($Raw)) `
        "Baseline non vide"

    try {
        $Json = $Raw | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "[FAIL-CLOSED] JSON invalide : $($_.Exception.Message)"
    }

    CHECK `
        ($null -ne $Json) `
        "Objet JSON chargé"

    PASS "JSON syntaxiquement valide"

    # ==========================================================================
    # 3 — ROOT SCHEMA
    # ==========================================================================

    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host " 3/8 — ROOT SCHEMA"
    Write-Host ("=" * 100)

    $RootExpected = @(
        "project"
        "version"
        "phase"
        "component"
        "certification"
        "backend"
        "artifacts"
        "integrity"
        "provenance"
    )

    CHECK-EXACT-PROPERTIES `
        -Object $Json `
        -Expected $RootExpected `
        -Scope "ROOT"

    $Project = GET-PROPERTY `
        -Object $Json `
        -Name "project" `
        -Description "ROOT.project présent"

    CHECK `
        ([string]$Project -eq "E-ZZIO") `
        "project = E-ZZIO"

    $Version = GET-PROPERTY `
        -Object $Json `
        -Name "version" `
        -Description "ROOT.version présent"

    CHECK `
        ([string]$Version -eq "V7") `
        "version = V7"

    $Phase = GET-PROPERTY `
        -Object $Json `
        -Name "phase" `
        -Description "ROOT.phase présent"

    CHECK `
        ([string]$Phase -eq "4.2-C") `
        "phase = 4.2-C"

    $Component = GET-PROPERTY `
        -Object $Json `
        -Name "component" `
        -Description "ROOT.component présent"

    CHECK `
        ([string]$Component -eq "Real Local STT Provider") `
        "component = Real Local STT Provider"

    # ==========================================================================
    # 4 — CERTIFICATION SCHEMA
    # ==========================================================================

    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host " 4/8 — CERTIFICATION"
    Write-Host ("=" * 100)

    $Certification = GET-PROPERTY `
        -Object $Json `
        -Name "certification" `
        -Description "certification présente"

    CHECK `
        ($null -ne $Certification) `
        "Objet certification valide"

    $CertificationExpected = @(
        "status"
        "score"
        "checks_passed"
        "checks_failed"
        "final_forensic_gate"
    )

    CHECK-EXACT-PROPERTIES `
        -Object $Certification `
        -Expected $CertificationExpected `
        -Scope "CERTIFICATION"

    $Status = GET-PROPERTY `
        -Object $Certification `
        -Name "status" `
        -Description "certification.status présent"

    CHECK `
        ([string]$Status -eq "CERTIFIED") `
        "certification.status = CERTIFIED"

    $Score = GET-PROPERTY `
        -Object $Certification `
        -Name "score" `
        -Description "certification.score présent"

    CHECK `
        ([int]$Score -eq 10) `
        "certification.score = 10"

    $ChecksPassed = GET-PROPERTY `
        -Object $Certification `
        -Name "checks_passed" `
        -Description "certification.checks_passed présent"

    CHECK `
        ([int]$ChecksPassed -eq 13) `
        "certification.checks_passed = 13"

    $ChecksFailed = GET-PROPERTY `
        -Object $Certification `
        -Name "checks_failed" `
        -Description "certification.checks_failed présent"

    CHECK `
        ([int]$ChecksFailed -eq 0) `
        "certification.checks_failed = 0"

    $ForensicGate = GET-PROPERTY `
        -Object $Certification `
        -Name "final_forensic_gate" `
        -Description "certification.final_forensic_gate présent"

    CHECK `
        ([string]$ForensicGate -eq "PASS") `
        "certification.final_forensic_gate = PASS"

    # ==========================================================================
    # 5 — BACKEND SCHEMA
    # ==========================================================================

    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host " 5/8 — BACKEND"
    Write-Host ("=" * 100)

    $Backend = GET-PROPERTY `
        -Object $Json `
        -Name "backend" `
        -Description "backend présent"

    $BackendExpected = @(
        "provider"
        "interface"
        "backend"
        "model_size"
        "device"
        "compute_type"
        "beam_size"
        "call_count"
        "sample_rate"
        "samples"
        "no_mock_fallback"
    )

    CHECK-EXACT-PROPERTIES `
        -Object $Backend `
        -Expected $BackendExpected `
        -Scope "BACKEND"

    CHECK `
        ([string]$Backend.provider -eq "WhisperSttProvider") `
        "backend.provider = WhisperSttProvider"

    CHECK `
        ([string]$Backend.interface -eq "ISttProvider") `
        "backend.interface = ISttProvider"

    CHECK `
        ([string]$Backend.backend -eq "faster-whisper") `
        "backend.backend = faster-whisper"

    CHECK `
        ([string]$Backend.model_size -eq "tiny") `
        "backend.model_size = tiny"

    CHECK `
        ([string]$Backend.device -eq "cpu") `
        "backend.device = cpu"

    CHECK `
        ([string]$Backend.compute_type -eq "int8") `
        "backend.compute_type = int8"

    CHECK `
        ([int]$Backend.beam_size -eq 1) `
        "backend.beam_size = 1"

    CHECK `
        ([int]$Backend.call_count -eq 1) `
        "backend.call_count = 1"

    CHECK `
        ([int]$Backend.sample_rate -eq 16000) `
        "backend.sample_rate = 16000"

    CHECK `
        ([int]$Backend.samples -eq 16000) `
        "backend.samples = 16000"

    CHECK `
        ([bool]$Backend.no_mock_fallback -eq $true) `
        "backend.no_mock_fallback = true"

    # ==========================================================================
    # 6 — ARTIFACTS + REAL SHA256
    # ==========================================================================

    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host " 6/8 — CERTIFIED ARTIFACTS / SHA256"
    Write-Host ("=" * 100)

    $ArtifactsRoot = GET-PROPERTY `
        -Object $Json `
        -Name "artifacts" `
        -Description "artifacts présent"

    $ArtifactNames = @(
        "provider"
        "test"
        "report"
    )

    CHECK-EXACT-PROPERTIES `
        -Object $ArtifactsRoot `
        -Expected $ArtifactNames `
        -Scope "ARTIFACTS"

    $ArtifactRecords = @()

    foreach ($Name in $ArtifactNames) {

        Write-Host ""
        Write-Host "[$($Name.ToUpperInvariant())]" -ForegroundColor Cyan

        $Artifact = $ArtifactsRoot.PSObject.Properties[$Name].Value

        CHECK `
            ($null -ne $Artifact) `
            "$Name : objet présent"

        $ArtifactExpected = @(
            "path"
            "sha256"
        )

        CHECK-EXACT-PROPERTIES `
            -Object $Artifact `
            -Expected $ArtifactExpected `
            -Scope "ARTIFACT.$Name"

        $Path = [string]$Artifact.path
        $ExpectedHash = ([string]$Artifact.sha256).ToUpperInvariant()

        CHECK `
            (-not [string]::IsNullOrWhiteSpace($Path)) `
            "$Name : path non vide"

        CHECK `
            ([System.IO.Path]::IsPathFullyQualified($Path)) `
            "$Name : chemin absolu"

        CHECK `
            ($Path.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)) `
            "$Name : chemin contenu dans E-ZZIO"

        CHECK `
            ($ExpectedHash -match '^[A-F0-9]{64}$') `
            "$Name : SHA256 syntaxiquement valide"

        Write-Host "PATH     : $Path"
        Write-Host "EXPECTED : $ExpectedHash"

        $ActualHash = HASH-FILE -Path $Path

        Write-Host "ACTUAL   : $ActualHash"

        CHECK `
            ($ActualHash -eq $ExpectedHash) `
            "$Name : SHA256 intact"

        $ArtifactRecords += [PSCustomObject]@{
            Name = $Name
            Path = $Path
            Hash = $ActualHash
        }
    }

    $UniquePaths = @(
        $ArtifactRecords |
            Select-Object -ExpandProperty Path -Unique
    )

    CHECK `
        ($UniquePaths.Count -eq $ArtifactRecords.Count) `
        "Aucun artefact ne partage le même chemin"

    # ==========================================================================
    # 7 — INTEGRITY / PROVENANCE
    # ==========================================================================

    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host " 7/8 — INTEGRITY / PROVENANCE"
    Write-Host ("=" * 100)

    $Integrity = GET-PROPERTY `
        -Object $Json `
        -Name "integrity" `
        -Description "integrity présente"

    $IntegrityExpected = @(
        "provider_unchanged_during_final_gate"
        "test_unchanged_during_final_gate"
        "report_unchanged_during_final_gate"
        "drill_writes"
    )

    CHECK-EXACT-PROPERTIES `
        -Object $Integrity `
        -Expected $IntegrityExpected `
        -Scope "INTEGRITY"

    CHECK `
        ([bool]$Integrity.provider_unchanged_during_final_gate -eq $true) `
        "integrity.provider_unchanged_during_final_gate = true"

    CHECK `
        ([bool]$Integrity.test_unchanged_during_final_gate -eq $true) `
        "integrity.test_unchanged_during_final_gate = true"

    CHECK `
        ([bool]$Integrity.report_unchanged_during_final_gate -eq $true) `
        "integrity.report_unchanged_during_final_gate = true"

    CHECK `
        ([int]$Integrity.drill_writes -eq 0) `
        "integrity.drill_writes = 0"

    $Provenance = GET-PROPERTY `
        -Object $Json `
        -Name "provenance" `
        -Description "provenance présente"

    $ProvenanceExpected = @(
        "source"
        "certification_date"
    )

    CHECK-EXACT-PROPERTIES `
        -Object $Provenance `
        -Expected $ProvenanceExpected `
        -Scope "PROVENANCE"

    CHECK `
        (-not [string]::IsNullOrWhiteSpace([string]$Provenance.source)) `
        "provenance.source non vide"

    CHECK `
        ([string]$Provenance.source -eq "E-ZZIO V7 Phase 4.2-C Final Forensic Gate") `
        "provenance.source exact"

    $CertificationDate = [string]$Provenance.certification_date

    CHECK `
        (-not [string]::IsNullOrWhiteSpace($CertificationDate)) `
        "provenance.certification_date non vide"

    $ParsedDate = [datetimeoffset]::MinValue

    CHECK `
        ([datetimeoffset]::TryParse(
            $CertificationDate,
            [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::RoundtripKind,
            [ref]$ParsedDate
        )) `
        "provenance.certification_date ISO valide"

    # ==========================================================================
    # 8 — FINAL GATE
    # ==========================================================================

    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host " 8/8 — FINAL FAIL-CLOSED GATE"
    Write-Host ("=" * 100)

    CHECK `
        ($Fail -eq 0) `
        "Aucun échec"

    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host " E-ZZIO V7 — PHASE 4.2-C — FROZEN BASELINE VERIFIED"
    Write-Host ("=" * 100)
    Write-Host ""

    Write-Host "PASS   : $Pass" -ForegroundColor Green
    Write-Host "FAIL   : $Fail"

    Write-Host ""
    Write-Host "STATUS             : CERTIFIED 10/10" -ForegroundColor Green
    Write-Host "PROVIDER           : UNCHANGED" -ForegroundColor Green
    Write-Host "TEST               : UNCHANGED" -ForegroundColor Green
    Write-Host "REPORT             : UNCHANGED" -ForegroundColor Green
    Write-Host "BASELINE           : UNCHANGED" -ForegroundColor Green
    Write-Host "CRYPTOGRAPHIC GATE : PASS" -ForegroundColor Green
    Write-Host "DRILL WRITES       : 0" -ForegroundColor Green
    Write-Host ""
    Write-Host "PHASE 4.2-C : FROZEN / CRYPTOGRAPHICALLY VERIFIED" -ForegroundColor Green
    Write-Host ""

    exit 0
}
catch {

    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host " E-ZZIO V7 — PHASE 4.2-C — FAIL-CLOSED"
    Write-Host ("=" * 100)
    Write-Host ""

    Write-Host $_.Exception.Message -ForegroundColor Red

    Write-Host ""
    Write-Host "NO CERTIFICATION VERDICT EMITTED." -ForegroundColor Red
    Write-Host "EXIT CODE : 1" -ForegroundColor Red
    Write-Host ""

    exit 1
}
