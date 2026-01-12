#!/bin/bash

# ============================================
# OpenIDCS OCI 容器引擎自动化安装配置脚本
# ============================================
# 功能：自动安装并配置 Docker/Podman 容器环境
# 适用：Ubuntu/Debian/CentOS/RHEL/Fedora/Arch
# 作者：OpenIDCS Team
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# 全局变量
SCRIPT_VERSION="1.0.0"
CONTAINER_ENGINE=""
FORCE=false
DELETE=false

# 日志函数
log() { echo -e "$1"; }
ok() { log "${GREEN}✓${NC} $1"; }
info() { log "${BLUE}ℹ${NC} $1"; }
warn() { log "${YELLOW}⚠${NC} $1"; }
err() { log "${RED}✗${NC} $1"; exit 1; }

# 打印分隔线
print_line() {
    local char="${1:-═}"
    printf "${BLUE}%s${NC}\n" "$(printf '%*s' 60 '' | tr ' ' "$char")"
}

# 打印标题
print_title() {
    echo
    print_line "═"
    echo -e "${WHITE}$1${NC}"
    print_line "═"
    echo
}

# 打印步骤标题
print_step() {
    echo
    print_line "─"
    echo -e "${CYAN}▶ 步骤 $1${NC}"
    print_line "─"
    echo
}

# 检查 root 权限
[[ $EUID -ne 0 ]] && err "请使用 root 权限运行此脚本"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    -f|--force) FORCE=true; shift;;
    -d|--delete) DELETE=true; shift;;
    -h|--help)
      print_title "OpenIDCS OCI 容器引擎安装脚本 v${SCRIPT_VERSION}"
      echo -e "${WHITE}用法:${NC}"
      echo -e "  ${CYAN}$0${NC} [选项]"
      echo
      echo -e "${WHITE}选项:${NC}"
      echo -e "  ${GREEN}-f, --force${NC}    强制重新安装（即使已安装）"
      echo -e "  ${RED}-d, --delete${NC}   卸载容器引擎及所有数据"
      echo -e "  ${BLUE}-h, --help${NC}     显示此帮助信息"
      echo
      echo -e "${WHITE}示例:${NC}"
      echo -e "  ${CYAN}$0${NC}              ${BLUE}# 安装 Docker/Podman${NC}"
      echo -e "  ${CYAN}$0 -f${NC}           ${BLUE}# 强制重新安装${NC}"
      echo -e "  ${CYAN}$0 -d${NC}           ${BLUE}# 卸载容器引擎${NC}"
      echo
      exit 0;;
    *) err "未知参数: $1 (使用 -h 查看帮助)";;
  esac
done

# 卸载功能
if [[ $DELETE == true ]]; then
  print_title "卸载 OCI 容器引擎"
  
  warn "此操作将完全卸载容器引擎及其所有数据！"
  echo
  
  # 检测已安装的容器引擎
  FOUND_ENGINE=false
  
  if command -v docker &> /dev/null; then
    echo "  - 检测到 Docker"
    FOUND_ENGINE=true
  fi
  
  if command -v podman &> /dev/null; then
    echo "  - 检测到 Podman"
    FOUND_ENGINE=true
  fi
  
  if [[ $FOUND_ENGINE == false ]]; then
    warn "未检测到已安装的容器引擎"
    exit 0
  fi
  
  echo
  read -p "确定要继续吗? (y/N): " CONFIRM
  if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
    ok "取消卸载操作"
    exit 0
  fi
  
  echo
  
  # 检测包管理器
  PKG_MANAGER=""
  if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
  elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
  elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
  elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
  fi
  
  # 卸载 Docker
  if command -v docker &> /dev/null; then
    info "停止 Docker 服务..."
    systemctl stop docker 2>/dev/null || true
    systemctl stop docker.socket 2>/dev/null || true
    
    info "卸载 Docker..."
    case $PKG_MANAGER in
      apt)
        apt-get purge -y docker-ce docker-ce-cli containerd.io docker-compose-plugin 2>/dev/null || true
        apt-get autoremove -y 2>/dev/null || true
        ;;
      dnf)
        dnf remove -y docker-ce docker-ce-cli containerd.io docker-compose-plugin 2>/dev/null || true
        ;;
      yum)
        yum remove -y docker-ce docker-ce-cli containerd.io docker-compose-plugin 2>/dev/null || true
        ;;
      pacman)
        pacman -Rns --noconfirm docker docker-compose 2>/dev/null || true
        ;;
    esac
    
    info "清理 Docker 数据..."
    rm -rf /var/lib/docker 2>/dev/null || true
    rm -rf /etc/docker 2>/dev/null || true
    rm -rf /var/run/docker.sock 2>/dev/null || true
  fi
  
  # 卸载 Podman
  if command -v podman &> /dev/null; then
    info "卸载 Podman..."
    case $PKG_MANAGER in
      apt)
        apt-get purge -y podman 2>/dev/null || true
        apt-get autoremove -y 2>/dev/null || true
        ;;
      dnf|yum)
        $PKG_MANAGER remove -y podman 2>/dev/null || true
        ;;
      pacman)
        pacman -Rns --noconfirm podman 2>/dev/null || true
        ;;
    esac
    
    info "清理 Podman 数据..."
    rm -rf /var/lib/containers 2>/dev/null || true
    rm -rf /etc/containers 2>/dev/null || true
    rm -rf ~/.local/share/containers 2>/dev/null || true
  fi
  
  echo
  ok "容器引擎卸载完成！"
  exit 0
