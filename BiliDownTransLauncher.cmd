@echo off
setlocal

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PYW=%VENV%\Scripts\pythonw.exe"

if exist "%PY%" (
    "%PY%" -c "import PySide6, qfluentwidgets, orjson, faster_whisper, huggingface_hub" >nul 2>nul
    if not errorlevel 1 goto start_app
)

echo 正在准备 BiliDownTrans 运行环境，首次启动可能需要几分钟...

where uv >nul 2>nul
if not errorlevel 1 (
    uv venv "%VENV%" --python 3.12
    if errorlevel 1 goto fallback_venv
    uv pip install --python "%PY%" -r "%ROOT%requirements.txt"
    if errorlevel 1 goto install_failed
    goto start_app
)

:fallback_venv
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -m venv "%VENV%" 2>nul || py -3 -m venv "%VENV%"
) else (
    python -m venv "%VENV%"
)
if errorlevel 1 goto install_failed

"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r "%ROOT%requirements.txt"
if errorlevel 1 goto install_failed

:start_app
start "" "%PYW%" "%ROOT%src\main.py"
exit /b 0

:install_failed
echo.
echo 运行环境准备失败。请确认已安装 Python 3.11+，并检查网络是否可以下载依赖。
echo 你也可以在本目录手动运行：pip install -r requirements.txt
pause
exit /b 1
