# Code Audit Fixes (Phase 1 + 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 解决 `docs/CODE_AUDIT_2026-05-13.md` 优先级总览中"立即修"（7 项）和"短期修"（10 项）的 17 个具体问题，覆盖：配置失效 bug、单例不同步 bug、日志体系修复、UX 误导项清理、死代码 / 过时注释清理。

**Architecture:** 不改动整体架构（pipeline / Config 单例 / QThread 模型保持不变）。所有改动是"精准修复 + 局部清理"——每条都对应审计文档中一处明确的文件:行号。中期 / 长期项（SVG helper 抽取、Stage 协议抽取、Config 不可变快照等）见末尾"后续 plan 占位"。

**Tech Stack:** Python 3.11 / PySide6 / PaddleOCR / pyahocorasick / mss / cv2 / pytest（plain assert 风格，无 fixture）。

**Verification 约定**：所有任务的"运行测试"步骤都用 `python tests/<test_file>.py`（项目当前测试风格是 `if __name__ == '__main__'` 直接跑，自带 sys.path 注入）。无需 pytest fixture。

**Changelog**：
- 2026-05-14 初版（覆盖审计 17 项立即修 + 短期修）。
- 2026-05-15 增量更新：纳入 2026-05-14 的代码变更（`build.spec` 已删、yaml 用户运行时值已偏移、`_minimize_for_scan` 新逻辑）—— Task 5 加注意事项，总验收新增 `_minimize_for_scan` 回归测试点，后续 plan 占位加 §十.9 跟进项。**任务编号、修法、Step 内容均未变**，可直接按编号执行。

---

## File Structure

修改 / 创建的文件清单：

**Modify**
- `tests/test_config_keys.py` — 修 expected ROI（Task 1）
- `pipeline/matcher.py` — 加载失败保留旧 keywords（Task 2）
- `pipeline/ocr_stage.py` — 删 `self._ocr` 实例字段（Task 3）
- `pipeline/capture.py` / `pipeline/diff_gate.py` / `pipeline/ocr_stage.py` / `pipeline/matcher.py` / `utils/hotkey.py` / `ui/scan_worker.py` / `ui/main_window.py` — `logging.error` → `logging.exception`（Task 4）
- `config/defaults.py` — `roi_rect` / `last_roi_choice` 一致化、删 `enable_diff_skip` / `matching.enabled`、`DEFAULT_BANLIST_FILE` 改路径（Task 5/6/7）
- `utils/logger.py` — 接 RotatingFileHandler，移除双 logger（Task 8/11）
- `ui/scan_worker.py` — 失败计数 + 异常停止状态（Task 9/10）
- `ui/widgets/status_bar.py` — 异常停止颜色（Task 10）
- `ui/widgets/settings_card.py` — 删 `HotkeyDisplay` 铅笔按钮（Task 12）
- `cli.py` — 判断 `enable_roi`（Task 13）
- 多个 `.py` — 注释清理（Task 14）+ 死代码清理（Task 15）
- `config/config.py` — `save_debounced` 节流（Task 16）
- 业务代码多处 — `config.get` falsy 检查改 `is None`（Task 17）

**Create**
- `tests/test_matcher_resilience.py` — 验证 Task 2 修复
- `tests/test_config_consistency.py` — 验证 Task 5 修复

---

## Phase 1：立即修（影响功能或诊断的 bug，先做）

### Task 1: 修复 `tests/test_config_keys.py` 与 defaults 不一致

**Files:**
- Modify: `tests/test_config_keys.py:16`

**Background:** 审计 §八.1。test 期望 `[1170, 256, 1880, 843]`，但 `config/defaults.py:25` 是 `[1136, 250, 1858, 850]`。`python tests/test_config_keys.py` 当前直接挂。

**Decision:** Task 5 会把 `roi_rect` 改成 `None`（与 `last_roi_choice='__reselect__'` 对齐），所以这里直接把 expected 改成 `None`，**并入 Task 5 一起做更高效**。但若 Task 5 决定保留具体坐标，这里就得改成当前 defaults 的值。

**为避免依赖**：本 task 先把 expected 改为与现 defaults 一致的 `[1136, 250, 1858, 850]`，让测试当前就能跑过；Task 5 改完 defaults 后会再次更新这个断言。

- [ ] **Step 1: 修改测试 expected**

```python
# tests/test_config_keys.py:16 改为
    assert scan['roi_rect'] == [1136, 250, 1858, 850]
```

- [ ] **Step 2: 运行测试验证通过**

Run: `python tests/test_config_keys.py`
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add tests/test_config_keys.py
git commit -m "test(config): 修复 test_config_keys 与 defaults 的 ROI 值不一致"
```

---

### Task 2: matcher 加载失败时保留旧 keywords

**Files:**
- Modify: `pipeline/matcher.py:89-125`
- Create: `tests/test_matcher_resilience.py`

**Background:** 审计 §五.6。`load()` 在 try 之前就 reset `self._keywords = {}` 和 `self._automaton = None`（matcher.py:94-95），任何 IO 异常（如记事本独占文件 PermissionError）会让关键词库静默清空。用户感知：扫一天发现"为啥从来不弹浮窗"。

**Fix strategy:** 先把读到的关键词收集到局部变量，全部成功后才赋值 `self._keywords` / `self._automaton`。

- [ ] **Step 1: 写失败测试**

Create `tests/test_matcher_resilience.py`:

```python
"""验证 matcher.load() 在 IO 失败时保留旧关键词。"""

import os
import sys
import tempfile
import unittest.mock as mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from pipeline.matcher import SubstringMatcher


def test_load_failure_preserves_old_keywords():
    """文件打开失败时，已加载的关键词不应被清空。"""
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.txt', encoding='utf-8') as f:
        f.write('hello 提示一\nworld 提示二\n')
        path = f.name
    try:
        m = SubstringMatcher(banlist_file=path)
        m.load()
        assert len(m.keywords) == 2, f'初次加载应有 2 条，实际 {len(m.keywords)}'

        # 模拟 open() 失败（如记事本独占 PermissionError）
        with mock.patch('builtins.open', side_effect=PermissionError('locked')):
            # 改 mtime 强制 reload_if_changed 触发
            os.utime(path, (1, 1))
            m.match([{'text': 'hello world'}])

        assert len(m.keywords) == 2, (
            f'load 失败后关键词被清空：{m.keywords}'
        )
    finally:
        os.unlink(path)


