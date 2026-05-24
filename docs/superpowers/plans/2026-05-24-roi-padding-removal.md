# ROI Padding 移除 + 红框 1px 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 `scan.roi_padding` 配置项与对应的外扩逻辑，让 ROI 红框与实际扫描区域完全重合；同时把红框粗细从 2px 调整为 1px。

**Architecture:** 纯删除 / 精确修改型变更，不引入新抽象。修改面：1 个配置 yaml、1 个默认值文件、1 个 pipeline 文件、1 个 UI widget、1 个 docs。CaptureStage 改为直接使用入参 rect 调 mss，去掉每边外扩 10px 的步骤；ROIBorder 改 `BORDER_WIDTH` 常量。

**Tech Stack:** Python 3.11 / PySide6 / mss / pytest（plain assert 风格）。

**Spec：** `docs/superpowers/specs/2026-05-24-roi-padding-removal-design.md`

**Verification 约定**：现有测试用 `python tests/<test_file>.py` 直接跑（项目已有 sys.path 注入）。新功能没补单测——本计划是删除 + 数值变更，单测覆盖收益低于 GUI 烟测。

---

## File Structure

修改的文件清单：

**Modify**
- `config/defaults.py` — 删除 `roi_padding` 键（Task 1）
- `config/config.yaml` — 删除 `roi_padding` 键（Task 1）
- `pipeline/capture.py` — 移除 padding 外扩逻辑（Task 2）
- `ui/roi_border.py` — `BORDER_WIDTH` 改为 1（Task 3）
- `CLAUDE.md` — 注释里的 padding 描述同步更新（Task 4）

**不动**：历史文档（`docs/GUI_DESIGN.md` / `docs/PRD_COMPARISON.md` / `docs/PYSIDE6_MIGRATION.md` / 旧 plan）—— 它们是过去某时点的快照，按"精准修改"原则保留。

---

## Task 1: 删除 `roi_padding` 配置项

**Files:**
- Modify: `config/defaults.py:20`
- Modify: `config/config.yaml:30`

**Background:** spec §决策 ①。`roi_padding` 在 defaults 和 yaml 各有一处定义。先把两处同时删掉，让后面 Task 2 改 capture.py 时 `config.get('scan.roi_padding')` 返回 None。

- [ ] **Step 1: 读 `config/defaults.py` 确认当前第 20 行内容**

Run: 使用 Read 工具读 `config/defaults.py` 第 1-50 行
Expected: 第 20 行是 `'roi_padding': 10,                # ROI 周围外扩像素数（避免边缘文字被裁切）`

- [ ] **Step 2: 删除 `config/defaults.py:20`**

把这一行整行删除（包括尾部换行符）。确保上下文行（19、21）原样保留。

删除前（示例上下文）：
```python
        # 扫描间隔（秒）
        'interval_seconds': 5.0,
        'roi_padding': 10,                # ROI 周围外扩像素数（避免边缘文字被裁切）
        'enable_roi': True,
```

删除后：
```python
        # 扫描间隔（秒）
        'interval_seconds': 5.0,
        'enable_roi': True,
```

（注：上面 19/21 行内容以实际文件为准，看 Step 1 确认后再做。）

- [ ] **Step 3: 读 `config/config.yaml` 确认第 30 行内容**

Run: Read `config/config.yaml`，看第 25-35 行
Expected: 第 30 行附近是 `roi_padding: 10`（缩进 2 格，在 `scan:` 块下）

- [ ] **Step 4: 删除 `config/config.yaml` 的 `roi_padding: 10` 行**

整行删除。注意 yaml 缩进，删除后上下行的缩进不应变化。

- [ ] **Step 5: 跑现有测试确认无回归**

Run（依次）:
```
python tests/test_config_keys.py
python tests/test_config_consistency.py
python tests/test_matcher_resilience.py
```

Expected: 三个测试都输出 `PASS`，无 AssertionError。

如果 `test_config_keys.py` 失败，检查是否有 `roi_padding` 相关断言——按 spec 说没有，但以实际为准。

- [ ] **Step 6: 验证运行时 config.get 返回 None**

Run（在项目根）:
```
python -c "from config.config import config; config.load(); print(repr(config.get('scan.roi_padding')))"
```

