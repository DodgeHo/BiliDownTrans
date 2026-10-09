from ..common._json import dumps, loads
from ..common.config import appdata_path
from ..common.database import Database
from .info import TranscribeTaskInfo, TranscribeStatus

from pathlib import Path


class TranscribeTaskDB(Database):
    def __init__(self):
        super().__init__()

        self.path = Path(appdata_path) / "BiliDownTrans" / "transcribe_task.db"
        self.path.parent.mkdir(parents = True, exist_ok = True)

        self.check_and_create_table()
        self.recover_running_tasks()

    def check_and_create_table(self):
        self.execute_script("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS "transcribe_task" (
                "id" TEXT PRIMARY KEY,
                "download_task_id" TEXT,
                "video_path" TEXT UNIQUE,
                "title" TEXT,
                "status" TEXT,
                "progress" INTEGER,
                "created_time" INTEGER,
                "updated_time" INTEGER,
                "started_time" INTEGER,
                "completed_time" INTEGER,
                "data" TEXT
            );
            CREATE INDEX IF NOT EXISTS "idx_transcribe_task_status" ON "transcribe_task" ("status");
            CREATE INDEX IF NOT EXISTS "idx_transcribe_task_updated_time" ON "transcribe_task" ("updated_time");
        """)

    def recover_running_tasks(self):
        rows = self.query('SELECT data FROM "transcribe_task" WHERE "status" = ?', (TranscribeStatus.RUNNING,))

        for row in rows:
            task = TranscribeTaskInfo.from_dict(loads(row[0]))
            task.status = TranscribeStatus.FAILED
            task.progress = 0
            task.error_message = "程序上次退出时任务仍在运行，请重做"
            task.started_time = 0
            self.upsert(task)

    def query_tasks(self):
        return self.query(
            'SELECT data FROM "transcribe_task" ORDER BY "updated_time" DESC, "created_time" DESC'
        )

    def query_task_by_id(self, task_id: str):
        return self.query('SELECT data FROM "transcribe_task" WHERE "id" = ?', (task_id,))

    def query_task_by_video_path(self, video_path: str):
        return self.query('SELECT data FROM "transcribe_task" WHERE "video_path" = ?', (video_path,))

    def upsert(self, task: TranscribeTaskInfo):
        data = dumps(task.to_dict())

        self.execute("""
            INSERT INTO transcribe_task (
                id, download_task_id, video_path, title, status, progress,
                created_time, updated_time, started_time, completed_time, data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_path) DO UPDATE SET
                download_task_id = excluded.download_task_id,
                title = excluded.title,
                status = excluded.status,
                progress = excluded.progress,
                updated_time = excluded.updated_time,
                started_time = excluded.started_time,
                completed_time = excluded.completed_time,
                data = excluded.data
        """, (
            task.id,
            task.download_task_id,
            task.video_path,
            task.title,
            task.status,
            task.progress,
            task.created_time,
            task.updated_time,
            task.started_time,
            task.completed_time,
            data
        ))

    def delete_tasks(self, task_ids: list[str]):
        if not task_ids:
            return

        for index in range(0, len(task_ids), 500):
            batch = task_ids[index:index + 500]
            placeholders = ", ".join("?" * len(batch))
            self.execute(f'DELETE FROM "transcribe_task" WHERE "id" IN ({placeholders})', tuple(batch))
