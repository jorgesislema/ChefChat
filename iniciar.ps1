# Abre ChefChat en http://127.0.0.1:8765  (funciona desde cualquier carpeta)
# Para otro puerto:  $env:CHEFCHAT_PORT=9000 ; .\iniciar.ps1
Set-Location -Path $PSScriptRoot
if (-not (Test-Path "web\dist\index.html")) {
    Write-Host "Falta construir la pantalla. Ejecuta: cd web; npm install; npm run build"
    exit 1
}
$puerto = if ($env:CHEFCHAT_PORT) { $env:CHEFCHAT_PORT } else { "8765" }
if (Get-NetTCPConnection -State Listen -LocalPort $puerto -ErrorAction SilentlyContinue) {
    Write-Host "Ya hay algo abierto en el puerto $puerto. Si es ChefChat, abre http://127.0.0.1:$puerto"
    Write-Host "Si no, usa otro puerto:  `$env:CHEFCHAT_PORT=9000 ; .\iniciar.ps1"
    exit 1
}
$env:CHEFCHAT_PORT = $puerto
# Abre el navegador SOLO cuando el servidor ya responde (puede tardar unos segundos)
Start-Job -ArgumentList $puerto -ScriptBlock {
    param($pt)
    for ($i = 0; $i -lt 60; $i++) {
        try { Invoke-WebRequest "http://127.0.0.1:$pt/api/salud" -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process "http://127.0.0.1:$pt"; return } catch { Start-Sleep 1 }
    }
} | Out-Null
Write-Host "Iniciando ChefChat en http://127.0.0.1:$puerto  (Ctrl+C para cerrar)"
& "$PSScriptRoot\.venv\Scripts\python.exe" -m server