if __name__ == '__main__':
    test_load_failure_preserves_old_keywords()
    print('PASS')
```

- [ ] **Step 2: 跑测试验证失败**

Run: `python tests/test_matcher_resilience.py`
Expected: `AssertionError: load 失败后关键词被清空：[]`

- [ ] **Step 3: 修改 `pipeline/matcher.py` 的 `load()` 方法**

把现有 `load()`（matcher.py:89-134）改为：

```python
    def load(self, banlist_file=None):
        """加载关键词文件并构建自动机。失败时保留旧数据，不清空。"""
        if banlist_file is not None:
            self._banlist_file = banlist_file
        path = self._banlist_file

        if not path:
            self._log('warning', "未提供关键词文件路径")
            self._keywords = {}
            self._automaton = None
            self._file_mtime = None
            return

        path = os.path.abspath(path)
        self._banlist_file = path

        if not os.path.exists(path):
            self._log('warning', f"关键词文件不存在: {path}")
            self._keywords = {}
            self._automaton = None
            self._file_mtime = None
            return

        # 先收集到局部变量，全部成功后才替换实例字段
        new_keywords = {}
        try:
            new_mtime = os.path.getmtime(path)
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    keyword, hint = parse_keyword_line(line)
                    if not keyword:
                        continue
                    norm = _normalize(keyword)
                    if not norm:
                        continue
                    new_keywords[norm] = {
                        'original': keyword,
                        'hint': hint,
                    }
        except Exception as e:
            self._log('error', f"加载关键词文件失败，保留旧关键词 ({len(self._keywords)} 条): {e}")
            return

        new_automaton = None
        if new_keywords:
            new_automaton = ahocorasick.Automaton()
            for kw_norm, info in new_keywords.items():
                new_automaton.add_word(kw_norm, info)
            new_automaton.make_automaton()

        self._keywords = new_keywords
        self._automaton = new_automaton
        self._file_mtime = new_mtime
        self._log('info', f"已加载 {len(self._keywords)} 个关键词")
```

- [ ] **Step 4: 跑测试验证通过**

Run: `python tests/test_matcher_resilience.py`
Expected: `PASS`

- [ ] **Step 5: 跑原有测试确认无回归**

Run: `python tests/test_config_keys.py`
Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add pipeline/matcher.py tests/test_matcher_resilience.py
git commit -m "fix(matcher): 加载失败时保留旧 keywords，防止 banlist 被独占时匹配失效"
```

---

### Task 3: 删除 `OCRStage.self._ocr` 实例字段，直接走模块单例

**Files:**
- Modify: `pipeline/ocr_stage.py:45-69`

**Background:** 审计 §一.2。`recognize()` 只在 `self._ocr is None` 时刷新（ocr_stage.py:61-62），但模块级 `_ocr_instance` 在 `(lang, gpu)` 变化时已经重建。结果：用户改 GPU/语言后下次 scan 仍用旧 `self._ocr` 引用。

**Fix strategy:** 删 `self._ocr` 字段，每次 `recognize` 直接 `_get_ocr()`。`_get_ocr()` 自身在元组未变时是 O(1) 返回，无性能损失。

- [ ] **Step 1: 修改 `pipeline/ocr_stage.py`**

```python
class OCRStage:
    def __init__(self):
        pass  # 模型走模块级单例 _ocr_instance，无需实例字段

    def init(self):
        """预初始化 OCR 模型（让 5-15s 加载发生在 scan 循环之前）"""
        _get_ocr()

    def recognize(self, frame_bgr):
        """OCR 识别。每次取最新模型实例，配置变更自动生效。"""
        ocr = _get_ocr()

        # 可选图像反色
        if config.get('ocr.enable_image_invert'):
            frame_bgr = cv2.bitwise_not(frame_bgr)

        start = time.time()
        result = ocr.ocr(frame_bgr)
        duration = time.time() - start
        logger.debug(f"OCR 耗时: {duration:.3f}s")

        # 提取结果（下面提取逻辑保持不变）
        texts = []
        min_conf = config.get('ocr.min_confidence')

        if result and len(result) > 0:
            ocr_result = result[0]
            if isinstance(ocr_result, dict):
                rec_texts = ocr_result.get('rec_texts', [])
                rec_scores = ocr_result.get('rec_scores', [])
                rec_polys = ocr_result.get('rec_polys', [])
                for i, text in enumerate(rec_texts):
                    conf = float(rec_scores[i]) if i < len(rec_scores) else 1.0
                    if conf >= min_conf:
                        texts.append({
                            'text': text,
                            'confidence': conf,
                            'bbox': (
                                rec_polys[i].tolist()
                                if i < len(rec_polys) else None
                            )
                        })
            elif isinstance(ocr_result, list):
                for line in ocr_result:
                    if line and len(line) >= 2:
                        text = line[1][0]
                        conf = float(line[1][1])
                        if conf >= min_conf:
                            texts.append({
                                'text': text,
                                'confidence': conf,
                                'bbox': line[0]
                            })

        logger.info(f"OCR 识别 {len(texts)} 行, 耗时 {duration:.3f}s")
        return texts

    def release(self):
        global _ocr_instance, _ocr_init_config
        _ocr_instance = None
        _ocr_init_config = None
        import gc
        gc.collect()
```

注意：`release()` 里也删掉 `self._ocr = None` 那一行。

- [ ] **Step 2: 手工验证 GUI 切换 GPU 开关后下一次扫描使用新模型**

Run: `python app.py`
- 启动后开扫一次（看到日志 `初始化 PaddleOCR: lang=ch, device=gpu`）
- 设置页关 GPU、保存配置
- 点"停止" → "开始"
- 观察日志：应看到新行 `初始化 PaddleOCR: lang=ch, device=cpu`

Expected: 第二次启动扫描日志里 device 切换正确。

- [ ] **Step 3: Commit**

```bash
git add pipeline/ocr_stage.py
git commit -m "fix(ocr): 删除 OCRStage.self._ocr 实例字段，避免配置切换后模型不同步"
```

