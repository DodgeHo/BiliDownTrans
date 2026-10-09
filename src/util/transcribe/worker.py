from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download

from pathlib import Path
import argparse
import json
import sys


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

    print(f"Input: {input_path}", flush = True)
    print(f"Model: {model_path}", flush = True)
    print("Loading large-v3 on CUDA float16...", flush = True)

    model = WhisperModel(model_path, device = "cuda", compute_type = "float16")
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
    args = parser.parse_args()

    try:
        transcribe(args)
    except Exception as error:
        print(f"Transcribe failed: {error}", file = sys.stderr, flush = True)
        raise


if __name__ == "__main__":
    main()
