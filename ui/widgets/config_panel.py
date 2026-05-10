from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox,
    QSlider, QLineEdit, QPushButton, QFrame, QFileDialog, QInputDialog,
)

from src.config.config import config


class LargeButton(QFrame):
    """主按钮卡片：两行（标题 + 小字 hint），整个卡片可点击。
    支持 enabled/disabled 状态：disabled 时不响应点击，QSS 控制变灰。"""

    clicked = Signal()

    def __init__(self, title, hint, object_name, parent=None):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(52)
        self._enabled = True
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)
        lbl_title = QLabel(title)
        lbl_title.setObjectName('lbBtnTitle')
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_hint = QLabel(hint)
        lbl_hint.setObjectName('lbBtnHint')
        lbl_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_hint)

    def setEnabled(self, enabled):
        self._enabled = enabled
        super().setEnabled(enabled)
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
        # 触发 QSS :disabled 选择器
        self.setProperty('disabled', not enabled)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if not self._enabled:
            return
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


def _make_group(title):
    """返回 (容器 QFrame, 内层 QVBoxLayout)。"""
    frame = QFrame()
    frame.setObjectName('configGroup')
    box = QVBoxLayout(frame)
    box.setContentsMargins(12, 12, 12, 12)
    box.setSpacing(8)
    title_lbl = QLabel(title)
    title_lbl.setObjectName('groupTitle')
    box.addWidget(title_lbl)
    return frame, box


def _slider_row(min_v, max_v, value, on_change, scale=1):
    """slider + 右侧白色圆角小盒子显示当前值（mockup .slider-value 样式）。
    返回 QHBoxLayout。"""
    s = QSlider(Qt.Horizontal)
    s.setMinimum(int(min_v * scale))
    s.setMaximum(int(max_v * scale))
    s.setValue(int(value * scale))
    value_box = QLabel(f'{value:g}')
    value_box.setObjectName('sliderValue')
    value_box.setAlignment(Qt.AlignCenter)
    value_box.setFixedSize(56, 28)
    s.valueChanged.connect(lambda v: (value_box.setText(f'{v/scale:g}'), on_change(v / scale)))
    wrap = QHBoxLayout()
    wrap.setSpacing(12)
    wrap.addWidget(s, 1)
    wrap.addWidget(value_box)
    return wrap


class ConfigPanel(QWidget):
    """主窗口左侧配置区：4 个 group + Action 按钮组。
    所有控件双向绑定 config 单例。"""

    start_clicked = Signal()
    stop_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        layout.addWidget(self._build_roi_group())
        layout.addWidget(self._build_pace_group())
        layout.addWidget(self._build_ocr_group())
        layout.addWidget(self._build_match_group())
        layout.addLayout(self._build_action_row())
        layout.addStretch(1)

        # 初始状态：未运行 → 开始可点，停止 disabled
        self.set_running(False)

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
        box.addLayout(_slider_row(
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
        box.addLayout(_slider_row(
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
        row.setSpacing(6)
        self.le_banlist = QLineEdit(str(config.get('files.banlist_file') or ''))
        self.le_banlist.setReadOnly(True)
        btn_browse = QPushButton('浏览…')
        btn_browse.clicked.connect(self._on_browse_banlist)
        btn_edit = QPushButton('编辑')
        btn_edit.clicked.connect(self._on_edit_banlist)
        row.addWidget(self.le_banlist, 1)
        row.addWidget(btn_browse)
        row.addWidget(btn_edit)
        box.addLayout(row)

        box.addWidget(QLabel('匹配后显示时长（秒）'))
        box.addLayout(_slider_row(
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

    def _on_edit_banlist(self):
        """用系统默认程序打开关键词文件（Windows: 记事本/用户自定义）。"""
        path = self.le_banlist.text().strip()
        if not path:
            return
        try:
            import os
            if os.path.isfile(path):
                os.startfile(path)  # noqa: SIM115 (Windows 专用)
        except Exception:
            pass

    # ----- Action 按钮（横向并排，每按钮 2 行：标题 + 热键提示） -----
    def _build_action_row(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        self.btn_start = self._build_large_button('▶ 开始扫描', 'Ctrl + Alt + 1', 'btnPrimary')
        self.btn_start.clicked.connect(self.start_clicked.emit)
        self.btn_stop = self._build_large_button('■ 停止扫描', 'Ctrl + Alt + 2', 'btnDanger')
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        row.addWidget(self.btn_start, 1)
        row.addWidget(self.btn_stop, 1)
        return row

    @staticmethod
    def _build_large_button(title, hint, object_name):
        """两行按钮：标题 + 热键提示。QPushButton 不支持多行子结构，
        所以用 LargeButton（QFrame + 2 QLabel + mousePressEvent → clicked）。"""
        return LargeButton(title, hint, object_name)

    def set_running(self, running):
        """更新启动/停止按钮的可用态。"""
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def reload_from_config(self):
        """重置配置后由 MainWindow 调用，刷新部分 widget 显示值。
        slider 由调用方重建更稳；此处仅刷新 checkbox / combo / lineedit。"""
        self.cb_enable_roi.setChecked(bool(config.get('scan.enable_roi')))
        self.cb_remember_roi.setChecked(bool(config.get('scan.remember_roi')))
        self._reload_presets()
        self.cb_gpu.setChecked(bool(config.get('gpu.enabled')))
        cur = config.get('ocr.language') or 'ch'
        idx = self.combo_lang.findData(cur)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.le_banlist.setText(str(config.get('files.banlist_file') or ''))
