#!/bin/bash

# VMware Workstation 环境初始化脚本
# 用于安装 VMware Workstation 并配置 vmrest API
# 支持多个 Linux 发行版: Ubuntu/Debian, CentOS/RHEL/Rocky, Fedora, Arch Linux

set -e

echo "=========================================="
echo "VMware Workstation 环境初始化脚本"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "错误: 请使用 root 权限运行此脚本"
    exit 1
fi

# 检测 Linux 发行版
echo ""
echo "检测系统信息..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
    echo "检测到系统: $NAME $VERSION"
else
    echo "错误: 无法检测系统类型"
    exit 1
fi

# 确定包管理器
case "$OS" in
    ubuntu|debian)
        PKG_MANAGER="apt"
        PKG_UPDATE="apt-get update"
        PKG_INSTALL="apt-get install -y"
        ;;
    centos|rhel|rocky|almalinux)
        if command -v dnf &> /dev/null; then
            PKG_MANAGER="dnf"
            PKG_UPDATE="dnf check-update || true"
            PKG_INSTALL="dnf install -y"
        else
            PKG_MANAGER="yum"
            PKG_UPDATE="yum check-update || true"
            PKG_INSTALL="yum install -y"
        fi
        ;;
    fedora)
        PKG_MANAGER="dnf"
        PKG_UPDATE="dnf check-update || true"
        PKG_INSTALL="dnf install -y"
        ;;
    arch|manjaro)
        PKG_MANAGER="pacman"
        PKG_UPDATE="pacman -Sy"
        PKG_INSTALL="pacman -S --noconfirm"
        ;;
    *)
        echo "警告: 未识别的发行版 '$OS'，将尝试使用默认配置"
        # 尝试检测可用的包管理器
        if command -v apt-get &> /dev/null; then
            PKG_MANAGER="apt"
            PKG_UPDATE="apt-get update"
            PKG_INSTALL="apt-get install -y"
        elif command -v dnf &> /dev/null; then
            PKG_MANAGER="dnf"
            PKG_UPDATE="dnf check-update || true"
            PKG_INSTALL="dnf install -y"
        elif command -v yum &> /dev/null; then
            PKG_MANAGER="yum"
            PKG_UPDATE="yum check-update || true"
            PKG_INSTALL="yum install -y"
        elif command -v pacman &> /dev/null; then
            PKG_MANAGER="pacman"
            PKG_UPDATE="pacman -Sy"
            PKG_INSTALL="pacman -S --noconfirm"
        else
            echo "错误: 无法检测到支持的包管理器"
            exit 1
        fi
        ;;
esac

echo "使用包管理器: $PKG_MANAGER"

# 1. 安装依赖包
echo ""
echo "[1/7] 安装依赖包..."

case "$OS" in
    ubuntu|debian)
        echo "在 Ubuntu/Debian 上安装依赖..."
        $PKG_UPDATE
        $PKG_INSTALL \
            build-essential \
            linux-headers-$(uname -r) \
            gcc \
            make \
            perl \
            wget \
            curl \
            ca-certificates
        ;;
        
    centos|rhel|rocky|almalinux)
        echo "在 CentOS/RHEL/Rocky 上安装依赖..."
        $PKG_INSTALL \
            kernel-headers \
            kernel-devel \
            gcc \
            make \
            perl \
            wget \
            curl \
            ca-certificates
        ;;
        
    fedora)
        echo "在 Fedora 上安装依赖..."
        $PKG_INSTALL \
            kernel-headers \
            kernel-devel \
            gcc \
            make \
            perl \
            wget \
            curl \
            ca-certificates
        ;;
        
    arch|manjaro)
        echo "在 Arch Linux 上安装依赖..."
        $PKG_INSTALL \
            linux-headers \
            gcc \
            make \
            perl \
            wget \
            curl \
            ca-certificates
        ;;
        
    *)
        echo "警告: 未知发行版，跳过依赖安装"
        ;;
esac

echo "依赖包安装完成"

# 2. 检查并安装 VMware Workstation
echo ""
echo "[2/7] 检查 VMware Workstation..."

VMWARE_INSTALLED=false
VMWARE_VERSION=""

# 检查 VMware 是否已安装
if command -v vmware &> /dev/null; then
    VMWARE_INSTALLED=true
    VMWARE_VERSION=$(vmware --version 2>/dev/null || echo "未知版本")
    echo "VMware Workstation 已安装: $VMWARE_VERSION"
