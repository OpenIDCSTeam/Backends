@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================
:: OpenIDCS VMware Workstation 自动化安装配置脚本 (Windows)
:: ============================================
:: 功能：自动安装并配置 VMware Workstation 及 vmrest API
:: 适用：Windows 10/11, Windows Server 2016+
:: 作者：OpenIDCS Team
:: ============================================

set "SCRIPT_VERSION=1.0.0"
set "FORCE_INSTALL=0"
set "UNINSTALL_MODE=0"
set "VMWARE_VERSION="
set "SILENT_MODE=0"

:: 颜色代码（使用 PowerShell 实现）
set "COLOR_RED=[91m"
set "COLOR_GREEN=[92m"
set "COLOR_YELLOW=[93m"
set "COLOR_BLUE=[94m"
set "COLOR_MAGENTA=[95m"
set "COLOR_CYAN=[96m"
set "COLOR_WHITE=[97m"
set "COLOR_RESET=[0m"

:: VMware 版本信息
set "VMWARE_16_NAME=VMware-workstation-full-16.2.5-20904516.exe"
set "VMWARE_17_NAME=VMware-workstation-full-17.5.2-23775571.exe"
set "VMWARE_25H2_NAME=VMware-workstation-full-17.6.0-24238078.exe"

set "VMWARE_16_URL=https://download3.vmware.com/software/WKST-1625-WIN/VMware-workstation-full-16.2.5-20904516.exe"
set "VMWARE_17_URL=https://download3.vmware.com/software/WKST-1752-WIN/VMware-workstation-full-17.5.2-23775571.exe"
set "VMWARE_25H2_URL=https://download3.vmware.com/software/WKST-1760-WIN/VMware-workstation-full-17.6.0-24238078.exe"

:: 解析命令行参数
:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="-f" set "FORCE_INSTALL=1" & shift & goto :parse_args
if /i "%~1"=="--force" set "FORCE_INSTALL=1" & shift & goto :parse_args
if /i "%~1"=="-d" set "UNINSTALL_MODE=1" & shift & goto :parse_args
if /i "%~1"=="--delete" set "UNINSTALL_MODE=1" & shift & goto :parse_args
if /i "%~1"=="-v" set "VMWARE_VERSION=%~2" & shift & shift & goto :parse_args
if /i "%~1"=="--version" set "VMWARE_VERSION=%~2" & shift & shift & goto :parse_args
if /i "%~1"=="-s" set "SILENT_MODE=1" & shift & goto :parse_args
if /i "%~1"=="--silent" set "SILENT_MODE=1" & shift & goto :parse_args
if /i "%~1"=="-h" goto :show_help
if /i "%~1"=="--help" goto :show_help
echo %COLOR_RED%✗ 未知参数: %~1%COLOR_RESET%
goto :show_help

:args_done

:: 检查管理员权限
call :check_admin
if errorlevel 1 (
    echo %COLOR_RED%✗ 请使用管理员权限运行此脚本%COLOR_RESET%
    echo.
    echo 右键点击脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)

:: 卸载模式
if "%UNINSTALL_MODE%"=="1" goto :uninstall_vmware

:: 显示标题
call :print_title "OpenIDCS VMware Workstation 安装向导 v%SCRIPT_VERSION%"

:: 检测系统信息
call :detect_system

:: 选择 VMware 版本
call :select_vmware_version

:: 获取安装包
call :get_vmware_installer

:: 安装 VMware Workstation
call :install_vmware

:: 配置 vmrest API
call :configure_vmrest

:: 配置防火墙
call :configure_firewall

:: 测试 API
call :test_vmrest_api

:: 显示配置摘要
call :show_summary

echo.
echo %COLOR_GREEN%✓ 安装完成！%COLOR_RESET%
pause
exit /b 0

:: ============================================
:: 函数定义
:: ============================================

