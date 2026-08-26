$ErrorActionPreference = 'Stop'
$ProjectRoot = 'G:\AI\E-zzio'
Set-Location -LiteralPath $ProjectRoot

$BootFile   = Join-Path $ProjectRoot "runtime\kernel\boot.py"
$BackupFile = Join-Path $ProjectRoot "runtime\kernel\boot.py.bak_v4258_pidfix"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO V4.2.5.8 - FIX os.kill(pid,0) -> CTRL_C_EVENT WINDOWS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $BootFile)) {
    throw "boot.py introuvable : $BootFile"
}

Copy-Item -LiteralPath $BootFile -Destination $BackupFile -Force
Write-Host "[OK] Backup cree : $BackupFile" -ForegroundColor Green

$content = [System.IO.File]::ReadAllText($BootFile)
$lines = $content -split "`r?`n"

# ------------------------------------------------------------
# 1. Insertion du helper _pid_is_alive() avant "class EzzioBootloader"
#    (uniquement si pas deja present)
# ------------------------------------------------------------

if ($content -notmatch '_pid_is_alive') {

    $classIndex = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^class EzzioBootloader') {
            $classIndex = $i
            break
        }
    }

    if ($classIndex -lt 0) {
        throw "class EzzioBootloader introuvable dans boot.py"
    }

    $helper = @(
        ''
        'def _pid_is_alive(pid: int) -> bool:'
        '    """'
        '    Verifie si un PID est vivant sans utiliser os.kill(pid, 0).'
        '    Sous Windows, Python mappe le signal 0 sur CTRL_C_EVENT et'
        '    appelle GenerateConsoleCtrlEvent(0, pid), ce qui envoie un'
        '    vrai Ctrl+C a tous les process du meme groupe console au'
        '    lieu de verifier simplement l existence du PID. Utiliser'
        '    OpenProcess evite cet effet de bord.'
        '    """'
        '    if os.name == "nt":'
        '        import ctypes'
        '        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000'
        '        handle = ctypes.windll.kernel32.OpenProcess('
        '            PROCESS_QUERY_LIMITED_INFORMATION, False, pid'
        '        )'
        '        if handle:'
        '            ctypes.windll.kernel32.CloseHandle(handle)'
        '            return True'
        '        return False'
        '    else:'
        '        try:'
        '            os.kill(pid, 0)'
        '            return True'
        '        except OSError:'
        '            return False'
        ''
    )

    $before = $lines[0..($classIndex - 1)]
    $after  = $lines[$classIndex..($lines.Count - 1)]

    $lines = @() + $before + $helper + $after

    Write-Host "[OK] Helper _pid_is_alive() insere avant la classe." -ForegroundColor Green
}
else {
    Write-Host "[INFO] _pid_is_alive() deja present, pas de reinsertion." -ForegroundColor Yellow
}

# ------------------------------------------------------------
# 2. Remplacement de l'appel os.kill(old_pid, 0) par _pid_is_alive(old_pid)
#    dans _acquire_process_lock
# ------------------------------------------------------------

$content = $lines -join "`r`n"

$oldBlock = @'
                    try:
                        os.kill(old_pid, 0)
                        return False

                    except OSError:
                        try:
                            os.remove(self.lock_path)
                        except (FileNotFoundError, OSError):
                            pass
'@

$newBlock = @'
                    if _pid_is_alive(old_pid):
                        return False
                    else:
                        try:
                            os.remove(self.lock_path)
                        except (FileNotFoundError, OSError):
                            pass
'@

if ($content -match [regex]::Escape('os.kill(old_pid, 0)')) {

    if ($content -match [regex]::Escape($oldBlock)) {
        $content = $content.Replace($oldBlock, $newBlock)
        Write-Host "[OK] os.kill(old_pid, 0) remplace par _pid_is_alive(old_pid)." -ForegroundColor Green
    }
    else {
        Write-Warning "Le bloc exact attendu autour de os.kill(old_pid, 0) n'a pas ete retrouve tel quel."
        Write-Warning "Remplacement minimal de l'appel uniquement (verifier manuellement le resultat)."
        $content = $content -replace [regex]::Escape('os.kill(old_pid, 0)'), '_pid_is_alive(old_pid)'
        $content = $content -replace '(?m)^\s*_pid_is_alive\(old_pid\)\s*$', '                    if not _pid_is_alive(old_pid):'
    }
}
else {
    Write-Host "[INFO] Aucun appel os.kill(old_pid, 0) trouve (deja patche ?)." -ForegroundColor Yellow
}

[System.IO.File]::WriteAllText($BootFile, $content, [System.Text.UTF8Encoding]::new($false))

# ------------------------------------------------------------
# 3. Compilation
# ------------------------------------------------------------

Write-Host ""
Write-Host "=== COMPILATION boot.py ===" -ForegroundColor Cyan

& "G:\Python312\python.exe" -m py_compile $BootFile

if ($LASTEXITCODE -ne 0) {
    throw "Compilation boot.py echouee - restaurer depuis $BackupFile si besoin"
}

Write-Host "[SUCCESS] boot.py compile." -ForegroundColor Green

# ------------------------------------------------------------
# 4. Verification rapide du contenu patche
# ------------------------------------------------------------

Write-Host ""
Write-Host "=== VERIFICATION ===" -ForegroundColor Cyan
Select-String -LiteralPath $BootFile -Pattern '_pid_is_alive|os\.kill\(old_pid' |
    ForEach-Object { Write-Host $_.Line -ForegroundColor Cyan }

# ------------------------------------------------------------
# 5. Re-run complet de la chaine de validation
# ------------------------------------------------------------

New-Item -ItemType Directory -Force -Path ".\tmp" | Out-Null

$Adversarial = (Get-ChildItem -Path $ProjectRoot -Filter "test_v424_adversarial.py" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
if (-not $Adversarial) {
    throw "test_v424_adversarial.py introuvable sous $ProjectRoot"
}

Write-Host ""
Write-Host ">>> TEST ADVERSARIAL APRES PATCH" -ForegroundColor Yellow

Remove-Item -LiteralPath ".\runtime\kernel\boot.lock" -Force -ErrorAction SilentlyContinue

& "G:\Python312\python.exe" -u $Adversarial
$v424Exit = $LASTEXITCODE

Write-Host ""
Write-Host "ExitCode adversarial : $v424Exit"

if ($v424Exit -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] V4.2.4 ADVERSARIAL VALIDE - plus de KeyboardInterrupt." -ForegroundColor Green
    Write-Host ">>> MASTER CERTIFICATION" -ForegroundColor Cyan

    Remove-Item -LiteralPath ".\runtime\kernel\boot.lock" -Force -ErrorAction SilentlyContinue

    & ".\certify_v4.ps1"
}
else {
    Write-Error "Echec test_v424_adversarial.py (code $v424Exit) meme apres le patch. Restaurer $BackupFile et analyser."
    exit $v424Exit
}
