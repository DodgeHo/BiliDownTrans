from PySide6.QtCore import QObject, QTimer

from ..common.config import appdata_path, config
from ..common._json import loads
from ..common.signal_bus import signal_bus
from ..common.timestamp import get_timestamp
from ..download.task.info import TaskInfo
from .db import TranscribeTaskDB
from .info import TranscribeTaskInfo, TranscribeStatus
from .runner import TranscribeRunner

from pathlib import Path
from uuid import uuid4
import logging
import re


logger = logging.getLogger(__name__)

MEDIA_EXTENSIONS = {".mp4", ".mkv", ".flv", ".mov", ".avi", ".webm", ".m4v", ".ts"}


class TranscribeTaskManager(QObject):
    def __init__(self):
        super().__init__()

        self.db = TranscribeTaskDB()
        self.active_runners: dict[str, TranscribeRunner] = {}

        signal_bus.transcribe.enqueue_completed_downloads.connect(self.enqueue_from_completed_downloads)
        signal_bus.transcribe.schedule.connect(self.schedule)

    def query(self) -> list[TranscribeTaskInfo]:
        return [TranscribeTaskInfo.from_dict(loads(row[0])) for row in self.db.query_tasks()]

    def query_by_id(self, task_id: str):
        result = self.db.query_task_by_id(task_id)

        if not result:
            return None

        return TranscribeTaskInfo.from_dict(loads(result[0][0]))

    def query_by_video_path(self, video_path: str):
        result = self.db.query_task_by_video_path(self._normalize_video_path(video_path))

        if not result:
            return None

        return TranscribeTaskInfo.from_dict(loads(result[0][0]))

    def sync_completed_downloads(self, auto_start: bool = False):
        from ..download.task.manager import task_manager

        self.enqueue_from_completed_downloads(task_manager.query(completed = True), auto_start = auto_start)

    def enqueue_from_completed_downloads(self, task_info_list: list[TaskInfo], auto_start: bool = True):
        changed = False

        for task_info in task_info_list:
            for video_path in self._resolve_video_paths(task_info):
                changed = self.enqueue_task(
                    video_path = str(video_path),
                    title = task_info.Basic.show_title or video_path.stem,
                    download_task_id = task_info.Basic.task_id,
                    auto_start = auto_start
                ) or changed

        if changed:
            signal_bus.transcribe.tasks_changed.emit()

        if auto_start:
            signal_bus.transcribe.schedule.emit()

    def enqueue_task(self, video_path: str, title: str = "", download_task_id: str = "", auto_start: bool = True) -> bool:
        video_path = self._normalize_video_path(video_path)

        if not video_path:
            return False

        path = Path(video_path)

        if not path.exists() or path.suffix.lower() not in MEDIA_EXTENSIONS:
            return False

        existing = self.query_by_video_path(video_path)

        if existing:
            outputs = self._collect_output_files(video_path)

            if outputs and existing.status != TranscribeStatus.COMPLETED:
                existing.status = TranscribeStatus.COMPLETED
                existing.progress = 100
                existing.output_files = outputs
                existing.error_message = ""
                existing.completed_time = get_timestamp()
                existing.updated_time = existing.completed_time
                self.db.upsert(existing)
                signal_bus.transcribe.task_updated.emit(existing)
                return True

            if auto_start and existing.status in (TranscribeStatus.READY, TranscribeStatus.FAILED, TranscribeStatus.CANCELED):
                existing.status = TranscribeStatus.QUEUED
                existing.progress = 0
                existing.error_message = ""
                existing.updated_time = get_timestamp()
                self.db.upsert(existing)
                signal_bus.transcribe.task_updated.emit(existing)
                return True

            return False

        now = get_timestamp()
        outputs = self._collect_output_files(video_path)
        status = TranscribeStatus.COMPLETED if outputs else (TranscribeStatus.QUEUED if auto_start else TranscribeStatus.READY)

        task = TranscribeTaskInfo(
            id = str(uuid4()),
            download_task_id = download_task_id,
            video_path = video_path,
            title = title or path.stem,
            status = status,
            progress = 100 if status == TranscribeStatus.COMPLETED else 0,
            output_dir = str(path.parent),
            output_files = outputs,
            created_time = now,
            updated_time = now,
            completed_time = now if status == TranscribeStatus.COMPLETED else 0
        )
        self.db.upsert(task)
        signal_bus.transcribe.task_updated.emit(task)

        return True

    def start_tasks(self, task_ids: list[str]):
        changed = False

        for task_id in task_ids:
            task = self.query_by_id(task_id)

            if not task or task.status == TranscribeStatus.RUNNING:
                continue

            task.status = TranscribeStatus.QUEUED
            task.progress = 0
            task.error_message = ""
            task.started_time = 0
            task.completed_time = 0
            task.updated_time = get_timestamp()
            self.db.upsert(task)
            signal_bus.transcribe.task_updated.emit(task)
            changed = True

        if changed:
            signal_bus.transcribe.tasks_changed.emit()
            signal_bus.transcribe.schedule.emit()

    def retry(self, task_ids: list[str]):
        self.start_tasks(task_ids)

    def cancel(self, task_ids: list[str]):
        changed = False

        for task_id in task_ids:
            runner = self.active_runners.get(task_id)

            if runner:
                runner.cancel()
                continue

            task = self.query_by_id(task_id)

            if not task or task.status not in (TranscribeStatus.QUEUED, TranscribeStatus.RUNNING):
                continue

            task.status = TranscribeStatus.CANCELED
            task.progress = 0
            task.updated_time = get_timestamp()
            self.db.upsert(task)
            signal_bus.transcribe.task_updated.emit(task)
            changed = True

        if changed:
            signal_bus.transcribe.tasks_changed.emit()
            signal_bus.transcribe.schedule.emit()

    def delete_task(self, task_ids: list[str]):
        for task_id in task_ids:
            runner = self.active_runners.get(task_id)

            if runner:
                runner.cancel()

        self.db.delete_tasks(task_ids)
        signal_bus.transcribe.tasks_changed.emit()
        signal_bus.transcribe.schedule.emit()

    def schedule(self):
        max_parallel = config.get(config.transcribe_parallel)

        while len(self.active_runners) < max_parallel:
            task = self._next_queued_task()

            if not task:
                return

            self._start_task(task)

    def shutdown(self):
        for runner in list(self.active_runners.values()):
            runner.cancel()

        self.active_runners.clear()

    def _next_queued_task(self):
        for task in self.query():
            if task.status == TranscribeStatus.QUEUED:
                return task

        return None

    def _start_task(self, task: TranscribeTaskInfo):
        video_path = Path(task.video_path)

        if not video_path.exists():
            task.status = TranscribeStatus.FAILED
            task.error_message = "源视频不存在"
            task.updated_time = get_timestamp()
            self.db.upsert(task)
            signal_bus.transcribe.task_updated.emit(task)
            return

        task.status = TranscribeStatus.RUNNING
        task.progress = 0
        task.started_time = get_timestamp()
        task.updated_time = task.started_time
        task.error_message = ""
        self.db.upsert(task)
        signal_bus.transcribe.task_updated.emit(task)

        runner = TranscribeRunner(
            python_path = config.get(config.transcribe_python_path),
            script_path = config.get(config.transcribe_script_path),
            video_path = task.video_path,
            model_path = self._resolve_model_argument(),
            output_dir = str(video_path.parent),
            language = config.get(config.transcribe_language),
            parent = self
        )
        runner.output.connect(lambda text, task_id = task.id: self._on_output(task_id, text))
        runner.finished.connect(lambda exit_code, exit_status, task_id = task.id: self._on_finished(task_id, exit_code, exit_status))
        runner.failed_to_start.connect(lambda message, task_id = task.id: self._on_failed_to_start(task_id, message))

        self.active_runners[task.id] = runner
        runner.start()

    def _on_output(self, task_id: str, text: str):
        task = self.query_by_id(task_id)

        if not task:
            return

        log = "\n".join((task.log_tail + "\n" + text).splitlines()[-20:])
        task.log_tail = log
        task.progress = max(task.progress, self._parse_progress(text))
        task.updated_time = get_timestamp()
        self.db.upsert(task)
        signal_bus.transcribe.task_updated.emit(task)

    def _on_failed_to_start(self, task_id: str, message: str):
        task = self.query_by_id(task_id)

        if not task:
            return

        task.status = TranscribeStatus.FAILED
        task.error_message = message
        task.updated_time = get_timestamp()
        self.db.upsert(task)
        signal_bus.transcribe.task_updated.emit(task)
        self.active_runners.pop(task_id, None)
        QTimer.singleShot(0, signal_bus.transcribe.schedule.emit)

    def _on_finished(self, task_id: str, exit_code: int, exit_status: int):
        runner = self.active_runners.pop(task_id, None)
        task = self.query_by_id(task_id)

        if not task:
            QTimer.singleShot(0, signal_bus.transcribe.schedule.emit)
            return

        if runner and runner.canceled:
            task.status = TranscribeStatus.CANCELED
            task.progress = 0
            task.error_message = "已取消"
        elif exit_code == 0 and exit_status == 0:
            task.status = TranscribeStatus.COMPLETED
            task.progress = 100
            task.output_files = self._collect_output_files(task.video_path)
            task.error_message = ""
            task.completed_time = get_timestamp()
        else:
            task.status = TranscribeStatus.FAILED
            task.error_message = f"转录进程退出码：{exit_code}"

        task.updated_time = get_timestamp()
        self.db.upsert(task)
        signal_bus.transcribe.task_updated.emit(task)
        signal_bus.transcribe.tasks_changed.emit()
        QTimer.singleShot(0, signal_bus.transcribe.schedule.emit)

    def _resolve_video_paths(self, task_info: TaskInfo):
        base_dir = Path(task_info.File.download_path or config.get(config.download_path), task_info.File.folder)
        candidates = []

        for relative_file in task_info.File.relative_files:
            path = base_dir / relative_file

            if path.exists() and path.suffix.lower() in MEDIA_EXTENSIONS:
                candidates.append(path)

        for ext in (task_info.File.merge_file_ext, task_info.File.video_file_ext, task_info.File.audio_file_ext):
            if not ext:
                continue

            path = base_dir / f"{task_info.File.name}.{ext}"

            if path.exists() and path.suffix.lower() in MEDIA_EXTENSIONS and path not in candidates:
                candidates.append(path)

        return candidates

    def _collect_output_files(self, video_path: str):
        path = Path(video_path)

        return [
            str(output)
            for output in path.parent.glob(f"{path.stem}.large-v3*")
            if output.is_file()
        ]

    def _normalize_video_path(self, video_path: str):
        if not video_path:
            return ""

        try:
            return str(Path(video_path).resolve())
        except OSError:
            return str(Path(video_path).absolute())

    def _parse_progress(self, text: str):
        values = [int(match) for match in re.findall(r"(\d{1,3})\s*%", text)]

        if not values:
            return 0

        return min(99, max(values))

    def _resolve_model_argument(self):
        model_path = config.get(config.transcribe_model_path)

        if model_path:
            return model_path

        model_dir = Path(appdata_path) / "BiliDownTrans" / "models" / "faster-whisper-large-v3"

        return f"{config.get(config.transcribe_model_repo)}|{model_dir}"


transcribe_task_manager = TranscribeTaskManager()
