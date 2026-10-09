# BiliDownTrans

![BiliDownTrans](assets/pipeline_icon.svg)

BiliDownTrans 是一个面向本地归档和字幕制作的 B 站下载转录流水线工具。它基于 [Bili23 Downloader](https://github.com/ScottSloan/Bili23-Downloader) 的下载、解析、任务队列、断点续传和 Fluent 桌面界面能力，并整合基于 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 与 `Systran/faster-whisper-large-v3` 的 GPU 转录流程。

项目目标很直接：输入 B 站链接，下载视频，然后把已下载视频排队转录成字幕和文本。下载和转录都长期保存任务列表，失败后可以重试，适合批量整理课程、访谈、播客、长视频素材和个人离线资料库。

[English](README_en.md) | [Release 下载](https://github.com/DodgeHo/BiliDownTrans/releases/latest)

## 核心功能

| 功能 | 说明 |
| --- | --- |
| B 站解析与下载 | 继承 Bili23 Downloader 的投稿视频、番剧、课程、合集、收藏夹、空间、历史记录等解析能力。 |
| 下载队列 | 支持任务排队、并发下载、暂停、重试、删除、断点续传和下载记录持久化。 |
| 快速/高级下载 | 下载页提供“立即下载”和“高级下载”两个入口，既能快速入队，也能保留原有细项配置。 |
| 文件命名 | 默认按视频标题保存，并删除 Windows 非法字符和空白字符，避免常见落盘失败。 |
| 转录队列 | 下载完成的视频进入“转录”页，可手动开始、取消、重做、删除记录和打开目录。 |
| 自动转录 | 默认开启“下载后自动转录”，下载完成后自动加入转录队列，并按视频路径去重。 |
| 字幕/文本输出 | 输出 `.large-v3.raw.srt`、`.large-v3.优化断句.srt`、`.large-v3.txt`、词级 JSON 和质量报告。 |
| 模型自动下载 | 首次转录时自动从 Hugging Face 下载 `Systran/faster-whisper-large-v3`，无需把 3GB 模型放进 Git。 |

## 下载与启动

1. 前往 [GitHub Releases](https://github.com/DodgeHo/BiliDownTrans/releases/latest) 下载 `BiliDownTrans-v0.1.0-win-x64-portable.zip`。
2. 解压到固定目录，例如 `D:\Apps\BiliDownTrans`。
3. 双击 `BiliDownTrans.exe` 启动。
4. 首次启动会自动创建 `.venv` 并安装依赖；首次转录会自动下载 large-v3 模型。

如果 `BiliDownTrans.exe` 被安全软件拦截，也可以运行同目录的 `BiliDownTransLauncher.cmd`。

## 模型与 GPU

BiliDownTrans 不把模型提交到 Git LFS，也不把 3GB 模型塞进 Release。默认模型来自 Hugging Face：

`Systran/faster-whisper-large-v3`

模型会缓存到应用数据目录下：

`BiliDownTrans\models\faster-whisper-large-v3`

如果网络无法访问 Hugging Face，可以手动下载该模型，并在配置里指定本地模型目录。当前转录默认使用 `CUDA + float16`，需要 NVIDIA 显卡、驱动和可用 CUDA 运行环境；环境异常时任务会失败并保留记录，可修复后点击“重做”。

## 与上游项目的关系

BiliDownTrans 是组合型新项目，不是从零重写：

- 下载器基础来自 [Bili23 Downloader](https://github.com/ScottSloan/Bili23-Downloader)，保留其解析、下载、队列、SQLite 存储、命名规则、登录、封面/字幕/弹幕/元数据等成熟能力。
- 转录能力基于 [faster-whisper](https://github.com/SYSTRAN/faster-whisper)、[CTranslate2](https://github.com/OpenNMT/CTranslate2) 和 `Systran/faster-whisper-large-v3` 模型。
- Windows 启动器目录 `launcher/` 继承自 [PyStand](https://github.com/skywind3000/PyStand) 的思路；当前 portable 包额外提供一个轻量 `BiliDownTrans.exe` 启动器。

感谢这些项目提供的基础工作。BiliDownTrans 在此之上聚焦“下载后自动转录”的一体化桌面工作流。

## 使用协议与免责声明

本项目仅供个人学习、研究和个人资料整理使用。下载内容仅限个人非商业用途，严禁用于商业分发、公开传播、批量抓取或任何违反目标平台服务条款的行为。

本软件不会绕过付费墙或平台知识产权保护措施，只基于用户账号本身拥有的合法访问权限工作。用户需自行承担使用本项目可能带来的账号、版权、网络和硬件风险。

## 开源许可

本项目以 GPL-3.0 发布。上游与依赖项目的许可请分别参考其原仓库：

- Bili23 Downloader: GPL-3.0
- faster-whisper: MIT
- CTranslate2: MIT
- PyStand: MIT

WBI 签名、部分接口以及 buvid3 等参数生成参考 [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)。