fi

# 检测 Linux 发行版
detect_distro() {
    info "检测操作系统..."
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
        OS_NAME=$NAME
        info "系统: $OS_NAME ${VERSION:-未知版本}"
    else
        err "无法检测系统类型"
    fi
}

# 确定包管理器
setup_package_manager() {
    info "检测包管理器..."
    case "$DISTRO" in
        ubuntu|debian)
            PKG_MANAGER="apt"
            PKG_UPDATE="apt-get update"
            PKG_INSTALL="apt-get install -y"
            info "包管理器: APT (Debian/Ubuntu)"
            ;;
        centos|rhel|rocky|almalinux)
            if command -v dnf &> /dev/null; then
                PKG_MANAGER="dnf"
                PKG_UPDATE="dnf check-update || true"
                PKG_INSTALL="dnf install -y"
                info "包管理器: DNF (CentOS/RHEL 8+)"
            else
                PKG_MANAGER="yum"
                PKG_UPDATE="yum check-update || true"
                PKG_INSTALL="yum install -y"
                info "包管理器: YUM (CentOS/RHEL)"
            fi
            ;;
        fedora)
            PKG_MANAGER="dnf"
            PKG_UPDATE="dnf check-update || true"
            PKG_INSTALL="dnf install -y"
            info "包管理器: DNF (Fedora)"
            ;;
        arch|manjaro)
            PKG_MANAGER="pacman"
            PKG_UPDATE="pacman -Sy"
            PKG_INSTALL="pacman -S --noconfirm"
            info "包管理器: Pacman (Arch Linux)"
            ;;
        *)
            warn "未识别的发行版 '$DISTRO'，尝试自动检测..."
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
                err "无法检测到支持的包管理器"
            fi
            ;;
    esac
}

# 安装 Docker
install_docker() {
    info "开始安装 Docker..."
    
    case "$DISTRO" in
        ubuntu|debian)
            info "在 Ubuntu/Debian 上安装 Docker..."
            
            # 安装依赖
            $PKG_INSTALL ca-certificates curl gnupg lsb-release || err "依赖安装失败"
            
            # 添加 Docker GPG 密钥
            info "添加 Docker GPG 密钥..."
            mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$DISTRO/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null || err "GPG 密钥添加失败"
            
            # 设置 Docker 仓库
            info "设置 Docker 仓库..."
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$DISTRO $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # 安装 Docker
            $PKG_UPDATE || warn "软件包列表更新失败"
            $PKG_INSTALL docker-ce docker-ce-cli containerd.io docker-compose-plugin || err "Docker 安装失败"
            ;;
            
        centos|rhel|rocky|almalinux)
            info "在 CentOS/RHEL/Rocky 上安装 Docker..."
            
            # 安装依赖
            $PKG_INSTALL yum-utils device-mapper-persistent-data lvm2 || warn "依赖安装失败"
            
            # 添加 Docker 仓库
            info "添加 Docker 仓库..."
            yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo || err "仓库添加失败"
            
            # 安装 Docker
            $PKG_INSTALL docker-ce docker-ce-cli containerd.io docker-compose-plugin || err "Docker 安装失败"
            ;;
            
        fedora)
            info "在 Fedora 上安装 Docker..."
            
            # 安装依赖
            $PKG_INSTALL dnf-plugins-core || warn "依赖安装失败"
            
            # 添加 Docker 仓库
            info "添加 Docker 仓库..."
            dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo || err "仓库添加失败"
            
            # 安装 Docker
            $PKG_INSTALL docker-ce docker-ce-cli containerd.io docker-compose-plugin || err "Docker 安装失败"
            ;;
            
        arch|manjaro)
            info "在 Arch Linux 上安装 Docker..."
            $PKG_INSTALL docker docker-compose || err "Docker 安装失败"
            ;;
            
        *)
            err "不支持的发行版 '$DISTRO' 的 Docker 安装"
            ;;
    esac
    
    # 启动 Docker 服务
    info "启动 Docker 服务..."
    systemctl start docker || err "Docker 服务启动失败"
    systemctl enable docker || warn "Docker 服务自启动设置失败"
    
    # 验证安装
    if docker --version &> /dev/null; then
        ok "Docker 安装成功: $(docker --version)"
    else
        err "Docker 安装验证失败"
    fi
}

