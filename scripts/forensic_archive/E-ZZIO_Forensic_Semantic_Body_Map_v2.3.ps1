# ============================================================================
# E-ZZIO — FORENSIC SEMANTIC BODY MAP v2.3
# READ-ONLY / FAIL-CLOSED / NO EXECUTION / NO MUTATION / NO SECRET CONTENT READ
# Optimized Ryzen 9 5900X / NVMe / bounded RunspacePool / batched work
# ============================================================================

& {
    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    $SearchRoot = 'G:\'
    $Phase1Root = 'C:\ProgramData\E-ZZIO\DeepBodyScan'

    $MaxReadBytes      = 4MB
    $ProgressEvery     = 2000
    $FlushEvery        = 1000
    $BatchSize         = 256
    $QueueCapacity     = 24
    $MinProcessedRatio = 0.95
    $IdleSleepMs       = 10

    $LogicalThreads = [Environment]::ProcessorCount
    if ($LogicalThreads -ge 24)      { $WorkerCount = 12 }
    elseif ($LogicalThreads -ge 16)  { $WorkerCount = 8 }
    elseif ($LogicalThreads -ge 8)   { $WorkerCount = 6 }
    else                             { $WorkerCount = 4 }

    $SecretFileNames = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    @(
        '.env','.env.local','.env.production','.env.development',
        'credentials.json','credential.json','secrets.json','secret.json',
        'secrets.yaml','secrets.yml','credentials.yaml','credentials.yml',
        'token.json','tokens.json','service-account.json','service_account.json',
        'id_rsa','id_ed25519','id_ecdsa','id_dsa'
    ) | ForEach-Object { [void]$SecretFileNames.Add($_) }

    $SecretDirectoryNames = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    @(
        '.ssh','secrets','secret','credentials','private','private_keys'
    ) | ForEach-Object { [void]$SecretDirectoryNames.Add($_) }

    $TextExtensions = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    @(
        '.py','.pyw','.ps1','.psm1','.psd1',
        '.js','.jsx','.mjs','.cjs','.ts','.tsx',
        '.json','.jsonl','.yaml','.yml','.toml',
        '.ini','.cfg','.conf','.txt','.md','.rst',
        '.xml','.html','.htm','.css','.scss',
        '.sql','.sh','.bat','.cmd','.env.example'
    ) | ForEach-Object { [void]$TextExtensions.Add($_) }

    $DiscordMarkers = @(
        'discord.py','discord.js','discord.ext','commands.Bot','discord.Client',
        'Client(','bot.run(','slash_command','tree.command','on_ready','on_message')
    $EzzioMarkers = @('E-ZZIO','Ezzio','EZZIO','runtime.model_router','model_router')
    $AiRuntimeMarkers = @('ollama','livekit','pipecat')
    $TestMarkers = @('pytest','unittest','test_','_test','fixtures','mock','assert ')
    $ObsoleteMarkers = @('deprecated','obsolete','legacy','quarantine','quarantined','disabled','unused')

    $ExtensionMap = @{
        '.py'='PYTHON'; '.pyw'='PYTHON'
        '.ps1'='POWERSHELL'; '.psm1'='POWERSHELL_MODULE'; '.psd1'='POWERSHELL_MANIFEST'
        '.js'='JAVASCRIPT'; '.mjs'='JAVASCRIPT'; '.cjs'='JAVASCRIPT'
        '.ts'='TYPESCRIPT'; '.tsx'='TYPESCRIPT'
        '.json'='JSON'; '.jsonl'='JSONL'; '.yaml'='YAML'; '.yml'='YAML'; '.toml'='TOML'
        '.xml'='XML'; '.md'='MARKDOWN'; '.txt'='TEXT'; '.log'='LOG'; '.csv'='CSV'
        '.sql'='SQL'; '.html'='HTML'; '.htm'='HTML'; '.css'='CSS'; '.scss'='CSS'
        '.cs'='CSHARP'; '.csproj'='CSHARP_PROJECT'; '.sln'='DOTNET_SOLUTION'
        '.dll'='BINARY'; '.exe'='BINARY_EXECUTABLE'; '.msi'='INSTALLER'
        '.zip'='ARCHIVE'; '.7z'='ARCHIVE'; '.rar'='ARCHIVE'; '.tar'='ARCHIVE'; '.gz'='ARCHIVE'
        '.onnx'='MODEL'; '.gguf'='MODEL'; '.bin'='BINARY'
    }

    $ArtifactNames = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    @(
        '__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.tox','.coverage',
        'node_modules','dist','build','target','.next','.cache','cache','temp','tmp',
        'quarantine','quarantined','archive','old','backup','backups'
    ) | ForEach-Object { [void]$ArtifactNames.Add($_) }

    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host " E-ZZIO — FORENSIC SEMANTIC BODY MAP v2.3" -ForegroundColor Cyan
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host " RACINE             : $SearchRoot"
    Write-Host " CPU THREADS        : $LogicalThreads"
    Write-Host " WORKERS            : $WorkerCount"
    Write-Host " BATCH SIZE         : $BatchSize"
    Write-Host " QUEUE CAPACITY     : $QueueCapacity batches"
    Write-Host " MAX CONTENT READ   : $MaxReadBytes"
    Write-Host " MODE               : READ-ONLY / FAIL-CLOSED" -ForegroundColor Green
    Write-Host " EXECUTION          : 0"
    Write-Host " MUTATION           : 0"
    Write-Host " SECRET CONTENT     : 0"
    Write-Host ""

    if (-not (Test-Path -LiteralPath $SearchRoot -PathType Container)) {
        throw "FAIL-CLOSED : racine inaccessible : $SearchRoot"
    }
    if (-not (Test-Path -LiteralPath $Phase1Root -PathType Container)) {
        throw "FAIL-CLOSED : dossier Phase 1 absent : $Phase1Root"
    }

    Write-Host "[0/7] Validation du dernier RUN Phase 1..." -ForegroundColor Cyan

    $selectedRun = $null
    $selectedManifest = $null

    foreach ($candidateRun in @(
        Get-ChildItem -LiteralPath $Phase1Root -Directory -ErrorAction Stop |
        Sort-Object LastWriteTimeUtc -Descending
    )) {
        $manifestPath = Join-Path $candidateRun.FullName 'RUN_MANIFEST.json'
        if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { continue }
        try {
            $m = Get-Content -LiteralPath $manifestPath -Raw -ErrorAction Stop |
                 ConvertFrom-Json -ErrorAction Stop
            if ($m.Status -eq 'COMPLETED') {
                $selectedRun = $candidateRun
                $selectedManifest = $m
                break
            }
        } catch { continue }
    }

    if ($null -eq $selectedRun) {
        throw "FAIL-CLOSED : aucun RUN Phase 1 COMPLETED valide."
    }

    $inventoryFile = Get-ChildItem -LiteralPath $selectedRun.FullName -File -ErrorAction Stop |
        Where-Object { $_.Name -match '(?i)(inventory|filesystem|files|map).*\.jsonl?$' } |
        Sort-Object Length -Descending |
        Select-Object -First 1

    if ($null -eq $inventoryFile) {
        throw "FAIL-CLOSED : inventaire Phase 1 introuvable."
    }

    Write-Host "    RUN       : $($selectedRun.FullName)" -ForegroundColor Green
    Write-Host "    INVENTORY : $($inventoryFile.FullName)" -ForegroundColor Green

    $RunId = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $OutputRoot = Join-Path 'C:\ProgramData\E-ZZIO\ForensicSemanticBodyMap' $RunId
    New-Item -ItemType Directory -Path $OutputRoot -Force -ErrorAction Stop | Out-Null

    $SemanticFile = Join-Path $OutputRoot 'SEMANTIC_MAP.jsonl'
    $ErrorFile    = Join-Path $OutputRoot 'READ_ERRORS.jsonl'
    $SummaryFile  = Join-Path $OutputRoot 'SUMMARY.json'
    $RunManifest  = Join-Path $OutputRoot 'RUN_MANIFEST.json'

    $WorkerScript = {
        param(
            [object[]]$Batch,
            [string]$RootPath,
            [hashtable]$ExtMap,
            [System.Collections.Generic.HashSet[string]]$SecretNames,
            [System.Collections.Generic.HashSet[string]]$SecretDirs,
            [System.Collections.Generic.HashSet[string]]$ArtifactDirs,
            [System.Collections.Generic.HashSet[string]]$TextExt,
            [long]$MaxBytes,
            [string[]]$Discord,
            [string[]]$Ezzio,
            [string[]]$Ai,
            [string[]]$Tests,
            [string[]]$Obsolete
        )

        $out = [System.Collections.Generic.List[string]]::new()

        foreach ($r in $Batch) {
            try {
                $path = [string]$r.Path
                $name = [string]$r.Name
                $ext  = [string]$r.Extension
                $len  = [int64]$r.Length
                $last = [datetime]$r.LastWriteUtc

                $o = [ordered]@{
                    Status='ANALYZED'; Path=$path; Name=$name; Extension=$ext
                    SizeBytes=$len; LastWriteUTC=$last.ToString('o')
                    Category='UNKNOWN'; Signals=[System.Collections.Generic.List[string]]::new()
                    Risk='LOW'; SecretRead=$false; ContentRead=$false
                }

                $relative = $path
                if ($path.StartsWith($RootPath,[StringComparison]::OrdinalIgnoreCase)) {
                    $relative = $path.Substring($RootPath.Length)
                }
                $segments = $relative -split '[\\/]'

                $secretDirHit = $false
                foreach ($seg in $segments) {
                    if ($SecretDirs.Contains($seg)) { $secretDirHit = $true; break }
                }

                if ($SecretNames.Contains($name) -or $secretDirHit) {
                    $o.Status='SECRET_FILE_NOT_READ'
                    if ($SecretNames.Contains($name)) { $o.Signals.Add('SECRET_FILE_NAME_MATCH') }
                    if ($secretDirHit) { $o.Signals.Add('SECRET_DIRECTORY_MATCH') }
                    $out.Add(($o | ConvertTo-Json -Compress -Depth 8))
                    continue
                }

                if ($ExtMap.ContainsKey($ext)) { $o.Category=$ExtMap[$ext] }

                foreach ($seg in $segments) {
                    if ($ArtifactDirs.Contains($seg)) { $o.Signals.Add("ARTIFACT_DIRECTORY:$seg") }
                }

                if ($name -match '(?i)(test|tests|spec|pytest)') { $o.Signals.Add('TEST_SIGNAL') }
                if ($name -match '(?i)(backup|bak|old|legacy|obsolete|deprecated)') { $o.Signals.Add('LEGACY_SIGNAL') }
                if ($name -match '(?i)(temp|tmp|cache)') { $o.Signals.Add('TEMPORARY_SIGNAL') }
                if ($name -match '(?i)(copy|duplicate|dup)') { $o.Signals.Add('DUPLICATE_NAME_SIGNAL') }

                if ($name -in @(
                    'package.json','requirements.txt','pyproject.toml','Pipfile','Cargo.toml',
                    'go.mod','pom.xml','build.gradle','docker-compose.yml','Dockerfile'
                )) { $o.Signals.Add('PROJECT_MANIFEST') }

                if ($path -match '(?i)E-?ZZIO') {
                    $o.Signals.Add('EZZIO_PATH'); $o.Risk='PROTECTED_REVIEW'
                }

                if ($len -ge 1GB) { $o.Signals.Add('VERY_LARGE_FILE') }
                elseif ($len -ge 100MB) { $o.Signals.Add('LARGE_FILE') }

                $age = ([datetime]::UtcNow - $last).TotalDays
                if ($age -ge 365) { $o.Signals.Add('OLDER_THAN_1_YEAR') }
                elseif ($age -ge 180) { $o.Signals.Add('OLDER_THAN_6_MONTHS') }

                if ($TextExt.Contains($ext) -and $len -gt 0 -and $len -le $MaxBytes) {
                    try {
                        $content = [IO.File]::ReadAllText(
                            $path,[Text.UTF8Encoding]::new($false,$false))
                        $o.ContentRead=$true

                        foreach ($m in $Discord) {
                            if ($content.IndexOf($m,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
                                $o.Signals.Add('DISCORD_CONTENT_MATCH'); break
                            }
                        }
                        foreach ($m in $Ezzio) {
                            if ($content.IndexOf($m,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
                                $o.Signals.Add('EZZIO_CONTENT_MATCH'); break
                            }
                        }
                        foreach ($m in $Ai) {
                            if ($content.IndexOf($m,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
                                $o.Signals.Add('AI_RUNTIME_CONTENT_MATCH'); break
                            }
                        }
                        foreach ($m in $Tests) {
                            if ($content.IndexOf($m,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
                                $o.Signals.Add('TEST_CONTENT_MATCH'); break
                            }
                        }
                        foreach ($m in $Obsolete) {
                            if ($content.IndexOf($m,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
                                $o.Signals.Add('OBSOLETE_CONTENT_MATCH'); break
                            }
                        }
                    }
                    catch {
                        $o.ContentRead=$false
                        $o.Signals.Add('CONTENT_READ_ERROR')
                    }
                }

                $out.Add(($o | ConvertTo-Json -Compress -Depth 8))
            }
            catch {
                $out.Add((
                    [ordered]@{
                        Status='READ_ERROR'
                        Path=([string]$r.Path)
                        Error=$_.Exception.GetType().FullName
                    } | ConvertTo-Json -Compress
                ))
            }
        }
        return $out
    }

    Write-Host "[1/7] Initialisation RunspacePool..." -ForegroundColor Cyan
    $iss = [System.Management.Automation.Runspaces.InitialSessionState]::CreateDefault()
    $pool = [RunspaceFactory]::CreateRunspacePool(1,$WorkerCount,$iss,$Host)
    $pool.Open()

    $jobs = [System.Collections.Generic.List[object]]::new()

    $semanticWriter = [IO.StreamWriter]::new(
        $SemanticFile,$false,[Text.UTF8Encoding]::new($false),1048576)
    $errorWriter = [IO.StreamWriter]::new(
        $ErrorFile,$false,[Text.UTF8Encoding]::new($false),262144)
    $semanticWriter.AutoFlush=$false
    $errorWriter.AutoFlush=$false

    [long]$InventoryLines=0
    [long]$Processed=0
    [long]$Analyzed=0
    [long]$SecretFiles=0
    [long]$ReadErrors=0
    [long]$DiscordHits=0
    [long]$EzzioHits=0

    $StartedUTC=[datetime]::UtcNow

    function Receive-Jobs {
        param([switch]$WaitOne)

        do {
            $completed=@($jobs | Where-Object { $_.Handle.IsCompleted })
            if ($completed.Count -eq 0) {
                if ($WaitOne -and $jobs.Count -gt 0) {
                    Start-Sleep -Milliseconds $IdleSleepMs
                    continue
                }
                break
            }

            foreach ($j in $completed) {
                try {
                    $rows=$j.PS.EndInvoke($j.Handle)
                    foreach ($row in $rows) {
                        $line=[string]$row
                        if ([string]::IsNullOrWhiteSpace($line)) { continue }

                        try {
                            $obj=$line | ConvertFrom-Json -ErrorAction Stop
                            $Processed++

                            if ($obj.Status -eq 'SECRET_FILE_NOT_READ') {
                                $SecretFiles++
                                $semanticWriter.WriteLine($line)
                            }
                            elseif ($obj.Status -eq 'READ_ERROR') {
                                $ReadErrors++
                                $errorWriter.WriteLine($line)
                            }
                            else {
                                $Analyzed++
                                if ($obj.Signals -contains 'DISCORD_CONTENT_MATCH') { $DiscordHits++ }
                                if ($obj.Signals -contains 'EZZIO_CONTENT_MATCH') { $EzzioHits++ }
                                $semanticWriter.WriteLine($line)
                            }

                            if (($Processed % $FlushEvery) -eq 0) {
                                $semanticWriter.Flush(); $errorWriter.Flush()
                            }
                            if (($Processed % $ProgressEvery) -eq 0) {
                                $sec=([datetime]::UtcNow-$StartedUTC).TotalSeconds
                                $rate=if($sec -gt 0){$Processed/$sec}else{0}
                                Write-Host (
                                    "[SEMANTIC] {0:N0} | {1:N0}/s | errors={2:N0} | workers={3}" -f
                                    $Processed,$rate,$ReadErrors,$WorkerCount)
                            }
                        }
                        catch {
                            $ReadErrors++
                            $errorWriter.WriteLine((
                                [ordered]@{Status='RESULT_PARSE_ERROR';Error=$_.Exception.GetType().FullName} |
                                ConvertTo-Json -Compress))
                        }
                    }
                }
                catch {
                    $ReadErrors++
                    $errorWriter.WriteLine((
                        [ordered]@{Status='WORKER_ERROR';Error=$_.Exception.GetType().FullName} |
                        ConvertTo-Json -Compress))
                }
                finally {
                    $j.PS.Dispose()
                    [void]$jobs.Remove($j)
                }
            }
        } while ($WaitOne -and $jobs.Count -gt 0)
    }

    function Get-InventoryRecord {
        param([string]$Line)
        $x=$Line | ConvertFrom-Json -ErrorAction Stop

        $p=$null
        foreach($n in @('Path','FullName','FullPath','FilePath','LiteralPath')) {
            if($null -ne $x.PSObject.Properties[$n]) {
                $v=[string]$x.$n
                if(-not [string]::IsNullOrWhiteSpace($v)){ $p=$v; break }
            }
        }
        if([string]::IsNullOrWhiteSpace($p)){ throw 'INVENTORY_MISSING_PATH' }

        $len=0L
        foreach($n in @('Length','SizeBytes','Size')) {
            if($null -ne $x.PSObject.Properties[$n] -and $null -ne $x.$n){
                try{$len=[int64]$x.$n;break}catch{}
            }
        }

        $last=[datetime]::UtcNow
        foreach($n in @('LastWriteTimeUtc','LastWriteUTC','LastModifiedUtc')) {
            if($null -ne $x.PSObject.Properties[$n] -and $null -ne $x.$n){
                try{$last=([datetime]::Parse([string]$x.$n)).ToUniversalTime();break}catch{}
            }
        }

        [pscustomobject]@{
            Path=$p
            Name=[IO.Path]::GetFileName($p)
            Extension=[IO.Path]::GetExtension($p)
            Length=$len
            LastWriteUtc=$last
        }
    }

    Write-Host "[2/7] Lecture streaming + création des lots..." -ForegroundColor Cyan

    $stream=$null; $reader=$null
    $batch=[System.Collections.Generic.List[object]]::new()

    try {
        $stream=[IO.File]::OpenRead($inventoryFile.FullName)
        $reader=[IO.StreamReader]::new($stream,[Text.Encoding]::UTF8,$true,1048576)

        while($null -ne ($line=$reader.ReadLine())) {
            if([string]::IsNullOrWhiteSpace($line)){continue}
            $InventoryLines++

            try {
                $batch.Add((Get-InventoryRecord $line))
            }
            catch {
                $ReadErrors++
                $errorWriter.WriteLine((
                    [ordered]@{Status='INVENTORY_RECORD_ERROR';Error=$_.Exception.GetType().FullName} |
                    ConvertTo-Json -Compress))
                continue
            }

            if($batch.Count -ge $BatchSize) {
                while($jobs.Count -ge $QueueCapacity){Receive-Jobs -WaitOne}

                $ps=[PowerShell]::Create()
                $ps.RunspacePool=$pool
                [void]$ps.AddScript($WorkerScript)
                [void]$ps.AddArgument($batch.ToArray())
                [void]$ps.AddArgument($SearchRoot)
                [void]$ps.AddArgument($ExtensionMap)
                [void]$ps.AddArgument($SecretFileNames)
                [void]$ps.AddArgument($SecretDirectoryNames)
                [void]$ps.AddArgument($ArtifactNames)
                [void]$ps.AddArgument($TextExtensions)
                [void]$ps.AddArgument([long]$MaxReadBytes)
                [void]$ps.AddArgument($DiscordMarkers)
                [void]$ps.AddArgument($EzzioMarkers)
                [void]$ps.AddArgument($AiRuntimeMarkers)
                [void]$ps.AddArgument($TestMarkers)
                [void]$ps.AddArgument($ObsoleteMarkers)

                $h=$ps.BeginInvoke()
                [void]$jobs.Add([pscustomobject]@{PS=$ps;Handle=$h})
                $batch.Clear()
            }
        }

        if($batch.Count -gt 0) {
            while($jobs.Count -ge $QueueCapacity){Receive-Jobs -WaitOne}
            $ps=[PowerShell]::Create()
            $ps.RunspacePool=$pool
            [void]$ps.AddScript($WorkerScript)
            [void]$ps.AddArgument($batch.ToArray())
            [void]$ps.AddArgument($SearchRoot)
            [void]$ps.AddArgument($ExtensionMap)
            [void]$ps.AddArgument($SecretFileNames)
            [void]$ps.AddArgument($SecretDirectoryNames)
            [void]$ps.AddArgument($ArtifactNames)
            [void]$ps.AddArgument($TextExtensions)
            [void]$ps.AddArgument([long]$MaxReadBytes)
            [void]$ps.AddArgument($DiscordMarkers)
            [void]$ps.AddArgument($EzzioMarkers)
            [void]$ps.AddArgument($AiRuntimeMarkers)
            [void]$ps.AddArgument($TestMarkers)
            [void]$ps.AddArgument($ObsoleteMarkers)
            $h=$ps.BeginInvoke()
            [void]$jobs.Add([pscustomobject]@{PS=$ps;Handle=$h})
            $batch.Clear()
        }
    }
    finally {
        if($null -ne $reader){$reader.Dispose()}
        if($null -ne $stream){$stream.Dispose()}
    }

    Write-Host "[3/7] Vidage complet des lots..." -ForegroundColor Cyan
    while($jobs.Count -gt 0){Receive-Jobs -WaitOne}

    $semanticWriter.Flush()
    $errorWriter.Flush()

    Write-Host "[4/7] Fermeture contrôlée..." -ForegroundColor Cyan
    try{$pool.Close()}finally{$pool.Dispose()}
    $semanticWriter.Dispose()
    $errorWriter.Dispose()

    Write-Host "[5/7] Contrôle d'intégrité..." -ForegroundColor Cyan

    $ratio=if($InventoryLines -gt 0){$Processed/$InventoryLines}else{0}
    $status=if($ratio -ge $MinProcessedRatio -and $ReadErrors -eq 0){
        'COMPLETED'
    } else {
        'FAILED_INTEGRITY_CHECK'
    }

    $duration=[datetime]::UtcNow-$StartedUTC

    $summary=[ordered]@{
        SchemaVersion='2.3'; Status=$status
        StartedUTC=$StartedUTC.ToString('o'); EndUTC=[datetime]::UtcNow.ToString('o')
        DurationSeconds=[math]::Round($duration.TotalSeconds,3)
        Root=$SearchRoot; Phase1Run=$selectedRun.FullName
        Phase1Inventory=$inventoryFile.FullName
        LogicalThreads=$LogicalThreads; WorkerCount=$WorkerCount
        BatchSize=$BatchSize; QueueCapacity=$QueueCapacity; MaxReadBytes=$MaxReadBytes
        InventoryLines=$InventoryLines; Processed=$Processed; Analyzed=$Analyzed
        SecretFiles=$SecretFiles; ReadErrors=$ReadErrors
        DiscordHits=$DiscordHits; EzzioHits=$EzzioHits
        ProcessedRatio=[math]::Round($ratio,4)
        MinProcessedRatio=$MinProcessedRatio
        ExecutionCount=0; MutationCount=0; DeleteCount=0; MoveCount=0; CopyCount=0
        SecretContentReads=0
        SemanticMap=$SemanticFile; ErrorLog=$ErrorFile
        Safety=[ordered]@{
            ReadOnly=$true; FailClosed=$true; Execution=$false; Mutation=$false
            Deletion=$false; Movement=$false; Copy=$false; SecretRead=$false
        }
    }

    $summary | ConvertTo-Json -Depth 15 |
        Set-Content -LiteralPath $SummaryFile -Encoding UTF8 -ErrorAction Stop

    $final=[ordered]@{
        SchemaVersion='2.3'; RunID=$RunId; Status=$status
        StartUTC=$StartedUTC.ToString('o'); EndUTC=[datetime]::UtcNow.ToString('o')
        SourcePhase1=$selectedRun.FullName; Inventory=$inventoryFile.FullName
        Output=$OutputRoot; Workers=$WorkerCount; CPUThreads=$LogicalThreads
        BatchSize=$BatchSize; QueueCapacity=$QueueCapacity
        InventoryLines=$InventoryLines; Processed=$Processed; Analyzed=$Analyzed
        SecretFiles=$SecretFiles; ReadErrors=$ReadErrors
        ProcessedRatio=[math]::Round($ratio,4)
        ReadOnly=$true; FailClosed=$true; Mutation=0; Execution=0
    }

    $final | ConvertTo-Json -Depth 15 |
        Set-Content -LiteralPath $RunManifest -Encoding UTF8 -ErrorAction Stop

    Write-Host "[6/7] Rapports écrits." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host " E-ZZIO — FORENSIC SEMANTIC BODY MAP v2.3 — $status" -ForegroundColor Green
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host (" Inventaire        : {0:N0}" -f $InventoryLines)
    Write-Host (" Traités           : {0:N0} ({1:P1})" -f $Processed,$ratio)
    Write-Host (" Analysés          : {0:N0}" -f $Analyzed)
    Write-Host (" Secrets NON LUS   : {0:N0}" -f $SecretFiles)
    Write-Host (" Erreurs           : {0:N0}" -f $ReadErrors)
    Write-Host (" Discord           : {0:N0}" -f $DiscordHits)
    Write-Host (" E-ZZIO            : {0:N0}" -f $EzzioHits)
    Write-Host (" Durée             : {0}" -f $duration)
    Write-Host ""
    Write-Host " SUMMARY  : $SummaryFile" -ForegroundColor Yellow
    Write-Host " SEMANTIC : $SemanticFile" -ForegroundColor Yellow
    Write-Host " ERRORS   : $ErrorFile" -ForegroundColor Yellow
    Write-Host " MANIFEST : $RunManifest" -ForegroundColor Yellow
    Write-Host ""

    if($status -ne 'COMPLETED'){
        Write-Host "[7/7] FAIL-CLOSED : résultat NON CERTIFIÉ." -ForegroundColor Red
        throw "FAIL-CLOSED : contrôle d'intégrité échoué. Voir $SummaryFile"
    }

    Write-Host "[7/7] READ-ONLY FORENSIC SEMANTIC MAP — PASS" -ForegroundColor Green
}
