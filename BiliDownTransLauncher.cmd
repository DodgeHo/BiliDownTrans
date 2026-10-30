@echo off
setlocal

rem 本文件必须是 CRLF 换行 + GBK(代码页 936) 编码。
rem cmd.exe 按字节定位正在执行的批处理：LF-only 换行会让它把下一行的开头
rem 接到本行末尾，命令被从中间截断，表现为 "系统找不到指定的路径" 外加
rem 一串 'f' / 'el' / 'nul' / 'w.exe"' 不是内部或外部命令。
rem 同理不要在脚本里 chcp 65001：切换代码页后 cmd 会按字符重算文件位置，同样的错位。

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
    rem 不锁 Python 版本：uv 会挑本机可用的 64 位解释器。
    rem 若机器上装的是 32 位 Python，PySide6 没有 win32 wheel，安装必然失败
    uv venv "%VENV%"
    if errorlevel 1 goto fallback_venv
    uv pip install --python "%PY%" -r "%ROOT%requirements.txt"
    if errorlevel 1 goto install_failed
    goto start_app
)

:fallback_venv
where py >nul 2>nul
if not errorlevel 1 (
    py -3.13 -m venv "%VENV%" 2>nul || py -3 -m venv "%VENV%"
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
echo 日志目录：%APPDATA%\BiliDownTrans\logs
pause
exit /b 1