# 安装 Podman
install_podman() {
    info "开始安装 Podman..."
    
    case "$DISTRO" in
        ubuntu|debian)
            info "在 Ubuntu/Debian 上安装 Podman..."
            $PKG_UPDATE || warn "软件包列表更新失败"
            $PKG_INSTALL podman || err "Podman 安装失败"
            ;;
            
        centos|rhel|rocky|almalinux|fedora)
            info "在 $OS_NAME 上安装 Podman..."
            $PKG_INSTALL podman || err "Podman 安装失败"
            ;;
            
        arch|manjaro)
            info "在 Arch Linux 上安装 Podman..."
            $PKG_INSTALL podman || err "Podman 安装失败"
            ;;
            
        *)
            err "不支持的发行版 '$DISTRO' 的 Podman 安装"
            ;;
    esac
    
    # 验证安装
    if podman --version &> /dev/null; then
        ok "Podman 安装成功: $(podman --version)"
    else
        err "Podman 安装验证失败"
    fi
}

# 配置 Docker TLS 远程访问
configure_docker_tls() {
    info "配置 Docker TLS 远程访问..."
    
    # 获取服务器地址
    SERVER_HOST=$(hostname -I | awk '{print $1}' | tr -d '[:space:]')
    if [ -z "$SERVER_HOST" ]; then
        SERVER_HOST=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' | tr -d '[:space:]')
    fi
    if [ -z "$SERVER_HOST" ]; then
        SERVER_HOST=$(hostname | tr -d '[:space:]')
    fi
    
    if [ -z "$SERVER_HOST" ]; then
        warn "无法自动获取服务器地址"
        read -p "请手动输入服务器地址 (IP 或域名): " SERVER_HOST
        [ -z "$SERVER_HOST" ] && err "服务器地址不能为空"
    fi
    
    ok "服务器地址: $SERVER_HOST"
    
    # 创建证书目录
    mkdir -p $CERT_DIR
    cd $CERT_DIR
    
    if [ -f "ca.pem" ] && [ -f "server-cert.pem" ] && [ -f "client-cert.pem" ]; then
        warn "TLS 证书已存在，跳过生成"
        return 0
    fi
    
    info "生成 TLS 证书..."
    
    # 检查 openssl
    if ! command -v openssl &> /dev/null; then
        err "openssl 未安装，无法生成证书"
    fi
    
    # 生成 CA 私钥
    info "生成 CA 私钥..."
    openssl genrsa -out ca-key.pem 4096 2>/dev/null || err "CA 私钥生成失败"
    
    # 生成 CA 证书
    info "生成 CA 证书..."
    openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=OpenIDCS/OU=IT/CN=$SERVER_HOST" 2>/dev/null || err "CA 证书生成失败"
    
    # 生成服务器私钥
    info "生成服务器私钥..."
    openssl genrsa -out server-key.pem 4096 2>/dev/null || err "服务器私钥生成失败"
    
    # 生成服务器证书签名请求
    info "生成服务器证书签名请求..."
    openssl req -new -sha256 -key server-key.pem -out server.csr \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=OpenIDCS/OU=IT/CN=$SERVER_HOST" 2>/dev/null || err "服务器 CSR 生成失败"
    
    # 配置证书扩展
    cat > extfile.cnf << EOF
subjectAltName = DNS:$SERVER_HOST,IP:$SERVER_HOST,IP:127.0.0.1
extendedKeyUsage = serverAuth
EOF
    
    # 签名服务器证书
    info "签名服务器证书..."
    openssl x509 -req -days 365 -sha256 -in server.csr -CA ca.pem -CAkey ca-key.pem \
        -CAcreateserial -out server-cert.pem -extfile extfile.cnf 2>/dev/null || err "服务器证书签名失败"
    
    # 生成客户端私钥
    info "生成客户端私钥..."
    openssl genrsa -out client-key.pem 4096 2>/dev/null || err "客户端私钥生成失败"
    
    # 生成客户端证书签名请求
    info "生成客户端证书签名请求..."
    openssl req -new -sha256 -key client-key.pem -out client.csr \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=OpenIDCS/OU=IT/CN=client" 2>/dev/null || err "客户端 CSR 生成失败"
    
    # 配置客户端证书扩展
    echo "extendedKeyUsage = clientAuth" > extfile-client.cnf
    
    # 签名客户端证书
    info "签名客户端证书..."
    openssl x509 -req -days 365 -sha256 -in client.csr -CA ca.pem -CAkey ca-key.pem \
        -CAcreateserial -out client-cert.pem -extfile extfile-client.cnf 2>/dev/null || err "客户端证书签名失败"
    
    # 清理临时文件
    rm -f client.csr server.csr extfile.cnf extfile-client.cnf ca.srl
    
    # 设置权限
    chmod 0400 ca-key.pem server-key.pem client-key.pem
    chmod 0444 ca.pem server-cert.pem client-cert.pem
    
    ok "TLS 证书生成完成"
    
    # 配置 Docker daemon
    info "配置 Docker daemon..."
    
    DOCKER_DAEMON_JSON="/etc/docker/daemon.json"
    
    # 备份原配置
    if [ -f "$DOCKER_DAEMON_JSON" ]; then
        cp $DOCKER_DAEMON_JSON ${DOCKER_DAEMON_JSON}.backup.$(date +%Y%m%d%H%M%S)
        info "已备份原配置文件"
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
    
    # 修改 systemd 配置
    info "修改 systemd 配置..."
    mkdir -p /etc/systemd/system/docker.service.d
    cat > /etc/systemd/system/docker.service.d/override.conf << EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
EOF
    
    # 重新加载并重启 Docker
    info "重启 Docker 服务..."
    systemctl daemon-reload
    systemctl restart docker || err "Docker 服务重启失败"
    
    # 等待服务启动
    sleep 3
    
    if systemctl is-active --quiet docker; then
        ok "Docker TLS 远程访问配置完成"
    else
        err "Docker 服务未正常运行"
    fi
}