---

### Task 4: `logging.error(f'...{e}')` → `logging.exception(...)` 全工程替换

**Files:**
- Modify: `pipeline/matcher.py:124` (1 处，注意是 `self._log('error', ...)` 形式，需配合 matcher 内 _log 调整)
- Modify: `utils/hotkey.py:21` (1 处 `logger.error`)
- Modify: `ui/scan_worker.py:66, 91` (2 处 `logging.error`)
- Modify: 其它 grep 出来的 `logging.error` / `logger.error`

**Background:** 审计 §五.2 / §十二.2。全工程 18 处 error 日志只有字符串，没有 traceback。改为 `logging.exception` 是 1 行 1 处的成本，故障排查时唯一线索。

- [ ] **Step 1: grep 出所有需要改的位置**

Run: `python -c "import subprocess; subprocess.run(['grep', '-rn', '--include=*.py', '-E', 'logger\\.error\\(|logging\\.error\\(', 'config', 'pipeline', 'utils', 'ui', 'cli.py', 'app.py'])"`

或用 Grep 工具（推荐）。预期至少看到这些位置（具体行号以现在文件为准）：
- `pipeline/matcher.py:124` (在 except 内)
- `utils/hotkey.py:21` (在 except 内)
- `ui/scan_worker.py:66` (在 except 内)
- `ui/scan_worker.py:91` (在 except 内)
- 其它 `logger.error` 不在 except 内的不改（exception 必须在 except 内调用）

- [ ] **Step 2: 修改 `ui/scan_worker.py`**

```python
# scan_worker.py:66
        except Exception as e:
            logging.exception('扫描线程异常')   # 原：logging.error(f'扫描线程异常: {e}')
            self.status_changed.emit('已停止')

# scan_worker.py:91
            except Exception as e:
                logging.exception('scan_once 失败')   # 原：logging.error(f'scan_once 失败: {e}')
                self._sleep_with_check(interval)
                continue
```

- [ ] **Step 3: 修改 `utils/hotkey.py`**

```python
# hotkey.py:21
        except Exception as e:
            logger.exception(f"注册热键失败 {hotkey}")   # 原：logger.error(f"注册热键失败 {hotkey}: {e}")
```

- [ ] **Step 4: 修改 `pipeline/matcher.py` 的 `_log` 调用**

matcher 用 `self._log('error', msg)` 包装，需要在 `_log` 内分流到 `logger.exception`：

```python
# matcher.py:124 调用处保持
        except Exception as e:
            self._log('exception', f"加载关键词文件失败，保留旧关键词 ({len(self._keywords)} 条)")
            return

# matcher.py:189-192 _log 方法支持 exception
    def _log(self, level, msg):
        if self._logger is None:
            return
        method = getattr(self._logger, level, None)
        if method is not None:
            method(msg)
```

注意：`_log('exception', ...)` 只能在 `except` 块内调用（否则 stack 是 None）。matcher.py:124 正好在 except 里 ✅。

- [ ] **Step 5: 手工验证日志带 traceback**

Run: 临时把 `pipeline/ocr_stage.py` 的 `_get_ocr` 改成 `raise RuntimeError("test")`，跑 `python app.py`，开扫，看日志面板。

Expected: 日志里能看到 `Traceback (most recent call last):` 几行，而不是单行 `scan_once 失败: test`。

测试完恢复 `ocr_stage.py`。

- [ ] **Step 6: Commit**

```bash
git add pipeline/matcher.py utils/hotkey.py ui/scan_worker.py
git commit -m "fix(logging): error 改为 exception，故障日志带 traceback"
```

---

### Task 5: `roi_rect` 与 `last_roi_choice` 默认值一致化

**Files:**
- Modify: `config/defaults.py:25, 32`
- Modify: `tests/test_config_keys.py:16` (Task 1 已改过，这里再改)
- Create: `tests/test_config_consistency.py`

**Background:** 审计 §十一.5。defaults 同时给了 `roi_rect: [1136,250,1858,850]` 和 `last_roi_choice: '__reselect__'`。按 `_resolve_roi` 逻辑首启走 picker，`roi_rect` 默认值永远走不到。两份意图打架，新用户首启行为不可预期。

**注意 (2026-05-14 更新)**：用户的运行时 `config/config.yaml` 已经把 `last_roi_choice` 改成 `'__custom__'`、`roi_rect` 改成 `[1136,224,1893,850]`——这是 yaml 而非 defaults 的偏移，**Task 5 改 defaults 的修法不变**，但执行 Step 6 烟测时，注意当前用户 yaml 不走 picker 分支（走 custom 分支），需要先临时把 yaml 的 `last_roi_choice` 改成 `'__reselect__'` 或备份 yaml 改用空文件，才能验证 picker 分支。

**Decision:** `roi_rect` 默认 `None`，`last_roi_choice` 保持 `'__reselect__'`，意图统一为"首启弹 picker"。

- [ ] **Step 1: 写一致性测试**

Create `tests/test_config_consistency.py`:

```python
"""验证 defaults 内部一致：roi_rect None ↔ last_roi_choice '__reselect__'。"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config.defaults import DEFAULT_CONFIG


def test_roi_rect_and_choice_consistent():
    scan = DEFAULT_CONFIG['scan']
    rect = scan['roi_rect']
    choice = scan['last_roi_choice']
    if rect is None:
        assert choice == '__reselect__', (
            f"roi_rect=None 时 last_roi_choice 应为 '__reselect__'，实际 {choice}"
        )
    else:
        assert choice != '__reselect__', (
            f"roi_rect 有具体值时 last_roi_choice 不应为 '__reselect__'"
        )


if __name__ == '__main__':
    test_roi_rect_and_choice_consistent()
    print('PASS')
```

- [ ] **Step 2: 跑测试验证失败**

Run: `python tests/test_config_consistency.py`
Expected: `AssertionError: roi_rect=None 时 ...`（实际上当前是 rect 有值 + choice='__reselect__'，应触发"有具体值时 ..." 那条）

- [ ] **Step 3: 修改 `config/defaults.py`**