else
    echo "VMware Workstation 未安装"
    
    read -p "是否需要安装 VMware Workstation? (y/n, 默认: y): " INSTALL_VMWARE
    INSTALL_VMWARE=${INSTALL_VMWARE:-y}
    
    if [ "$INSTALL_VMWARE" = "y" ]; then
        echo ""
        echo "请提供 VMware Workstation 安装包路径"
        echo "注意: 请从 VMware 官网下载对应的 .bundle 文件"
        echo "下载地址: https://www.vmware.com/products/workstation-pro/workstation-pro-evaluation.html"
        echo ""
        
        read -p "请输入 VMware Workstation .bundle 文件的完整路径: " VMWARE_BUNDLE
        
        if [ ! -f "$VMWARE_BUNDLE" ]; then
            echo "错误: 文件不存在: $VMWARE_BUNDLE"
            echo "请下载 VMware Workstation 安装包后重新运行此脚本"
            exit 1
        fi
        
        echo "开始安装 VMware Workstation..."
        chmod +x "$VMWARE_BUNDLE"
        
        # 静默安装 VMware Workstation
        "$VMWARE_BUNDLE" --console --required --eulas-agreed
        
        if [ $? -eq 0 ]; then
            echo "VMware Workstation 安装完成"
            VMWARE_INSTALLED=true
            VMWARE_VERSION=$(vmware --version 2>/dev/null || echo "未知版本")
        else
            echo "错误: VMware Workstation 安装失败"
            exit 1
        fi
    else
        echo "跳过 VMware Workstation 安装"
        echo "注意: 需要手动安装 VMware Workstation 才能继续配置"
        exit 1
    fi
fi

# 3. 配置 vmrest API
echo ""
echo "[3/7] 配置 vmrest API..."

# 检查 vmrest 是否存在
VMREST_PATH=""
if command -v vmrest &> /dev/null; then
    VMREST_PATH=$(which vmrest)
elif [ -f "/usr/bin/vmrest" ]; then
    VMREST_PATH="/usr/bin/vmrest"
elif [ -f "/usr/local/bin/vmrest" ]; then
    VMREST_PATH="/usr/local/bin/vmrest"
else
    echo "警告: 未找到 vmrest 命令"
    echo "尝试在常见位置查找..."
    
    # 在 VMware 安装目录中查找
    for dir in /usr/lib/vmware /opt/vmware /usr/local/lib/vmware; do
        if [ -f "$dir/vmrest" ]; then
            VMREST_PATH="$dir/vmrest"
            break
        fi
    done
    
    if [ -z "$VMREST_PATH" ]; then
        echo "错误: 无法找到 vmrest，请确认 VMware Workstation 安装正确"
        exit 1
    fi
fi

echo "找到 vmrest: $VMREST_PATH"

# 4. 设置 vmrest 用户名和密码
echo ""
echo "[4/7] 设置 vmrest 用户名和密码..."

read -p "请输入 vmrest API 用户名 (默认: admin): " VMREST_USER
VMREST_USER=${VMREST_USER:-admin}

read -sp "请输入 vmrest API 密码: " VMREST_PASS
echo ""

if [ -z "$VMREST_PASS" ]; then
    echo "错误: 密码不能为空"
    exit 1
fi

read -sp "请再次输入密码确认: " VMREST_PASS_CONFIRM
echo ""

if [ "$VMREST_PASS" != "$VMREST_PASS_CONFIRM" ]; then
    echo "错误: 两次输入的密码不一致"
    exit 1
fi

# 创建 vmrest 配置目录
VMREST_CONFIG_DIR="/etc/vmware/vmrest"
mkdir -p "$VMREST_CONFIG_DIR"

# 设置 vmrest 凭据
echo "配置 vmrest 凭据..."

# 使用 vmrest -C 命令设置凭据
echo "$VMREST_PASS" | "$VMREST_PATH" -C -u "$VMREST_USER" 2>/dev/null || {
    echo "警告: vmrest -C 命令执行失败，尝试手动配置..."
    
    # 手动创建配置文件
    VMREST_CRED_FILE="$VMREST_CONFIG_DIR/credentials"
    
    # 生成密码哈希（使用 openssl）
    PASS_HASH=$(echo -n "$VMREST_PASS" | openssl dgst -sha256 | awk '{print $2}')
    
    # 创建凭据文件
    cat > "$VMREST_CRED_FILE" << EOF
{
  "username": "$VMREST_USER",
  "password": "$PASS_HASH"
}
EOF
    
    chmod 600 "$VMREST_CRED_FILE"
}

echo "vmrest 凭据配置完成"

# 5. 配置 vmrest 服务
echo ""
echo "[5/7] 配置 vmrest 服务..."

