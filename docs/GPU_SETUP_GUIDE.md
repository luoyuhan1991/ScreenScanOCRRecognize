# GPU加速配置指南

## 当前状态

- **显卡型号**: NVIDIA GeForce RTX 4060 Ti
- **CUDA版本**: 12.6
- **当前PyTorch**: 2.9.1+cpu (CPU版本，不支持GPU加速)

## 安装步骤

### 步骤1: 卸载当前的CPU版本PyTorch

```bash
py -m pip uninstall torch torchvision torchaudio -y
```

### 步骤2: 安装支持CUDA 12.6的PyTorch版本

对于Windows系统，使用以下命令安装支持CUDA 12.6的PyTorch：

```bash
py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

**注意**: 这个安装包比较大（约2-3GB），下载和安装可能需要几分钟时间。

### 步骤3: 验证GPU支持

安装完成后，运行以下命令验证：

```bash
py -c "import torch; print('PyTorch版本:', torch.__version__); print('CUDA可用:', torch.cuda.is_available()); print('GPU名称:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

预期输出：
```
PyTorch版本: 2.9.1+cu126
CUDA可用: True
GPU名称: NVIDIA GeForce RTX 4060 Ti
```

### 步骤4: 测试GPU加速

运行GPU测试脚本：

```bash
py scripts/test_gpu.py
```

或者运行主程序并强制使用GPU：

```bash
py main.py 1 2 1
```

参数说明：
- `1`: 全屏扫描
- `2`: 强制使用GPU
- `1`: 中英文

## 性能对比

根据EasyOCR的官方说明，使用GPU加速可以显著提升识别速度：

| 模式 | 识别速度 | 备注 |
|------|---------|------|
| CPU | ~5-10秒/图 | 适合低频使用 |
| GPU (RTX 4060 Ti) | ~0.5-2秒/图 | 适合高频使用 |

## 常见问题

### Q1: 安装失败或下载速度慢

**解决方案**:
1. 使用国内镜像源：
```bash
py -m pip install torch torchvision torchaudio -i https://pypi.tuna.tsinghua.edu.cn/simple --index-url https://download.pytorch.org/whl/cu126
```

2. 或者使用conda安装（如果你有Anaconda）：
```bash
conda install pytorch torchvision torchaudio pytorch-cuda=12.6 -c pytorch -c nvidia
```

### Q2: CUDA不可用

**解决方案**:
1. 确认NVIDIA驱动已安装并更新到最新版本
2. 下载并安装CUDA Toolkit 12.6: https://developer.nvidia.com/cuda-12-6-0-download-archive
3. 重启电脑后再次验证

### Q3: 显存不足

**解决方案**:
如果遇到显存不足的问题，可以修改 `src/ocr_recognize.py` 中的参数：

```python
# 降低canvas_size以减少显存使用
canvas_size=1280,  # 从2560降低到1280
```

## 使用建议

1. **开发/测试阶段**: 使用CPU模式（`py main.py 1 3 1`），避免频繁切换GPU
2. **生产环境**: 使用GPU模式（`py main.py 1 2 1`），提升识别速度
3. **混合模式**: 使用自动检测（`py main.py 1 1 1`），让程序自动选择最佳模式

## 监控GPU使用情况

运行程序时，可以在另一个终端窗口运行以下命令监控GPU使用情况：

```bash
nvidia-smi -l 1
```

这将每秒刷新一次GPU状态，包括显存使用情况、GPU利用率等。

## 完整安装脚本

如果你想一次性完成所有步骤，可以创建一个批处理文件 `install_gpu.bat`：

```batch
@echo off
echo ========================================
echo GPU加速安装脚本
echo ========================================
echo.

echo [1/4] 卸载CPU版本PyTorch...
py -m pip uninstall torch torchvision torchaudio -y

echo.
echo [2/4] 安装支持CUDA 12.6的PyTorch...
py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

echo.
echo [3/4] 验证GPU支持...
py -c "import torch; print('PyTorch版本:', torch.__version__); print('CUDA可用:', torch.cuda.is_available()); print('GPU名称:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"

echo.
echo [4/4] 安装完成！
echo.
echo 现在可以使用GPU加速了：
echo   py main.py 1 2 1
echo.
pause
```

保存后双击运行即可。

---

**注意**: 安装GPU版本PyTorch需要较大的磁盘空间（约3-5GB），请确保有足够的可用空间。
