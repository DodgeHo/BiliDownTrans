from dataclasses import dataclass, asdict, field


class TranscribeStatus:
    READY = "ready"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class TranscribeTaskInfo:
    id: str = ""
    download_task_id: str = ""
    video_path: str = ""
    title: str = ""
    status: str = TranscribeStatus.READY
    progress: int = 0
    output_dir: str = ""
    output_files: list[str] = field(default_factory = list)
    log_tail: str = ""
    error_message: str = ""
    created_time: int = 0
    updated_time: int = 0
    started_time: int = 0
    completed_time: int = 0

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        task = cls()

        for key, value in data.items():
            if hasattr(task, key):
                setattr(task, key, value)

        return task
