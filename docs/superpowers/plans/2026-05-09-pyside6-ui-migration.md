# PySide6 UI 迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前 tkinter GUI（`app.py` ~1077 行）替换为 PySide6 实现，1:1 还原 `mockups/light_ui_prototype.html` 浅色主题设计稿；pipeline / matcher / hotkey / config 大体保留，仅 `capture.py` 加 1 行 + `defaults.py` 增删若干键。

**Architecture:** 单 `QMainWindow` + 左侧 sidebar (`QListWidget`) + 右侧 `QStackedWidget` 三页（扫描 / 设置 / 关于）。系统 titlebar，QSS 翻译 mockup 的 CSS。Pipeline 在 `QThread` 里跑，结果通过 Signal 推回主线程。Overlay 用 `QWidget + WA_TranslucentBackground + WindowTransparentForInput` 重写。

**Tech Stack:** PySide6 6.x（LGPL 动态链接）、现有 PaddleOCR / mss / pyahocorasick / keyboard / pyyaml 全部不动。

**前置文档：** `docs/PYSIDE6_MIGRATION.md` —— 设计决策、key 命名、风险表、阶段总览都在那里。本计划只展开「怎么做」。

---

## 文件结构

新增：

```
ui/
├── __init__.py
├── main_window.py          # QMainWindow + sidebar + QStackedWidget
├── pages/
│   ├── __init__.py
│   ├── scan_page.py        # 扫描页：装载 config_panel + log_panel + status_bar
│   ├── settings_page.py    # QScrollArea + 5 张卡（其中热键卡 disabled）
│   └── about_page.py       # 静态：版本/作者/依赖
├── widgets/
│   ├── __init__.py
│   ├── sidebar.py          # 自绘 QListWidget
│   ├── config_panel.py     # 4 个 group + 启动按钮
│   ├── log_panel.py        # QPlainTextEdit + 着色
│   └── status_bar.py       # 4 字段 + QTimer 刷新内存
├── overlay.py              # 阶段 4 才完整实现，3a 用 OverlayStub
├── overlay_stub.py         # 阶段 3a 占位
├── scan_worker.py          # QThread worker：3 个 Signal
├── tray.py                 # QSystemTrayIcon
├── log_bridge.py           # logging.Handler → Signal
└── styles/
    └── light.qss           # 从 mockup CSS 翻译

tests/
├── test_config_keys.py     # ROI 重命名 + reset_to_defaults
└── test_capture_enable_roi.py
```

修改：

| 文件 | 改动 |
|---|---|
| `app.py` | 完全重写为 ~50 行 PySide6 启动入口 |
| `defaults.py` | rename `'roi'` → `'roi_rect'`；新增 `APP_VERSION`、`'app'` 块 |
| `cli.py` | `scan.roi` → `scan.roi_rect` |
| `src/pipeline/capture.py` | `grab()` 加 1 行 `enable_roi` 检查 |
| `old_version/app.py` | `scan.roi` → `scan.roi_rect`（4 处） |
| `old_version/cli.py` | 检查并重命名（如有） |
| `old_version/src/core/scan_service.py` | 间接引用更新 |
| `requirements.txt` | 加 `PySide6>=6.7.0`，最后清理 `pystray` / `pillow`（如已无引用） |
| `gui.bat` | 启动入口不变（仍 `app.py`），但 app.py 已是 PySide6 |

---

## Stage 1：启动骨架（0.5 天）

### Task 1：分支 + 依赖

**Files:**
- Modify: `requirements.txt`
- Branch: `feature/pyside6`（基于 `feature/light_ui`）

- [ ] **Step 1：创建分支**

```bash
git checkout feature/light_ui
git pull
git checkout -b feature/pyside6
```

- [ ] **Step 2：装 PySide6**

```bash
.venv\Scripts\pip install PySide6
```

预期：装上 PySide6 6.7.x 或更高（含 PySide6-Essentials + shiboken6）。

- [ ] **Step 3：更新 requirements.txt**

在末尾追加：

```
PySide6>=6.7.0
```

- [ ] **Step 4：验证导入**

```bash
.venv\Scripts\python -c "from PySide6.QtWidgets import QApplication; print('OK')"
```

预期输出：`OK`。

- [ ] **Step 5：commit**

```bash
git add requirements.txt
git commit -m "deps: add PySide6 for UI migration"
```

---

### Task 2：MainWindow 骨架 + sidebar + 三页占位

**Files:**
- Create: `ui/__init__.py`（空）
- Create: `ui/main_window.py`
- Create: `ui/pages/__init__.py`（空）
- Create: `ui/pages/scan_page.py`
- Create: `ui/pages/settings_page.py`
- Create: `ui/pages/about_page.py`
- Create: `ui/widgets/__init__.py`（空）
- Create: `ui/widgets/sidebar.py`

- [ ] **Step 1：创建空 page 模块**

`ui/pages/scan_page.py`：

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class ScanPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('扫描页（占位）'))
```

`ui/pages/settings_page.py` 与 `ui/pages/about_page.py` 同模板，类名 `SettingsPage` / `AboutPage`，文案改成「设置页（占位）」/「关于页（占位）」。

- [ ] **Step 2：创建 sidebar widget**

`ui/widgets/sidebar.py`：

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem


class Sidebar(QListWidget):
    """三项导航：扫描 / 设置 / 关于。currentRowChanged 已是 Qt 内置信号，可直接连接。"""

    PAGE_SCAN = 0
    PAGE_SETTINGS = 1
    PAGE_ABOUT = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        for label in ('扫描', '设置', '关于'):
            self.addItem(QListWidgetItem(label))
        self.setCurrentRow(0)
        self.setObjectName('sidebar')   # 给 QSS 选中
```

- [ ] **Step 3：创建 MainWindow**

`ui/main_window.py`：

```python
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget

from .widgets.sidebar import Sidebar
from .pages.scan_page import ScanPage
from .pages.settings_page import SettingsPage
from .pages.about_page import AboutPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('屏幕扫描 OCR 识别系统')
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(160)
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.scan_page = ScanPage()
        self.settings_page = SettingsPage()
        self.about_page = AboutPage()
        self.stack.addWidget(self.scan_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.about_page)
        layout.addWidget(self.stack, 1)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
```

- [ ] **Step 4：重写 app.py 入口**

`app.py`（覆盖原 1077 行 tkinter 实现 —— 新建一个 `app.py.tk_backup` 留底以便对照）：

```bash
git mv app.py app.py.tk_backup
```

新建 `app.py`：

```python
"""PySide6 入口。原 tkinter 实现已重命名为 app.py.tk_backup（迁移完成后删除）。"""

import os
import sys

from PySide6.QtWidgets import QApplication

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.config import config
from ui.main_window import MainWindow


def main():
    config.load()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
```

- [ ] **Step 5：手动验证**

```bash
.venv\Scripts\python app.py
```

预期：弹出无样式窗口（1280x800），左侧 sidebar 三行（扫描/设置/关于），点击切换右侧占位文案。系统 titlebar 显示「屏幕扫描 OCR 识别系统」。

- [ ] **Step 6：commit**

```bash
git add ui/ app.py app.py.tk_backup
git commit -m "feat(ui): MainWindow skeleton with sidebar + 3 placeholder pages"
```

---

### Task 3：light.qss 色板（第一版）

**Files:**
- Create: `ui/styles/__init__.py`（空）
- Create: `ui/styles/light.qss`
- Modify: `app.py`

- [ ] **Step 1：从 mockup 提取色板**

打开 `mockups/light_ui_prototype.html`，定位 `:root` 块（约 line 30-60）。把所有 `--xxx: #xxx;` 列出来，例如：

```
--bg: #F5F7FA;
--card: #FFFFFF;
--text: #1F2937;
--text-secondary: #6B7280;
--border: #E5E7EB;
--brand: #2F6FEB;
--brand-hover: #2557C7;
--success: #10B981;
--warning: #F59E0B;
--danger: #EF4444;
```

（实际颜色以 mockup 为准，QSS 没有 `var()`，需要手动展开。）

- [ ] **Step 2：写 light.qss 第一版**

`ui/styles/light.qss`：

```css
/* 主窗口背景 */
QMainWindow, QWidget {
    background-color: #F5F7FA;
    color: #1F2937;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* Sidebar */
QListWidget#sidebar {
    background-color: #FFFFFF;
    border-right: 1px solid #E5E7EB;
    outline: 0;
}
QListWidget#sidebar::item {
    padding: 12px 16px;
    border-left: 3px solid transparent;
}
QListWidget#sidebar::item:selected {
    background-color: #EEF2FF;
    color: #2F6FEB;
    border-left: 3px solid #2F6FEB;
}
QListWidget#sidebar::item:hover {
    background-color: #F3F4F6;
}
```

（占位最小集；后续 Task 11 大幅扩展。）

- [ ] **Step 3：在 app.py 加载 QSS**

修改 `main()` 函数，在 `app = QApplication(...)` 之后加：

```python
qss_path = os.path.join(PROJECT_ROOT, 'ui', 'styles', 'light.qss')
with open(qss_path, encoding='utf-8') as f:
    app.setStyleSheet(f.read())
```

- [ ] **Step 4：手动验证**

```bash
.venv\Scripts\python app.py
```

