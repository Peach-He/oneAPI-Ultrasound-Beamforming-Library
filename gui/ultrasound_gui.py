import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from PySide6 import QtCore, QtWidgets


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


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ultrasound Beamforming GUI")
        self.resize(1100, 750)

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
        # run_button 的实际逻辑将在后续子进程实现步骤中补充

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