```python
# defaults.py:22-25
        # 当前生效的 ROI 坐标 [x1, y1, x2, y2]，屏幕绝对像素；None = 未保存，首启弹 picker。
        # 与 last_roi_choice='__reselect__' 配合：两者必须保持一致意图。
        'roi_rect': None,
```

- [ ] **Step 4: 跑一致性测试验证通过**

Run: `python tests/test_config_consistency.py`
Expected: `PASS`

- [ ] **Step 5: 同步更新 `tests/test_config_keys.py`**

```python
# tests/test_config_keys.py:16
    assert scan['roi_rect'] is None
```

- [ ] **Step 6: 验证 ROI 解析路径不会因 None 崩**

Run: 浏览 `ui/main_window.py:_resolve_roi`，确认 `roi_rect=None` 时走 picker 分支（应已经如此，因为 `last_roi_choice='__reselect__'` 是同样意图）。

也跑 `python tests/test_config_keys.py` 确认不挂。

- [ ] **Step 7: Commit**

```bash
git add config/defaults.py tests/test_config_keys.py tests/test_config_consistency.py
git commit -m "fix(config): roi_rect 默认 None，与 last_roi_choice 意图一致"
```

---

### Task 6: 清理声明了但不生效的配置项

**Files:**
- Modify: `config/defaults.py`

**Background:** 审计 §一.1。`scan.enable_diff_skip` 在 `diff_gate.py` 无引用、`matching.enabled` 全工程 0 调用方。要么实现要么删，**选择删**（实现成本高于价值，且当前 pipeline 行为符合用户预期）。

- [ ] **Step 1: 确认 `enable_diff_skip` 全工程无引用**

Run: 用 Grep 工具搜 `enable_diff_skip`
Expected: 仅 `config/defaults.py:20` 一处出现

- [ ] **Step 2: 确认 `matching.enabled` 全工程无引用**

Run: 用 Grep 工具搜 `matching\.enabled|'enabled'.*matching|matching.*'enabled'`
Expected: 仅 defaults.py 一处

- [ ] **Step 3: 从 defaults.py 删除两项**

```python
# defaults.py:20 删除整行
'enable_diff_skip': True,         # 帧差检测：与上次画面相似时跳过 OCR

# defaults.py:46 删除整行
'enabled': True,                    # 是否启用关键词匹配（False 时只 OCR 不弹浮窗）
```

注意：`'matching'` 字段块本身保留（display_duration 等还在用）。

- [ ] **Step 4: 跑全部已有测试**

Run: 顺序跑
```
python tests/test_config_keys.py
python tests/test_config_consistency.py
python tests/test_matcher_resilience.py
```
Expected: 全 PASS

- [ ] **Step 5: 启动 GUI 烟测**

Run: `python app.py`，点几下"开始/停止"，确认无 KeyError / 异常。

- [ ] **Step 6: Commit**

```bash
git add config/defaults.py
git commit -m "chore(config): 删除未实现的 scan.enable_diff_skip 和 matching.enabled"
```

---

### Task 7: `DEFAULT_BANLIST_FILE` 改用项目内示例路径

**Files:**
- Modify: `config/defaults.py:11`
- Create: `config/banlist.example.txt`

**Background:** 审计 §一.4。defaults 写死 `C:/Users/Administrator/Desktop/banlist.txt`，新机器/新用户一定不存在。

**Fix strategy:** 改成项目内 `config/banlist.example.txt`，并提交一个示例文件让首启就能用。

- [ ] **Step 1: 创建示例 banlist**

Create `config/banlist.example.txt`:

```
# 关键词文件示例。一行一条，支持两种格式：
#   关键词 提示词       （空白分隔，推荐）
#   关键词:提示词       （冒号分隔，旧格式兼容）
# 以 # 开头的行被忽略（其实 matcher 会按"无关键词"自动跳过）

错误 系统错误提示
警告 风险信号
异常 异常状态告警
```

- [ ] **Step 2: 修改 defaults.py**

```python
# defaults.py:11
DEFAULT_BANLIST_FILE = 'config/banlist.example.txt'
```

- [ ] **Step 3: 验证 matcher 读取相对路径正常**

`pipeline/matcher.py:102` 已经做了 `os.path.abspath(path)`——相对路径会拼到 CWD。CWD 在 `python app.py` / `python cli.py` 时是项目根（入口文件做了 `sys.path.insert(0, os.path.dirname(__file__))`，但 CWD 依赖启动方式）。

Run: `python cli.py`（在项目根）
Expected: 启动日志含 `已加载 3 个关键词`

如果 CWD 不是项目根，matcher 会找不到文件 → 改用绝对路径，把 defaults 改成：

```python
import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BANLIST_FILE = os.path.join(_PROJECT_ROOT, 'config', 'banlist.example.txt')
```

- [ ] **Step 4: 跑已有测试**

Run: `python tests/test_config_keys.py && python tests/test_config_consistency.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config/defaults.py config/banlist.example.txt
git commit -m "fix(config): banlist 默认路径改为项目内示例文件，首启即可用"
```

---

## Phase 2：短期修（明显收益，可逐项做）

### Task 8: 接入 RotatingFileHandler

**Files:**
- Modify: `utils/logger.py`

**Background:** 审计 §一.1 + §十二.3。defaults 里 `logging.file / max_bytes / backup_count` 都声明了但从未生效，崩溃后日志全丢。

- [ ] **Step 1: 改写 `utils/logger.py`**

```python
import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name='screen_scan', level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        formatter.default_msec_format = '%s.%03d'
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = True
    return logger


logger = setup_logger()


def configure_from_config(cfg):
    """根据配置调整 root + screen_scan logger 的级别 + file handler。"""
    level_str = cfg.get('logging.level', 'INFO')
    level = getattr(logging, level_str.upper(), logging.INFO)

    # 1. 设置 logger 级别（root 也要设，否则 LogBridge 接到的消息可能被 root 过滤）
    logging.getLogger().setLevel(level)
    logger.setLevel(level)
    for h in logger.handlers:
        h.setLevel(level)

    # 2. 装 RotatingFileHandler 到 root（让所有模块的日志都进文件）
    file_path = cfg.get('logging.file', 'logs/app.log')
    max_bytes = int(cfg.get('logging.max_bytes', 10 * 1024 * 1024))
    backup_count = int(cfg.get('logging.backup_count', 5))
    fmt = cfg.get(
        'logging.format',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 避免重复装
    root = logging.getLogger()
    has_file = any(isinstance(h, RotatingFileHandler) for h in root.handlers)
    if not has_file:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)) or '.', exist_ok=True)
        fh = RotatingFileHandler(
            file_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
        )
        formatter = logging.Formatter(fmt)
        formatter.default_msec_format = '%s.%03d'
        fh.setFormatter(formatter)
        fh.setLevel(level)
        root.addHandler(fh)
```

