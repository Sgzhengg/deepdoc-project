@echo off
echo ========================================
echo DeepSeek API 快速测试
echo ========================================
echo.

cd /d "%~dp0backend"

echo [1/3] 检查依赖...
python -c "import httpx" 2>nul
if errorlevel 1 (
    echo 安装依赖...
    pip install httpx
)

echo [2/3] 测试 API 连接...
python test_deepseek_api.py
if errorlevel 1 (
    echo.
    echo ❌ API 测试失败
    echo 请检查:
    echo   1. API Key 是否正确
    echo   2. 网络连接是否正常
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] 启动后端服务...
echo.
echo 启动后，访问 http://localhost:8000/docs 测试聊天接口
echo.
echo 按 Ctrl+C 停止服务
echo.

python main.py

pause
