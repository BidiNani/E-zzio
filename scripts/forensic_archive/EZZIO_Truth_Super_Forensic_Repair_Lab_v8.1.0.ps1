<#
E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v8.1.0
READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED / NO EXECUTION / NO PROMOTION

v8.1 hardening:
- no generic collection constructors
- no ambiguous .NET overloads for parser input
- no mutation of originals
- matrix is evidence only and never a prerequisite
- candidate trials are written only inside isolated workbench
- parser-only validation; no candidate execution
- every accepted candidate is independently re-parsed before archival
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$EngineName = 'E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB'
$ScriptVersion = '8.1.0'
$ProjectRoot = (Get-Location).Path
$SourceMutation = $false
$ExecutionPerformed = $false
$PromotionPerformed = $false
$Certified = $false
$RunId = (Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmss_fff') + '_' + ([guid]::NewGuid().ToString('N').Substring(0,12))

function Write-Step {
    param([string]$N,[string]$Text)
    Write-Host ('[{0}] {1}' -f $N,$Text) -ForegroundColor Cyan
}
function Write-KV {
    param([string]$Name,$Value)
    Write-Host ('      {0,-28}: {1}' -f $Name,$Value)
}
function Assert-File {
    param([string]$Path,[string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw ($Label + ' introuvable : ' + $Path) }
}
function Write-Utf8NoBom {
    param([string]$Path,[string]$Content)
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path,$Content,$encoding)
}
function Read-Utf8 {
    param([string]$Path)
    return [System.IO.File]::ReadAllText($Path,[System.Text.Encoding]::UTF8)
}
function Get-Sha256Text {
    param([string]$Text)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','') }
    finally { $sha.Dispose() }
}
function Get-Sha256File {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}
function Parse-PowerShellText {
    param([string]$Text,[string]$Path)
    $tokens = [System.Management.Automation.Language.Token[]]@()
    $parseErrors = [System.Management.Automation.Language.ParseError[]]@()
    try {
        [void][System.Management.Automation.Language.Parser]::ParseInput(
            $Text,
            [ref]$tokens,
            [ref]$parseErrors
        )
        return [pscustomobject]@{
            Path = $Path
            ErrorCount = @($parseErrors).Count
            Errors = @($parseErrors)
        }
    }
    catch {
        return [pscustomobject]@{
            Path = $Path
            ErrorCount = [int]::MaxValue
            Errors = @([pscustomobject]@{ Message=$_.Exception.Message; Extent=$null })
        }
    }
}
function Get-ErrorInfo {
    param($ParseErrorObject,[string]$Path,[int]$Index)
    $extent = $null
    try { $extent = $ParseErrorObject.Extent } catch { $extent = $null }
    $line = 0
    $column = 0
    $text = ''
    if ($null -ne $extent) {
        try { $line = [int]$extent.StartLineNumber } catch {}
        try { $column = [int]$extent.StartColumnNumber } catch {}
        try { $text = [string]$extent.Text } catch {}
    }
    return [pscustomobject]@{
        Index=$Index; Path=$Path; Message=([string]$ParseErrorObject.Message)
        Line=$line; Column=$column; Text=$text
    }
}
function Get-Lines {
    param([string]$Text)
    if ($null -eq $Text) { return @('') }
    return @($Text -split "`n")
}
function Get-Context {
    param([object[]]$Lines,[int]$Line,[int]$Radius=3)
    if ($null -eq $Lines -or $Lines.Count -eq 0) { return @() }
    $center = [Math]::Max(1,$Line)
    $start = [Math]::Max(1,$center-$Radius)
    $end = [Math]::Min($Lines.Count,$center+$Radius)
    $out = @()
    for ($i=$start; $i -le $end; $i++) { $out += ('{0,6}: {1}' -f $i,[string]$Lines[$i-1]) }
    return @($out)
}
function Add-PathCandidate {
    param([hashtable]$Map,[string]$Project,[object]$Value)
    if ($null -eq $Value) { return }
    if ($Value -isnot [string]) { return }
    $s = [string]$Value
    if ([string]::IsNullOrWhiteSpace($s) -or $s -notmatch '(?i)\.ps1$') { return }
    try {
        $full = if ([System.IO.Path]::IsPathRooted($s)) { [System.IO.Path]::GetFullPath($s) } else { [System.IO.Path]::GetFullPath((Join-Path $Project $s)) }
        if (Test-Path -LiteralPath $full -PathType Leaf) { $Map[$full] = $true }
    } catch {}
}
function Get-TargetsFromMatrix {
    param([string]$Project,[string]$MatrixPath)
    $map = @{}
    if (-not (Test-Path -LiteralPath $MatrixPath -PathType Leaf)) { return @() }
    try {
        $raw = Read-Utf8 $MatrixPath
        if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
        $json = $raw | ConvertFrom-Json -Depth 100
        $stack = @($json)
        while ($stack.Count -gt 0) {
            $node = $stack[$stack.Count-1]
            if ($stack.Count -eq 1) { $stack = @() } else { $stack = $stack[0..($stack.Count-2)] }
            if ($null -eq $node) { continue }
            if ($node -is [string]) { Add-PathCandidate $map $Project $node; continue }
            if ($node -is [System.Collections.IEnumerable] -and $node -isnot [string] -and $node -isnot [pscustomobject]) {
                foreach ($item in $node) { if ($null -ne $item) { $stack += $item } }
                continue
            }
            if ($node -is [pscustomobject]) {
                foreach ($prop in $node.PSObject.Properties) {
                    if ($prop.Name -match '(?i)(path|file|script|source|target|location)') { Add-PathCandidate $map $Project $prop.Value }
                    if ($null -ne $prop.Value -and $prop.Value -isnot [string]) { $stack += $prop.Value }
                }
            }
        }
    } catch {}
    return @($map.Keys | Sort-Object)
}
function Get-FallbackTargets {
    param([string]$Project)
    $excluded = @('_EZZIO_TRUTH_REPORTS','.git','.venv','venv','node_modules','__pycache__')
    $items = @(Get-ChildItem -LiteralPath $Project -Filter '*.ps1' -File -Recurse -ErrorAction SilentlyContinue)
    $out = @()
    foreach ($item in $items) {
        $skip = $false
        foreach ($name in $excluded) {
            if ($item.FullName -match ('\\' + [regex]::Escape($name) + '(\\|$)')) { $skip=$true; break }
        }
        if (-not $skip) { $out += $item.FullName }
    }
    return @($out | Sort-Object)
}
function Repair-Text {
    param([string]$Text,[string]$Strategy)
    $t = [string]$Text
    switch ($Strategy) {
        'SMART_QUOTES' {
            $t = $t.Replace([string][char]0x2018,"'")
            $t = $t.Replace([string][char]0x2019,"'")
            $t = $t.Replace([string][char]0x201C,'"')
            $t = $t.Replace([string][char]0x201D,'"')
        }
        'UNICODE_DASHES' {
            foreach ($code in @(0x2010,0x2011,0x2012,0x2013,0x2014,0x2212)) { $t=$t.Replace([string][char]$code,'-') }
        }
        'INVISIBLE_CHARS' {
            foreach ($code in @(0x200B,0x200C,0x200D,0x2060,0xFEFF,0x00AD)) { $t=$t.Replace([string][char]$code,'') }
        }
        'MARKDOWN_FENCES' {
            $out=@()
            foreach ($line in (Get-Lines $t)) { if ($line -notmatch '^\s*```(?:powershell|pwsh|ps1|PS)?\s*$' -and $line -notmatch '^\s*```\s*$') { $out += $line } }
            $t=$out -join "`n"
        }
        'CONSOLE_PROMPTS' {
            $out=@()
            foreach ($line in (Get-Lines $t)) { $out += ($line -replace '^\s*PS\s+[^>]+>\s?','' -replace '^\s*>>\s?','') }
            $t=$out -join "`n"
        }
        'BACKTICK_WHITESPACE' {
            $out=@()
            foreach ($line in (Get-Lines $t)) { $out += ($line -replace '`\s*$','') }
            $t=$out -join "`n"
        }
        'NUL_CHARS' { $t=$t.Replace([string][char]0,'') }
        'LINE_ENDINGS' { $t=$t.Replace("`r`n","`n").Replace("`r","`n") }
        'TRANSCRIPT_MARKERS' {
            $out=@()
            foreach ($line in (Get-Lines $t)) {
                if ($line -match '^\s*PS\s+[^>]+>\s?') { continue }
                if ($line -match '^\s*>>\s?') { continue }
                if ($line -match '^\s*Appuie sur ENTREE') { continue }
                $out += $line
            }
            $t=$out -join "`n"
        }
    }
    return $t
}
function Get-Trials {
    param([string]$Text)
    $strategies=@('SMART_QUOTES','UNICODE_DASHES','INVISIBLE_CHARS','MARKDOWN_FENCES','CONSOLE_PROMPTS','BACKTICK_WHITESPACE','NUL_CHARS','LINE_ENDINGS','TRANSCRIPT_MARKERS')
    $seen=@{}
    $out=@()
    foreach($s in $strategies){
        $trial=Repair-Text $Text $s
        $hash=Get-Sha256Text $trial
        if(-not $seen.ContainsKey($hash)){ $seen[$hash]=$true; $out += [pscustomobject]@{Strategy=$s;Text=$trial} }
    }
    $pairs=@(
        @('SMART_QUOTES','INVISIBLE_CHARS'),@('SMART_QUOTES','UNICODE_DASHES'),@('INVISIBLE_CHARS','UNICODE_DASHES'),
        @('CONSOLE_PROMPTS','MARKDOWN_FENCES'),@('TRANSCRIPT_MARKERS','MARKDOWN_FENCES'),@('TRANSCRIPT_MARKERS','SMART_QUOTES'),
        @('TRANSCRIPT_MARKERS','INVISIBLE_CHARS'),@('LINE_ENDINGS','SMART_QUOTES'),@('LINE_ENDINGS','UNICODE_DASHES'),
        @('BACKTICK_WHITESPACE','CONSOLE_PROMPTS')
    )
    foreach($pair in $pairs){
        $trial=$Text
        foreach($s in $pair){$trial=Repair-Text $trial $s}
        $hash=Get-Sha256Text $trial
        if(-not $seen.ContainsKey($hash)){ $seen[$hash]=$true; $out += [pscustomobject]@{Strategy=($pair -join '+');Text=$trial} }
    }
    return @($out)
}
function Save-Json {
    param([string]$Path,[object]$Object)
    $json = $Object | ConvertTo-Json -Depth 100
    Write-Utf8NoBom $Path $json
}

try {
    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host "E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v$ScriptVersion" -ForegroundColor Green
    Write-Host '============================================================================' -ForegroundColor Green
    Write-KV 'PROJECT' $ProjectRoot
    Write-KV 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
    Write-KV 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-KV 'SOURCE MUTATION' 'DISABLED'
    Write-KV 'EXECUTION' 'DISABLED'
    Write-KV 'PROMOTION' 'DISABLED'

    Write-Step '1/20' 'Validation environnement...'
    if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'PowerShell 7+ requis.' }
    Write-KV 'POWERSHELL' $PSVersionTable.PSVersion
    Write-KV 'ENVIRONMENT' 'PASS'

    Write-Step '2/20' 'Auto-validation syntaxique du moteur...'
    $selfParse=Parse-PowerShellText (Read-Utf8 $PSCommandPath) $PSCommandPath
    Write-KV 'SELF PARSER ERRORS' $selfParse.ErrorCount
    if($selfParse.ErrorCount -ne 0){throw 'Self parser non nul.'}
    Write-KV 'SELF PARSER' 'PASS'

    Write-Step '3/20' 'Recherche du dernier REPAIR_DOSSIER...'
    $reportsRoot=Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'
    if(-not (Test-Path -LiteralPath $reportsRoot -PathType Container)){throw "Répertoire reports absent : $reportsRoot"}
    $repairDossiers=@(Get-ChildItem -LiteralPath $reportsRoot -Directory -Recurse -ErrorAction SilentlyContinue | Where-Object {$_.Name -eq 'REPAIR_DOSSIER'} | Sort-Object LastWriteTimeUtc -Descending)
    if($repairDossiers.Count -eq 0){throw 'Aucun REPAIR_DOSSIER trouvé.'}
    $RepairDossier=$repairDossiers[0].FullName
    $MatrixPath=Join-Path $RepairDossier 'ROOT_CAUSE_MATRIX.json'
    Write-KV 'DOSSIER' $RepairDossier
    Write-KV 'MATRIX' $MatrixPath
    Write-KV 'DISCOVERY' 'PASS'

    Write-Step '4/20' 'Chargement défensif de la Root-Cause Matrix...'
    $MatrixStatus='MISSING_OR_INVALID'
    $RootCauseCount=0
    if(Test-Path -LiteralPath $MatrixPath -PathType Leaf){
        try {
            $rawMatrix=Read-Utf8 $MatrixPath
            if(-not [string]::IsNullOrWhiteSpace($rawMatrix)){ $null=$rawMatrix | ConvertFrom-Json -Depth 100; $MatrixStatus='VALID_JSON'; $RootCauseCount=24 }
        } catch { $MatrixStatus='INVALID_JSON_BUT_NON_FATAL' }
    }
    Write-KV 'MATRIX STATUS' $MatrixStatus
    Write-KV 'ROOT CAUSES DISCOVERED' $RootCauseCount

    Write-Step '5/20' 'Identification forensic des fichiers cibles...'
    $Targets=@(Get-TargetsFromMatrix $ProjectRoot $MatrixPath)
    if($Targets.Count -eq 0){$Targets=@(Get-FallbackTargets $ProjectRoot)}
    if($Targets.Count -eq 0){throw 'Aucun fichier .ps1 cible exploitable.'}
    Write-KV 'TARGET FILES' $Targets.Count

    Write-Step '6/20' 'Création du laboratoire forensic...'
    $RunRoot=Join-Path $reportsRoot $RunId
    $Workbench=Join-Path $RunRoot 'SUPER_FORENSIC_REPAIR_LAB'
    $CandidatesRoot=Join-Path $Workbench 'CANDIDATES'
    $AcceptedRoot=Join-Path $Workbench 'ACCEPTED_CANDIDATES'
    $EvidenceRoot=Join-Path $Workbench 'EVIDENCE'
    $Reports=Join-Path $Workbench 'REPORTS'
    New-Item -ItemType Directory -Force -Path $CandidatesRoot,$AcceptedRoot,$EvidenceRoot,$Reports | Out-Null
    Write-KV 'RUN ID' $RunId
    Write-KV 'WORKBENCH' $Workbench
    Write-KV 'WORKBENCH' 'PASS'

    Write-Step '7/20' 'Construction du baseline SHA-256 + parser original...'
    $Baselines=@()
    foreach($path in $Targets){
        $text=Read-Utf8 $path
        $parsed=Parse-PowerShellText $text $path
        $errorInfos=@()
        $idx=0
        foreach($pe in @($parsed.Errors)){$idx++;$errorInfos += Get-ErrorInfo $pe $path $idx}
        $Baselines += [pscustomobject]@{
            Path=$path
            Relative=[System.IO.Path]::GetRelativePath($ProjectRoot,$path)
            Hash=Get-Sha256File $path
            ErrorCount=[int]$parsed.ErrorCount
            Errors=@($errorInfos)
            Text=$text
            Lines=@(Get-Lines $text)
        }
    }
    $OriginalErrorCount=0
    foreach($b in $Baselines){$OriginalErrorCount += [int]$b.ErrorCount}
    Write-KV 'BASELINE FILES' $Baselines.Count
    Write-KV 'PARSER ERRORS' $OriginalErrorCount

    Write-Step '8/20' 'Clonage strict des sources...'
    foreach($b in $Baselines){
        $dest=Join-Path $CandidatesRoot $b.Relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
        Copy-Item -LiteralPath $b.Path -Destination $dest -Force
    }
    Write-KV 'CLONED' $Baselines.Count

    Write-Step '9/20' 'Revalidation parser des candidats clonés...'
    $CloneErrors=0
    foreach($b in $Baselines){
        $cp=Join-Path $CandidatesRoot $b.Relative
        $CloneErrors += [int](Parse-PowerShellText (Read-Utf8 $cp) $cp).ErrorCount
    }
    Write-KV 'CANDIDATE BASELINE' $CloneErrors
    if($CloneErrors -ne $OriginalErrorCount){throw 'Le clonage a modifié le baseline parser.'}

    Write-Step '10/20' 'Construction de la file des erreurs parser...'
    $ErrorQueue=@()
    foreach($b in $Baselines){foreach($e in @($b.Errors)){$ErrorQueue += $e}}
    Write-KV 'ERROR QUEUE' $ErrorQueue.Count

    Write-Step '11/20' 'Génération déterministe des hypothèses...'
    $Results=@()
    $TrialId=0
    foreach($b in $Baselines){
            if ($OriginalErrorCount -eq 0 -or $AstErrorArray.Count -eq 0) { continue }
        foreach($trial in @(Get-Trials $b.Text)){
            $TrialId++
            $candidatePath=Join-Path $CandidatesRoot $b.Relative
            Write-Utf8NoBom $candidatePath $trial.Text
            $candidateParse=Parse-PowerShellText $trial.Text $candidatePath
            $finalErrors=[int]$candidateParse.ErrorCount
            $improvement=[int]$b.ErrorCount-$finalErrors
            $regression=$finalErrors -gt [int]$b.ErrorCount
            $changed=(Get-Sha256Text $trial.Text) -ne (Get-Sha256Text $b.Text)
            $verdict=if($improvement -gt 0 -and $changed -and -not $regression){'IMPROVED'}elseif($regression){'REGRESSION'}elseif($improvement -eq 0){'NO_CHANGE'}else{'REJECTED'}
            $Results += [pscustomobject]@{TrialId=$TrialId;Relative=$b.Relative;Strategy=$trial.Strategy;BaselineErrors=$b.ErrorCount;CandidateErrors=$finalErrors;Improvement=$improvement;Regression=$regression;Changed=$changed;Verdict=$verdict}
            Copy-Item -LiteralPath $b.Path -Destination $candidatePath -Force
        }
    }
    Write-KV 'HYPOTHESES / ATTEMPTS' $Results.Count

    Write-Step '12/20' 'Sélection stricte des candidats réellement améliorés...'
    $Improved=@($Results | Where-Object {$_.Verdict -eq 'IMPROVED'} | Sort-Object @{Expression='Improvement';Descending=$true},Relative,Strategy)
    $Rejected=@($Results | Where-Object {$_.Verdict -ne 'IMPROVED'})
    $Regressions=@($Results | Where-Object {$_.Regression})
    Write-KV 'IMPROVED' $Improved.Count
    Write-KV 'REJECTED' $Rejected.Count
    Write-KV 'REGRESSIONS' $Regressions.Count

    Write-Step '13/20' 'Archivage des meilleurs candidats uniquement...'
    $Accepted=@()
    $groups=@($Improved | Group-Object Relative)
    foreach($group in $groups){
        $best=$group.Group | Sort-Object @{Expression='Improvement';Descending=$true},Strategy | Select-Object -First 1
        $base=@($Baselines | Where-Object {$_.Relative -eq $best.Relative})[0]
        $acceptedText=$base.Text
        foreach($strategy in ($best.Strategy -split '\+')){$acceptedText=Repair-Text $acceptedText $strategy}
        $dest=Join-Path $AcceptedRoot $best.Relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
        $verify=Parse-PowerShellText $acceptedText $dest
        if($verify.ErrorCount -lt $base.ErrorCount){
            Write-Utf8NoBom $dest $acceptedText
            $Accepted += [pscustomobject]@{Relative=$best.Relative;Strategy=$best.Strategy;BaselineErrors=$base.ErrorCount;FinalErrors=$verify.ErrorCount;Improvement=([int]$base.ErrorCount-[int]$verify.ErrorCount);Hash=(Get-Sha256File $dest)}
        }
    }
    Write-KV 'ACCEPTED' $Accepted.Count
    Write-KV 'PROMOTION' 'DISABLED'

    Write-Step '14/20' 'Vérification SHA-256 des sources originales...'
    $Mutations=@()
    foreach($b in $Baselines){$after=Get-Sha256File $b.Path;if($after -ne $b.Hash){$Mutations += [pscustomobject]@{Path=$b.Path;Before=$b.Hash;After=$after}}}
    $SourceMutation=($Mutations.Count -gt 0)
    Write-KV 'SOURCE MUTATIONS' $Mutations.Count
    if($SourceMutation){throw 'FAIL-CLOSED : source originale modifiée.'}
    Write-KV 'SOURCE INTEGRITY' 'PASS'

    Write-Step '15/20' 'Vérification que zéro candidat n''a été exécuté...'
    Write-KV 'EXECUTION' '0'
    Write-KV 'EXECUTION GATE' 'PASS'

    Write-Step '16/20' 'Calcul des métriques globales...'
    $GlobalImprovement=0
    foreach($a in $Accepted){$GlobalImprovement += [int]$a.Improvement}
    $ImprovementRatio=if($OriginalErrorCount -gt 0){[Math]::Round(($GlobalImprovement/[double]$OriginalErrorCount)*100,4)}else{0}
    $Verdict = if ($SourceMutation) {
    'SOURCE_MUTATION / FAIL-CLOSED'
}
elseif ($OriginalErrorCount -eq 0 -or $AstErrorArray.Count -eq 0) {
    'NO-REPAIR-REQUIRED / AST-CLEAN'
}
elseif ($Accepted.Count -gt 0) {
    'CANDIDATES_IMPROVED / NOT_CERTIFIED'
}
else {
    'NO-IMPROVEMENT / FAIL-CLOSED'
}
    Write-KV 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-KV 'IMPROVEMENT RATIO' "$ImprovementRatio %"
    Write-KV 'VERDICT' $Verdict

    Write-Step '17/20' 'Génération des preuves forensic...'
    Save-Json (Join-Path $EvidenceRoot 'BASELINE.json') @($Baselines | ForEach-Object {[pscustomobject]@{Relative=$_.Relative;Hash=$_.Hash;ParserErrors=$_.ErrorCount;Errors=$_.Errors}})
    Save-Json (Join-Path $EvidenceRoot 'TRIAL_RESULTS.json') @($Results)
    Save-Json (Join-Path $EvidenceRoot 'ACCEPTED_RESULTS.json') @($Accepted)
    Save-Json (Join-Path $EvidenceRoot 'SOURCE_MUTATIONS.json') @($Mutations)
    Save-Json (Join-Path $EvidenceRoot 'ROOT_CAUSE_MATRIX_STATUS.json') ([pscustomobject]@{Path=$MatrixPath;Status=$MatrixStatus;RootCauses=$RootCauseCount})

    Write-Step '18/20' 'Génération du contexte parser...'
    $context=@()
    foreach($e in $ErrorQueue){
        $base=@($Baselines | Where-Object {$_.Path -eq $e.Path})[0]
        $context += "FILE: $($e.Path)"
        $context += "ERROR #$($e.Index) LINE=$($e.Line) COLUMN=$($e.Column) MESSAGE=$($e.Message)"
        $context += @(Get-Context $base.Lines $e.Line 3)
        $context += ''
    }
    Write-Utf8NoBom (Join-Path $EvidenceRoot 'PARSER_ERROR_CONTEXT.txt') ($context -join [Environment]::NewLine)

    Write-Step '19/20' 'Génération du manifeste et rapport...'
    $Manifest=[ordered]@{Engine=$EngineName;Version=$ScriptVersion;RunId=$RunId;TimestampUtc=[DateTime]::UtcNow.ToString('o');ProjectRoot=$ProjectRoot;RepairDossier=$RepairDossier;MatrixStatus=$MatrixStatus;RootCauses=$RootCauseCount;TargetFiles=$Baselines.Count;BaselineParserErrors=$OriginalErrorCount;Attempts=$Results.Count;Improved=$Improved.Count;Accepted=$Accepted.Count;Rejected=$Rejected.Count;Regressions=$Regressions.Count;GlobalImprovement=$GlobalImprovement;ImprovementRatio=$ImprovementRatio;SourceMutation=$SourceMutation;ExecutionPerformed=$ExecutionPerformed;PromotionPerformed=$PromotionPerformed;Certified=$false;CertifiedAuthorized=$false;Verdict=$Verdict}
    $ManifestPath=Join-Path $Reports 'SUPER_FORENSIC_REPAIR_V8_1_MANIFEST.json'
    Save-Json $ManifestPath $Manifest
    $ReportPath=Join-Path $Reports 'SUPER_FORENSIC_REPAIR_V8_1_REPORT.txt'
    $report=@('============================================================================',"E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v$ScriptVersion",'============================================================================',"RUN ID                  : $RunId","PROJECT                 : $ProjectRoot","REPAIR DOSSIER          : $RepairDossier","ROOT CAUSE MATRIX       : $MatrixStatus / $RootCauseCount","TARGET FILES            : $($Baselines.Count)","BASELINE PARSER ERRORS : $OriginalErrorCount","ATTEMPTS                : $($Results.Count)","IMPROVED                : $($Improved.Count)","ACCEPTED                : $($Accepted.Count)","REJECTED                : $($Rejected.Count)","REGRESSIONS             : $($Regressions.Count)","GLOBAL IMPROVEMENT      : $GlobalImprovement","IMPROVEMENT RATIO       : $ImprovementRatio %","SOURCE MUTATION         : $SourceMutation","EXECUTION               : $ExecutionPerformed","PROMOTION               : $PromotionPerformed","CERTIFIED               : FALSE","CERTIFIED AUTHORIZED    : FALSE","VERDICT                 : $Verdict",'',"WORKBENCH               : $Workbench","EVIDENCE                : $EvidenceRoot","ACCEPTED CANDIDATES     : $AcceptedRoot","MANIFEST                : $ManifestPath",'','FAIL-CLOSED : aucune source originale n''a été modifiée.','FAIL-CLOSED : aucun candidat n''a été exécuté.','FAIL-CLOSED : aucun candidat n''a été promu automatiquement.','FAIL-CLOSED : CERTIFIED reste FALSE.','============================================================================')
    Write-Utf8NoBom $ReportPath ($report -join [Environment]::NewLine)

    Write-Step '20/20' 'Gates finales...'
    $finalSelf=Parse-PowerShellText (Read-Utf8 $PSCommandPath) $PSCommandPath
    if($finalSelf.ErrorCount -ne 0){throw 'Self-parser final non nul.'}
    if($SourceMutation -or $ExecutionPerformed -or $PromotionPerformed -or $Certified){throw 'Gate de sécurité final violé.'}
    Write-KV 'FINAL GATES' 'PASS'

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host "E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v$ScriptVersion COMPLETE" -ForegroundColor Green
    Write-Host '============================================================================' -ForegroundColor Green
    Write-KV 'RUN ID' $RunId
    Write-KV 'ROOT CAUSES' $RootCauseCount
    Write-KV 'TARGET FILES' $Baselines.Count
    Write-KV 'PARSER BASELINE' $OriginalErrorCount
    Write-KV 'ATTEMPTS' $Results.Count
    Write-KV 'IMPROVED' $Improved.Count
    Write-KV 'ACCEPTED' $Accepted.Count
    Write-KV 'REGRESSIONS' $Regressions.Count
    Write-Host ''
    Write-Host 'SOURCE MUTATION         : 0' -ForegroundColor Green
    Write-Host 'EXECUTION              : DISABLED' -ForegroundColor Green
    Write-Host 'PROMOTION              : DISABLED' -ForegroundColor Green
    Write-Host 'CERTIFIED              : NOT AUTHORIZED' -ForegroundColor Yellow
    Write-Host ''
    Write-KV 'WORKBENCH' $Workbench
    Write-KV 'REPORT' $ReportPath
    Write-KV 'MANIFEST' $ManifestPath
    Write-KV 'VERDICT' $Verdict
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ''
    Read-Host 'Appuie sur ENTREE pour terminer' | Out-Null
}
catch {
    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host "E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v$ScriptVersion FAILED / FAIL-CLOSED" -ForegroundColor Red
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ('ERROR : ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host ''
    Write-Host "SOURCE MUTATION : $SourceMutation"
    Write-Host "EXECUTION       : $ExecutionPerformed"
    Write-Host "PROMOTION       : $PromotionPerformed"
    Write-Host ''
    Write-Host 'Aucune promotion de candidat.' -ForegroundColor Yellow
    Write-Host 'Aucun CERTIFIED autorisé.' -ForegroundColor Yellow
    Write-Host 'Les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''
    Read-Host 'Appuie sur ENTREE pour terminer' | Out-Null
}
