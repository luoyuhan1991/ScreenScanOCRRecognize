"""DeletableComboBox：下拉项右侧带 X 删除按钮的 QComboBox。

用法：
    combo = DeletableComboBox()
    combo.add_item('xxx', userdata, deletable=True)   # 可删行
    combo.add_item('全部', None, deletable=False)      # 不可删（不画 X）
    combo.item_delete_requested.connect(my_handler)    # 收 userdata

实现要点
- delegate 完全自绘背景 / 文字 / X。**不能** super().paint：QSS 中只要写了
  `QComboBox QAbstractItemView::item`，Qt 的 QStyleSheetStyle 会接管 item 绘制，
  把 delegate 在 super 之后画的 X 整个覆盖掉，X 就出不来。
- 颜色对齐 mockup：hover #F4F6FA，selected --sidebar-active #E6EFFD + 主蓝字 + Medium。
- X 按钮 hover：圆形浅红背景 + X 变红，明确表达"删除"动作。
- 通过 viewport().installEventFilter 拦截鼠标事件：
  * MouseMove 跟踪 X 区是否被 hover（更新 self._x_hover_row）
  * MouseButtonPress 命中 X 时 emit item_delete_requested 并 return True，阻止
    ComboBox 把这一行选中、关闭 popup
- 显式 setView(QListView())，避免 QComboBox 内部某些版本用特殊 view 导致
  setItemDelegate 不生效。
- "可删"标志写在 Qt.UserRole + 1，data 写在 Qt.UserRole（QComboBox.addItem 默认）。
"""

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QListView, QStyle, QStyledItemDelegate

_DELETABLE_ROLE = Qt.UserRole + 1

# 颜色（mockup .dropdown-menu / .item / .item.active）
_BG_DEFAULT = QColor('#FFFFFF')
_BG_HOVER = QColor('#F4F6FA')
_BG_SELECTED = QColor('#E6EFFD')        # --sidebar-active
_TEXT = QColor('#1E293B')
_TEXT_SELECTED = QColor('#2F6FEB')      # --primary
_X_COLOR = QColor('#94A3B8')
_X_COLOR_SELECTED = QColor('#2F6FEB')
_X_COLOR_HOVER = QColor('#E5484D')      # --danger，hover 时变红表示"删除"动作
_X_HOVER_BG = QColor(229, 72, 77, 36)   # rgba(--danger, ~14%) 圆形浅红底

# 几何参数
_FONT_SIZE = 13
_ROW_HEIGHT = 34         # mockup .item padding 7+7 + 13×1.5 ≈ 33.5，取 34 圆整
_TEXT_LEFT_PAD = 12      # mockup .item padding-left
_X_RIGHT_PAD = 12        # X 距 item 右边距
_X_HALF = 4              # X 视觉半边长（叉占 8x8）
_X_HIT = 22              # X 命中区（也是 hover 圆背景的直径）


class _DeletableItemDelegate(QStyledItemDelegate):
    delete_requested = Signal(object)  # 透传 item 的 userData

    def __init__(self, view):
        super().__init__(view)
        self._view = view
        self._x_hover_row = -1
        view.viewport().setMouseTracking(True)
        view.viewport().installEventFilter(self)

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        return QSize(s.width(), max(_ROW_HEIGHT, s.height()))

    def paint(self, painter, option, index):
        is_selected = bool(option.state & QStyle.State_Selected)
        is_row_hover = bool(option.state & QStyle.State_MouseOver)
        deletable = bool(index.data(_DELETABLE_ROLE))

        # 1. 背景
        if is_selected:
            bg = _BG_SELECTED
        elif is_row_hover:
            bg = _BG_HOVER
        else:
            bg = _BG_DEFAULT
        painter.fillRect(option.rect, bg)

        # 2. 文字（右侧给 X 留位）
        right_reserve = (_X_RIGHT_PAD + 2 * _X_HALF + 8) if deletable else _TEXT_LEFT_PAD
        text_rect = option.rect.adjusted(_TEXT_LEFT_PAD, 0, -right_reserve, 0)
        font = QFont(option.font)
        font.setPixelSize(_FONT_SIZE)
        if is_selected:
            font.setWeight(QFont.Medium)
        painter.setFont(font)
        painter.setPen(_TEXT_SELECTED if is_selected else _TEXT)
        painter.drawText(
            text_rect, Qt.AlignVCenter | Qt.AlignLeft, str(index.data() or '')
        )

        # 3. X（仅 deletable 行）
        if not deletable:
            return
        cx = option.rect.right() - _X_RIGHT_PAD - _X_HALF
        cy = option.rect.center().y()
        is_x_hover = (index.row() == self._x_hover_row)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        # 3a. hover 圆形背景
        if is_x_hover:
            painter.setPen(Qt.NoPen)
            painter.setBrush(_X_HOVER_BG)
            radius = _X_HIT // 2
            painter.drawEllipse(QPoint(cx, cy), radius, radius)
        # 3b. X 线条
        if is_x_hover:
            x_color = _X_COLOR_HOVER
        elif is_selected:
            x_color = _X_COLOR_SELECTED
        else:
            x_color = _X_COLOR
        pen = QPen(x_color)
        pen.setWidthF(1.6 if is_x_hover else 1.5)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(cx - _X_HALF, cy - _X_HALF, cx + _X_HALF, cy + _X_HALF)
        painter.drawLine(cx - _X_HALF, cy + _X_HALF, cx + _X_HALF, cy - _X_HALF)
        painter.restore()

    def _x_hit_rect(self, item_rect):
        cx = item_rect.right() - _X_RIGHT_PAD - _X_HALF
        cy = item_rect.center().y()
        return QRect(cx - _X_HIT // 2, cy - _X_HIT // 2, _X_HIT, _X_HIT)

    def _set_x_hover(self, row):
        if row != self._x_hover_row:
            self._x_hover_row = row
            self._view.viewport().update()

    def eventFilter(self, obj, event):
        et = event.type()
        if et == QEvent.MouseMove:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            idx = self._view.indexAt(pos)
            new_hover = -1
            if idx.isValid() and bool(idx.data(_DELETABLE_ROLE)):
                if self._x_hit_rect(self._view.visualRect(idx)).contains(pos):
                    new_hover = idx.row()
            self._set_x_hover(new_hover)
        elif et == QEvent.Leave:
            self._set_x_hover(-1)
        elif et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            idx = self._view.indexAt(pos)
            if idx.isValid() and bool(idx.data(_DELETABLE_ROLE)):
                if self._x_hit_rect(self._view.visualRect(idx)).contains(pos):
                    self.delete_requested.emit(idx.data(Qt.UserRole))
                    return True
        return False


class DeletableComboBox(QComboBox):
    item_delete_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 显式用标准 QListView 作 popup view
        view = QListView(self)
        view.setCursor(Qt.PointingHandCursor)
        self.setView(view)
        self._delegate = _DeletableItemDelegate(view)
        view.setItemDelegate(self._delegate)
        self._delegate.delete_requested.connect(self.item_delete_requested.emit)

    def add_item(self, text, data, deletable=True):
        """addItem 加强版：写入 deletable 标记到 UserRole+1。"""
        idx = self.count()
        self.addItem(text, data)
        self.setItemData(idx, bool(deletable), _DELETABLE_ROLE)
