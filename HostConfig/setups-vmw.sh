#!/bin/bash

# ============================================
# OpenIDCS VMware Workstation 自动化安装配置脚本
# ============================================
# 功能：自动安装并配置 VMware Workstation 及 vmrest API
# 适用：Ubuntu/Debian/CentOS/RHEL/Rocky/Fedora/Arch
# 作者：OpenIDCS Team
# ============================================

set -e

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
FORCE=false
DELETE=false
VMWARE_VERSION=""
VMWARE_BUNDLE=""

# VMware 版本信息
declare -A VMWARE_VERSIONS=(
    ["16"]="VMware-Workstation-Full-16.2.5-20904516.x86_64.bundle"
    ["17"]="VMware-Workstation-Full-17.5.2-23775571.x86_64.bundle"
    ["25H2"]="VMware-Workstation-Full-17.6.0-24238078.x86_64.bundle"
)

declare -A VMWARE_DOWNLOAD_URLS=(
    ["16"]="https://download3.vmware.com/software/WKST-1625-LX/VMware-Workstation-Full-16.2.5-20904516.x86_64.bundle"
    ["17"]="https://download3.vmware.com/software/WKST-1752-LX/VMware-Workstation-Full-17.5.2-23775571.x86_64.bundle"
    ["25H2"]="https://download3.vmware.com/software/WKST-1760-LX/VMware-Workstation-Full-17.6.0-24238078.x86_64.bundle"
)

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

# 参数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force) FORCE=true; shift;;
        -d|--delete) DELETE=true; shift;;
        -v|--version) VMWARE_VERSION="$2"; shift 2;;
        -h|--help)
            print_title "OpenIDCS VMware Workstation 安装脚本 v${SCRIPT_VERSION}"
            echo -e "${WHITE}用法:${NC}"
            echo -e "  ${CYAN}$0${NC} [选项]"
            echo
            echo -e "${WHITE}选项:${NC}"
            echo -e "  ${GREEN}-v, --version <版本>${NC}  指定 VMware 版本 (16/17/25H2)"
            echo -e "  ${GREEN}-f, --force${NC}           强制重新安装（即使已安装）"
            echo -e "  ${RED}-d, --delete${NC}          卸载 VMware Workstation"
            echo -e "  ${BLUE}-h, --help${NC}            显示此帮助信息"
            echo
            echo -e "${WHITE}示例:${NC}"
            echo -e "  ${CYAN}$0${NC}                    ${BLUE}# 交互式安装${NC}"
            echo -e "  ${CYAN}$0 -v 17${NC}              ${BLUE}# 安装 VMware 17${NC}"
            echo -e "  ${CYAN}$0 -f${NC}                 ${BLUE}# 强制重新安装${NC}"
            echo -e "  ${CYAN}$0 -d${NC}                 ${BLUE}# 卸载 VMware${NC}"
            echo
            exit 0;;
        *) err "未知参数: $1 (使用 -h 查看帮助)";;
    esac
done

# 卸载功能
if [[ $DELETE == true ]]; then
    print_title "卸载 VMware Workstation"
    
    warn "此操作将完全卸载 VMware Workstation 及其所有数据！"
    echo
    
    # 检测已安装的 VMware
    FOUND_VMWARE=false
    
    if command -v vmware &> /dev/null; then
        VMWARE_VERSION_INSTALLED=$(vmware --version 2>/dev/null || echo "未知版本")
        echo "  - 检测到已安装的 VMware: $VMWARE_VERSION_INSTALLED"
        FOUND_VMWARE=true
    fi
    
    if [[ $FOUND_VMWARE == false ]]; then
        warn "未检测到已安装的 VMware Workstation"
        exit 0
    fi
    
    echo
    read -p "确定要继续吗? (y/N): " CONFIRM
    if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
        ok "取消卸载操作"
        exit 0
    fi
    
    echo
    info "停止 VMware 服务..."
    systemctl stop vmrest.service 2>/dev/null || true
    systemctl stop vmware.service 2>/dev/null || true
    systemctl stop vmware-workstation-server.service 2>/dev/null || true
    
    info "卸载 VMware Workstation..."
    vmware-installer -u vmware-workstation 2>/dev/null || true
    
    info "清理 VMware 文件和配置..."
    rm -rf /etc/vmware 2>/dev/null || true
    rm -rf /usr/lib/vmware 2>/dev/null || true
    rm -rf /opt/vmware 2>/dev/null || true
    rm -rf ~/.vmware 2>/dev/null || true
    rm -rf /var/lib/vmware 2>/dev/null || true
    rm -rf /var/log/vmware 2>/dev/null || true
    
    info "清理 vmrest 服务..."
    systemctl disable vmrest.service 2>/dev/null || true
    rm -f /etc/systemd/system/vmrest.service 2>/dev/null || true
    systemctl daemon-reload
    
    echo
    ok "VMware Workstation 卸载完成！"
    exit 0
