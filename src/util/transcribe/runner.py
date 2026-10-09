from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from pathlib import Path
import sys


class TranscribeRunner(QObject):
    output = Signal(str)
    finished = Signal(int, int)
    failed_to_start = Signal(str)

    def __init__(
        self,
        python_path: str,
        script_path: str,
        video_path: str,
        model_path: str,
        output_dir: str,
        language: str,
        parent = None
    ):
        super().__init__(parent)

        self.python_path = python_path
        self.script_path = script_path
        self.video_path = video_path
        self.model_path = model_path
        self.output_dir = output_dir
        self.language = language
        self.canceled = False
        self.process = QProcess(self)

        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.errorOccurred.connect(self._on_error)
        self.process.finished.connect(self._on_finished)

    def start(self):
        self.process.setWorkingDirectory(self.output_dir)

        python_path = self.python_path or sys.executable

        if python_path.lower().endswith("pythonw.exe"):
            candidate = Path(python_path).with_name("python.exe")

            if candidate.exists():
                python_path = str(candidate)
        script_path = Path(self.script_path) if self.script_path else None

        if script_path and script_path.exists():
            arguments = [
                str(script_path),
                self.video_path,
            ]
        else:
            arguments = [
                "-m",
                "util.transcribe.worker",
                self.video_path,
            ]

        arguments.extend([
            "--model",
            self.model_path,
            "--output-dir",
            self.output_dir,
            "--language",
            self.language
        ])

        env = QProcessEnvironment.systemEnvironment()
        src_path = str(Path(__file__).resolve().parents[2])
        old_python_path = env.value("PYTHONPATH", "")
        env.insert("PYTHONPATH", src_path if not old_python_path else f"{src_path};{old_python_path}")
        self.process.setProcessEnvironment(env)

        self.process.setProgram(python_path)
        self.process.setArguments(arguments)
        self.process.start()

    def cancel(self):
        self.canceled = True

        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()

    def _read_stdout(self):
        self._emit_output(self.process.readAllStandardOutput().data())

    def _read_stderr(self):
        self._emit_output(self.process.readAllStandardError().data())

    def _emit_output(self, data: bytes):
        if not data:
            return

        text = data.decode("utf-8", errors = "replace").strip()

        if text:
            self.output.emit(text)

    def _on_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.failed_to_start.emit("无法启动转录进程，请检查 Python 路径")

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus):
        status = 0 if exit_status == QProcess.ExitStatus.NormalExit else 1
        self.finished.emit(exit_code, status)
