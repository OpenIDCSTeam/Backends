#!/bin/bash

# Docker/Podman 环境初始化脚本
# 用于配置 Docker 容器环境、网络和 TLS 远程访问
# 支持多个 Linux 发行版: Ubuntu/Debian, CentOS/RHEL/Rocky, Fedora, Arch Linux

set -e

echo "=========================================="
echo "Docker/Podman 环境初始化脚本"
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

# 选择容器引擎
echo ""
echo "请选择要安装的容器引擎:"
echo "1) Docker"
echo "2) Podman"
read -p "请输入选项 (1 或 2, 默认: 1): " ENGINE_CHOICE
ENGINE_CHOICE=${ENGINE_CHOICE:-1}

if [ "$ENGINE_CHOICE" = "2" ]; then
    CONTAINER_ENGINE="podman"
    echo "已选择: Podman"
else
    CONTAINER_ENGINE="docker"
    echo "已选择: Docker"
fi

# 1. 安装 Docker/Podman 和依赖
echo ""
echo "[1/7] 安装 $CONTAINER_ENGINE 和依赖包..."

# 安装 Docker 的函数
install_docker() {
    case "$OS" in
        ubuntu|debian)
            echo "在 Ubuntu/Debian 上安装 Docker..."
            
            # 更新包索引
            $PKG_UPDATE
            
            # 安装依赖
            $PKG_INSTALL \
                ca-certificates \
                curl \
                gnupg \
                lsb-release
            
            # 添加 Docker 官方 GPG 密钥
            mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            
            # 设置 Docker 仓库
            echo \
              "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
              $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # 安装 Docker Engine
            $PKG_UPDATE
            $PKG_INSTALL docker-ce docker-ce-cli containerd.io docker-compose-plugin
            ;;
            
        centos|rhel|rocky|almalinux)
            echo "在 CentOS/RHEL/Rocky 上安装 Docker..."
            
            # 安装依赖
            $PKG_INSTALL yum-utils device-mapper-persistent-data lvm2
            
            # 添加 Docker 仓库
            if [ "$OS" = "centos" ]; then
                yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            else
                # RHEL/Rocky/AlmaLinux 使用 CentOS 仓库
                yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            fi
            
            # 安装 Docker Engine
            $PKG_INSTALL docker-ce docker-ce-cli containerd.io docker-compose-plugin
            ;;
            
        fedora)
            echo "在 Fedora 上安装 Docker..."
            
            # 安装依赖
            $PKG_INSTALL dnf-plugins-core
            
            # 添加 Docker 仓库
            dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
            
            # 安装 Docker Engine
            $PKG_INSTALL docker-ce docker-ce-cli containerd.io docker-compose-plugin
            ;;
            
        arch|manjaro)
            echo "在 Arch Linux 上安装 Docker..."
            
            # Arch 官方仓库包含 Docker
            $PKG_INSTALL docker docker-compose
            ;;
            
        *)
            echo "错误: 不支持的发行版 '$OS' 的 Docker 安装"
            echo "请手动安装 Docker: https://docs.docker.com/engine/install/"
            exit 1
            ;;
    esac
    
    # 启动 Docker 服务
    systemctl start docker
    systemctl enable docker
    
    echo "Docker 安装完成"
}

# 安装 Podman 的函数
install_podman() {
    case "$OS" in
        ubuntu|debian)
            echo "在 Ubuntu/Debian 上安装 Podman..."
            $PKG_UPDATE
            $PKG_INSTALL podman
            ;;
            
        centos|rhel|rocky|almalinux|fedora)
            echo "在 $NAME 上安装 Podman..."
            $PKG_INSTALL podman
            ;;
            
        arch|manjaro)
            echo "在 Arch Linux 上安装 Podman..."
            $PKG_INSTALL podman
            ;;
            
        *)
            echo "错误: 不支持的发行版 '$OS' 的 Podman 安装"
            exit 1
            ;;
    esac
    
    echo "Podman 安装完成"
}

if [ "$CONTAINER_ENGINE" = "docker" ]; then
    # 安装 Docker
    if command -v docker &> /dev/null; then
        echo "Docker 已安装，版本: $(docker --version)"
    else
        install_docker
    fi
else
    # 安装 Podman
    if command -v podman &> /dev/null; then
        echo "Podman 已安装，版本: $(podman --version)"
    else
        install_podman
    fi
fi

