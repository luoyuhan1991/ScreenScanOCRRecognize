# GUI 重做 · 方案 C 落地 design

日期：2026-05-07
分支：feature/version_switched
关联 mockup：`mockups/mockup_c.png`、`mockups/mockup_c.py`

## 目标

把 `app.py` 的 GUI 从「单列 4 个 LabelFrame」改成方案 C 的「顶部状态栏 + 左侧边栏 Tab + 右侧日志 + 底部按钮栏」布局，并按用户偏好把「匹配后显示时长」从 mockup C 的「高级」tab 移到「常用配置」tab。窗口大小保持 **860×680**（mockup C 原稿 1100×700，按用户要求压缩，靠缩小日志区适配）。

## 现状

`app.py:318-327` 的 `_create_widgets` 顺序调用 6 个子方法搭建界面：状态栏 / 扫描配置 / OCR 配置 / 关键词匹配 / 日志区 / 按钮区，全部上下排列在一个 padding=10 的主 Frame 里。配置项控件本身（Var、回调、save/load）实现完整且无 bug，需要保留。

需要重做的纯粹是「容器层」：把 6 个 LabelFrame 拆解、重新组装到新的容器结构（Notebook、左右分栏、顶部/底部 Bar）里。

## 设计

### 整体布局（860×680）

```
┌───────────────────────────────────────────────────────────────┐
│ ● 已停止          扫描次数 28  最近 10:56:54  内存 1349.2 MB │ 56px
├──────────────────┬────────────────────────────────────────────┤
│ [常用] [高级]    │ 运行日志    · N 条 · 实时刷新     [清空] │
│                  │ ┌────────────────────────────────────────┐ │
│ 扫描区域         │ │                                        │ │
│  ☐ 启用 ROI      │ │   日志内容（黑底彩字）                 │ │
│  ☑ 记住 ROI      │ │                                        │ │ 552px
│  预设: [4+2  ▾]  │ │                                        │ │
│  [保存当前]      │ │                                        │ │
│ 扫描节奏         │ │                                        │ │
│  间隔 [▬▬▬○▬▬]  │ │                                        │ │
│ OCR              │ │                                        │ │
│  ...             │ │                                        │ │
│  300px 宽        │ │                                        │ │
├──────────────────┴────────────────────────────────────────────┤
│ [开始扫描]  [停止扫描]              [清除匹配记录][重置配置] │ 56px
└───────────────────────────────────────────────────────────────┘
```

侧边栏宽度从 mockup C 的 340 缩到 **300**，给主区让出更多空间。顶/底 Bar 高度从 64 缩到 **56**。

主区可视高度：680 − 56 − 56 = **568** px；扣掉日志 header (~28) 和上下边距 ≈ 530 px 给日志框，相比 mockup C（约 600 px）缩 ~12%，仍能完整显示十多行日志。

### Tab 内容拆分

| 控件 | Tab | 在原 app.py 中的位置 |
|---|---|---|
| 启用 ROI / 记住 ROI / ROI 预设 / 保存当前 | 常用 · 扫描区域 | `_create_scan_config` |
| 扫描间隔 | 常用 · 扫描节奏 | `_create_scan_config` |
| 语言 / GPU 加速 / 最小置信度 | 常用 · OCR | `_create_ocr_config` |
| 关键词文件 + 浏览 + 编辑 | 常用 · 关键词 | `_create_match_config` |
| **匹配后显示时长** | 常用 · 关键词 | `_create_match_config`（原归属在「关键词匹配」LabelFrame 第二行） |
| 帧差阈值 | 高级 · 帧差检测 | `_create_scan_config` |
| 字号 / 位置 / 音效 | 高级 · 浮窗外观 | `_create_match_config` |
| 图像反色 | 高级 · OCR 进阶 | `_create_ocr_config` |

### 保留 vs 移除

