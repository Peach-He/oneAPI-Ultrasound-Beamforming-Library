import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets


CONFIG_FILE_NAME = "gui_config.json"


@dataclass
class AppConfig:
    easy_app_path: str = ""
    mock_path: str = ""
    raw_path: str = ""
    output_dir: str = ""


def default_paths() -> AppConfig:
    repo_root = Path(__file__).resolve().parents[1]
    gpu_build = repo_root / "gpu" / "build"
    data_dir = gpu_build / "data"
    res_dir = gpu_build / "res"

    easy_app = gpu_build / "easy_app.exe"
    mock = data_dir / "linearProbe_IPCAI_128-2.mock"
    raw = data_dir / "linearProbe_IPCAI_128-2_0.raw"

    return AppConfig(
        easy_app_path=str(easy_app) if easy_app.exists() else "",
        mock_path=str(mock) if mock.exists() else "",
        raw_path=str(raw) if raw.exists() else "",
        output_dir=str(res_dir),
    )


def load_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        return default_paths()
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return AppConfig(
            easy_app_path=data.get("easy_app_path", ""),
            mock_path=data.get("mock_path", ""),
            raw_path=data.get("raw_path", ""),
            output_dir=data.get("output_dir", ""),
        )
    except Exception:
        # 如果配置损坏，退回默认值
        return default_paths()


def save_config(config_path: Path, cfg: AppConfig) -> None:
    try:
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
    except Exception:
        # 配置保存失败不应影响正常运行
        pass


