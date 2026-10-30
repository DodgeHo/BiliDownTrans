from pathlib import Path
import argparse
import json
import sys


# 可展示给用户的失败原因前缀。manager.py 里有一份同名常量，两边必须一致：
# 界面靠它把这条捡出来当错误信息显示，否则用户只会看到"转录进程退出码：1"
ERROR_PREFIX = "ERROR: "


class TranscriptionError(RuntimeError):
    """带有可直接展示的中文原因，main() 会以 ERROR_PREFIX 单独打印"""


def _register_cuda_dll_dirs():
    """
    在 Windows 上把 cuBLAS / CUDA Runtime 装进本进程

    ctranslate2 的 wheel 自带 cudnn64_9.dll，但不带 cuBLAS 与 CUDA Runtime ——
    官方要求本机装 CUDA 12 Toolkit。这里改用 PyPI 上的可再发行包
    nvidia-cublas-cu12 / nvidia-cuda-runtime-cu12，省掉用户手动装几 GB 的 Toolkit。

    必须早于 ctranslate2 加载：它是在真正推理时才去 LoadLibrary("cublas64_12.dll")，
    走的是不带搜索标志的普通查找，只看 exe 目录 / System32 / PATH ——
    add_dll_directory() 加进去的目录对这条路无效（它只作用于带
    LOAD_LIBRARY_SEARCH_* 标志的 LoadLibraryEx）。所以这里直接把 DLL 显式装进
    进程：Windows 按模块名复用已加载的 DLL，ctranslate2 后来的 LoadLibrary
    会直接拿到这里的句柄。晚一步就是
    "Library cublas64_12.dll is not found or cannot be loaded"
    """
    if sys.platform != "win32":
        return

    import ctypes

    for base in sys.path:
        for relative in ("nvidia/cuda_runtime/bin", "nvidia/cublas/bin", "nvidia/cudnn/bin"):
            directory = Path(base) / relative

            if not directory.is_dir():
                continue

            for library in sorted(directory.glob("*.dll")):
                try:
                    ctypes.CDLL(str(library))

                except OSError:
                    # 个别 DLL 可能有额外依赖，装不上就交给 ctranslate2 自己报错
                    pass


# 必须早于 faster_whisper：它一被导入就会加载 ctranslate2 及其 CUDA 依赖
_register_cuda_dll_dirs()

from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download


def format_timestamp(seconds: float):
    milliseconds = round(seconds * 1000)
    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000
    minutes = milliseconds // 60_000
    milliseconds %= 60_000
    secs = milliseconds // 1000
    milliseconds %= 1000

    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def write_srt(path: Path, segments: list[dict]):
    with path.open("w", encoding = "utf-8") as f:
        for index, segment in enumerate(segments, 1):
            f.write(f"{index}\n")
            f.write(f"{format_timestamp(segment['start'])} --> {format_timestamp(segment['end'])}\n")
            f.write(segment["text"].strip() + "\n\n")


def resolve_model(model: str):
    if "|" not in model:
        return model

    repo_id, local_dir = model.split("|", 1)
    local_path = Path(local_dir)

    if (local_path / "model.bin").exists():
        print(f"Model ready: {local_path}", flush = True)
        return str(local_path)

    local_path.mkdir(parents = True, exist_ok = True)

    print(f"Downloading model from Hugging Face: {repo_id}", flush = True)
    print(f"Model target: {local_path}", flush = True)

    snapshot_download(
        repo_id = repo_id,
        local_dir = str(local_path),
        local_dir_use_symlinks = False,
        allow_patterns = [
            "config.json",
            "model.bin",
            "preprocessor_config.json",
            "tokenizer.json",
            "vocabulary.json",
            "README.md",
        ],
    )

    print("Model download completed", flush = True)

    return str(local_path)


