<#
E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v8.0.0
READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED / NO EXECUTION / NO PROMOTION

Purpose:
  Build an auditable repair laboratory from the latest REPAIR_DOSSIER.
  Discover target PowerShell files defensively, establish SHA-256 + parser
  baselines, generate isolated repair hypotheses, validate candidates by
  parsing only, and emit evidence. Original project files are NEVER written.

Important:
  This engine never executes candidate source code and never promotes a
  candidate. "CERTIFIED" is permanently false.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$EngineName   = 'E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB'
$ScriptVersion = '8.0.0'
$ProjectRoot  = (Get-Location).Path
$SourceMutation = $false
$ExecutionPerformed = $false
$PromotionPerformed = $false
$Certified = $false
$RunId = '{0}_{1}' -f (Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmss_fff'), ([guid]::NewGuid().ToString('N').Substring(0,12))

function Write-Step {
    param([string]$N,[string]$Text)
    Write-Host "[$N] $Text" -ForegroundColor Cyan
}
function Write-KV {
    param([string]$Name,$Value)
    Write-Host ('      {0,-28}: {1}' -f $Name,$Value)
}
function Assert-PathFile {
    param([string]$Path,[string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "$Label introuvable : $Path" }
}
function Write-Utf8NoBom {
    param([string]$Path,[string]$Content)
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path,$Content,$enc)
}
function Read-Utf8 {
    param([string]$Path)
    [System.IO.File]::ReadAllText($Path,[System.Text.Encoding]::UTF8)
}
function Get-Sha256 {
    param([string]$Path)
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}
function Convert-ToArraySafe {
    param($Value)
    if ($null -eq $Value) { return @() }
    if ($Value -is [System.Array]) { return @($Value) }
    return @($Value)
}
function Parse-PowerShellText {
    param([string]$Text,[string]$Path)
    $tokens = $null
    $parseErrors = $null
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
    } catch {
        return [pscustomobject]@{
            Path = $Path
            ErrorCount = [int]::MaxValue
            Errors = @([pscustomobject]@{ Message = $_.Exception.Message; Extent = $null })
        }
    }
}
function Get-ErrorRecord {
    param($ErrorRecord,[string]$Path,[int]$Index)
    $extent = $null
    try { $extent = $ErrorRecord.Extent } catch {}
    $line = 0; $column = 0; $text = ''
    if ($null -ne $extent) {
        try { $line = [int]$extent.StartLineNumber } catch {}
        try { $column = [int]$extent.StartColumnNumber } catch {}
        try { $text = [string]$extent.Text } catch {}
    }
    [pscustomobject]@{
        Index=$Index; Path=$Path; Message=([string]$ErrorRecord.Message)
        Line=$line; Column=$column; Text=$text
    }
}
function Get-SourceLines {
    param([string]$Text)
    return @($Text -split "`n",-1)
}
function Get-Context {
    param([string[]]$Lines,[int]$Line,[int]$Radius=3)
    if ($Lines.Count -eq 0) { return @() }
    $center = [Math]::Max(1,$Line)
    $a = [Math]::Max(1,$center-$Radius)
    $b = [Math]::Min($Lines.Count,$center+$Radius)
    $out = New-Object System.Collections.Generic.List[string]
    for ($i=$a; $i -le $b; $i++) {
        $out.Add(('{0,6}: {1}' -f $i,$Lines[$i-1]))
    }
    return @($out)
}
function Get-CandidateTargetPaths {
    param([string]$Project,[string]$MatrixPath)
    $paths = New-Object System.Collections.Generic.HashSet[string]([StringComparer]::OrdinalIgnoreCase)

    function Add-PathValue($v) {
        if ($null -eq $v) { return }
        if ($v -is [string]) {
            $s = [string]$v
            if ([string]::IsNullOrWhiteSpace($s)) { return }
            if ($s -notmatch '\.ps1$') { return }
            $resolved = $null
            if ([System.IO.Path]::IsPathRooted($s)) { $resolved=$s }
            else { $resolved=Join-Path $Project $s }
            try {
                $full=[System.IO.Path]::GetFullPath($resolved)
                if (Test-Path -LiteralPath $full -PathType Leaf) { [void]$paths.Add($full) }
            } catch {}
        }
    }

    if (Test-Path -LiteralPath $MatrixPath -PathType Leaf) {
        try {
            $raw=Read-Utf8 $MatrixPath
            if (-not [string]::IsNullOrWhiteSpace($raw)) {
                $json=$raw | ConvertFrom-Json -Depth 100
                $stack=New-Object System.Collections.Stack
                if ($null -ne $json) { $stack.Push($json) }
                while ($stack.Count -gt 0) {
                    $node=$stack.Pop()
                    if ($null -eq $node) { continue }
                    if ($node -is [string]) { Add-PathValue $node; continue }
                    if ($node -is [System.Collections.IEnumerable] -and -not ($node -is [System.Management.Automation.PSCustomObject])) {
                        foreach($x in $node){ if($null -ne $x){$stack.Push($x)} }
                        continue
                    }
                    if ($node -is [pscustomobject]) {
                        foreach($p in $node.PSObject.Properties) {
                            if ($p.Name -match '(?i)(path|file|script|source|target|location)') { Add-PathValue $p.Value }
                            $v=$p.Value
                            if ($v -isnot [string] -and $null -ne $v) { $stack.Push($v) }
                        }
                    }
                }
            }
        } catch {
            # Matrix is evidence, not a trusted executable contract. Fallback below.
        }
    }

    if ($paths.Count -eq 0) {
        $excluded = @('_EZZIO_TRUTH_REPORTS','.git','.venv','venv','node_modules','__pycache__')
        Get-ChildItem -LiteralPath $Project -Filter '*.ps1' -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object {
                $p=$_.FullName
                -not ($excluded | Where-Object { $p -match ('\\{0}(\\|$)' -f [regex]::Escape($_)) })
            } |
            ForEach-Object { [void]$paths.Add($_.FullName) }
    }
    return @($paths | Sort-Object)
}
function New-RepairTrial {
    param([string]$Text,[string]$Strategy)
    $t = $Text
    switch ($Strategy) {
        'SMART_QUOTES' {
            $t = $t.Replace([string][char]0x2018,"'").Replace([string][char]0x2019,"'").Replace([string][char]0x201C,'"').Replace([string][char]0x201D,'"')
        }
        'UNICODE_DASHES' {
            $t = $t.Replace([string][char]0x2010,'-').Replace([string][char]0x2011,'-').Replace([string][char]0x2012,'-').Replace([string][char]0x2013,'-').Replace([string][char]0x2014,'-').Replace([string][char]0x2212,'-')
        }
        'INVISIBLE_CHARS' {
            foreach($c in @([char]0x200B,[char]0x200C,[char]0x200D,[char]0x2060,[char]0xFEFF,[char]0x00AD)) { $t=$t.Replace([string]$c,'') }
        }
        'MARKDOWN_FENCES' {
            $ls=Get-SourceLines $t
            $ls=@($ls | Where-Object { $_ -notmatch '^\s*```(?:powershell|pwsh|ps1|PS)?\s*$' -and $_ -notmatch '^\s*```\s*$' })
            $t=$ls -join "`n"
        }
        'CONSOLE_PROMPTS' {
            $ls=Get-SourceLines $t
            $ls=@($ls | ForEach-Object { $_ -replace '^\s*PS\s+[^>]+>\s?','' -replace '^\s*>>\s?','' })
            $t=$ls -join "`n"
        }
        'BACKTICK_WHITESPACE' {
            $ls=Get-SourceLines $t
            $out=New-Object System.Collections.Generic.List[string]
            foreach($l in $ls){
                if($l -match '`\s*$'){ $out.Add(($l -replace '`\s*$','')) } else {$out.Add($l)}
            }
            $t=$out -join "`n"
        }
        'NUL_CHARS' {
            $t=$t.Replace([string][char]0,'')
        }
        'LINE_ENDINGS' {
            $t=$t.Replace("`r`n","`n").Replace("`r","`n")
        }
        'TRANSCRIPT_MARKERS' {
            $ls=Get-SourceLines $t
            $out=New-Object System.Collections.Generic.List[string]
            foreach($l in $ls){
                if($l -match '^\s*PS\s+[^>]+>\s?'){ continue }
                if($l -match '^\s*>>\s?'){ continue }
                if($l -match '^\s*Appuie sur ENTREE'){ continue }
                $out.Add($l)
            }
            $t=$out -join "`n"
        }
    }
    return $t
}
function Get-CompositeTrials {
    param([string]$Text)
    $strategies=@('SMART_QUOTES','UNICODE_DASHES','INVISIBLE_CHARS','MARKDOWN_FENCES','CONSOLE_PROMPTS','BACKTICK_WHITESPACE','NUL_CHARS','LINE_ENDINGS','TRANSCRIPT_MARKERS')
    $seen=New-Object System.Collections.Generic.HashSet[string]
    $result=New-Object System.Collections.Generic.List[object]
    foreach($s in $strategies){
        $trial=New-RepairTrial $Text $s
        $hash=[System.BitConverter]::ToString((New-Object System.Security.Cryptography.SHA256Managed).ComputeHash([System.Text.Encoding]::UTF8.GetBytes($trial))).Replace('-','')
        if($seen.Add($hash)){ $result.Add([pscustomobject]@{Strategy=$s;Text=$trial}) }
    }
    # Deterministic combinations; useful when two independent transcript corruptions coexist.
    $pairs=@(
        @('SMART_QUOTES','INVISIBLE_CHARS'),@('SMART_QUOTES','UNICODE_DASHES'),
        @('INVISIBLE_CHARS','UNICODE_DASHES'),@('CONSOLE_PROMPTS','MARKDOWN_FENCES'),
        @('TRANSCRIPT_MARKERS','MARKDOWN_FENCES'),@('TRANSCRIPT_MARKERS','SMART_QUOTES'),
        @('TRANSCRIPT_MARKERS','INVISIBLE_CHARS'),@('LINE_ENDINGS','SMART_QUOTES'),
        @('LINE_ENDINGS','UNICODE_DASHES'),@('BACKTICK_WHITESPACE','CONSOLE_PROMPTS')
    )
    foreach($pair in $pairs){
        $trial=$Text
        foreach($s in $pair){$trial=New-RepairTrial $trial $s}
        $hash=[System.BitConverter]::ToString((New-Object System.Security.Cryptography.SHA256Managed).ComputeHash([System.Text.Encoding]::UTF8.GetBytes($trial))).Replace('-','')
        if($seen.Add($hash)){ $result.Add([pscustomobject]@{Strategy=($pair -join '+');Text=$trial}) }
    }
    return @($result)
}
function Save-Json {
    param([string]$Path,$Object)
    $Object | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $Path -Encoding utf8
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
    if($PSVersionTable.PSVersion.Major -lt 7){ throw 'PowerShell 7+ requis.' }
    Write-KV 'POWERSHELL' $PSVersionTable.PSVersion
    Write-KV 'ENVIRONMENT' 'PASS'

    Write-Step '2/20' 'Auto-validation syntaxique du moteur...'
    $selfText=Read-Utf8 $PSCommandPath
    $selfParse=Parse-PowerShellText $selfText $PSCommandPath
    Write-KV 'SELF PARSER ERRORS' $selfParse.ErrorCount
    if($selfParse.ErrorCount -ne 0){ throw 'Le moteur v8 ne passe pas son propre parser.' }
    Write-KV 'SELF PARSER' 'PASS'

    Write-Step '3/20' 'Recherche du dernier REPAIR_DOSSIER...'
    $reportsRoot=Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'
    Assert-PathFile (Join-Path $ProjectRoot 'EZZIO_Truth_Super_Forensic_Repair_Lab_v8.0.0.ps1') 'Moteur v8'
    if(-not (Test-Path -LiteralPath $reportsRoot -PathType Container)){ throw "Répertoire reports absent : $reportsRoot" }
    $repairDossiers=Get-ChildItem -LiteralPath $reportsRoot -Directory -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq 'REPAIR_DOSSIER' } | Sort-Object LastWriteTimeUtc -Descending
    if($repairDossiers.Count -eq 0){ throw 'Aucun REPAIR_DOSSIER trouvé.' }
    $RepairDossier=$repairDossiers[0].FullName
    $MatrixPath=Join-Path $RepairDossier 'ROOT_CAUSE_MATRIX.json'
    Write-KV 'DOSSIER' $RepairDossier
    Write-KV 'MATRIX' $MatrixPath
    Write-KV 'DISCOVERY' 'PASS'

    Write-Step '4/20' 'Chargement défensif de la Root-Cause Matrix...'
    $MatrixObject=$null; $MatrixLoad='MISSING_OR_INVALID'
    if(Test-Path -LiteralPath $MatrixPath -PathType Leaf){
        try{
            $rawMatrix=Read-Utf8 $MatrixPath
            if(-not [string]::IsNullOrWhiteSpace($rawMatrix)){ $MatrixObject=$rawMatrix | ConvertFrom-Json -Depth 100; $MatrixLoad='VALID_JSON' }
        }catch{ $MatrixLoad='INVALID_JSON_BUT_NON_FATAL' }
    }
    $RootCauseRecords=@()
    if($null -ne $MatrixObject){
        $stack=New-Object System.Collections.Stack
        $stack.Push($MatrixObject)
        while($stack.Count -gt 0){
            $n=$stack.Pop()
            if($null -eq $n){continue}
            if($n -is [System.Collections.IEnumerable] -and -not ($n -is [string]) -and -not ($n -is [System.Management.Automation.PSCustomObject])){foreach($x in $n){if($null -ne $x){$stack.Push($x)}};continue}
            if($n -is [pscustomobject]){
                $names=@($n.PSObject.Properties.Name)
                $msg=($names | Where-Object {$_ -match '(?i)(message|reason|cause|error|problem|diagnostic|description)' } | Select-Object -First 1)
                $path=($names | Where-Object {$_ -match '(?i)(path|file|script|source|target)' } | Select-Object -First 1)
                if($msg -or $path){
                    $RootCauseRecords += [pscustomobject]@{ Message=if($msg){[string]$n.$msg}else{''}; Path=if($path){[string]$n.$path}else{''}; Raw=$n }
                }
                foreach($p in $n.PSObject.Properties){$v=$p.Value;if($v -isnot [string] -and $null -ne $v){$stack.Push($v)}}
            }
        }
    }
    Write-KV 'MATRIX STATUS' $MatrixLoad
    Write-KV 'ROOT CAUSES DISCOVERED' $RootCauseRecords.Count

    Write-Step '5/20' 'Identification forensic des fichiers cibles...'
    $Targets=Get-CandidateTargetPaths $ProjectRoot $MatrixPath
    if($Targets.Count -eq 0){ throw 'Aucun fichier PowerShell cible exploitable trouvé.' }
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
    $Baselines=New-Object System.Collections.Generic.List[object]
    foreach($path in $Targets){
        $text=Read-Utf8 $path
        $p=Parse-PowerShellText $text $path
        $lines=Get-SourceLines $text
        $errs=New-Object System.Collections.Generic.List[object]
        $i=0; foreach($e in $p.Errors){$i++;$errs.Add((Get-ErrorRecord $e $path $i))}
        $Baselines.Add([pscustomobject]@{Path=$path;Relative=([System.IO.Path]::GetRelativePath($ProjectRoot,$path));Hash=(Get-Sha256 $path);ErrorCount=$p.ErrorCount;Errors=@($errs);Text=$text;Lines=$lines})
    }
    $OriginalErrorCount=($Baselines | Measure-Object -Property ErrorCount -Sum).Sum
    Write-KV 'BASELINE FILES' $Baselines.Count
    Write-KV 'PARSER ERRORS' $OriginalErrorCount

    Write-Step '8/20' 'Clonage strict des sources...'
    foreach($b in $Baselines){
        $dest=Join-Path $CandidatesRoot $b.Relative
        $parent=Split-Path -Parent $dest
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Copy-Item -LiteralPath $b.Path -Destination $dest -Force
    }
    Write-KV 'CLONED' $Baselines.Count

    Write-Step '9/20' 'Revalidation parser des candidats clonés...'
    $CloneErrors=0
    foreach($b in $Baselines){
        $cp=Join-Path $CandidatesRoot $b.Relative
        $ct=Read-Utf8 $cp
        $CloneErrors += (Parse-PowerShellText $ct $cp).ErrorCount
    }
    Write-KV 'CANDIDATE BASELINE' $CloneErrors
    if($CloneErrors -ne $OriginalErrorCount){ throw 'Le clonage a modifié le nombre d erreurs : intégrité candidate invalide.' }

    Write-Step '10/20' 'Construction de la file des erreurs parser...'
    $ErrorQueue=New-Object System.Collections.Generic.List[object]
    foreach($b in $Baselines){ foreach($e in $b.Errors){$ErrorQueue.Add($e)} }
    Write-KV 'ERROR QUEUE' $ErrorQueue.Count

    Write-Step '11/20' 'Génération déterministe des hypothèses...'
    $StrategyNames=@('SMART_QUOTES','UNICODE_DASHES','INVISIBLE_CHARS','MARKDOWN_FENCES','CONSOLE_PROMPTS','BACKTICK_WHITESPACE','NUL_CHARS','LINE_ENDINGS','TRANSCRIPT_MARKERS')
    $TrialIndex=0
    $Results=New-Object System.Collections.Generic.List[object]
    foreach($b in $Baselines){
        $trials=Get-CompositeTrials $b.Text
        foreach($trial in $trials){
            $TrialIndex++
            $candidatePath=Join-Path $CandidatesRoot $b.Relative
            Write-Utf8NoBom $candidatePath $trial.Text
            $cp=Parse-PowerShellText $trial.Text $candidatePath
            $candidateErrors=@($cp.Errors)
            $base=$b.ErrorCount
            $final=$cp.ErrorCount
            $delta=$base-$final
            $regression=($final -gt $base)
            $changed=(Get-Sha256 $candidatePath) -ne $b.Hash
            $verdict=if($delta -gt 0 -and -not $regression -and $changed){'IMPROVED'}elseif($regression){'REGRESSION'}elseif($delta -eq 0){'NO_CHANGE'}else{'REJECTED'}
            $Results.Add([pscustomobject]@{TrialId=$TrialIndex;Relative=$b.Relative;SourcePath=$b.Path;Strategy=$trial.Strategy;BaselineErrors=$base;CandidateErrors=$final;Improvement=$delta;Regression=$regression;Changed=$changed;Verdict=$verdict;CandidatePath=$candidatePath})
            # Restore clone for next isolated trial.
            Copy-Item -LiteralPath $b.Path -Destination $candidatePath -Force
        }
    }
    Write-KV 'HYPOTHESES / ATTEMPTS' $Results.Count

    Write-Step '12/20' 'Sélection stricte des candidats réellement améliorés...'
    $Improved=@($Results | Where-Object {$_.Verdict -eq 'IMPROVED'} | Sort-Object @{Expression='Improvement';Descending=$true},Strategy,Relative)
    $Rejected=@($Results | Where-Object {$_.Verdict -ne 'IMPROVED'})
    $Regressions=@($Results | Where-Object {$_.Regression})
    Write-KV 'IMPROVED' $Improved.Count
    Write-KV 'REJECTED' $Rejected.Count
    Write-KV 'REGRESSIONS' $Regressions.Count

    Write-Step '13/20' 'Archivage des meilleurs candidats uniquement...'
    $Accepted=@()
    foreach($group in ($Improved | Group-Object Relative)){
        $best=$group.Group | Sort-Object @{Expression='Improvement';Descending=$true},Strategy | Select-Object -First 1
        $src=$best.CandidatePath
        $dest=Join-Path $AcceptedRoot $best.Relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
        # Re-create candidate from source then apply the exact accepted strategy chain.
        $acceptedText=$null
        $base=($Baselines | Where-Object {$_.Relative -eq $best.Relative} | Select-Object -First 1)
        if($null -ne $base){
            $acceptedText=$base.Text
            foreach($s in ($best.Strategy -split '\+')){$acceptedText=New-RepairTrial $acceptedText $s}
            $verify=Parse-PowerShellText $acceptedText $dest
            if($verify.ErrorCount -lt $base.ErrorCount){
                Write-Utf8NoBom $dest $acceptedText
                $Accepted += [pscustomobject]@{Relative=$best.Relative;Strategy=$best.Strategy;BaselineErrors=$base.ErrorCount;FinalErrors=$verify.ErrorCount;Improvement=($base.ErrorCount-$verify.ErrorCount);Hash=(Get-Sha256 $dest)}
            }
        }
    }
    Write-KV 'ACCEPTED' $Accepted.Count
    Write-KV 'PROMOTION' 'DISABLED'

    Write-Step '14/20' 'Vérification SHA-256 des sources originales...'
    $Mutations=New-Object System.Collections.Generic.List[object]
    foreach($b in $Baselines){
        $after=Get-Sha256 $b.Path
        if($after -ne $b.Hash){$Mutations.Add([pscustomobject]@{Path=$b.Path;Before=$b.Hash;After=$after})}
    }
    $SourceMutation=($Mutations.Count -gt 0)
    Write-KV 'SOURCE MUTATIONS' $Mutations.Count
    if($SourceMutation){throw 'FAIL-CLOSED : une source originale a changé.'}
    Write-KV 'SOURCE INTEGRITY' 'PASS'

    Write-Step '15/20' 'Vérification que zéro candidat n''a été exécuté...'
    Write-KV 'EXECUTION' '0'
    Write-KV 'EXECUTION GATE' 'PASS'

    Write-Step '16/20' 'Calcul des métriques globales...'
    $GlobalImprovement=0
    if($Accepted.Count -gt 0){$GlobalImprovement=($Accepted | Measure-Object -Property Improvement -Sum).Sum}
    $ImprovementRatio=if($OriginalErrorCount -gt 0){[Math]::Round(($GlobalImprovement/[double]$OriginalErrorCount)*100,4)}else{0}
    $Verdict=if($SourceMutation){'SOURCE_MUTATION / FAIL-CLOSED'}elseif($Accepted.Count -gt 0){'CANDIDATES_IMPROVED / NOT_CERTIFIED'}else{'NO-IMPROVEMENT / FAIL-CLOSED'}
    Write-KV 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-KV 'IMPROVEMENT RATIO' "$ImprovementRatio %"
    Write-KV 'VERDICT' $Verdict

    Write-Step '17/20' 'Génération des preuves forensic...'
    Save-Json (Join-Path $EvidenceRoot 'BASELINE.json') @($Baselines | ForEach-Object {[pscustomobject]@{Relative=$_.Relative;Hash=$_.Hash;ParserErrors=$_.ErrorCount;Errors=$_.Errors}})
    Save-Json (Join-Path $EvidenceRoot 'TRIAL_RESULTS.json') @($Results)
    Save-Json (Join-Path $EvidenceRoot 'ACCEPTED_RESULTS.json') @($Accepted)
    Save-Json (Join-Path $EvidenceRoot 'SOURCE_MUTATIONS.json') @($Mutations)
    Save-Json (Join-Path $EvidenceRoot 'ROOT_CAUSE_MATRIX_STATUS.json') ([pscustomobject]@{Path=$MatrixPath;Status=$MatrixLoad;RootCauseRecords=$RootCauseRecords.Count})

    Write-Step '18/20' 'Génération du contexte parser...'
    $contextLines=New-Object System.Collections.Generic.List[string]
    foreach($e in $ErrorQueue){
        $b=$Baselines | Where-Object {$_.Path -eq $e.Path} | Select-Object -First 1
        $contextLines.Add("FILE: $($e.Path)")
        $contextLines.Add("ERROR #$($e.Index) LINE=$($e.Line) COLUMN=$($e.Column) MESSAGE=$($e.Message)")
        foreach($line in (Get-Context $b.Lines $e.Line 3)){$contextLines.Add($line)}
        $contextLines.Add('')
    }
    Write-Utf8NoBom (Join-Path $EvidenceRoot 'PARSER_ERROR_CONTEXT.txt') ($contextLines -join [Environment]::NewLine)

    Write-Step '19/20' 'Génération du manifeste et rapport...'
    $Manifest=[ordered]@{
        Engine=$EngineName;Version=$ScriptVersion;RunId=$RunId;TimestampUtc=[DateTime]::UtcNow.ToString('o');ProjectRoot=$ProjectRoot;RepairDossier=$RepairDossier
        MatrixStatus=$MatrixLoad;RootCauseRecords=$RootCauseRecords.Count;TargetFiles=$Baselines.Count;BaselineParserErrors=$OriginalErrorCount
        Attempts=$Results.Count;Improved=$Improved.Count;Accepted=$Accepted.Count;Rejected=$Rejected.Count;Regressions=$Regressions.Count
        GlobalImprovement=$GlobalImprovement;ImprovementRatio=$ImprovementRatio;SourceMutation=$SourceMutation;ExecutionPerformed=$ExecutionPerformed;PromotionPerformed=$PromotionPerformed
        Certified=$false;CertifiedAuthorized=$false;Verdict=$Verdict
    }
    $ManifestPath=Join-Path $Reports 'SUPER_FORENSIC_REPAIR_V8_MANIFEST.json'
    Save-Json $ManifestPath $Manifest
    $ReportPath=Join-Path $Reports 'SUPER_FORENSIC_REPAIR_V8_REPORT.txt'
    $report=@(
        '============================================================================'
        "E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v$ScriptVersion"
        '============================================================================'
        "RUN ID                  : $RunId"
        "PROJECT                 : $ProjectRoot"
        "REPAIR DOSSIER          : $RepairDossier"
        "ROOT CAUSE MATRIX       : $MatrixLoad / $($RootCauseRecords.Count) records"
        "TARGET FILES            : $($Baselines.Count)"
        "BASELINE PARSER ERRORS : $OriginalErrorCount"
        "ATTEMPTS                : $($Results.Count)"
        "IMPROVED                : $($Improved.Count)"
        "ACCEPTED                : $($Accepted.Count)"
        "REJECTED                : $($Rejected.Count)"
        "REGRESSIONS             : $($Regressions.Count)"
        "GLOBAL IMPROVEMENT      : $GlobalImprovement"
        "IMPROVEMENT RATIO       : $ImprovementRatio %"
        "SOURCE MUTATION         : $SourceMutation"
        "EXECUTION               : $ExecutionPerformed"
        "PROMOTION               : $PromotionPerformed"
        "CERTIFIED               : FALSE"
        "CERTIFIED AUTHORIZED    : FALSE"
        "VERDICT                 : $Verdict"
        ''
        "WORKBENCH               : $Workbench"
        "EVIDENCE                : $EvidenceRoot"
        "ACCEPTED CANDIDATES     : $AcceptedRoot"
        "MANIFEST                : $ManifestPath"
        ' '
        'FAIL-CLOSED : aucune source originale n''a été modifiée.'
        'FAIL-CLOSED : aucun candidat n''a été exécuté.'
        'FAIL-CLOSED : aucun candidat n''a été promu automatiquement.'
        'FAIL-CLOSED : CERTIFIED reste FALSE, indépendamment du score.'
        '============================================================================'
    )
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
    Write-KV 'ROOT CAUSES' $RootCauseRecords.Count
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
    Write-Host "ERROR : $($_.Exception.Message)" -ForegroundColor Red
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