预期：sidebar 现在白底，三项有 padding，选中项左侧蓝条 + 蓝色文字 + 浅蓝背景；hover 灰背景。背景色从 Qt 默认浅灰变成 `#F5F7FA`。

- [ ] **Step 5：commit**

```bash
git add ui/styles/ app.py
git commit -m "feat(ui): add light.qss color palette + sidebar styling"
```

---

## Stage 2：扫描页（2 天，主战场）

### Task 4：ROI key 重命名（6 文件原子改动）

**Files:**
- Create: `tests/__init__.py`（空）
- Create: `tests/test_config_keys.py`
- Modify: `defaults.py:28`
- Modify: `cli.py:21`
- Modify: `app.py.tk_backup` lines 522/579/664/684
- Modify: `old_version/app.py` lines 642/645/657
- Modify: `old_version/src/core/scan_service.py`（如有 `scan.roi` 字符串）

> **重要**：本任务必须原子完成（一次 commit），否则 `feature/light_ui` 上现版 tk 与新版 PySide6 会读不同 key 互相打架。

- [ ] **Step 1：写 failing test**

`tests/test_config_keys.py`：

```python
"""验证 ROI key 重命名后 defaults 里没有旧 key 'roi'，新 key 'roi_rect' 存在。"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from defaults import DEFAULT_CONFIG


def test_roi_renamed():
    scan = DEFAULT_CONFIG['scan']
    assert 'roi' not in scan, "旧 key 'roi' 仍存在，重命名未完成"
    assert 'roi_rect' in scan, "新 key 'roi_rect' 不存在"
    assert scan['roi_rect'] == [1170, 256, 1880, 843]


def test_enable_roi_intact():
    assert DEFAULT_CONFIG['scan']['enable_roi'] is True


if __name__ == '__main__':
    test_roi_renamed()
    test_enable_roi_intact()
    print('PASS')
```

- [ ] **Step 2：跑测试，确认失败**

```bash
.venv\Scripts\python tests\test_config_keys.py
```

预期：`AssertionError: 旧 key 'roi' 仍存在`。

- [ ] **Step 3：改 defaults.py**

`defaults.py:26-28`：

```python
        # 当前生效的 ROI 坐标 [x1, y1, x2, y2]，屏幕绝对像素；None = 未保存。
        # 默认 [1170, 256, 1880, 843] 是项目工作区域，开箱即用。
        # （旧名 'roi' 已重命名为 'roi_rect'，避免「None=禁用 / coords=启用」二义性，
        #  开关由 enable_roi 单独承担。）
        'roi_rect': [1170, 256, 1880, 843],
```

- [ ] **Step 4：跑测试，确认通过**

```bash
.venv\Scripts\python tests\test_config_keys.py
```

预期：`PASS`。

- [ ] **Step 5：grep 全仓 + 改其他 5 文件**

```bash
git grep -n "scan\.roi[^_]" -- ":!docs" ":!*.md"
```

对每条结果（除 `scan.roi_padding` / `scan.roi_presets` / `scan.roi_rect`），把 `'scan.roi'` 字符串改成 `'scan.roi_rect'`。预期改动点：
- `cli.py:21` —— `config.get('scan.roi')` → `config.get('scan.roi_rect')`
- `app.py.tk_backup:522/579/664/684` —— 四处
- `old_version/app.py:642/645/657` —— 三处
- `old_version/src/core/scan_service.py` —— grep 后按需改
- `old_version/cli.py` —— grep 后按需改

- [ ] **Step 6：用户的 yaml 兼容**

如 `config/config.yaml` 里有用户保存的 `scan.roi: [...]`（非默认 None），手动 rename 为 `scan.roi_rect`。本仓库 `config/config.yaml` 当前未含 `scan.roi`，跳过。

- [ ] **Step 7：旧 tk 版回归测试**

```bash
.venv\Scripts\python app.py.tk_backup
```

预期：旧 tk GUI 正常打开，「使用已保存 ROI」日志显示 `[1170, 256, 1880, 843]`，扫描正常（按 Ctrl+Alt+1 / Ctrl+Alt+2）。

- [ ] **Step 8：commit**

```bash
git add tests/ defaults.py cli.py app.py.tk_backup old_version/
git commit -m "refactor(config): rename scan.roi -> scan.roi_rect across 6 files"
```

---

### Task 5：capture.py 加 enable_roi 防御读

**Files:**
- Create: `tests/test_capture_enable_roi.py`
- Modify: `src/pipeline/capture.py`

- [ ] **Step 1：写 failing test**

`tests/test_capture_enable_roi.py`：

```python
"""capture.grab() 在 enable_roi=False 时应忽略传入的 roi 参数，回退全屏。
不实际截屏，mock mss 的 grab 调用，验证 monitor 字典即可。"""

import os
import sys
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.config.config import config
from src.pipeline.capture import CaptureStage


def _mock_sct():
    sct = MagicMock()
    sct.monitors = [None, {'left': 0, 'top': 0, 'width': 1920, 'height': 1080}]
    grab_result = MagicMock()
    import numpy as np
    grab_result.__array__ = lambda self: np.zeros((10, 10, 4), dtype=np.uint8)
    sct.grab = MagicMock(return_value=grab_result)
    return sct


def test_enable_roi_false_forces_fullscreen():
    config.load()
    config.set('scan.enable_roi', False)
    cap = CaptureStage()
    with patch('src.pipeline.capture.mss.mss', return_value=_mock_sct()):
        cap.grab(roi=(100, 100, 500, 500))
    monitor = cap.sct.grab.call_args[0][0]
    # enable_roi=False 必须走全屏分支：monitor == sct.monitors[1]
    assert monitor == cap.sct.monitors[1], f'未回退全屏，实际 monitor={monitor}'


def test_enable_roi_true_uses_roi():
    config.load()
    config.set('scan.enable_roi', True)
    cap = CaptureStage()
    with patch('src.pipeline.capture.mss.mss', return_value=_mock_sct()):
        cap.grab(roi=(100, 100, 500, 500))
    monitor = cap.sct.grab.call_args[0][0]
    assert monitor['width'] == 400 + 2 * 10, '未应用 ROI（含 padding）'


if __name__ == '__main__':
    test_enable_roi_false_forces_fullscreen()
    test_enable_roi_true_uses_roi()
    print('PASS')
```

- [ ] **Step 2：跑测试，确认 false 那条失败**

```bash
.venv\Scripts\python tests\test_capture_enable_roi.py
```

预期：第一个测试 fail（当前 capture.py 不读 enable_roi）。

- [ ] **Step 3：改 capture.py**

`src/pipeline/capture.py:34` 之前插入：

```python
        # 防御性二次校验：如果 config 关闭了 ROI，无视调用方传入的 roi
        if roi is not None and not config.get('scan.enable_roi'):
            roi = None

```

- [ ] **Step 4：跑测试，确认全部通过**

```bash
.venv\Scripts\python tests\test_capture_enable_roi.py
```

预期：`PASS`。

- [ ] **Step 5：旧 tk 回归**

```bash
.venv\Scripts\python app.py.tk_backup
```

预期：勾选「启用 ROI」时仍按 ROI 截屏；取消勾选时全屏（GUI 通过 `pipeline.set_roi(None)` 已经实现，capture 这层是兜底）。

- [ ] **Step 6：commit**

```bash
git add tests/ src/pipeline/capture.py
git commit -m "feat(capture): defensive enable_roi check in CaptureStage.grab"
```

---

### Task 6：defaults.py 新增 APP_VERSION + app 块

**Files:**
- Modify: `defaults.py`

- [ ] **Step 1：在文件顶部加常量**

`defaults.py` 第 16 行（`DEFAULT_BANLIST_FILE` 后）追加：

```python
APP_VERSION = '1.0.0'
```

- [ ] **Step 2：在 DEFAULT_CONFIG 末尾加 app 块**

在 `'performance': {...},` 行之后（字典闭合前）追加：

```python
    'app': {                              # 新版专有：PySide6 GUI 通用设置
        'minimize_to_tray': True,         # 关闭主窗口时缩进系统托盘
        'startup_mode': 'paused',         # 'paused' = 启动后停在待机；'auto' = 等 OCR 加载完自动开扫
    },
```

- [ ] **Step 3：扩展 test_config_keys.py**

追加测试：

```python
def test_app_block_exists():
    from defaults import DEFAULT_CONFIG, APP_VERSION
    assert APP_VERSION == '1.0.0'
    assert DEFAULT_CONFIG['app']['minimize_to_tray'] is True
    assert DEFAULT_CONFIG['app']['startup_mode'] in ('paused', 'auto')
```

并在 `if __name__ == '__main__':` 块加 `test_app_block_exists()` 调用。

- [ ] **Step 4：跑测试**

```bash
.venv\Scripts\python tests\test_config_keys.py
```

预期：`PASS`。

- [ ] **Step 5：commit**

```bash
git add defaults.py tests/test_config_keys.py
git commit -m "feat(config): add APP_VERSION constant and app.* defaults block"
```

---

### Task 7：scan_page.py 骨架

**Files:**
- Modify: `ui/pages/scan_page.py`

- [ ] **Step 1：用 mockup 主窗口右半部分的结构搭骨架**

mockup 主窗口右侧 = config-panel（中）+ log-panel（右）+ status-bar（下）。`ScanPage` 用 `QGridLayout` 三区域：