:show_help
echo.
call :print_line "═"
echo %COLOR_WHITE%OpenIDCS VMware Workstation 安装脚本 v%SCRIPT_VERSION%%COLOR_RESET%
call :print_line "═"
echo.
echo %COLOR_WHITE%用法:%COLOR_RESET%
echo   %COLOR_CYAN%vmw-setups.bat%COLOR_RESET% [选项]
echo.
echo %COLOR_WHITE%选项:%COLOR_RESET%
echo   %COLOR_GREEN%-v, --version ^<版本^>%COLOR_RESET%  指定 VMware 版本 (16/17/25H2)
echo   %COLOR_GREEN%-f, --force%COLOR_RESET%           强制重新安装（即使已安装）
echo   %COLOR_GREEN%-s, --silent%COLOR_RESET%          静默安装模式（使用默认配置）
echo   %COLOR_RED%-d, --delete%COLOR_RESET%          卸载 VMware Workstation
echo   %COLOR_BLUE%-h, --help%COLOR_RESET%            显示此帮助信息
echo.
echo %COLOR_WHITE%示例:%COLOR_RESET%
echo   %COLOR_CYAN%vmw-setups.bat%COLOR_RESET%                    %COLOR_BLUE%# 交互式安装%COLOR_RESET%
echo   %COLOR_CYAN%vmw-setups.bat -v 17%COLOR_RESET%              %COLOR_BLUE%# 安装 VMware 17%COLOR_RESET%
echo   %COLOR_CYAN%vmw-setups.bat -f%COLOR_RESET%                 %COLOR_BLUE%# 强制重新安装%COLOR_RESET%
echo   %COLOR_CYAN%vmw-setups.bat -d%COLOR_RESET%                 %COLOR_BLUE%# 卸载 VMware%COLOR_RESET%
echo.
exit /b 0

:check_admin
net session >nul 2>&1
exit /b %errorlevel%

:print_line
set "char=%~1"
if "%char%"=="" set "char=═"
echo %COLOR_BLUE%════════════════════════════════════════════════════════════%COLOR_RESET%
exit /b 0

:print_title
echo.
call :print_line "═"
echo %COLOR_WHITE%  %~1%COLOR_RESET%
call :print_line "═"
echo.
exit /b 0

:print_step
echo.
call :print_line "─"
echo %COLOR_CYAN%▶ %~1%COLOR_RESET%
call :print_line "─"
echo.
exit /b 0

:detect_system
call :print_step "检测系统信息"

echo %COLOR_BLUE%ℹ%COLOR_RESET% 检测操作系统...

for /f "tokens=4-5 delims=. " %%i in ('ver') do set "OS_VERSION=%%i.%%j"
for /f "tokens=*" %%i in ('wmic os get caption ^| findstr /v Caption') do set "OS_NAME=%%i"

echo %COLOR_GREEN%✓%COLOR_RESET% 系统: !OS_NAME! (版本 !OS_VERSION!)

:: 检查系统架构
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    echo %COLOR_GREEN%✓%COLOR_RESET% 架构: x64
) else (
    echo %COLOR_RED%✗%COLOR_RESET% 不支持的架构: %PROCESSOR_ARCHITECTURE%
    echo VMware Workstation 需要 64 位系统
    pause
    exit /b 1
)

:: 检查虚拟化支持
echo %COLOR_BLUE%ℹ%COLOR_RESET% 检查虚拟化支持...
systeminfo | findstr /C:"Hyper-V" >nul 2>&1
if %errorlevel%==0 (
    echo %COLOR_YELLOW%⚠%COLOR_RESET% 检测到 Hyper-V 已启用，可能与 VMware 冲突
    echo 如果遇到问题，请禁用 Hyper-V: bcdedit /set hypervisorlaunchtype off
)

exit /b 0