# 安装 ttyd（Web Terminal）
echo ""
echo "安装 ttyd (Web Terminal)..."
if ! command -v ttyd &> /dev/null; then
    case "$OS" in
        ubuntu|debian)
            $PKG_INSTALL ttyd
            ;;
        centos|rhel|rocky|almalinux|fedora)
            # EPEL 仓库可能包含 ttyd，或从源码编译
            echo "尝试从 EPEL 安装 ttyd..."
            if [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "rocky" ] || [ "$OS" = "almalinux" ]; then
                $PKG_INSTALL epel-release || true
            fi
            $PKG_INSTALL ttyd || {
                echo "警告: ttyd 安装失败，可能需要手动编译安装"
                echo "参考: https://github.com/tsl0922/ttyd"
            }
            ;;
        arch|manjaro)
            $PKG_INSTALL ttyd
            ;;
        *)
            echo "警告: 未知发行版，跳过 ttyd 安装"
            ;;
    esac
    
    if command -v ttyd &> /dev/null; then
        echo "ttyd 安装完成"
    else
        echo "警告: ttyd 未安装，Web Terminal 功能将不可用"
    fi
else
    echo "ttyd 已安装"
fi

# 安装网络工具
echo ""
echo "安装网络工具..."
case "$OS" in
    ubuntu|debian)
        $PKG_INSTALL bridge-utils iproute2
        ;;
    centos|rhel|rocky|almalinux|fedora)
        $PKG_INSTALL bridge-utils iproute
        ;;
    arch|manjaro)
        $PKG_INSTALL bridge-utils iproute2
        ;;
    *)
        echo "警告: 跳过网络工具安装"
        ;;
esac

# 2. 配置 Docker 网络
echo ""
echo "[2/7] 配置 Docker 网络..."

# 读取用户输入的网桥名称
read -p "请输入公网网桥名称 (默认: docker-pub): " BRIDGE_PUB
BRIDGE_PUB=${BRIDGE_PUB:-docker-pub}

read -p "请输入内网网桥名称 (默认: docker-nat): " BRIDGE_NAT
BRIDGE_NAT=${BRIDGE_NAT:-docker-nat}

# 创建 Docker 网络（如果不存在）
if [ "$CONTAINER_ENGINE" = "docker" ]; then
    # 创建公网网桥
    if ! docker network ls | grep -q "$BRIDGE_PUB"; then
        echo "创建公网 Docker 网络: $BRIDGE_PUB"
        read -p "请输入公网网段 (例如: 8.142.255.0/24): " PUB_SUBNET
        docker network create \
            --driver bridge \
            --subnet=$PUB_SUBNET \
            $BRIDGE_PUB
    else
        echo "公网网络 $BRIDGE_PUB 已存在"
    fi
    
    # 创建内网网桥
    if ! docker network ls | grep -q "$BRIDGE_NAT"; then
        echo "创建内网 Docker 网络: $BRIDGE_NAT"
        read -p "请输入内网网段 (例如: 252.227.81.0/24): " NAT_SUBNET
        docker network create \
            --driver bridge \
            --subnet=$NAT_SUBNET \
            $BRIDGE_NAT
    else
        echo "内网网络 $BRIDGE_NAT 已存在"
    fi
else
    # Podman 网络配置
    if ! podman network ls | grep -q "$BRIDGE_PUB"; then
        echo "创建公网 Podman 网络: $BRIDGE_PUB"
        read -p "请输入公网网段 (例如: 8.142.255.0/24): " PUB_SUBNET
        podman network create \
            --subnet=$PUB_SUBNET \
            $BRIDGE_PUB
    else
        echo "公网网络 $BRIDGE_PUB 已存在"
    fi
    
    if ! podman network ls | grep -q "$BRIDGE_NAT"; then
        echo "创建内网 Podman 网络: $BRIDGE_NAT"
        read -p "请输入内网网段 (例如: 252.227.81.0/24): " NAT_SUBNET
        podman network create \
            --subnet=$NAT_SUBNET \
            $BRIDGE_NAT
    else
        echo "内网网络 $BRIDGE_NAT 已存在"
    fi
fi

# 3. 配置 Docker 远程访问（TLS）
echo ""
echo "[3/7] 配置 Docker 远程访问 (TLS)..."

read -p "是否配置 Docker 远程访问? (y/n, 默认: y): " ENABLE_REMOTE
ENABLE_REMOTE=${ENABLE_REMOTE:-y}

