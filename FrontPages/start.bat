@echo off
chcp 65001 >nul
echo ========================================
echo OpenIDCS Frontend 快速启动脚本
echo ========================================
echo.

REM 检查Node.js是否安装
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到Node.js，请先安装Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo [信息] Node.js版本:
node --version
echo.

REM 检查npm是否安装
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到npm
    pause
    exit /b 1
)

echo [信息] npm版本:
npm --version
echo.

REM 检查node_modules是否存在
if not exist "node_modules" (
    echo [信息] 首次运行，正在安装依赖...
    echo.
    npm install
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo.
    echo [成功] 依赖安装完成
    echo.
) else (
    echo [信息] 依赖已安装
    echo.
)

echo [信息] 启动开发服务器...
echo [信息] 访问地址: http://localhost:3000
echo [信息] 按 Ctrl+C 停止服务器
echo.
echo ========================================
echo.

npm run dev

pause
