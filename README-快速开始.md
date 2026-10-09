# BiliDownTrans 快速开始

BiliDownTrans 是基于 Bili23 Downloader 改造的 B 站下载与 GPU 转录流水线工具。

## 使用方式

1. 下载 `BiliDownTrans-v0.1.0-win-x64-portable.zip`。
2. 解压到一个固定目录，例如 `D:\Apps\BiliDownTrans`。
3. 双击 `BiliDownTrans.exe` 启动。若被安全软件拦截，也可以运行 `BiliDownTransLauncher.cmd`。
4. 在“下载”页输入 B 站视频链接并下载。
5. 下载完成的视频会出现在“转录”页；默认开启“下载后自动转录”。

## 首次运行

首次运行会自动创建 `.venv` 并安装依赖，因此可能需要几分钟。

首次转录时，如果本机没有模型，程序会从 Hugging Face 自动下载：

`Systran/faster-whisper-large-v3`

模型会保存到应用数据目录下的 `BiliDownTrans\models\faster-whisper-large-v3`。如果你已经有本地模型，也可以在配置里设置模型目录。

## GPU 要求

默认转录使用 `CUDA + float16`，需要 NVIDIA 显卡和可用驱动/CUDA 运行环境。若 CUDA 初始化失败，转录任务会失败并显示错误，可修复环境后点击“重做”。

## 注意

- 删除转录任务只删除列表记录，不删除视频或字幕文件。
- 模型来自 Hugging Face 官方模型仓库，不放在本项目 Git LFS 或 GitHub Release 中。
- 如果网络无法访问 Hugging Face，请手动下载 `Systran/faster-whisper-large-v3` 并配置模型目录。