# 配置防火墙
configure_firewall() {
    info "配置防火墙..."
    
    FIREWALL_CONFIGURED=false
    
    # UFW (Ubuntu/Debian)
    if command -v ufw &> /dev/null; then
        info "配置 UFW 防火墙..."
        ufw allow 2376/tcp comment 'Docker TLS' 2>/dev/null && ok "已添加 Docker TLS 端口规则"
        ufw reload 2>/dev/null || true
        FIREWALL_CONFIGURED=true
    fi
    
    # firewalld (CentOS/RHEL/Fedora)
    if command -v firewall-cmd &> /dev/null && [ "$FIREWALL_CONFIGURED" = false ]; then
        info "配置 firewalld..."
        firewall-cmd --permanent --add-port=2376/tcp 2>/dev/null && ok "已添加 Docker TLS 端口规则"
        firewall-cmd --reload 2>/dev/null || true
        FIREWALL_CONFIGURED=true
    fi
    
    # iptables (通用)
    if command -v iptables &> /dev/null && [ "$FIREWALL_CONFIGURED" = false ]; then
        info "配置 iptables..."
        iptables -A INPUT -p tcp --dport 2376 -j ACCEPT
        
        # 保存规则
        case "$DISTRO" in
            ubuntu|debian)
                if ! command -v iptables-persistent &> /dev/null; then
                    $PKG_INSTALL iptables-persistent 2>/dev/null || true
                fi
                iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
                ;;
            centos|rhel|rocky|almalinux|fedora)
                service iptables save 2>/dev/null || iptables-save > /etc/sysconfig/iptables 2>/dev/null || true
                ;;
            arch|manjaro)
                iptables-save > /etc/iptables/iptables.rules 2>/dev/null || true
                systemctl enable iptables 2>/dev/null || true
                ;;
        esac
        
        ok "已添加 iptables 规则"
        FIREWALL_CONFIGURED=true
    fi
    
    if [ "$FIREWALL_CONFIGURED" = false ]; then
        warn "未检测到防火墙工具，请手动配置防火墙开放 2376 端口"
    fi
}

# 主程序开始
print_title "OpenIDCS OCI 容器引擎安装向导 v${SCRIPT_VERSION}"

print_step "1/7: 检测系统环境"

detect_distro

info "检测系统架构..."
arch=$(uname -m)
case $arch in
    x86_64)
        ok "架构: amd64"
        ;;
    aarch64|arm64)
        ok "架构: arm64"
        ;;
    *)
        err "不支持的架构: $arch (仅支持 amd64/arm64)"
        ;;
esac

setup_package_manager

# 检查已安装的容器引擎
info "检查容器引擎安装状态..."
DOCKER_INSTALLED=false
PODMAN_INSTALLED=false

if command -v docker &> /dev/null; then
    DOCKER_INSTALLED=true
    info "检测到 Docker: $(docker --version 2>/dev/null || echo '版本未知')"
fi

if command -v podman &> /dev/null; then
    PODMAN_INSTALLED=true
    info "检测到 Podman: $(podman --version 2>/dev/null || echo '版本未知')"
fi