if [ "$ENABLE_REMOTE" = "y" ] && [ "$CONTAINER_ENGINE" = "docker" ]; then
    # 证书存储目录
    read -p "请输入证书存储目录 (默认: /etc/docker/certs): " CERT_DIR
    CERT_DIR=${CERT_DIR:-/etc/docker/certs}
    
    mkdir -p $CERT_DIR
    cd $CERT_DIR
    
    # 生成 CA 证书
    if [ ! -f "ca.pem" ]; then
        echo "生成 CA 证书..."
        
        read -p "请输入服务器主机名或 IP: " SERVER_HOST
        
        # 生成 CA 私钥
        openssl genrsa -aes256 -out ca-key.pem 4096
        
        # 生成 CA 证书
        openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem \
            -subj "/C=CN/ST=Beijing/L=Beijing/O=OpenIDCS/OU=IT/CN=$SERVER_HOST"
        
        # 生成服务器私钥
        openssl genrsa -out server-key.pem 4096
        
        # 生成服务器证书签名请求
        openssl req -subj "/CN=$SERVER_HOST" -sha256 -new -key server-key.pem -out server.csr
        
        # 配置证书扩展
        echo "subjectAltName = DNS:$SERVER_HOST,IP:$SERVER_HOST,IP:127.0.0.1" >> extfile.cnf
        echo "extendedKeyUsage = serverAuth" >> extfile.cnf
        
        # 签名服务器证书
        openssl x509 -req -days 365 -sha256 -in server.csr -CA ca.pem -CAkey ca-key.pem \
            -CAcreateserial -out server-cert.pem -extfile extfile.cnf
        
        # 生成客户端私钥
        openssl genrsa -out client-key.pem 4096
        
        # 生成客户端证书签名请求
        openssl req -subj '/CN=client' -new -key client-key.pem -out client.csr
        
        # 配置客户端证书扩展
        echo "extendedKeyUsage = clientAuth" > extfile-client.cnf
        
        # 签名客户端证书
        openssl x509 -req -days 365 -sha256 -in client.csr -CA ca.pem -CAkey ca-key.pem \
            -CAcreateserial -out client-cert.pem -extfile extfile-client.cnf
        
        # 清理临时文件
        rm -f client.csr server.csr extfile.cnf extfile-client.cnf
        
        # 设置权限
        chmod 0400 ca-key.pem server-key.pem client-key.pem
        chmod 0444 ca.pem server-cert.pem client-cert.pem
        
        echo "TLS 证书生成完成"
        echo "证书位置: $CERT_DIR"
        echo ""
        echo "客户端需要的文件:"
        echo "  - ca.pem"
        echo "  - client-cert.pem"
        echo "  - client-key.pem"
    else
        echo "TLS 证书已存在"
    fi
    
    # 配置 Docker daemon
    echo ""
    echo "配置 Docker daemon..."
    
    DOCKER_DAEMON_JSON="/etc/docker/daemon.json"
    
    # 备份原配置
    if [ -f "$DOCKER_DAEMON_JSON" ]; then
        cp $DOCKER_DAEMON_JSON ${DOCKER_DAEMON_JSON}.backup
    fi
    
    # 创建新配置
    cat > $DOCKER_DAEMON_JSON << EOF
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2376"],
  "tls": true,
  "tlscacert": "$CERT_DIR/ca.pem",
  "tlscert": "$CERT_DIR/server-cert.pem",
  "tlskey": "$CERT_DIR/server-key.pem",
  "tlsverify": true
}
EOF
    
    echo "Docker daemon 配置已更新"
    
    # 修改 systemd 配置
    echo ""
    echo "修改 systemd 配置..."
    
    mkdir -p /etc/systemd/system/docker.service.d
    cat > /etc/systemd/system/docker.service.d/override.conf << EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
EOF
    
    # 重新加载并重启 Docker
    systemctl daemon-reload
    systemctl restart docker
    
    echo "Docker 远程访问配置完成"
    echo "远程访问地址: tcp://$SERVER_HOST:2376"
fi

# 4. 配置存储目录
echo ""
echo "[4/7] 配置存储目录..."

read -p "请输入镜像存储路径 (默认: /var/lib/docker-images): " IMAGES_PATH
IMAGES_PATH=${IMAGES_PATH:-/var/lib/docker-images}

read -p "请输入容器数据存储路径 (默认: /var/lib/docker-data): " DATA_PATH
DATA_PATH=${DATA_PATH:-/var/lib/docker-data}

read -p "请输入备份存储路径 (默认: /var/lib/docker-backups): " BACKUP_PATH
BACKUP_PATH=${BACKUP_PATH:-/var/lib/docker-backups}

read -p "请输入外部挂载路径 (默认: /var/lib/docker-mounts): " EXTERN_PATH
EXTERN_PATH=${EXTERN_PATH:-/var/lib/docker-mounts}

# 创建目录
mkdir -p $IMAGES_PATH
mkdir -p $DATA_PATH
mkdir -p $BACKUP_PATH
mkdir -p $EXTERN_PATH

echo "存储目录创建完成"

# 5. 安装 Python Docker SDK
echo ""
echo "[5/7] 安装 Python Docker SDK..."

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
    echo "使用 $PIP_CMD 安装 Docker SDK..."
    $PIP_CMD install docker
    echo "Python Docker SDK 安装完成"
else
    echo "警告: pip 未安装，请手动安装 Python Docker SDK:"
    echo "  pip3 install docker"
fi

# 6. 配置防火墙（如果需要）
echo ""
echo "[6/7] 配置防火墙..."

