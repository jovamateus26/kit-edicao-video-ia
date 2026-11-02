@echo off
rem Instalador do kit no Windows. Roda o instalar.ps1 sem mudar a politica de execucao do sistema.
rem Uso: instalar.cmd [-Dependencias] [-Destino "pasta1;pasta2"] [-Copiar] [-Forcar] [-SoProprias] [-Verificar]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1" %*
set "RC=%ERRORLEVEL%"
rem aberto com dois cliques (sem argumentos): espera para dar tempo de ler o resultado
if "%~1"=="" pause
exit /b %RC%