if [[ $DOCKER_INSTALLED == true ]] || [[ $PODMAN_INSTALLED == true ]]; then
    if [[ $FORCE == true ]]; then
        warn "检测到已安装的容器引擎，使用 -f 参数将强制重新安装"
        echo
        read -p "确定要继续吗? (y/N): " FORCE_CONFIRM
        if [[ $FORCE_CONFIRM != "y" && $FORCE_CONFIRM != "Y" ]]; then
            ok "取消重新安装操作"
            exit 0
        fi
    else
        ok "容器引擎已安装"
        echo
        info "提示："
        echo "  - 卸载: $0 -d"
        echo "  - 强制重新安装: $0 -f"
        exit 0
    fi
fi

ok "环境检测通过"

print_step "2/7: 选择容器引擎"

echo -e "${WHITE}请选择要安装的容器引擎:${NC}"
echo
echo -e "  ${GREEN}1)${NC} Docker   ${BLUE}(推荐，生态完善，社区活跃)${NC}"
echo -e "  ${GREEN}2)${NC} Podman   ${BLUE}(无守护进程，更安全)${NC}"
echo

read -p "请输入选项 (1 或 2, 默认: 1): " ENGINE_CHOICE
ENGINE_CHOICE=${ENGINE_CHOICE:-1}

if [ "$ENGINE_CHOICE" = "2" ]; then
    CONTAINER_ENGINE="podman"
    ok "已选择: Podman"
else
    CONTAINER_ENGINE="docker"
    ok "已选择: Docker"
fi

print_step "3/7: 安装容器引擎"

info "更新软件包列表..."
$PKG_UPDATE || warn "软件包列表更新失败，继续安装..."

if [ "$CONTAINER_ENGINE" = "docker" ]; then
    install_docker
else
    install_podman
fi

print_step "4/7: 配置网络"

echo -e "${YELLOW}[1/2]${NC} 公网网桥名称 ${BLUE}(用于公网访问)${NC}"
read -p "      名称 [默认: ${CONTAINER_ENGINE}-pub]: " BRIDGE_PUB
BRIDGE_PUB=${BRIDGE_PUB:-${CONTAINER_ENGINE}-pub}
echo

echo -e "${YELLOW}[2/2]${NC} 内网网桥名称 ${BLUE}(用于 NAT 网络)${NC}"
read -p "      名称 [默认: ${CONTAINER_ENGINE}-nat]: " BRIDGE_NAT
BRIDGE_NAT=${BRIDGE_NAT:-${CONTAINER_ENGINE}-nat}
echo

# 创建网络
info "创建容器网络..."

if [ "$CONTAINER_ENGINE" = "docker" ]; then
    # 创建公网网桥
    if ! docker network ls | grep -q "$BRIDGE_PUB"; then
        echo -e "${CYAN}创建公网网络: $BRIDGE_PUB${NC}"
        read -p "请输入公网网段 (例如: 172.18.0.0/16, 直接回车使用默认): " PUB_SUBNET
        if [ -n "$PUB_SUBNET" ]; then
            docker network create --driver bridge --subnet=$PUB_SUBNET $BRIDGE_PUB && ok "公网网络创建成功" || warn "公网网络创建失败"
        else
            docker network create --driver bridge $BRIDGE_PUB && ok "公网网络创建成功" || warn "公网网络创建失败"
        fi
    else
        ok "公网网络 $BRIDGE_PUB 已存在"
    fi
    
    # 创建内网网桥
    if ! docker network ls | grep -q "$BRIDGE_NAT"; then
        echo -e "${CYAN}创建内网网络: $BRIDGE_NAT${NC}"
        read -p "请输入内网网段 (例如: 172.19.0.0/16, 直接回车使用默认): " NAT_SUBNET
        if [ -n "$NAT_SUBNET" ]; then
            docker network create --driver bridge --subnet=$NAT_SUBNET $BRIDGE_NAT && ok "内网网络创建成功" || warn "内网网络创建失败"
        else
            docker network create --driver bridge $BRIDGE_NAT && ok "内网网络创建成功" || warn "内网网络创建失败"
        fi
    else
        ok "内网网络 $BRIDGE_NAT 已存在"
    fi
else
    # Podman 网络
    if ! podman network ls | grep -q "$BRIDGE_PUB"; then
        echo -e "${CYAN}创建公网网络: $BRIDGE_PUB${NC}"
        read -p "请输入公网网段 (例如: 172.18.0.0/16, 直接回车使用默认): " PUB_SUBNET
        if [ -n "$PUB_SUBNET" ]; then
            podman network create --subnet=$PUB_SUBNET $BRIDGE_PUB && ok "公网网络创建成功" || warn "公网网络创建失败"
        else
            podman network create $BRIDGE_PUB && ok "公网网络创建成功" || warn "公网网络创建失败"
        fi
    else
        ok "公网网络 $BRIDGE_PUB 已存在"
    fi
    
    if ! podman network ls | grep -q "$BRIDGE_NAT"; then
        echo -e "${CYAN}创建内网网络: $BRIDGE_NAT${NC}"
        read -p "请输入内网网段 (例如: 172.19.0.0/16, 直接回车使用默认): " NAT_SUBNET
        if [ -n "$NAT_SUBNET" ]; then
            podman network create --subnet=$NAT_SUBNET $BRIDGE_NAT && ok "内网网络创建成功" || warn "内网网络创建失败"
        else
            podman network create $BRIDGE_NAT && ok "内网网络创建成功" || warn "内网网络创建失败"
        fi
    else
        ok "内网网络 $BRIDGE_NAT 已存在"
    fi
