#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cx-Freeze打包脚本 - OpenIDCS Client
使用cx-Freeze将Flask应用打包成独立可执行文件
"""

import sys
import os
from cx_Freeze import setup, Executable

# 项目配置
PROJECT_NAME = "OpenIDCS-Client"
PROJECT_VERSION = "1.0.0"
PROJECT_DESCRIPTION = "OpenIDCS Flask Server - 虚拟机管理平台"
PROJECT_AUTHOR = "OpenIDCS Team"

# 项目根目录
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# 主脚本
MAIN_SCRIPT = "HostServer.py"

# 图标文件
ICON_FILE = os.path.join(PROJECT_ROOT, "../HostConfig/HostManage.ico")

# ============================================================================
# 需要包含的包和模块
# ============================================================================

# 核心依赖包（基于 requirements.txt）
PACKAGES = [
    # Web框架
    "flask",
    "werkzeug",
    "jinja2",
    "click",
    "itsdangerous",
    "markupsafe",
    
    # 日志
    "loguru",
    
    # HTTP请求
    "requests",
    "urllib3",
    "certifi",
    "charset_normalizer",
    "idna",
    
    # 系统监控
    "psutil",
    "GPUtil",
    "cpuinfo",
    
    # 压缩工具
    "py7zr",
    
    # 数据库
    "sqlite3",
    
    # 邮件
    "email",
    "smtplib",
    
    # 标准库（这些通常会自动包含，但显式列出以确保）
    "encodings",  # 必需：Python 编码支持
    "encodings.utf_8",
    "encodings.ascii",
    "encodings.latin_1",
    "encodings.idna",
    "json",
    "threading",
    "traceback",
    "secrets",
    "functools",
    "hashlib",
    "base64",
    "datetime",
    "pathlib",
    "shutil",
    "subprocess",
    "multiprocessing",
    "os",
    "sys",
    "re",
    "time",
    "socket",
    "ssl",
    "collections",
    "io",
    "typing",
    
    # 项目模块
    "HostModule",
    "HostServer",
    "MainObject",
    "VNCConsole",
    "Websockify",
]

# 可选包（如果已安装则包含，基于 requirements.txt）
OPTIONAL_PACKAGES = [
    "pyvmomi",    # VMware vSphere 支持
    "pylxd",      # LXD 容器支持
    "docker",     # Docker 容器支持
    "pywin32",    # Windows API（仅Windows）
    "pythonnet",  # Windows .NET 支持（仅Windows）
]

# 需要排除的包（减小体积）
EXCLUDES = [
    "tkinter",
    "test",
    "unittest",
    "setuptools",
    "pip",
    "wheel",
    "distutils",
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "sphinx",
]

# ============================================================================
# 需要包含的数据文件和目录
# ============================================================================

INCLUDE_FILES = [
    # Web模板和静态文件
    ("WebDesigns", "WebDesigns"),
    ("static", "static") if os.path.exists("static") else None,
    
    # VNC控制台
    ("VNCConsole/Sources", "VNCConsole/Sources"),
    
    # Websockify 二进制文件
    ("Websockify/websocketproxy.exe", "Websockify/websocketproxy.exe"),
    
    # 配置文件和工具
    ("HostConfig", "HostConfig"),
    
    # 数据库初始化脚本
    ("HostConfig/HostManage.sql", "HostConfig/HostManage.sql"),
]

# 过滤掉None值（不存在的文件）
INCLUDE_FILES = [f for f in INCLUDE_FILES if f is not None]

# ============================================================================
# 检查可选包是否已安装
# ============================================================================

def check_package_installed(package_name):
    """检查包是否已安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

# 添加已安装的可选包
installed_optional = []
for package in OPTIONAL_PACKAGES:
    if check_package_installed(package):
        PACKAGES.append(package)
        installed_optional.append(package)
        print(f"[INFO] 包含可选包: {package}")

# ============================================================================
# cx-Freeze构建选项
# ============================================================================

build_exe_options = {
    # 包含的包
    "packages": PACKAGES,
    
    # 排除的包
    "excludes": EXCLUDES,
    
    # 包含的文件
    "include_files": INCLUDE_FILES,
    
    # 优化级别（0=无优化，1=基本优化，2=完全优化）
    "optimize": 2,
    
    # 包含所有依赖的DLL
    "include_msvcr": True,
    
    # 构建目录（挪到上级目录的 BuildCache 下）
    "build_exe": os.path.join(PROJECT_ROOT, "..", "BuildCache", "cxfreeze"),
    
    # 确保 encodings 和资源目录不被压缩到 zip
    "zip_include_packages": "*",
    "zip_exclude_packages": ["encodings", "VNCConsole", "Websockify"],
    
    # 静默模式（不显示警告）
    # "silent": True,
}

# ============================================================================
# 可执行文件配置
# ============================================================================

# Windows平台特定配置
if sys.platform == "win32":
    base = None  # "Win32GUI" 表示无控制台窗口，None 表示有控制台窗口
    
    executables = [
        Executable(
            script=MAIN_SCRIPT,
            base=base,
            target_name=f"{PROJECT_NAME}.exe",
            icon=ICON_FILE if os.path.exists(ICON_FILE) else None,
            # 版权信息
            copyright=f"Copyright (C) 2024 {PROJECT_AUTHOR}",
            # 快捷方式名称
            shortcut_name=PROJECT_NAME,
            # 快捷方式目录
            shortcut_dir="DesktopFolder",
        )
    ]
else:
    # Linux/Mac平台
    executables = [
        Executable(
            script=MAIN_SCRIPT,
            target_name=PROJECT_NAME,
        )
    ]

# ============================================================================
# setup配置
# ============================================================================

setup(
    name=PROJECT_NAME,
    version=PROJECT_VERSION,
    description=PROJECT_DESCRIPTION,
    author=PROJECT_AUTHOR,
    options={
        "build_exe": build_exe_options,
    },
    executables=executables,
)

# ============================================================================
# 使用说明
# ============================================================================