- [ ] **Step 2: 确保 GUI 入口也调 `configure_from_config`**

Read `app.py` 检查是否调了 `configure_from_config`。若没调，加上：

```python
# app.py 在 config.load() 之后
from utils.logger import configure_from_config
config.load()
configure_from_config(config)
```

- [ ] **Step 3: 烟测：启动后产生日志写文件**

Run: `python app.py` → 开扫几秒 → 关掉。
Expected: `logs/app.log` 存在且有内容。

- [ ] **Step 4: 烟测：超过 max_bytes 触发旋转**

把 `config/config.yaml` 里 `logging.max_bytes` 临时改成 `1024`，开扫几秒。
Expected: 出现 `logs/app.log.1` / `.2` 等旋转文件。

测完恢复 `max_bytes` 为 `10485760`。

- [ ] **Step 5: Commit**

```bash
git add utils/logger.py app.py
git commit -m "feat(logging): 接入 RotatingFileHandler，崩溃后保留日志"
```

---

### Task 9: `scan_once` 失败计数 + 自动停止

**Files:**
- Modify: `ui/scan_worker.py`

**Background:** 审计 §五.3。`scan_once` 永久失败（如 paddle DLL 缺失）时，循环每 `interval` 秒打一行 ERROR 直到用户停。

**Fix strategy:** 连续 N 次失败后状态切"异常停止" + 触发 stop。

- [ ] **Step 1: 修改 `_do_loop`，加失败计数**

```python
    def _do_loop(self):
        self.status_changed.emit('运行中')
        consecutive_failures = 0
        FAILURE_THRESHOLD = 5

        while not self._stop:
            interval = float(config.get('scan.interval_seconds') or 5.0)
            t0 = time.time()
            try:
                result = self.pipeline.scan_once()
                consecutive_failures = 0
            except Exception:
                logging.exception('scan_once 失败')
                consecutive_failures += 1
                if consecutive_failures >= FAILURE_THRESHOLD:
                    logging.error(
                        f'scan_once 连续失败 {FAILURE_THRESHOLD} 次，自动停止扫描'
                    )
                    self.status_changed.emit('异常停止')
                    return
                self._sleep_with_check(interval)
                continue

            # 日志：跳过 / 识别行数 / 匹配数 / 耗时
            if result.skipped:
                logging.info(f'帧差跳过（OCR 复用上次结果），耗时 {result.duration*1000:.0f} ms')
            else:
                logging.info(
                    f'OCR {len(result.ocr_results)} 行，'
                    f'命中 {len(result.matches)} 条，'
                    f'耗时 {result.duration*1000:.0f} ms'
                )
            for m in result.matches:
                logging.warning(f'>>> {m.get("keyword","")} → {m.get("hint","")}')

            self.result_ready.emit(result.ocr_results, result.matches)

            elapsed = time.time() - t0
            self._sleep_with_check(max(0.0, interval - elapsed))

        self.status_changed.emit('已停止')
        logging.info('扫描已停止')
```

- [ ] **Step 2: 烟测异常路径**

临时把 `pipeline/diff_gate.py:21` 的 `threshold = config.get('scan.diff_threshold')` 改为 `raise RuntimeError("test")`。

Run: `python app.py` → 开扫，把 interval 设短（如 1s）。
Expected: 日志 5 次 traceback 后状态变"异常停止"，循环退出。

测完恢复 `diff_gate.py`。

- [ ] **Step 3: Commit**

```bash
git add ui/scan_worker.py
git commit -m "feat(scan): scan_once 连续失败 5 次后自动停止扫描"
```

---

### Task 10: 异常停止与正常停止状态色区分

**Files:**
- Modify: `ui/widgets/status_bar.py`

**Background:** 审计 §五.4。当前 `'已停止'` 是用户停止 + 崩溃共享的状态字符串，但语义不同。Task 9 已 emit `'异常停止'`，本任务在 StatusBar 给它一个区分色。

- [ ] **Step 1: 找到状态色映射**

Read `ui/widgets/status_bar.py`，找 `_STATUS_COLOR` 或类似字典。预期 `'已停止'` 是红色 / 灰色。

- [ ] **Step 2: 加 `'异常停止'` 条目**

在 `_STATUS_COLOR` 字典加：

```python
_STATUS_COLOR = {
    '运行中': '#…',
    '初始化中': '#…',
    '已停止': '#…',        # 用户主动停止 — 灰
    '异常停止': '#d32f2f',  # 崩溃停止 — 强烈红
}
```

颜色值以现有"已停止"为基准对调，确保两者视觉可区分。

- [ ] **Step 3: 烟测**

复用 Task 9 的烟测路径，观察状态栏：连续失败到阈值后状态条变更显眼的红色。

- [ ] **Step 4: Commit**

```bash
git add ui/widgets/status_bar.py
git commit -m "feat(ui): 异常停止状态加独立颜色，与用户停止区分"
```

---

### Task 11: 统一 logging 调用方式（删 `screen_scan` 命名 logger 的冗余链）

**Files:**
- Modify: `utils/logger.py`
- Modify: 业务模块（`pipeline/*.py` / `utils/hotkey.py`）— 从 `from utils.logger import logger` 改为 `import logging; logger = logging.getLogger(__name__)`

**Background:** 审计 §一.3。当前混用 `screen_scan` 命名 logger（通过 propagate 上抛到 root）+ `logging.*` 直接调 root。LogBridge 在 root 上挂 formatter，screen_scan 也挂自己的 → 同一条消息走两遍 formatter。

