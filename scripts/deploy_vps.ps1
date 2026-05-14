param(
    [string]$Message = "",
    [string]$Remote = "root@145.223.93.162",
    [string]$RemotePath = "/var/www/site_idiomas",
    [string]$Branch = "main",
    [string]$Service = "site_idiomas"
)

$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [string]$Title,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    & $Command
}

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Comando obrigatorio nao encontrado: $Name"
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

Require-Command "git"
Require-Command "python"
Require-Command "ssh"

if (-not $Message) {
    $Message = Read-Host "Mensagem do commit"
}

if (-not $Message) {
    throw "Informe uma mensagem de commit."
}

Run-Step "Rodando testes locais" {
    python manage.py test
}

Run-Step "Rodando check local" {
    python manage.py check
}

$status = git status --short
if ($status) {
    Run-Step "Preparando commit local" {
        git status --short
        git add .
        git commit -m $Message
    }
} else {
    Write-Host ""
    Write-Host "==> Nenhuma alteracao local para commitar" -ForegroundColor Yellow
}

Run-Step "Enviando para o GitHub" {
    git push origin $Branch
}

$remoteCommand = @"
set -e
cd '$RemotePath'
git fetch origin '$Branch'
git pull --ff-only origin '$Branch'
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py import_alice_phrases
python manage.py collectstatic --noinput
python manage.py check
systemctl restart '$Service'
systemctl status '$Service' --no-pager
"@

Run-Step "Atualizando VPS em $Remote" {
    ssh $Remote $remoteCommand
}

Write-Host ""
Write-Host "Deploy finalizado: https://fabianopolone.com.br" -ForegroundColor Green
