# 代码审查报告 — 2026-05-13

**审查范围**：`app.py / cli.py / config / pipeline / utils / ui` 全部业务源码（不含 `.venv` / `tests` / `docs/mockups`）。
**审查方法**：通读 + grep 验证调用方。
**审查目标**：技术框架是否合理、代码层面有无冗余、具体实现是否有逻辑反复可以简化。

---

## 一、技术框架/架构层面

### 1. 多个声明了但根本没生效的配置项（建议直接清理）

| 配置键 | 现象 | 位置 |
|---|---|---|
| `scan.enable_diff_skip` | defaults 里 `True`，但 `DiffGate.should_skip()` 只看阈值，**没有任何 `if not enable_diff_skip` 的短路** | `config/defaults.py:20` |
| `matching.enabled` | 全工程 grep 0 调用方，pipeline 总是匹配 | `config/defaults.py:46` |
| `logging.file / format / max_bytes / backup_count` | `utils/logger.py` 只读 `logging.level`，**根本没装 RotatingFileHandler**——所谓"日志旋转 10MB×5"是纸面承诺 | `config/defaults.py:54-57` |
| `ocr.enable_image_invert` | pipeline 读取了，但 GUI 没暴露开关，半死状态 | `config/defaults.py:37` |

**结论**：要么补实现，要么从 defaults 删。配置项放着不工作是最容易踩的坑。

### 2. OCRStage 单例与实例字段双重持有，存在配置切换 bug

`pipeline/ocr_stage.py`：
- 模块级 `_ocr_instance` + `(lang, gpu)` 元组单例，**配置变就重建** ✅
- 但 `OCRStage.__init__` 又有 `self._ocr`，`recognize()` 里只在 `self._ocr is None` 时刷新

```python
# ocr_stage.py:61-62
if self._ocr is None:
    self._ocr = _get_ocr()
```

**后果**：用户在 GUI 改了语言/GPU 后，模块级单例确实重建了，但 `OCRStage 实例.self._ocr` 还是旧引用，下一次 `recognize` 仍然用旧模型。

**修法**：删 `self._ocr` 字段，`recognize` 里直接 `_get_ocr().ocr(...)`；或每次 `self._ocr = _get_ocr()` 不带 `if None` 守卫。

### 3. 日志体系混乱（双格式化、双 logger、配置不生效）

- `utils/logger.py` 配置了名为 `screen_scan` 的 logger + StreamHandler；
- `pipeline/*` 和 `utils/hotkey.py` 用 `from .logger import logger; logger.info`；
- `ui/scan_worker.py / ui/main_window.py` 直接 `logging.info(...)`（root logger）；
- `ui/log_bridge.py` 挂在 root 上做 LogBridge，又**自己装了一套 formatter**；
- `screen_scan` logger 的 StreamHandler 也输出控制台 → 通过 `propagate=True` 又冒到 root → root 的 LogBridge 再格式化一次（formatter 重复格式化）；
- `configure_from_config(cfg)` 仅在 CLI 调用，GUI 启动后 `logging.level` 配置实际不生效。

**修法**：所有模块统一用 `logging.getLogger(__name__)`；utils/logger 只保留一个"装 root 的 file handler + console handler"的 setup，删 `screen_scan` 命名 logger。

### 4. `DEFAULT_BANLIST_FILE` 硬编码桌面路径

```python
DEFAULT_BANLIST_FILE = 'C:/Users/Administrator/Desktop/banlist.txt'
```

在新机器/新用户上必定不存在，开箱即用承诺破灭。改为项目根的 `config/banlist.example.txt` 或 `%USERPROFILE%/...` 才合理。

### 5. CLI 与 GUI 行为不一致

`cli.py:21-23`：
```python
roi_str = config.get('scan.roi_rect')
if roi_str:
    pipeline.set_roi(tuple(roi_str))
```

**不看 `scan.enable_roi`**——只依赖 `capture.py:35` 的"防御性二次校验"救场。这把判断放在 `capture` 既职责错位也容易让人误解（cli 改了配置以为关掉 ROI 了，其实是 capture 救了）。

**修法**：判断挪到 cli/scan_worker 的"准备 roi"那一步，capture 不应承担。

### 6. `build.spec` 与运行时分歧

- defaults 里默认 `banlist_file` 指向桌面但 spec 没打包示例文件；
- `hiddenimports` 列了 `paddlepaddle`（实际包名是 `paddle`）。打包过的话八成踩过。

---

## 二、代码冗余（可直接删/合并）

### 1. 6 处重复的"SVG → 染色 → QPixmap → QIcon"逻辑

| 文件 | 函数 |
|---|---|
| `ui/widgets/sidebar.py` | `_render_svg_to_pixmap` |
| `ui/widgets/log_panel.py` | `_make_broom_icon` |
| `ui/widgets/config_panel.py` | `_render_svg` |
| `ui/widgets/settings_card.py` | `_svg_icon` |
| `ui/tray.py` | `_draw_fallback_icon` 内嵌 |
| `ui/pages/about_page.py` | `_hero_icon` |

核心步骤完全一致（读 bytes → `replace(b'currentColor', color)` → `QSvgRenderer` → `QPixmap.fill(transparent)` → `render`）。抽到 `ui/svg_utils.py::render_svg_icon(svg_bytes_or_path, color, size, as_icon=False)` 后能干掉 80+ 行。

### 2. 几乎相同的两个 `_slider` helper

`ui/widgets/config_panel.py::_slider_row`（返回 HBoxLayout）vs `ui/pages/settings_page.py::_slider`（返回 QFrame）。逻辑一模一样，差别只在容器类型。合并成一个返回 QFrame，HBoxLayout 用法处 `addWidget(frame)` 完全等价。

### 3. 死代码（grep 全工程 0 调用方）

