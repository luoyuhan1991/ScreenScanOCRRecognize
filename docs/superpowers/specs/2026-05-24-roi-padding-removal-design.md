# ROI 红框与扫描区域对齐 + 红框粗细调整设计

**日期：** 2026-05-24
**触发问题：** 扫描运行时，屏幕上的 ROI 红框与实际被 OCR 扫描的区域存在视觉偏差，用户描述为"红框与 ROI 区域有些许误差"。

---

## 背景

当前实现中：

- `pipeline/capture.py:38-50`：CaptureStage 截屏前，把入参 rect 按 `scan.roi_padding`（默认 10 像素）**每边外扩**后再交给 mss。
- `ui/main_window.py:170`：`roi_border.show_for(roi)` 传入的是用户在 picker 里框选的**原始 rect**，未外扩。
- `ui/roi_border.py:13`：`BORDER_WIDTH = 2`，红框 2px 粗。

结果：**实际扫描区域 = 用户选的 rect + 10px 外扩**，而**红框 = 用户选的 rect**。视觉上红框比扫描区域小一圈（每边 10px），违反"红框应反映正在扫的真实区域"的预期。

`roi_padding` 的历史动机是"避免边缘文字被裁切"（见 `defaults.py:20` 注释），但代价是引入"两个 rect 不一致"的同步负担。运行环境（Windows 单屏 100% 缩放，已通过排查确认）下不存在 DPI 缩放或多屏负坐标等其它偏移源。

## 决策

**① 彻底删除 `roi_padding`**

理由（YAGNI）：

- 当前 padding 实际只造成视觉不一致 bug，没有用户层面的可观察收益（边缘字裁切问题用户从未报告过）。
- 保留配置项就要持续维护"红框是否跟着外扩"的同步逻辑；删除一次到位，配置/代码双清。
- 如果未来真的出现"边缘字识别不到"，让用户在 picker 时框得稍大一点是更直观的解。彼时若证明确实有共性需求，再加回 1 行配置成本极低。

**② 红框粗细 2 → 1 像素**

理由：

- ROIBorder 是工作时屏幕指示，1px 已足够辨识且更不打扰。
- paintEvent 现有公式 `drawRect(bw//2, bw//2, w-bw, h-bw)` 在 bw=1 时仍正确：`bw//2=0` → 画 `(0,0)~(w-1,h-1)` 紧贴窗口外沿。
- `Antialiasing=False`（roi_border.py:46）保证 1px 边线在整数坐标上锐利不模糊。

## 改动清单

### 文件修改

| 文件 | 行号 | 改动 |
|---|---|---|
| `config/defaults.py` | 20 | 删除 `'roi_padding': 10` 整行 |
| `config/config.yaml` | 30 | 删除 `roi_padding: 10` 整行 |
| `pipeline/capture.py` | 38-50 | 移除 padding 外扩逻辑，`monitor` 直接用入参 rect 构造：`{"left": x1, "top": y1, "width": x2-x1, "height": y2-y1}` |
| `ui/roi_border.py` | 13 | `BORDER_WIDTH = 2` → `BORDER_WIDTH = 1` |
| `CLAUDE.md` | 87 | 把"ROI 模式按 `scan.roi_padding` 外扩"改为"ROI 模式按入参 rect 直接截取" |

### 不动的文件（按"精准修改"原则）

历史文档保留过去某时点的快照，不属于本次范围：

- `docs/GUI_DESIGN.md`（提到 `roi_padding` 两处）
- `docs/PRD_COMPARISON.md`
- `docs/PYSIDE6_MIGRATION.md`
- `docs/superpowers/plans/2026-05-09-pyside6-ui-migration.md`

### 不需要新增/删除测试

- `tests/test_config_keys.py` 不断言 `roi_padding`，自动通过。
- `tests/test_config_consistency.py` 同上。
- 不补新单测：本次改动是删除 + 1 个数值变更，单测覆盖收益低于 GUI 烟测。

## 验证

**自动化测试**

```
python tests/test_config_keys.py
python tests/test_config_consistency.py
python tests/test_matcher_resilience.py
```

预期：全 PASS（这些测试不依赖 padding）。

**手动 GUI 烟测**

1. `python app.py` 启动 → 点开扫 → picker 框选一块（建议框带有明确边界的区域，如某个对话框边缘）
2. **重点：四角对齐** — 红框的内沿应与 picker 时拖出来的框完全重合
3. **1px 边线锐利度** — 红框在浅色和深色背景上都能看清，无模糊
4. **OCR 行为没回退** — 框出来的内容仍能正常被 OCR 识别，没有因为不再外扩导致少识别（如果有，记录"哪种内容受影响"作为后续判断是否要恢复 padding 的依据）

**配置层验证**

- 启动后 `config.get('scan.roi_padding')` 应返回 `None`（defaults 已删，yaml 已删）—— 用 Python 交互式或临时打印验证
- `Config` 深合并对"yaml 有但 defaults 无的键"行为是直接保留，删 yaml 才能彻底清掉残留

## 风险

| 风险 | 严重度 | 缓解 |
|---|---|---|
| 用户旧版本升级后 yaml 残留 `roi_padding` 键 | 低 | 本次同步删 yaml，新用户全新；老用户即使残留也只是无意义键，不报错 |
| 边缘文字裁切 | 中 | 用户可在 picker 时多框 10-20px。若实际发生，单独跟进（不作本次范围） |
| 1px 红框在某些显示器/亮度下不够显眼 | 低 | 用户可反馈，下次调回 2px 或加阴影 |

## 后续可能（不包含在本次）

- 若边缘裁切问题确实出现：考虑"扫描区域 = 红框"恒等，由用户主动框大一点（无配置项）
- 若 1px 不够显眼：考虑加 1px 黑色阴影描边（仍保持视觉细线感）

---

**Status：** Ready for plan
