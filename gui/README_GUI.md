# Ultrasound Beamforming GUI

该 GUI 程序是对命令行工具 `easy_app.exe` 的一个简单封装，便于通过图形界面选择输入文件、运行并查看结果图像。

## 依赖安装

1. 安装 Python 3.9+（建议 64 位）。
2. 在本仓库根目录下执行：

```bash
cd gui
pip install -r requirements.txt
```

## 运行 GUI

在仓库根目录下或 `gui` 目录中执行：

```bash
python gui/ultrasound_gui.py
```

首次启动时仅会显示一个简单窗口，后续会逐步完善为可配置 `easy_app.exe`、输入数据路径和输出目录，并展示运行日志和结果 PNG 图像。

