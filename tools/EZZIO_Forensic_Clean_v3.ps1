# ==============================================================================
# E-ZZIO — FORENSIC CLEAN v3 (STRICT SYNTAX & RO-001 PATCHED)
# READ ONLY — AUCUNE MODIFICATION DU PROJET
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- CONFIGURATION ---
$Project = 'G:\AI\E-zzio'
$Python  = 'G:\Python312\python.exe'
$ReportDir = Join-Path $env:TEMP 'EZZIO_FORENSIC_CLEAN'
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$ReportJson = Join-Path $ReportDir "forensic_$Timestamp.json"
$ReportTxt  = Join-Path $ReportDir "forensic_$Timestamp.txt"

$Results = [System.Collections.Generic.List[object]]::new()
$Started = Get-Date

function Add-Result {
    param(
        [Parameter(Mandatory)][string]$Id,
        [Parameter(Mandatory)][ValidateSet('PASS','FAIL','WARN','INFO')][string]$Status,
        [Parameter(Mandatory)][string]$Message,
        $Data = $null
    )
    $Results.Add([pscustomobject]@{ Id = $Id; Status = $Status; Message = $Message; Data = $Data })
    $Color = switch ($Status) {
        'PASS' { 'Green' }
        'FAIL' { 'Red' }
        'WARN' { 'Yellow' }
        default { 'Cyan' }
    }
    Write-Host "[$Status] $Id - $Message" -ForegroundColor $Color
}

Clear-Host
Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO FORENSIC CLEAN v3 — READ ONLY' -ForegroundColor Cyan
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host ''

# --- 01/10 ENVIRONNEMENT ---
Write-Host '[01/10] ENVIRONNEMENT' -ForegroundColor Cyan
if (Test-Path -LiteralPath $Project -PathType Container) {
    Add-Result -Id 'ENV-001' -Status 'PASS' -Message "Projet accessible : $Project"
} else {
    Add-Result -Id 'ENV-001' -Status 'FAIL' -Message "Projet inaccessible : $Project"
}

if (Test-Path -LiteralPath $Python -PathType Leaf) {
    try {
        $PythonVersion = & $Python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Add-Result -Id 'ENV-002' -Status 'PASS' -Message "$PythonVersion"
        } else {
            Add-Result -Id 'ENV-002' -Status 'FAIL' -Message "Python non exécutable : $Python"
        }
    } catch {
        Add-Result -Id 'ENV-002' -Status 'FAIL' -Message "Erreur Python : $($_.Exception.Message)"
    }
} else {
    Add-Result -Id 'ENV-002' -Status 'FAIL' -Message "Python introuvable : $Python"
}

# --- 02/10 MEMORY CORE ---
Write-Host '[02/10] MEMORY CORE' -ForegroundColor Cyan
$MemoryExpected = Join-Path $Project 'core\memory_core.py'
$MemoryCandidates = @(Get-ChildItem -LiteralPath $Project -File -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'memory_core.py' } | Sort-Object FullName)

if (Test-Path -LiteralPath $MemoryExpected -PathType Leaf) {
    $MemoryItem = Get-Item -LiteralPath $MemoryExpected
    Add-Result -Id 'FILE-MEM' -Status 'PASS' -Message "memory_core.py présent : $($MemoryItem.FullName) ($($MemoryItem.Length) octets)"
} elseif ($MemoryCandidates.Count -gt 0) {
    foreach ($Candidate in $MemoryCandidates) {
        Add-Result -Id 'FILE-MEM-DISCOVERY' -Status 'INFO' -Message "memory_core.py trouvé ailleurs : $($Candidate.FullName)"
    }
    Add-Result -Id 'FILE-MEM' -Status 'WARN' -Message "Chemin attendu absent : $MemoryExpected ; un autre memory_core.py existe."
} else {
    Add-Result -Id 'FILE-MEM' -Status 'FAIL' -Message "Aucun memory_core.py trouvé dans le projet."
}

# --- 03/10 WEB SERVER ---
Write-Host '[03/10] WEB SERVER — DECOUVERTE REELLE' -ForegroundColor Cyan
$WebCandidates = @(Get-ChildItem -LiteralPath $Project -File -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'web_server.py' } | Sort-Object FullName)
$WebServer = $null

