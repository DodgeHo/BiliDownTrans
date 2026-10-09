from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QTableWidget,
    QTableWidgetItem, QVBoxLayout
)

from qfluentwidgets import BodyLabel, PrimaryPushButton, PushButton, SwitchButton

from util.common.config import config
from util.common.signal_bus import signal_bus
from util.transcribe.info import TranscribeStatus
from util.transcribe.manager import transcribe_task_manager

from datetime import datetime
from pathlib import Path


STATUS_TEXT = {
    TranscribeStatus.READY: "待转录",
    TranscribeStatus.QUEUED: "排队中",
    TranscribeStatus.RUNNING: "转录中",
    TranscribeStatus.COMPLETED: "已完成",
    TranscribeStatus.FAILED: "失败",
    TranscribeStatus.CANCELED: "已取消",
}


class TranscribeInterface(QFrame):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.setObjectName("TranscribeInterface")

        self.init_UI()
        self.connect_signals()

        transcribe_task_manager.sync_completed_downloads(auto_start = False)
        self.refresh()

    def init_UI(self):
        self.auto_label = BodyLabel("下载后自动转录", self)
        self.auto_switch = SwitchButton(self)
        self.auto_switch.setChecked(config.get(config.auto_transcribe_after_download))

        self.add_video_btn = PushButton("添加视频", self)
        self.start_btn = PrimaryPushButton("开始转录", self)
        self.retry_btn = PushButton("重做", self)
        self.cancel_btn = PushButton("取消", self)
        self.delete_btn = PushButton("删除记录", self)
        self.open_dir_btn = PushButton("打开目录", self)
        self.refresh_btn = PushButton("刷新", self)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self.auto_label)
        toolbar_layout.addWidget(self.auto_switch)
        toolbar_layout.addSpacing(12)
        toolbar_layout.addWidget(self.add_video_btn)
        toolbar_layout.addWidget(self.start_btn)
        toolbar_layout.addWidget(self.retry_btn)
        toolbar_layout.addWidget(self.cancel_btn)
        toolbar_layout.addWidget(self.delete_btn)
        toolbar_layout.addWidget(self.open_dir_btn)
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addStretch()

        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["标题", "状态", "进度", "视频路径", "更新时间", "错误/日志"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 15)
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.table)

    def connect_signals(self):
        self.auto_switch.checkedChanged.connect(self.on_auto_switch_changed)
        self.add_video_btn.clicked.connect(self.on_add_video)
        self.start_btn.clicked.connect(self.on_start)
        self.retry_btn.clicked.connect(self.on_retry)
        self.cancel_btn.clicked.connect(self.on_cancel)
        self.delete_btn.clicked.connect(self.on_delete)
        self.open_dir_btn.clicked.connect(self.on_open_dir)
        self.refresh_btn.clicked.connect(self.on_refresh)

        signal_bus.transcribe.tasks_changed.connect(self.refresh)
        signal_bus.transcribe.task_updated.connect(lambda _: self.refresh())

    def refresh(self):
        tasks = transcribe_task_manager.query()

        self.table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            values = [
                task.title or Path(task.video_path).stem,
                STATUS_TEXT.get(task.status, task.status),
                f"{task.progress}%" if task.status != TranscribeStatus.RUNNING or task.progress else "运行中",
                task.video_path,
                self._format_time(task.updated_time),
                self._message(task)
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)

                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, task.id)

                self.table.setItem(row, column, item)

    def selected_task_ids(self):
        ids = []

        for item in self.table.selectedItems():
            row = item.row()
            task_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

            if task_id not in ids:
                ids.append(task_id)

        return ids

    def selected_video_path(self):
        rows = sorted({item.row() for item in self.table.selectedItems()})

        if not rows:
            return ""

        return self.table.item(rows[0], 3).text()

    def on_auto_switch_changed(self, checked: bool):
        config.set(config.auto_transcribe_after_download, checked)

    def on_add_video(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频",
            config.get(config.download_path),
            "Video Files (*.mp4 *.mkv *.flv *.mov *.avi *.webm *.m4v *.ts);;All Files (*)"
        )

        for file_path in files:
            path = Path(file_path)
            transcribe_task_manager.enqueue_task(str(path), path.stem, auto_start = False)

        self.refresh()

    def on_start(self):
        transcribe_task_manager.start_tasks(self.selected_task_ids())

    def on_retry(self):
        transcribe_task_manager.retry(self.selected_task_ids())

    def on_cancel(self):
        transcribe_task_manager.cancel(self.selected_task_ids())

    def on_delete(self):
        transcribe_task_manager.delete_task(self.selected_task_ids())

    def on_open_dir(self):
        video_path = self.selected_video_path()

        if video_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(video_path).parent)))

    def on_refresh(self):
        transcribe_task_manager.sync_completed_downloads(auto_start = False)
        self.refresh()

    def _format_time(self, timestamp: int):
        if not timestamp:
            return ""

        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def _message(self, task):
        if task.error_message:
            return task.error_message

        if task.log_tail:
            return task.log_tail.splitlines()[-1]

        return ""
