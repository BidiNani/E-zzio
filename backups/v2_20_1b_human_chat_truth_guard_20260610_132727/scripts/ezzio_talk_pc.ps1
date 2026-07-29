param(
    [Parameter(Mandatory=$true)]
    [string]$Text,

    [string]$Session = "pc",

    [string]$Task = "auto",

    [string]$Speed = "auto",

    [int]$Predict = 260
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    text = $Text
    session = $Session
    task = $Task
    speed = $Speed
    predict = $Predict
} | ConvertTo-Json -Depth 20

$res = Invoke-RestMethod "http://127.0.0.1:8000/api/chat/human" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 240 `
    -Body $body

[pscustomobject]@{
    ok = $res.ok
    session = $res.session
    command = $res.command
    model = $res.route.model
    task = $res.route.task
    deterministic = $res.deterministic
    elapsed_ms = $(if ($null -ne $res.human_chat_elapsed_ms) { $res.human_chat_elapsed_ms } else { $res.elapsed_ms })
    reply = $res.reply
}
