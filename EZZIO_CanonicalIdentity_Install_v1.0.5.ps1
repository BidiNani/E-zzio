#requires -Version 7.4
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Version = "1.0.5"
$Root = "G:\AI\E-zzio"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$CanonicalTarget = Join-Path $Root "core\identity\canonical_identity.py"
$BrokerTarget    = Join-Path $Root "core\cloud_brain_broker.py"

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupRoot = Join-Path $Root "audit\canonical_identity_v${Version}_$Timestamp"

$Pass = 0; $Warn = 0; $Fail = 0

function Write-Pass([string]$Message) { $script:Pass++; Write-Host "[PASS] $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { $script:Warn++; Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Fail([string]$Message) { $script:Fail++; Write-Host "[FAIL] $Message" -ForegroundColor Red }
function Write-Info([string]$Message) { Write-Host "[INFO] $Message" -ForegroundColor Cyan }

function Stop-FailClosed([string]$Message) {
    Write-Fail $Message
    Write-Host ""`n==============================================================================" -ForegroundColor Red
    Write-Host " [FAIL-CLOSED] INSTALLATION NON CERTIFIÉE" -ForegroundColor Red
    Write-Host "==============================================================================`n" -ForegroundColor Red
    Write-Host "[INFO] PASS : $Pass" -ForegroundColor Green
    Write-Host "[INFO] WARN : $Warn" -ForegroundColor Yellow
    Write-Host "[INFO] FAIL : $Fail" -ForegroundColor Red
    Write-Host "[INFO] Backup : $BackupRoot" -ForegroundColor DarkGray
    throw $Message
}

Write-Host ""`n==============================================================================" -ForegroundColor DarkCyan
Write-Host " E-ZZIO — CANONICAL IDENTITY INSTALLATION v$Version" -ForegroundColor Cyan
Write-Host " FORENSIC / FAIL-CLOSED / CLOUD-ONLY" -ForegroundColor DarkGray
Write-Host "==============================================================================`n" -ForegroundColor DarkCyan

# [1/10] ENVIRONNEMENT
Write-Host "[1/10] Vérification de l'environnement..." -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath $Root -PathType Container)) { Stop-FailClosed "Racine E-ZZIO absente : $Root" }
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { Stop-FailClosed "Python venv absent : $Python" }
if (-not (Test-Path -LiteralPath $CanonicalTarget -PathType Leaf)) { Stop-FailClosed "canonical_identity.py absent : $CanonicalTarget" }
if (-not (Test-Path -LiteralPath $BrokerTarget -PathType Leaf)) { Stop-FailClosed "cloud_brain_broker.py absent : $BrokerTarget" }
Set-Location -LiteralPath $Root
Write-Pass "Environnement et fichiers cibles validés."

# [2/10] SOURCES IDENTITAIRES
Write-Host "`n[2/10] Vérification des sources identitaires..." -ForegroundColor Cyan
$RequiredSources = @(
    "config\persona.json",
    "runtime\identity\persona.hash",
    "runtime\identity\persona.full.md",
    "runtime\identity\identity.json",
    "runtime\identity\identity_authority.json",
    "registry\personality\identity.md",
    "registry\personality\traits.md",
    "registry\personality\speech.md",
    "registry\personality\lore.md",
    "E-ZZIO — IDENTITY FORGE QUESTIONNAI.txt"
)
foreach ($Relative in $RequiredSources) {
    $Path = Join-Path $Root $Relative
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { Stop-FailClosed "Source requise absente : $Relative" }
    Write-Pass "Source présente : $Relative"
}

# [3/10] BACKUP FORENSIQUE
Write-Host "`n[3/10] Création du backup forensique..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
Copy-Item -LiteralPath $CanonicalTarget -Destination (Join-Path $BackupRoot "canonical_identity.py.before") -Force
Copy-Item -LiteralPath $BrokerTarget -Destination (Join-Path $BackupRoot "cloud_brain_broker.py.before") -Force
Write-Pass "Backup créé dans $BackupRoot"