| 位置 | 函数/方法 |
|---|---|
| `pipeline/matcher.py:50` | `keyword_in_text()` |
| `pipeline/matcher.py:78` | `SubstringMatcher.banlist_file` property |
| `pipeline/matcher.py:82` | `SubstringMatcher.keywords` property |
| `pipeline/matcher.py:85` | `SubstringMatcher.get_hint()` |
| `pipeline/matcher.py:199` | `get_cached_matcher()` + `_cache` + `_cache_lock` |
| `ui/scan_worker.py:40` | `ScanWorker.set_roi()`（注释吹的"运行中切 ROI"无调用方） |
| `ui/widgets/config_panel.py:420` | `ConfigPanel.reload_from_config()` |
| `ui/widgets/settings_card.py:169` | `HotkeyDisplay.set_hotkey()` |
| `ui/widgets/sidebar.py:159` | `Sidebar.setCurrentRow()` |
| `pipeline/ocr_stage.py:111` | `OCRStage.release()` — GUI 永远不调（worker 注释明确写不释放） |

### 4. `pipeline/matcher.py::_log` 的双重防御

```python
def _log(self, level, msg):
    if self._logger is None:
        return
    getattr(self._logger, level, lambda *_: None)(msg)
```

已经 None 短路了，下面的 `lambda *_: None` 兜底没有触发路径，删。

### 5. `Overlay._cfg` 的 except TypeError 是僵尸守卫

```python
try:
    v = self._config.get(key, default)
except TypeError:
    v = self._config.get(key)
```

`Config.get(key, default=None)` 永远接受第二参数，TypeError 无触发路径。删。

### 6. CLI 中变量命名错误

`cli.py:21`：`roi_str = config.get('scan.roi_rect')` — 拿的是 list，叫 `roi_str`。

---

## 三、具体实现的逻辑反复 / 可简化

### 1. 高频写盘（slider 拖动期间每次值变都 `config.save()`）

`config_panel.py / settings_page.py` 里的每一个 `valueChanged`：
```python
lambda v: (config.set('xxx', v), config.save())
```

拖 slider 一次能触发几十次磁盘写。

**修法**：`Config` 加 `_save_timer = QTimer / threading.Timer` 节流，所有 `set` 后调用 `save_debounced(delay_ms=200)`；或写一个 `config.set_and_save()` helper 内置节流。

### 2. `_make_group`（config_panel）与 `SettingsCard`（settings_card）两套近似容器

都是"标题 + 内容垂直堆"。视觉差异（pill 小色块 vs 卡片边框）应在 QSS 层面切，Python 层合并成一个组件即可。

### 3. `Overlay.update(self, ocr_results, matches)` 与 `QWidget.update()` 同名

是个潜在陷阱：父类 `update()` 是触发重绘的无参方法，被覆盖后类外只能传参调用，类内还要 `super().update()` 才能重绘。文件里也确实这么写了。改成 `refresh(ocr_results, matches)` 或 `update_data(...)` 更安全。

### 4. `Overlay.destroy` 复用 Qt 保留名

`QWidget.destroy()` 在 Qt 里有具体语义（销毁底层 X/Win window），项目里覆盖成 close+deleteLater 容易让 reader 误解。改名 `cleanup()`。

### 5. `ScanWorker._sleep_with_check` 累加变量与实际睡眠量解耦

```python
slept += step           # 实际可能 sleep 了更短
```

`slept` 只参与循环条件 `slept < seconds`，不外传，所以**功能完全正确**。仅风格：若未来想把 `slept` 暴露给外部（例如打 metric），需要先改成 `slept += min(step, seconds - slept)`。低优。

### 6. `_resolve_roi` 预设丢失静默 fallback 全屏

```python
# 预设被删了或名字不对，fallback 全屏
return None
```

没有 log.warning，用户开了 ROI 但意外扫了全屏会一脸懵。加一行 `logger.warning(f"预设 {last} 不存在，本次回退全屏")`。

### 7. `HotkeyManager.register` 失败静默

库没装 / 没权限时只 warning，没返回成功标志。MainWindow 不知道注册结果，按钮和热键的行为对等性无法保证。返回 bool，让 MainWindow 至少能在状态栏标 "热键不可用"。

### 8. `pipeline.pipeline:32` 重复 fallback

```python
banlist_file = config.get('files.banlist_file', DEFAULT_BANLIST_FILE)
```

defaults 深合并已经保证有值，这里再传 fallback 是冗余。`config.get('files.banlist_file')` 足够。`CLAUDE.md` 里也明确写了"defaults 已合并，通常无需传 default"。

---

---

# 第二轮补充审查（2026-05-13）

接续第一轮，按 9 个角度展开。剔除"打包与发布"和"跨平台/移植性"。每条都附文件:行号定位。

---

## 四、并发与线程安全

### 4.1 `Config` 单例无锁，跨线程读写有窗口
`config/config.py`：`_data` 字典在多个线程被访问。
- 主线程：GUI slider/checkbox 触发 `config.set(...)` → `config.save()`，写 `_data` 并落盘。
- worker 线程：每次 `scan_once` 通过 `config.get('scan.interval_seconds')` 等读 `_data`（`pipeline/diff_gate.py:21`、`pipeline/ocr_stage.py:14-15`、`pipeline/capture.py:35,40`、`ui/scan_worker.py:86` 等）。

`Config.get`（`config.py:53-64`）的 dotted-key 是循环遍历：
```python
for k in keys:
    if isinstance(val, dict) and k in val:
        val = val[k]
```
如果 worker 在中途读，主线程同时 `set` 改了中间节点，理论上可见中间状态。**风险低（Python dict 单步操作受 GIL 保护、且嵌套节点很少同时改），但形式上不是 thread-safe**。建议：要么加 `threading.RLock` 包 `get/set/save`，要么明确文档"config 写仅限主线程，worker 不写"。

### 4.2 `Config` 懒加载多次触发
`config/config.py:55-56`：
```python
def get(self, dotted_key, default=None):
    if not self._loaded:
        self.load()
```
首次访问时多线程并发能同时进入 `load()`，浪费一次磁盘读 + deep_merge。结果一致所以不会错，但应在 `__new__` 或 `app.py / cli.py` 启动时**显式预热一次**，去掉 `get/set` 里的懒加载分支。

### 4.3 `Config.save` 多写者会撕裂文件
`config.py:75-77` 用 `yaml.dump` 写整文件，无锁。当前**事实上只有主线程写**（worker 不调 set），但接口没有强制约束，未来如果在 worker/热键回调里写就会产生 yaml 半截损坏。注释里也没声明"save 只能主线程调"。