```python
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QLabel, QFrame
)


class ScanPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 占位三块；具体 widget 在 Task 8/9/10 装入
        self.config_panel_holder = QFrame()
        self.config_panel_holder.setObjectName('configPanelHolder')
        self.config_panel_holder.setMinimumWidth(320)
        QVBoxLayout(self.config_panel_holder).addWidget(QLabel('config_panel 占位'))

        self.log_panel_holder = QFrame()
        self.log_panel_holder.setObjectName('logPanelHolder')
        QVBoxLayout(self.log_panel_holder).addWidget(QLabel('log_panel 占位'))

        self.status_bar_holder = QFrame()
        self.status_bar_holder.setObjectName('statusBarHolder')
        self.status_bar_holder.setFixedHeight(32)
        QVBoxLayout(self.status_bar_holder).addWidget(QLabel('status_bar 占位'))

        layout.addWidget(self.config_panel_holder, 0, 0)
        layout.addWidget(self.log_panel_holder, 0, 1)
        layout.addWidget(self.status_bar_holder, 1, 0, 1, 2)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 1)
```

- [ ] **Step 2：手动验证**

```bash
.venv\Scripts\python app.py
```

预期：扫描页（默认显示）出现三块灰色占位区，左窄 + 右宽 + 底栏。其它页仍是占位。

- [ ] **Step 3：commit**

```bash
git add ui/pages/scan_page.py
git commit -m "feat(ui): scan page layout skeleton (3-region grid)"
```

---

### Task 8：config_panel.py（4 group + 启动按钮）

**Files:**
- Create: `ui/widgets/config_panel.py`
- Modify: `ui/pages/scan_page.py`

- [ ] **Step 1：实现 ConfigPanel 4 个 group**

`ui/widgets/config_panel.py`：

```python
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox,
    QSlider, QLineEdit, QPushButton, QFrame, QFileDialog
)

from src.config.config import config


def _make_group(title):
    """工具：返回 (容器 QFrame, 内层 QVBoxLayout)。"""
    frame = QFrame()
    frame.setObjectName('configGroup')
    box = QVBoxLayout(frame)
    box.setContentsMargins(12, 12, 12, 12)
    box.setSpacing(8)
    title_lbl = QLabel(title)
    title_lbl.setObjectName('groupTitle')
    box.addWidget(title_lbl)
    return frame, box


def _slider(min_v, max_v, value, on_change, scale=1):
    """整数 slider；scale 用于浮点（例如间隔 0.5–10s 用 scale=10）。"""
    s = QSlider(Qt.Horizontal)
    s.setMinimum(int(min_v * scale))
    s.setMaximum(int(max_v * scale))
    s.setValue(int(value * scale))
    label = QLabel(str(value))
    s.valueChanged.connect(lambda v: (label.setText(f'{v/scale:g}'), on_change(v / scale)))
    wrap = QHBoxLayout()
    wrap.addWidget(s, 1)
    wrap.addWidget(label)
    return wrap


class ConfigPanel(QWidget):
    """主窗口左侧配置区：4 个 group + Action 按钮组。
    所有控件双向绑定 config 单例。"""

    start_clicked = Signal()
    stop_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self._build_roi_group())
        layout.addWidget(self._build_pace_group())
        layout.addWidget(self._build_ocr_group())
        layout.addWidget(self._build_match_group())
        layout.addLayout(self._build_action_row())
        layout.addStretch(1)

    # ----- 扫描区域 -----
    def _build_roi_group(self):
        frame, box = _make_group('扫描区域')

        self.cb_enable_roi = QCheckBox('启用 ROI')
        self.cb_enable_roi.setChecked(bool(config.get('scan.enable_roi')))
        self.cb_enable_roi.stateChanged.connect(
            lambda s: (config.set('scan.enable_roi', bool(s)), config.save())
        )

        self.cb_remember_roi = QCheckBox('记住区域')
        self.cb_remember_roi.setChecked(bool(config.get('scan.remember_roi')))
        self.cb_remember_roi.stateChanged.connect(
            lambda s: (config.set('scan.remember_roi', bool(s)), config.save())
        )
        toggle_row = QHBoxLayout()
        toggle_row.addWidget(self.cb_enable_roi)
        toggle_row.addWidget(self.cb_remember_roi)
        toggle_row.addStretch(1)
        box.addLayout(toggle_row)

        box.addWidget(QLabel('ROI 预设'))
        preset_row = QHBoxLayout()
        self.combo_preset = QComboBox()
        self._reload_presets()
        self.combo_preset.currentTextChanged.connect(self._on_preset_changed)
        btn_save_preset = QPushButton('保存当前')
        btn_save_preset.clicked.connect(self._on_save_preset)
        preset_row.addWidget(self.combo_preset, 1)
        preset_row.addWidget(btn_save_preset)
        box.addLayout(preset_row)
        return frame

    def _reload_presets(self):
        self.combo_preset.blockSignals(True)
        self.combo_preset.clear()
        presets = config.get('scan.roi_presets') or {}
        for name in presets.keys():
            self.combo_preset.addItem(name)
        self.combo_preset.blockSignals(False)

    def _on_preset_changed(self, name):
        if not name:
            return
        presets = config.get('scan.roi_presets') or {}
        if name in presets:
            config.set('scan.roi_rect', list(presets[name]))
            config.save()

    def _on_save_preset(self):
        from PySide6.QtWidgets import QInputDialog
        roi = config.get('scan.roi_rect')
        if not roi:
            return
        name, ok = QInputDialog.getText(self, '保存预设', '预设名称：')
        if ok and name:
            presets = config.get('scan.roi_presets') or {}
            presets[name] = list(roi)
            config.set('scan.roi_presets', presets)
            config.save()
            self._reload_presets()
            self.combo_preset.setCurrentText(name)

    # ----- 扫描节奏 -----
    def _build_pace_group(self):
        frame, box = _make_group('扫描节奏')
        box.addWidget(QLabel('扫描间隔（秒）'))
        box.addLayout(_slider(
            0.5, 10.0, float(config.get('scan.interval_seconds') or 5.0),
            lambda v: (config.set('scan.interval_seconds', round(v, 1)), config.save()),
            scale=10,
        ))
        return frame

    # ----- OCR 识别 -----
    def _build_ocr_group(self):
        frame, box = _make_group('OCR 识别')
        row = QHBoxLayout()
        row.addWidget(QLabel('语言'))
        self.combo_lang = QComboBox()
        for code, name in (('ch', 'ch (中文)'), ('en', 'en (English)')):
            self.combo_lang.addItem(name, code)
        cur = config.get('ocr.language') or 'ch'
        idx = self.combo_lang.findData(cur)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentIndexChanged.connect(
            lambda _: (config.set('ocr.language', self.combo_lang.currentData()), config.save())
        )
        row.addWidget(self.combo_lang)
        self.cb_gpu = QCheckBox('GPU 加速')
        self.cb_gpu.setChecked(bool(config.get('gpu.enabled')))
        self.cb_gpu.stateChanged.connect(
            lambda s: (config.set('gpu.enabled', bool(s)), config.save())
        )
        row.addWidget(self.cb_gpu)
        row.addStretch(1)
        box.addLayout(row)

        box.addWidget(QLabel('最小置信度'))
        box.addLayout(_slider(
            0.0, 1.0, float(config.get('ocr.min_confidence') or 0.3),
            lambda v: (config.set('ocr.min_confidence', round(v, 2)), config.save()),
            scale=100,
        ))
        return frame

    # ----- 关键词匹配 -----
    def _build_match_group(self):
        frame, box = _make_group('关键词匹配')
        box.addWidget(QLabel('词库文件'))
        row = QHBoxLayout()
        self.le_banlist = QLineEdit(str(config.get('files.banlist_file') or ''))
        self.le_banlist.setReadOnly(True)
        btn_browse = QPushButton('浏览…')
        btn_browse.clicked.connect(self._on_browse_banlist)
        row.addWidget(self.le_banlist, 1)
        row.addWidget(btn_browse)
        box.addLayout(row)

        box.addWidget(QLabel('匹配后显示时长（秒）'))
        box.addLayout(_slider(
            0.5, 10.0, float(config.get('matching.display_duration') or 3.0),
            lambda v: (config.set('matching.display_duration', round(v, 1)), config.save()),
            scale=10,
        ))
        return frame

    def _on_browse_banlist(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择关键词文件', '', 'Text (*.txt);;All (*)')
        if path:
            self.le_banlist.setText(path)
            config.set('files.banlist_file', path)
            config.save()

    # ----- Action 按钮 -----
    def _build_action_row(self):
        row = QVBoxLayout()
        self.btn_start = QPushButton('▶ 开始扫描   Ctrl+Alt+1')
        self.btn_start.setObjectName('btnPrimary')
        self.btn_start.clicked.connect(self.start_clicked.emit)
        self.btn_stop = QPushButton('■ 停止扫描   Ctrl+Alt+2')
        self.btn_stop.setObjectName('btnDanger')
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_stop)
        return row

    def reload_from_config(self):
        """重置配置后由 MainWindow 调用，刷新所有 widget 显示值。"""
        self.cb_enable_roi.setChecked(bool(config.get('scan.enable_roi')))
        self.cb_remember_roi.setChecked(bool(config.get('scan.remember_roi')))
        self._reload_presets()
        self.cb_gpu.setChecked(bool(config.get('gpu.enabled')))
        cur = config.get('ocr.language') or 'ch'
        idx = self.combo_lang.findData(cur)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.le_banlist.setText(str(config.get('files.banlist_file') or ''))
        # slider 由调用方重建更稳；此处简化省略
```