**保留**（功能不变，只换位置或样式）：
- 全部 Tk 变量：`_var_enable_roi` / `_var_remember_roi` / `_var_gpu` / `_var_interval` / `_var_diff_threshold` / `_var_lang` / `_var_confidence` / `_var_invert` / `_var_banlist` / `_var_duration` / `_var_fontsize` / `_var_position` / `_var_sound` / `_var_roi_preset`
- 全部回调：`_on_*_scale`、`_on_preset_selected`、`_save_roi_preset`、`_browse_banlist`、`_edit_banlist`、`_clear_session`、`_reset_config`、`_clear_log`
- `_load_settings` / `_save_settings` 不动（变量名不变）
- 启动链路完整保留：`on_start` → `_init_and_start`（后台线程）→ `_after_init_ok` / `_after_init_fail` → `_do_roi_select`（含 iconify/300ms 延迟）→ `_start_scanning` → `_show_roi_border`
- 停止链路：`on_stop` / `_on_scan_thread_exit` / `_hide_roi_border`
- 错误/弹窗：OCR init 失败 `showerror`、保存 ROI 预设无 ROI 时 `showwarning`、重置配置 `askyesno`、编辑词表文件不存在时 `askyesno` 创建、ROI 预设名 `simpledialog.askstring`、浏览词表 `filedialog.askopenfilename`、编辑词表 Toplevel 编辑器
- 扫描线程主循环（`_scan_loop`）+ overlay 主线程调度 + 统计刷新
- 日志：`_setup_gui_logger` / `_drain_log_queue`（100ms / 15 条）/ 2000 行裁剪 / 4 种 tag 配色（INFO `#4ec9b0` / WARNING `#dcdcaa` / ERROR `#f48771` / DEBUG `#569cd6`）
- 托盘：`_setup_tray` / `_minimize_to_tray` / `_tray_show` / `_tray_quit` / `_on_close`（含 3 秒看门狗强杀 `os._exit(0)`）
- 热键：Ctrl+Alt+1 / Ctrl+Alt+2，`_register_hotkeys`
- 内存：`_schedule_memory_update`（5 秒一刷）+ `_get_memory_mb`（Win32 API 取 RSS）
- ROI 红框可视化：`_show_roi_border` / `_hide_roi_border`（独立 Toplevel + Canvas）
- ROI 交互选择：`select_roi_interactive`（半透明全屏 + ESC 取消 → fallback 全屏）
- 「浏览」+「编辑」两个独立按钮（mockup C 里压成一个 `…` 是简化，功能上需要分离）
- 窗口标题动态化（运行中/扫描中/初始化中），`_update_title`

**调整**：
- 状态栏从 `LabelFrame` 改为白色无边 Bar，**新增** `●` 颜色指示灯（红=停止 / 黄=初始化 / 绿=运行中）；扫描次数 / 最近扫描 / 内存改为 cell 布局（副标题在上 + 大字在下）
- 4 个 LabelFrame 全部解散，控件重组到 Notebook 两个 Tab 下
- 按钮区从普通 ttk.Button 改为彩色样式（开始=主色蓝填充，停止=红色描边）
- **日志清空按钮**从「叠在日志框右上角的小 X（用 `place()` + `<Configure>` 重定位）」迁到日志 header 行的普通「清空」按钮，命令仍是 `_clear_log`。原 `_reposition_clear` 逻辑及 `<Configure>` 绑定一并删除。

**不加**（YAGNI）：
- mockup C 的「导出日志」按钮 — 原来没有，不加
- 配色主题切换 — 原来没有，不加

### 颜色与样式（沿用 mockup C 调色板）

```
BG       = #fafafa  主背景
SIDEBAR  = #eef0f3  侧边栏底
CARD     = #ffffff  顶部 / 底部 Bar
PRIMARY  = #0066cc  主色（开始按钮、选中 tab 文字）
DANGER   = #d83b01  停止按钮、红点
SUCCESS  = #107c10  绿点
WARNING  = #d8a200  黄点（初始化中）
TEXT     = #222
SUBTEXT  = #777     副标题、单位标签
BORDER   = #d8dade  分隔线
```

ttk 主题切到 `clam`（同 mockup C），原生 Windows 主题对 ttk.Combobox 的配色支持有限。

### 状态指示灯三态

- 红 `●` + 「已停止」：`is_running=False`
- 黄 `●` + 「初始化中」：`_init_and_start` 启动到 `_after_init_ok` 之间
- 绿 `●` + 「运行中」：`_start_scanning` 之后、`on_stop` 之前