### 4.4 `pipeline/ocr_stage.py` 模块级单例的跨线程访问
`_ocr_instance` / `_ocr_init_config` 是模块级全局（`ocr_stage.py:8-9`），由 worker 线程的 `_get_ocr()` 读写。如果未来在主线程做"预热 OCR"按钮，会撞车。建议加 `threading.Lock` 保护 `_get_ocr` 内的 instance 切换。

### 4.5 Qt Signal 跨线程默认 AutoConnection — 实际验证过都正确
查了所有 `connect` / `emit`（结果见上）：
- `worker.result_ready` / `worker.status_changed` → 主线程槽，Qt 自动选 QueuedConnection ✅
- `_hotkey_start_requested.emit` 由 keyboard 库线程调用 → 主线程槽，自动 QueuedConnection ✅
- `LogBridge.emit` 由任意 logging 调用线程触发 → 主线程 `LogPanel.append`，自动 QueuedConnection ✅

注释里说"signal queued connection 中转"是对的。**仅一处隐患**：`scan_worker.result_ready.emit(result.ocr_results, result.matches)`（`scan_worker.py:108`）传的是 list 引用，与 pipeline 内部 `_last_result.ocr_results` 是同一对象。当前 pipeline 每次扫描都**整体替换** `_last_result`，不会就地改写，所以安全。但若未来改成增量修改 list，主线程 Overlay 渲染期间 worker 线程改动会出问题。建议 emit 时 `list(...)` 浅拷贝一份。

### 4.6 `ROIPicker.pick()` 内嵌 QEventLoop 调用栈耦合
`ui/roi_picker.py:49-51`：`self._loop = QEventLoop(); self._loop.exec()`。这是从 `_on_start`（主线程 slot）发起的阻塞调用，期间 worker 还能照常发 signal 进队列。`exec()` 返回后队列里堆积的 `result_ready` 一次性 flush，可能导致框选过程结束瞬间 Overlay 闪一下旧数据。当前 `_on_start` 先 `_resolve_roi`（含 picker）再 `worker.start_scan`，所以 picker 期间 worker 还没启动 → 队列里没东西。但**未来如果允许"运行中重选 ROI"**（注释里 `ScanWorker.set_roi` 暗示过），就要处理积压。

---

## 五、错误处理与鲁棒性

### 5.1 13 处 `except .*: pass`（含 swallow）
完整列表（grep 验证）：
| 文件:行 | 上下文 | 评估 |
|---|---|---|
| `app.py:27-28` | SetCurrentProcessExplicitAppUserModelID 兜底 | 合理（非关键路径） |
| `config/config.py:47-48` | FileNotFoundError，首次启动 yaml 不存在 | 合理 |
| `pipeline/capture.py:29-30` | sct.close() 失败 | 合理（清理） |
| `pipeline/matcher.py:144-145` | os.path.getmtime 失败时静默 return | **可疑**：mtime 失败一般是路径消失，应 warn |
| `utils/hotkey.py:29-30` | keyboard.remove_hotkey 失败 | 合理 |
| `utils/hotkey.py:32-33` | 整段 unregister_all 兜底 | 多此一举（外层 try 嵌套，可删） |
| `ui/main_window.py:192-207` | closeEvent 4 段清理 | 合理但**全吞**，应 `logging.exception` |
| `ui/overlay.py:116-117` | destroy 的 close+deleteLater | 合理 |
| `ui/overlay.py:264-265` | `except TypeError` 僵尸守卫 | 上一轮已记 |
| `ui/pages/about_page.py:55-56` | webbrowser.open 失败 | 合理但**用户无反馈** |
| `ui/widgets/config_panel.py:400-401` | os.startfile 失败 | 同上，用户无反馈 |
| `ui/widgets/status_bar.py:82-83` | _get_memory_mb 整段 except | 合理（边缘功能） |

**总体倾向**：清理路径 + 用户体感不强的边缘调用，吞了无所谓；但 `webbrowser.open` / `os.startfile` 失败用户主动触发的，应该弹消息盒或日志可见。

### 5.2 18 处 `logger.error / logging.error` 全部不带 stack
全工程 0 处 `logging.exception` / `traceback`。所有错误日志写法都是：
```python
logging.error(f'扫描线程异常: {e}')                    # scan_worker.py:66
logging.error(f'scan_once 失败: {e}')                  # scan_worker.py:91
self._log('error', f"加载关键词文件失败: {e}")        # matcher.py:124
logger.error(f"注册热键失败 {hotkey}: {e}")           # hotkey.py:21
```
出问题只能看到一句字符串，没有 traceback。**改成 `logging.exception(...)` 是 1 行改动，收益巨大**。

### 5.3 `scan_once` 失败后无退避，原地高频重试
`ui/scan_worker.py:88-93`：
```python
try:
    result = self.pipeline.scan_once()
except Exception as e:
    logging.error(f'scan_once 失败: {e}')
    self._sleep_with_check(interval)
    continue
```
如果是永久性失败（如 paddle DLL 缺失、GPU 显存挂了），每 `interval` 秒打一行 ERROR 直到用户停。**应该计数连续失败次数，到阈值后**：
- 状态栏切"已停止（异常）"
- 自动 stop_scan()
- 弹通知"扫描已停止，详见日志"

### 5.4 ScanWorker 异常退出与正常退出状态相同
`scan_worker.py:62-67`：
```python
try:
    self._do_init()
    self._do_loop()
except Exception as e:
    logging.error(f'扫描线程异常: {e}')
    self.status_changed.emit('已停止')
```
crash 路径和用户点"停止"都 emit `'已停止'`。状态栏 `_STATUS_COLOR` 把"已停止"染红，本意是"非工作中"，但混淆了**用户停止**和**异常崩溃**。建议加 `'异常停止'` 状态。