:select_vmware_version
if not "%VMWARE_VERSION%"=="" (
    if /i "%VMWARE_VERSION%"=="16" goto :version_selected
    if /i "%VMWARE_VERSION%"=="17" goto :version_selected
    if /i "%VMWARE_VERSION%"=="25H2" goto :version_selected
    echo %COLOR_RED%✗ 不支持的 VMware 版本: %VMWARE_VERSION%%COLOR_RESET%
    echo 支持的版本: 16, 17, 25H2
    pause
    exit /b 1
)

if "%SILENT_MODE%"=="1" (
    set "VMWARE_VERSION=17"
    goto :version_selected
)

echo.
echo %COLOR_WHITE%请选择要安装的 VMware Workstation 版本:%COLOR_RESET%
echo.
echo   %COLOR_CYAN%[1]%COLOR_RESET% VMware Workstation 16.x (16.2.5)
echo   %COLOR_CYAN%[2]%COLOR_RESET% VMware Workstation 17.x (17.5.2) %COLOR_GREEN%[推荐]%COLOR_RESET%
echo   %COLOR_CYAN%[3]%COLOR_RESET% VMware Workstation 17.6 (25H2 兼容版本)
echo.
set /p "VERSION_CHOICE=请输入选项 [1-3, 默认: 2]: "
if "%VERSION_CHOICE%"=="" set "VERSION_CHOICE=2"

if "%VERSION_CHOICE%"=="1" set "VMWARE_VERSION=16"
if "%VERSION_CHOICE%"=="2" set "VMWARE_VERSION=17"
if "%VERSION_CHOICE%"=="3" set "VMWARE_VERSION=25H2"

if "%VMWARE_VERSION%"=="" (
    echo %COLOR_RED%✗ 无效的选项: %VERSION_CHOICE%%COLOR_RESET%
    pause
    exit /b 1
)

:version_selected
echo %COLOR_GREEN%✓%COLOR_RESET% 已选择: VMware Workstation %VMWARE_VERSION%
exit /b 0

:get_vmware_installer
call :print_step "获取 VMware 安装包"

if "%VMWARE_VERSION%"=="16" (
    set "INSTALLER_NAME=%VMWARE_16_NAME%"
    set "DOWNLOAD_URL=%VMWARE_16_URL%"
) else if "%VMWARE_VERSION%"=="17" (
    set "INSTALLER_NAME=%VMWARE_17_NAME%"
    set "DOWNLOAD_URL=%VMWARE_17_URL%"
) else if "%VMWARE_VERSION%"=="25H2" (
    set "INSTALLER_NAME=%VMWARE_25H2_NAME%"
    set "DOWNLOAD_URL=%VMWARE_25H2_URL%"
)

if "%SILENT_MODE%"=="1" (
    set "DOWNLOAD_CHOICE=1"
    goto :download_method_selected
)

echo.
echo %COLOR_WHITE%获取 VMware 安装包的方式:%COLOR_RESET%
echo.
echo   %COLOR_CYAN%[1]%COLOR_RESET% 自动下载 (从 VMware 官网)
echo   %COLOR_CYAN%[2]%COLOR_RESET% 手动指定本地文件路径
echo.
set /p "DOWNLOAD_CHOICE=请选择 [1-2, 默认: 1]: "
if "%DOWNLOAD_CHOICE%"=="" set "DOWNLOAD_CHOICE=1"