复用现有的 `_update_status(text)`，只是同步把指示灯颜色也切了。

## 实现策略

**单文件改动**：只改 `app.py`，其它文件零改动（pipeline/overlay/config 都不动）。

**结构重组**：

```python
def _create_widgets(self):
    self._setup_styles()
    self._create_topbar(self.root)
    self._create_bottombar(self.root)        # 先 pack bottom，再 pack body
    body = ttk.Frame(self.root)
    body.pack(fill=tk.BOTH, expand=True)
    self._create_sidebar(body)               # 左
    self._create_main_area(body)             # 右

def _create_topbar(self, parent): ...        # 状态指示 + 3 个统计 cell
def _create_sidebar(self, parent): ...       # ttk.Notebook with 2 tabs
def _create_tab_common(self, nb): ...        # 4 组：扫描区域 / 扫描节奏 / OCR / 关键词
def _create_tab_advanced(self, nb): ...      # 3 组：帧差检测 / 浮窗外观 / OCR 进阶
def _create_main_area(self, parent): ...     # 日志 header + log textbox
def _create_bottombar(self, parent): ...     # 4 个按钮
def _setup_styles(self): ...                 # ttk.Style + 配色常量
```

原来的 `_create_status_bar` / `_create_scan_config` / `_create_ocr_config` / `_create_match_config` / `_create_log_area` / `_create_buttons` 全部删掉。

**状态指示灯**：在 `_create_topbar` 里把 `●` 标签存为 `self._lbl_dot`，改 `_update_status`：

```python
def _update_status(self, text):
    self._lbl_status.config(text=text)
    if '初始化' in text: color = WARNING       # 黄
    elif text == '运行中': color = SUCCESS     # 绿
    else: color = DANGER                        # 红 = 已停止 / 异常文字
    self._lbl_dot.config(fg=color)
    self._update_title(text)
```

调用方已用 `_update_status('已停止' / '运行中' / '初始化中...')`，无需改业务逻辑。

**统计指标 label**：把 `_lbl_count` / `_lbl_last` / `_lbl_mem` 三个 Label 移到 topbar 的 cell 结构里。文字格式从 `"扫描: 28"` 改为「副标题在上 + 大字在下」两行布局，但 `_update_stats` 和 `_schedule_memory_update` 的 set 调用照原样工作（每个 cell 维护自己的「值」label）。

## 测试策略

无单测，靠手测：

1. `python app.py` 启动，肉眼检查布局对得上 mockup
2. 切换两个 Tab，控件齐全、状态保留
3. 改任一控件值（间隔、字号、关键词文件等），停止→重启，看是否持久化（验证 `_save_settings` 仍工作）
4. 点开始扫描，观察：状态灯红→黄→绿、统计指标更新、日志滚动、ROI 红框可见
5. 点停止：灯回红、按钮状态切换
6. 测「保存 ROI 预设」「浏览」「编辑」「清除匹配记录」「重置配置」每个按钮
7. 关闭窗口缩到托盘 → 右键退出
8. Ctrl+Alt+1 / Ctrl+Alt+2 热键

## 风险与权衡

- **860×680 偏紧**：侧边栏 300 + 内边距 16 后，可用宽度约 268 px。Scale 控件长度从 mockup C 的 220 压到约 180 才能塞进去。可接受。
- **clam 主题外观差异**：和 Windows 原生主题肉眼可辨，部分用户可能觉得「不像 Windows 应用」。但 mockup C 已用 clam，用户已认可整体方向。
- **状态灯颜色与窗口标题双重指示**：略冗余。但窗口标题在窗口最小化到任务栏时才能看到，而灯在窗口正前。两个互补。
- **日志区缩小**：可视行数从约 14 行降到约 10 行。日志限制 2000 行的逻辑不变，滚动可见即可。

## 范围之外（明确不做）

- 不引入主题切换 / 暗色模式
- 不重写 pipeline、overlay、config 等非 UI 模块
- 不改快捷键、热键
- 不改默认配置、不动 yaml
- 不重命名/移动文件，仅改 `app.py`
- 不写单测（GUI 重排不值得）