### 5.5 模型加载失败用户看不到原因
`scan_worker._do_init`（`scan_worker.py:73-81`）：
```python
self.status_changed.emit('初始化中')
self.pipeline.init()
self._initialized = True
```
`pipeline.init()` 在 `OCRStage.init` 里调 `_get_ocr()`，若 paddle 没装好直接抛 ImportError 或 RuntimeError。被上层 `try` 抓后只是日志 + 状态切"已停止"。新用户首次启动 GPU 没装会一脸懵，建议在 `_do_init` 单独捕获，emit 一个 `init_failed(reason: str)` signal，让 MainWindow 弹 QMessageBox 给出修复建议。

### 5.6 关键词文件被独占时静默清空
`pipeline/matcher.py:109-125`：`load()` 用 `open(path, 'r')`，记事本独占模式（开 .txt 又锁了）会 PermissionError → 落到 `except Exception` → `_keywords = {}` 已在前面 reset，结果**关键词库被清空**，扫描继续但永远不匹配。
**修法**：捕获后保留原有 `_keywords` / `_automaton`（先暂存到局部变量，成功才赋值）。

### 5.7 `os.startfile(path)` 用户可控路径
`ui/widgets/config_panel.py:398-401`：banlist_file 来自用户浏览，用户可以指到 `.exe / .bat / .ps1`，"编辑"按钮就会执行它。当前是单机本地工具，**安全风险极低**；但代码上应当 `if path.lower().endswith('.txt'):` 加白名单，规避未来万一引入"导入远程配置"功能后的攻击面。

### 5.8 `Config.get(key)` 不传 default 时返回 None — 业务 falsy 检查会误判
`config/config.py:51` 签名 `get(dotted_key, default=None)`，当 yaml 写错或 defaults 漏键时返回 `None`。业务代码若写 `if not config.get('xxx'):`，**`None` / `0` / `0.0` / `False` / `''` 五种值会触发同一分支**。`CLAUDE.md` 明确说"defaults 深合并已经保证有值，通常无需传 default"，这个约定一旦被破坏（新增字段忘了写 defaults / yaml 老版本残留），bug 会以"开关失效"或"阈值变 0"的形式悄悄出现。

**修法**：
- 短期：业务代码做 falsy 检查时显式与 `None` 比较（`if config.get('xxx') is None:`）
- 长期：见 §13.5，dataclass / pydantic 模型从根上消除 dotted-key 返回 `Any` 的问题

---

## 六、资源管理 / 长跑稳定性

### 6.1 PaddleOCR 长跑显存增长（已知社区问题，本项目无兜底）
`OCRStage` 单例驻留整个进程生命周期。PaddleOCR GitHub issue tracker 多个 "memory leak after long inference" 报告。**当前没有定期 reload 机制**，跑一周 + 大量画面变动后 GPU 显存可能涨到 OOM。
**修法**：可以加一个"每 N 小时或每 M 帧 OCR 后，触发 `OCRStage.release` + 重建"。

### 6.2 `Overlay` 永久持有
`MainWindow.__init__` 创建 Overlay，主窗关到托盘后 Overlay 仍存活（hide 不释放）。无功能问题，但每个 Overlay 内有缓存的字体、QFontMetrics、行数据 list；长跑下 `_session_matches` 字典只增不减（直到用户点"开始扫描"触发 `clear_session`）。
**修法**：在 `_session_matches` 累计到阈值（如 500 个 keyword）时 warn + cap。

### 6.3 `LogPanel` 内存上限
`ui/widgets/log_panel.py:76`：`setMaximumBlockCount(10000)`。日志超过 10000 段后**静默丢弃**，用户排查 issue 拉到顶看不到事故初期。
**修法**：日志同时写到 `logs/app.log`（接 §一.1 提到的 RotatingFileHandler 实现）。

### 6.4 `OCRStage.release` GUI 永远不调
`scan_worker.py:68-71` 注释明确"worker 退出不释放 pipeline"，pipeline.release 也没被 MainWindow.closeEvent 调过。**程序退出靠 OS 收内存**。当前 Qt 应用退出时 PaddleOCR 析构可能挂很久（gc + paddle.fluid 退出），用户感觉"关了主窗口还卡好几秒"。
**修法**：closeEvent 真退出路径下，spawn 一个守护 daemon thread 调 `pipeline.release()`，主进程不等它。

### 6.5 ScanWorker 退出不清理 `_initialized`
`scan_worker.py:36` 字段 `_initialized = False`，但 worker run 退出后不重置。下次 `start_scan` → 新 thread → `_do_init` 再次执行 init（OCRStage 单例已存在所以快速返回），但 `self._initialized` 这次重新被设 True，逻辑无问题。**仅风格**：退出时 `self._initialized = False` 更对称。

---

## 七、性能热路径

### 7.1 DiffGate 用 `cvtColor` 多一步
`pipeline/diff_gate.py:24-25`：
```python
gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
thumb = cv2.resize(gray, (160, 120), interpolation=cv2.INTER_AREA)
```
全屏 4K 截图 cvtColor 单步 ~5-10ms；diff_threshold 命中时这是 pipeline **唯一**开销。可以反向：先 resize 到 160x120 BGR（4×缩减），再 cvtColor，把 cvtColor 的工作量降 16×。或者更激进：取 BGR 单通道 (B 或 G) 直接 resize 当灰度近似，对场景变动检测足够。

### 7.2 `SubstringMatcher.reload_if_changed` 每次扫描调
`pipeline/matcher.py:159`：`match()` 入口每次都 `reload_if_changed` → `os.path.getmtime`。一次 syscall ~ 几十 μs，每秒数次，相对 OCR 几百 ms 可忽略。**不优化**。

### 7.3 `Overlay._compute_rows` 每次扫描重建
所有行的 `horizontalAdvance` 测宽 + `QFontMetrics` 重建 + 排序。OCR 行多时是 O(n)，但 Python 层，对 50 行 OCR 大概 < 1ms。**不优化**。

### 7.4 `Config.save` 写盘节流（前文 §三.1 已记）
slider 拖动每次 valueChanged 都 fsync。Windows 上一次 yaml.dump 20-50ms，UI 线程会有可感卡顿。**值得做**：上次提到的 200ms debounce。

### 7.5 `cv2.resize INTER_AREA` 对 160x120 足够
当前用 `INTER_AREA`（高质量下采样），对帧差检测来说 `INTER_NEAREST` 都够，可以再省 30%。**收益小，不必动**。