:download_method_selected
if "%DOWNLOAD_CHOICE%"=="1" (
    set "DOWNLOAD_DIR=%TEMP%\vmware-installer"
    if not exist "!DOWNLOAD_DIR!" mkdir "!DOWNLOAD_DIR!"
    set "INSTALLER_PATH=!DOWNLOAD_DIR!\%INSTALLER_NAME%"
    
    if exist "!INSTALLER_PATH!" (
        echo %COLOR_YELLOW%⚠%COLOR_RESET% 发现已存在的安装包
        if "%SILENT_MODE%"=="0" (
            set /p "REDOWNLOAD=是否重新下载? (y/N): "
            if /i "!REDOWNLOAD!"=="y" del "!INSTALLER_PATH!"
        )
    )
    
    if not exist "!INSTALLER_PATH!" (
        echo %COLOR_BLUE%ℹ%COLOR_RESET% 开始下载 VMware Workstation %VMWARE_VERSION%...
        echo   文件名: %INSTALLER_NAME%
        echo   下载地址: %DOWNLOAD_URL%
        echo.
        echo %COLOR_YELLOW%⚠%COLOR_RESET% 文件较大（约 600MB），请耐心等待...
        echo.
        
        :: 使用 PowerShell 下载
        powershell -Command "& {$ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '!INSTALLER_PATH!' -UseBasicParsing; exit 0 } catch { Write-Host 'Download failed:' $_.Exception.Message; exit 1 }}"
        
        if errorlevel 1 (
            echo %COLOR_RED%✗ 下载失败%COLOR_RESET%
            echo 请检查网络连接或手动下载后使用选项 2
            pause
            exit /b 1
        )
        
        echo %COLOR_GREEN%✓%COLOR_RESET% 下载完成
    ) else (
        echo %COLOR_GREEN%✓%COLOR_RESET% 使用已存在的安装包
    )
) else if "%DOWNLOAD_CHOICE%"=="2" (
    echo.
    echo %COLOR_YELLOW%请提供 VMware Workstation 安装包路径%COLOR_RESET%
    echo %COLOR_BLUE%提示: 请从 VMware 官网下载对应的 .exe 文件%COLOR_RESET%
    echo %COLOR_BLUE%下载地址: https://www.vmware.com/products/workstation-pro/workstation-pro-evaluation.html%COLOR_RESET%
    echo.
    set /p "INSTALLER_PATH=请输入 .exe 文件的完整路径: "
    
    if not exist "!INSTALLER_PATH!" (
        echo %COLOR_RED%✗ 文件不存在: !INSTALLER_PATH!%COLOR_RESET%
        pause
        exit /b 1
    )
    
    echo %COLOR_GREEN%✓%COLOR_RESET% 使用本地安装包: !INSTALLER_PATH!
) else (
    echo %COLOR_RED%✗ 无效的选项: %DOWNLOAD_CHOICE%%COLOR_RESET%
    pause
    exit /b 1
)

exit /b 0

:install_vmware
call :print_step "安装 VMware Workstation"

:: 检查是否已安装
set "VMWARE_INSTALLED=0"
reg query "HKLM\SOFTWARE\VMware, Inc.\VMware Workstation" /v InstallPath >nul 2>&1
if %errorlevel%==0 (
    set "VMWARE_INSTALLED=1"
    for /f "tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\VMware, Inc.\VMware Workstation" /v InstallPath 2^>nul') do set "VMWARE_PATH=%%b"
    echo %COLOR_YELLOW%⚠%COLOR_RESET% 检测到已安装的 VMware Workstation
    echo   安装路径: !VMWARE_PATH!
    
    if "%FORCE_INSTALL%"=="0" (
        if "%SILENT_MODE%"=="0" (
            echo.
            set /p "CONTINUE_INSTALL=是否继续安装? (y/N): "
            if /i not "!CONTINUE_INSTALL!"=="y" (
                echo %COLOR_BLUE%ℹ%COLOR_RESET% 跳过 VMware 安装
                goto :install_done
            )
        ) else (
            echo %COLOR_BLUE%ℹ%COLOR_RESET% 跳过 VMware 安装（已安装）
            goto :install_done
        )
    )
)

echo %COLOR_BLUE%ℹ%COLOR_RESET% 准备安装 VMware Workstation...
echo %COLOR_BLUE%ℹ%COLOR_RESET% 安装参数: /s /v/qn EULAS_AGREED=1 SERIALNUMBER="" AUTOSOFTWAREUPDATE=0
echo.
echo %COLOR_YELLOW%⚠%COLOR_RESET% 安装过程可能需要 5-10 分钟，请耐心等待...
echo.

