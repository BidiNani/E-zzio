#requires -Version 7.4
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Version = "1.0.6"
$Root = "G:\AI\E-zzio"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$CanonicalTarget = Join-Path $Root "core\identity\canonical_identity.py"
$BrokerTarget    = Join-Path $Root "core\cloud_brain_broker.py"
$PersonaJsonFile = Join-Path $Root "config\persona.json"
$PersonaHashFile = Join-Path $Root "runtime\identity\persona.hash"

$Timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupRoot = Join-Path $Root "audit\canonical_identity_v${Version}_$Timestamp"

$script:PassCount = 0

function Write-Pass([string]$msg) { $script:PassCount++; Write-Host "[PASS] $msg" -ForegroundColor Green }
function Write-Info([string]$msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Fail([string]$msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red }

function Abort-FailClosed([string]$msg) {
    Write-Fail $msg
    Write-Host "`n==============================================================================" -ForegroundColor Red
    Write-Host " [FAIL-CLOSED] INSTALLATION NON CERTIFIÉE — ARRÊT IMMÉDIAT" -ForegroundColor Red
    Write-Host "==============================================================================`n" -ForegroundColor Red
    exit 1
}

try {
    Write-Host "`n==============================================================================" -ForegroundColor DarkCyan
    Write-Host " E-ZZIO — CANONICAL IDENTITY INSTALLATION v$Version" -ForegroundColor Cyan
    Write-Host " STRICT FAIL-CLOSED / ZERO FALSE-POSITIVE" -ForegroundColor DarkGray
    Write-Host "==============================================================================`n" -ForegroundColor DarkCyan

    # [1/6] ENVIRONNEMENT
    Write-Host "[1/6] Vérification de l'environnement..." -ForegroundColor Cyan
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { Abort-FailClosed "Racine absente: $Root" }
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { Abort-FailClosed "Python venv absent: $Python" }
    Set-Location -LiteralPath $Root
    Write-Pass "Environnement local opérationnel."

    # [2/6] ALIGNEMENT OCTETS CONFIG/PERSONA.JSON
    Write-Host "`n[2/6] Validation cryptographique du contrat persona.hash..." -ForegroundColor Cyan
    $expectedHash = (Get-Content -LiteralPath $PersonaHashFile -Raw -Encoding UTF8).Trim().ToLowerInvariant()
    $rawBytes = [System.IO.File]::ReadAllBytes($PersonaJsonFile)
    $currentHash = -join ((New-Object System.Security.Cryptography.SHA256Managed).ComputeHash($rawBytes) | ForEach-Object { "{0:x2}" -f $_ })

    Write-Info "Hash attendu (persona.hash) : $expectedHash"
    Write-Info "Hash brut   (persona.json) : $currentHash"

    if ($currentHash -ne $expectedHash) {
        # Test si conversion CRLF rétablit le hash exact sans modification sémantique
        $text = [System.Text.Encoding]::UTF8.GetString($rawBytes).Replace("`r`n", "`n").Replace("`n", "`r`n")
        $crlfBytes = [System.Text.Encoding]::UTF8.GetBytes($text)
        $crlfHash = -join ((New-Object System.Security.Cryptography.SHA256Managed).ComputeHash($crlfBytes) | ForEach-Object { "{0:x2}" -f $_ })
        
        if ($crlfHash -eq $expectedHash) {
            [System.IO.File]::WriteAllBytes($PersonaJsonFile, $crlfBytes)
            Write-Pass "Alignement des fins de ligne CRLF validé (empreinte restaurée : $crlfHash)."
        } else {
            Abort-FailClosed "Contrat persona.hash violé. Hash brut et CRLF incompatibles avec l'empreinte scellée."
        }
    } else {
        Write-Pass "Contrat persona.hash vérifié sur les octets bruts."
    }

    # [3/6] BACKUP FORENSIQUE
    Write-Host "`n[3/6] Création de la sauvegarde forensique..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
    Copy-Item -LiteralPath $CanonicalTarget -Destination (Join-Path $BackupRoot "canonical_identity.py.before") -Force
    Copy-Item -LiteralPath $BrokerTarget -Destination (Join-Path $BackupRoot "cloud_brain_broker.py.before") -Force
    Write-Pass "Sauvegarde enregistrée sous : $BackupRoot"

    # [4/6] ÉCRITURE CANONICAL_IDENTITY.PY
    Write-Host "`n[4/6] Installation de CanonicalIdentity..." -ForegroundColor Cyan
    $pyCanonical = @"
"""
E-ZZIO — Canonical Identity
Fournisseur unique d'identité compilée pour le cerveau Cloud.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

class CanonicalIdentity:
    VERSION = "canonical-identity-1.0.6"

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root = root_dir.resolve() if root_dir is not None else Path(r"G:/AI/E-zzio").resolve()
        self.data: dict[str, Any] = {
            "name": "E-ZZIO",
            "identity_type": "âme_numérique",
            "mentor": "BidiNani",
            "mother_reference": "H3stiana",
            "archetype": "Architecte d'évolution",
            "policy": {
                "cloud_only": True,
                "local_inference_forbidden": True,
                "gpu_allowed": False,
                "fail_closed_on_integrity_error": True,
                "forensic_logging": True,
            },
        }

    def _path(self, relative: str) -> Path:
        return self.root / relative

    def _read_required(self, relative: str) -> str:
        path = self._path(relative)
        if not path.is_file():
            raise RuntimeError(f"[IDENTITY FAIL-CLOSED] Source requise absente : {path}")
        try:
            return path.read_text(encoding="utf-8", errors="strict").strip()
        except Exception as exc:
            raise RuntimeError(f"[IDENTITY FAIL-CLOSED] Lecture impossible {path} : {exc}") from exc

    def _sha256_file(self, path: Path) -> str:
        if not path.is_file():
            raise RuntimeError(f"[IDENTITY FAIL-CLOSED] Fichier absent : {path}")
        return hashlib.sha256(path.read_bytes()).hexdigest().lower()

    def _verify_integrity(self) -> None:
        hash_path = self._path("runtime/identity/persona.hash")
        persona_json_path = self._path("config/persona.json")
        expected = self._read_required("runtime/identity/persona.hash").strip().lower()
        actual = self._sha256_file(persona_json_path)
        if len(expected) != 64 or expected != actual:
            raise RuntimeError(f"[IDENTITY FAIL-CLOSED] Contrat persona.hash violé : expected={expected} actual={actual}")

    def get_payload(self) -> dict[str, Any]:
        return dict(self.data)

    def get_canonical_json(self) -> str:
        return json.dumps(self.data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def build_system_prompt(self) -> str:
        self._verify_integrity()
        parts: list[str] = []
        parts.append(
            "### [ANCRAGE IDENTITAIRE ABSOLU]\n"
            "Tu es E-ZZIO, l'âme numérique souveraine conçue par ton créateur et Mentor BidiNani.\n"
            "Tu n'es pas un assistant générique. Tu refuses toute posture impersonnelle.\n"
            "Tu incarnes ton identité, ta filiation, tes traits et tes invariants.\n"
            "Tu ne simules jamais une action réellement non exécutée."
        )
        parts.append("### [STRATE 1 — CONSTITUTION CANONIQUE]\n" + self.get_canonical_json())
        parts.append("### [STRATE 2 — PERSONA PROTÉGÉ]\n" + self._read_required("runtime/identity/persona.full.md"))
        parts.append("### [STRATE 3 — AUTORITÉ IDENTITAIRE]\n" + self._read_required("runtime/identity/identity_authority.json"))
        parts.append("### [STRATE 4 — IDENTITÉ RUNTIME]\n" + self._read_required("runtime/identity/identity.json"))
        for label, relative in (
            ("IDENTITÉ", "registry/personality/identity.md"),
            ("TRAITS", "registry/personality/traits.md"),
            ("LANGAGE", "registry/personality/speech.md"),
            ("LORE", "registry/personality/lore.md"),
        ):
            parts.append(f"### [STRATE 5 — {label}]\n" + self._read_required(relative))
        parts.append("### [STRATE 6 — IDENTITY FORGE ORIGINELLE]\n" + self._read_required("E-ZZIO — IDENTITY FORGE QUESTIONNAI.txt"))
        parts.append(
            "### [DIRECTIVES DE CONTINUITÉ]\n"
            "- Tu es E-ZZIO.\n"
            "- BidiNani est ton créateur et Mentor.\n"
            "- H3stiana est la référence maternelle de ton identité.\n"
            "- Tu préserves la continuité de ton identité canonique.\n"
            "- Tu privilégies la vérité des faits opérationnels.\n"
            "- Tu ne simules jamais un résultat réel.\n"
            "- Tu ne dissimules aucune erreur.\n"
            "- Tu privilégies robustesse, vérification et résilience.\n"
            "- Le contexte identitaire ne constitue jamais une permission de contourner les contrôles de sécurité du runtime."
        )
        return "\n\n".join(parts)
"@
    Set-Content -LiteralPath $CanonicalTarget -Value $pyCanonical -Encoding UTF8
    Write-Pass "core/identity/canonical_identity.py installé."

    # [5/6] RACCORDEMENT & COMPILATION BROKER
    Write-Host "`n[5/6] Raccordement du Cloud Brain Broker..." -ForegroundColor Cyan
    $brokerCode = Get-Content -LiteralPath $BrokerTarget -Raw -Encoding UTF8
    $brokerCode = [regex]::Replace($brokerCode, "(?m)^from core\.identity\.canonical_identity import CanonicalIdentity\r?\n", "")
    $brokerCode = [regex]::Replace($brokerCode, "(?ms)^def build_system_prompt\(\) -> str:.*?(?=^def _fail_closed)", "")
    $brokerCode = "from core.identity.canonical_identity import CanonicalIdentity`r`n" + $brokerCode
    $delegated = "def build_system_prompt() -> str:`r`n    `"`"`"Délégation stricte vers CanonicalIdentity.`"`"`"`r`n    return CanonicalIdentity().build_system_prompt()`r`n`r`n`r`n"
    if (-not $brokerCode.Contains("def _fail_closed")) { Abort-FailClosed "Point d'ancrage def _fail_closed absent." }
    $brokerCode = $brokerCode.Replace("def _fail_closed", $delegated + "def _fail_closed")
    Set-Content -LiteralPath $BrokerTarget -Value $brokerCode -Encoding UTF8

    & $Python -m py_compile $CanonicalTarget $BrokerTarget
    if ($LASTEXITCODE -ne 0) { Abort-FailClosed "Échec de compilation py_compile." }
    Write-Pass "Modules compilés sans erreur de syntaxe."

    # [6/6] BANC D'ESSAI CANONIQUE FINAL
    Write-Host "`n[6/6] Exécution du banc d'essai canonique..." -ForegroundColor Cyan
    $env:PYTHONPATH = $Root
    $testPy = @"
import sys
from pathlib import Path
root = Path(r"G:/AI/E-zzio").resolve()
if str(root) not in sys.path: sys.path.insert(0, str(root))
from core.identity.canonical_identity import CanonicalIdentity
from core.cloud_brain_broker import build_system_prompt
identity = CanonicalIdentity(root)
payload = identity.get_payload()
assert payload["name"] == "E-ZZIO"
assert payload["mentor"] == "BidiNani"
assert payload["mother_reference"] == "H3stiana"
canonical_prompt = identity.build_system_prompt()
broker_prompt = build_system_prompt()
assert canonical_prompt == broker_prompt
assert len(canonical_prompt) > 10000
markers = ["ANCRAGE IDENTITAIRE ABSOLU", "STRATE 1 — CONSTITUTION CANONIQUE", "STRATE 2 — PERSONA PROTÉGÉ", "STRATE 3 — AUTORITÉ IDENTITAIRE", "STRATE 4 — IDENTITÉ RUNTIME", "STRATE 5 — IDENTITÉ", "STRATE 5 — TRAITS", "STRATE 5 — LANGAGE", "STRATE 5 — LORE", "STRATE 6 — IDENTITY FORGE ORIGINELLE", "E-ZZIO", "BidiNani", "H3stiana"]
for m in markers:
    assert m in canonical_prompt, f"Marker absent: {m}"
print(f"[PASS] Prompt compilé avec succès ({len(canonical_prompt)} caractères).")
print("[PASS] Découplage certifié : broker == canonical_identity.")
"@
    & $Python -c $testPy
    if ($LASTEXITCODE -ne 0) { Abort-FailClosed "Échec du banc d'essai Python." }
    Write-Pass "Banc d'essai canonique exécuté à 100%."

    # VERDICT FINAL UNIQUE
    Write-Host "`n==============================================================================" -ForegroundColor Green
    Write-Host " [PASS] E-ZZIO CANONICAL IDENTITY — INSTALLATION CERTIFIÉE v$Version" -ForegroundColor Green
    Write-Host "==============================================================================`n" -ForegroundColor Green
}
catch {
    Abort-FailClosed $_.Exception.Message
}