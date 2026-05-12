"""SavePresetDialog：弹窗里也有一个支持 X 删除 + 可输入新名字的下拉。

行为
- 下拉里列出当前所有命名预设；用户可：
  - 选某项 → input 自动填该名字（点保存即覆盖）
  - 自己输入新名字（点保存即新增）
  - 点项右侧 X → 删除该预设（直接落到 config）
- accept 后 chosen_name() 返回 stripped 字符串。
- 删除直接写 config，无论对话框最终 accept 还是 reject 都生效，避免操作丢失。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from config.config import config
from .deletable_combo import DeletableComboBox


class SavePresetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('保存预设')
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel('选已有名字覆盖，或输入新名字：'))

        self.combo = DeletableComboBox(self)
        self.combo.setEditable(True)
        # 编辑框为空时点保存视作未填，需要用户主动输入或选预设
        self.combo.setInsertPolicy(DeletableComboBox.NoInsert)
        self._reload_combo()
        self.combo.item_delete_requested.connect(self._on_delete)
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

    def _reload_combo(self):
        """从 config 重建下拉项；input 清空让用户主动选择/输入。"""
        self.combo.blockSignals(True)
        self.combo.clear()
        presets = config.get('scan.roi_presets') or {}
        for name in presets.keys():
            self.combo.add_item(name, name, deletable=True)
        self.combo.setEditText('')
        self.combo.blockSignals(False)

    def _on_delete(self, name):
        """从 config 删该预设；如果是当前 last_roi_choice，回退到自定义区域。"""
        from .config_panel import CUSTOM_TOKEN
        presets = config.get('scan.roi_presets') or {}
        if name in presets:
            del presets[name]
            config.set('scan.roi_presets', presets)
            if config.get('scan.last_roi_choice') == name:
                config.set('scan.last_roi_choice', CUSTOM_TOKEN)
            config.save()
        self._reload_combo()

    def chosen_name(self):
        return (self.combo.currentText() or '').strip()