- [ ] **Step 2：装到 scan_page.py**

`ui/pages/scan_page.py`，把 `config_panel_holder` 替换为真正的 `ConfigPanel`：

```python
from ui.widgets.config_panel import ConfigPanel

# 在 __init__ 里：
self.config_panel = ConfigPanel()
layout.addWidget(self.config_panel, 0, 0)
# 删掉 config_panel_holder 相关 4 行
```

- [ ] **Step 3：手动验证**

```bash
.venv\Scripts\python app.py
```

预期：扫描页左侧出现 4 个 group + 2 个按钮；勾选 / 拖动滑块 / 改 ROI 预设后，关掉 app 再开，状态保留（写入了 config.yaml）。

```bash
type config\config.yaml
```

预期：能看到刚才改过的 key/value。

- [ ] **Step 4：commit**

```bash
git add ui/widgets/config_panel.py ui/pages/scan_page.py
git commit -m "feat(ui): ConfigPanel with 4 groups + action buttons (config-bound)"
```

---

### Task 9：log_panel.py + log_bridge.py

**Files:**
- Create: `ui/widgets/log_panel.py`
- Create: `ui/log_bridge.py`
- Modify: `ui/pages/scan_page.py`

- [ ] **Step 1：log_panel.py**

`ui/widgets/log_panel.py`：

```python
from PySide6.QtCore import Slot
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QLabel


_LEVEL_COLORS = {
    'DEBUG': '#06B6D4',
    'INFO': '#1F2937',
    'WARNING': '#F59E0B',
    'ERROR': '#EF4444',
}


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(QLabel('运行日志'))
        header.addStretch(1)
        btn_clear = QPushButton('清空日志')
        btn_clear.clicked.connect(self._clear)
        header.addWidget(btn_clear)
        layout.addLayout(header)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(10000)
        self.text.setObjectName('logText')
        layout.addWidget(self.text, 1)

    @Slot(str, str)
    def append(self, level, message):
        color = _LEVEL_COLORS.get(level.upper(), '#1F2937')
        cursor = self.text.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(message + '\n')
        self.text.setTextCursor(cursor)
        self.text.ensureCursorVisible()

    def _clear(self):
        self.text.clear()
```

- [ ] **Step 2：log_bridge.py**

`ui/log_bridge.py`：

```python
"""把 logging.Handler 的输出桥到 PySide6 Signal。
worker QThread 也可以通过它发送日志（间接经由 logging.getLogger）。"""

import logging

from PySide6.QtCore import QObject, Signal


class LogBridge(QObject, logging.Handler):
    record_emitted = Signal(str, str)  # (level_name, formatted_message)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        fmt = logging.Formatter('%(asctime)s.%(msecs)03d - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.setFormatter(fmt)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.record_emitted.emit(record.levelname, msg)
        except Exception:
            self.handleError(record)
```

- [ ] **Step 3：装到 scan_page**

`ui/pages/scan_page.py`：

```python
from ui.widgets.log_panel import LogPanel

# 在 __init__ 里：
self.log_panel = LogPanel()
layout.addWidget(self.log_panel, 0, 1)
# 删掉 log_panel_holder
```

- [ ] **Step 4：MainWindow 装 log_bridge**

`ui/main_window.py` `__init__` 末尾追加：

```python
import logging
from .log_bridge import LogBridge

self.log_bridge = LogBridge()
logging.getLogger().addHandler(self.log_bridge)
logging.getLogger().setLevel(logging.INFO)
self.log_bridge.record_emitted.connect(self.scan_page.log_panel.append)
```

- [ ] **Step 5：手动验证**

在 `app.py` 的 `main()` 末尾、`window.show()` 之前临时加：

```python
import logging
logging.getLogger().info('hello info')
logging.getLogger().warning('hello warning')
logging.getLogger().error('hello error')
```

跑 `python app.py`，预期日志面板出现三行不同颜色文字。验证后**删掉这三行临时代码**。

- [ ] **Step 6：commit**

```bash
git add ui/widgets/log_panel.py ui/log_bridge.py ui/pages/scan_page.py ui/main_window.py
git commit -m "feat(ui): LogPanel + LogBridge (logging.Handler -> Signal)"
```

---

### Task 10：status_bar.py

**Files:**
- Create: `ui/widgets/status_bar.py`
- Modify: `ui/pages/scan_page.py`

- [ ] **Step 1：实现 StatusBar**

`ui/widgets/status_bar.py`：

```python
from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from defaults import APP_VERSION


def _get_memory_mb():
    """搬自 app.py.tk_backup:_get_memory_mb，纯 Win32 ctypes。"""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t),
            ]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        h = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
            return pmc.WorkingSetSize / 1024 / 1024
    except Exception:
        pass
    return None


class StatusBar(QWidget):
    """4 字段：运行状态 / 内存 / 版本 / 引擎。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(16)

        self.lbl_status = QLabel('● 运行状态：初始化中')
        self.lbl_mem = QLabel('内存占用：-- MB')
        self.lbl_version = QLabel(f'版本：{APP_VERSION}')
        self.lbl_engine = QLabel('引擎：加载中')
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_mem)
        layout.addStretch(1)
        layout.addWidget(self.lbl_version)
        layout.addWidget(self.lbl_engine)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_memory)
        self._timer.start(5000)
        self._refresh_memory()

    @Slot()
    def _refresh_memory(self):
        mb = _get_memory_mb()
        if mb is not None:
            self.lbl_mem.setText(f'内存占用：{mb:.1f} MB')

    @Slot(str)
    def set_status(self, text):
        self.lbl_status.setText(f'● 运行状态：{text}')

    @Slot(str)
    def set_engine(self, version_str):
        """version_str 形如 '3.2.2'，显示成 'PaddleOCR 3.x'。"""
        major = version_str.split('.')[0]
        self.lbl_engine.setText(f'引擎：PaddleOCR {major}.x')
```

- [ ] **Step 2：装到 scan_page**

`ui/pages/scan_page.py`：

```python
from ui.widgets.status_bar import StatusBar

# 在 __init__ 里：
self.status_bar = StatusBar()
self.status_bar.setFixedHeight(32)
layout.addWidget(self.status_bar, 1, 0, 1, 2)
# 删掉 status_bar_holder
```

- [ ] **Step 3：手动验证**

`python app.py`：

预期：底栏显示「● 运行状态：初始化中  内存占用：XX.X MB」+ 右侧「版本：1.0.0  引擎：加载中」。等 5 秒后内存数字会刷新。

- [ ] **Step 4：commit**

```bash
git add ui/widgets/status_bar.py ui/pages/scan_page.py
git commit -m "feat(ui): StatusBar with 4 fields + 5s memory refresh"
```

---

### Task 11：light.qss 大幅扩展（CSS → QSS 翻译）

**Files:**
- Modify: `ui/styles/light.qss`

> 本任务是**视觉对齐**主战场，工时占 Stage 2 的相当一部分。逐 group 翻译，按 mockup CSS 实测对照。

- [ ] **Step 1：翻译 group 卡片样式**

参 mockup `.group` / `.group-title` CSS（`box-shadow` 用 `QGraphicsDropShadowEffect` 改外加，QSS 写圆角 + border）：

```css
QFrame#configGroup {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
}
QLabel#groupTitle {
    font-weight: 600;
    color: #1F2937;
    padding-bottom: 4px;
    border-bottom: 1px solid #E5E7EB;
}
```

`ConfigPanel._make_group` 末尾给 frame 加阴影（一次性、轻量）：

```python
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

shadow = QGraphicsDropShadowEffect(frame)
shadow.setBlurRadius(8)
shadow.setOffset(0, 1)
shadow.setColor(QColor(0, 0, 0, 20))
frame.setGraphicsEffect(shadow)
```

- [ ] **Step 2：翻译按钮 / 输入 / select / slider / checkbox**

继续往 `light.qss` 追加（关键样式骨架，颜色与 mockup 对齐）：

```css
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover { border-color: #2F6FEB; color: #2F6FEB; }
QPushButton#btnPrimary {
    background-color: #2F6FEB; color: white; border: none;
    padding: 10px 16px; font-weight: 600;
}
QPushButton#btnPrimary:hover { background-color: #2557C7; }
QPushButton#btnDanger {
    background-color: #EF4444; color: white; border: none;
    padding: 10px 16px; font-weight: 600;
}
QPushButton#btnDanger:hover { background-color: #DC2626; }

QLineEdit, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
}
QComboBox::drop-down { border: none; width: 20px; }

QSlider::groove:horizontal {
    border: none; height: 4px; background: #E5E7EB; border-radius: 2px;
}
QSlider::sub-page:horizontal { background: #2F6FEB; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #FFFFFF; border: 2px solid #2F6FEB;
    width: 12px; height: 12px; margin: -6px 0; border-radius: 8px;
}

QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #E5E7EB; border-radius: 3px;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked { background-color: #2F6FEB; border-color: #2F6FEB; }

QPlainTextEdit#logText {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    font-family: "Consolas", "Microsoft YaHei", monospace;
    font-size: 12px;
}
```