fi

# 检测 Linux 发行版
detect_distro() {
    info "检测操作系统..."
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        info "系统: $NAME $VERSION"
    else
        err "无法检测系统类型"
    fi
}

# 确定包管理器
setup_package_manager() {
    info "检测包管理器..."
    case "$OS" in
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
            else
                PKG_MANAGER="yum"
                PKG_UPDATE="yum check-update || true"
                PKG_INSTALL="yum install -y"
            fi
            info "包管理器: $PKG_MANAGER (RHEL/CentOS)"
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
            warn "未识别的发行版 '$OS'，尝试自动检测..."
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

# 安装依赖包
install_dependencies() {
    print_step "1/7: 安装依赖包"
    
    info "更新软件包列表..."
    eval $PKG_UPDATE
    
    info "安装编译工具和依赖..."
    case "$OS" in
        ubuntu|debian)
            $PKG_INSTALL \
                build-essential \
                linux-headers-$(uname -r) \
                gcc \
                make \
                perl \
                wget \
                curl \
                ca-certificates \
                openssl
            ;;
        centos|rhel|rocky|almalinux)
            $PKG_INSTALL \
                kernel-headers \
                kernel-devel \
                gcc \
                make \
                perl \
                wget \
                curl \
                ca-certificates \
                openssl
            ;;
        fedora)
            $PKG_INSTALL \
                kernel-headers \
                kernel-devel \
                gcc \
                make \
                perl \
                wget \
                curl \
                ca-certificates \
                openssl
            ;;
        arch|manjaro)
            $PKG_INSTALL \
                linux-headers \
                gcc \
                make \
                perl \
                wget \
                curl \
                ca-certificates \
                openssl
            ;;
    esac
    
    ok "依赖包安装完成"
}

# 选择 VMware 版本
select_vmware_version() {
    if [[ -n "$VMWARE_VERSION" ]]; then
        # 验证版本号
        if [[ ! -v VMWARE_VERSIONS[$VMWARE_VERSION] ]]; then
            err "不支持的 VMware 版本: $VMWARE_VERSION (支持: 16, 17, 25H2)"
        fi
        info "使用指定版本: VMware Workstation $VMWARE_VERSION"
        return
    fi
    
    echo
    echo -e "${WHITE}请选择要安装的 VMware Workstation 版本:${NC}"
    echo
    echo -e "  ${CYAN}[1]${NC} VMware Workstation 16.x (16.2.5)"
    echo -e "  ${CYAN}[2]${NC} VMware Workstation 17.x (17.5.2)"
    echo -e "  ${CYAN}[3]${NC} VMware Workstation 17.6 (25H2 兼容版本)"
    echo
    read -p "请输入选项 [1-3, 默认: 2]: " VERSION_CHOICE
    VERSION_CHOICE=${VERSION_CHOICE:-2}
    
    case $VERSION_CHOICE in
        1)
            VMWARE_VERSION="16"
            ;;
        2)
            VMWARE_VERSION="17"
            ;;
        3)
            VMWARE_VERSION="25H2"
            ;;
        *)
            err "无效的选项: $VERSION_CHOICE"
            ;;
    esac
    
    ok "已选择: VMware Workstation $VMWARE_VERSION"
}