fi

print_step "5/7: 配置存储路径"

echo -e "${YELLOW}[1/4]${NC} 镜像存储路径 ${BLUE}(用于存放容器镜像)${NC}"
read -p "      路径 [默认: /opt/oidc/oci/images]: " IMAGES_PATH
IMAGES_PATH=${IMAGES_PATH:-/opt/oidc/oci/images}
echo

echo -e "${YELLOW}[2/4]${NC} 容器数据路径 ${BLUE}(用于存放容器数据)${NC}"
read -p "      路径 [默认: /opt/oidc/oci/data]: " DATA_PATH
DATA_PATH=${DATA_PATH:-/opt/oidc/oci/data}
echo

echo -e "${YELLOW}[3/4]${NC} 备份存储路径 ${BLUE}(用于存放容器备份)${NC}"
read -p "      路径 [默认: /opt/oidc/oci/backup]: " BACKUP_PATH
BACKUP_PATH=${BACKUP_PATH:-/opt/oidc/oci/backup}
echo

echo -e "${YELLOW}[4/4]${NC} 外部挂载路径 ${BLUE}(用于外部数据挂载)${NC}"
read -p "      路径 [默认: /opt/oidc/oci/mounts]: " EXTERN_PATH
EXTERN_PATH=${EXTERN_PATH:-/opt/oidc/oci/mounts}
echo

# 创建目录
info "创建存储目录..."
mkdir -p "$IMAGES_PATH" && ok "镜像目录: $IMAGES_PATH" || warn "镜像目录创建失败"
mkdir -p "$DATA_PATH" && ok "数据目录: $DATA_PATH" || warn "数据目录创建失败"
mkdir -p "$BACKUP_PATH" && ok "备份目录: $BACKUP_PATH" || warn "备份目录创建失败"
mkdir -p "$EXTERN_PATH" && ok "挂载目录: $EXTERN_PATH" || warn "挂载目录创建失败"

print_step "6/7: 配置远程访问"

if [ "$CONTAINER_ENGINE" = "docker" ]; then
    echo
    read -p "是否配置 Docker TLS 远程访问? (y/N): " ENABLE_REMOTE
    ENABLE_REMOTE=${ENABLE_REMOTE:-n}
    
    if [[ $ENABLE_REMOTE == "y" || $ENABLE_REMOTE == "Y" ]]; then
        echo
        echo -e "${YELLOW}证书存储目录${NC}"
        read -p "路径 [默认: /opt/oidc/oci/certs]: " CERT_DIR
        CERT_DIR=${CERT_DIR:-/opt/oidc/oci/certs}
        
        configure_docker_tls
        
        echo
        read -p "是否配置防火墙规则? (y/N): " CONFIG_FW
        if [[ $CONFIG_FW == "y" || $CONFIG_FW == "Y" ]]; then
            configure_firewall
        else
            warn "跳过防火墙配置，请手动开放 2376 端口"
        fi
    else
        info "跳过远程访问配置"
        CERT_DIR=""
    fi
else
    info "Podman 不需要配置远程访问（使用 SSH 连接）"
    CERT_DIR=""
fi

print_step "7/7: 安装 Python SDK"

echo
read -p "是否安装 Python SDK? (y/N): " INSTALL_SDK
INSTALL_SDK=${INSTALL_SDK:-n}

if [[ $INSTALL_SDK == "y" || $INSTALL_SDK == "Y" ]]; then
    # 检测 Python
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
        info "Python 未安装，正在安装..."
        case "$DISTRO" in
            ubuntu|debian)
                $PKG_INSTALL python3 python3-pip
                PIP_CMD="pip3"
                ;;
            centos|rhel|rocky|almalinux|fedora)
                $PKG_INSTALL python3 python3-pip
                PIP_CMD="pip3"
                ;;
            arch|manjaro)
                $PKG_INSTALL python python-pip
                PIP_CMD="pip"
                ;;
        esac
    fi
    
    if [ -n "$PIP_CMD" ]; then
        info "安装 Python SDK..."
        if [ "$CONTAINER_ENGINE" = "docker" ]; then
            $PIP_CMD install docker && ok "Docker SDK 安装成功" || warn "Docker SDK 安装失败"
        else
            $PIP_CMD install podman && ok "Podman SDK 安装成功" || warn "Podman SDK 安装失败"
        fi
    else
        warn "pip 未安装，请手动安装 Python SDK"
    fi