- [ ] **Step 3：翻译 status bar 与 sidebar 残留细节**

按 mockup `.status-bar` 视觉，给 `StatusBar` 加底色与上边框：

```css
StatusBar {
    background-color: #F9FAFB;
    border-top: 1px solid #E5E7EB;
    color: #6B7280;
}
```

并给 `Sidebar` 顶部留一段 spacer（在 `Sidebar.__init__` 里 `self.setSpacing(2); self.setContentsMargins(0,16,0,0)`）。

- [ ] **Step 4：手动比对 mockup**

并排打开 `mockups/light_ui_prototype.html`（浏览器）与 `python app.py`。逐 group 视觉对照。允许 ±5px 偏差。预期出入项记到 `docs/PYSIDE6_MIGRATION.md` 末尾或单独 issue（不在本任务修复非阻塞偏差）。

- [ ] **Step 5：commit**

```bash
git add ui/styles/light.qss ui/widgets/config_panel.py
git commit -m "style(ui): translate mockup CSS to QSS for groups/buttons/inputs/sliders"
```

---

## Stage 3a：pipeline 接入（1 天）

### Task 12：ScanWorker QThread + 3 Signal

**Files:**
- Create: `ui/scan_worker.py`

- [ ] **Step 1：ScanWorker 实现**

`ui/scan_worker.py`：

```python
"""把现有 ScanPipeline 包装成 QThread worker。
3 个 Signal：
  init_done(str)         OCR init 完成后发，参数 = PaddleOCR 版本字符串
  result_ready(object)   每次 scan_once 完成时发，参数 = ScanResult
  log_message(str, str)  level + message（备用，目前 logging.Handler 已直接走 LogBridge）
"""

import time
import threading

from PySide6.QtCore import QObject, QThread, Signal, Slot

from src.config.config import config
from src.pipeline.pipeline import ScanPipeline


class ScanWorker(QObject):
    init_done = Signal(str)
    result_ready = Signal(object)
    log_message = Signal(str, str)
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.pipeline = ScanPipeline()
        self._stop_event = threading.Event()
        self._scanning = False

    @Slot()
    def init(self):
        """阻塞式：在 worker 线程里调，完成后发 init_done。
        @Slot() 装饰是 QMetaObject.invokeMethod 跨线程调用的前提。"""
        self.pipeline.init()
        try:
            import paddleocr
            ver = paddleocr.__version__
        except Exception:
            ver = '?.?.?'
        self.init_done.emit(ver)

    @Slot(object)
    def set_roi(self, roi):
        """主线程随时调用；不需要 stop。"""
        self.pipeline.set_roi(roi)

    @Slot()
    def start_scanning(self):
        """开始扫描循环。在 worker 线程里跑。"""
        self._stop_event.clear()
        self._scanning = True
        while not self._stop_event.is_set():
            interval = float(config.get('scan.interval_seconds') or 5.0)
            try:
                result = self.pipeline.scan_once()
                self.result_ready.emit(result)
            except Exception as e:
                self.log_message.emit('ERROR', f'scan_once 异常: {e}')
            # 简易可中断 sleep
            for _ in range(int(interval * 10)):
                if self._stop_event.is_set():
                    break
                time.sleep(0.1)
        self._scanning = False
        self.finished.emit()

    @Slot()
    def stop_scanning(self):
        self._stop_event.set()

    @Slot()
    def shutdown(self):
        self.stop_scanning()
        self.pipeline.release()
```

- [ ] **Step 2：单独冒烟 verify**

新建临时脚本 `tests/_smoke_worker.py`（用完删掉）：

```python
"""手动跑一次 worker init + 单帧扫描，验证 Signal 能发出来。"""

import sys
from PySide6.QtCore import QCoreApplication, QThread

sys.path.insert(0, '.')
from src.config.config import config
from ui.scan_worker import ScanWorker

config.load()
app = QCoreApplication([])
worker = ScanWorker()
thread = QThread()
worker.moveToThread(thread)


def on_init_done(ver):
    print(f'init_done: PaddleOCR {ver}')
    app.quit()


worker.init_done.connect(on_init_done)
thread.started.connect(worker.init)
thread.start()
app.exec()
worker.shutdown()
thread.quit()
thread.wait()
```

```bash
.venv\Scripts\python tests\_smoke_worker.py
```

预期：等 OCR 加载（首次较慢），打印 `init_done: PaddleOCR 3.x.x` 后退出。

```bash
del tests\_smoke_worker.py
```

- [ ] **Step 3：commit**

```bash
git add ui/scan_worker.py
git commit -m "feat(ui): ScanWorker QThread wrapping ScanPipeline with 3 Signals"
```

---

### Task 13：OverlayStub

**Files:**
- Create: `ui/overlay_stub.py`

- [ ] **Step 1：实现 stub**

`ui/overlay_stub.py`：

```python
"""阶段 3a 的 overlay 占位。方法签名与 shared/overlay.Overlay 完全一致，
全部 no-op；update 在命中关键词时打 debug 日志（便于验证流程通了）。
阶段 4 的 ui/overlay.py 完成后，MainWindow 替换持有引用即可。"""

import logging

logger = logging.getLogger(__name__)


class OverlayStub:
    def __init__(self, *args, **kwargs):
        logger.debug('OverlayStub created (stage 3a placeholder)')

    def setup(self):
        pass

    def update(self, ocr_results, matches):
        if matches:
            kws = [m.get('keyword', '?') for m in matches]
            logger.debug(f'[stub overlay] 命中 {len(matches)} 条: {kws}')

    def hide(self):
        pass

    def clear_session(self):
        pass

    def destroy(self):
        pass
```

- [ ] **Step 2：commit**

```bash
git add ui/overlay_stub.py
git commit -m "feat(ui): OverlayStub for stage 3a (no-op placeholder)"
```

---

### Task 14：MainWindow 接入 worker + ROI 流 + Overlay

**Files:**
- Modify: `ui/main_window.py`

- [ ] **Step 1：MainWindow 装 worker + overlay stub**

在 `MainWindow.__init__` 末尾追加：

```python
from PySide6.QtCore import QThread

from src.config.config import config
from .scan_worker import ScanWorker
from .overlay_stub import OverlayStub

# overlay：3a 阶段用 stub，阶段 4 才换真实 ui.overlay.Overlay
self.overlay = OverlayStub(parent_root=self, config=config, logger=None)

# worker
self._thread = QThread(self)
self.worker = ScanWorker()
self.worker.moveToThread(self._thread)
self._thread.start()

# Signals
self.worker.init_done.connect(self._on_init_done)
self.worker.result_ready.connect(self._on_scan_result)
self.worker.finished.connect(lambda: self.scan_page.status_bar.set_status('已停止'))

# Action 按钮
self.scan_page.config_panel.start_clicked.connect(self._on_start_clicked)
self.scan_page.config_panel.stop_clicked.connect(self._on_stop_clicked)

# 启动 OCR init（worker 线程异步）
self.scan_page.status_bar.set_status('初始化中')
from PySide6.QtCore import QMetaObject, Qt
QMetaObject.invokeMethod(self.worker, 'init', Qt.QueuedConnection)
```

- [ ] **Step 2：实现 slot**

`MainWindow` 类内追加：

```python
@Slot(str)
def _on_init_done(self, version):
    self.scan_page.status_bar.set_engine(version)
    self.scan_page.status_bar.set_status('待机')

@Slot(object)
def _on_scan_result(self, result):
    if result.skipped:
        return
    self.overlay.update(result.ocr_results, result.matches)

def _compute_roi(self):
    if not config.get('scan.enable_roi'):
        return None
    rect = config.get('scan.roi_rect')
    if rect is None:
        import logging
        logging.getLogger().warning('enable_roi=True 但 roi_rect 未设置，本次回退全屏')
        return None
    return tuple(rect)

@Slot()
def _on_start_clicked(self):
    roi = self._compute_roi()
    self.worker.set_roi(roi)
    self.overlay.clear_session()
    self.scan_page.status_bar.set_status('运行中')
    QMetaObject.invokeMethod(self.worker, 'start_scanning', Qt.QueuedConnection)

@Slot()
def _on_stop_clicked(self):
    self.worker.stop_scanning()
    self.overlay.hide()
```

补 import：`from PySide6.QtCore import Slot`。

- [ ] **Step 3：closeEvent 关 worker**

`MainWindow` 类内追加：

```python
def closeEvent(self, event):
    self.worker.shutdown()
    self._thread.quit()
    self._thread.wait(2000)
    super().closeEvent(event)
```

- [ ] **Step 4：手动验证完整流程**

```bash
.venv\Scripts\python app.py
```

预期：
1. 状态栏「初始化中」→ 几秒后变「待机」+ 引擎字段显示「PaddleOCR 3.x」
2. 点「开始扫描」→ 状态栏「运行中」，日志面板每隔 N 秒打 OCR 结果
3. ROI toggle 切到 off 后再开扫，截全屏
4. 点「停止扫描」→ 状态栏「已停止」，日志停更
5. 命中关键词时日志里出现 `[stub overlay] 命中 N 条: [...]`（debug 级别需把 logger 级别调到 DEBUG 才能看到，否则只在控制台 print）