### 7.6 OCRStage 跳过文档方向检测已做
`ocr_stage.py:27-34` 已显式禁用 `use_doc_orientation_classify` 等 3 项。注释解释清楚（屏幕截图始终正向）。✅

---

## 八、测试覆盖

### 8.1 现有 2 个测试中有 1 个已坏
`tests/test_config_keys.py:16`：
```python
assert scan['roi_rect'] == [1170, 256, 1880, 843]
```
但 `config/defaults.py:25` 是 `[1136, 250, 1858, 850]`。**`pytest tests/` 现在直接挂**。要么改测试，要么改默认值，**这个 mismatch 自相矛盾**——defaults 注释还在吹"[1136, 250, 1858, 850] 是项目工作区域"。

### 8.2 业务核心零覆盖
- `pipeline/matcher.py`（归一化 + AC 自动机 + mtime 重载 + 多模式匹配） — **零测试**。CLAUDE.md 提到的"`034`、`da` 误判长串"历史 bug 没有回归保护。
- `pipeline/diff_gate.py`（首帧/相同帧/差异帧三态 + reset） — 零测试。
- `pipeline/ocr_stage.py` 的 v2/v3 格式分支 — 零测试（虽然依赖 PaddleOCR 难 mock，但 `_get_ocr` 的单例语义可单测）。
- `pipeline/pipeline.py` 的 diff-skip 复用上次结果逻辑 — 零测试。
- `config/config.py` 的 `_deep_merge` — 零测试，但这是用户配置和默认值合并的核心，应单测。

### 8.3 测试入口在 CLAUDE.md 未提
新读者打开项目，CLAUDE.md 没说 `pytest tests/` 是测试入口，也没说测试用什么框架（虽然文件里用了 plain assert，能直接 `python tests/test_config_keys.py` 跑）。

### 8.4 建议补充测试清单
按优先级：
1. `test_matcher.py`：归一化（`_normalize` 对中文/英文大小写/标点处理）、`parse_keyword_line` 三种格式、子串匹配不误判、mtime 重载、文件被独占时不清空（§五.6 修后）。
2. `test_diff_gate.py`：首帧返回 False、相同帧返回 True、变化帧返回 False、阈值边界、reset 后重新返 False。
3. `test_config_deep_merge.py`：覆盖 default 中没有的 key 由 yaml 添加、嵌套 dict 合并、用户管理字典（roi_presets）删除后不复活。
4. `test_pipeline_skip_reuse.py`：diff_gate 命中时返回 last 结果，skipped=True，duration 重算。

---

## 九、注释与文档质量

### 9.1 引用已删除文件的死链接
- `ui/sound.py:3-4`："被 ui/overlay.py（新 PySide6 版）和 shared/overlay.py（旧 tkinter 版）共用" — **shared/ 目录不存在**。
- `ui/overlay.py:77`：`# ============ 公开 API（与 shared/overlay.py 对齐）============`
- `ui/overlay.py:119`：`# ============ 渲染：行数据计算（搬自 shared/overlay.py 视觉规则）============`
- `ui/widgets/status_bar.py:46`：`"""搬自 app.py.tk_backup:_get_memory_mb..."""` — **app.py.tk_backup 不存在**。

### 9.2 引用历史 TODO 编号 T17 / T23
- `ui/pages/settings_page.py:175`：`# T23 接入 HotkeyManager 后这里改成可编辑；当前只读显示`
- `ui/pages/settings_page.py:203`：`# T17 才真正接入；当前是空槽`
- `ui/widgets/settings_card.py:147`：`"""具体编辑流由 T23 HotkeyManager 接入）。"""`

事实上 `HotkeyManager` 已经实现并接入 `MainWindow.__init__:100-102`、`SettingsPage._on_reset` 也已经接入 `config.reset_to_defaults()`。注释**严重落后于现实**。

### 9.3 注释承诺了不存在的行为
- `ScanWorker.set_roi`（`scan_worker.py:40-44`）注释 "运行中改 ROI 立即生效" — grep 全工程无调用方（前文 §二.3 已列）。注释比死代码更危险：未来 reader 会以为这个能力存在。
- `OCRStage.release`（`ocr_stage.py:111-117`）注释暗示是清理入口，但 GUI 永远不调（前文 §六.4）。

### 9.4 `HotkeyDisplay` 的铅笔按钮误导
`ui/widgets/settings_card.py:160-167`：渲染了"铅笔编辑"按钮 + `edit_clicked` signal，但 `settings_page` 里**没人 connect**。用户看到铅笔按钮以为能改热键，点了没反应。属于 UI 半完成态。

### 9.5 文档与 CLAUDE.md 描述脱节
- CLAUDE.md 说 "`ui/sound.py` CHORD_WAV 字节" — 实际还有 `_build_chord_wav` 函数生成它，注释里说"被 tk 版共用"过时。
- CLAUDE.md 说 "logging 配置：DEBUG / INFO / WARNING / ERROR、日志文件路径、max_bytes、backup_count" — 实际除 level 外都未实现（§一.1）。

### 9.6 注释体量过大（部分）
`ui/main_window.py:96-99` 4 行注释解释 1 行代码，`ui/widgets/config_panel.py:18-23` 7 行注释解释 2 个常量。可读性 OK，但**部分注释完全可以删**（如 `config_panel.py:108-115` 详述了"按下区域内释放才发 clicked"——这是 PyQt 标准按钮行为，不解释也不会有人误读）。

---

## 十、用户体验里的边界状态

### 10.1 多屏：Overlay / ROIPicker 都只看主屏
`ui/overlay.py:130,205,277` 三处 `QGuiApplication.primaryScreen()`。`ui/roi_picker.py:35` 也仅 primary。在副屏跑的用户：
- 想框副屏内容 → picker 只覆盖主屏，没法选副屏。
- 即使 cli 配了副屏 ROI 坐标，匹配到关键词后 Overlay 总弹在主屏。

注释承认了 picker 单屏，但 Overlay 那里没解释。**应在副屏检测到 ROI 后让 Overlay 跟到那块屏**，或至少明确说 "目前仅主屏"。