else
    info "跳过 Python SDK 安装"
fi

# 完成
print_title "✓ 安装完成！配置信息汇总"

ok "OCI 容器引擎已成功安装并配置完成！"
echo

# 系统信息
print_line "═"
echo -e "${WHITE}系统信息${NC}"
print_line "─"
printf "  %-24s %s\n" "${CYAN}操作系统:${NC}" "$OS_NAME ${VERSION:-未知版本}"
printf "  %-24s %s\n" "${CYAN}系统架构:${NC}" "$(uname -m)"
printf "  %-24s %s\n" "${CYAN}容器引擎:${NC}" "$CONTAINER_ENGINE"
if [ "$CONTAINER_ENGINE" = "docker" ]; then
    printf "  %-24s %s\n" "${CYAN}Docker 版本:${NC}" "$(docker --version 2>/dev/null || echo '未知')"
else
    printf "  %-24s %s\n" "${CYAN}Podman 版本:${NC}" "$(podman --version 2>/dev/null || echo '未知')"
fi
print_line "═"
echo

# 配置信息
print_line "═"
echo -e "${WHITE}【OpenIDCS 配置参数】${NC}"
print_line "─"
echo
echo -e "${CYAN}请将以下配置信息填写到 HSConfig.py:${NC}"
echo
printf "  %-24s ${GREEN}'%s'${NC}\n" "server_type:" "$CONTAINER_ENGINE"
if [ -n "$SERVER_HOST" ]; then
    printf "  %-24s ${GREEN}'%s'${NC}\n" "server_addr:" "$SERVER_HOST"
else
    printf "  %-24s ${YELLOW}'<服务器IP地址>'${NC}\n" "server_addr:"
fi
if [ "$CONTAINER_ENGINE" = "docker" ] && [ -n "$CERT_DIR" ]; then
    printf "  %-24s ${GREEN}2376${NC}\n" "server_port:"
else
    printf "  %-24s ${GREEN}22${NC} ${BLUE}(SSH)${NC}\n" "server_port:"
fi
printf "  %-24s ${GREEN}'%s'${NC}\n" "network_pub:" "$BRIDGE_PUB"
printf "  %-24s ${GREEN}'%s'${NC}\n" "network_nat:" "$BRIDGE_NAT"
printf "  %-24s ${GREEN}'%s'${NC}\n" "images_path:" "$IMAGES_PATH"
printf "  %-24s ${GREEN}'%s'${NC}\n" "system_path:" "$DATA_PATH"
printf "  %-24s ${GREEN}'%s'${NC}\n" "backup_path:" "$BACKUP_PATH"
printf "  %-24s ${GREEN}'%s'${NC}\n" "extern_path:" "$EXTERN_PATH"
if [ -n "$CERT_DIR" ]; then
    printf "  %-24s ${GREEN}'%s'${NC}\n" "launch_path:" "$CERT_DIR"
fi
print_line "═"
echo

# 网络信息
print_line "═"
echo -e "${WHITE}【网络配置】${NC}"
print_line "─"
if [ "$CONTAINER_ENGINE" = "docker" ]; then
    docker network ls
else
    podman network ls
fi
print_line "═"
echo

# TLS 证书信息
if [ -n "$CERT_DIR" ]; then
    print_line "═"
    echo -e "${WHITE}【TLS 证书信息】${NC}"
    print_line "─"
    echo -e "  ${CYAN}证书目录:${NC} $CERT_DIR"
    echo -e "  ${CYAN}远程地址:${NC} tcp://$SERVER_HOST:2376"
    echo
    echo -e "  ${YELLOW}客户端需要的文件:${NC}"
    echo -e "    - ca.pem"
    echo -e "    - client-cert.pem"
    echo -e "    - client-key.pem"
    echo
    echo -e "  ${YELLOW}复制证书到客户端:${NC}"
    echo -e "    ${BLUE}scp -r $CERT_DIR/* user@client:/path/to/certs/${NC}"
    print_line "═"
    echo
fi

