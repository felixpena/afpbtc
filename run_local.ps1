# Ejecuta el recolector y abre una vista previa local en http://localhost:8080
# Uso (PowerShell, dentro de C:\claude\afpbtc):   .\run_local.ps1
# Requiere Python 3.10 o superior (https://www.python.org/downloads/).

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Probando el recolector..." -ForegroundColor Yellow
python -m unittest discover -s tests

Write-Host "Descargando datos onchain (la primera vez toma ~1 minuto)..." -ForegroundColor Yellow
python -m collector.collect --out public/data

Write-Host "Vista previa en http://localhost:8080  (Ctrl+C para salir)" -ForegroundColor Green
python -m http.server 8080 --directory public