- [ ] **Step 5：commit**

```bash
git add ui/main_window.py
git commit -m "feat(ui): MainWindow integrates ScanWorker + ROI flow + OverlayStub"
```

---

## Stage 3b：设置页 + 关于页（1 天）

### Task 15：settings_page.py（5 卡）

**Files:**
- Modify: `ui/pages/settings_page.py`

- [ ] **Step 1：完整实现 5 卡**

```python
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QCheckBox, QComboBox, QSlider, QPushButton, QMessageBox
)

from src.config.config import config


def _card(title):
    frame = QFrame()
    frame.setObjectName('settingsCard')
    box = QVBoxLayout(frame)
    box.setContentsMargins(16, 16, 16, 16)
    box.setSpacing(10)
    lbl = QLabel(title)
    lbl.setObjectName('cardTitle')
    box.addWidget(lbl)
    return frame, box


def _row(label_text, widget):
    row = QHBoxLayout()
    row.addWidget(QLabel(label_text))
    row.addStretch(1)
    row.addWidget(widget)
    return row


class SettingsPage(QWidget):
    reset_requested = Signal()  # 由 MainWindow 接管，触发整体 reload

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        inner = QWidget()
        scroll.setWidget(inner)
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(self._card_general())
        layout.addWidget(self._card_scan())
        layout.addWidget(self._card_overlay())
        layout.addWidget(self._card_hotkey())
        layout.addWidget(self._card_config_mgmt())
        layout.addStretch(1)

    def _card_general(self):
        frame, box = _card('常规设置')

        cb_tray = QCheckBox()
        cb_tray.setChecked(bool(config.get('app.minimize_to_tray')))
        cb_tray.stateChanged.connect(
            lambda s: (config.set('app.minimize_to_tray', bool(s)), config.save())
        )
        box.addLayout(_row('最小化到托盘', cb_tray))

        combo_mode = QComboBox()
        combo_mode.addItem('暂停扫描', 'paused')
        combo_mode.addItem('自动开始', 'auto')
        cur = config.get('app.startup_mode') or 'paused'
        idx = combo_mode.findData(cur)
        combo_mode.setCurrentIndex(max(0, idx))
        combo_mode.currentIndexChanged.connect(
            lambda _: (config.set('app.startup_mode', combo_mode.currentData()), config.save())
        )
        box.addLayout(_row('启动后默认状态', combo_mode))
        return frame

    def _card_scan(self):
        frame, box = _card('扫描配置')
        box.addWidget(QLabel('帧差阈值'))
        s = QSlider(Qt.Horizontal)
        s.setRange(0, 200)  # 0-20.0 with scale=10
        s.setValue(int(float(config.get('scan.diff_threshold') or 5.0) * 10))
        lbl = QLabel(f"{config.get('scan.diff_threshold'):g}")
        s.valueChanged.connect(
            lambda v: (lbl.setText(f'{v/10:g}'),
                       config.set('scan.diff_threshold', round(v / 10, 1)),
                       config.save())
        )
        wrap = QHBoxLayout()
        wrap.addWidget(s, 1)
        wrap.addWidget(lbl)
        box.addLayout(wrap)
        return frame

    def _card_overlay(self):
        frame, box = _card('浮窗提示')

        box.addWidget(QLabel('字号'))
        s_size = QSlider(Qt.Horizontal)
        s_size.setRange(10, 48)
        s_size.setValue(int(config.get('matching.font_size') or 18))
        lbl_size = QLabel(str(s_size.value()))
        s_size.valueChanged.connect(
            lambda v: (lbl_size.setText(str(v)),
                       config.set('matching.font_size', v),
                       config.save())
        )
        size_row = QHBoxLayout()
        size_row.addWidget(s_size, 1)
        size_row.addWidget(lbl_size)
        box.addLayout(size_row)

        combo_pos = QComboBox()
        for code, name in (('center', '居中'), ('top', '顶部'), ('bottom', '底部')):
            combo_pos.addItem(name, code)
        cur = config.get('matching.position') or 'center'
        idx = combo_pos.findData(cur)
        combo_pos.setCurrentIndex(max(0, idx))
        combo_pos.currentIndexChanged.connect(
            lambda _: (config.set('matching.position', combo_pos.currentData()), config.save())
        )
        box.addLayout(_row('位置', combo_pos))

        cb_sound = QCheckBox()
        cb_sound.setChecked(bool(config.get('matching.enable_sound')))
        cb_sound.stateChanged.connect(
            lambda s: (config.set('matching.enable_sound', bool(s)), config.save())
        )
        box.addLayout(_row('音效提醒', cb_sound))
        return frame

    def _card_hotkey(self):
        frame, box = _card('热键设置（敬请期待）')
        frame.setEnabled(False)  # 整卡 disabled
        box.addWidget(QLabel('开始/暂停扫描   Ctrl + Alt + 1'))
        box.addWidget(QLabel('停止扫描        Ctrl + Alt + 2'))
        return frame

    def _card_config_mgmt(self):
        frame, box = _card('配置管理')
        btn_reset = QPushButton('重置全部配置')
        btn_reset.setObjectName('btnDanger')
        btn_reset.clicked.connect(self._on_reset_clicked)
        box.addLayout(_row('恢复出厂默认（不可撤销）', btn_reset))
        return frame

    def _on_reset_clicked(self):
        ret = QMessageBox.warning(
            self, '重置配置',
            '确认要重置全部配置吗？\n\n'
            '会清空：\n'
            '  · 所有自定义 ROI 预设\n'
            '  · 当前 ROI 坐标\n'
            '  · 关键词文件路径\n'
            '  · 所有滑块/下拉/开关的当前值\n\n'
            '此操作不可撤销。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret == QMessageBox.Yes:
            self.reset_requested.emit()
```

- [ ] **Step 2：手动验证**

`python app.py`，切到「设置」页：

预期：5 张卡可滚动，常规/扫描配置/浮窗提示/配置管理 4 张正常交互；热键卡灰色不可点。改字号/位置/音效后切回扫描页，再回设置页，状态保留（写到 config.yaml）。

- [ ] **Step 3：commit**

```bash
git add ui/pages/settings_page.py
git commit -m "feat(ui): SettingsPage with 5 cards (hotkey card disabled)"
```

---

### Task 16：about_page.py

**Files:**
- Modify: `ui/pages/about_page.py`

- [ ] **Step 1：实现 AboutPage**

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from defaults import APP_VERSION


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        title = QLabel('ScreenScanOCRRecognize')
        title.setStyleSheet('font-size: 24px; font-weight: 700;')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        meta = QLabel(f'版本 {APP_VERSION}  ·  © 2026 yhluo9')
        meta.setStyleSheet('color: #6B7280;')
        meta.setAlignment(Qt.AlignCenter)
        layout.addWidget(meta)

        link = QLabel('<a href="https://github.com/yhluo9/ScreenScanOCRRecognize">GitHub</a>')
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignCenter)
        layout.addWidget(link)

        deps = QLabel(
            '<b>第三方依赖</b><br>'
            '· PaddleOCR (Apache-2.0)<br>'
            '· pyahocorasick (BSD-3)<br>'
            '· PySide6 (LGPL-3，动态链接)<br>'
            '· keyboard / mss / pyyaml'
        )
        deps.setAlignment(Qt.AlignCenter)
        deps.setStyleSheet('color: #6B7280;')
        layout.addWidget(deps)
```

- [ ] **Step 2：手动验证**

`python app.py`，点击 sidebar「关于」。预期：居中文字 + 可点击 GitHub 链接（点击会用默认浏览器打开）。

- [ ] **Step 3：commit**

```bash
git add ui/pages/about_page.py
git commit -m "feat(ui): AboutPage with version + deps acknowledgement"
```

---

### Task 17：reset_to_defaults 接入

**Files:**
- Modify: `ui/main_window.py`
- Modify: `ui/widgets/config_panel.py`（如需补 reload）
- Create: `tests/test_reset_defaults.py`

- [ ] **Step 1：写 failing test**

`tests/test_reset_defaults.py`：

```python
import copy
import os
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from defaults import DEFAULT_CONFIG
from src.config.config import config


def test_reset_clears_user_changes():
    # 用临时 yaml 文件加载，避免污染真实 config.yaml
    fd, tmp = tempfile.mkstemp(suffix='.yaml')
    os.close(fd)
    try:
        config.load(tmp)
        config.set('scan.diff_threshold', 99.9)
        config.save()
        # 重置
        config._data = copy.deepcopy(DEFAULT_CONFIG)
        config.save()
        # 重新读
        config._loaded = False
        config.load(tmp)
        assert config.get('scan.diff_threshold') == DEFAULT_CONFIG['scan']['diff_threshold']
    finally:
        os.unlink(tmp)


if __name__ == '__main__':
    test_reset_clears_user_changes()
    print('PASS')