:: 静默安装 VMware Workstation
"%INSTALLER_PATH%" /s /v/qn EULAS_AGREED=1 SERIALNUMBER="" AUTOSOFTWAREUPDATE=0

if errorlevel 1 (
    echo %COLOR_RED%✗ VMware Workstation 安装失败%COLOR_RESET%
    pause
    exit /b 1
)

:: 等待安装完成
echo %COLOR_BLUE%ℹ%COLOR_RESET% 等待安装完成...
timeout /t 30 /nobreak >nul

:: 验证安装
reg query "HKLM\SOFTWARE\VMware, Inc.\VMware Workstation" /v InstallPath >nul 2>&1
if errorlevel 1 (
    echo %COLOR_RED%✗ 安装验证失败%COLOR_RESET%
    pause
    exit /b 1
)

:install_done
for /f "tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\VMware, Inc.\VMware Workstation" /v InstallPath 2^>nul') do set "VMWARE_PATH=%%b"
echo %COLOR_GREEN%✓%COLOR_RESET% VMware Workstation 安装完成
echo   安装路径: %VMWARE_PATH%

exit /b 0

:configure_vmrest
call :print_step "配置 vmrest API"

:: 查找 vmrest.exe
set "VMREST_PATH="
if exist "%VMWARE_PATH%vmrest.exe" (
    set "VMREST_PATH=%VMWARE_PATH%vmrest.exe"
) else if exist "C:\Program Files (x86)\VMware\VMware Workstation\vmrest.exe" (
    set "VMREST_PATH=C:\Program Files (x86)\VMware\VMware Workstation\vmrest.exe"
) else if exist "C:\Program Files\VMware\VMware Workstation\vmrest.exe" (
    set "VMREST_PATH=C:\Program Files\VMware\VMware Workstation\vmrest.exe"
)

if "%VMREST_PATH%"=="" (
    echo %COLOR_RED%✗ 无法找到 vmrest.exe%COLOR_RESET%
    pause
    exit /b 1
)

echo %COLOR_GREEN%✓%COLOR_RESET% 找到 vmrest: %VMREST_PATH%

:: 设置 vmrest 凭据
echo.
if "%SILENT_MODE%"=="1" (
    set "VMREST_USER=admin"
    set "VMREST_PASS=Admin@123"
    set "VMREST_PORT=8697"
    set "VMREST_HOST=0.0.0.0"
) else (
    set /p "VMREST_USER=请输入 vmrest API 用户名 [默认: admin]: "
    if "!VMREST_USER!"=="" set "VMREST_USER=admin"
    
    powershell -Command "$pass = Read-Host '请输入 vmrest API 密码' -AsSecureString; $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass); [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)" > "%TEMP%\vmrest_pass.tmp"
    set /p "VMREST_PASS=" < "%TEMP%\vmrest_pass.tmp"
    del "%TEMP%\vmrest_pass.tmp"
    
    if "!VMREST_PASS!"=="" (
        echo %COLOR_RED%✗ 密码不能为空%COLOR_RESET%
        pause
        exit /b 1
    )
    
    set /p "VMREST_PORT=请输入 vmrest API 监听端口 [默认: 8697]: "
    if "!VMREST_PORT!"=="" set "VMREST_PORT=8697"
    
    set /p "VMREST_HOST=请输入 vmrest API 监听地址 [默认: 0.0.0.0]: "
    if "!VMREST_HOST!"=="" set "VMREST_HOST=0.0.0.0"
)

echo %COLOR_BLUE%ℹ%COLOR_RESET% 配置 vmrest 凭据...

:: 使用 vmrest -C 命令设置凭据
echo !VMREST_PASS!| "%VMREST_PATH%" -C -u "!VMREST_USER!" >nul 2>&1

echo %COLOR_GREEN%✓%COLOR_RESET% vmrest 凭据配置完成

:: 创建 Windows 服务
echo %COLOR_BLUE%ℹ%COLOR_RESET% 创建 vmrest Windows 服务...

