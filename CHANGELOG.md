# BiliDownTrans 更新日志

## 0.1.1 (2026-10-30)

### 修复

- **转录直接失败（退出码 1）**：`av` 装到 19.x 后 `av.open()` 不再接受 `metadata_errors` 参数，而 `faster_whisper/audio.py` 仍在传它。依赖锁到 `av==16.1.0` —— `faster-whisper` 只声明 `av>=11` 没有上限，不锁就会漂。
- **推理时报 `cublas64_12.dll is not found`**：ctranslate2 的 wheel 自带 cuDNN，但不带 cuBLAS 与 CUDA Runtime。改用 PyPI 可再发行包 `nvidia-cublas-cu12` / `nvidia-cuda-runtime-cu12`，并在加载 ctranslate2 之前把 DLL 显式装入进程（`add_dll_directory` 对普通 `LoadLibrary` 不起作用）。
- **双击启动器报「系统找不到指定的路径」外加一串 `'f'`、`'el'`、`'nul' 不是命令」**：`BiliDownTransLauncher.cmd` 是 LF 换行，而 cmd.exe 按字节定位正在执行的批处理，会把下一行的开头接到本行末尾。文件改为 CRLF + GBK，并在 `.gitattributes` 里钉住 `eol=crlf`，避免检出时又被转回去。
- **每次启动都记一条「检查更新失败」**：缺 `verhub-sdk`，已补进 `requirements.txt` 与 `pyproject.toml`。
- **启动脚本硬编码 `--python 3.12`**：机器上若只装了 32 位的 3.12，PySide6 没有 win32 wheel，重建环境必然失败。改为让 uv 自选 64 位解释器。

### 新增

- **显卡不可用时给出具体原因**。以前界面只显示「转录进程退出码：1」，看不出是显卡的事；现在会明确提示未检测到 NVIDIA 显卡，并说明笔记本电池供电可能已关闭独显。
- **转录设备策略 `Transcribe/device`**：
  - `auto`（默认）—— 有显卡走 GPU，没有就退回 CPU（int8），慢但能出字幕
  - `cuda` —— 强制 GPU，看不到显卡直接报错，不静默降级
  - `cpu` —— 强制 CPU
- **关闭启动时的自动检查更新**。原更新通道登记的是上游 Bili23-Downloader，却拿来比对本项目的版本号，结果恒为「有新版本」，每次启动都弹一个无关项目的更新窗。设置页的手动「检查更新」保留。

### 注意

- Windows GPU 转录现在依赖 `nvidia-cublas-cu12` 与 `nvidia-cuda-runtime-cu12`（合计约 800 MB），首次安装会慢；从 PyPI 官方源下大包容易卡住，建议换国内镜像源。
- `Transcribe/device` 目前没有设置界面入口，需要改 `config.json`。