read -p "是否配置防火墙规则? (y/n, 默认: n): " CONFIG_FIREWALL
CONFIG_FIREWALL=${CONFIG_FIREWALL:-n}

if [ "$CONFIG_FIREWALL" = "y" ]; then
    FIREWALL_CONFIGURED=false
    
    # 尝试 UFW (Ubuntu/Debian)
    if command -v ufw &> /dev/null; then
        echo "配置 UFW 防火墙..."
        ufw allow 2376/tcp comment 'Docker TLS'
        ufw allow 7681/tcp comment 'ttyd Web Terminal'
        ufw reload
        echo "UFW 防火墙规则已添加"
        FIREWALL_CONFIGURED=true
    fi
    
    # 尝试 firewalld (CentOS/RHEL/Fedora)
    if command -v firewall-cmd &> /dev/null && [ "$FIREWALL_CONFIGURED" = false ]; then
        echo "配置 firewalld..."
        firewall-cmd --permanent --add-port=2376/tcp
        firewall-cmd --permanent --add-port=7681/tcp
        firewall-cmd --reload
        echo "firewalld 规则已添加"
        FIREWALL_CONFIGURED=true
    fi
    
    # 尝试 iptables (通用)
    if command -v iptables &> /dev/null && [ "$FIREWALL_CONFIGURED" = false ]; then
        echo "配置 iptables..."
        iptables -A INPUT -p tcp --dport 2376 -j ACCEPT
        iptables -A INPUT -p tcp --dport 7681 -j ACCEPT
        
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
        echo "需要开放的端口:"
        echo "  - 2376/tcp (Docker TLS)"
        echo "  - 7681/tcp (ttyd Web Terminal)"
    fi
fi

# 7. 测试 Docker 环境
echo ""
echo "[7/7] 测试 Docker 环境..."

if [ "$CONTAINER_ENGINE" = "docker" ]; then
    echo "Docker 版本:"
    docker --version
    
    echo ""
    echo "Docker 网络列表:"
    docker network ls
    
    echo ""
    echo "测试运行容器:"
    docker run --rm hello-world
else
    echo "Podman 版本:"
    podman --version
    
    echo ""
    echo "Podman 网络列表:"
    podman network ls
fi

# 完成
echo ""
echo "=========================================="
echo "Docker/Podman 环境初始化完成！"
echo "=========================================="
echo ""
echo "配置摘要:"
echo "  - 容器引擎: $CONTAINER_ENGINE"
echo "  - 公网网桥: $BRIDGE_PUB"
echo "  - 内网网桥: $BRIDGE_NAT"
echo "  - 镜像存储路径: $IMAGES_PATH"
echo "  - 容器数据路径: $DATA_PATH"
echo "  - 备份存储路径: $BACKUP_PATH"
echo "  - 外部挂载路径: $EXTERN_PATH"

if [ "$ENABLE_REMOTE" = "y" ] && [ "$CONTAINER_ENGINE" = "docker" ]; then
    echo "  - TLS 证书目录: $CERT_DIR"
    echo "  - 远程访问地址: tcp://$SERVER_HOST:2376"
fi

echo ""
echo "请在 HSConfig 中配置以下参数:"
echo "  - server_type: 'docker' 或 'podman'"
echo "  - server_addr: '$SERVER_HOST' (远程) 或 'localhost' (本地)"
echo "  - network_pub: '$BRIDGE_PUB'"
echo "  - network_nat: '$BRIDGE_NAT'"
echo "  - images_path: '$IMAGES_PATH'"
echo "  - system_path: '$DATA_PATH'"
echo "  - backup_path: '$BACKUP_PATH'"
echo "  - extern_path: '$EXTERN_PATH'"
echo "  - launch_path: '$CERT_DIR' (TLS 证书目录)"
echo ""
echo "建议测试命令:"
echo "  docker ps -a              # 列出所有容器"
echo "  docker network ls         # 列出所有网络"
echo "  docker images             # 列出所有镜像"
echo ""

if [ "$ENABLE_REMOTE" = "y" ] && [ "$CONTAINER_ENGINE" = "docker" ]; then
    echo "远程连接测试:"
    echo "  docker --tlsverify --tlscacert=$CERT_DIR/ca.pem \\"
    echo "    --tlscert=$CERT_DIR/client-cert.pem \\"
    echo "    --tlskey=$CERT_DIR/client-key.pem \\"
    echo "    -H=tcp://$SERVER_HOST:2376 ps"
    echo ""
fi

echo "注意事项:"
echo "  1. 请将客户端证书 (ca.pem, client-cert.pem, client-key.pem) 复制到客户端的 launch_path 目录"
echo "  2. 确保防火墙允许 2376 端口访问"
echo "  3. 建议定期备份证书文件"
echo ""