:: 停止并删除旧服务（如果存在）
sc query vmrest >nul 2>&1
if %errorlevel%==0 (
    net stop vmrest >nul 2>&1
    sc delete vmrest >nul 2>&1
    timeout /t 2 /nobreak >nul
)

:: 使用 NSSM 或直接创建服务
:: 这里使用 sc 命令创建服务
sc create vmrest binPath= "\"%VMREST_PATH%\" -H !VMREST_HOST! -p !VMREST_PORT!" start= auto DisplayName= "VMware Workstation REST API Service" >nul 2>&1

if errorlevel 1 (
    echo %COLOR_YELLOW%⚠%COLOR_RESET% 无法创建 Windows 服务，将使用计划任务
    
    :: 创建启动脚本
    set "STARTUP_SCRIPT=%VMWARE_PATH%start_vmrest.bat"
    echo @echo off > "!STARTUP_SCRIPT!"
    echo start "" "%VMREST_PATH%" -H !VMREST_HOST! -p !VMREST_PORT! >> "!STARTUP_SCRIPT!"
    
    :: 创建计划任务
    schtasks /create /tn "VMware REST API" /tr "!STARTUP_SCRIPT!" /sc onlogon /rl highest /f >nul 2>&1
    
    :: 立即启动
    start "" "%VMREST_PATH%" -H !VMREST_HOST! -p !VMREST_PORT!
    
    echo %COLOR_GREEN%✓%COLOR_RESET% vmrest 计划任务创建完成
) else (
    :: 启动服务
    net start vmrest >nul 2>&1
    
    if errorlevel 1 (
        echo %COLOR_YELLOW%⚠%COLOR_RESET% vmrest 服务启动失败
        echo 尝试直接启动...
        start "" "%VMREST_PATH%" -H !VMREST_HOST! -p !VMREST_PORT!
    ) else (
        echo %COLOR_GREEN%✓%COLOR_RESET% vmrest 服务启动成功
    )
)

:: 等待服务启动
timeout /t 5 /nobreak >nul

exit /b 0

:configure_firewall
call :print_step "配置防火墙"

if "%SILENT_MODE%"=="1" (
    set "CONFIG_FIREWALL=y"
) else (
    set /p "CONFIG_FIREWALL=是否配置防火墙规则? (y/N) [默认: y]: "
    if "!CONFIG_FIREWALL!"=="" set "CONFIG_FIREWALL=y"
)

if /i not "!CONFIG_FIREWALL!"=="y" (
    echo %COLOR_BLUE%ℹ%COLOR_RESET% 跳过防火墙配置
    exit /b 0
)

echo %COLOR_BLUE%ℹ%COLOR_RESET% 配置 Windows 防火墙...

:: 删除旧规则（如果存在）
netsh advfirewall firewall delete rule name="VMware REST API" >nul 2>&1

:: 添加新规则
netsh advfirewall firewall add rule name="VMware REST API" dir=in action=allow protocol=TCP localport=%VMREST_PORT% >nul 2>&1

if errorlevel 1 (
    echo %COLOR_YELLOW%⚠%COLOR_RESET% 防火墙规则添加失败
    echo 请手动配置防火墙以允许端口: %VMREST_PORT%/TCP
) else (
    echo %COLOR_GREEN%✓%COLOR_RESET% 防火墙规则已添加
)

exit /b 0

:test_vmrest_api
echo.
echo %COLOR_BLUE%ℹ%COLOR_RESET% 测试 vmrest API 连接...

:: 获取本机 IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "SERVER_ADDR=%%a"
    set "SERVER_ADDR=!SERVER_ADDR:~1!"
    goto :ip_found
)
:ip_found

if "%SERVER_ADDR%"=="" set "SERVER_ADDR=localhost"

set "TEST_URL=http://!SERVER_ADDR!:%VMREST_PORT%/api/vms"
echo   测试 URL: !TEST_URL!

