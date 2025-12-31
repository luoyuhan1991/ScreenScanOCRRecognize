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
else:
    print("警告: CUDA不可用，将使用CPU模式")

# 2. 检查EasyOCR的GPU支持
print("\n[2] EasyOCR GPU支持检查:")
try:
    import easyocr
    print(f"EasyOCR版本: {easyocr.__version__}")
except AttributeError:
    print("EasyOCR已安装（无法获取版本信息）")

# 3. 测试EasyOCR初始化（GPU模式）
print("\n[3] 测试EasyOCR初始化（GPU模式）:")
try:
    if torch.cuda.is_available():
        print("正在初始化EasyOCR（GPU模式）...")
        start_time = datetime.now()
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"初始化成功（耗时: {duration:.2f}秒）")
        print("确认: EasyOCR正在使用GPU加速")
    else:
        print("跳过GPU测试（CUDA不可用）")
except Exception as e:
    print(f"初始化失败: {e}")

# 4. 测试EasyOCR初始化（CPU模式）
print("\n[4] 测试EasyOCR初始化（CPU模式）:")
try:
    print("正在初始化EasyOCR（CPU模式）...")
    start_time = datetime.now()
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"初始化成功（耗时: {duration:.2f}秒）")
    print("确认: EasyOCR正在使用CPU模式")
except Exception as e:
    print(f"初始化失败: {e}")

# 5. 性能对比建议
print("\n[5] 性能对比建议:")
if torch.cuda.is_available():
    print("✓ GPU可用，建议在配置文件中设置:")
    print("  gpu:")
    print("    force_gpu: true")
    print("    或")
    print("    auto_detect: true")
else:
    print("✗ GPU不可用，将使用CPU模式")
    print("  如果您的系统有NVIDIA GPU，请检查:")
    print("  1. 是否安装了NVIDIA驱动")
    print("  2. 是否安装了CUDA工具包")
    print("  3. 是否安装了支持CUDA的PyTorch版本")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