Expected: `None`（说明 defaults 和 yaml 都已删除，深合并后该 key 不存在）

- [ ] **Step 7: Commit**

```bash
git add config/defaults.py config/config.yaml
git commit -m "chore(config): 删除未发挥价值的 scan.roi_padding"
```

---

## Task 2: 移除 `CaptureStage.grab` 的 padding 外扩逻辑

**Files:**
- Modify: `pipeline/capture.py:38-50`

**Background:** spec §改动清单。Task 1 删完配置后，capture.py:40 的 `config.get('scan.roi_padding')` 会返回 None，下面的 `x1 - padding` 会抛 `TypeError: unsupported operand type(s) for -: 'int' and 'NoneType'`。本任务把整段 padding 逻辑移除，让 monitor 直接用入参 rect。

- [ ] **Step 1: 读 `pipeline/capture.py:38-57` 确认当前实现**

Run: Read `pipeline/capture.py`，看第 30-60 行
Expected: 看到 38-50 行的 `if roi is not None: ... padding = config.get(...)` 那段

- [ ] **Step 2: 用 Edit 工具替换 38-50 行**

把以下旧代码：

```python
        if roi is not None:
            x1, y1, x2, y2 = roi
            padding = config.get('scan.roi_padding')
            monitor_info = self.sct.monitors[1]
            sw, sh = monitor_info['width'], monitor_info['height']
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(sw, x2 + padding)
            y2 = min(sh, y2 + padding)
            monitor = {
                "left": x1, "top": y1,
                "width": x2 - x1, "height": y2 - y1
            }
        else:
            monitor = self.sct.monitors[1]
```

替换为：

```python
        if roi is not None:
            x1, y1, x2, y2 = roi
            monitor = {
                "left": x1, "top": y1,
                "width": x2 - x1, "height": y2 - y1
            }
        else:
            monitor = self.sct.monitors[1]
```

注意：
- 保留 `roi is not None` 分支
- 保留 `else: monitor = self.sct.monitors[1]` 全屏分支
- **不要**改动 38 行之前的"防御性二次校验"块（`if roi is not None and not config.get('scan.enable_roi'): roi = None`）
- **不要**改动 54 行之后的 `img = self.sct.grab(monitor)` 等

- [ ] **Step 3: 跑测试**

Run:
```
python tests/test_config_keys.py
python tests/test_config_consistency.py
python tests/test_matcher_resilience.py
```

Expected: 三个 PASS。

- [ ] **Step 4: GUI 烟测——开扫看是否报错**

Run: `python app.py`
- 启动后点"开始扫描"
- picker 弹出 → 框选一小块（如桌面某个图标）→ 释放
- 看日志面板：应正常显示 `OCR ... 行` 之类的扫描日志，**不**应有 `TypeError: unsupported operand type(s) for -` 之类报错
- 点"停止"

Expected: 扫描正常运行，无异常。

> 如果你在开发机上（无法运行 GUI），跳过此步，由用户验证。本机改完代码即可，CLAUDE.md 提醒"开发机 ≠ 运行机"。

- [ ] **Step 5: Commit**

```bash
git add pipeline/capture.py
git commit -m "refactor(capture): 删除 ROI 外扩，扫描区域直接等于入参 rect"
```

---

## Task 3: 红框粗细 2 → 1 像素

**Files:**
- Modify: `ui/roi_border.py:13`

**Background:** spec §决策 ②。视觉减重，配合 Task 2 的"红框对齐扫描区域"。paintEvent 公式 `drawRect(bw//2, bw//2, w-bw, h-bw)` 在 bw=1 时仍正确（`bw//2=0`，画 `(0,0)~(w-1,h-1)`），无需改 paintEvent。

- [ ] **Step 1: 读 `ui/roi_border.py:10-15` 确认 BORDER_WIDTH 当前值**

Run: Read `ui/roi_border.py`，看第 10-20 行
Expected: 第 13 行是 `BORDER_WIDTH = 2`

- [ ] **Step 2: 用 Edit 工具改 BORDER_WIDTH**

把：
```python
    BORDER_WIDTH = 2
```

改为：
```python
    BORDER_WIDTH = 1
```

不动 14 行的 `BORDER_COLOR`。

- [ ] **Step 3: GUI 烟测——红框对齐 + 锐利度**

