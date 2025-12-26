@echo off
REM ============================================================================
REM cx-Freeze 打包脚本 (Windows批处理版本)
REM OpenIDCS Client
REM ============================================================================

echo ============================================================
echo OpenIDCS Client - cx-Freeze 打包工具 (Windows)
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python未安装或未添加到PATH
    pause
    exit /b 1
)

echo [OK] Python已安装
python --version
echo.

REM 检查cx-Freeze是否安装
python -c "import cx_Freeze" >nul 2>&1
if errorlevel 1 (
    echo [WARN] cx-Freeze未安装
    echo.
    set /p install="是否安装cx-Freeze? (y/n): "
    if /i "%install%"=="y" (
        echo 正在安装cx-Freeze...
        python -m pip install cx-Freeze
        if errorlevel 1 (
            echo [ERROR] cx-Freeze安装失败
            pause
            exit /b 1
        )
        echo [OK] cx-Freeze安装成功
    ) else (
        echo 取消打包
        pause
        exit /b 1
    )
) else (
    echo [OK] cx-Freeze已安装
)
echo.

REM 清理旧的构建
if exist "build_cxfreeze" (
    echo 清理旧的构建目录...
    rmdir /s /q build_cxfreeze
)
if exist "dist" (
    rmdir /s /q dist
)
echo.

REM 开始打包
echo ============================================================
echo 开始打包...
echo ============================================================
echo.

python setup_cxfreeze.py build

if errorlevel 1 (
    echo.
    echo ============================================================
    echo [ERROR] 打包失败
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [SUCCESS] 打包成功!
echo 输出目录: build_cxfreeze\
echo ============================================================
echo.

REM 显示生成的文件
if exist "build_cxfreeze" (
    echo 生成的文件:
    dir /b build_cxfreeze\*.exe
    echo.
)

pause
