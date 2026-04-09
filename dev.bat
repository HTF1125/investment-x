@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "UI_DIR=%ROOT%\ui"

set "CMD=%~1"
if "%CMD%"=="" set "CMD=start"

if /i "%CMD%"=="help"    goto :usage
if /i "%CMD%"=="start"   goto :start_dev
if /i "%CMD%"=="restart" goto :start_dev
if /i "%CMD%"=="be"      goto :start_backend
if /i "%CMD%"=="fe"      goto :start_frontend
if /i "%CMD%"=="stop"    goto :stop_all
if /i "%CMD%"=="prod"    goto :start_prod
if /i "%CMD%"=="fetch"           goto :run_script
if /i "%CMD%"=="fetch_data"      goto :run_script
if /i "%CMD%"=="send"            goto :run_send
if /i "%CMD%"=="send_data"       goto :run_send
if /i "%CMD%"=="research"        goto :run_script
if /i "%CMD%"=="macro_research"  goto :run_script
if /i "%CMD%"=="collect"         goto :run_script
if /i "%CMD%"=="regime"          goto :run_script
if /i "%CMD%"=="nlm_login"       goto :run_script

echo Unknown command: %CMD%
goto :usage

:usage
echo.
echo   Investment-X
echo.
echo   dev            Dev mode (local backend + frontend + tunnel)
echo   dev prod       Prod mode (Docker containers)
echo   dev stop       Stop everything
echo   dev be         Backend only (port 8000)
echo   dev fe         Frontend only (port 3000)
echo.
echo   dev fetch      Fetch data (Yahoo/Fred/Naver)
echo   dev research   Macro research pipeline
echo   dev collect    Data collectors (CFTC, AAII, etc.)
echo   dev regime     Compute regime strategy
echo   dev send       Send data reports via email
echo   dev nlm_login  NotebookLM login
echo.
exit /b 0

:start_dev
echo [DEV] Stopping prod containers...
docker compose stop tunnel frontend backend >nul 2>&1
echo [DEV] Freeing ports...
call :kill_port 8000
call :kill_port 3000
call :kill_tunnel
echo [DEV] Starting database...
docker compose up -d db >nul 2>&1
echo [DEV] Launching backend + frontend + tunnel...
call :launch both
call :launch_tunnel
echo.
echo   App:    http://localhost:3000
echo   API:    http://localhost:8000/docs
echo   Tunnel: investment-x.app
echo.
exit /b 0

:start_prod
echo [PROD] Stopping local processes...
call :kill_port 8000
call :kill_port 3000
call :kill_tunnel
echo [PROD] Starting Docker containers...
docker compose up -d
echo.
echo   App:    http://localhost:3000
echo   API:    http://localhost:8000 (internal)
echo   Tunnel: investment-x.app
echo.
exit /b 0

:start_backend
call :kill_port 8000
call :launch backend
echo   API: http://localhost:8000/docs
exit /b 0

:start_frontend
call :kill_port 3000
call :launch frontend
echo   UI: http://localhost:3000
exit /b 0

:stop_all
echo Stopping local processes...
call :kill_port 8000
call :kill_port 3000
call :kill_tunnel
echo Stopping Docker containers...
docker compose stop tunnel frontend backend >nul 2>&1
echo Done. Database left running.
exit /b 0

:run_send
python -c "from ix.common.task import send_data_reports; send_data_reports()"
exit /b %errorlevel%

:run_script
if /i "%CMD%"=="fetch" python scripts/data/fetch_data.py %2 %3 %4 %5 %6
if /i "%CMD%"=="fetch_data" python scripts/data/fetch_data.py %2 %3 %4 %5 %6
if /i "%CMD%"=="research" python scripts/research/macro_research.py %2 %3 %4 %5 %6
if /i "%CMD%"=="macro_research" python scripts/research/macro_research.py %2 %3 %4 %5 %6
if /i "%CMD%"=="collect" python scripts/research/collect_sources.py %2 %3 %4 %5 %6
if /i "%CMD%"=="regime" python scripts/strategy/compute_regime_strategy.py %2 %3 %4 %5 %6
if /i "%CMD%"=="nlm_login" python scripts/research/nlm_login.py
exit /b %errorlevel%

:launch
set "MODE=%~1"
where wt >nul 2>&1
if errorlevel 1 goto :launch_cmd
if /i "%MODE%"=="both" (
    start "" wt -d "%ROOT%" --title "IX Backend" -- cmd /k "python -m uvicorn ix.api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir ix"
    start "" wt -d "%UI_DIR%" --title "IX Frontend" -- cmd /k "npx next dev -p 3000"
) else if /i "%MODE%"=="backend" (
    start "" wt -d "%ROOT%" --title "IX Backend" -- cmd /k "python -m uvicorn ix.api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir ix"
) else if /i "%MODE%"=="frontend" (
    start "" wt -d "%UI_DIR%" --title "IX Frontend" -- cmd /k "npx next dev -p 3000"
)
exit /b 0
:launch_cmd
if /i "%MODE%"=="both" (
    start "IX-Backend" cmd /k "cd /d %ROOT% && python -m uvicorn ix.api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir ix"
    start "IX-Frontend" cmd /k "cd /d %UI_DIR% && npx next dev -p 3000"
) else if /i "%MODE%"=="backend" (
    start "IX-Backend" cmd /k "cd /d %ROOT% && python -m uvicorn ix.api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir ix"
) else if /i "%MODE%"=="frontend" (
    start "IX-Frontend" cmd /k "cd /d %UI_DIR% && npx next dev -p 3000"
)
exit /b 0

:launch_tunnel
for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%\.env") do (
    if "%%A"=="CLOUDFLARE_TUNNEL_TOKEN" set "CF_TOKEN=%%B"
)
if not defined CF_TOKEN (
    echo   [WARN] CLOUDFLARE_TUNNEL_TOKEN not found in .env, skipping tunnel
    exit /b 0
)
where wt >nul 2>&1
if errorlevel 1 (
    start "IX-Tunnel" cmd /k "cloudflared tunnel --no-autoupdate run --token %CF_TOKEN%"
) else (
    start "" wt -d "%ROOT%" --title "IX Tunnel" -- cmd /k "cloudflared tunnel --no-autoupdate run --token %CF_TOKEN%"
)
exit /b 0

:kill_tunnel
powershell -NoProfile -Command "Get-Process -Name cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1
exit /b 0

:kill_port
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1
exit /b 0