**Fix strategy:** 删 `screen_scan` 命名 logger 的 StreamHandler / formatter；所有业务代码用 `logging.getLogger(__name__)`，root 由 `utils/logger.py` 统一装 console + file handler。

- [ ] **Step 1: 改写 `utils/logger.py`**

```python
import logging
import os
from logging.handlers import RotatingFileHandler


# 不再创建命名 logger；setup 直接装 root。
_setup_done = False


def setup_logger(level=logging.INFO):
    """装 root 的 StreamHandler。多次调用幂等。"""
    global _setup_done
    root = logging.getLogger()
    if _setup_done:
        return
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    formatter.default_msec_format = '%s.%03d'
    handler.setFormatter(formatter)
    handler.setLevel(level)
    root.addHandler(handler)
    root.setLevel(level)
    _setup_done = True


setup_logger()

# 向后兼容：保留模块级 logger 别名（部分业务文件 import 它）
logger = logging.getLogger('screen_scan')


def configure_from_config(cfg):
    """根据配置调整 root 级别 + 装 RotatingFileHandler。"""
    level_str = cfg.get('logging.level', 'INFO')
    level = getattr(logging, level_str.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    for h in root.handlers:
        h.setLevel(level)

    file_path = cfg.get('logging.file', 'logs/app.log')
    max_bytes = int(cfg.get('logging.max_bytes', 10 * 1024 * 1024))
    backup_count = int(cfg.get('logging.backup_count', 5))
    fmt = cfg.get(
        'logging.format',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    has_file = any(isinstance(h, RotatingFileHandler) for h in root.handlers)
    if not has_file:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)) or '.', exist_ok=True)
        fh = RotatingFileHandler(
            file_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
        )
        formatter = logging.Formatter(fmt)
        formatter.default_msec_format = '%s.%03d'
        fh.setFormatter(formatter)
        fh.setLevel(level)
        root.addHandler(fh)
```

注意：保留 `logger = logging.getLogger('screen_scan')` 是为了让现有 `from utils.logger import logger` 不挂；它会 propagate 到 root，root 上有 handler，效果等价。

- [ ] **Step 2: 渐进替换业务代码（可选）**

把 `pipeline/*.py` / `utils/hotkey.py` 内的 `from .logger import logger` 改为：

```python
import logging
logger = logging.getLogger(__name__)
```

可一次一个文件做并测试。

注意：本步骤是 cleanup，不改时 Step 1 已经修了"双 formatter"问题。要严格按 audit 修，建议至少把 `pipeline/matcher.py:logger=` 和 `pipeline/ocr_stage.py:logger=` 改掉。

- [ ] **Step 3: 烟测：日志在 LogPanel 和 logs/app.log 中只出现一次**

Run: `python app.py` → 开扫 → 看日志面板内一条 INFO 不重复。同时检查 `logs/app.log` 内同一条也只一行。

- [ ] **Step 4: Commit**

```bash
git add utils/logger.py pipeline/matcher.py pipeline/ocr_stage.py
git commit -m "refactor(logging): 统一走 root logger，消除双 formatter 重复"
```

---

### Task 12: 删 `HotkeyDisplay` 的铅笔编辑按钮

**Files:**
- Modify: `ui/widgets/settings_card.py:160-167`

**Background:** 审计 §九.4。铅笔按钮渲染了 `edit_clicked` signal 但无人 connect，用户点了没反应。

**Decision:** 删按钮（而不是补功能），因为热键编辑不在本轮范围内。

- [ ] **Step 1: 删按钮代码**

Read `ui/widgets/settings_card.py` 找到 `HotkeyDisplay` 类，删掉创建铅笔按钮 + `edit_clicked` Signal 的代码。具体删除：
- `edit_clicked = Signal()` 那一行
- 创建 `QToolButton(铅笔图标)` 的 6-8 行代码
- 把按钮加入布局的那一行

确保 `HotkeyDisplay` 仍正常显示热键文本。

- [ ] **Step 2: 检查无其它地方引用**

Run: Grep `edit_clicked` / `HotkeyDisplay`
Expected: `edit_clicked` 全工程 0 引用（删之前就是死信号）

- [ ] **Step 3: 烟测**

Run: `python app.py` → 进设置页 → 看热键卡片
Expected: 没有铅笔按钮，热键以纯文本显示

- [ ] **Step 4: Commit**

```bash
git add ui/widgets/settings_card.py
git commit -m "chore(ui): 删 HotkeyDisplay 铅笔按钮，避免用户点击无响应"
```

---

### Task 13: CLI 尊重 `enable_roi`

**Files:**
- Modify: `cli.py:20-23`

**Background:** 审计 §一.5。`cli.py` 只看 `roi_rect` 真值，不看 `enable_roi`。当前靠 `capture.py:35` 防御性二次校验救场，职责错位。

- [ ] **Step 1: 修改 cli.py**

```python
# cli.py:20-23 改为
    # ROI 设置：尊重 enable_roi 开关
    if config.get('scan.enable_roi'):
        roi = config.get('scan.roi_rect')
        if roi:
            pipeline.set_roi(tuple(roi))
        else:
            print("scan.enable_roi=True 但 roi_rect 未设置，按全屏扫描")
```

注意：变量名同时从 `roi_str` 改成 `roi`（审计 §二.6 命名错误顺手修了）。

- [ ] **Step 2: 烟测**

把 `config/config.yaml` 中 `scan.enable_roi` 改成 `false`，跑 `python cli.py`。
Expected: 启动后扫的是全屏，无 ROI 边界。

测完恢复配置。

- [ ] **Step 3: Commit**

```bash
git add cli.py
git commit -m "fix(cli): 尊重 scan.enable_roi 开关，与 GUI 行为对齐"
```

---

### Task 14: 删除引用已删文件的过时注释

**Files:**
- Modify: `ui/sound.py:3-4`
- Modify: `ui/overlay.py:77, 119`
- Modify: `ui/widgets/status_bar.py:46`
- Modify: `ui/pages/settings_page.py:175, 203`
- Modify: `ui/widgets/settings_card.py:147`

**Background:** 审计 §九.1-9.3。引用了 `shared/overlay`、`tk_backup`、`T17/T23` 等已不存在的实体。

- [ ] **Step 1: 用 Grep 锁定全部过时注释**

