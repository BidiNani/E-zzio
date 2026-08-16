param(
    [Parameter(Mandatory=$true)]
    [string]$Text,

    [string]$Session = "pc"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    text = $Text
    session = $Session
} | ConvertTo-Json -Depth 20

$res = Invoke-RestMethod "http://127.0.0.1:8001/api/chat/commander" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 240 `
    -Body $body

[pscustomobject]@{
    ok = $res.ok
    version = $res.version
    session = $res.session
    mode = $res.mode
    action = $res.action
    requires_confirmation = $res.requires_confirmation
    proposal_id = $res.proposal.id
    elapsed_ms = $res.elapsed_ms
    reply = $res.reply
}