### 10.2 启动 5-15 秒加载期反馈不足
worker `_do_init` 只 emit 一次 `'初始化中'` 状态。日志第一行有 "正在初始化 OCR 模型与关键词…"。**没有进度条、没有"还要多久"提示**。用户首次启动会以为程序卡了。

### 10.3 OCR 配置改动当前扫描不停就不生效
- 改 OCR 语言/GPU → 下一次 `scan_once` 调 `_get_ocr` 检测元组变化重建 → **下一次扫描才换模型**，且重建会卡 5-15s 让用户惊吓。
- 改 `min_confidence` / `enable_image_invert` → 立即生效（每次 recognize 都读 config）。
- 改 `scan.diff_threshold` / `scan.interval_seconds` → 立即生效。

**应在 GUI 切语言/GPU 时弹一句 "扫描中改动会触发模型重载，可能卡 10 秒"**，或者干脆禁用这些开关只在停止状态下可改。

### 10.4 `_resolve_roi` 预设丢失 / 取消 / 全屏 fallback 都没视觉提示
- 预设被外部删了 → fallback 全屏（`main_window.py:148`）无日志、无提示。
- picker 取消 → 启动流程静默放弃，按钮回弹但无文字说明"已取消"。
- `enable_roi=False` → 直接全屏，但 sidebar 的 ROIBorder 红框 hide 后用户没法直观知道"现在扫的是全屏"。

### 10.5 关键词文件不存在/为空，匹配静默失败
matcher.load 失败只记 warning，状态栏 / 标题栏 / 用户视野零提示。用户配错路径后扫一天，"为啥从来不弹浮窗" 完全不知道。**应在状态栏加 "关键词：N 条"**。

### 10.6 启动模式 auto 但 OCR 还没好就响应热键
`main_window.py:105-106` startup_mode=auto 时延迟 200ms `_on_start`，但 OCR init 在 worker 里要 5-15s。这期间用户敲 Ctrl+Alt+2 停止——会触发 `worker.stop_scan` 设置 `_stop=True`，但 worker 还在 init 阶段不 check `_stop`，初始化完后才退出。"用户感觉停了但其实还在加载"。

### 10.7 banlist 路径用户写错时无回显
`ConfigPanel` 用 QFileDialog 浏览选择，路径会落进 yaml；但 banlist 也可能用户手动改 yaml 写错 + 重启。matcher 加载失败只 log warning。**配置面板应在路径变化时 stat 文件**，红字提示"文件不存在"。

### 10.8 拖 slider 期间 yaml 持续写盘 → 偶发 UI 卡顿
前文已记。用户视觉感受是 slider 拖动不流畅，看不到底层原因。

---

## 十一、配置 schema 演化

### 11.1 `Config.save()` 全量覆盖，用户注释丢失
`config.py:75-77` 用 `yaml.dump(self._data, ...)` 写全字段。**任何用户在 yaml 里加的注释 / 字段顺序 / 空行格式都会被擦掉**。当前 yaml 文件就只是数据存储，没有"用户可读编辑"语义。
**两个方案**：
- 接受现状，明确文档"yaml 由程序管理，请用 GUI 编辑"。
- 改用 ruamel.yaml 的 round-trip mode 保留注释（依赖更重）。

### 11.2 无 schema 版本号，老 yaml 升级有"幽灵字段"风险
未来如果把 `enable_roi` 改成 `roi_mode: enabled/disabled/preset`，老 yaml 里的 `enable_roi: true` 会通过 deep_merge 保留在 `_data['scan']['enable_roi']` 里，业务代码读不到也不会清理。yaml 越积越多老字段。
**修法**：defaults 加 `schema_version: 1`，load 后检查版本，写 migration 函数。当前没必要立即做，但应在 README/CLAUDE.md 标注 "破坏性配置变更需写 migration"。

### 11.3 用户管理字典的"复活"约定无强制
defaults.py 注释（`config/defaults.py:26-29`）说 `roi_presets` 必须默认 `{}`，否则用户删除后 deep_merge 会让 default 项复活。这是个**靠人记**的约定。未来加新的用户字典（如"关键词组预设"）必须遵守。
**修法**：要么在 `_deep_merge` 加一个 "用户管理" 标记白名单，要么在 Config 内显式做"用户字典 = yaml 优先且不合并"的特殊处理。

### 11.4 默认配置与当前 yaml 冲突需要决定
- defaults.py：`minimize_to_tray: True`、`interval_seconds: 5.0`、`min_confidence: 0.3`、`display_duration: 3.0`
- config.yaml：`minimize_to_tray: false`、`interval_seconds: 3.0`、`min_confidence: 0.28`、`display_duration: 2.5`、`roi_presets: {4+2: ...}`

这些是用户在使用中改出来的值。**问题**：`tests/test_config_keys.py:26` 还在断言 `minimize_to_tray is True`——defaults 真要改 `False` 测试就过了，目前是矛盾的（defaults True、当前 yaml False、测试期望 True）。

### 11.5 `roi_rect` 默认值与 `last_roi_choice='__reselect__'` 自相矛盾
defaults 同时给了：
- `roi_rect: [1136, 250, 1858, 850]`（具体坐标）
- `last_roi_choice: '__reselect__'`（启动弹 picker）

按 `_resolve_roi` 逻辑，第一次启动会走 picker 分支，**`roi_rect` 默认值永远走不到**。要么把 `roi_rect` 默认 `None`，要么 `last_roi_choice` 默认 `'__custom__'` —— 两者保持一种意图。当前是两份意图打架。

---

## 十二、可观测性 / 调试支撑

### 12.1 总共只有 18 处 log 调用
`logging.* / logger.*` 全工程 18 次，分布：
- pipeline/diff_gate.py: 2（debug 级，输出帧差值）
- pipeline/ocr_stage.py: 4
- utils/hotkey.py: 3
- ui/scan_worker.py: 9

**缺的维度**：
- 没有 startup banner（版本号、配置摘要、CUDA 状态）
- 没有"匹配命中率"聚合 metric
- 没有"OCR 平均耗时 / 帧差 skip 率" 统计
- 没有按 N 次扫描汇总的"扫描健康度"

长跑回看时用户只能看到一行一行 INFO，**无法判断"今天扫了 8 小时是不是正常"**。