class RunnerThread(QtCore.QThread):
    line_received = QtCore.Signal(str)
    finished_with_code = QtCore.Signal(int)

    def __init__(self, args: list[str], work_dir: str, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._args = args
        self._work_dir = work_dir

    def run(self) -> None:  # noqa: D401
        """在线程中运行子进程并逐行读取输出。"""
        try:
            proc = subprocess.Popen(
                self._args,
                cwd=self._work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as e:  # noqa: BLE001
            self.line_received.emit(f"[ERROR] 无法启动进程: {e}")
            self.finished_with_code.emit(-1)
            return

        assert proc.stdout is not None
        for line in proc.stdout:
            self.line_received.emit(line.rstrip("\n"))

        proc.wait()
        self.finished_with_code.emit(proc.returncode)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ultrasound Beamforming GUI")
        self.resize(1100, 750)

        self._runner_thread: "RunnerThread | None" = None
        self._image_paths: list[Path] = []
        self._current_pixmap: QtGui.QPixmap | None = None

        self._config_path = Path(__file__).resolve().parent / CONFIG_FILE_NAME
        self._config = load_config(self._config_path)

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 参数区
        params_group = QtWidgets.QGroupBox("参数设置", self)
        params_layout = QtWidgets.QGridLayout(params_group)

        # easy_app.exe
        self.easy_app_edit = QtWidgets.QLineEdit(self._config.easy_app_path, self)
        easy_app_btn = QtWidgets.QPushButton("浏览...", self)
        easy_app_btn.clicked.connect(self._on_browse_easy_app)

        params_layout.addWidget(QtWidgets.QLabel("easy_app.exe 路径:", self), 0, 0)
        params_layout.addWidget(self.easy_app_edit, 0, 1)
        params_layout.addWidget(easy_app_btn, 0, 2)

        # mock
        self.mock_edit = QtWidgets.QLineEdit(self._config.mock_path, self)
        mock_btn = QtWidgets.QPushButton("浏览...", self)
        mock_btn.clicked.connect(self._on_browse_mock)

        params_layout.addWidget(QtWidgets.QLabel(".mock 文件:", self), 1, 0)
        params_layout.addWidget(self.mock_edit, 1, 1)
        params_layout.addWidget(mock_btn, 1, 2)

        # raw
        self.raw_edit = QtWidgets.QLineEdit(self._config.raw_path, self)
        raw_btn = QtWidgets.QPushButton("浏览...", self)
        raw_btn.clicked.connect(self._on_browse_raw)

        params_layout.addWidget(QtWidgets.QLabel(".raw 文件:", self), 2, 0)
        params_layout.addWidget(self.raw_edit, 2, 1)
        params_layout.addWidget(raw_btn, 2, 2)

        # output dir
        self.output_dir_edit = QtWidgets.QLineEdit(self._config.output_dir, self)
        output_btn = QtWidgets.QPushButton("选择目录...", self)
        output_btn.clicked.connect(self._on_browse_output_dir)

        params_layout.addWidget(QtWidgets.QLabel("输出目录:", self), 3, 0)
        params_layout.addWidget(self.output_dir_edit, 3, 1)
        params_layout.addWidget(output_btn, 3, 2)

        # 配置按钮
        btn_save_cfg = QtWidgets.QPushButton("保存配置", self)
        btn_reset_cfg = QtWidgets.QPushButton("恢复默认", self)
        btn_save_cfg.clicked.connect(self._on_save_config_clicked)
        btn_reset_cfg.clicked.connect(self._on_reset_default_clicked)

        cfg_button_layout = QtWidgets.QHBoxLayout()
        cfg_button_layout.addStretch(1)
        cfg_button_layout.addWidget(btn_save_cfg)
        cfg_button_layout.addWidget(btn_reset_cfg)

        params_layout.addLayout(cfg_button_layout, 4, 0, 1, 3)

        # 运行控制区
        control_layout = QtWidgets.QHBoxLayout()
        self.run_button = QtWidgets.QPushButton("运行", self)
        self.status_label = QtWidgets.QLabel("就绪", self)
        self.status_label.setMinimumWidth(200)

        control_layout.addWidget(self.run_button)
        control_layout.addSpacing(20)
        control_layout.addWidget(QtWidgets.QLabel("状态:", self))
        control_layout.addWidget(self.status_label)
        control_layout.addStretch(1)

        # 信息与结果区
        splitter = QtWidgets.QSplitter(self)
        splitter.setOrientation(QtCore.Qt.Horizontal)

        # 左侧：日志
        log_widget = QtWidgets.QWidget(self)
        log_layout = QtWidgets.QVBoxLayout(log_widget)
        log_layout.setContentsMargins(4, 4, 4, 4)
        log_layout.setSpacing(4)

        log_label = QtWidgets.QLabel("运行日志 / 耗时信息", self)
        self.log_edit = QtWidgets.QPlainTextEdit(self)
        self.log_edit.setReadOnly(True)

        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_edit)

        # 右侧：图像浏览（后续步骤中实现具体逻辑）
        right_widget = QtWidgets.QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(4)

        img_top_layout = QtWidgets.QHBoxLayout()
        img_label = QtWidgets.QLabel("结果图像:", self)
        self.image_list = QtWidgets.QComboBox(self)
        img_top_layout.addWidget(img_label)
        img_top_layout.addWidget(self.image_list, 1)

        self.image_view = QtWidgets.QLabel("结果图像将在这里显示", self)
        self.image_view.setAlignment(QtCore.Qt.AlignCenter)
        self.image_view.setStyleSheet("QLabel { background-color: #202020; color: #DDDDDD; }")

        right_layout.addLayout(img_top_layout)
        right_layout.addWidget(self.image_view, 1)

        splitter.addWidget(log_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # 总布局组合
        main_layout.addWidget(params_group)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(splitter, 1)

        # 连接信号
        self.run_button.clicked.connect(self._on_run_clicked)

        self.image_list.currentIndexChanged.connect(self._on_image_selected)

    # ----------------- 运行 easy_app 相关 -----------------
    def _on_run_clicked(self) -> None:
        if self._runner_thread is not None and self._runner_thread.isRunning():
            # 当前简单处理为禁用“停止”功能，避免复杂状态：后续可扩展为真正终止进程
            QtWidgets.QMessageBox.information(
                self,
                "正在运行",
                "程序正在运行，请等待当前运行结束。",
            )
            return

        cfg = self._gather_config_from_ui()

        # 基本校验
        if not cfg.easy_app_path or not os.path.isfile(cfg.easy_app_path):
            QtWidgets.QMessageBox.warning(self, "路径错误", "请正确选择 easy_app.exe 路径。")
            return
        if not cfg.mock_path or not os.path.isfile(cfg.mock_path):
            QtWidgets.QMessageBox.warning(self, "路径错误", "请正确选择 .mock 输入文件。")
            return
        if not cfg.raw_path or not os.path.isfile(cfg.raw_path):
            QtWidgets.QMessageBox.warning(self, "路径错误", "请正确选择 .raw 输入文件。")
            return
        if not cfg.output_dir:
            QtWidgets.QMessageBox.warning(self, "路径错误", "请正确选择输出目录。")
            return

        # 创建输出目录
        try:
            Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(
                self,
                "输出目录错误",
                f"无法创建输出目录：{cfg.output_dir}\n{e}",
            )
            return

        # 清空日志，更新状态
        self.log_edit.clear()
        self.status_label.setText("正在运行...")
        self.run_button.setEnabled(False)

        # 启动后台线程
        args = [
            cfg.easy_app_path,
            cfg.mock_path,
            cfg.raw_path,
            cfg.output_dir,
        ]

        self._runner_thread = RunnerThread(args=args, work_dir=str(Path(cfg.easy_app_path).parent))
        self._runner_thread.line_received.connect(self._append_log_line)
        self._runner_thread.finished_with_code.connect(self._on_run_finished)
        self._runner_thread.start()

    @QtCore.Slot(str)
    def _append_log_line(self, line: str) -> None:
        self.log_edit.appendPlainText(line.rstrip("\n"))
        # 自动滚动到底部
        cursor = self.log_edit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.log_edit.setTextCursor(cursor)

    @QtCore.Slot(int)
    def _on_run_finished(self, exit_code: int) -> None:
        self.run_button.setEnabled(True)
        if exit_code == 0:
            self.status_label.setText("完成")
        else:
            self.status_label.setText(f"失败（退出码 {exit_code}）")

        # 运行完成后刷新结果图像列表
        self._refresh_image_list()

    # ----------------- 结果图像相关 -----------------
    def _refresh_image_list(self) -> None:
        """扫描输出目录中的 PNG 文件并填充下拉列表。"""
        cfg = self._gather_config_from_ui()
        output_dir = Path(cfg.output_dir) if cfg.output_dir else None
        self.image_list.blockSignals(True)
        self.image_list.clear()
        self._image_paths = []
        self._current_pixmap = None
        self.image_view.setText("结果图像将在这里显示")

        if output_dir is None or not output_dir.exists():
            self.image_list.blockSignals(False)
            return

        png_files = sorted(output_dir.glob("*.png"))
        if not png_files:
            self.image_list.blockSignals(False)
            QtWidgets.QMessageBox.information(
                self,
                "未找到图像",
                f"在目录中未找到 PNG 图像：{output_dir}",
            )
            return

        for p in png_files:
            self.image_list.addItem(p.name)
            self._image_paths.append(p)

        self.image_list.blockSignals(False)
        # 默认选择第一个
        self.image_list.setCurrentIndex(0)
        self._load_current_image()

    def _on_image_selected(self, index: int) -> None:
        if index < 0:
            return
        self._load_current_image()

    def _load_current_image(self) -> None:
        idx = self.image_list.currentIndex()
        if idx < 0 or idx >= len(self._image_paths):
            return
        path = self._image_paths[idx]
        pixmap = QtGui.QPixmap(str(path))
        if pixmap.isNull():
            self.image_view.setText(f"无法加载图像：{path.name}")
            self._current_pixmap = None
            return

        self._current_pixmap = pixmap
        self._update_image_view()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: D401
        """在窗口大小变化时自适应缩放图像。"""
        super().resizeEvent(event)
        self._update_image_view()

    def _update_image_view(self) -> None:
        if self._current_pixmap is None:
            return
        label_size = self.image_view.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            return
        scaled = self._current_pixmap.scaled(
            label_size,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        self.image_view.setPixmap(scaled)

    # ----------------- 配置相关操作 -----------------
    def _gather_config_from_ui(self) -> AppConfig:
        return AppConfig(
            easy_app_path=self.easy_app_edit.text().strip(),
            mock_path=self.mock_edit.text().strip(),
            raw_path=self.raw_edit.text().strip(),
            output_dir=self.output_dir_edit.text().strip(),
        )

    def _apply_config_to_ui(self, cfg: AppConfig) -> None:
        self.easy_app_edit.setText(cfg.easy_app_path)
        self.mock_edit.setText(cfg.mock_path)
        self.raw_edit.setText(cfg.raw_path)
        self.output_dir_edit.setText(cfg.output_dir)

    def _on_save_config_clicked(self) -> None:
        cfg = self._gather_config_from_ui()
        save_config(self._config_path, cfg)
        self.status_label.setText("配置已保存")

    def _on_reset_default_clicked(self) -> None:
        cfg = default_paths()
        self._config = cfg
        self._apply_config_to_ui(cfg)
        self.status_label.setText("已恢复默认配置")

    # ----------------- 浏览按钮槽函数 -----------------
    def _on_browse_easy_app(self) -> None:
        current = self.easy_app_edit.text().strip()
        start_dir = os.path.dirname(current) if current else str(Path(__file__).resolve().parents[1] / "gpu" / "build")
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择 easy_app.exe",
            start_dir,
            "Executable (*.exe);;All Files (*)",
        )
        if file_path:
            self.easy_app_edit.setText(file_path)

    def _on_browse_mock(self) -> None:
        current = self.mock_edit.text().strip()
        start_dir = os.path.dirname(current) if current else str(Path(__file__).resolve().parents[1] / "gpu" / "build" / "data")
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择 .mock 文件",
            start_dir,
            "Mock Files (*.mock);;All Files (*)",
        )
        if file_path:
            self.mock_edit.setText(file_path)

    def _on_browse_raw(self) -> None:
        current = self.raw_edit.text().strip()
        start_dir = os.path.dirname(current) if current else str(Path(__file__).resolve().parents[1] / "gpu" / "build" / "data")
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择 .raw 文件",
            start_dir,
            "Raw Files (*.raw);;All Files (*)",
        )
        if file_path:
            self.raw_edit.setText(file_path)

    def _on_browse_output_dir(self) -> None:
        current = self.output_dir_edit.text().strip()
        start_dir = current if current else str(Path(__file__).resolve().parents[1] / "gpu" / "build" / "res")
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            start_dir,
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