def resolve_device(choice = "auto"):
    """
    决定这次转录用哪块设备

    choice 取自配置 Transcribe/device：
      auto —— 有卡用 GPU，没卡退回 CPU（慢但能出结果）
      cuda —— 强制 GPU，没卡直接报错，不静默降级
      cpu  —— 强制 CPU

    笔记本在电池供电时，电源策略可能把独显整个断掉 —— 连 nvlddmkm 驱动服务都不在，
    ctranslate2 会数到 0 张卡。这种情况下若直接构造 WhisperModel，只会抛
    "CUDA failed with error no CUDA-capable device is detected"
    """
    if choice == "cpu":
        return "cpu", "int8"

    available = 0

    try:
        import ctranslate2

        available = ctranslate2.get_cuda_device_count()

    except Exception:
        available = 0

    if available > 0:
        return "cuda", "float16"

    if choice == "cuda":
        raise TranscriptionError(
            "未检测到可用的 NVIDIA 显卡。笔记本在电池供电时可能已关闭独立显卡，"
            "请接通电源后重试；若已接电源仍报此错，请重启电脑或重新启用显卡驱动"
        )

    # auto：退回 CPU，但必须让用户知道慢在哪里，否则会以为卡死
    print(
        "WARNING: 未检测到可用的 NVIDIA 显卡，改用 CPU（int8）转录，速度会慢很多。"
        "笔记本在电池供电时可能已关闭独立显卡，接通电源后重做即可回到 GPU",
        flush = True
    )

    return "cpu", "int8"


def transcribe(args):
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents = True, exist_ok = True)

    stem = input_path.stem
    raw_srt = output_dir / f"{stem}.large-v3.raw.srt"
    polished_srt = output_dir / f"{stem}.large-v3.优化断句.srt"
    transcript_txt = output_dir / f"{stem}.large-v3.txt"
    words_json = output_dir / f"{stem}.large-v3.words.json"
    report_md = output_dir / f"{stem}.large-v3.质量报告.md"

    model_path = resolve_model(args.model)
    device, compute_type = resolve_device(args.device)

    print(f"Input: {input_path}", flush = True)
    print(f"Model: {model_path}", flush = True)
    print(f"Loading large-v3 on {device} {compute_type}...", flush = True)

    model = WhisperModel(model_path, device = device, compute_type = compute_type)
    segments_gen, info = model.transcribe(
        str(input_path),
        language = args.language,
        task = "transcribe",
        beam_size = 5,
        temperature = 0,
        condition_on_previous_text = True,
        vad_filter = True,
        word_timestamps = True,
    )

    duration = max(float(getattr(info, "duration", 0) or 0), 1)
    segments = []
    words = []
    last_progress = -1

    for segment in segments_gen:
        text = segment.text.strip()
        item = {
            "start": float(segment.start),
            "end": float(segment.end),
            "text": text,
        }
        segments.append(item)

        if segment.words:
            for word in segment.words:
                words.append({
                    "start": float(word.start),
                    "end": float(word.end),
                    "word": word.word,
                    "probability": float(word.probability),
                })

        progress = min(99, int(item["end"] / duration * 100))

        if progress > last_progress:
            last_progress = progress
            print(f"Progress: {progress}%", flush = True)

    transcript = "\n".join(segment["text"] for segment in segments)

    write_srt(raw_srt, segments)
    write_srt(polished_srt, segments)
    transcript_txt.write_text(transcript, encoding = "utf-8")
    words_json.write_text(json.dumps(words, ensure_ascii = False, indent = 2), encoding = "utf-8")
    report_md.write_text(
        "\n".join([
            "# large-v3 字幕质量报告",
            "",
            f"- 输入：`{input_path}`",
            f"- 模型：`{model_path}`",
            f"- 语言：`{args.language}`",
            f"- 分段数：{len(segments)}",
            f"- 词数：{len(words)}",
            "",
            "## 输出",
            f"- `{raw_srt.name}`",
            f"- `{polished_srt.name}`",
            f"- `{transcript_txt.name}`",
            f"- `{words_json.name}`",
        ]),
        encoding = "utf-8"
    )

    print("Progress: 100%", flush = True)
    print(f"Output: {polished_srt}", flush = True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--model", default = "Systran/faster-whisper-large-v3")
    parser.add_argument("--output-dir", default = str(Path.cwd()))
    parser.add_argument("--language", default = "zh")
    parser.add_argument("--device", default = "auto", choices = ("auto", "cuda", "cpu"), help = "auto：没显卡就退回 CPU；cuda：强制 GPU")
    args = parser.parse_args()

    try:
        transcribe(args)

    except TranscriptionError as error:
        # 打印带前缀的一行，界面据此显示具体原因，而不是笼统的退出码
        print(f"{ERROR_PREFIX}{error}", file = sys.stderr, flush = True)

        sys.exit(2)

    except Exception as error:
        print(f"Transcribe failed: {error}", file = sys.stderr, flush = True)
        raise


if __name__ == "__main__":
    main()