### 12.2 错误日志无 traceback（§五.2 已记，强调）
所有 `logging.error(f'...{e}')` 应改为 `logging.exception(f'...')`。这是 Python 日志最佳实践，且改动成本极低。

### 12.3 无 file handler，崩溃后日志丢失
`logs/` 目录存在但**永远是空**的。GUI 模式 LogPanel 内存里 10000 行后丢弃，崩溃后用户找不到任何前情日志。
**修法**：utils/logger.py 加 `RotatingFileHandler` 用 `config.yaml` 的 `logging.file / max_bytes / backup_count`（这些字段已经在 defaults 里，只是没用）。

### 12.4 无运行时 metric 暴露
程序内部状态（连续多少帧 skip、OCR 平均耗时、命中关键词 top-N）只能从日志逐行 grep 还原。**修法**：状态栏多加一段"今日：OCR N 次 / 命中 M 次 / 平均 Tms"。或者写到 `logs/metrics.jsonl` 一行一条。

### 12.5 无 `--profile` / `--debug` 启动开关
现在只有 yaml 配置 logging.level。想临时打印详细 trace 还得改 yaml 再启动。**修法**：`app.py / cli.py` 加 argparse，支持 `--debug` / `--profile`，便于排查现场问题。

---

## 十三、架构层面的可重构机会

前面 1-12 章是"实现层"的 bug 和瑕疵；这一章是"如果项目代码量再涨 3 倍，现在哪些选择会变成债"。每条都不紧急，但应在架构会议上有意识地选择"做"或"不做"。

### 13.1 全局可变 `Config` 单例 → 应改为不可变快照 + 显式 update
当前 worker 线程每次 `scan_once` 都从全局可变 `config` 读最新值（`pipeline/diff_gate.py:21`、`pipeline/ocr_stage.py:14-15`、`pipeline/capture.py:35,40`）。这导致：
- pipeline 不是纯函数，单元测试必须 mock 全局单例（§八.2 测试覆盖率低的根因之一）
- 热重载语义分散在各阶段（matcher 看 mtime、OCR 看元组 diff、其它看每次 `config.get`）
- §四.1 / §四.4 提到的线程安全问题本质都是"全局可变状态"的衍生

**重构方向**：
- `ScanWorker.start_scan()` 时把当前 config freeze 成 `ScanConfig` 不可变 dataclass
- pipeline 各阶段 `__init__(cfg: ScanConfig)`，不再 import 全局 config
- 配置变更走 `worker.update_config(new)` 显式接口，pipeline 内部 swap 快照

收益：测试不用 mock 全局态；配置变更点收敛到一处；热重载语义统一。代价：一次较大的内部 API 改动。

### 13.2 缺 Stage 协议，新增管线阶段需改 pipeline 本身
`ScanPipeline.__init__` 硬编码四个阶段实例，每个的方法名也不同（`grab` / `should_skip` / `recognize` / `match`）。CLAUDE.md "扩展模式"教人参考极简形式，但每加一个阶段都要改 `scan_once` 的串联逻辑。

**重构方向**：定义 `Stage(Protocol)` 接口（`process(ctx) -> ctx`），pipeline 改成 `stages: list[Stage]`，`scan_once` 退化为 `reduce(stages, ctx)`。

**何时该做**：当前 4 阶段稳定，**不急**；如果未来要加 "前处理（去噪/二值化）" 或 "后处理（按区域过滤）" 阶段，先做这一步。

### 13.3 UI 与业务逻辑耦合在 `ScanWorker` 里
`ScanWorker(QThread)` 同时承担：（a）业务调度（pipeline.init / 循环 scan_once）；（b）UI 桥接（status_changed / result_ready Signal）；（c）状态机（`_initialized` / `_stop` / `_roi`）。

后果：
- 业务路径无法独立测试（§八.2 pipeline.scan_once 复用上次结果零覆盖，部分原因是测试需要起 QThread）
- CLI 模式（`cli.py`）的循环是完全独立实现，与 GUI 重复（间接导致 §一.5 CLI 不看 enable_roi）

**重构方向**：抽 `BackgroundScanner`（纯 Python，无 Qt 依赖）持有 pipeline + 状态机 + 回调；`ScanWorker(QThread)` 退化为薄薄一层，只把 scanner 回调转 Signal；CLI 直接复用 `BackgroundScanner`。

### 13.4 三种热重载策略各自实现，缺统一通知机制
- matcher：`reload_if_changed` 在每次 `match()` 入口检查 mtime
- OCR：`_get_ocr()` 检查 `(lang, gpu)` 元组 diff
- 其它阶段：每次 `config.get` 直接读

各自都正确，但**没有统一的"配置变更通知"**。结果是 §一.2 OCRStage 双单例 bug 这种"实例字段没跟上模块单例"的问题只会在某种特定热重载策略下出现，难以系统性排查。

**重构方向**：`Config` 加 `subscribe(key_prefix, callback)`；OCRStage 订阅 `ocr.*` + `gpu.*`，matcher 订阅 `files.banlist_file`，pipeline 阶段不再每次轮询。配合 §13.1 的 freeze 快照，可以做得很干净。

### 13.5 dotted-key 字符串访问 → 类型不安全
`config.get('ocr.min_confidence')` 返回 `Any`，IDE 无补全、无类型检查、改 key 名要全局 grep。`config/defaults.py` 是结构良好的 dict 但被当字符串字典用。

**重构方向**：
- 轻量：`TypedDict` + 用 `cfg["scan"]["interval_seconds"]` 替代 dotted-key
- 中量：`dataclass` + `from_dict()` 反序列化，业务代码用 `cfg.scan.interval_seconds`
- 重量：`pydantic` 模型，自带校验和 schema 版本管理（顺便覆盖 §十一.2）

**何时该做**：现在配置项 ~30 个还能 hold；超过 50 个或新加复杂嵌套结构（如"按预设组合"）时必须做。

### 13.6 测试覆盖低的结构性根因
§八.2 列了 5 处零测试模块，但**没归因**。真实原因：
- pipeline 各阶段 import 全局 config → 单测要 mock 单例
- ScanWorker 是 QThread 子类 → 业务测试要起 Qt 事件循环
- matcher 通过 mtime 触发 reload → 测试要操纵文件系统时间