:: 使用 PowerShell 测试 API
powershell -Command "& {try { $cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes('%VMREST_USER%:%VMREST_PASS%')); $headers = @{Authorization = \"Basic $cred\"}; $response = Invoke-WebRequest -Uri '%TEST_URL%' -Headers $headers -UseBasicParsing -TimeoutSec 10; if ($response.StatusCode -eq 200) { Write-Host 'SUCCESS'; exit 0 } else { Write-Host 'FAILED'; exit 1 } } catch { Write-Host 'ERROR'; exit 1 }}" > "%TEMP%\api_test.tmp" 2>&1

set /p "API_RESULT=" < "%TEMP%\api_test.tmp"
del "%TEMP%\api_test.tmp"

if "!API_RESULT!"=="SUCCESS" (
    echo %COLOR_GREEN%✓%COLOR_RESET% vmrest API 测试成功
) else (
    echo %COLOR_YELLOW%⚠%COLOR_RESET% vmrest API 测试失败
    echo   服务可能正在启动，请稍后手动测试
)

exit /b 0

:show_summary
call :print_title "✓ 安装完成！配置信息汇总"

echo %COLOR_GREEN%✓ VMware Workstation 已成功安装并配置完成！%COLOR_RESET%
echo.

call :print_line "═"
echo %COLOR_WHITE%系统信息%COLOR_RESET%
call :print_line "─"
echo   操作系统:          !OS_NAME!
echo   VMware 版本:       VMware Workstation %VMWARE_VERSION%
echo   vmrest 路径:       %VMREST_PATH%
call :print_line "═"
echo.

call :print_line "═"
echo %COLOR_WHITE%【服务器基本配置】%COLOR_RESET%
call :print_line "─"
echo   服务器名称:        %COLOR_YELLOW%^<请自定义^>%COLOR_RESET% %COLOR_BLUE%(自定义一个易识别的名称)%COLOR_RESET%
echo   服务器类型:        %COLOR_GREEN%vmware%COLOR_RESET% %COLOR_BLUE%(固定值)%COLOR_RESET%
echo   服务器地址:        %COLOR_GREEN%!SERVER_ADDR!%COLOR_RESET% %COLOR_BLUE%(本机IP地址)%COLOR_RESET%
echo   服务器端口:        %COLOR_GREEN%!VMREST_PORT!%COLOR_RESET% %COLOR_BLUE%(vmrest API端口)%COLOR_RESET%
echo   用户名:            %COLOR_GREEN%!VMREST_USER!%COLOR_RESET% %COLOR_BLUE%(API认证用户名)%COLOR_RESET%
echo   密码:              %COLOR_YELLOW%********%COLOR_RESET% %COLOR_BLUE%(您设置的密码)%COLOR_RESET%
call :print_line "═"
echo.

call :print_line "═"
echo %COLOR_WHITE%【API 端点】%COLOR_RESET%
call :print_line "─"
echo   虚拟机列表:
echo     http://!SERVER_ADDR!:!VMREST_PORT!/api/vms
echo.
echo   网络列表:
echo     http://!SERVER_ADDR!:!VMREST_PORT!/api/vmnets
echo.
echo   API 文档:
echo     http://!SERVER_ADDR!:!VMREST_PORT!/api/swagger
call :print_line "═"
echo.

call :print_line "═"
echo %COLOR_WHITE%【测试命令 (PowerShell)】%COLOR_RESET%
call :print_line "─"
echo   # 列出所有虚拟机
echo   $cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes('!VMREST_USER!:!VMREST_PASS!'))
echo   Invoke-RestMethod -Uri "http://!SERVER_ADDR!:!VMREST_PORT!/api/vms" -Headers @{Authorization="Basic $cred"}
call :print_line "═"
echo.

call :print_line "═"
echo %COLOR_WHITE%【服务管理命令】%COLOR_RESET%
call :print_line "─"
echo   启动服务:   net start vmrest
echo   停止服务:   net stop vmrest
echo   查看状态:   sc query vmrest
call :print_line "═"
echo.

