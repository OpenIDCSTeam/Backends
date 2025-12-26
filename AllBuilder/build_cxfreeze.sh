#!/bin/bash
# ============================================================================
# cx-Freeze 打包脚本 (Linux/Mac Shell版本)
# OpenIDCS Client
# ============================================================================

set -e  # 遇到错误立即退出

echo "============================================================"
echo "OpenIDCS Client - cx-Freeze 打包工具 (Linux/Mac)"
echo "============================================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3未安装"
    exit 1
fi

echo "[OK] Python已安装"
python3 --version
echo ""

# 检查cx-Freeze是否安装
if ! python3 -c "import cx_Freeze" &> /dev/null; then
    echo "[WARN] cx-Freeze未安装"
    echo ""
    read -p "是否安装cx-Freeze? (y/n): " install
    if [ "$install" = "y" ] || [ "$install" = "Y" ]; then
        echo "正在安装cx-Freeze..."
        python3 -m pip install cx-Freeze
        echo "[OK] cx-Freeze安装成功"
    else
        echo "取消打包"
        exit 1
    fi
else
    echo "[OK] cx-Freeze已安装"
fi
echo ""

# 清理旧的构建
if [ -d "build_cxfreeze" ]; then
    echo "清理旧的构建目录..."
    rm -rf build_cxfreeze
fi
if [ -d "dist" ]; then
    rm -rf dist
fi
echo ""

# 开始打包
echo "============================================================"
echo "开始打包..."
echo "============================================================"
echo ""

python3 setup_cxfreeze.py build

echo ""
echo "============================================================"
echo "[SUCCESS] 打包成功!"
echo "输出目录: build_cxfreeze/"
echo "============================================================"
echo ""

# 显示生成的文件
if [ -d "build_cxfreeze" ]; then
    echo "生成的文件:"
    ls -lh build_cxfreeze/ | grep -E "OpenIDCS|^d"
    echo ""
fi

# 设置可执行权限
if [ -f "build_cxfreeze/OpenIDCS-Client" ]; then
    chmod +x build_cxfreeze/OpenIDCS-Client
    echo "[OK] 已设置可执行权限"
fi