Run: Grep 用以下模式
- `shared/overlay`
- `tk_backup`
- `T17|T23` （正则）

预期会命中上述文件的 6-8 处。

- [ ] **Step 2: 逐个删/改**

对每处：
- 注释整段都是过时背景 → 删整段
- 注释中只有一两句过时 → 只删那一两句，保留有用的部分

具体改法（按审计 §九.1-9.3）：
- `ui/sound.py:3-4` "被 ui/overlay.py 和 shared/overlay.py 共用" → 改为"由 ui/overlay.py 使用"
- `ui/overlay.py:77` `# ============ 公开 API（与 shared/overlay.py 对齐）============` → 改 `# ============ 公开 API ============`
- `ui/overlay.py:119` `（搬自 shared/overlay.py 视觉规则）` → 删括号内字
- `ui/widgets/status_bar.py:46` `"""搬自 app.py.tk_backup:_get_memory_mb..."""` → 删整个 docstring 或改为简述
- `ui/pages/settings_page.py:175` `# T23 接入 HotkeyManager 后...` → 改为"当前为只读显示"
- `ui/pages/settings_page.py:203` `# T17 才真正接入；当前是空槽` → 检查实际是否还是空槽，若已接入则删整段
- `ui/widgets/settings_card.py:147` `（具体编辑流由 T23 HotkeyManager 接入）` → 删括号内字

- [ ] **Step 3: 烟测**

Run: `python app.py`，确认 UI 行为无任何变化。

- [ ] **Step 4: Commit**

```bash
git add ui/sound.py ui/overlay.py ui/widgets/status_bar.py ui/pages/settings_page.py ui/widgets/settings_card.py
git commit -m "chore(docs): 清理引用已删文件的过时注释"
```

---

### Task 15: 删除审计 §二.3 列出的 10 处死代码

**Files:**
- Modify: `pipeline/matcher.py:50, 78, 82, 85, 199` (5 处)
- Modify: `ui/scan_worker.py:40` (1 处)
- Modify: `ui/widgets/config_panel.py:420` (1 处)
- Modify: `ui/widgets/settings_card.py:169` (1 处)
- Modify: `ui/widgets/sidebar.py:159` (1 处)
- Modify: `pipeline/ocr_stage.py:111` (1 处)

**Background:** 审计 §二.3。每条都 grep 验证过 0 引用。

**Decision:** 全部删除（不保留"未来可能用"，YAGNI）。

- [ ] **Step 1: 删 `pipeline/matcher.py` 的 5 处**

删除：
- `keyword_in_text()` 函数（matcher.py:50-57）
- `SubstringMatcher.banlist_file` property（matcher.py:77-79）
- `SubstringMatcher.keywords` property（matcher.py:81-83）
- `SubstringMatcher.get_hint()` 方法（matcher.py:85-87）
- `get_cached_matcher()` + `_cache` + `_cache_lock`（matcher.py:195-209）

注意：Task 2 创建的 `tests/test_matcher_resilience.py` 用了 `m.keywords` property —— **保留**这个 property 给测试用，从删除清单移除。

- [ ] **Step 2: 删 `ui/scan_worker.py:40-44` 的 `set_roi`**

```python
# 整个 set_roi 方法删除
    def set_roi(self, roi):
        """run 之前或运行中都可以调；运行中改 ROI 立即生效。"""
        ...
```

注意：若 `MainWindow` 调过 `worker.set_roi`（搜确认），那这条算误判，保留。

Run: Grep `worker\.set_roi|\.set_roi\(` 在 `ui/` 内
Expected: 仅 `pipeline.set_roi` 调用，无 `worker.set_roi`

- [ ] **Step 3: 删其它 4 处死方法**

- `ui/widgets/config_panel.py:420` `reload_from_config()` 方法
- `ui/widgets/settings_card.py:169` `HotkeyDisplay.set_hotkey()` 方法
- `ui/widgets/sidebar.py:159` `Sidebar.setCurrentRow()` 方法
- `pipeline/ocr_stage.py:111` `OCRStage.release()` 方法

每处删之前用 Grep 再验证一遍 0 引用。

- [ ] **Step 4: 顺手清理 §二.4 / §二.5 的僵尸守卫**

- `pipeline/matcher.py:189-192` `_log` 已在 Task 4 调整过；删 `lambda *_: None` 的兜底（已是 method is None 短路）
- `ui/overlay.py:264-265` `except TypeError` 守卫 → 删 try/except，直接 `v = self._config.get(key, default)`

- [ ] **Step 5: 跑全部测试**

Run:
```
python tests/test_config_keys.py
python tests/test_config_consistency.py
python tests/test_matcher_resilience.py
```
Expected: 全 PASS

- [ ] **Step 6: 烟测 GUI**

Run: `python app.py` → 完整跑一遍开扫/停扫/设置页/关闭流程，无异常。

- [ ] **Step 7: Commit**

```bash
git add pipeline/matcher.py pipeline/ocr_stage.py ui/scan_worker.py ui/widgets/config_panel.py ui/widgets/settings_card.py ui/widgets/sidebar.py ui/overlay.py
git commit -m "chore: 删除审计 §二.3 列出的死代码和僵尸守卫"
```

---

### Task 16: `Config.save` debounce 节流

**Files:**
- Modify: `config/config.py`
- Modify: GUI 控件的 valueChanged 回调（`ui/widgets/config_panel.py` / `ui/pages/settings_page.py`）

**Background:** 审计 §三.1。slider 拖动期间每次 valueChanged 触发 `config.set + config.save`，一次拖动几十次 fsync，UI 卡顿。

**Fix strategy:** Config 加 `save_debounced(delay_ms=200)`，用 `QTimer.singleShot` 或 `threading.Timer` 节流。GUI 回调统一改用 `save_debounced`。

- [ ] **Step 1: 在 `config/config.py` 加 `save_debounced`**

```python
# config.py 末尾或 Config 类内
import threading

class Config:
    # ... 现有代码 ...

    def save_debounced(self, delay_ms=200):
        """节流保存。在 delay_ms 内多次调用只产生一次磁盘写。"""
        if not hasattr(self, '_save_timer_lock'):
            self._save_timer_lock = threading.Lock()
            self._save_timer = None

        with self._save_timer_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(delay_ms / 1000.0, self.save)
            self._save_timer.daemon = True
            self._save_timer.start()
```

