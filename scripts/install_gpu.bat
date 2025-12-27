@echo off
chcp 65001 >nul
echo ========================================
echo GPU加速安装脚本
echo ========================================
echo.

echo [1/4] 卸载CPU版本PyTorch...
py -m pip uninstall torch torchvision torchaudio -y

echo.
echo [2/4] 安装支持CUDA 12.6的PyTorch...
echo 注意：这个步骤可能需要几分钟时间，请耐心等待...
echo.
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
