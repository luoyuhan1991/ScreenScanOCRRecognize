"""关于页：mockup 没专门设计这一页，参照 sidebar / settings 的视觉一致性自绘。
布局：顶部 Hero（大蓝色图标卡 + app 名 + 版本 + tagline）+ 信息卡 + 技术栈卡。"""
import os
import webbrowser
from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QPainter, QPixmap, QCursor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
)

from config.defaults import APP_VERSION
from ..widgets.settings_card import SettingsCard, SettingsRow

_REPO_URL = 'https://github.com/luoyuhan1991/ScreenScanOCRRecognize'
_AUTHOR = 'luoyuhan'
_LICENSE = 'MIT'
_TAGLINE = '定时截图 → OCR 识别 → 关键词匹配 → 屏幕浮窗提示'


def _hero_icon(size=48):
    """复用 sidebar 的 bullseye 图标，渲染成大尺寸白色图标用于 Hero 卡片。"""
    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="8"/>
        <circle cx="12" cy="12" r="3" fill="white" stroke="none"/>
        <line x1="12" y1="2"  x2="12" y2="5"/>
        <line x1="12" y1="19" x2="12" y2="22"/>
        <line x1="2"  y1="12" x2="5"  y2="12"/>
        <line x1="19" y1="12" x2="22" y2="12"/></svg>'''
    renderer = QSvgRenderer(QByteArray(svg))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(p)
    p.end()
    return pix


class _LinkLabel(QLabel):
    """蓝字 + 手型 cursor + 点击开浏览器。"""

    def __init__(self, text, url, parent=None):
        super().__init__(text, parent)
        self._url = url
        self.setObjectName('aboutLink')
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            try:
                webbrowser.open(self._url)
            except Exception:
                pass
        super().mousePressEvent(event)


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName('aboutPage')

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 整页可滚（窗口拉小时不被截）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QFrame()
        content.setObjectName('aboutContent')
        scroll.setWidget(content)

        v = QVBoxLayout(content)
        v.setContentsMargins(40, 32, 40, 32)
        v.setSpacing(20)
        v.setAlignment(Qt.AlignTop)

        v.addWidget(self._build_hero())
        v.addWidget(self._build_project_card())
        v.addWidget(self._build_stack_card())
        v.addStretch(1)

    # -------- Hero：大图标 + 名称 + 版本 + tagline --------
    def _build_hero(self):
        hero = QFrame()
        hero.setObjectName('aboutHero')
        h = QHBoxLayout(hero)
        h.setContentsMargins(0, 8, 0, 8)
        h.setSpacing(20)
        # 左侧：蓝底圆角图标卡
        icon_card = QFrame()
        icon_card.setObjectName('aboutHeroIcon')
        icon_card.setFixedSize(80, 80)
        ic_box = QVBoxLayout(icon_card)
        ic_box.setContentsMargins(0, 0, 0, 0)
        ic_box.setAlignment(Qt.AlignCenter)
        icon = QLabel()
        icon.setPixmap(_hero_icon(48))
        icon.setAlignment(Qt.AlignCenter)
        ic_box.addWidget(icon)
        h.addWidget(icon_card)
        # 右侧：纵向 [name] [version] [tagline]
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 4, 0, 4)
        text_col.setSpacing(4)
        name = QLabel('屏幕扫描 OCR 识别系统')
        name.setObjectName('aboutAppName')
        version = QLabel(f'版本 {APP_VERSION}')
        version.setObjectName('aboutVersion')
        tagline = QLabel(_TAGLINE)
        tagline.setObjectName('aboutTagline')
        tagline.setWordWrap(True)
        text_col.addWidget(name)
        text_col.addWidget(version)
        text_col.addWidget(tagline)
        text_col.addStretch(1)
        h.addLayout(text_col, 1)
        return hero

    # -------- 项目信息卡 --------
    def _build_project_card(self):
        card = SettingsCard('项目信息')
        card.add_row(SettingsRow('作者', QLabel(_AUTHOR), with_separator=False))
        card.add_row(SettingsRow('仓库', _LinkLabel(_REPO_URL, _REPO_URL)))
        card.add_row(SettingsRow('许可证', QLabel(_LICENSE)))
        return card

    # -------- 技术栈卡 --------
    def _build_stack_card(self):
        card = SettingsCard('技术栈')
        card.add_row(SettingsRow('GUI 框架', QLabel('PySide6 (Qt for Python)'),
                                 with_separator=False))
        card.add_row(SettingsRow('OCR 引擎', QLabel('PaddleOCR 3.x')))
        card.add_row(SettingsRow('截屏', QLabel('mss (跨进程屏幕抓取)')))
        card.add_row(SettingsRow('关键词匹配', QLabel('pyahocorasick (Aho-Corasick 自动机)')))
        card.add_row(SettingsRow('全局热键', QLabel('keyboard (Windows 全局钩子)')))
        return card
