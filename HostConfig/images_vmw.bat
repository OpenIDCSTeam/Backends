@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "API_URL=https://shared.pika.net.cn/api/fs/list"
set "API_PATH=/Mirrors/OSImages/PikaCloudOS/VmwareOS"
set "DOWNLOAD_BASE_URL=https://shared.pika.net.cn/d"
set "STORAGE_PATH="
set "TEMP_JSON=%TEMP%\vmw_images.json"
set "TEMP_LIST=%TEMP%\vmw_list.txt"

:main_menu
cls
echo ================================
echo     VMware 镜像下载脚本
echo    OpenIDCS by PikaCloud
echo ================================
echo 1. 设置存储路径
echo 2. 下载镜像
echo 3. 查看镜像列表
echo 0. 退出
echo ================================
if defined STORAGE_PATH (
    echo [信息] 当前存储路径: !STORAGE_PATH!
) else (
    echo [警告] 未设置存储路径
)
echo ================================
set /p "choice=请选择 [0-3]: "

if "%choice%"=="1" goto set_storage_path
if "%choice%"=="2" goto menu_download
if "%choice%"=="3" goto menu_list
if "%choice%"=="0" goto exit_script
echo [错误] 无效选择
pause
goto main_menu

:set_storage_path
cls
echo ================================
echo     设置镜像存储路径
echo ================================
if defined STORAGE_PATH (
    echo [信息] 当前存储路径: !STORAGE_PATH!
    set /p "change=是否更改？(y/n) [n]: "
    if /i not "!change!"=="y" goto main_menu
)

set /p "new_path=请输入镜像存储路径: "
if "!new_path!"=="" (
    echo [错误] 路径不能为空
    pause
    goto main_menu
)

if not exist "!new_path!" (
    set /p "create=目录不存在，是否创建？(y/n) [y]: "
    if "!create!"=="" set "create=y"
    if /i "!create!"=="y" (
        mkdir "!new_path!" 2>nul
        if errorlevel 1 (
            echo [错误] 目录创建失败
            pause
            goto main_menu
        )
        echo [成功] 目录创建成功
    ) else (
        goto main_menu
    )
)

set "STORAGE_PATH=!new_path!"
echo [成功] 存储路径已设置: !STORAGE_PATH!
pause
goto main_menu

:menu_download
if not defined STORAGE_PATH (
    echo [警告] 请先设置镜像存储路径
    pause
    goto set_storage_path
)

cls
echo ================================
echo        下载镜像
echo ================================
echo [信息] 正在获取镜像列表...

call :fetch_image_list
if errorlevel 1 (
    pause
    goto main_menu
)

call :show_image_list

set /p "image_choices=输入编号，多个用逗号分隔，或 all 全部下载: "
if "!image_choices!"=="" (
    echo [警告] 未选择任何镜像
    pause
    goto main_menu
)

set "selected_count=0"
set "selected_list="

if /i "!image_choices!"=="all" (
    for /f "tokens=1,* delims=:" %%a in ('type "!TEMP_LIST!"') do (
        set /a selected_count+=1
        set "selected_list=!selected_list! %%a"
    )
) else (
    for %%i in (!image_choices:,= !) do (
        set "idx=%%i"
        set "idx=!idx: =!"
        findstr /b "!idx!:" "!TEMP_LIST!" >nul 2>&1
        if !errorlevel! equ 0 (
            set /a selected_count+=1
            set "selected_list=!selected_list! !idx!"
        ) else (
            echo [警告] 无效的编号: !idx!
        )
    )
)

if !selected_count! equ 0 (
    echo [警告] 未选择任何有效镜像
    pause
    goto main_menu
)

echo [成功] 已选择 !selected_count! 个镜像
echo.

set "current=0"
set "success=0"
set "failed=0"

for %%i in (!selected_list!) do (
    set /a current+=1
    echo [!current!/!selected_count!]
    
    for /f "tokens=1,* delims=:" %%a in ('findstr /b "%%i:" "!TEMP_LIST!"') do (
        set "image_name=%%b"
        call :download_image "!image_name!"
        if !errorlevel! equ 0 (
            set /a success+=1
        ) else (
            set /a failed+=1
        )
    )
    echo.
)

echo [成功] 下载完成: 成功 !success! 个, 失败 !failed! 个
pause
goto main_menu

:menu_list
cls
echo ================================
echo      刷新镜像列表
echo ================================
echo [信息] 正在获取镜像列表...

call :fetch_image_list
if errorlevel 1 (
    pause
    goto main_menu
)

call :show_image_list
pause
goto main_menu

:fetch_image_list
set "json_data={\"path\":\"%API_PATH%\",\"password\":\"\",\"page\":1,\"per_page\":0,\"refresh\":true}"

curl -s -X POST "%API_URL%" -H "Content-Type: application/json" -d "%json_data%" -o "%TEMP_JSON%" 2>nul
if errorlevel 1 (
    echo [错误] 无法连接到服务器
    exit /b 1
)

findstr /c:"\"code\":200" "%TEMP_JSON%" >nul 2>&1
if errorlevel 1 (
    echo [错误] 获取镜像列表失败
    exit /b 1
)

if exist "%TEMP_LIST%" del "%TEMP_LIST%"

set "idx=0"
for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command "$json = Get-Content '%TEMP_JSON%' -Raw | ConvertFrom-Json; $json.data.content | Where-Object { $_.name -like '*img.rar' } | ForEach-Object { $_.name + '|' + $_.size }"`) do (
    set /a idx+=1
    echo !idx!:%%a >> "%TEMP_LIST%"
)

if !idx! equ 0 (
    echo [警告] 未找到可用的镜像文件
    exit /b 1
)

echo [成功] 找到 !idx! 个镜像文件
exit /b 0

:show_image_list
echo.
echo ============================================================================================================
set "idx=0"
for /f "tokens=1,2,3 delims=:|" %%a in ('type "%TEMP_LIST%"') do (
    set /a idx+=1
    set "name=%%b"
    set "size=%%c"
    call :format_size !size! size_str
    echo  !idx!^) !name! [!size_str!]
)
echo ============================================================================================================
echo.
exit /b 0

:format_size
set "size=%~1"
set "result="

if !size! lss 1024 (
    set "result=!size!B"
) else if !size! lss 1048576 (
    set /a kb=!size!/1024
    set "result=!kb!KB"
) else if !size! lss 1073741824 (
    set /a mb=!size!/1048576
    set "result=!mb!MB"
) else (
    set /a gb=!size!/1073741824
    set "result=!gb!GB"
)

set "%~2=!result!"
exit /b 0

:download_image
set "image_name=%~1"
set "download_url=%DOWNLOAD_BASE_URL%%API_PATH%/%image_name%"
set "output_file=%STORAGE_PATH%\%image_name%"

echo [信息] 下载: !image_name!
echo [信息] URL: !download_url!

if exist "!output_file!" (
    echo [警告] 文件已存在: !output_file!
    set /p "overwrite=是否覆盖？(y/n) [n]: "
    if /i not "!overwrite!"=="y" (
        echo [信息] 跳过下载
        exit /b 0
    )
)

curl -L --progress-bar -o "!output_file!" "!download_url!" 2>nul
if errorlevel 1 (
    echo [错误] 下载失败: !image_name!
    if exist "!output_file!" del "!output_file!"
    exit /b 1
)

echo [成功] 下载完成: !output_file!
exit /b 0

:exit_script
if exist "%TEMP_JSON%" del "%TEMP_JSON%"
if exist "%TEMP_LIST%" del "%TEMP_LIST%"
echo [成功] 退出
exit /b 0
