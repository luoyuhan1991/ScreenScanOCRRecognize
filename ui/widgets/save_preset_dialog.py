"""SavePresetDialog：取一个预设名（新建 / 覆盖均走同一路径）。

下拉列出当前所有命名预设；用户：
- 选某项 → input 自动填该名字（点保存即覆盖）
- 自己输入新名字（点保存即新增）
- 删除入口不在这里 —— 在主面板「删除」按钮（A 方案，纯 QSS 控样式）

accept 后 chosen_name() 返回 stripped 字符串。
"""

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from config.config import config


class SavePresetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('保存预设')
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel('选已有名字覆盖，或输入新名字：'))

        self.combo = QComboBox(self)
        self.combo.setEditable(True)
        # NoInsert：用户输入新名字时不自动加进下拉项（避免 currentText 副作用）
        self.combo.setInsertPolicy(QComboBox.NoInsert)
        presets = config.get('scan.roi_presets') or {}
        for name in presets.keys():
            self.combo.addItem(name, name)
        self.combo.setEditText('')
        # 选下拉项时把名字带到 input
        self.combo.activated.connect(
            lambda i: self.combo.setEditText(self.combo.itemText(i))
        )
        layout.addWidget(self.combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self
        )
        buttons.button(QDialogButtonBox.Save).setText('保存')
        buttons.button(QDialogButtonBox.Cancel).setText('取消')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def chosen_name(self):
        return (self.combo.currentText() or '').strip()