if ($WebCandidates.Count -eq 0) {
    Add-Result -Id 'FILE-WEB' -Status 'WARN' -Message 'Aucun web_server.py trouvé dans le projet.'
} else {
    foreach ($File in $WebCandidates) {
        Add-Result -Id 'FILE-WEB-DISCOVERY' -Status 'PASS' -Message "web_server.py trouvé : $($File.FullName) ($($File.Length) octets)"
    }
    $PreferredPaths = @((Join-Path $Project 'web\web_server.py'), (Join-Path $Project 'web_server.py'))
    foreach ($PreferredPath in $PreferredPaths) {
        $Match = $WebCandidates | Where-Object { $_.FullName -eq $PreferredPath } | Select-Object -First 1
        if ($null -ne $Match) {
            $WebServer = $Match.FullName
            break
        }
    }
    if ($null -eq $WebServer) {
        $WebServer = ($WebCandidates | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
    }
    Add-Result -Id 'FILE-WEB-ACTIVE' -Status 'INFO' -Message "web_server.py retenu : $WebServer"
}

# --- 04/10 SQLITE ---
Write-Host '[04/10] SQLITE — DECOUVERTE REELLE' -ForegroundColor Cyan
$DbCandidates = @(
    (Join-Path $Project 'runtime\memory\database\memory.sqlite3'),
    (Join-Path $Project 'runtime\memory\sqlite\cognitive_store.db'),
    (Join-Path $Project 'data\action_registry.db')
)
$MemoryDb = $null

foreach ($CandidatePath in $DbCandidates) {
    if (Test-Path -LiteralPath $CandidatePath -PathType Leaf) {
        $MemoryDb = $CandidatePath
        break
    }
}

if ($null -eq $MemoryDb) {
    $FoundDatabases = @(Get-ChildItem -LiteralPath $Project -File -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in @('.db','.sqlite','.sqlite3') } | Sort-Object Length -Descending)
    if ($FoundDatabases.Count -gt 0) {
        foreach ($Database in $FoundDatabases) {
            Add-Result -Id 'SQLITE-DISCOVERY' -Status 'INFO' -Message "SQLite trouvé : $($Database.FullName) ($($Database.Length) octets)"
        }
        $MemoryDb = $FoundDatabases[0].FullName
    }
}

if ($null -ne $MemoryDb) {
    $DbItem = Get-Item -LiteralPath $MemoryDb
    Add-Result -Id 'SQLITE' -Status 'PASS' -Message "Base SQLite retenue : $MemoryDb ($($DbItem.Length) octets)"
} else {
    Add-Result -Id 'SQLITE' -Status 'WARN' -Message 'Aucune base SQLite trouvée.'
}

# --- 05/10 SYNTAXE PYTHON — MEMORY CORE ---
Write-Host '[05/10] PYTHON — SYNTAXE MEMORY CORE' -ForegroundColor Cyan
if ($null -ne $MemoryExpected -and (Test-Path -LiteralPath $MemoryExpected -PathType Leaf)) {
    try {
        $PythonAstCode = "import ast`nimport sys`npath = sys.argv[1]`nwith open(path, 'r', encoding='utf-8') as f:`n    source = f.read()`nast.parse(source, filename=path)`nprint('SYNTAX_OK')"
        $TempAstScript = Join-Path $env:TEMP "ezzio_ast_$([guid]::NewGuid().ToString('N')).py"
        Set-Content -LiteralPath $TempAstScript -Value $PythonAstCode -Encoding UTF8
        
        $AstOutput = & $Python $TempAstScript $MemoryExpected 2>&1
        if ($LASTEXITCODE -eq 0) {
            Add-Result -Id 'PY-MEM' -Status 'PASS' -Message 'memory_core.py : syntaxe Python OK'
        } else {
            Add-Result -Id 'PY-MEM' -Status 'FAIL' -Message "memory_core.py : syntaxe invalide. $($AstOutput -join ' ')"
        }
        if (Test-Path -LiteralPath $TempAstScript -PathType Leaf) { Remove-Item -LiteralPath $TempAstScript -Force -ErrorAction SilentlyContinue }
    } catch {
        Add-Result -Id 'PY-MEM' -Status 'FAIL' -Message "Impossible de contrôler memory_core.py : $($_.Exception.Message)"
    }
} else {
    Add-Result -Id 'PY-MEM' -Status 'WARN' -Message 'Contrôle syntaxique memory_core.py ignoré : fichier absent.'
}

