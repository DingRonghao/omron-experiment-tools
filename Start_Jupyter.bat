@echo off
setlocal
set "EXPERIMENT_DIR=%USERPROFILE%\Experiment"
set "PYTHON_EXE=%EXPERIMENT_DIR%\.venv\Scripts\python.exe"

if not exist "%EXPERIMENT_DIR%\" (
    echo [ERROR] Experiment directory not found: "%EXPERIMENT_DIR%"
    goto :failure
)
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python interpreter not found: "%PYTHON_EXE%"
    goto :failure
)

pushd "%EXPERIMENT_DIR%"
if errorlevel 1 (
    echo [ERROR] Cannot open the Experiment directory.
    goto :failure
)

"%PYTHON_EXE%" -c "import notebook"
if errorlevel 1 (
    echo [ERROR] Cannot load Notebook using the existing environment.
    popd
    goto :failure
)

echo Starting Jupyter Notebook...
echo Keep this window open. Press Ctrl+C to stop the server.
"%PYTHON_EXE%" -m notebook
set "JUPYTER_EXIT=%ERRORLEVEL%"
popd
if not "%JUPYTER_EXIT%"=="0" (
    echo [ERROR] Jupyter Notebook exited with code %JUPYTER_EXIT%.
    goto :failure
)
endlocal
exit /b 0

:failure
echo No software was installed and no system settings were changed.
pause
endlocal
exit /b 1