# 读取端口配置
read -p "请输入 vmrest API 监听端口 (默认: 8697): " VMREST_PORT
VMREST_PORT=${VMREST_PORT:-8697}

# 读取监听地址
read -p "请输入 vmrest API 监听地址 (默认: 0.0.0.0): " VMREST_HOST
VMREST_HOST=${VMREST_HOST:-0.0.0.0}

# 创建 systemd 服务文件
echo "创建 vmrest systemd 服务..."

cat > /etc/systemd/system/vmrest.service << EOF
[Unit]
Description=VMware Workstation REST API Service
After=network.target vmware.service

[Service]
Type=simple
User=root
ExecStart=$VMREST_PATH -H $VMREST_HOST -p $VMREST_PORT
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd
systemctl daemon-reload

# 启动并启用 vmrest 服务
echo "启动 vmrest 服务..."
systemctl enable vmrest.service
systemctl start vmrest.service

# 检查服务状态
sleep 2
if systemctl is-active --quiet vmrest.service; then
    echo "✓ vmrest 服务启动成功"
else
    echo "✗ vmrest 服务启动失败"
    echo "查看日志: journalctl -u vmrest.service -n 50"
    exit 1
fi

# 6. 配置防火墙
echo ""
echo "[6/7] 配置防火墙..."

read -p "是否配置防火墙规则? (y/n, 默认: y): " CONFIG_FIREWALL
CONFIG_FIREWALL=${CONFIG_FIREWALL:-y}

if [ "$CONFIG_FIREWALL" = "y" ]; then
    FIREWALL_CONFIGURED=false
    
    # 尝试 UFW (Ubuntu/Debian)
    if command -v ufw &> /dev/null; then
        echo "配置 UFW 防火墙..."
        ufw allow $VMREST_PORT/tcp comment 'VMware REST API'
        ufw reload
        echo "UFW 防火墙规则已添加"
        FIREWALL_CONFIGURED=true
    fi
    
    # 尝试 firewalld (CentOS/RHEL/Fedora)
    if command -v firewall-cmd &> /dev/null && [ "$FIREWALL_CONFIGURED" = false ]; then
        echo "配置 firewalld..."
        firewall-cmd --permanent --add-port=$VMREST_PORT/tcp
        firewall-cmd --reload
        echo "firewalld 规则已添加"
        FIREWALL_CONFIGURED=true
    fi
    
    # 尝试 iptables (通用)
    if command -v iptables &> /dev/null && [ "$FIREWALL_CONFIGURED" = false ]; then
        echo "配置 iptables..."
        iptables -A INPUT -p tcp --dport $VMREST_PORT -j ACCEPT
        
        # 尝试保存规则
        if command -v iptables-save &> /dev/null; then
            case "$OS" in
                ubuntu|debian)
                    $PKG_INSTALL iptables-persistent
                    iptables-save > /etc/iptables/rules.v4
                    ;;
                centos|rhel|rocky|almalinux|fedora)
                    service iptables save || iptables-save > /etc/sysconfig/iptables
                    ;;
                arch|manjaro)
                    iptables-save > /etc/iptables/iptables.rules
                    systemctl enable iptables
                    ;;
            esac
        fi
        
        echo "iptables 规则已添加"
        FIREWALL_CONFIGURED=true
    fi
    
    if [ "$FIREWALL_CONFIGURED" = false ]; then
        echo "警告: 未检测到支持的防火墙工具，请手动配置防火墙"
        echo "需要开放的端口: $VMREST_PORT/tcp (VMware REST API)"
    fi
fi

# 7. 安装 Python VMware SDK (可选)
echo ""
echo "[7/7] 安装 Python VMware SDK (可选)..."

read -p "是否安装 Python VMware SDK? (y/n, 默认: y): " INSTALL_SDK
INSTALL_SDK=${INSTALL_SDK:-y}

if [ "$INSTALL_SDK" = "y" ]; then
    # 检测 Python 和 pip
    PYTHON_CMD=""
    PIP_CMD=""
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        if command -v pip3 &> /dev/null; then
            PIP_CMD="pip3"
        fi
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        if command -v pip &> /dev/null; then
            PIP_CMD="pip"
        fi
    fi
    
    if [ -z "$PYTHON_CMD" ]; then
        echo "Python 未安装，正在安装..."
        case "$OS" in
            ubuntu|debian)
                $PKG_INSTALL python3 python3-pip
                PIP_CMD="pip3"
                ;;
            centos|rhel|rocky|almalinux)
                $PKG_INSTALL python3 python3-pip
                PIP_CMD="pip3"
                ;;
            fedora)
                $PKG_INSTALL python3 python3-pip
                PIP_CMD="pip3"
                ;;
            arch|manjaro)
                $PKG_INSTALL python python-pip
                PIP_CMD="pip"
                ;;
            *)
                echo "警告: 无法自动安装 Python，请手动安装"
                ;;
        esac
    fi
    
    if [ -n "$PIP_CMD" ]; then
        echo "使用 $PIP_CMD 安装 VMware SDK..."
        $PIP_CMD install requests
        echo "Python VMware SDK 依赖安装完成"
    else
        echo "警告: pip 未安装，请手动安装 Python 依赖:"
        echo "  pip3 install requests"
    fi