§13.1 + §13.3 落地后，pipeline / scanner 都能纯函数测试，§八.4 列的 4 个测试文件能 ≤ 1 天写完。**这条不是独立的架构项，是 §13.1+§13.3 的副产品**。

---

## 修复优先级总览（统一排序，按 风险×代价 / 杠杆）

### 立即修（成本 < 30 分钟、影响功能或诊断）
1. **`test_config_keys.py` 已坏** — 改 expected 值或改 defaults，二选一（§八.1）
2. **`matcher` 加载失败时清空关键词** — 用户在 GUI 模式下记事本打开 banlist.txt 就匹配静默失效；改成保留旧值（§五.6）⬆️ *从短期修升级*
3. **OCRStage `self._ocr` 字段不同步** — 用户改 GPU/语言后下次 scan 还用旧模型（§一.2）
4. **所有 `logging.error(f'...{e}')` → `logging.exception(...)`** — 1 行 1 处，故障排查时唯一线索（§五.2 / §十二.2）
5. **`roi_rect` vs `last_roi_choice` 自相矛盾** — defaults 改成一致（§十一.5）
6. **声明了但不生效的配置项** — `scan.enable_diff_skip` / `matching.enabled` 要么实现要么删（§一.1）
7. **`DEFAULT_BANLIST_FILE` 硬编码桌面路径** — 改成 `config/banlist.example.txt` 或 `%USERPROFILE%/...`（§一.4）

### 短期修（30 分钟 - 2 小时、明显收益）
8. **`utils/logger.py` 接入 RotatingFileHandler** — defaults 里 4 个字段都写了但没实现，崩溃后日志全丢（§一.1 / §十二.3）
9. **`scan_once` 失败计数 + 自动停止** — 防止异常路径每 interval 秒刷一行 ERROR 直到天荒地老（§五.3）
10. **崩溃路径与正常停止区分状态** — 加 '异常停止' 状态色（§五.4）
11. **日志体系混乱** — 统一 `logging.getLogger(__name__)`，删 `screen_scan` 命名 logger 的 propagate 链（§一.3）
12. **`HotkeyDisplay` 铅笔按钮误导** — 删按钮，或者标 "TODO 未实现"（§九.4）
13. **CLI 尊重 `enable_roi`** — 判断挪到 cli/scan_worker，capture 不应承担兜底（§一.5）
14. **删 / 更新过时注释** — 全文搜索 `shared/overlay` / `T17` / `T23` / `tk_backup`（§九.1-9.3）
15. **死代码清理** — §二.3 列出的 10 处（matcher 死方法、`ScanWorker.set_roi`、`OCRStage.release` 等）
16. **`config.save` 节流（debounce 200ms）** — 拖 slider 期间反复 fsync 卡 UI（§三.1 / §七.4）
17. **`Config.get` 返回 None 的 falsy 误判** — 业务代码改 `is None` 显式比较，或长期改 dataclass 模型（§5.8 / §13.5）

### 中期项（重复劳动合并，2-4 小时）
18. **6 处 SVG 渲染抽公共 helper** — `ui/svg_utils.py::render_svg_icon`，能干掉 80+ 行（§二.1）
19. **两个 `_slider` helper 合并**（§二.2）
20. **`_make_group` 与 `SettingsCard` 合并**（§三.2）
21. **Overlay 方法改名 `update→refresh` / `destroy→cleanup`** — 避免覆盖 QWidget 保留名（§三.3 / §三.4）
22. **matcher / diff_gate / pipeline / config 补单元测试** — 4 个测试文件覆盖核心（§八.4）

### 长期项（架构层面、择期决策）
23. **`Config` 不可变快照 + 显式 update**（§13.1）— 解一类问题
24. **抽 `BackgroundScanner` 与 Qt 解耦**（§13.3）— UI/CLI/test 三方都受益
25. **统一配置变更通知机制**（§13.4）
26. **配置 schema 版本号 + migration**（§十一.2 / §13.5）
27. **PaddleOCR 周期性 reload 兜底** — 防长跑显存增长，需先量化 24h/7d 增量是否成问题（§六.1）
28. **多屏支持 Overlay 跟随 ROI 屏幕**（§十.1）
29. **加 metric 输出**（聚合日志 + 状态栏数字）（§十二.4）
30. **类型安全的配置访问**（TypedDict / dataclass / pydantic）（§13.5）

### 不修（已评估、收益过低）
- ~~`pillow` 列在 requirements 多余~~ — 是 paddleocr 间接依赖，删了没明显收益
- ~~`_get_memory_mb` 5s timer 在最小化后仍跑~~ — μs 级开销
- ~~`_sleep_with_check` 累加变量不精准~~ — 不外传，功能正确
- ~~`SubstringMatcher.reload_if_changed` 每次扫描调 mtime~~ — 几十 μs vs OCR 几百 ms

---

## 演化叙事（这份代码为什么长成这样）

理解审计结果时建议参考的演化背景：

1. **重构期残留**：注释里大量 `shared/overlay`、`tk_backup`、`T17/T23` 引用（§九）说明项目从 tkinter 迁到 PySide6 过程中，**重构期没回头清死链**。这是大多数 "过时注释 + 死代码 + 半完成 UI（铅笔按钮）" 的统一来源。
2. **yaml 当数据存储用**：§十一.1 yaml 注释会被擦说明作者**从一开始就把 yaml 当 pickle 替代品**，不期望用户手写。这影响了所有"用户配置可读性"相关的决策。
3. **GUI/CLI 平行实现**：`cli.py` 是早期实现，GUI 加进来后没有抽 `BackgroundScanner` 共享调度逻辑（§13.3），导致两边行为漂移（§一.5 是直接后果）。
4. **配置访问的"轻量哲学"**：dotted-key 字符串 + 全局单例是"快速能用"的选择（§13.1 / §13.5）。当前 ~30 个配置项还 hold 得住，但已经露出了 §四.1 线程不安全、§八.2 测试难写、§一.2 双单例 bug 三个症状——它们的共同根因是同一个架构选择。

