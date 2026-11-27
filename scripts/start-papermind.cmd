@echo off
rem PaperMind one-click launcher. ASCII only on purpose:
rem cmd.exe reads .cmd files with the OEM codepage, so any non-ASCII
rem byte here corrupts the line structure. All Chinese output lives
rem in start-papermind.ps1 (UTF-8 with BOM) instead.
setlocal
cd /d "%~dp0.."

where powershell >nul 2>nul
if errorlevel 1 goto nops

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-papermind.ps1" %*
goto done

:nops
echo [ERROR] powershell.exe not found in PATH.

:done
echo.
echo ------------------------------------------------------------
echo  Frontend: http://localhost:8081
echo  Status:   scripts\start-papermind.cmd -Status
echo  Stop:     scripts\start-papermind.cmd -Down
echo ------------------------------------------------------------