注意：`threading.Timer` 的回调在独立线程跑，`save()` 内做 yaml.dump 写盘——若 worker 线程也在并发读 `_data`，应在 `save()` 内加 lock（暂不做，按审计 §四.1 长期项处理）。当前事实上只有主线程写。

- [ ] **Step 2: 修改 GUI 控件回调**

把 `ui/widgets/config_panel.py` 和 `ui/pages/settings_page.py` 内所有 `lambda v: (config.set(...), config.save())` 改为：

```python
lambda v: (config.set('xxx', v), config.save_debounced())
```

用 Grep 搜 `config\.save\(\)` 在 ui/ 内逐个改。

- [ ] **Step 3: 烟测**

Run: `python app.py` → 设置页拖 slider 几秒。
Expected: 拖动流畅无卡顿。停手 200ms 后 yaml mtime 更新（Get-Item config/config.yaml 看 LastWriteTime）。

- [ ] **Step 4: Commit**

```bash
git add config/config.py ui/widgets/config_panel.py ui/pages/settings_page.py
git commit -m "perf(config): save 节流 debounce 200ms，缓解 slider 拖动卡顿"
```

---

### Task 17: `config.get` 的 falsy 误判收口

**Files:**
- 业务代码多处（grep 出来再决定）

**Background:** 审计 §5.8。`config.get('xxx')` 不传 default 时返回 None，业务代码 `if not v:` 在 0 / 0.0 / False / '' 四种值上也会触发，潜在 bug。

**Fix strategy:** 短期：把"应该接受 0/False 作为合法值"的 falsy 检查改为 `is None`。长期方案见 §13.5。

- [ ] **Step 1: grep 找潜在误判点**

Run: Grep 用 `if not config\.get\(`
Expected: 命中若干处。逐一判断每处的 key 是否可能合法地取到 falsy 值（0 / False / 空字符串）。

例如：
- `if not config.get('matching.font_size'):` ← 0 是非法值，falsy 检查 OK
- `if not config.get('scan.diff_threshold'):` ← 0.0 可能是用户想关帧差检测的值，falsy 检查会错杀，应改 `is None`
- `if not config.get('scan.enable_roi'):` ← False 是合法关闭值，falsy 检查刚好等价，OK

- [ ] **Step 2: 改高风险点**

对每处判断为"falsy 合法"的点：

```python
# 改前
if not config.get('xxx'):

# 改后
v = config.get('xxx')
if v is None:
    # 真的没配置；处理 fallback
```

- [ ] **Step 3: 烟测**

Run: `python app.py`，对涉及阈值的配置项设为 0（如 `scan.diff_threshold: 0.0`）观察是否正确生效（即不会被当成"未配置"绕开）。

- [ ] **Step 4: Commit**

```bash
git add <touched files>
git commit -m "fix(config): 阈值类配置的 falsy 检查改为 is None，避免 0/False 被误判"
```

---

## 完成后总验收

- [ ] 跑全部测试：
```
python tests/test_config_keys.py
python tests/test_config_consistency.py
python tests/test_matcher_resilience.py
```
Expected: 全 PASS

- [ ] GUI 烟测：
- 启动 → 弹 ROI picker（因 Task 5 改了默认）→ 框选 → 开扫
- 设置页改 GPU 开关、改 OCR 语言 → 停扫 → 开扫 → 日志显示新模型加载
- 拖 slider → UI 流畅
- 改 banlist 路径到不存在文件 → 看 LogPanel 是否有警告（不静默清空）
- 关主窗口到托盘 → 再打开 → 状态保留
- **新增（2026-05-14 _minimize_for_scan 回归测试）**：
  - `app.minimize_to_tray=True` 状态下点"开始" → 主窗口应进托盘 → 扫描正常
  - `app.minimize_to_tray=False` 状态下点"开始" → 主窗口应最小化到任务栏 → 扫描正常
  - 进 picker 阶段先取消 → 主窗口应正常恢复（不应留在最小化/托盘隐藏状态）

- [ ] CLI 烟测：
- `python cli.py`，设 `scan.enable_roi=false` → 全屏扫描
- 设 `enable_roi=true` + `roi_rect=null` → 提示需要先在 GUI 框选

- [ ] 日志文件存在：`logs/app.log` 有内容且能滚动

- [ ] 没引入新警告：观察 GUI 日志面板和控制台启动期 0 ERROR / WARN

---

## 后续 plan 占位（中期 / 长期项，本计划不含）

**中期项**（重复劳动合并，2-4 小时；下一份 plan）：
- 6 处 SVG 渲染抽 `ui/svg_utils.py::render_svg_icon`（§二.1）
- 两个 `_slider` helper 合并（§二.2）
- `_make_group` 与 `SettingsCard` 合并（§三.2）
- Overlay 方法改名 `update→refresh` / `destroy→cleanup`（§三.3 / §三.4）
- 补单元测试 `tests/test_matcher.py` / `test_diff_gate.py` / `test_pipeline_skip_reuse.py` / `test_config_deep_merge.py`（§八.4）
- **新增（来自审计 §十.9）**：`_minimize_for_scan` 边界优化 —— picker 取消时用 `windowState()` 还原而非 `showNormal`（避免丢失 maximized 状态）；托盘图标加状态 tooltip。

**长期项**（架构层面，每条独立 plan）：
- `Config` 不可变快照 + 显式 update（§13.1）— 解一类问题
- 抽 `BackgroundScanner` 与 Qt 解耦（§13.3）— UI/CLI/test 三方都受益
- 统一配置变更通知机制（§13.4）
- 配置 schema 版本号 + migration（§十一.2 / §13.5）
- PaddleOCR 周期性 reload 兜底（§六.1）
- 多屏支持 Overlay 跟随 ROI 屏幕（§十.1）
- metric 输出（聚合日志 + 状态栏数字）（§十二.4）
- 类型安全的配置访问 dataclass / pydantic（§13.5）

每项落地前建议单开一份 plan 走 brainstorm → write-plan → 执行的完整流程。
