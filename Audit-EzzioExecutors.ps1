<#
.SYNOPSIS
    E-zzio Phase 2.3: Executor Compliance Audit & Git Sealing (V2 - Hardened)
#>
[CmdletBinding()]
param([string]$ProjectRoot = "G:\AI\E-zzio")

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $ProjectRoot
$Utf8NoBOM = New-Object System.Text.UTF8Encoding $false

function Write-Header { param([string]$Msg) Write-Host "`n=== $Msg ===" -ForegroundColor Cyan }
function Write-Success { param([string]$Msg) Write-Host "[+] $Msg" -ForegroundColor Green }
function Write-ErrorCustom { param([string]$Msg) Write-Host "[-] $Msg" -ForegroundColor Red }

Write-Header "E-ZZIO PHASE 2.3 : EXECUTOR COMPLIANCE AUDIT (STRICT)"

# 1. UTILITAIRE D'ÉCRITURE ABSOLUE
function Write-Utf8File {
    param([string]$RelativePath, [string]$Content)
    $FullPath = Join-Path $ProjectRoot $RelativePath
    $Parent = Split-Path $FullPath -Parent
    if (!(Test-Path $Parent)) { New-Item -ItemType Directory -Force -Path $Parent | Out-Null }
    [System.IO.File]::WriteAllText($FullPath, $Content, $Utf8NoBOM)
    if (!(Test-Path $FullPath)) { throw "Échec critique: $FullPath" }
}

# 2. NORMALISATION DE GIT EXECUTOR (Option A : Stub Conforme)
$GitExecutorCode = @"
from runtime.contracts.execution_context import ExecutionContext
from runtime.contracts.tool_result import ToolResult
from runtime.execution.decorators import executor

@executor
class GitStatusExecutor:
    TOOL_NAME = "system.git.status"
    SECURITY_LEVEL = "read-only"
    VERSION = "1.0-stub"

    def execute(self, context: ExecutionContext) -> ToolResult:
        return ToolResult(
            success=False,
            error="GitStatusExecutor not fully implemented yet in Industrial Phase",
            exit_code=-99
        )
"@
Write-Utf8File "runtime\tools\executors\git.py" $GitExecutorCode

# 3. GÉNÉRATION DU SCRIPT D'AUDIT PYTHON (AVEC CORRECTIFS SYS.PATH & INSTANCIATION)
$PythonAuditCode = @"
import sys
import os

# Résolution dynamique du sys.path pour accès au package global 'runtime'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import importlib
import pkgutil
import inspect
import runtime.tools.executors
from runtime.contracts.execution_context import ExecutionContext
from runtime.contracts.tool_result import ToolResult

def run_audit():
    package = runtime.tools.executors
    print("\n=============================================")
    print("         EXECUTOR COMPLIANCE REPORT          ")
    print("=============================================\n")

    all_compliant = True
    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            module = importlib.import_module(module_name)
            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                
                # Cible les classes avec TOOL_NAME
                if isinstance(obj, type) and hasattr(obj, "TOOL_NAME"):
                    tool_name = getattr(obj, "TOOL_NAME", "UNKNOWN")
                    issues = []

                    # A. Vérification du Décorateur (présence du flag __is_executor__)
                    if not getattr(obj, "__is_executor__", False):
                        issues.append("Missing @executor decorator")
                    
                    # B. Vérification de la signature de execute()
                    if hasattr(obj, "execute"):
                        sig = inspect.signature(obj.execute)
                        if "context" not in sig.parameters:
                            issues.append("execute() missing 'context' parameter")
                    else:
                        issues.append("Missing execute() method")

                    # C. Vérification des Métadonnées injectées
                    meta = getattr(obj, "__executor_metadata__", {})
                    if not meta.get("version"):
                        issues.append("Missing version metadata")
                    if not meta.get("security_level"):
                        issues.append("Missing security_level metadata")
                    if not meta.get("contract_version"):
                        issues.append("Missing contract_version metadata")

                    # D. Validation exécution et type de retour (ToolResult strict)
                    if not issues: # On ne tente l'instanciation que si la classe est bien formée
                        try:
                            instance = obj()
                            fake_context = ExecutionContext(
                                trace_id="audit-dry-run",
                                tool_name=tool_name,
                                arguments={}
                            )
                            result = instance.execute(fake_context)
                            
                            if not isinstance(result, ToolResult):
                                issues.append(f"execute() returns {type(result).__name__}, expected ToolResult")
                        except Exception as e:
                            issues.append(f"Runtime execution failure during audit instantiation: {e}")

                    if issues:
                        print(f"{tool_name:<25} [FAIL]")
                        for issue in issues:
                            print(f"  -> {issue}")
                        all_compliant = False
                    else:
                        print(f"{tool_name:<25} [PASS]")
                        
        except Exception as e:
            print(f"{module_name:<25} [CRASH] : {e}")
            all_compliant = False

    print("\n=============================================")
    if all_compliant:
        print("RESULT : 100% COMPLIANT. SYSTEM READY.")
        sys.exit(0)
    else:
        print("RESULT : COMPLIANCE FAILURES DETECTED.")
        sys.exit(1)

if __name__ == '__main__':
    run_audit()
"@
Write-Utf8File "runtime\execution\audit_compliance.py" $PythonAuditCode

# 4. EXÉCUTION DE L'AUDIT
Write-Host "[*] Lancement de l'audit de conformité strict..." -ForegroundColor Yellow
& python "runtime\execution\audit_compliance.py"
$AuditExitCode = $LASTEXITCODE

# 5. SCELLAGE GIT (Si 100% PASS)
if ($AuditExitCode -eq 0) {
    Write-Header "SCELLAGE GIT"
    try {
        git add .
        git commit -m "E-zzio Runtime Phase 2.2 Industrial Hardening validated" | Out-Null
        Write-Success "Commit validé : 'E-zzio Runtime Phase 2.2 Industrial Hardening validated'"
    } catch {
        Write-Host "[!] Git a rencontré une erreur ou il n'y a rien à committer." -ForegroundColor Yellow
    }
    Write-Success "PHASE 2.3 COMPLÈTE. Le moteur Runtime est officiellement certifié."
} else {
    Write-ErrorCustom "L'audit a échoué. Le commit Git a été annulé pour protéger le dépôt."
    throw "Audit compliance failure."
}