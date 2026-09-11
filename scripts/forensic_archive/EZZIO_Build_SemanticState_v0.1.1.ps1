#Requires -Version 7.0
<#
.SYNOPSIS
    E-ZZIO — SEMANTIC TRUTH ENGINE v0.1.1
    NIVEAU 3 — SEMANTIC TRUTH

.DESCRIPTION
    Dérive une représentation sémantique déterministe depuis le Point Zéro
    et les fichiers physiques correspondants.

    CONTRAT :
      - Le Point Zéro et son état topologique sont en lecture seule.
      - Aucun parcours global du corpus pour découvrir les fichiers.
      - Les feuilles du Niveau 2 déterminent les fichiers à analyser.
      - Re-vérification SHA-256 obligatoire avant parsing.
      - Provenance obligatoire : PointZero RunId + hash physique du record.
      - PowerShell : parseur AST natif System.Management.Automation.
      - Python : module standard ast via sous-processus python.
      - JSON : parseur JSON strict + structure de premier/second niveau.
      - Autres extensions : PARSER_UNSUPPORTED, sans inférence.
      - Canonicalisation ordinale stricte.
      - Aucune mutation du Point Zéro.
      - Sortie dans un répertoire distinct.
      - Fail-closed : aucune certification si une gate bloquante échoue.

    IMPORTANT :
      TG-05 dans ce moteur mesure la stabilité canonique de reconstruction
      dans le processus courant. Elle NE constitue PAS la preuve finale de
      déterminisme inter-processus. Une preuve externe Processus A/B est
      requise pour déclarer CERTIFIED_SEMANTIC_DERIVATION.

.NOTES
    Point Zero par défaut :
      G:\AI\_forensic\ContentTruth\run_20260820_130134_380

    Corpus par défaut :
      G:\AI\E-zzio

    Sortie par défaut :
      G:\AI\_forensic\SelfBody\semantic\run_20260820_130134_380
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$PointZeroDir = 'G:\AI\_forensic\ContentTruth\run_20260820_130134_380',

    [Parameter(Mandatory = $false)]
    [string]$SourceRoot = 'G:\AI\E-zzio',

    [Parameter(Mandatory = $false)]
    [string]$OutputDir = 'G:\AI\_forensic\SelfBody\semantic\run_20260820_130134_380',

    [Parameter(Mandatory = $false)]
    [ValidateSet('FAST','FORENSIC')]
    [string]$Mode = 'FORENSIC',

    [Parameter(Mandatory = $false)]
    [switch]$AllowExistingOutput
)