Run: `python app.py` → 点开始 → 框选 → 看红框：

1. **四角对齐**：红框的边线应恰好沿着 picker 拖出来的边界，不外溢、不内缩
2. **1px 锐利**：放大看（或截屏放大），红框应是清晰 1px 实线，无模糊或抗锯齿羽化
3. **不同背景可见性**：把扫描区域放在浅色（如桌面壁纸）和深色（如终端窗口）背景上各看一次，红框都能辨识

Expected: 三条都满足。

> 若 1px 在某种背景下确实看不清，记录现象但不本任务回退——按 spec §后续可能，作为后续单独 issue。

- [ ] **Step 4: Commit**

```bash
git add ui/roi_border.py
git commit -m "feat(roi): 红框粗细 2px 改 1px，减少视觉干扰"
```

---

## Task 4: 更新 `CLAUDE.md` 注释

**Files:**
- Modify: `CLAUDE.md:87`

**Background:** spec §改动清单。CLAUDE.md 描述了 capture.py 的行为，提到"ROI 模式按 `scan.roi_padding` 外扩"——这是 Claude 的项目记忆来源，必须同步，否则未来会议中 Claude 会按错的描述思考问题。

- [ ] **Step 1: 读 `CLAUDE.md:80-95` 确认当前内容**

Run: Read `CLAUDE.md`，看 80-95 行
Expected: 第 87 行附近有 `**`pipeline/capture.py`** — `CaptureStage`，mss 截屏。...ROI 模式按 `scan.roi_padding` 外扩。`

- [ ] **Step 2: 用 Edit 工具替换**

把：
```
ROI 模式按 `scan.roi_padding` 外扩。
```

改为：
```
ROI 模式按入参 rect 直接截取。
```

如果原文是更长的一句话（含此片段），只替换该片段，不动周围文字。

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): 同步 capture.py 不再外扩的事实"
```

---

## 完成后总验收

- [ ] **配置层**：跑
```
python -c "from config.config import config; config.load(); print('roi_padding =', repr(config.get('scan.roi_padding')))"
```
Expected: `roi_padding = None`

- [ ] **回归测试**：依次跑
```
python tests/test_config_keys.py
python tests/test_config_consistency.py
python tests/test_matcher_resilience.py
```
Expected: 全 PASS

- [ ] **GUI 烟测**：
  - 启动 → 开扫 → picker 框选某个 UI 元素（如标题栏带 "X" 关闭按钮的对话框）
  - 红框四角应**严格对齐**框选边界
  - 红框是 1px 清晰实线
  - OCR 仍能识别框内文字（命中关键词时弹 overlay）
  - 停扫 → 红框消失
  - 改 picker 选区再开扫 → 新红框对齐新区域

- [ ] **代码层确认**：
  - `pipeline/capture.py` 内 grep `roi_padding` → 0 命中
  - `config/defaults.py` 内 grep `roi_padding` → 0 命中
  - `config/config.yaml` 内 grep `roi_padding` → 0 命中
  - `CLAUDE.md` 内 grep `roi_padding` → 0 命中（仅历史 docs/ 下应该还有）

- [ ] **git log 检查**：4 个 commit 都已落地，顺序为：
  1. `chore(config): 删除未发挥价值的 scan.roi_padding`
  2. `refactor(capture): 删除 ROI 外扩，扫描区域直接等于入参 rect`
  3. `feat(roi): 红框粗细 2px 改 1px，减少视觉干扰`
  4. `docs(claude): 同步 capture.py 不再外扩的事实`

---

## 风险与回退

**若 GUI 烟测发现 OCR 识别边缘文字困难**（spec §风险）：

- 不回退本计划。让用户在 picker 阶段框得稍大。
- 若后续证实是共性问题，单开 issue 决定是否引入"边缘扩"配置（届时要同步红框跟随外扩）。

**若 1px 红框某些背景下看不清**：

- 不回退本计划。
- 后续可单独加 1px 黑色阴影描边（仍保持视觉细线感）作为增强。

**回退操作**（万不得已）：

```bash
git revert <commit-hash-of-task1> <commit-hash-of-task2> <commit-hash-of-task3> <commit-hash-of-task4>
```

按提交顺序逆序 revert，或者整体 reset 到本计划前的 HEAD。
