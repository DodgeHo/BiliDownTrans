# BiliDownTrans

![BiliDownTrans](assets/pipeline_icon.svg)

BiliDownTrans is a desktop pipeline for downloading Bilibili videos and transcribing downloaded videos into subtitles and text. It builds on [Bili23 Downloader](https://github.com/ScottSloan/Bili23-Downloader) for parsing, downloading, task queues, resume support, SQLite persistence, and Fluent UI, then adds a GPU transcription workflow powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and `Systran/faster-whisper-large-v3`.

The goal is simple: paste a Bilibili URL, download the video, and queue the completed video for local transcription. Both download and transcription tasks are persisted, failed jobs can be retried, and the workflow is designed for courses, interviews, podcasts, long videos, and personal archives.

[简体中文](README.md) | [Releases](https://github.com/DodgeHo/BiliDownTrans/releases/latest)

## Features

| Feature | Description |
| --- | --- |
| Bilibili parsing and download | Inherits Bili23 Downloader support for videos, bangumi, courses, collections, favorites, user spaces, history, and more. |
| Download queue | Supports queued downloads, concurrency, pause, retry, delete, resume, and persistent task records. |
| Quick/advanced download | The download page offers both immediate download and advanced options. |
| File naming | Saves videos by title by default and removes Windows-invalid characters and whitespace. |
| Transcription queue | Completed videos appear in the transcription page and can be started, canceled, retried, removed, or opened in Explorer. |
| Auto transcription | Enabled by default; completed downloads are automatically added to the transcription queue with path-based deduplication. |
| Subtitle/text output | Produces `.large-v3.raw.srt`, `.large-v3.优化断句.srt`, `.large-v3.txt`, word-level JSON, and a quality report. |
| Automatic model download | Downloads `Systran/faster-whisper-large-v3` from Hugging Face on first transcription instead of storing a 3GB model in Git. |

## Download and Start

1. Download `BiliDownTrans-v0.1.0-win-x64-portable.zip` from [GitHub Releases](https://github.com/DodgeHo/BiliDownTrans/releases/latest).
2. Extract it to a stable folder, for example `D:\Apps\BiliDownTrans`.
3. Run `BiliDownTrans.exe`.
4. First launch creates a `.venv` and installs dependencies; first transcription downloads the large-v3 model.

If `BiliDownTrans.exe` is blocked by security software, run `BiliDownTransLauncher.cmd` in the same folder.

## Model and GPU

BiliDownTrans does not put the model in Git LFS or GitHub Release assets. The default model source is:

`Systran/faster-whisper-large-v3`

The model is cached under the application data directory:

`BiliDownTrans\models\faster-whisper-large-v3`

If Hugging Face is unreachable, download the model manually and configure the local model directory. Transcription currently defaults to `CUDA + float16`, so an NVIDIA GPU, working driver, and CUDA runtime are required. Failed tasks stay in the queue and can be retried after the environment is fixed.

## Upstream Projects

BiliDownTrans is an integration project, not a ground-up rewrite:

- Downloading is based on [Bili23 Downloader](https://github.com/ScottSloan/Bili23-Downloader), including its parsing, downloading, queueing, SQLite storage, naming rules, authentication, covers, subtitles, danmaku, and metadata features.
- Transcription is based on [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [CTranslate2](https://github.com/OpenNMT/CTranslate2), and `Systran/faster-whisper-large-v3`.
- The Windows launcher directory keeps the lineage of [PyStand](https://github.com/skywind3000/PyStand); the portable package also includes a small `BiliDownTrans.exe` launcher.

Thanks to these upstream projects. BiliDownTrans focuses on the combined “download then transcribe” desktop workflow.

## Terms and Disclaimer

This project is for personal learning, research, and personal archiving only. Downloaded content must remain for personal non-commercial use. Do not use this project for commercial distribution, public redistribution, batch scraping, or any activity that violates platform terms.

The software does not bypass paywalls or intellectual-property protections. It operates only through the access permissions of the user account. Users are responsible for account, copyright, network, and hardware risks.

## License

This project is released under GPL-3.0. See upstream repositories for their own licenses:

- Bili23 Downloader: GPL-3.0
- faster-whisper: MIT
- CTranslate2: MIT
- PyStand: MIT

WBI signatures, selected API behavior, and buvid3-related parameters reference [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect).
