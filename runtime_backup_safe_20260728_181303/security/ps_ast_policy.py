import base64
import json

class PowerShellASTPolicy:
    """
    Génère un Wrapper PowerShell qui utilise System.Management.Automation.Language.Parser
    pour analyser l'Arbre Syntaxique (AST) de la commande cible avant exécution, 
    contournant ainsi les attaques par Alias ou Injections.
    """
    
    @staticmethod
    def build_secure_wrapper(target_command: str, allowed_commands: list, blocked_commands: list) -> list:
        # Script PowerShell injecté qui analyse l'AST de la commande cible
        ast_script = f"""
        $cmd = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{base64.b64encode(target_command.encode('utf-8')).decode('utf-8')}'))
        $allowed = {json.dumps(allowed_commands)}
        $blocked = {json.dumps(blocked_commands)}

        # 1. Purge absolue des Alias pour éviter 'gci' -> 'Get-ChildItem'
        Remove-Item Alias:* -Force -ErrorAction SilentlyContinue

        # 2. Parse de l'AST
        $tokens = $null
        $errors = $null
        $ast = [System.Management.Automation.Language.Parser]::ParseInput($cmd, [ref]$tokens, [ref]$errors)

        if ($errors.Count -gt 0) {{
            Write-Error "Syntaxe invalide ou tentative d'injection refusée."
            exit 1
        }}

        # 3. Analyse des nœuds CommandAst
        $commands = $ast.FindAll({{ $args[0] -is [System.Management.Automation.Language.CommandAst] }}, $true)
        foreach ($c in $commands) {{
            $cmdName = $c.GetCommandName().ToLower()
            if ([string]::IsNullOrWhiteSpace($cmdName)) {{ continue }}
            
            # Blocklist stricte
            foreach ($b in $blocked) {{
                if ($cmdName -eq $b.ToLower()) {{
                    Write-Error "DENIED BY AST POLICY: Commande interdite '$cmdName'"
                    exit 1
                }}
            }}
            
            # Allowlist stricte
            $isAllowed = $false
            foreach ($a in $allowed) {{
                if ($cmdName -eq $a.ToLower()) {{ $isAllowed = $true; break }}
            }}
            if (-not $isAllowed) {{
                Write-Error "DENIED BY AST POLICY: Commande non autorisée '$cmdName'"
                exit 1
            }}
        }}

        # 4. Exécution confinée si l'AST est valide
        Invoke-Expression $cmd
        """
        
        b64_script = base64.b64encode(ast_script.encode('utf-16-le')).decode('utf-8')
        return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", b64_script]