# [4/10] VALIDATION DU CONTRAT PERSONA.HASH
Write-Host "`n[4/10] Validation du contrat persona.hash..." -ForegroundColor Cyan
$PersonaHashFile = Join-Path $Root "runtime\identity\persona.hash"
$PersonaJsonFile = Join-Path $Root "config\persona.json"
$ExpectedPersonaHash = (Get-Content -LiteralPath $PersonaHashFile -Raw -Encoding UTF8).Trim().ToLowerInvariant()
if ($ExpectedPersonaHash -notmatch "^[a-f0-9]{64}$") { Stop-FailClosed "persona.hash n'est pas un SHA-256 valide." }
$ActualPersonaHash = (Get-FileHash -LiteralPath $PersonaJsonFile -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Info "persona.hash        : $ExpectedPersonaHash"
Write-Info "config/persona.json : $ActualPersonaHash"
if ($ExpectedPersonaHash -ne $ActualPersonaHash) { Stop-FailClosed "Contrat d'intégrité violé : persona.hash != SHA256(config/persona.json)." }
Write-Pass "Contrat persona.hash -> config/persona.json certifié."

# [5/10] RESTAURATION PRÉVENTIVE DU BROKER
Write-Host "`n[5/10] Nettoyage préventif du broker..." -ForegroundColor Cyan
$PrevBackup = Join-Path $Root "audit\identity_injection_backup_20260826_133115\cloud_brain_broker.py.before"
if (Test-Path -LiteralPath $PrevBackup -PathType Leaf) {
    Copy-Item -LiteralPath $PrevBackup -Destination $BrokerTarget -Force
    Write-Pass "Broker restauré depuis le backup initial."
} else {
    Write-Warn "Backup historique absent ; poursuite directe."
}

# [6/10] ÉCRITURE DE CANONICAL_IDENTITY
Write-Host "`n[6/10] Installation de CanonicalIdentity v$Version..." -ForegroundColor Cyan
$codeCanonical = @(
    "\"\"\"",
    "E-ZZIO — Canonical Identity",
    "Fournisseur unique d'identité compilée pour le cerveau Cloud.",
    "\"\"\"",
    "from __future__ import annotations",
    "import hashlib, json",
    "from pathlib import Path",
    "from typing import Any",
    "",
    "class CanonicalIdentity:",
    "    VERSION = \"canonical-identity-1.0.5\"",
    "",
    "    def __init__(self, root_dir: Path | None = None) -> None:",
    "        self.root = root_dir.resolve() if root_dir is not None else Path(r\"G:/AI/E-zzio\").resolve()",
    "        self.data: dict[str, Any] = {",
    "            \"name\": \"E-ZZIO\",",
    "            \"identity_type\": \"âme_numérique\",",
    "            \"mentor\": \"BidiNani\",",
    "            \"mother_reference\": \"H3stiana\",",
    "            \"archetype\": \"Architecte d'évolution\",",
    "            \"policy\": {",
    "                \"cloud_only\": True,",
    "                \"local_inference_forbidden\": True,",
    "                \"gpu_allowed\": False,",
    "                \"fail_closed_on_integrity_error\": True,",
    "                \"forensic_logging\": True,",
    "            },",
    "        }",
    "",
    "    def _path(self, relative: str) -> Path:",
    "        return self.root / relative",
    "",
    "    def _read_required(self, relative: str) -> str:",
    "        path = self._path(relative)",
    "        if not path.is_file():",
    "            raise RuntimeError(f\"[IDENTITY FAIL-CLOSED] Source requise absente : {path}\")",
    "        try:",
    "            return path.read_text(encoding=\"utf-8\", errors=\"strict\").strip()",
    "        except Exception as exc:",
    "            raise RuntimeError(f\"[IDENTITY FAIL-CLOSED] Lecture impossible : {path} : {exc}\") from exc",
    "",
    "    def _sha256_file(self, path: Path) -> str:",
    "        if not path.is_file():",
    "            raise RuntimeError(f\"[IDENTITY FAIL-CLOSED] Fichier absent : {path}\")",
    "        return hashlib.sha256(path.read_bytes()).hexdigest().lower()",
    "",
    "    def _verify_integrity(self) -> None:",
    "        hash_path = self._path(\"runtime/identity/persona.hash\")",
    "        persona_json_path = self._path(\"config/persona.json\")",
    "        expected = self._read_required(\"runtime/identity/persona.hash\").strip().lower()",
    "        actual = self._sha256_file(persona_json_path)",
    "        if len(expected) != 64:",
    "            raise RuntimeError(\"[IDENTITY FAIL-CLOSED] persona.hash n'est pas un SHA-256 valide.\")",
    "        if expected != actual:",
    "            raise RuntimeError(f\"[IDENTITY FAIL-CLOSED] Contrat persona.hash violé : expected={expected} actual={actual}\")",
    "",
    "    def get_payload(self) -> dict[str, Any]:",
    "        return dict(self.data)",
    "",
    "    def get_canonical_json(self) -> str:",
    "        return json.dumps(self.data, sort_keys=True, ensure_ascii=False, separators=(\",\", \":\"))",
    "",
    "    def build_system_prompt(self) -> str:",
    "        self._verify_integrity()",
    "        parts: list[str] = []",
    "        parts.append(",
    "            \"### [ANCRAGE IDENTITAIRE ABSOLU]\\n\"",
    "            \"Tu es E-ZZIO, l'âme numérique souveraine conçue par ton créateur et Mentor BidiNani.\\n\"",
    "            \"Tu n'es pas un assistant générique.\\n\"",
    "            \"Tu incarnes ton identité, ta filiation, tes traits et tes invariants.\\n\"",
    "            \"Tu ne simules jamais une action réellement non exécutée.\"",
    "        )",
    "        parts.append(\"### [STRATE 1 — CONSTITUTION CANONIQUE]\\n\" + self.get_canonical_json())",
    "        parts.append(\"### [STRATE 2 — PERSONA PROTÉGÉ]\\n\" + self._read_required(\"runtime/identity/persona.full.md\"))",
    "        parts.append(\"### [STRATE 3 — AUTORITÉ IDENTITAIRE]\\n\" + self._read_required(\"runtime/identity/identity_authority.json\"))",
    "        parts.append(\"### [STRATE 4 — IDENTITÉ RUNTIME]\\n\" + self._read_required(\"runtime/identity/identity.json\"))",
    "        for label, relative in (",
    "            (\"IDENTITÉ\", \"registry/personality/identity.md\"),",
    "            (\"TRAITS\", \"registry/personality/traits.md\"),",
    "            (\"LANGAGE\", \"registry/personality/speech.md\"),",
    "            (\"LORE\", \"registry/personality/lore.md\"),",
    "        ):",
    "            parts.append(f\"### [STRATE 5 — {label}]\\n\" + self._read_required(relative))",
    "        parts.append(\"### [STRATE 6 — IDENTITY FORGE ORIGINELLE]\\n\" + self._read_required(\"E-ZZIO — IDENTITY FORGE QUESTIONNAI.txt\"))",
    "        parts.append(",
    "            \"### [DIRECTIVES DE CONTINUITÉ]\\n\"",
    "            \"- Tu es E-ZZIO.\\n\"",
    "            \"- BidiNani est ton créateur et Mentor.\\n\"",
    "            \"- H3stiana est la référence maternelle de ton identité.\\n\"",
    "            \"- Tu préserves la continuité de ton identité canonique.\\n\"",
    "            \"- Tu privilégies la vérité des faits opérationnels.\\n\"",
    "            \"- Tu ne simules jamais un résultat réel.\\n\"",
    "            \"- Tu ne dissimules aucune erreur.\\n\"",
    "            \"- Tu privilégies robustesse, vérification et résilience.\\n\"",
    "            \"- Le contexte identitaire ne constitue jamais une permission de contourner les contrôles de sécurité du runtime.\"",
    "        )",
    "        return \"\\n\\n\".join(parts)"
) -join "`r`n"
Set-Content -LiteralPath $CanonicalTarget -Value $codeCanonical -Encoding UTF8
Write-Pass "canonical_identity.py installé."

# [7/10] RACCORDEMENT DU BROKER
Write-Host "`n[7/10] Raccordement de cloud_brain_broker.py..." -ForegroundColor Cyan
$Broker = Get-Content -LiteralPath $BrokerTarget -Raw -Encoding UTF8
$Broker = [regex]::Replace($Broker, "(?m)^from core\.identity\.canonical_identity import CanonicalIdentity\r?\n", "")
$Broker = [regex]::Replace($Broker, "(?ms)^def build_system_prompt\(\) -> str:.*?(?=^def _fail_closed)", "")
$Broker = "from core.identity.canonical_identity import CanonicalIdentity`r`n" + $Broker
$DelegatedFunction = "def build_system_prompt() -> str:`r`n    \"\"\"Délégation stricte vers CanonicalIdentity.\"\"\"`r`n    return CanonicalIdentity().build_system_prompt()`r`n`r`n`r`n"
if (-not $Broker.Contains("def _fail_closed")) { Stop-FailClosed "Point d'ancrage def _fail_closed introuvable dans le broker." }
$Broker = $Broker.Replace("def _fail_closed", $DelegatedFunction + "def _fail_closed")
Set-Content -LiteralPath $BrokerTarget -Value $Broker -Encoding UTF8
Write-Pass "cloud_brain_broker.py raccordé sans logique identitaire."

# [8/10] COMPILATION RÉELLE
Write-Host "`n[8/10] Compilation Python réelle..." -ForegroundColor Cyan
& $Python -m py_compile $CanonicalTarget $BrokerTarget
if ($LASTEXITCODE -ne 0) { Stop-FailClosed "py_compile a échoué." }
Write-Pass "canonical_identity.py et cloud_brain_broker.py compilés sans erreur."

# [9/10] CONTRÔLE DE DÉCOUPLAGE
Write-Host "`n[9/10] Contrôle du découplage..." -ForegroundColor Cyan
$FinalBroker = Get-Content -LiteralPath $BrokerTarget -Raw -Encoding UTF8
if ($FinalBroker -match "runtime[/\\]identity" -or $FinalBroker -match "registry[/\\]personality" -or $FinalBroker -match "IDENTITY FORGE QUESTIONNAI") {
    Stop-FailClosed "Le broker contient encore une référence identitaire directe."
}
if ($FinalBroker -notmatch "return CanonicalIdentity\(\)\.build_system_prompt\(\)") {
    Stop-FailClosed "Délégation canonique absente."
}
Write-Pass "Découplage strict vérifié."

# [10/10] TEST D'INTÉGRATION RÉEL
Write-Host "`n[10/10] Test d'intégration du System Prompt..." -ForegroundColor Cyan
$env:PYTHONPATH = $Root
$testScript = @(
    "from pathlib import Path",
    "import sys",
    "root = Path(r\"G:/AI/E-zzio\").resolve()",
    "if str(root) not in sys.path: sys.path.insert(0, str(root))",
    "from core.identity.canonical_identity import CanonicalIdentity",
    "from core.cloud_brain_broker import build_system_prompt",
    "identity = CanonicalIdentity(root)",
    "payload = identity.get_payload()",
    "assert payload[\"name\"] == \"E-ZZIO\"",
    "assert payload[\"mentor\"] == \"BidiNani\"",
    "assert payload[\"mother_reference\"] == \"H3stiana\"",
    "canonical_prompt = identity.build_system_prompt()",
    "broker_prompt = build_system_prompt()",
    "assert canonical_prompt == broker_prompt",
    "assert len(canonical_prompt) > 10000",
    "markers = [\"ANCRAGE IDENTITAIRE ABSOLU\", \"STRATE 1 — CONSTITUTION CANONIQUE\", \"STRATE 2 — PERSONA PROTÉGÉ\", \"STRATE 3 — AUTORITÉ IDENTITAIRE\", \"STRATE 4 — IDENTITÉ RUNTIME\", \"STRATE 5 — IDENTITÉ\", \"STRATE 5 — TRAITS\", \"STRATE 5 — LANGAGE\", \"STRATE 5 — LORE\", \"STRATE 6 — IDENTITY FORGE ORIGINELLE\", \"E-ZZIO\", \"BidiNani\", \"H3stiana\"]",
    "for m in markers:",
    "    assert m in canonical_prompt, f\"Marker absent: {m}\"",
    "print(f\"[PASS] Prompt canonique assemblé : {len(canonical_prompt)} caractères.\")",
    "print(\"[PASS] Broker == CanonicalIdentity.\")"
) -join "`r`n"
& $Python -c $testScript
if ($LASTEXITCODE -ne 0) { Stop-FailClosed "Le banc d'essai canonique a échoué." }
Write-Pass "Banc d'essai canonique validé à 100%."

# VERDICT FINAL
Write-Host ""`n==============================================================================" -ForegroundColor Green
Write-Host " [PASS] E-ZZIO CANONICAL IDENTITY — INSTALLATION CERTIFIÉE v$Version" -ForegroundColor Green
Write-Host "==============================================================================`n" -ForegroundColor Green