# --- 06/10 SYNTAXE PYTHON — WEB SERVER ---
Write-Host '[06/10] PYTHON — SYNTAXE WEB SERVER' -ForegroundColor Cyan
if ($null -ne $WebServer) {
    try {
        $PythonAstCode = "import ast`nimport sys`npath = sys.argv[1]`nwith open(path, 'r', encoding='utf-8') as f:`n    source = f.read()`nast.parse(source, filename=path)`nprint('SYNTAX_OK')"
        $TempAstScript = Join-Path $env:TEMP "ezzio_ast_$([guid]::NewGuid().ToString('N')).py"
        Set-Content -LiteralPath $TempAstScript -Value $PythonAstCode -Encoding UTF8
        
        $AstOutput = & $Python $TempAstScript $WebServer 2>&1
        if ($LASTEXITCODE -eq 0) {
            Add-Result -Id 'PY-WEB' -Status 'PASS' -Message 'web_server.py : syntaxe Python OK'
        } else {
            Add-Result -Id 'PY-WEB' -Status 'FAIL' -Message "web_server.py : syntaxe invalide. $($AstOutput -join ' ')"
        }
        if (Test-Path -LiteralPath $TempAstScript -PathType Leaf) { Remove-Item -LiteralPath $TempAstScript -Force -ErrorAction SilentlyContinue }
    } catch {
        Add-Result -Id 'PY-WEB' -Status 'FAIL' -Message "Impossible de contrôler web_server.py : $($_.Exception.Message)"
    }
} else {
    Add-Result -Id 'PY-WEB' -Status 'WARN' -Message 'Contrôle syntaxique web_server.py ignoré : fichier absent.'
}

# --- 07/10 HEALTH HTTP ---
Write-Host '[07/10] HEALTH HTTP' -ForegroundColor Cyan
try {
    $Health = Invoke-WebRequest -Uri 'http://127.0.0.1:8001/health' -TimeoutSec 3 -ErrorAction Stop
    if ($Health.StatusCode -eq 200) {
        Add-Result -Id 'HEALTH' -Status 'PASS' -Message '/health HTTP 200'
    } else {
        Add-Result -Id 'HEALTH' -Status 'WARN' -Message "/health HTTP $($Health.StatusCode)"
    }
} catch {
    Add-Result -Id 'HEALTH' -Status 'WARN' -Message 'Démon non joignable sur 127.0.0.1:8001.'
}

# --- 08/10 GUARDIAN BACKUPS ---
Write-Host '[08/10] GUARDIAN RUNTIME' -ForegroundColor Cyan
$RuntimePath = Join-Path $Project 'runtime'
if (Test-Path -LiteralPath $RuntimePath -PathType Container) {
    $RuntimeBackups = @(Get-ChildItem -LiteralPath $RuntimePath -Directory -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'guardian.backup-*' })
    if ($RuntimeBackups.Count -eq 0) {
        Add-Result -Id 'GUARDIAN' -Status 'PASS' -Message 'Aucun guardian.backup-* dans runtime.'
    } else {
        Add-Result -Id 'GUARDIAN' -Status 'WARN' -Message "$($RuntimeBackups.Count) backup(s) guardian encore présent(s) dans runtime."
        foreach ($Backup in $RuntimeBackups) {
            Add-Result -Id 'GUARDIAN-BACKUP' -Status 'INFO' -Message "Backup présent : $($Backup.FullName)"
        }
    }
} else {
    Add-Result -Id 'GUARDIAN' -Status 'WARN' -Message "Dossier runtime absent : $RuntimePath"
}

# --- 09/10 CONTROLE READ ONLY ---
Write-Host '[09/10] CONTROLE READ ONLY' -ForegroundColor Cyan
$ScriptPath = $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
    Add-Result -Id 'RO-001' -Status 'WARN' -Message 'Chemin du script courant indisponible.'
}
else {
    try {
        $ScriptContent = Get-Content -LiteralPath $ScriptPath -Raw -Encoding UTF8

        # Obfuscation des mots-clés pour empêcher l'auto-détection par le scanner
        $WriteCmds = @(
            'Remove' + '-Item',
            'Move' + '-Item',
            'Rename' + '-Item',
            'Copy' + '-Item',
            'Set' + '-Content',
            'Add' + '-Content',
            'Clear' + '-Content'
        )

        $DangerousMatches = 0
        $TargetVar = '\$Project'

        foreach ($Cmd in $WriteCmds) {
            # On cherche une commande destructrice suivie de la variable $Project
            $Pattern = "(?im)\b$Cmd\b.*$TargetVar"
            $Matches = [regex]::Matches($ScriptContent, $Pattern)
            if ($Matches.Count -gt 0) {
                $DangerousMatches += $Matches.Count
            }
        }

        if ($DangerousMatches -eq 0) {
            Add-Result -Id 'RO-001' -Status 'PASS' -Message 'Aucune operation destructive ciblee vers le projet detectee.'
        }
        else {
            Add-Result -Id 'RO-001' -Status 'FAIL' -Message "$DangerousMatches operation(s) dangereuse(s) ciblee(s) vers le projet detectee(s)."
        }
    }
    catch {
        Add-Result -Id 'RO-001' -Status 'FAIL' -Message "Controle READ ONLY impossible : $($_.Exception.Message)"
    }
}