# 下载或指定 VMware 安装包
get_vmware_bundle() {
    print_step "2/7: 获取 VMware 安装包"
    
    BUNDLE_NAME="${VMWARE_VERSIONS[$VMWARE_VERSION]}"
    DOWNLOAD_URL="${VMWARE_DOWNLOAD_URLS[$VMWARE_VERSION]}"
    
    echo
    echo -e "${WHITE}获取 VMware 安装包的方式:${NC}"
    echo
    echo -e "  ${CYAN}[1]${NC} 自动下载 (从 VMware 官网)"
    echo -e "  ${CYAN}[2]${NC} 手动指定本地文件路径"
    echo
    read -p "请选择 [1-2, 默认: 1]: " BUNDLE_CHOICE
    BUNDLE_CHOICE=${BUNDLE_CHOICE:-1}
    
    case $BUNDLE_CHOICE in
        1)
            info "准备下载 VMware Workstation $VMWARE_VERSION..."
            echo -e "  ${BLUE}文件名:${NC} $BUNDLE_NAME"
            echo -e "  ${BLUE}下载地址:${NC} $DOWNLOAD_URL"
            echo
            
            DOWNLOAD_DIR="/tmp/vmware-installer"
            mkdir -p "$DOWNLOAD_DIR"
            VMWARE_BUNDLE="$DOWNLOAD_DIR/$BUNDLE_NAME"
            
            if [[ -f "$VMWARE_BUNDLE" ]]; then
                warn "发现已存在的安装包，是否重新下载?"
                read -p "重新下载? (y/N): " REDOWNLOAD
                if [[ $REDOWNLOAD == "y" || $REDOWNLOAD == "Y" ]]; then
                    rm -f "$VMWARE_BUNDLE"
                else
                    ok "使用已存在的安装包"
                    return
                fi
            fi
            
            info "开始下载 (文件较大，请耐心等待)..."
            if wget -O "$VMWARE_BUNDLE" "$DOWNLOAD_URL" --progress=bar:force 2>&1; then
                ok "下载完成"
            else
                err "下载失败，请检查网络连接或手动下载后使用选项 2"
            fi
            ;;
        2)
            echo
            echo -e "${YELLOW}请提供 VMware Workstation 安装包路径${NC}"
            echo -e "${BLUE}提示: 请从 VMware 官网下载对应的 .bundle 文件${NC}"
            echo -e "${BLUE}下载地址: https://www.vmware.com/products/workstation-pro/workstation-pro-evaluation.html${NC}"
            echo
            
            read -p "请输入 .bundle 文件的完整路径: " VMWARE_BUNDLE
            
            if [[ ! -f "$VMWARE_BUNDLE" ]]; then
                err "文件不存在: $VMWARE_BUNDLE"
            fi
            
            ok "使用本地安装包: $VMWARE_BUNDLE"
            ;;
        *)
            err "无效的选项: $BUNDLE_CHOICE"
            ;;
    esac
}

# 安装 VMware Workstation
install_vmware() {
    print_step "3/7: 安装 VMware Workstation"
    
    # 检查是否已安装
    if command -v vmware &> /dev/null && [[ $FORCE == false ]]; then
        INSTALLED_VERSION=$(vmware --version 2>/dev/null || echo "未知版本")
        warn "检测到已安装的 VMware: $INSTALLED_VERSION"
        echo
        read -p "是否继续安装? (y/N): " CONTINUE_INSTALL
        if [[ $CONTINUE_INSTALL != "y" && $CONTINUE_INSTALL != "Y" ]]; then
            ok "跳过 VMware 安装"
            return
        fi
    fi
    
    info "准备安装 VMware Workstation..."
    chmod +x "$VMWARE_BUNDLE"
    
    info "开始安装 (这可能需要几分钟)..."
    echo -e "${BLUE}安装参数: --console --required --eulas-agreed${NC}"
    
    if "$VMWARE_BUNDLE" --console --required --eulas-agreed; then
        ok "VMware Workstation 安装完成"
        
        # 验证安装
        if command -v vmware &> /dev/null; then
            INSTALLED_VERSION=$(vmware --version 2>/dev/null || echo "未知版本")
            ok "安装版本: $INSTALLED_VERSION"
        else
            warn "vmware 命令不可用，但安装可能已完成"
        fi
    else
        err "VMware Workstation 安装失败"
    fi
}

# 查找 vmrest 路径
find_vmrest() {
    print_step "4/7: 配置 vmrest API"
    
    info "查找 vmrest 命令..."
    VMREST_PATH=""
    
    if command -v vmrest &> /dev/null; then
        VMREST_PATH=$(which vmrest)
    elif [[ -f "/usr/bin/vmrest" ]]; then
        VMREST_PATH="/usr/bin/vmrest"
    elif [[ -f "/usr/local/bin/vmrest" ]]; then
        VMREST_PATH="/usr/local/bin/vmrest"
    else
        # 在 VMware 安装目录中查找
        for dir in /usr/lib/vmware /opt/vmware /usr/local/lib/vmware; do
            if [[ -f "$dir/vmrest" ]]; then
                VMREST_PATH="$dir/vmrest"
                break
            fi
        done
    fi
    
    if [[ -z "$VMREST_PATH" ]]; then
        err "无法找到 vmrest，请确认 VMware Workstation 安装正确"
    fi
    
    ok "找到 vmrest: $VMREST_PATH"
}

