#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
websockify 打包脚本
使用 PyInstaller 和 websockify.spec 文件将 websockify 打包成独立可执行文件

前置要求:
    - 确保 websockify.spec 文件存在于项目根目录
    - 已安装 PyInstaller: pip install pyinstaller

使用方法:
    python build_vncproxy.py

打包后的文件位置:
    dist/websocketproxy.exe (Windows)
    dist/websocketproxy (Linux/Mac)
"""

import os
import shutil
import sys
import subprocess
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, 'strict')


def build_websockify():
    """打包 websockify 为独立可执行文件"""

    # 获取项目根目录（AllBuilder 的父目录）
    project_root = Path(__file__).parent.parent.absolute()
    allbuilder_dir = Path(__file__).parent.absolute()
    build_cache_dir = project_root / "BuildCache" / "websockify"
    websockify_script = project_root / "Websockify" / "websocketproxy.py"
    websockify_dir = project_root / "Websockify"
    spec_file = allbuilder_dir / "websockify.spec"
    
    # 确保 BuildCache 目录存在
    build_cache_dir.mkdir(parents=True, exist_ok=True)

    if not websockify_script.exists():
        print(f"错误: 找不到 websockify 脚本: {websockify_script}")
        return False

    if not spec_file.exists():
        print(f"错误: 找不到 spec 文件: {spec_file}")
        print("请确保 websockify.spec 文件存在于项目根目录")
        return False

    print(f"项目根目录: {project_root}")
    print(f"构建缓存目录: {build_cache_dir}")
    print(f"websockify 脚本: {websockify_script}")
    print(f"websockify 模块目录: {websockify_dir}")
    print(f"spec 文件: {spec_file}")
    print("-" * 60)

    # 删除 Websockify 目录下的旧 exe 文件，避免递归打包
    old_exe = websockify_dir / "websocketproxy.exe"
    if old_exe.exists():
        print(f"删除旧的 exe 文件: {old_exe}")
        old_exe.unlink()
        print("旧文件已删除")
        print("-" * 60)

    # 使用 spec 文件打包
    cmd = [
        "pyinstaller",
        "--clean",  # 清理临时文件
        "--noconfirm",  # 覆盖已存在的文件
        f"--distpath={build_cache_dir / 'dist'}",  # 指定输出目录
        f"--workpath={build_cache_dir / 'build'}",  # 指定工作目录
        str(spec_file)
    ]

    print("执行打包命令:")
    print(" ".join(cmd))
    print("-" * 60)

    try:
        # 执行打包
        result = subprocess.run(cmd, cwd=str(allbuilder_dir), check=True)

        # 检查打包结果
        if sys.platform == "win32":
            exe_path = build_cache_dir / "dist" / "websocketproxy.exe"
        else:
            exe_path = build_cache_dir / "dist" / "websocketproxy"

        if exe_path.exists():
            print("-" * 60)
            print("[SUCCESS] 打包成功!")
            print(f"可执行文件位置: {exe_path}")
            print(f"文件大小: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            # 复制到 Websockify 目录
            target_path = project_root / "Websockify" / "websocketproxy.exe"
            shutil.copy(exe_path, target_path)
            print(f"已复制到: {target_path}")
            
            # 清理临时文件（保留在BuildCache中，不删除）
            # 如果需要清理，可以手动删除 BuildCache/websockify 目录
            
            return True
        else:
            print("[ERROR] 打包失败: 找不到输出文件")
            return False

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 打包失败: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] 发生错误: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("websockify 打包工具")
    print("=" * 60)

    # 检查是否安装了 PyInstaller
    try:
        subprocess.run(["pyinstaller", "--version"],
                       capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] 未安装 PyInstaller")
        print("请先安装: pip install pyinstaller")
        sys.exit(1)

    # 执行打包
    success = build_websockify()

    if success:

        sys.exit(0)
    else:
        sys.exit(1)
