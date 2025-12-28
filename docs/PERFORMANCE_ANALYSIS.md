# OCR性能分析与优化建议

## 当前性能瓶颈分析

### 1. 图像预处理耗时（EasyOCR）

**位置**: `src/easy_ocr.py` - `preprocess_image()` 函数

**问题**:
- 多次颜色空间转换（RGB → BGR → GRAY → RGB）
- CLAHE（自适应直方图均衡化）计算开销大
- 锐化滤波（filter2D）需要卷积运算
- 每次识别都要执行完整的预处理流程

**优化建议**:
1. **缓存预处理结果**：如果图像内容相同，可以缓存预处理结果
2. **简化预处理流程**：根据图像质量选择性应用预处理
3. **并行处理**：使用多线程处理多张图像
4. **降低预处理精度**：对于实时场景，可以降低CLAHE的tileGridSize

### 2. 图像分辨率优化耗时

**位置**: `src/easy_ocr.py` - `optimize_image_resolution()` 函数

**问题**:
- 每次都要检查图像尺寸
- 使用LANCZOS重采样算法，质量高但速度慢
- 对于大图像，缩放操作耗时较长

**优化建议**:
1. **跳过不必要的缩放**：如果图像尺寸已经在合理范围内，直接跳过
2. **使用更快的重采样算法**：对于实时场景，可以使用NEAREST或BILINEAR
3. **预计算缩放比例**：避免重复计算

### 3. EasyOCR参数设置

**位置**: `src/easy_ocr.py` - `recognize_text()` 函数中的 `readtext()` 调用

**问题**:
- `canvas_size=2560` 较大，处理大图像时耗时
- `mag_ratio=2.0` 放大比例高，增加计算量
- 多个阈值参数设置较低，可能导致处理更多候选区域

**优化建议**:
1. **降低canvas_size**：根据实际图像尺寸动态调整，默认可以设为1280
2. **降低mag_ratio**：对于高分辨率图像，可以设为1.0或1.5
3. **优化阈值参数**：提高阈值可以减少处理的候选区域数量

### 4. PaddleOCR性能

**位置**: `src/paddle_ocr.py` - `recognize_and_print()` 函数

**问题**:
- 没有图像预处理优化
- 每次都要进行PIL到numpy的转换
- 没有使用GPU加速配置（如果可用）

**优化建议**:
1. **添加GPU支持检测**：PaddleOCR支持GPU，但代码中没有配置
2. **优化图像转换**：减少不必要的格式转换
3. **添加图像预处理**：类似EasyOCR的预处理可以提高识别准确率

### 5. 主循环性能

**位置**: `main.py` - 主循环

**问题**:
- 固定5秒间隔，没有考虑OCR实际耗时
- 如果OCR耗时超过间隔时间，会导致任务堆积

**优化建议**:
1. **动态调整间隔**：根据OCR耗时动态调整（已实现）
2. **异步处理**：使用异步IO处理OCR，不阻塞主循环
3. **批量处理**：如果有多张图像，可以批量处理

### 6. 图像格式转换开销

**问题**:
- PIL Image → numpy array → OpenCV BGR → RGB 多次转换
- 每次转换都需要内存拷贝

**优化建议**:
1. **统一图像格式**：在流程早期统一格式，避免多次转换
2. **使用内存视图**：使用numpy的view而不是copy
3. **直接使用OpenCV**：如果可能，直接使用OpenCV读取图像

## 具体优化方案

### 方案1: 优化图像预处理（高优先级）

```python
# 在config.yaml中添加预处理开关
ocr:
  use_preprocessing: true
  preprocessing:
    enable_clahe: true  # 可以关闭CLAHE加速
    enable_sharpen: true  # 可以关闭锐化加速
    fast_mode: false  # 快速模式，降低预处理质量
```

### 方案2: 优化EasyOCR参数（高优先级）

```python
# 根据图像尺寸动态调整参数
if image_width > 1920:
    canvas_size = 1920
    mag_ratio = 1.5
else:
    canvas_size = 1280
    mag_ratio = 1.0
```

### 方案3: 添加GPU支持（中优先级）

```python
# 在PaddleOCR初始化时添加GPU支持
ocr = PaddleOCR(
    lang=ocr_lang,
    use_gpu=use_gpu,  # 添加GPU支持
    use_angle_cls=True,  # 角度分类
    enable_mkldnn=True,  # Intel CPU优化
)
```

### 方案4: 图像缓存（低优先级）

```python
# 缓存相同图像的预处理结果
from functools import lru_cache
import hashlib

@lru_cache(maxsize=10)
def cached_preprocess(image_hash, image_size):
    # 预处理逻辑
    pass
```

## 预期性能提升

1. **优化预处理**: 可节省 20-30% 时间
2. **优化参数**: 可节省 15-25% 时间
3. **GPU加速**: 可提升 3-10倍速度（如果有GPU）
4. **图像缓存**: 可节省 10-20% 时间（对于重复图像）

## 建议实施顺序

1. **第一步**: 优化EasyOCR参数（canvas_size, mag_ratio）
2. **第二步**: 添加预处理开关，允许关闭耗时操作
3. **第三步**: 为PaddleOCR添加GPU支持
4. **第四步**: 实现图像缓存（如果需要）

## 监控建议

- 使用已添加的耗时统计功能，监控各步骤耗时
- 记录图像尺寸与耗时的关系
- 分析不同场景下的性能表现

