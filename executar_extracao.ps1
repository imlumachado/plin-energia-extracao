param(
    [string]$Diretorio = $PSScriptRoot
)

$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $Diretorio

$venv = Join-Path $Diretorio ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venv)) {
    $venv = "python"
}

$logDir = Join-Path $Diretorio "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$saida = Join-Path $logDir "extracao_$timestamp.txt"
$resumo = Join-Path $logDir "ultima_execucao.txt"

$env:PLIN_HEADLESS = "1"

& $venv "Teste_Plin_Playwright.py" *> $saida
$codigo = $LASTEXITCODE

"Codigo de saida: $codigo" | Set-Content -Path $resumo -Encoding utf8
"Execucao concluida: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Add-Content -Path $resumo -Encoding utf8
"Log: $saida" | Add-Content -Path $resumo -Encoding utf8

exit $codigo