```

```bash
.venv\Scripts\python tests\test_reset_defaults.py
```

预期：PASS（这其实只是验证 `_data` 直赋的语义，无需修改 Config 类）。

- [ ] **Step 2：MainWindow 接 reset_requested**

`ui/main_window.py` `__init__` 末尾追加：

```python
self.settings_page.reset_requested.connect(self._on_reset_config)
```

类内追加：

```python
@Slot()
def _on_reset_config(self):
    import copy
    from defaults import DEFAULT_CONFIG
    config._data = copy.deepcopy(DEFAULT_CONFIG)
    config.save()
    self.scan_page.config_panel.reload_from_config()
    # settings_page 自己的 widget 也得刷，最简：重建整个 settings_page
    self.stack.removeWidget(self.settings_page)
    from .pages.settings_page import SettingsPage
    self.settings_page = SettingsPage()
    self.settings_page.reset_requested.connect(self._on_reset_config)
    self.stack.insertWidget(1, self.settings_page)
    import logging
    logging.getLogger().info('配置已重置为默认值')
```

> 注：重建 `settings_page` 是务实做法，避免给所有 widget 写 `reload_from_config`。

- [ ] **Step 3：手动验证**

`python app.py`：
1. 改帧差阈值滑块到 15
2. 切到设置页，点「重置全部配置」→ 弹窗确认
3. 切回扫描页，看刚才改过的值是否回默认

预期：所有 GUI 控件回默认；`config/config.yaml` 内容也回默认。

- [ ] **Step 4：commit**

```bash
git add ui/main_window.py tests/test_reset_defaults.py
git commit -m "feat(ui): wire settings_page reset_requested to reload-from-defaults"
```

---

### Task 18：startup_mode='auto' 接入

**Files:**
- Modify: `ui/main_window.py`

- [ ] **Step 1：在 init_done slot 里 fork**

修改 `_on_init_done`：

```python
@Slot(str)
def _on_init_done(self, version):
    self.scan_page.status_bar.set_engine(version)
    self.scan_page.status_bar.set_status('待机')
    if config.get('app.startup_mode') == 'auto':
        import logging
        logging.getLogger().info('startup_mode=auto，自动开始扫描')
        self._on_start_clicked()
```

- [ ] **Step 2：手动验证**

```bash
.venv\Scripts\python app.py
```

到设置页把「启动后默认状态」改成「自动开始」，关闭 app，再开。

预期：等 OCR 加载完成（状态栏从「初始化中」→「待机」），紧接着自动变成「运行中」，扫描循环开始。

切回「暂停扫描」再重启，预期：停在「待机」，不自动开扫。

- [ ] **Step 3：commit**

```bash
git add ui/main_window.py
git commit -m "feat(ui): wire startup_mode=auto to auto-start scan after OCR init"
```

---

## Stage 4：Overlay 重写（1 天）

### Task 19：ui/overlay.py 骨架（透明窗 + 鼠标穿透）

**Files:**
- Create: `ui/overlay.py`

- [ ] **Step 1：基础骨架**

```python
"""PySide6 浮窗：真 alpha 通道 + 鼠标穿透。
方法签名与 OverlayStub / shared.overlay.Overlay 完全一致，便于 MainWindow 平滑替换。"""

import io
import math
import struct
import threading
import wave

try:
    import winsound
    _SOUND_OK = True
except ImportError:
    _SOUND_OK = False

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics
from PySide6.QtWidgets import QWidget, QApplication


def _build_chord_wav():
    """C 大三和弦 WAV，搬自 shared/overlay.py。"""
    sample_rate = 22050
    duration = 0.35
    n = int(sample_rate * duration)
    freqs = [523.25, 659.25, 783.99]
    samples = []
    for i in range(n):
        t = i / sample_rate
        fade = min(t / 0.05, 1.0) * min((duration - t) / 0.08, 1.0)
        val = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
        samples.append(int(val * fade * 16000))
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f'<{n}h', *samples))
    return buf.getvalue()


_CHORD = _build_chord_wav()


class Overlay(QWidget):
    def __init__(self, parent_root=None, config=None, logger=None):
        super().__init__(None)
        self._cfg = config
        self._logger = logger
        self._session = {}
        self._ocr_results = []
        self._matches = []

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def setup(self):
        pass  # Qt 下构造时已完成

    def update(self, ocr_results, matches):
        new_kw = []
        for m in matches:
            kw = m.get('keyword', '')
            if kw and kw not in self._session:
                self._session[kw] = m.get('hint', '')
                new_kw.append(kw)
        self._ocr_results = ocr_results
        self._matches = matches

        if new_kw and self._cfg_get('matching.enable_sound', True) and _SOUND_OK:
            threading.Thread(
                target=lambda: winsound.PlaySound(_CHORD, winsound.SND_MEMORY),
                daemon=True
            ).start()

        self._reposition_and_show()

    def clear_session(self):
        self._session.clear()

    def hide(self):
        self._hide_timer.stop()
        super().hide()

    def destroy(self):
        self.hide()
        super().deleteLater()

    def _cfg_get(self, key, default):
        if self._cfg is None:
            return default
        try:
            v = self._cfg.get(key, default)
        except TypeError:
            v = self._cfg.get(key)
        return v if v is not None else default
```

- [ ] **Step 2：commit**

```bash
git add ui/overlay.py
git commit -m "feat(overlay): PySide6 Overlay skeleton with translucent + click-through"
```

---

### Task 20：paintEvent 渲染（左右双列 + 阴影）

**Files:**
- Modify: `ui/overlay.py`

- [ ] **Step 1：实现 _reposition_and_show + paintEvent**

`Overlay` 类内追加：

```python
def _reposition_and_show(self):
    font_size = max(10, int(self._cfg_get('matching.font_size', 18)) - 2)
    font = QFont('Microsoft YaHei', font_size, QFont.Bold)
    fm = QFontMetrics(font)
    line_h = int(fm.lineSpacing() * 1.15)

    matched_kws = {m['keyword'] for m in self._matches if m.get('keyword')}

    # 屏幕封顶
    screen = QApplication.primaryScreen().size()
    sw, sh = screen.width(), screen.height()

    # 左列：累计匹配
    left = sorted(self._session.items(), key=lambda kv: kv[0].casefold())
    if not left:
        left_rows = [('暂无匹配', '', '#aaaaaa', '#aaaaaa')]
    else:
        left_rows = [(kw, hint, '#ff3333', '#ff3333') for kw, hint in left]

    # 右列：命中行（红）+ 未命中前 10（绿）+ 摘要
    matched_lines = []
    unmatched = []
    for r in self._ocr_results:
        text = r.get('text', '') if isinstance(r, dict) else ''
        if not text:
            continue
        cf = text.casefold()
        hit = [kw for kw in matched_kws if kw.casefold() in cf]
        if hit:
            matched_lines.append((min(k.casefold() for k in hit), text))
        else:
            unmatched.append(text)
    matched_lines.sort(key=lambda x: x[0])
    right_rows = [(t, '#ff3333') for _, t in matched_lines]
    for t in unmatched[:10]:
        right_rows.append((t, '#00ff00'))
    if len(unmatched) > 10:
        right_rows.append((f'+ {len(unmatched) - 10} 行未显示', '#888888'))
    if not right_rows:
        right_rows.append(('暂无识别结果', '#aaaaaa'))

    # 列宽（封顶）
    kw_cap, hint_cap, ocr_cap = int(sw * 0.20), int(sw * 0.20), int(sw * 0.40)
    max_kw = min(max((fm.horizontalAdvance(r[0]) for r in left_rows), default=0), kw_cap)
    max_hint = min(max((fm.horizontalAdvance(r[1]) for r in left_rows), default=0), hint_cap)
    max_ocr = min(max((fm.horizontalAdvance(r[0]) for r in right_rows), default=0), ocr_cap)

    pad, gap_kw, gap_mid = 6, 12, 28
    total_w = pad + max_kw + gap_kw + max_hint + gap_mid + max_ocr + 2 + pad
    rows = max(len(left_rows), len(right_rows))
    total_h = rows * line_h + 8

    pos = self._cfg_get('matching.position', 'center')
    if pos == 'top':
        x, y = (sw - total_w) // 2, 50
    elif pos == 'bottom':
        x, y = (sw - total_w) // 2, sh - total_h - 50
    else:
        x, y = (sw - total_w) // 2, (sh - total_h) // 2

    self.setGeometry(x, y, total_w, total_h)
    self._render_meta = dict(
        font=font, line_h=line_h, pad=pad, gap_kw=gap_kw, gap_mid=gap_mid,
        max_kw=max_kw, max_hint=max_hint,
        left_rows=left_rows, right_rows=right_rows,
    )
    self.update()  # 触发 paintEvent（QWidget.update，不是我们的方法）
    self.show()
    duration = float(self._cfg_get('matching.display_duration', 3.0))
    self._hide_timer.start(int(duration * 1000))

def paintEvent(self, event):
    if not hasattr(self, '_render_meta'):
        return
    m = self._render_meta
    p = QPainter(self)
    p.setFont(m['font'])
    fm = QFontMetrics(m['font'])
    ascent = fm.ascent()
    pad, gap_kw, gap_mid = m['pad'], m['gap_kw'], m['gap_mid']
    kw_x = pad
    hint_x = kw_x + m['max_kw'] + gap_kw
    ocr_x = hint_x + m['max_hint'] + gap_mid

    def draw(x, y, text, color):
        if not text:
            return
        # 阴影
        p.setPen(QColor('#000000'))
        p.drawText(x + 1, y + 1, text)
        p.setPen(QColor(color))
        p.drawText(x, y, text)

    rows = max(len(m['left_rows']), len(m['right_rows']))
    for i in range(rows):
        y = 4 + i * m['line_h'] + ascent
        if i < len(m['left_rows']):
            kw, hint, c_kw, c_hint = m['left_rows'][i]
            draw(kw_x, y, kw, c_kw)
            draw(hint_x, y, hint, c_hint)
        if i < len(m['right_rows']):
            text, c_ocr = m['right_rows'][i]
            draw(ocr_x, y, text, c_ocr)
    p.end()