# --- 10/10 SYNTAXE POWERSHELL ---
Write-Host '[10/10] POWERSHELL — PARSER' -ForegroundColor Cyan
if ($null -ne $ScriptPath -and (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {
    try {
        $ParseErrors = $null
        [System.Management.Automation.Language.Parser]::ParseFile($ScriptPath, [ref]$null, [ref]$ParseErrors) | Out-Null
        if ($null -eq $ParseErrors -or $ParseErrors.Count -eq 0) {
            Add-Result -Id 'PS-SYNTAX' -Status 'PASS' -Message 'Syntaxe PowerShell valide.'
        } else {
            foreach ($ParseError in $ParseErrors) {
                $Msg = "Ligne {0}, colonne {1} : {2}" -f $ParseError.Extent.StartLineNumber, $ParseError.Extent.StartColumnNumber, $ParseError.Message
                Add-Result -Id 'PS-SYNTAX-ERROR' -Status 'FAIL' -Message $Msg
            }
            Add-Result -Id 'PS-SYNTAX' -Status 'FAIL' -Message "$($ParseErrors.Count) erreur(s) de syntaxe PowerShell."
        }
    } catch {
        Add-Result -Id 'PS-SYNTAX' -Status 'FAIL' -Message "Parser PowerShell impossible : $($_.Exception.Message)"
    }
} else {
    Add-Result -Id 'PS-SYNTAX' -Status 'FAIL' -Message 'Script courant introuvable.'
}

# --- SYNTHESE & RAPPORTS ---
$Pass = @($Results | Where-Object { $_.Status -eq 'PASS' }).Count
$Fail = @($Results | Where-Object { $_.Status -eq 'FAIL' }).Count
$Warn = @($Results | Where-Object { $_.Status -eq 'WARN' }).Count
$Info = @($Results | Where-Object { $_.Status -eq 'INFO' }).Count

$Overall = if ($Fail -gt 0) { 'FAIL' } elseif ($Warn -gt 0) { 'PASS_WITH_WARNINGS' } else { 'PASS' }
$Finished = Get-Date
$Duration = $Finished - $Started

if (-not (Test-Path -LiteralPath $ReportDir -PathType Container)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}

$Report = [ordered]@{
    Validation = 'E-ZZIO FORENSIC CLEAN v3'
    Mode       = 'READ_ONLY'
    Project    = $Project
    Python     = $Python
    MemoryCore = $MemoryExpected
    WebServer  = $WebServer
    MemoryDb   = $MemoryDb
    Overall    = $Overall
    Statistics = [ordered]@{ PASS = $Pass; FAIL = $Fail; WARN = $Warn; INFO = $Info; Total = $Results.Count }
    Started    = $Started.ToString('o')
    Finished   = $Finished.ToString('o')
    Duration   = $Duration.ToString()
    Results    = $Results
}

$Report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $ReportJson -Encoding UTF8

$Lines = [System.Collections.Generic.List[string]]::new()
$Lines.Add('E-ZZIO FORENSIC CLEAN v3')
$Lines.Add('MODE : READ_ONLY')
$Lines.Add("Overall : $Overall")
$Lines.Add("PASS=$Pass FAIL=$Fail WARN=$Warn INFO=$Info")
$Lines.Add("Total=$($Results.Count)")
foreach ($Result in $Results) {
    $FormattedLine = '[{0}] {1} - {2}' -f $Result.Status, $Result.Id, $Result.Message
    $Lines.Add($FormattedLine)
}
$Lines | Set-Content -LiteralPath $ReportTxt -Encoding UTF8

$FinalColor = if ($Fail -gt 0) { 'Red' } elseif ($Warn -gt 0) { 'Yellow' } else { 'Green' }
Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host " RÉSULTAT GLOBAL : $Overall" -ForegroundColor $FinalColor
Write-Host " PASS=$Pass  FAIL=$Fail  WARN=$Warn  INFO=$Info"
Write-Host " Durée : $Duration"
Write-Host " Rapport TXT  : $ReportTxt" -ForegroundColor DarkGray
Write-Host " Rapport JSON : $ReportJson" -ForegroundColor DarkGray
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host ''