call :print_line "═"
echo %COLOR_WHITE%【注意事项】%COLOR_RESET%
call :print_line "─"
echo   %COLOR_GREEN%1.%COLOR_RESET% vmrest 服务已设置为开机自启动
echo   %COLOR_GREEN%2.%COLOR_RESET% 确保防火墙允许 !VMREST_PORT! 端口访问
echo   %COLOR_GREEN%3.%COLOR_RESET% 建议定期更改 API 密码以提高安全性
echo   %COLOR_GREEN%4.%COLOR_RESET% 如遇到问题，请检查 Windows 事件查看器
echo   %COLOR_GREEN%5.%COLOR_RESET% VMware 安装路径: %VMWARE_PATH%
call :print_line "═"
echo.

exit /b 0

:uninstall_vmware
call :print_title "卸载 VMware Workstation"

echo %COLOR_YELLOW%⚠ 此操作将完全卸载 VMware Workstation 及其所有数据！%COLOR_RESET%
echo.

:: 检测已安装的 VMware
set "FOUND_VMWARE=0"
reg query "HKLM\SOFTWARE\VMware, Inc.\VMware Workstation" /v InstallPath >nul 2>&1
if %errorlevel%==0 (
    set "FOUND_VMWARE=1"
    for /f "tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\VMware, Inc.\VMware Workstation" /v InstallPath 2^>nul') do set "VMWARE_PATH=%%b"
    echo   检测到已安装的 VMware Workstation
    echo   安装路径: !VMWARE_PATH!
)

if "%FOUND_VMWARE%"=="0" (
    echo %COLOR_YELLOW%⚠ 未检测到已安装的 VMware Workstation%COLOR_RESET%
    pause
    exit /b 0
)

echo.
set /p "CONFIRM=确定要继续吗? (y/N): "
if /i not "!CONFIRM!"=="y" (
    echo %COLOR_BLUE%ℹ 取消卸载操作%COLOR_RESET%
    exit /b 0
)

echo.
echo %COLOR_BLUE%ℹ%COLOR_RESET% 停止 VMware 服务...
net stop vmrest >nul 2>&1
sc delete vmrest >nul 2>&1
schtasks /delete /tn "VMware REST API" /f >nul 2>&1

echo %COLOR_BLUE%ℹ%COLOR_RESET% 卸载 VMware Workstation...

:: 查找卸载程序
set "UNINSTALLER="
if exist "!VMWARE_PATH!uninstall.exe" (
    set "UNINSTALLER=!VMWARE_PATH!uninstall.exe"
) else if exist "C:\Program Files (x86)\VMware\VMware Workstation\uninstall.exe" (
    set "UNINSTALLER=C:\Program Files (x86)\VMware\VMware Workstation\uninstall.exe"
) else if exist "C:\Program Files\VMware\VMware Workstation\uninstall.exe" (
    set "UNINSTALLER=C:\Program Files\VMware\VMware Workstation\uninstall.exe"
)

if not "%UNINSTALLER%"=="" (
    "%UNINSTALLER%" /s /v/qn
    timeout /t 30 /nobreak >nul
) else (
    echo %COLOR_YELLOW%⚠ 未找到卸载程序，尝试使用 msiexec...%COLOR_RESET%
    
    :: 从注册表获取产品代码
    for /f "tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "VMware Workstation" ^| findstr "UninstallString"') do (
        set "UNINSTALL_CMD=%%b"
        !UNINSTALL_CMD! /qn
    )
)

echo %COLOR_BLUE%ℹ%COLOR_RESET% 清理防火墙规则...
netsh advfirewall firewall delete rule name="VMware REST API" >nul 2>&1

echo.
echo %COLOR_GREEN%✓ VMware Workstation 卸载完成！%COLOR_RESET%
pause
exit /b 0