```

- [ ] **Step 2：commit**

```bash
git add ui/overlay.py
git commit -m "feat(overlay): paintEvent rendering with left/right cols + shadow"
```

---

### Task 21：替换 OverlayStub + 验证

**Files:**
- Modify: `ui/main_window.py`

- [ ] **Step 1：MainWindow 换实例**

`ui/main_window.py` `__init__`，把 `from .overlay_stub import OverlayStub` 换成：

```python
from .overlay import Overlay
```

把 `self.overlay = OverlayStub(...)` 换成：

```python
self.overlay = Overlay(parent_root=self, config=config, logger=None)
```

- [ ] **Step 2：手动验证完整流程**

```bash
.venv\Scripts\python app.py
```

预期：
1. 启动 + 开始扫描
2. 当 OCR 命中关键词时，屏幕上出现真透明浮窗（左列累计 + 右列本次 OCR）
3. 鼠标可以**穿过浮窗点到下层应用**（关键回归测试）
4. 命中新关键词时听到柔和和弦声
5. 浮窗按 `display_duration` 配置时长后自动消失
6. 改 `matching.position` 后，浮窗位置变化
7. 改 `matching.font_size` 后，下次显示字号变化

- [ ] **Step 3：commit**

```bash
git add ui/main_window.py
git commit -m "feat(ui): replace OverlayStub with real Overlay (PySide6 implementation)"
```

---

## Stage 5：托盘 + 收尾（0.5 天）

### Task 22：ui/tray.py + minimize_to_tray

**Files:**
- Create: `ui/tray.py`
- Modify: `ui/main_window.py`

- [ ] **Step 1：tray.py**

```python
"""QSystemTrayIcon 托盘，替代 pystray + Pillow。"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import QSystemTrayIcon, QMenu


def _make_scan_icon():
    """用 QPainter 现画一个扫描图标（与 mockup app icon 一致：4 个角标 + 中线）。"""
    pix = QPixmap(64, 64)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor('#2F6FEB'))
    pen.setWidth(5); pen.setCapStyle(0x10); pen.setJoinStyle(0x40)
    p.setPen(pen)
    # 4 个 L 形角标
    p.drawPolyline([(8, 20), (8, 8), (20, 8)])
    p.drawPolyline([(44, 8), (56, 8), (56, 20)])
    p.drawPolyline([(56, 44), (56, 56), (44, 56)])
    p.drawPolyline([(20, 56), (8, 56), (8, 44)])
    # 中间扫描线
    p.drawLine(8, 32, 56, 32)
    p.end()
    return QIcon(pix)


class Tray(QObject):
    show_window = Signal()
    quit_app = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray = QSystemTrayIcon(_make_scan_icon())
        self.tray.setToolTip('屏幕扫描 OCR')
        menu = QMenu()
        act_show = menu.addAction('显示主窗口')
        act_show.triggered.connect(self.show_window.emit)
        menu.addSeparator()
        act_quit = menu.addAction('退出')
        act_quit.triggered.connect(self.quit_app.emit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activate)
        self.tray.show()

    def _on_activate(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # 左键单击
            self.show_window.emit()
```

- [ ] **Step 2：MainWindow 接 tray**

`__init__` 末尾追加：

```python
from .tray import Tray
self.tray = Tray(self)
self.tray.show_window.connect(self._show_normal)
self.tray.quit_app.connect(QApplication.instance().quit)
```

补 import：`from PySide6.QtWidgets import QApplication`。

类内追加：

```python
@Slot()
def _show_normal(self):
    self.show()
    self.raise_()
    self.activateWindow()
```

修改 `closeEvent`：

```python
def closeEvent(self, event):
    if config.get('app.minimize_to_tray'):
        event.ignore()
        self.hide()
        return
    self.worker.shutdown()
    self._thread.quit()
    self._thread.wait(2000)
    super().closeEvent(event)
```

- [ ] **Step 3：手动验证**

`python app.py`：
1. 看托盘出现扫描图标
2. 点关闭按钮 → 窗口消失但进程还在（任务管理器看得到 python.exe）
3. 左键托盘 → 主窗口回来
4. 右键托盘 → 菜单：显示 / 退出
5. 改设置「最小化到托盘」off，再点关闭 → 进程退出

- [ ] **Step 4：commit**

```bash
git add ui/tray.py ui/main_window.py
git commit -m "feat(ui): QSystemTrayIcon + minimize_to_tray wiring"
```

---

### Task 23：HotkeyManager 接入

**Files:**
- Modify: `ui/main_window.py`

- [ ] **Step 1：装热键**

`MainWindow.__init__` 末尾追加：

```python
from src.utils.hotkey import HotkeyManager
self.hotkey = HotkeyManager()
# keyboard 库的回调在自己的线程里跑，必须用 QMetaObject.invokeMethod 切回主线程
def _hk_start():
    QMetaObject.invokeMethod(self, '_on_start_clicked', Qt.QueuedConnection)

def _hk_stop():
    QMetaObject.invokeMethod(self, '_on_stop_clicked', Qt.QueuedConnection)

self.hotkey.register('ctrl+alt+1', _hk_start, '开始扫描')
self.hotkey.register('ctrl+alt+2', _hk_stop, '停止扫描')
```

- [ ] **Step 2：closeEvent 卸载**

`closeEvent` 在真退出分支末尾加：

```python
self.hotkey.unregister_all()
```

- [ ] **Step 3：手动验证**

`python app.py`（如 keyboard 库报权限错误，以管理员身份运行）：

1. 焦点切到其他应用（比如浏览器）
2. 按 Ctrl+Alt+1 → 主窗口的扫描状态栏变「运行中」
3. 按 Ctrl+Alt+2 → 状态栏变「已停止」

预期：跨应用全局热键正常工作，主线程 UI 正确响应。

- [ ] **Step 4：commit**

```bash
git add ui/main_window.py
git commit -m "feat(ui): wire HotkeyManager via QMetaObject.invokeMethod"
```

---

### Task 24：删旧 tk 代码 + 更新 gui.bat

**Files:**
- Delete: `app.py.tk_backup`
- Verify: `gui.bat`

- [ ] **Step 1：检查 gui.bat**

```bash
type gui.bat
```

预期：仍然 `pythonw app.py`（入口文件没变，只是内容换了）。如有问题改成：

```bat
@echo off
.venv\Scripts\pythonw.exe app.py
```

- [ ] **Step 2：双击 gui.bat 验证**

预期：无控制台窗口，PySide6 GUI 正常打开。

- [ ] **Step 3：删 backup**

```bash
git rm app.py.tk_backup
```

- [ ] **Step 4：commit**

```bash
git add gui.bat
git commit -m "chore: remove tkinter backup; verify gui.bat entry"
```

---

### Task 25：requirements 清理

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1：grep pystray / pillow 引用**

```bash
git grep -l "pystray\|PIL\|pillow"
```

预期：除 `requirements.txt` / `old_version/` 外无引用。

- [ ] **Step 2：清理**

如新版没有任何引用，从 `requirements.txt` 移除 `pystray>=0.19.0` 与 `pillow>=12.0.0`。`old_version/` 仍依赖的话，在 `old_version/requirements.txt`（如有，否则不动）单独保留。

- [ ] **Step 3：重装环境验证**

```bash
.venv\Scripts\pip uninstall -y pystray pillow
.venv\Scripts\python app.py
```

预期：新版 PySide6 GUI 正常启动；旧版 `python old_version/app.py` 如果用到 pystray 会失败，但 old_version 不在维护范围。

- [ ] **Step 4：基线记录**

启动后记录：
- 冷启动时间（OCR init 完成前到完成后）
- 待机内存占用（状态栏数字）
- 运行 1 分钟扫描的内存占用

记到本计划末尾或单独 issue。

- [ ] **Step 5：commit + push**

```bash
git add requirements.txt
git commit -m "chore: remove pystray/pillow deps (replaced by QSystemTrayIcon)"
git push -u origin feature/pyside6
```

- [ ] **Step 6：开 PR**

```bash
gh pr create --base main --title "feat(ui): migrate GUI from tkinter to PySide6"
```

---

## 性能基线（Task 25 结束后填写）

| 指标 | 旧 tk 版 | 新 PySide6 版 |
|---|---|---|
| 冷启动到主窗口可见 | TBD | TBD |
| OCR init 完成时长 | TBD | TBD |
| 待机内存 | TBD | TBD |
| 运行 1 分钟内存 | TBD | TBD |

---

## 不在本计划范围内

- 暗色主题 / 主题切换
- 热键编辑功能（mockup 卡留位 disabled）
- 配置导入/导出（mockup 已只剩"重置"按钮）
- old_version/ 的功能改动（仅 ROI key 重命名）
- CLI 重构（仅 ROI key 重命名）
- pyinstaller 打包（独立任务）