fi

# 测试 vmrest API
echo ""
echo "测试 vmrest API 连接..."

# 等待服务完全启动
sleep 3

# 测试 API 连接
TEST_URL="http://$VMREST_HOST:$VMREST_PORT/api/vms"
echo "测试 URL: $TEST_URL"

# 使用 curl 测试（带认证）
if command -v curl &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -u "$VMREST_USER:$VMREST_PASS" "$TEST_URL" 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✓ vmrest API 测试成功 (HTTP $HTTP_CODE)"
    elif [ "$HTTP_CODE" = "401" ]; then
        echo "✗ vmrest API 认证失败 (HTTP $HTTP_CODE)"
        echo "  请检查用户名和密码是否正确"
    else
        echo "⚠ vmrest API 响应异常 (HTTP $HTTP_CODE)"
        echo "  服务可能正在启动，请稍后手动测试"
    fi
else
    echo "警告: curl 未安装，无法测试 API 连接"
fi

# 完成
echo ""
echo "=========================================="
echo "VMware Workstation 环境初始化完成！"
echo "=========================================="
echo ""
echo "系统信息:"
echo "  - 操作系统: $NAME $VERSION"
echo "  - VMware 版本: $VMWARE_VERSION"
echo "  - vmrest 路径: $VMREST_PATH"
echo ""
echo "配置信息:"
echo "  - API 地址: http://$(hostname -I | awk '{print $1}'):$VMREST_PORT"
echo "  - 监听地址: $VMREST_HOST"
echo "  - 监听端口: $VMREST_PORT"
echo "  - 用户名: $VMREST_USER"
echo "  - 密码: ********"
echo "  - 配置目录: $VMREST_CONFIG_DIR"
echo ""
echo "服务状态:"
systemctl status vmrest.service --no-pager -l | head -n 10
echo ""
echo "API 端点:"
echo "  - 虚拟机列表: http://$(hostname -I | awk '{print $1}'):$VMREST_PORT/api/vms"
echo "  - 网络列表: http://$(hostname -I | awk '{print $1}'):$VMREST_PORT/api/vmnets"
echo "  - API 文档: http://$(hostname -I | awk '{print $1}'):$VMREST_PORT/api/swagger"
echo ""
echo "测试命令:"
echo "  # 列出所有虚拟机"
echo "  curl -u $VMREST_USER:$VMREST_PASS http://$(hostname -I | awk '{print $1}'):$VMREST_PORT/api/vms"
echo ""
echo "  # 获取虚拟机详情"
echo "  curl -u $VMREST_USER:$VMREST_PASS http://$(hostname -I | awk '{print $1}'):$VMREST_PORT/api/vms/{vm_id}"
echo ""
echo "  # 启动虚拟机"
echo "  curl -X PUT -u $VMREST_USER:$VMREST_PASS http://$(hostname -I | awk '{print $1}'):$VMREST_PORT/api/vms/{vm_id}/power -d 'on'"
echo ""
echo "Python 客户端配置 (HSConfig):"
echo "  - server_type: 'vmware'"
echo "  - server_addr: '$(hostname -I | awk '{print $1}')'"
echo "  - server_port: $VMREST_PORT"
echo "  - username: '$VMREST_USER'"
echo "  - password: '********'"
echo ""
echo "注意事项:"
echo "  1. vmrest 服务已设置为开机自启动"
echo "  2. 确保防火墙允许 $VMREST_PORT 端口访问"
echo "  3. 建议定期更改 API 密码以提高安全性"
echo "  4. 如需修改配置，请编辑 /etc/systemd/system/vmrest.service"
echo "  5. 查看服务日志: journalctl -u vmrest.service -f"
echo ""
echo "管理命令:"
echo "  - 启动服务: systemctl start vmrest.service"
echo "  - 停止服务: systemctl stop vmrest.service"
echo "  - 重启服务: systemctl restart vmrest.service"
echo "  - 查看状态: systemctl status vmrest.service"
echo "  - 查看日志: journalctl -u vmrest.service -n 50"
echo ""
echo "=========================================="
