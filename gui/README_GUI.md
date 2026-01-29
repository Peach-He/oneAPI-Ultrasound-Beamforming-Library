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

## 界面与功能简介

- **参数设置区**：
  - `easy_app.exe 路径`：选择在 `gpu/build/` 下生成的 `easy_app.exe` 可执行文件。
  - `.mock 文件` / `.raw 文件`：选择 `gpu/build/data/` 目录中的示例输入数据，或你自己的数据。
  - `输出目录`：选择/填写结果图像输出目录（默认建议为 `gpu/build/res`，不存在时会自动创建）。
  - 可以通过“保存配置”按钮将当前设置写入 `gui/gui_config.json`，下次启动会自动加载。

- **运行与日志**：
  - 点击 “运行” 按钮后，GUI 会在后台启动子进程：
    - 命令形式：`easy_app.exe <mock> <raw> <output_dir>`。
  - 终端中的输出（包括各 kernel 的耗时信息）会实时显示在左侧“运行日志 / 耗时信息”区域。
  - 运行结束后状态栏会显示“完成”或“失败（退出码 X）”。

- **结果图像浏览**：
  - 程序结束后，会自动扫描输出目录下的所有 `*.png` 文件。
  - 右侧顶部下拉框列出所有找到的 PNG，选择不同条目可切换查看。
  - 图像区域会根据窗口大小自动等比例缩放显示图像。

## 注意事项

- 请先按照主仓库 `README.md` 的说明完成 oneAPI 环境配置和 `easy_app.exe` 的编译。
- 若执行后未看到任何 PNG 图像，请先查看左侧日志中的错误信息，并确认输出目录设置是否正确。

