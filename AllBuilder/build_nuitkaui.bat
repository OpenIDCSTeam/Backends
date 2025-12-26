@echo off
REM OpenIDCS Client - Nuitka打包脚本 (Windows)
REM 使用Nuitka将项目打包成独立可执行文件

echo ========================================
echo OpenIDCS Client - Nuitka打包工具
echo ========================================
echo.

REM 切换到项目根目录
cd ..
echo 项目根目录: %CD%
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 检查是否在项目根目录
if not exist "HostServer.py" (
    echo [错误] 找不到HostServer.py，请在项目根目录运行此脚本
    pause
    exit /b 1
)

REM 检查Nuitka是否安装
python -m nuitka --version >nul 2>&1
if errorlevel 1 (
    echo [提示] Nuitka未安装，正在安装...
    python -m pip install -U nuitka
    if errorlevel 1 (
        echo [错误] Nuitka安装失败
        pause
        exit /b 1
    )
    echo [成功] Nuitka安装完成
    echo.
)

REM 询问是否清理旧的构建
if exist "build_nuitka" (
    echo 发现旧的构建目录
    set /p clean="是否清理旧的构建目录? (y/n): "
    if /i "%clean%"=="y" (
        echo 正在清理...
        rmdir /s /q build_nuitka
        echo 清理完成
        echo.
    )
)

echo ========================================
echo 开始打包...
echo ========================================
echo.
echo 这可能需要几分钟时间，请耐心等待...
echo.

REM 使用配置文件打包
python -m nuitka @nuitka_build/nuitka.config HostServer.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo [错误] 打包失败
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo [成功] 打包完成!
echo 输出目录: build_nuitka
echo ========================================
echo.

REM 显示生成的文件
if exist "build_nuitka\OpenIDCS-Client.exe" (
    echo 可执行文件: build_nuitka\OpenIDCS-Client.exe
    dir "build_nuitka\OpenIDCS-Client.exe"
)

pause
