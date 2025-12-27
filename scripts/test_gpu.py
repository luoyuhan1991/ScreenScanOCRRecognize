"""
测试GPU加速是否被EasyOCR正确使用
"""

import torch
import easyocr
from datetime import datetime

print("=" * 60)
print("GPU加速测试")
print("=" * 60)

# 1. 检查PyTorch的GPU支持
print("\n[1] PyTorch GPU支持检查:")
print(f"PyTorch版本: {torch.__version__}")
print(f"CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA版本: {torch.version.cuda}")
    print(f"GPU数量: {torch.cuda.device_count()}")
    print(f"GPU名称: {torch.cuda.get_device_name(0)}")
    print(f"当前GPU: {torch.cuda.current_device()}")
else:
    print("CUDA不可用")

# 2. 测试EasyOCR的GPU使用
print("\n[2] EasyOCR GPU使用测试:")

# 测试使用GPU
print("\n尝试使用GPU初始化EasyOCR...")
try:
    reader_gpu = easyocr.Reader(['ch_sim', 'en'], gpu=True)
    print("✅ GPU模式初始化成功")
except Exception as e:
    print(f"❌ GPU模式初始化失败: {e}")
    reader_gpu = None

# 测试使用CPU
print("\n尝试使用CPU初始化EasyOCR...")
try:
    reader_cpu = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    print("✅ CPU模式初始化成功")
except Exception as e:
    print(f"❌ CPU模式初始化失败: {e}")
    reader_cpu = None

# 3. 测试识别速度
print("\n[3] 识别速度对比测试:")

# 创建一个简单的测试图像
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# 创建测试图像
img = Image.new('RGB', (800, 200), color='white')
draw = ImageDraw.Draw(img)
draw.text((10, 50), "这是一个测试文本，用于比较GPU和CPU的识别速度", fill='black')
draw.text((10, 100), "This is a test text for comparing GPU and CPU recognition speed", fill='black')

# 转换为numpy数组
img_array = np.array(img)

# 测试GPU识别速度
if reader_gpu:
    print("\nGPU识别测试...")
    import time
    start = time.time()
    result_gpu = reader_gpu.readtext(img_array)
    gpu_time = time.time() - start
    print(f"GPU识别耗时: {gpu_time:.3f}秒")
    print(f"识别结果数量: {len(result_gpu)}")
    if result_gpu:
        print(f"第一个结果: {result_gpu[0][1]} (置信度: {result_gpu[0][2]:.3f})")

# 测试CPU识别速度
if reader_cpu:
    print("\nCPU识别测试...")
    import time
    start = time.time()
    result_cpu = reader_cpu.readtext(img_array)
    cpu_time = time.time() - start
    print(f"CPU识别耗时: {cpu_time:.3f}秒")
    print(f"识别结果数量: {len(result_cpu)}")
    if result_cpu:
        print(f"第一个结果: {result_cpu[0][1]} (置信度: {result_cpu[0][2]:.3f})")

# 4. 性能对比
if reader_gpu and reader_cpu:
    print("\n[4] 性能对比:")
    speedup = cpu_time / gpu_time
    print(f"GPU加速比: {speedup:.2f}x")
    print(f"GPU比CPU快: {(1 - gpu_time/cpu_time)*100:.1f}%")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