# 配置 vmrest 凭据
setup_vmrest_credentials() {
    print_step "5/7: 设置 vmrest 凭据"
    
    echo
    read -p "请输入 vmrest API 用户名 [默认: admin]: " VMREST_USER
    VMREST_USER=${VMREST_USER:-admin}
    
    while true; do
        read -sp "请输入 vmrest API 密码: " VMREST_PASS
        echo
        
        if [[ -z "$VMREST_PASS" ]]; then
            warn "密码不能为空，请重新输入"
            continue
        fi
        
        read -sp "请再次输入密码确认: " VMREST_PASS_CONFIRM
        echo
        
        if [[ "$VMREST_PASS" != "$VMREST_PASS_CONFIRM" ]]; then
            warn "两次输入的密码不一致，请重新输入"
            continue
        fi
        
        break
    done
    
    # 创建配置目录
    VMREST_CONFIG_DIR="/etc/vmware/vmrest"
    mkdir -p "$VMREST_CONFIG_DIR"
    
    info "配置 vmrest 凭据..."
    
    # 尝试使用 vmrest -C 命令
    if echo "$VMREST_PASS" | "$VMREST_PATH" -C -u "$VMREST_USER" 2>/dev/null; then
        ok "vmrest 凭据配置成功"
    else
        warn "vmrest -C 命令失败，尝试手动配置..."
        
        # 手动创建配置文件
        VMREST_CRED_FILE="$VMREST_CONFIG_DIR/credentials"
        PASS_HASH=$(echo -n "$VMREST_PASS" | openssl dgst -sha256 | awk '{print $2}')
        
        cat > "$VMREST_CRED_FILE" << EOF
{
  "username": "$VMREST_USER",
  "password": "$PASS_HASH"
}
EOF
        
        chmod 600 "$VMREST_CRED_FILE"
        ok "手动配置完成"
    fi
}

# 配置 vmrest 服务
setup_vmrest_service() {
    print_step "6/7: 配置 vmrest 服务"
    
    echo
    read -p "请输入 vmrest API 监听端口 [默认: 8697]: " VMREST_PORT
    VMREST_PORT=${VMREST_PORT:-8697}
    
    read -p "请输入 vmrest API 监听地址 [默认: 0.0.0.0]: " VMREST_HOST
    VMREST_HOST=${VMREST_HOST:-0.0.0.0}
    
    info "创建 vmrest systemd 服务..."
    
    cat > /etc/systemd/system/vmrest.service << EOF
[Unit]
Description=VMware Workstation REST API Service
After=network.target vmware.service
Wants=vmware.service

[Service]
Type=simple
User=root
ExecStart=$VMREST_PATH -H $VMREST_HOST -p $VMREST_PORT
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    info "重新加载 systemd..."
    systemctl daemon-reload
    
    info "启动并启用 vmrest 服务..."
    systemctl enable vmrest.service
    systemctl start vmrest.service
    
    # 等待服务启动
    sleep 3
    
    # 检查服务状态
    if systemctl is-active --quiet vmrest.service; then
        ok "vmrest 服务启动成功"
    else
        warn "vmrest 服务启动失败"
        echo
        info "查看服务日志:"
        journalctl -u vmrest.service -n 20 --no-pager
        echo
        err "请检查上述日志并修复问题"
    fi
}

