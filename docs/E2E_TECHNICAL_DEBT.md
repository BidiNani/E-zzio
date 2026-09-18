# E2E Technical Debt - Brave 153+ CDP Crash

## Statut
ACTIF - Tests E2E desactives

## Symptome

Brave 153+ (Build 153.1.95.104) sur Windows crashe immediatement
au lancement avec --remote-debugging-port, quelle que soit la
combinaison de flags testee.

### Codes d'erreur observes

- 0xC0000005 = STATUS_ACCESS_VIOLATION
- 3221225477 (decimal, equivalent)
- -1073741819 (signe, equivalent)

### Comportement

- OK : Brave demarre normalement (usage perso)
- KO : Brave crashe avec --remote-debugging-port=XXXX
- KO : Crash identique en --headless=new, --headless, ou headed
- KO : Crash identique avec --no-sandbox, --disable-gpu, etc.
- KO : Crash identique via Python subprocess.Popen et PowerShell Start-Process
- KO : Crash identique depuis un working dir neutre (C:\Windows\Temp)

### Tests effectues (2026-09-19)

8 combinaisons de flags -> 8 echecs.
5 tests d'environnement -> echecs.

### Hypotheses ecartees

- Flags incorrects : teste 8 combinaisons
- Conflit de profil : profil tempdir isole
- Conflit de port : ports dynamiques
- Conflit Python/DLL : teste depuis dossier neutre
- Windows Defender / ASR : aucune regle active
- Zone.Identifier : absent sur brave.exe

### Hypotheses restantes

1. Bug Brave 153+ : regression introduite dans cette version
2. Conflit avec Brave perso actif : Brave refuse un 2e instance CDP
3. Verrou systeme : le binaire brave.exe est verrouille par l'instance perso
4. Incompatibilite avec Windows 10/11 build specifique

## Solutions a explorer (session dediee)

### Option 1 : Chrome a la place de Brave
Installer Chrome pour les tests E2E.

### Option 2 : Playwright
Migrer les tests vers Playwright qui gere le browser lui-meme.

### Option 3 : Tuer Brave perso temporairement
NON RETENU - l'utilisateur utilise Brave en permanence.

## Impact

- Tests E2E Web UI : 7 tests desactives
- Tests backend : 880+ tests toujours verts

## Workaround actuel

Les tests E2E sont skippes proprement avec une raison claire.

## Priorite

MOYENNE - non bloquant pour le developpement.

A traiter dans une session dediee "E2E Chrome/Playwright".