# 测试命令
print_line "═"
echo -e "${WHITE}【测试命令】${NC}"
print_line "─"
if [ "$CONTAINER_ENGINE" = "docker" ]; then
    echo -e "  ${CYAN}# 查看容器列表${NC}"
    echo -e "  ${BLUE}docker ps -a${NC}"
    echo
    echo -e "  ${CYAN}# 查看网络列表${NC}"
    echo -e "  ${BLUE}docker network ls${NC}"
    echo
    echo -e "  ${CYAN}# 查看镜像列表${NC}"
    echo -e "  ${BLUE}docker images${NC}"
    echo
    if [ -n "$CERT_DIR" ]; then
        echo -e "  ${CYAN}# 远程连接测试${NC}"
        echo -e "  ${BLUE}docker --tlsverify \\${NC}"
        echo -e "  ${BLUE}  --tlscacert=$CERT_DIR/ca.pem \\${NC}"
        echo -e "  ${BLUE}  --tlscert=$CERT_DIR/client-cert.pem \\${NC}"
        echo -e "  ${BLUE}  --tlskey=$CERT_DIR/client-key.pem \\${NC}"
        echo -e "  ${BLUE}  -H=tcp://$SERVER_HOST:2376 ps${NC}"
        echo
    fi
else
    echo -e "  ${CYAN}# 查看容器列表${NC}"
    echo -e "  ${BLUE}podman ps -a${NC}"
    echo
    echo -e "  ${CYAN}# 查看网络列表${NC}"
    echo -e "  ${BLUE}podman network ls${NC}"
    echo
    echo -e "  ${CYAN}# 查看镜像列表${NC}"
    echo -e "  ${BLUE}podman images${NC}"
    echo
fi
print_line "═"
echo

# 常见问题
print_line "═"
echo -e "${WHITE}【常见问题处理】${NC}"
print_line "─"
echo
if [ "$CONTAINER_ENGINE" = "docker" ]; then
    echo -e "${YELLOW}问题 1:${NC} Docker 服务无法启动"
    echo -e "  ${GREEN}解决方案:${NC}"
    echo -e "    ${CYAN}1.${NC} 查看日志: ${BLUE}journalctl -u docker -n 50${NC}"
    echo -e "    ${CYAN}2.${NC} 检查配置: ${BLUE}dockerd --validate${NC}"
    echo -e "    ${CYAN}3.${NC} 重启服务: ${BLUE}systemctl restart docker${NC}"
    echo
    echo -e "${YELLOW}问题 2:${NC} 无法远程连接"
    echo -e "  ${GREEN}检查清单:${NC}"
    echo -e "    ${CYAN}1.${NC} 确认防火墙已开放 2376 端口"
    echo -e "    ${CYAN}2.${NC} 确认证书文件权限正确"
    echo -e "    ${CYAN}3.${NC} 确认 Docker daemon 配置正确"
    echo
else
    echo -e "${YELLOW}问题 1:${NC} Podman 容器无法启动"
    echo -e "  ${GREEN}解决方案:${NC}"
    echo -e "    ${CYAN}1.${NC} 查看日志: ${BLUE}podman logs <container_id>${NC}"
    echo -e "    ${CYAN}2.${NC} 检查权限: ${BLUE}podman unshare cat /proc/self/uid_map${NC}"
    echo
fi
echo -e "${YELLOW}问题 3:${NC} 网络连接问题"
echo -e "  ${GREEN}解决方案:${NC}"
echo -e "    ${CYAN}1.${NC} 检查网络: ${BLUE}${CONTAINER_ENGINE} network inspect <network_name>${NC}"
echo -e "    ${CYAN}2.${NC} 重建网络: ${BLUE}${CONTAINER_ENGINE} network rm <network_name>${NC}"
echo -e "    ${CYAN}3.${NC} 检查 iptables: ${BLUE}iptables -L -n${NC}"
print_line "═"
echo

# 管理命令
print_line "═"
echo -e "${WHITE}【管理命令】${NC}"
print_line "─"
if [ "$CONTAINER_ENGINE" = "docker" ]; then
    echo -e "  ${CYAN}启动服务:${NC} ${BLUE}systemctl start docker${NC}"
    echo -e "  ${CYAN}停止服务:${NC} ${BLUE}systemctl stop docker${NC}"
    echo -e "  ${CYAN}重启服务:${NC} ${BLUE}systemctl restart docker${NC}"
    echo -e "  ${CYAN}查看状态:${NC} ${BLUE}systemctl status docker${NC}"
    echo -e "  ${CYAN}查看日志:${NC} ${BLUE}journalctl -u docker -f${NC}"
else
    echo -e "  ${CYAN}查看容器:${NC} ${BLUE}podman ps -a${NC}"
    echo -e "  ${CYAN}启动容器:${NC} ${BLUE}podman start <container_id>${NC}"
    echo -e "  ${CYAN}停止容器:${NC} ${BLUE}podman stop <container_id>${NC}"
    echo -e "  ${CYAN}删除容器:${NC} ${BLUE}podman rm <container_id>${NC}"
    echo -e "  ${CYAN}查看日志:${NC} ${BLUE}podman logs <container_id>${NC}"
fi
print_line "═"
echo

ok "安装完成！"
echo
info "如有问题，请查看日志或访问项目文档"
echo
