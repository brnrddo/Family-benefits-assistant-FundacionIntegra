# make.ps1 — equivalente del Makefile para Windows PowerShell (sin `make`).
#
# Uso (desde backend/):
#   .\make.ps1 data     # (re)genera e3.db desde los CSV + precálculo + vistas
#   .\make.ps1 test     # corre la suite de tests
#   .\make.ps1 clean    # borra e3.db local
#
# El objetivo `data` reproduce la misma base que el Dockerfile embebe en la
# imagen para AWS. $env:PYTHON permite elegir otro intérprete.

param(
    [Parameter(Position = 0)]
    [ValidateSet('data', 'load', 'views', 'test', 'clean')]
    [string]$Target = 'data'
)

$ErrorActionPreference = 'Stop'
$Python = if ($env:PYTHON) { $env:PYTHON } else { 'python' }

function Invoke-Step($desc, $cmd) {
    Write-Host "==> $desc" -ForegroundColor Cyan
    & $Python @cmd
    if ($LASTEXITCODE -ne 0) { throw "Fallo en: $desc (exit $LASTEXITCODE)" }
}

switch ($Target) {
    'load'  { Invoke-Step 'Loader M1 (CSV -> SQLite)' @('-m', 'app.loader.load', '--force') }
    'views' { Invoke-Step 'Precálculo + vistas de cruce' @('-m', 'app.db.build_views') }
    'test'  { Invoke-Step 'Tests Rol 1' @('-m', 'pytest') }
    'clean' {
        if (Test-Path 'e3.db') { Remove-Item 'e3.db' -Force; Write-Host 'e3.db eliminada.' }
        else { Write-Host 'No hay e3.db que borrar.' }
    }
    'data' {
        Invoke-Step 'Loader M1 (CSV -> SQLite)' @('-m', 'app.loader.load', '--force')
        Invoke-Step 'Precálculo + vistas de cruce' @('-m', 'app.db.build_views')
        Write-Host 'Listo: e3.db regenerada con precálculo y vistas.' -ForegroundColor Green
    }
}