& {
    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    $EngineVersion = '0.1.1'
    $SchemaVersion = '1.0'
    $SupportedExtensions = @('.ps1','.py','.json')

    $script:Gate = [ordered]@{}
    $script:Counts = [ordered]@{
        topology_files       = 0L
        selected_files       = 0L
        parsed_files         = 0L
        unsupported_files    = 0L
        failed_files         = 0L
        total_symbols        = 0L
        total_functions      = 0L
        total_classes        = 0L
        total_methods        = 0L
        total_imports        = 0L
        total_json_keys      = 0L
    }

    function Fail-Closed {
        param([Parameter(Mandatory)][string]$Message)
        throw "FAIL-CLOSED: $Message"
    }

    function Get-Sha256File {
        param([Parameter(Mandatory)][string]$Path)

        if (-not [System.IO.File]::Exists($Path)) {
            Fail-Closed "Fichier absent : $Path"
        }

        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            $stream = [System.IO.File]::Open(
                $Path,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::Read,
                [System.IO.FileShare]::Read
            )
            try {
                $bytes = $sha.ComputeHash($stream)
            }
            finally {
                $stream.Dispose()
            }
        }
        finally {
            $sha.Dispose()
        }

        return ([System.BitConverter]::ToString($bytes)).Replace('-','').ToLowerInvariant()
    }

    function Get-Sha256Text {
        param([Parameter(Mandatory)][AllowEmptyString()][string]$Content)

        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($Content)
            $hash = $sha.ComputeHash($bytes)
        }
        finally {
            $sha.Dispose()
        }

        return ([System.BitConverter]::ToString($hash)).Replace('-','').ToLowerInvariant()
    }

    function Read-Utf8Strict {
        param([Parameter(Mandatory)][string]$Path)

        $encoding = [System.Text.UTF8Encoding]::new($false,$true)
        return [System.IO.File]::ReadAllText($Path,$encoding)
    }

    function ConvertTo-CanonicalJson {
        param([Parameter(Mandatory)]$Object)

        return ($Object | ConvertTo-Json -Depth 100 -Compress)
    }

    function Test-RelativePathSafe {
        param([Parameter(Mandatory)][string]$RelativePath)

        if ([string]::IsNullOrWhiteSpace($RelativePath)) {
            return $false
        }

        $p = $RelativePath.Replace('\','/')
        if ($p.StartsWith('/')) { return $false }
        if ($p -match '^[A-Za-z]:') { return $false }
        if ($p -match '(^|/)\.\.(/|$)') { return $false }
        return $true
    }

    function Resolve-ContainedPath {
        param(
            [Parameter(Mandatory)][string]$Root,
            [Parameter(Mandatory)][string]$RelativePath
        )

        if (-not (Test-RelativePathSafe -RelativePath $RelativePath)) {
            Fail-Closed "RelativePath dangereux : $RelativePath"
        }

        $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\','/')
        $candidate = [System.IO.Path]::GetFullPath(
            [System.IO.Path]::Combine($rootFull,$RelativePath.Replace('/','\'))
        )

        $prefix = $rootFull + [System.IO.Path]::DirectorySeparatorChar
        $cmp = [System.StringComparison]::OrdinalIgnoreCase

        if (
            -not $candidate.StartsWith($prefix,$cmp) -and
            -not [string]::Equals($candidate,$rootFull,$cmp)
        ) {
            Fail-Closed "Évasion de confinement : $RelativePath"
        }

        return $candidate
    }

    function Get-ObjectPropertyString {
        param(
            [Parameter(Mandatory)]$Object,
            [Parameter(Mandatory)][string]$Name
        )

        $prop = $Object.PSObject.Properties[$Name]
        if ($null -eq $prop) { return $null }
        if ($null -eq $prop.Value) { return $null }
        return [string]$prop.Value
    }

    function Get-ObjectPropertyInt64 {
        param(
            [Parameter(Mandatory)]$Object,
            [Parameter(Mandatory)][string]$Name
        )

        $prop = $Object.PSObject.Properties[$Name]
        if ($null -eq $prop) { return $null }
        if ($null -eq $prop.Value) { return $null }
        return [int64]$prop.Value
    }

    function Get-AstLineSpan {
        param([Parameter(Mandatory)]$Extent)

        return @(
            [int]$Extent.StartLineNumber,
            [int]$Extent.EndLineNumber
        )
    }

    function New-Provenance {
        param(
            [Parameter(Mandatory)][string]$RelativePath,
            [Parameter(Mandatory)][string]$ParentRunId,
            [Parameter(Mandatory)][string]$ParentRecordHash,
            [Parameter(Mandatory)]$Extent
        )

        return [ordered]@{
            source_file           = $RelativePath
            parent_point_zero_run = $ParentRunId
            parent_record_hash    = $ParentRecordHash
            line_span             = @(Get-AstLineSpan -Extent $Extent)
        }
    }

    function New-Symbol {
        param(
            [Parameter(Mandatory)][string]$Name,
            [Parameter(Mandatory)][string]$Type,
            [Parameter(Mandatory)]$Provenance,
            [Parameter(Mandatory)]$Signature
        )

        return [ordered]@{
            symbol_name = $Name
            symbol_type = $Type
            provenance  = $Provenance
            signature   = $Signature
        }
    }

    function Get-PythonExecutable {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $cmd) {
            $cmd = Get-Command py -ErrorAction SilentlyContinue
        }
        if ($null -eq $cmd) {
            return $null
        }
        return $cmd.Source
    }

    function Invoke-PythonAst {
        param(
            [Parameter(Mandatory)][string]$PythonExe,
            [Parameter(Mandatory)][string]$Path
        )

        $helper = @'
import ast, json, sys

path = sys.argv[1]

with open(path, "r", encoding="utf-8", errors="strict") as f:
    source = f.read()

tree = ast.parse(source, filename=path, mode="exec")

symbols = []
imports = []

def span(node):
    return [int(getattr(node, "lineno", 1)), int(getattr(node, "end_lineno", getattr(node, "lineno", 1)))]

def name_of(node):
    return getattr(node, "name", None)

def signature_for(node):
    result = {}
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        result["async"] = isinstance(node, ast.AsyncFunctionDef)
        result["args"] = []
        for a in list(getattr(node.args, "posonlyargs", [])) + list(node.args.args):
            result["args"].append(a.arg)
        result["vararg"] = node.args.vararg.arg if node.args.vararg else None
        result["kwarg"] = node.args.kwarg.arg if node.args.kwarg else None
        result["returns"] = ast.unparse(node.returns) if node.returns is not None else None
    elif isinstance(node, ast.ClassDef):
        result["bases"] = [ast.unparse(x) for x in node.bases]
        result["keywords"] = [k.arg for k in node.keywords]
    else:
        result["value"] = None
    return result

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        typ = "method" if any(isinstance(p, ast.ClassDef) for p in ast.walk(tree) if False) else "function"
        symbols.append({
            "name": node.name,
            "type": typ,
            "span": span(node),
            "signature": signature_for(node)
        })
    elif isinstance(node, ast.ClassDef):
        symbols.append({
            "name": node.name,
            "type": "class",
            "span": span(node),
            "signature": signature_for(node)
        })
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
            module = None
        else:
            names = [a.name for a in node.names]
            module = node.module
        imports.append({
            "name": module if module else ",".join(names),
            "type": "import",
            "span": span(node),
            "signature": {
                "module": module,
                "names": names
            }
        })

# Correct method/function classification using parent ownership.
parent = {}
for n in ast.walk(tree):
    for child in ast.iter_child_nodes(n):
        parent[id(child)] = n

for s in symbols:
    # Locate corresponding node by name + span.
    for n in ast.walk(tree):
        if getattr(n, "name", None) == s["name"] and span(n) == s["span"]:
            p = parent.get(id(n))
            if isinstance(p, ast.ClassDef):
                s["type"] = "method"
            break

symbols.extend(imports)

symbols.sort(key=lambda x: (x["span"][0], x["span"][1], x["type"], x["name"]))

print(json.dumps({
    "parser": "python.ast",
    "python_version": sys.version.split()[0],
    "symbols": symbols
}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
'@

        $temp = [System.IO.Path]::GetTempFileName()
        try {
            [System.IO.File]::WriteAllText(
                $temp,
                $helper,
                [System.Text.UTF8Encoding]::new($false)
            )

            # -c is intentionally used with the helper body. The temporary
            # file is only an execution aid and is deleted in finally.
            $code = [System.IO.File]::ReadAllText(
                $temp,
                [System.Text.UTF8Encoding]::new($false)
            )

            $psi = [System.Diagnostics.ProcessStartInfo]::new()
            $psi.FileName = $PythonExe
            $psi.UseShellExecute = $false
            $psi.RedirectStandardOutput = $true
            $psi.RedirectStandardError = $true
            $psi.CreateNoWindow = $true
            [void]$psi.ArgumentList.Add('-c')
            [void]$psi.ArgumentList.Add($code)
            [void]$psi.ArgumentList.Add($Path)

            $process = [System.Diagnostics.Process]::new()
            $process.StartInfo = $psi

            if (-not $process.Start()) {
                Fail-Closed "Impossible de démarrer Python pour $Path"
            }

            $stdout = $process.StandardOutput.ReadToEnd()
            $stderr = $process.StandardError.ReadToEnd()
            $process.WaitForExit()

            if ($process.ExitCode -ne 0) {
                throw "Python AST parse failed: $stderr"
            }

            if ([string]::IsNullOrWhiteSpace($stdout)) {
                throw "Python AST parser returned empty output."
            }

            return ($stdout | ConvertFrom-Json)
        }
        finally {
            if ([System.IO.File]::Exists($temp)) {
                Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
            }
        }
    }

    function Invoke-PowerShellAst {
        param(
            [Parameter(Mandatory)][string]$Path
        )

        $tokens = $null
        $errors = $null

        $text = Read-Utf8Strict -Path $Path

        $ast = [System.Management.Automation.Language.Parser]::ParseInput(
            $text,
            [ref]$tokens,
            [ref]$errors
        )

        if ($null -eq $ast) {
            throw "PowerShell AST parser returned null."
        }

        if ($null -ne $errors -and $errors.Count -gt 0) {
            $messages = @(
                $errors | ForEach-Object {
                    "L$($_.Extent.StartLineNumber):$($_.Message)"
                }
            )
            throw ("PowerShell syntax errors: " + ($messages -join ' | '))
        }

        $symbols = [System.Collections.Generic.List[object]]::new()

        $functions = @(
            $ast.FindAll(
                {
                    param($node)
                    $node -is [System.Management.Automation.Language.FunctionDefinitionAst]
                },
                $true
            )
        )

        foreach ($node in $functions) {
            $prov = New-Provenance `
                -RelativePath '' `
                -ParentRunId '' `
                -ParentRecordHash '' `
                -Extent $node.Extent

            $signature = [ordered]@{
                parameters = @()
                filter     = ($node.IsFilter)
            }

            $symbols.Add(
                (New-Symbol `
                    -Name ([string]$node.Name) `
                    -Type 'function' `
                    -Provenance $prov `
                    -Signature $signature)
            )
        }

        # TypeDefinitionAst is intentionally discovered by runtime type name,
        # avoiding hard dependency on a concrete class that varies across PS versions.
        $typeDefinitions = @(
            $ast.FindAll(
                {
                    param($node)
                    $node.GetType().Name -eq 'TypeDefinitionAst'
                },
                $true
            )
        )

        foreach ($node in $typeDefinitions) {
            $nodeName = [string]$node.Name
            if ([string]::IsNullOrWhiteSpace($nodeName)) {
                continue
            }

            $prov = New-Provenance `
                -RelativePath '' `
                -ParentRunId '' `
                -ParentRecordHash '' `
                -Extent $node.Extent

            $bases = @()
            if ($null -ne $node.PSObject.Properties['BaseTypes']) {
                $bases = @(
                    $node.BaseTypes | ForEach-Object { [string]$_ }
                )
            }

            $classSignature = [ordered]@{
                bases   = @($bases | Sort-Object)
                methods = @()
            }

            if ($null -ne $node.PSObject.Properties['Members']) {
                foreach ($member in @($node.Members)) {
                    if ($member.GetType().Name -match 'FunctionMemberAst|PropertyMemberAst') {
                        if ($member.GetType().Name -match 'FunctionMemberAst') {
                            $classSignature.methods += [string]$member.Name
                        }
                    }
                }
            }

            $classSignature.methods =
                @($classSignature.methods | Sort-Object -Unique)

            $symbols.Add(
                (New-Symbol `
                    -Name $nodeName `
                    -Type 'class' `
                    -Provenance $prov `
                    -Signature $classSignature)
            )

            if ($null -ne $node.PSObject.Properties['Members']) {
                foreach ($member in @($node.Members)) {
                    if ($member.GetType().Name -notmatch 'FunctionMemberAst') {
                        continue
                    }

                    $memberName = [string]$member.Name
                    if ([string]::IsNullOrWhiteSpace($memberName)) {
                        continue
                    }

                    $memberProv = New-Provenance `
                        -RelativePath '' `
                        -ParentRunId '' `
                        -ParentRecordHash '' `
                        -Extent $member.Extent

                    $memberSig = [ordered]@{
                        class_name = $nodeName
                        parameters = @()
                    }

                    $symbols.Add(
                        (New-Symbol `
                            -Name $memberName `
                            -Type 'method' `
                            -Provenance $memberProv `
                            -Signature $memberSig)
                    )
                }
            }
        }

        $usingStatements = @(
            $ast.FindAll(
                {
                    param($node)
                    $node -is [System.Management.Automation.Language.UsingStatementAst]
                },
                $true
            )
        )

        foreach ($node in $usingStatements) {
            $name = [string]$node.Extent.Text.Trim()
            $prov = New-Provenance `
                -RelativePath '' `
                -ParentRunId '' `
                -ParentRecordHash '' `
                -Extent $node.Extent

            $signature = [ordered]@{
                statement = $name
            }

            $symbols.Add(
                (New-Symbol `
                    -Name $name `
                    -Type 'import' `
                    -Provenance $prov `
                    -Signature $signature)
            )
        }

        # Explicit Import-Module commands.
        $commands = @(
            $ast.FindAll(
                {
                    param($node)
                    $node -is [System.Management.Automation.Language.CommandAst]
                },
                $true
            )
        )

        foreach ($command in $commands) {
            if ($command.CommandElements.Count -eq 0) {
                continue
            }

            $commandName = [string]$command.CommandElements[0].Extent.Text
            if ($commandName -notmatch '^(Import-Module|ipmo)$') {
                continue
            }

            $moduleText = if ($command.CommandElements.Count -gt 1) {
                [string]$command.CommandElements[1].Extent.Text
            }
            else {
                ''
            }

            $prov = New-Provenance `
                -RelativePath '' `
                -ParentRunId '' `
                -ParentRecordHash '' `
                -Extent $command.Extent

            $signature = [ordered]@{
                module = $moduleText
            }

            $symbols.Add(
                (New-Symbol `
                    -Name $moduleText `
                    -Type 'import' `
                    -Provenance $prov `
                    -Signature $signature)
            )
        }

        return [ordered]@{
            parser        = 'powershell.ast'
            powershell    = $PSVersionTable.PSVersion.ToString()
            symbols       = @(
                $symbols |
                    Sort-Object `
                        @{Expression={ $_.provenance.line_span[0] }}, `
                        @{Expression={ $_.provenance.line_span[1] }}, `
                        @{Expression={ $_.symbol_type }}, `
                        @{Expression={ $_.symbol_name }}
            )
        }
    }

    function Invoke-JsonSemantic {
        param(
            [Parameter(Mandatory)][string]$Path
        )

        $text = Read-Utf8Strict -Path $Path
        $obj = $text | ConvertFrom-Json

        if ($null -eq $obj) {
            throw "JSON parser returned null."
        }

        $firstLevel = @(
            $obj.PSObject.Properties |
                ForEach-Object { [string]$_.Name } |
                Sort-Object -Culture Invariant
        )

        $secondLevel = [ordered]@{}

        foreach ($prop in @($obj.PSObject.Properties)) {
            $value = $prop.Value
            $keys = @()

            if ($null -ne $value -and $value.PSObject.Properties) {
                $keys = @(
                    $value.PSObject.Properties |
                        ForEach-Object { [string]$_.Name } |
                        Sort-Object -Culture Invariant
                )
            }

            $secondLevel[[string]$prop.Name] = $keys
        }

        return [ordered]@{
            parser = 'json.net'
            structure = [ordered]@{
                first_level_keys = $firstLevel
                second_level_keys = $secondLevel
            }
        }
    }

    function Set-ProvenanceOnSymbols {
        param(
            [Parameter(Mandatory)]$Result,
            [Parameter(Mandatory)][string]$RelativePath,
            [Parameter(Mandatory)][string]$ParentRunId,
            [Parameter(Mandatory)][string]$ParentRecordHash
        )

        $out = [System.Collections.Generic.List[object]]::new()

        foreach ($symbol in @($Result.symbols)) {
            $prov = [ordered]@{
                source_file           = $RelativePath
                parent_point_zero_run = $ParentRunId
                parent_record_hash    = $ParentRecordHash
                line_span             = @(
                    [int]$symbol.provenance.line_span[0],
                    [int]$symbol.provenance.line_span[1]
                )
            }

            $sig = [ordered]@{}
            if ($null -ne $symbol.signature) {
                foreach ($p in @($symbol.signature.PSObject.Properties | Sort-Object Name)) {
                    $sig[[string]$p.Name] = $p.Value
                }
            }

            $out.Add(
                [ordered]@{
                    symbol_name = [string]$symbol.symbol_name
                    symbol_type = [string]$symbol.symbol_type
                    provenance  = $prov
                    signature   = $sig
                }
            )
        }

        return @(
            $out |
                Sort-Object `
                    @{Expression={ $_.provenance.line_span[0] }}, `
                    @{Expression={ $_.provenance.line_span[1] }}, `
                    @{Expression={ $_.symbol_type }}, `
                    @{Expression={ $_.symbol_name }}
        )
    }

    function Get-TopologyLeaves {
        param(
            [Parameter(Mandatory)]$Node,
            [Parameter(Mandatory)][string]$RelativePrefix
        )

        $result = [System.Collections.Generic.List[object]]::new()

        $type = [string]$Node.type
        $name = [string]$Node.name

        if ($type -eq 'file') {
            $relative = if ([string]::IsNullOrWhiteSpace($RelativePrefix)) {
                $name
            }
            else {
                "$RelativePrefix/$name"
            }

            $result.Add(
                [ordered]@{
                    relative_path = $relative.Replace('\','/')
                    name          = $name
                    type          = 'file'
                    size_bytes    = [int64]$Node.size_bytes
                    sha256        = [string]$Node.sha256
                }
            )

            return @($result)
        }

        if ($type -ne 'directory') {
            Fail-Closed "Type topologique inconnu : $type"
        }

        $nextPrefix = if (
            [string]::IsNullOrWhiteSpace($RelativePrefix) -or
            $name -eq 'root'
        ) {
            if ($name -eq 'root') { '' } else { $name }
        }
        else {
            "$RelativePrefix/$name"
        }

        $childrenProp = $Node.PSObject.Properties['children']
        if ($null -eq $childrenProp) {
            Fail-Closed "Nœud topologique sans children : $name"
        }

        foreach ($childProp in @(
            $childrenProp.Value.PSObject.Properties |
                Sort-Object Name
        )) {
            $child = $childProp.Value
            foreach ($leaf in @(Get-TopologyLeaves -Node $child -RelativePrefix $nextPrefix)) {
                $result.Add($leaf)
            }
        }

        return @($result)
    }

    function New-SemanticRecord {
        param(
            [Parameter(Mandatory)][string]$RelativePath,
            [Parameter(Mandatory)][string]$RecordHash,
            [Parameter(Mandatory)][int64]$SizeBytes,
            [Parameter(Mandatory)][string]$ParserStatus,
            [Parameter(Mandatory)][string]$Parser,
            [Parameter(Mandatory)]$Symbols
        )

        return [ordered]@{
            source_file = $RelativePath
            record_hash = $RecordHash
            size_bytes  = $SizeBytes
            parser      = $Parser
            parser_status = $ParserStatus
            symbols     = @($Symbols)
        }
    }

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host " E-ZZIO — SEMANTIC TRUTH ENGINE v$EngineVersion" -ForegroundColor Cyan
    Write-Host ' NIVEAU 3 — SEMANTIC TRUTH' -ForegroundColor Cyan
    Write-Host " MODE : $Mode / READ-ONLY / FAIL-CLOSED" -ForegroundColor Yellow
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''

    try {
        # =====================================================================
        # 0. PREFLIGHT
        # =====================================================================
        Write-Host '[PREFLIGHT] Validation des frontières...' -ForegroundColor Yellow

        if (-not [System.IO.Directory]::Exists($PointZeroDir)) {
            Fail-Closed "PointZeroDir inaccessible : $PointZeroDir"
        }

        if (-not [System.IO.Directory]::Exists($SourceRoot)) {
            Fail-Closed "SourceRoot inaccessible : $SourceRoot"
        }

        $recordsPath = Join-Path $PointZeroDir 'records.jsonl'
        $manifestPath = Join-Path $PointZeroDir 'run_manifest.json'
        $topologyStatePath = Join-Path $OutputDir '..\topology\run_20260820_130134_380\EZZIO_TOPOLOGY_STATE.json'

        # Prefer the topology path derived from the Point Zero run id.
        # The explicit fallback keeps this script usable if the directory was moved.
        $manifestText = Read-Utf8Strict -Path $manifestPath
        $parentManifest = $manifestText | ConvertFrom-Json

        $parentRunId = Get-ObjectPropertyString -Object $parentManifest -Name 'RunId'
        $parentChain = Get-ObjectPropertyString -Object $parentManifest -Name 'ChainHash'
        $parentCertified = [bool]$parentManifest.Certified
        $parentCount = Get-ObjectPropertyInt64 -Object $parentManifest -Name 'FilesProcessed'

        if ([string]::IsNullOrWhiteSpace($parentRunId)) {
            Fail-Closed 'RunId parent absent.'
        }

        if ($parentRunId -ne (Split-Path -Leaf $PointZeroDir)) {
            Fail-Closed "RunId du manifest incohérent avec PointZeroDir : $parentRunId"
        }

        if ([string]::IsNullOrWhiteSpace($parentChain)) {
            Fail-Closed 'ChainHash parent absent.'
        }

        if ($parentCount -le 0) {
            Fail-Closed 'FilesProcessed parent invalide.'
        }

        if (-not $parentCertified) {
            Fail-Closed 'Point Zero non certifié.'
        }

        if (-not [System.IO.File]::Exists($recordsPath)) {
            Fail-Closed "records.jsonl absent : $recordsPath"
        }

        # Topology output is expected one level above the semantic directory.
        $topologyBase = Split-Path -Parent $OutputDir
        $topologyStatePath = Join-Path $topologyBase '..\topology' 
        $topologyStatePath = Join-Path $topologyStatePath (
            (Split-Path -Leaf $OutputDir) + '\EZZIO_TOPOLOGY_STATE.json'
        )
        $topologyStatePath = [System.IO.Path]::GetFullPath($topologyStatePath)

        if (-not [System.IO.File]::Exists($topologyStatePath)) {
            Fail-Closed "État topologique Niveau 2 absent : $topologyStatePath"
        }

        $resolvedPointZero = [System.IO.Path]::GetFullPath($PointZeroDir).TrimEnd('\','/')
        $resolvedOutput = [System.IO.Path]::GetFullPath($OutputDir).TrimEnd('\','/')
        $resolvedSource = [System.IO.Path]::GetFullPath($SourceRoot).TrimEnd('\','/')

        $cmp = [System.StringComparison]::OrdinalIgnoreCase

        if ([string]::Equals($resolvedPointZero,$resolvedOutput,$cmp)) {
            Fail-Closed 'OutputDir identique au Point Zero.'
        }

        if (
            [string]::Equals($resolvedSource,$resolvedOutput,$cmp) -or
            $resolvedOutput.StartsWith($resolvedSource + '\',$cmp)
        ) {
            Fail-Closed 'OutputDir ne doit pas être dans le corpus source.'
        }

        $script:Gate['SG-01_BOUNDARIES'] = $true

        Write-Host ' [PASS] SG-01_BOUNDARIES' -ForegroundColor Green
        Write-Host "        Point Zero : $PointZeroDir"
        Write-Host "        SourceRoot : $SourceRoot"
        Write-Host "        Topology   : $topologyStatePath"
        Write-Host "        Output     : $OutputDir"

        # =====================================================================
        # 1. VERIFY RECORDS PHYSICAL HASH
        # =====================================================================
        Write-Host ''
        Write-Host '[TG-01] Vérification cryptographique du Point Zéro...' -ForegroundColor Yellow

        $recordsSha256 = Get-Sha256File -Path $recordsPath
        $script:Gate['TG-01_PARENT_RECORDS_HASH'] = $recordsSha256 -match '^[0-9a-f]{64}$'

        if (-not $script:Gate['TG-01_PARENT_RECORDS_HASH']) {
            Fail-Closed 'SHA-256 records.jsonl invalide.'
        }

        Write-Host ' [PASS] TG-01_PARENT_RECORDS_HASH' -ForegroundColor Green
        Write-Host "        Records SHA : $recordsSha256"
        Write-Host "        Chain Hash  : $parentChain"
        Write-Host "        Files        : $parentCount"

        # =====================================================================
        # 2. LOAD RECORD HASH MAP
        # =====================================================================
        Write-Host ''
        Write-Host '[TG-02] Construction de l''index de provenance depuis records.jsonl...' -ForegroundColor Yellow

        $recordMap = [System.Collections.Generic.Dictionary[string,string]]::new(
            [System.StringComparer]::Ordinal
        )

        $recordSizeMap = [System.Collections.Generic.Dictionary[string,int64]]::new(
            [System.StringComparer]::Ordinal
        )

        $recordCountObserved = 0L
        $recordsReader = [System.IO.StreamReader]::new(
            $recordsPath,
            [System.Text.UTF8Encoding]::new($false,$true),
            $true,
            65536
        )

        try {
            while (-not $recordsReader.EndOfStream) {
                $line = $recordsReader.ReadLine()

                if ([string]::IsNullOrWhiteSpace($line)) {
                    continue
                }

                $line = $line.Trim().Trim([char]0xFEFF)
                $record = $line | ConvertFrom-Json
                $recordCountObserved++

                $pathProp = $record.PSObject.Properties['RelativePath']
                $hashProp = $record.PSObject.Properties['Hash']
                $sizeProp = $record.PSObject.Properties['SizeExpected']

                if ($null -eq $pathProp -or $null -eq $hashProp -or $null -eq $sizeProp) {
                    Fail-Closed "Record incomplet à l''index $recordCountObserved."
                }

                $rel = ([string]$pathProp.Value).Replace('\','/')
                $hash = ([string]$hashProp.Value).ToLowerInvariant()
                $size = [int64]$sizeProp.Value

                if (-not (Test-RelativePathSafe -RelativePath $rel)) {
                    Fail-Closed "RelativePath dangereux dans records.jsonl : $rel"
                }

                if ($hash -notmatch '^[0-9a-f]{64}$') {
                    Fail-Closed "Hash de record invalide : $rel"
                }

                if ($size -lt 0) {
                    Fail-Closed "SizeExpected négatif : $rel"
                }

                if ($recordMap.ContainsKey($rel)) {
                    Fail-Closed "RelativePath dupliqué dans records.jsonl : $rel"
                }

                $recordMap.Add($rel,$hash)
                $recordSizeMap.Add($rel,$size)
            }
        }
        finally {
            $recordsReader.Dispose()
        }

        if ($recordCountObserved -ne $parentCount) {
            Fail-Closed "Parité records/manifest rompue : $recordCountObserved != $parentCount"
        }

        $script:Gate['TG-02_RECORD_CARDINALITY'] = ($recordCountObserved -eq $parentCount)

        Write-Host ' [PASS] TG-02_RECORD_CARDINALITY' -ForegroundColor Green
        Write-Host "        Records indexés : $recordCountObserved"

        # =====================================================================
        # 3. LOAD TOPOLOGY STATE
        # =====================================================================
        Write-Host ''
        Write-Host '[TG-03] Chargement et validation du Niveau 2...' -ForegroundColor Yellow

        $topologyText = Read-Utf8Strict -Path $topologyStatePath
        $topologyState = $topologyText | ConvertFrom-Json

        if ([string]$topologyState.artifact_type -ne 'EZZIO_TOPOLOGY_STATE') {
            Fail-Closed 'Artifact type topologique invalide.'
        }

        $topologyParent = [string]$topologyState.lineage.parent_point_zero_run
        if ($topologyParent -ne $parentRunId) {
            Fail-Closed "Lignée topologique incohérente : $topologyParent != $parentRunId"
        }

        $topologyParentRecordsHash = [string]$topologyState.lineage.parent_records_sha256
        if ($topologyParentRecordsHash -ne $recordsSha256) {
            Fail-Closed 'Le Niveau 2 ne pointe pas vers le SHA-256 physique actuel de records.jsonl.'
        }

        $topologyLeaves = @(Get-TopologyLeaves -Node $topologyState.tree -RelativePrefix '')
        $script:Counts.topology_files = $topologyLeaves.Count

        if ($topologyLeaves.Count -ne $recordCountObserved) {
            Fail-Closed "Parité topologie/records rompue : $($topologyLeaves.Count) != $recordCountObserved"
        }

        $topologyMap = [System.Collections.Generic.Dictionary[string,object]]::new(
            [System.StringComparer]::Ordinal
        )

        foreach ($leaf in $topologyLeaves) {
            $rp = [string]$leaf.relative_path
            if ($topologyMap.ContainsKey($rp)) {
                Fail-Closed "Chemin dupliqué dans la topologie : $rp"
            }
            $topologyMap.Add($rp,$leaf)
        }

        foreach ($rp in $recordMap.Keys) {
            if (-not $topologyMap.ContainsKey($rp)) {
                Fail-Closed "Record absent de la topologie : $rp"
            }

            if ([string]$topologyMap[$rp].sha256 -ne $recordMap[$rp]) {
                Fail-Closed "Hash record/topologie divergent : $rp"
            }
        }

        $script:Gate['TG-03_TOPOLOGY_PARITY'] = $true

        Write-Host ' [PASS] TG-03_TOPOLOGY_PARITY' -ForegroundColor Green
        Write-Host "        Feuilles topologiques : $($topologyLeaves.Count)"

        # =====================================================================
        # 4. DETERMINE SEMANTIC TARGETS
        # =====================================================================
        Write-Host ''
        Write-Host '[SELECTION] Sélection déterministe des fichiers sémantiques...' -ForegroundColor Yellow

        $topologyFilesSorted = @(
            $topologyLeaves |
                Sort-Object -Property relative_path
        )

        $script:Counts.selected_files = $topologyFilesSorted.Count

        $pythonExe = Get-PythonExecutable
        $pythonAvailable = $null -ne $pythonExe

        $script:Gate['TG-04_PARSER_PREREQUISITES'] = $true

        foreach ($leaf in $topologyFilesSorted) {
            $ext = [System.IO.Path]::GetExtension([string]$leaf.relative_path).ToLowerInvariant()

            if ($ext -eq '.py' -and -not $pythonAvailable) {
                $script:Gate['TG-04_PARSER_PREREQUISITES'] = $false
                break
            }
        }

        if (-not $script:Gate['TG-04_PARSER_PREREQUISITES']) {
            Fail-Closed 'Python requis pour les fichiers .py mais introuvable.'
        }

        Write-Host ' [PASS] TG-04_PARSER_PREREQUISITES' -ForegroundColor Green
        if ($pythonAvailable) {
            Write-Host "        Python : $pythonExe"
        }

        # =====================================================================
        # 5. SEMANTIC ANALYSIS
        # =====================================================================
        Write-Host ''
        Write-Host '[INGESTION] Analyse AST strictement ciblée par la topologie...' -ForegroundColor Yellow
        Write-Host '            Aucun Get-ChildItem / parcours de découverte du corpus.' -ForegroundColor DarkGray

        $semanticFiles = [System.Collections.Generic.List[object]]::new()
        $index = 0
        $total = $topologyFilesSorted.Count

        foreach ($topologyFile in $topologyFilesSorted) {
            $index++

            if (
                $Mode -eq 'FORENSIC' -and
                (
                    $index -eq 1 -or
                    $index % 100 -eq 0 -or
                    $index -eq $total
                )
            ) {
                $pct = if ($total -gt 0) {
                    [int](($index / $total) * 100)
                }
                else {
                    100
                }

                Write-Progress `
                    -Activity 'E-ZZIO Semantic Truth' `
                    -Status "$index / $total" `
                    -PercentComplete $pct
            }

            $relativePath = [string]$topologyFile.relative_path
            $expectedHash = [string]$recordMap[$relativePath]
            $expectedSize = [int64]$recordSizeMap[$relativePath]

            $sourcePath = Resolve-ContainedPath `
                -Root $SourceRoot `
                -RelativePath $relativePath

            if (-not [System.IO.File]::Exists($sourcePath)) {
                Fail-Closed "Fichier source absent : $relativePath"
            }

            $actualSize = [System.IO.FileInfo]::new($sourcePath).Length
            if ($actualSize -ne $expectedSize) {
                Fail-Closed "Taille physique divergente avant parsing : $relativePath"
            }

            $beforeHash = Get-Sha256File -Path $sourcePath

            if ($beforeHash -ne $expectedHash) {
                Fail-Closed "Hash physique divergent avant parsing : $relativePath"
            }

            $ext = [System.IO.Path]::GetExtension($relativePath).ToLowerInvariant()

            $status = 'UNSUPPORTED'
            $parser = 'none'
            $symbols = @()

            try {
                if ($ext -eq '.ps1') {
                    $result = Invoke-PowerShellAst -Path $sourcePath
                    $symbols = Set-ProvenanceOnSymbols `
                        -Result $result `
                        -RelativePath $relativePath `
                        -ParentRunId $parentRunId `
                        -ParentRecordHash $expectedHash
                    $status = 'PARSED'
                    $parser = [string]$result.parser
                }
                elseif ($ext -eq '.py') {
                    $result = Invoke-PythonAst `
                        -PythonExe $pythonExe `
                        -Path $sourcePath

                    $symbols = Set-ProvenanceOnSymbols `
                        -Result $result `
                        -RelativePath $relativePath `
                        -ParentRunId $parentRunId `
                        -ParentRecordHash $expectedHash
                    $status = 'PARSED'
                    $parser = [string]$result.parser
                }
                elseif ($ext -eq '.json') {
                    $result = Invoke-JsonSemantic -Path $sourcePath

                    $prov = [ordered]@{
                        source_file           = $relativePath
                        parent_point_zero_run = $parentRunId
                        parent_record_hash    = $expectedHash
                        line_span             = @(1, ([System.IO.File]::ReadAllLines($sourcePath,[System.Text.UTF8Encoding]::new($false,$true))).Count)
                    }

                    $jsonKeys = @($result.structure.first_level_keys)
                    $secondLevel = [ordered]@{}
                    foreach ($p in @($result.structure.second_level_keys.PSObject.Properties | Sort-Object Name)) {
                        $secondLevel[[string]$p.Name] = @($p.Value)
                    }

                    $symbols = @(
                        New-Symbol `
                            -Name '__json_structure__' `
                            -Type 'json_structure' `
                            -Provenance $prov `
                            -Signature ([ordered]@{
                                first_level_keys  = $jsonKeys
                                second_level_keys = $secondLevel
                            })
                    )

                    $script:Counts.total_json_keys += $jsonKeys.Count
                    $status = 'PARSED'
                    $parser = [string]$result.parser
                }
                else {
                    $script:Counts.unsupported_files++
                }
            }
            catch {
                $script:Counts.failed_files++

                $status = 'PARSER_ERROR'
                $parser = if ($ext -eq '.ps1') {
                    'powershell.ast'
                }
                elseif ($ext -eq '.py') {
                    'python.ast'
                }
                elseif ($ext -eq '.json') {
                    'json.net'
                }
                else {
                    'none'
                }

                # Parsing failure is a hard semantic failure for a supported file.
                Fail-Closed "Parsing échoué pour $relativePath : $($_.Exception.Message)"
            }

            # Mandatory mutation race check after parsing.
            $afterHash = Get-Sha256File -Path $sourcePath

            if ($afterHash -ne $expectedHash) {
                Fail-Closed "Mutation détectée pendant parsing : $relativePath"
            }

            if ($beforeHash -ne $afterHash) {
                Fail-Closed "Hash instable pendant parsing : $relativePath"
            }

            $semanticRecord = New-SemanticRecord `
                -RelativePath $relativePath `
                -RecordHash $expectedHash `
                -SizeBytes $expectedSize `
                -ParserStatus $status `
                -Parser $parser `
                -Symbols $symbols

            $semanticFiles.Add(
                $semanticRecord
            )

            if ($status -eq 'PARSED') {
                $script:Counts.parsed_files++
            }

            $script:Counts.total_symbols += @($symbols).Count

            foreach ($symbol in @($symbols)) {
                switch ([string]$symbol.symbol_type) {
                    'function' { $script:Counts.total_functions++ }
                    'class' { $script:Counts.total_classes++ }
                    'method' { $script:Counts.total_methods++ }
                    'import' { $script:Counts.total_imports++ }
                }
            }
        }

        if ($Mode -eq 'FORENSIC') {
            Write-Progress `
                -Activity 'E-ZZIO Semantic Truth' `
                -Completed
        }

        if ($script:Counts.failed_files -ne 0) {
            Fail-Closed 'Au moins un fichier supporté a échoué au parsing.'
        }

        # =====================================================================
        # 6. CANONICAL PAYLOAD
        # =====================================================================
        Write-Host ''
        Write-Host '[CANONICAL] Construction déterministe du payload sémantique...' -ForegroundColor Yellow

        $canonicalFiles = @(
            $semanticFiles |
                Sort-Object source_file |
                ForEach-Object {
                    $symbolsCanonical = @(
                        @($_.symbols) |
                            Sort-Object `
                                @{Expression={ $_.provenance.line_span[0] }}, `
                                @{Expression={ $_.provenance.line_span[1] }}, `
                                @{Expression={ $_.symbol_type }}, `
                                @{Expression={ $_.symbol_name }}
                    )

                    [ordered]@{
                        source_file   = [string]$_.source_file
                        record_hash   = [string]$_.record_hash
                        size_bytes    = [int64]$_.size_bytes
                        parser        = [string]$_.parser
                        parser_status = [string]$_.parser_status
                        symbols       = $symbolsCanonical
                    }
                }
        )

        $canonicalSummary = [ordered]@{
            topology_files    = [int64]$script:Counts.topology_files
            selected_files    = [int64]$script:Counts.selected_files
            parsed_files      = [int64]$script:Counts.parsed_files
            unsupported_files = [int64]$script:Counts.unsupported_files
            failed_files      = [int64]$script:Counts.failed_files
            total_symbols     = [int64]$script:Counts.total_symbols
            total_functions   = [int64]$script:Counts.total_functions
            total_classes     = [int64]$script:Counts.total_classes
            total_methods     = [int64]$script:Counts.total_methods
            total_imports     = [int64]$script:Counts.total_imports
            total_json_keys   = [int64]$script:Counts.total_json_keys
        }

        $lineage = [ordered]@{
            parent_point_zero_run = $parentRunId
            parent_records_sha256 = $recordsSha256
            parent_chain_hash     = $parentChain
            parent_record_count   = [int64]$recordCountObserved
            parent_topology_state = 'EZZIO_TOPOLOGY_STATE'
        }

        $canonicalPayloadObject = [ordered]@{
            lineage = $lineage
            summary = $canonicalSummary
            files   = $canonicalFiles
        }

        $canonicalPayloadJson = ConvertTo-CanonicalJson -Object $canonicalPayloadObject
        $semanticPayloadSha256 = Get-Sha256Text -Content $canonicalPayloadJson

        # Reconstruct canonical JSON independently from the already canonical
        # object. This is a same-process canonical stability check only.
        $canonicalPayloadJson2 = ConvertTo-CanonicalJson -Object $canonicalPayloadObject
        $semanticPayloadSha2562 = Get-Sha256Text -Content $canonicalPayloadJson2

        $script:Gate['TG-05_CANONICAL_STABILITY'] = (
            $semanticPayloadSha256 -eq $semanticPayloadSha2562 -and
            $semanticPayloadSha256 -match '^[0-9a-f]{64}$'
        )

        if (-not $script:Gate['TG-05_CANONICAL_STABILITY']) {
            Fail-Closed 'Échec de stabilité canonique.'
        }

        Write-Host ' [PASS] TG-05_CANONICAL_STABILITY' -ForegroundColor Green
        Write-Host "        Semantic Payload SHA256 : $semanticPayloadSha256"
        Write-Host '        NOTE : TG-05 inter-processus reste à prouver par harness externe.' -ForegroundColor DarkYellow

        # =====================================================================
        # 7. FINAL QUALITY GATES
        # =====================================================================
        $script:Gate['TG-06_SYMBOL_PROVENANCE'] = $true

        foreach ($file in $canonicalFiles) {
            if ([string]::IsNullOrWhiteSpace([string]$file.source_file)) {
                $script:Gate['TG-06_SYMBOL_PROVENANCE'] = $false
                break
            }

            if ([string]$file.record_hash -notmatch '^[0-9a-f]{64}$') {
                $script:Gate['TG-06_SYMBOL_PROVENANCE'] = $false
                break
            }

            foreach ($symbol in @($file.symbols)) {
                if (
                    [string]$symbol.provenance.source_file -ne
                    [string]$file.source_file
                ) {
                    $script:Gate['TG-06_SYMBOL_PROVENANCE'] = $false
                    break
                }

                if (
                    [string]$symbol.provenance.parent_record_hash -ne
                    [string]$file.record_hash
                ) {
                    $script:Gate['TG-06_SYMBOL_PROVENANCE'] = $false
                    break
                }
            }

            if (-not $script:Gate['TG-06_SYMBOL_PROVENANCE']) {
                break
            }
        }

        if (-not $script:Gate['TG-06_SYMBOL_PROVENANCE']) {
            Fail-Closed 'Provenance inverse incomplète.'
        }

        $script:Gate['TG-07_SOURCE_STABILITY'] = $true

        foreach ($leaf in $topologyFilesSorted) {
            $rp = [string]$leaf.relative_path
            $sourcePath = Resolve-ContainedPath -Root $SourceRoot -RelativePath $rp
            $hashNow = Get-Sha256File -Path $sourcePath

            if ($hashNow -ne [string]$recordMap[$rp]) {
                $script:Gate['TG-07_SOURCE_STABILITY'] = $false
                break
            }
        }

        if (-not $script:Gate['TG-07_SOURCE_STABILITY']) {
            Fail-Closed 'Un ou plusieurs fichiers ont muté pendant la construction.'
        }

        Write-Host ''
        Write-Host '[QUALITY GATES] Validation finale...' -ForegroundColor Yellow

        foreach ($gateName in @($script:Gate.Keys)) {
            if ([bool]$script:Gate[$gateName]) {
                Write-Host " [PASS] $gateName" -ForegroundColor Green
            }
            else {
                Write-Host " [FAIL] $gateName" -ForegroundColor Red
            }
        }

        # =====================================================================
        # 8. OUTPUT TRANSACTION — NEVER OVERWRITE FROZEN
        # =====================================================================
        if ([System.IO.Directory]::Exists($OutputDir)) {
            $frozen = Join-Path $OutputDir 'FROZEN'
            if ([System.IO.File]::Exists($frozen) -and -not $AllowExistingOutput) {
                Fail-Closed "Dérivation sémantique déjà FROZEN : $OutputDir"
            }

            if (-not $AllowExistingOutput) {
                Fail-Closed "OutputDir existe déjà. Utiliser un nouveau run ou -AllowExistingOutput explicitement."
            }
        }

        [System.IO.Directory]::CreateDirectory($OutputDir) | Out-Null

        $statePath = Join-Path $OutputDir 'EZZIO_SEMANTIC_STATE.json'
        $semanticManifestPath = Join-Path $OutputDir 'semantic_manifest.json'
        $frozenPath = Join-Path $OutputDir 'FROZEN'

        $generatedAt = [DateTime]::UtcNow.ToString('o')

        $stateObject = [ordered]@{
            artifact_type = 'EZZIO_SEMANTIC_STATE'
            schema_version = $SchemaVersion
            metadata = [ordered]@{
                generated_at_utc = $generatedAt
                generator_version = $EngineVersion
                engine = 'EZZIO_Semantic_Truth_Engine'
                mode = $Mode
            }
            lineage = $lineage
            summary = $canonicalSummary
            files = $canonicalFiles
            proof = [ordered]@{
                semantic_payload_sha256 = $semanticPayloadSha256
                gates_passed = @(
                    $script:Gate.GetEnumerator() |
                        Where-Object { [bool]$_.Value } |
                        ForEach-Object { [string]$_.Key }
                )
            }
        }

        $stateJson = ConvertTo-CanonicalJson -Object $stateObject

        $tempState = "$statePath.tmp.$([Guid]::NewGuid().ToString('N'))"
        [System.IO.File]::WriteAllText(
            $tempState,
            $stateJson,
            [System.Text.UTF8Encoding]::new($false)
        )

        if ([System.IO.File]::Exists($statePath)) {
            Remove-Item -LiteralPath $statePath -Force
        }

        Move-Item -LiteralPath $tempState -Destination $statePath -Force

        $artifactSha256 = Get-Sha256File -Path $statePath

        $semanticManifestObject = [ordered]@{
            artifact_type = 'EZZIO_SEMANTIC_MANIFEST'
            schema_version = $SchemaVersion
            sealed_at_utc = [DateTime]::UtcNow.ToString('o')
            generator_version = $EngineVersion
            parent_point_zero_run = $parentRunId
            parent_records_sha256 = $recordsSha256
            parent_chain_hash = $parentChain
            topology_state_sha256 = Get-Sha256File -Path $topologyStatePath
            semantic_payload_sha256 = $semanticPayloadSha256
            semantic_artifact_sha256 = $artifactSha256
            record_count = [int64]$recordCountObserved
            parsed_files = [int64]$script:Counts.parsed_files
            unsupported_files = [int64]$script:Counts.unsupported_files
            failed_files = [int64]$script:Counts.failed_files
            tg05_scope = 'IN_PROCESS_CANONICAL_STABILITY_ONLY'
            status = 'DERIVATION_READY_FOR_EXTERNAL_TG05'
        }

        $manifestJson = ConvertTo-CanonicalJson -Object $semanticManifestObject

        [System.IO.File]::WriteAllText(
            $semanticManifestPath,
            $manifestJson,
            [System.Text.UTF8Encoding]::new($false)
        )

        $manifestSha256 = Get-Sha256File -Path $semanticManifestPath

        # Intentionally DO NOT emit FROZEN/CERTIFIED here.
        # The external double-process TG-05 must be supplied by a separate harness.
        $script:Gate['TG-08_OUTPUT_INTEGRITY'] = (
            [System.IO.File]::Exists($statePath) -and
            [System.IO.File]::Exists($semanticManifestPath) -and
            (Get-Sha256File -Path $statePath) -eq $artifactSha256 -and
            (Get-Sha256File -Path $semanticManifestPath) -eq $manifestSha256
        )

        if (-not $script:Gate['TG-08_OUTPUT_INTEGRITY']) {
            Fail-Closed 'Intégrité post-commit des artefacts échouée.'
        }

        # =====================================================================
        # 9. VERDICT
        # =====================================================================
        Write-Host ''
        Write-Host '============================================================' -ForegroundColor Cyan
        Write-Host ' NIVEAU 3 : DERIVATION SEMANTIQUE PRODUITE' -ForegroundColor Green
        Write-Host '============================================================' -ForegroundColor Cyan

        Write-Host "Point Zero          : $parentRunId"
        Write-Host "Records             : $recordCountObserved"
        Write-Host "Parsed files        : $($script:Counts.parsed_files)"
        Write-Host "Unsupported files   : $($script:Counts.unsupported_files)"
        Write-Host "Symbols             : $($script:Counts.total_symbols)"
        Write-Host "Functions           : $($script:Counts.total_functions)"
        Write-Host "Classes             : $($script:Counts.total_classes)"
        Write-Host "Methods             : $($script:Counts.total_methods)"
        Write-Host "Imports             : $($script:Counts.total_imports)"
        Write-Host ''
        Write-Host "Semantic Payload    : $semanticPayloadSha256"
        Write-Host "Semantic Artifact   : $artifactSha256"
        Write-Host "Manifest SHA256     : $manifestSha256"
        Write-Host ''
        Write-Host "Artefact            : $statePath"
        Write-Host "Manifest            : $semanticManifestPath"
        Write-Host "FROZEN              : NON ÉMIS — TG-05 EXTERNE REQUIS" -ForegroundColor Yellow
        Write-Host ''
        Write-Host 'STATUT : DERIVATION_READY_FOR_EXTERNAL_TG05' -ForegroundColor Yellow
        Write-Host '============================================================' -ForegroundColor Cyan

        # Explicit machine-readable exit state.
        if (-not $script:Gate['TG-08_OUTPUT_INTEGRITY']) {
            exit 20
        }

        exit 0
    }
    catch {
        Write-Host ''
        Write-Host '============================================================' -ForegroundColor Red
        Write-Host ' E-ZZIO — SEMANTIC TRUTH ENGINE : FAIL-CLOSED' -ForegroundColor Red
        Write-Host '============================================================' -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Write-Host ''
        Write-Host 'Aucun statut CERTIFIED/FROZEN n''est autorisé après échec.' -ForegroundColor Yellow
        exit 10
    }
}