# 配置防火墙
configure_firewall() {
    print_step "7/7: 配置防火墙"
    
    echo
    read -p "是否配置防火墙规则? (y/N) [默认: y]: " CONFIG_FIREWALL
    CONFIG_FIREWALL=${CONFIG_FIREWALL:-y}
    
    if [[ $CONFIG_FIREWALL != "y" && $CONFIG_FIREWALL != "Y" ]]; then
        info "跳过防火墙配置"
        return
    fi
    
    FIREWALL_CONFIGURED=false
    
    # 尝试 UFW (Ubuntu/Debian)
    if command -v ufw &> /dev/null; then
        info "配置 UFW 防火墙..."
        ufw allow $VMREST_PORT/tcp comment 'VMware REST API'
        ufw reload
        ok "UFW 防火墙规则已添加"
        FIREWALL_CONFIGURED=true
    fi
    
    # 尝试 firewalld (CentOS/RHEL/Fedora)
    if command -v firewall-cmd &> /dev/null && [[ $FIREWALL_CONFIGURED == false ]]; then
        info "配置 firewalld..."
        firewall-cmd --permanent --add-port=$VMREST_PORT/tcp
        firewall-cmd --reload
        ok "firewalld 规则已添加"
        FIREWALL_CONFIGURED=true
    fi
    
    # 尝试 iptables (通用)
    if command -v iptables &> /dev/null && [[ $FIREWALL_CONFIGURED == false ]]; then
        info "配置 iptables..."
        iptables -A INPUT -p tcp --dport $VMREST_PORT -j ACCEPT
        
        # 尝试保存规则
        case "$OS" in
            ubuntu|debian)
                if ! command -v iptables-persistent &> /dev/null; then
                    $PKG_INSTALL iptables-persistent
                fi
                iptables-save > /etc/iptables/rules.v4
                ;;
            centos|rhel|rocky|almalinux|fedora)
                service iptables save 2>/dev/null || iptables-save > /etc/sysconfig/iptables
                ;;
            arch|manjaro)
                iptables-save > /etc/iptables/iptables.rules
                systemctl enable iptables 2>/dev/null || true
                ;;
        esac
        
        ok "iptables 规则已添加"
        FIREWALL_CONFIGURED=true
    fi
    
    if [[ $FIREWALL_CONFIGURED == false ]]; then
        warn "未检测到支持的防火墙工具"
        echo
        echo -e "${YELLOW}请手动配置防火墙以允许端口: $VMREST_PORT/tcp${NC}"
        echo
        echo -e "${BLUE}示例命令:${NC}"
        echo -e "  ${CYAN}# UFW${NC}"
        echo -e "  ufw allow $VMREST_PORT/tcp"
        echo
        echo -e "  ${CYAN}# firewalld${NC}"
        echo -e "  firewall-cmd --permanent --add-port=$VMREST_PORT/tcp"
        echo -e "  firewall-cmd --reload"
        echo
        echo -e "  ${CYAN}# iptables${NC}"
        echo -e "  iptables -A INPUT -p tcp --dport $VMREST_PORT -j ACCEPT"
        echo
    fi
}

# 测试 vmrest API
test_vmrest_api() {
    info "测试 vmrest API 连接..."
    
    # 等待服务完全启动
    sleep 3
    
    # 获取本机 IP
    SERVER_ADDR=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)
    if [[ -z "$SERVER_ADDR" ]]; then
        SERVER_ADDR="localhost"
    fi
    
    TEST_URL="http://$SERVER_ADDR:$VMREST_PORT/api/vms"
    echo -e "  ${BLUE}测试 URL:${NC} $TEST_URL"
    
    if command -v curl &> /dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -u "$VMREST_USER:$VMREST_PASS" "$TEST_URL" 2>/dev/null || echo "000")
        
        case $HTTP_CODE in
            200)
                ok "vmrest API 测试成功 (HTTP $HTTP_CODE)"
                ;;
            401)
                warn "vmrest API 认证失败 (HTTP $HTTP_CODE)"
                echo -e "  ${YELLOW}请检查用户名和密码是否正确${NC}"
                ;;
            000)
                warn "无法连接到 vmrest API"
                echo -e "  ${YELLOW}请检查服务是否正常运行: systemctl status vmrest.service${NC}"
                ;;
            *)
                warn "vmrest API 响应异常 (HTTP $HTTP_CODE)"
                echo -e "  ${YELLOW}服务可能正在启动，请稍后手动测试${NC}"
                ;;
        esac
    else
        warn "curl 未安装，无法测试 API 连接"
        info "请手动测试: curl -u $VMREST_USER:*** $TEST_URL"
    fi
}

