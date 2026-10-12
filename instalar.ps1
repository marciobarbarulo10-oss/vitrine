# Copia a skill para a pasta de skills do Claude Code e cria a pasta de estado.
# Uso: powershell -ExecutionPolicy Bypass -File instalar.ps1
$ErrorActionPreference = "Stop"

$origem = Join-Path $PSScriptRoot "skill"
$destino = Join-Path $HOME ".claude\skills\vitrine"

New-Item -ItemType Directory -Force $destino | Out-Null
Copy-Item -Path (Join-Path $origem "*") -Destination $destino -Recurse -Force
Write-Host "Skill copiada para $destino"

# Cria ~/.claude/vitrine com um alvo.json vazio, se ainda não existir.
python (Join-Path $destino "scripts\vitrine.py") init
