$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$api = Invoke-RestMethod "http://127.0.0.1:8000/maintenance/audit" -Method GET -TimeoutSec 180

$scriptErrors = @()

Get-ChildItem "G:\AI\E-zzio\scripts" -Filter "*.ps1" -File -ErrorAction SilentlyContinue | ForEach-Object {
    $errors = $null
    $content = Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8

    $null = [System.Management.Automation.PSParser]::Tokenize(
        $content,
        [ref]$errors
    )

    if ($errors -and $errors.Count -gt 0) {
        $scriptErrors += [pscustomobject]@{
            path = $_.FullName
            message = $errors[0].Message
        }
    }
}

[pscustomobject]@{
    ok = ($api.ok -and $scriptErrors.Count -eq 0)
    python_checked = $api.checked_count
    python_bad = $api.bad_count
    powershell_bad = $scriptErrors.Count
    bad = $api.bad
    ps_errors = $scriptErrors
}