# 显示配置摘要
show_summary() {
    print_title "✓ 安装完成！配置信息汇总"
    
    ok "VMware Workstation 已成功安装并配置完成！"
    echo
    
    # 获取本机 IP
    SERVER_ADDR=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)
    if [[ -z "$SERVER_ADDR" ]]; then
        SERVER_ADDR=$(hostname -I | awk '{print $1}')
    fi
    
    # 系统信息
    print_line "═"
    echo -e "${WHITE}系统信息${NC}"
    print_line "─"
    printf "  %-24s %s\n" "${CYAN}操作系统:${NC}" "$OS ${OS_VERSION:-未知版本}"
    printf "  %-24s %s\n" "${CYAN}VMware 版本:${NC}" "$(vmware --version 2>/dev/null || echo '未知')"
    printf "  %-24s %s\n" "${CYAN}vmrest 路径:${NC}" "$VMREST_PATH"
    print_line "═"
    echo
    
    # 配置信息
    print_line "═"
    echo -e "${WHITE}【服务器基本配置】${NC}"
    print_line "─"
    printf "  %-24s ${YELLOW}%-20s${NC} ${BLUE}%s${NC}\n" "服务器名称:" "<请自定义>" "(自定义一个易识别的名称)"
    printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "服务器类型:" "vmware" "(固定值)"
    printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "服务器地址:" "$SERVER_ADDR" "(本机IP地址)"
    printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "服务器端口:" "$VMREST_PORT" "(vmrest API端口)"
    printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "用户名:" "$VMREST_USER" "(API认证用户名)"
    printf "  %-24s ${YELLOW}%-20s${NC} ${BLUE}%s${NC}\n" "密码:" "********" "(您设置的密码)"
    print_line "═"
    echo
    
    # API 端点
    print_line "═"
    echo -e "${WHITE}【API 端点】${NC}"
    print_line "─"
    echo -e "  ${CYAN}虚拟机列表:${NC}"
    echo -e "    http://$SERVER_ADDR:$VMREST_PORT/api/vms"
    echo
    echo -e "  ${CYAN}网络列表:${NC}"
    echo -e "    http://$SERVER_ADDR:$VMREST_PORT/api/vmnets"
    echo
    echo -e "  ${CYAN}API 文档:${NC}"
    echo -e "    http://$SERVER_ADDR:$VMREST_PORT/api/swagger"
    print_line "═"
    echo
    
    # 测试命令
    print_line "═"
    echo -e "${WHITE}【测试命令】${NC}"
    print_line "─"
    echo -e "  ${BLUE}# 列出所有虚拟机${NC}"
    echo -e "  ${CYAN}curl -u $VMREST_USER:$VMREST_PASS http://$SERVER_ADDR:$VMREST_PORT/api/vms${NC}"
    echo
    echo -e "  ${BLUE}# 获取虚拟机详情${NC}"
    echo -e "  ${CYAN}curl -u $VMREST_USER:$VMREST_PASS http://$SERVER_ADDR:$VMREST_PORT/api/vms/{vm_id}${NC}"
    echo
    echo -e "  ${BLUE}# 启动虚拟机${NC}"
    echo -e "  ${CYAN}curl -X PUT -u $VMREST_USER:$VMREST_PASS http://$SERVER_ADDR:$VMREST_PORT/api/vms/{vm_id}/power -d 'on'${NC}"
    print_line "═"
    echo
    
    # 管理命令
    print_line "═"
    echo -e "${WHITE}【服务管理命令】${NC}"
    print_line "─"
    echo -e "  ${CYAN}启动服务:${NC}   systemctl start vmrest.service"
    echo -e "  ${CYAN}停止服务:${NC}   systemctl stop vmrest.service"
    echo -e "  ${CYAN}重启服务:${NC}   systemctl restart vmrest.service"
    echo -e "  ${CYAN}查看状态:${NC}   systemctl status vmrest.service"
    echo -e "  ${CYAN}查看日志:${NC}   journalctl -u vmrest.service -f"
    print_line "═"
    echo
    
    # 注意事项
    print_line "═"
    echo -e "${WHITE}【注意事项】${NC}"
    print_line "─"
    echo -e "  ${GREEN}1.${NC} vmrest 服务已设置为开机自启动"
    echo -e "  ${GREEN}2.${NC} 确保防火墙允许 $VMREST_PORT 端口访问"
    echo -e "  ${GREEN}3.${NC} 建议定期更改 API 密码以提高安全性"
    echo -e "  ${GREEN}4.${NC} 如需修改配置，请编辑 /etc/systemd/system/vmrest.service"
    echo -e "  ${GREEN}5.${NC} 配置文件位置: $VMREST_CONFIG_DIR"
    print_line "═"
    echo
    
    ok "安装完成！"
    echo
}

# 主流程
main() {
    print_title "OpenIDCS VMware Workstation 安装向导 v${SCRIPT_VERSION}"
    
    # 检测系统环境
    detect_distro
    setup_package_manager
    
    # 安装依赖
    install_dependencies
    
    # 选择版本
    select_vmware_version
    
    # 获取安装包
    get_vmware_bundle
    
    # 安装 VMware
    install_vmware
    
    # 配置 vmrest
    find_vmrest
    setup_vmrest_credentials
    setup_vmrest_service
    
    # 配置防火墙
    configure_firewall
    
    # 测试 API
    test_vmrest_api
    
    # 显示摘要
    show_summary
}

# 执行主流程
main
