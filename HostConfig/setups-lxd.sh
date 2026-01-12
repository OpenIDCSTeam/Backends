#!/bin/bash

# ============================================
# OpenIDCS LXD 自动化安装配置脚本
# ============================================
# 功能：自动安装并配置 LXD 容器虚拟化环境
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
NAME="LXD"
FORCE=false
DELETE=false
SCRIPT_VERSION="1.0.0"

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

[[ $EUID -ne 0 ]] && err "请使用 root 运行"

while [[ $# -gt 0 ]]; do
  case $1 in
    -f|--force) FORCE=true; shift;;
    -d|--delete) DELETE=true; shift;;
    -h|--help)
      print_title "OpenIDCS LXD 安装脚本 v${SCRIPT_VERSION}"
      echo -e "${WHITE}用法:${NC}"
      echo -e "  ${CYAN}$0${NC} [选项]"
      echo
      echo -e "${WHITE}选项:${NC}"
      echo -e "  ${GREEN}-f, --force${NC}    强制重新安装（即使已安装 LXD）"
      echo -e "  ${RED}-d, --delete${NC}   卸载 LXD 及所有数据"
      echo -e "  ${BLUE}-h, --help${NC}     显示此帮助信息"
      echo
      echo -e "${WHITE}示例:${NC}"
      echo -e "  ${CYAN}$0${NC}              ${BLUE}# 安装 LXD${NC}"
      echo -e "  ${CYAN}$0 -f${NC}           ${BLUE}# 强制重新安装${NC}"
      echo -e "  ${CYAN}$0 -d${NC}           ${BLUE}# 卸载 LXD${NC}"
      echo
      echo -e "${WHITE}详细教程:${NC} ${CYAN}https://github.com/xkatld/zjmf-lxd-server/wiki${NC}"
      echo
      exit 0;;
    *) err "未知参数: $1 (使用 -h 查看帮助)";;
  esac
done

if [[ $DELETE == true ]]; then
  print_title "卸载 LXD"
  
  warn "此操作将完全卸载 LXD 及其所有数据！"
  echo
  
  # 检测已安装的 LXD
  FOUND_LXD=false
  
  if [[ -f /snap/bin/lxd || -f /snap/bin/lxc || -f /var/lib/snapd/snap/bin/lxd || -f /var/lib/snapd/snap/bin/lxc ]]; then
    echo "  - 检测到 Snap 安装的 LXD"
    FOUND_LXD=true
  fi
  
  if [[ -f /usr/bin/lxd || -f /usr/bin/lxc ]]; then
    echo "  - 检测到 APT/DEB 安装的 LXD"
    FOUND_LXD=true
  fi
  
  if [[ -f /usr/local/bin/lxd || -f /usr/local/bin/lxc ]]; then
    echo "  - 检测到本地编译的 LXD"
    FOUND_LXD=true
  fi
  
  if [[ $FOUND_LXD == false ]]; then
    warn "未检测到已安装的 LXD"
    exit 0
  fi
  
  echo
  read -p "确定要继续吗? (y/N): " CONFIRM
  if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
    ok "取消卸载操作"
    exit 0
  fi
  
  echo
  info "停止 LXD 服务..."
  systemctl stop lxd 2>/dev/null || true
  systemctl stop lxd.socket 2>/dev/null || true
  systemctl stop lxd-containers 2>/dev/null || true
  
  # 检测包管理器
  PKG_MANAGER=""
  if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
  elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
  elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
  elif command -v zypper &> /dev/null; then
    PKG_MANAGER="zypper"
  elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
  fi
  
  # 卸载 Snap LXD
  if [[ -f /snap/bin/lxd || -f /snap/bin/lxc || -f /var/lib/snapd/snap/bin/lxd || -f /var/lib/snapd/snap/bin/lxc ]]; then
    info "卸载 Snap LXD..."
    snap remove lxd 2>/dev/null || warn "Snap LXD 卸载失败"
  fi
  
  # 卸载 APT/DEB LXD
  if [[ -f /usr/bin/lxd || -f /usr/bin/lxc ]]; then
    info "卸载 APT/DEB LXD..."
    case $PKG_MANAGER in
      apt)
        apt-get purge -y lxd lxd-client lxc lxc-utils 2>/dev/null || true
        apt-get autoremove -y 2>/dev/null || true
        ;;
      yum)
        yum remove -y lxd lxc 2>/dev/null || true
        ;;
      dnf)
        dnf remove -y lxd lxc 2>/dev/null || true
        ;;
      zypper)
        zypper remove -y lxd lxc 2>/dev/null || true
        ;;
      pacman)
        pacman -Rns --noconfirm lxd lxc 2>/dev/null || true
        ;;
    esac
  fi
  
  # 删除本地编译的 LXD
  if [[ -f /usr/local/bin/lxd || -f /usr/local/bin/lxc ]]; then
    info "删除本地编译的 LXD..."
    rm -f /usr/local/bin/lxd /usr/local/bin/lxc 2>/dev/null || true
  fi
  
  info "清理 LXD 数据和配置..."
  rm -rf /var/lib/lxd 2>/dev/null || true
  rm -rf /var/log/lxd 2>/dev/null || true
  rm -rf /etc/lxd 2>/dev/null || true
  rm -rf ~/.config/lxc 2>/dev/null || true
  
  info "清理环境变量配置..."
  if [[ -f /etc/profile.d/snap.sh ]]; then
    rm -f /etc/profile.d/snap.sh
    ok "已删除环境变量配置文件"
  fi
  
  info "清理符号链接..."
  if [[ -L /snap ]]; then
    rm -f /snap
    ok "已删除符号链接 /snap"
  fi
  
  echo
  ok "LXD 卸载完成！"
  echo
  warn "环境变量已清理，建议重新登录系统或重启终端"
  exit 0
fi

# 检测并修复 squashfs 支持
check_squashfs_support() {
    info "检查 squashfs 文件系统支持..."
    
    # 检查内核是否支持 squashfs
    if grep -q squashfs /proc/filesystems 2>/dev/null; then
        ok "squashfs 已加载"
        return 0
    fi
    
    warn "squashfs 未加载，尝试加载模块..."
    
    # 尝试加载 squashfs 模块
    if modprobe squashfs 2>/dev/null; then
        ok "squashfs 模块加载成功"
        # 确保重启后自动加载
        echo "squashfs" >> /etc/modules-load.d/squashfs.conf 2>/dev/null || true
        return 0
    fi
    
    warn "无法加载 squashfs 模块，尝试安装..."
    
    # 根据发行版安装 squashfs 工具和内核模块
    case $DISTRO in
        ubuntu|debian)
            apt-get update
            apt-get install -y squashfs-tools linux-modules-extra-$(uname -r) 2>/dev/null || \
            apt-get install -y squashfs-tools linux-image-$(uname -r) 2>/dev/null || true
            ;;
        centos|rhel|rocky|almalinux)
            yum install -y squashfs-tools kernel-modules-extra 2>/dev/null || \
            dnf install -y squashfs-tools kernel-modules 2>/dev/null || true
            ;;
        fedora)
            dnf install -y squashfs-tools kernel-modules 2>/dev/null || true
            ;;
        arch|manjaro)
            pacman -Sy --noconfirm squashfs-tools 2>/dev/null || true
            ;;
    esac
    
    # 再次尝试加载模块
    if modprobe squashfs 2>/dev/null; then
        ok "squashfs 模块安装并加载成功"
        echo "squashfs" >> /etc/modules-load.d/squashfs.conf 2>/dev/null || true
        return 0
    fi
    
    # 检查是否在容器环境中
    if [ -f /.dockerenv ] || grep -q "lxc\|docker" /proc/1/cgroup 2>/dev/null; then
        warn "检测到容器环境，squashfs 可能不被支持"
        warn "将使用原生包管理器而非 snap 安装 LXD"
        return 1
    fi
    
    warn "无法启用 squashfs 支持，snap 可能无法正常工作"
    return 1
}

# 检测 Linux 发行版
detect_distro() {
    info "检测操作系统..."
    if [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    else
        DISTRO="unknown"
    fi
    
    info "系统: $DISTRO ${VERSION:-未知版本}"
}

print_title "OpenIDCS LXD 安装向导 v${SCRIPT_VERSION}"

print_step "1/7: 检测系统环境"

detect_distro

info "检测系统架构..."
arch=$(uname -m)
case $arch in
    x86_64)
        info "架构: amd64"
        ;;
    aarch64|arm64)
        info "架构: arm64"
        ;;
    *)
        err "不支持的架构: $arch (仅支持 amd64/arm64)"
        ;;
esac

info "检查 LXD 是否已安装..."
LXD_INSTALLED=false
INSTALL_TYPE=""

if [[ -f /snap/bin/lxd || -f /snap/bin/lxc || -f /var/lib/snapd/snap/bin/lxd || -f /var/lib/snapd/snap/bin/lxc ]]; then
    LXD_INSTALLED=true
    INSTALL_TYPE="snap"
fi

if [[ -f /usr/bin/lxd || -f /usr/bin/lxc ]]; then
    LXD_INSTALLED=true
    INSTALL_TYPE="${INSTALL_TYPE:+$INSTALL_TYPE 和 }apt/deb"
fi

if [[ -f /usr/local/bin/lxd || -f /usr/local/bin/lxc ]]; then
    LXD_INSTALLED=true
    INSTALL_TYPE="${INSTALL_TYPE:+$INSTALL_TYPE 和 }本地编译"
fi

if [[ $LXD_INSTALLED == true ]]; then
    if [[ $FORCE == true ]]; then
        echo
        warn "检测到 LXD 已安装 (安装方式: $INSTALL_TYPE)"
        warn "使用了 -f 参数，将强制重新安装"
        echo
        read -p "确定要继续吗? (y/N): " FORCE_CONFIRM
        if [[ $FORCE_CONFIRM != "y" && $FORCE_CONFIRM != "Y" ]]; then
            ok "取消重新安装操作"
            exit 0
        fi
    else
        echo
        err "LXD 已安装 (安装方式: $INSTALL_TYPE)
    
提示：
  - 卸载: $0 -d
  - 强制重新安装: $0 -f"
    fi
fi

ok "环境检测通过"

# 检查 squashfs 支持（snap 需要）
check_squashfs_support
SQUASHFS_SUPPORTED=$?

print_step "2/7: 安装 Snap 包管理器"

info "检测 snapd 是否已安装..."
SNAPD_INSTALLED=false
if [[ -f /usr/bin/snap || -f /usr/sbin/snapd || -f /usr/lib/snapd/snapd ]]; then
    SNAPD_INSTALLED=true
    info "检测到 snapd 已安装"
fi

info "检测包管理器..."
PKG_MANAGER=""
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
    info "包管理器: APT (Debian/Ubuntu)"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    info "包管理器: YUM (CentOS/RHEL)"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    info "包管理器: DNF (Fedora/RHEL 8+)"
elif command -v zypper &> /dev/null; then
    PKG_MANAGER="zypper"
    info "包管理器: Zypper (openSUSE)"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
    info "包管理器: Pacman (Arch Linux)"
else
    err "无法检测到支持的包管理器"
fi

if [[ $SNAPD_INSTALLED == true ]]; then
    info "卸载旧的 snapd..."
    case $PKG_MANAGER in
        apt)
            apt-get purge -y snapd 2>/dev/null || true
            apt-get autoremove -y 2>/dev/null || true
            ;;
        yum)
            yum remove -y snapd 2>/dev/null || true
            ;;
        dnf)
            dnf remove -y snapd 2>/dev/null || true
            ;;
        zypper)
            zypper remove -y snapd 2>/dev/null || true
            ;;
        pacman)
            pacman -Rns --noconfirm snapd 2>/dev/null || true
            ;;
    esac
fi

info "更新软件包列表..."
case $PKG_MANAGER in
    apt)
        apt-get update -y || err "软件包列表更新失败"
        ;;
    yum)
        yum makecache -y || warn "软件包缓存更新失败"
        ;;
    dnf)
        dnf makecache -y || warn "软件包缓存更新失败"
        ;;
    zypper)
        zypper refresh || warn "软件包列表更新失败"
        ;;
    pacman)
        pacman -Sy || warn "软件包列表更新失败"
        ;;
esac

info "安装 snapd..."
case $PKG_MANAGER in
    apt)
        apt-get install -y snapd || err "snapd 安装失败"
        ;;
    yum)
        yum install -y epel-release || true
        yum install -y snapd || err "snapd 安装失败"
        ;;
    dnf)
        dnf install -y snapd || err "snapd 安装失败"
        ;;
    zypper)
        zypper install -y snapd || err "snapd 安装失败"
        ;;
    pacman)
        pacman -S --noconfirm snapd || err "snapd 安装失败"
        ;;
esac

info "启用 snapd 服务..."
systemctl enable --now snapd || err "snapd 服务启用失败"
systemctl enable --now snapd.socket 2>/dev/null || true

# RHEL/CentOS/AlmaLinux 等系统需要额外启用 snapd.seeded
if [[ "$PKG_MANAGER" == "yum" || "$PKG_MANAGER" == "dnf" ]]; then
    info "启用 snapd.seeded 服务 (RHEL/CentOS 系统)..."
    systemctl enable --now snapd.seeded 2>/dev/null || true
fi

info "配置系统环境变量..."
if [[ ! -f /etc/profile.d/snap.sh ]]; then
  cat > /etc/profile.d/snap.sh <<'EOF'
# 添加 Snap 二进制文件目录到 PATH
# 支持不同发行版的 snap 路径
export PATH="/snap/bin:/var/lib/snapd/snap/bin:$PATH"
EOF
  chmod +x /etc/profile.d/snap.sh
  ok "环境变量配置已写入 /etc/profile.d/snap.sh"
else
  info "环境变量配置已存在"
fi

info "更新当前会话环境变量..."
export PATH="/snap/bin:/var/lib/snapd/snap/bin:$PATH"

info "等待 snapd 服务就绪..."
sleep 5

info "查询 snap 版本..."
if [[ -f /usr/bin/snap ]]; then
    SNAP_VERSION=$(/usr/bin/snap --version 2>/dev/null | head -1 || echo "未知")
    ok "Snap 版本: $SNAP_VERSION"
else
    warn "snap 命令不可用"
fi

print_step "3/7: 安装 LXD 容器引擎"

info "创建必要的系统目录..."
mkdir -p /usr/src 2>/dev/null || true
mkdir -p /lib/modules 2>/dev/null || true

info "安装 LXD (Snap)..."
snap install lxd --channel=latest/stable || err "LXD 安装失败"

info "更新当前会话环境变量..."
export PATH="/snap/bin:/var/lib/snapd/snap/bin:$PATH"

info "检测 LXD 安装路径..."
LXD_BIN_DIR=""
if [[ -f /snap/bin/lxd ]]; then
    LXD_BIN_DIR="/snap/bin"
    ok "LXD 路径: /snap/bin (Debian/Ubuntu 风格)"
elif [[ -f /var/lib/snapd/snap/bin/lxd ]]; then
    LXD_BIN_DIR="/var/lib/snapd/snap/bin"
    ok "LXD 路径: /var/lib/snapd/snap/bin (RHEL/CentOS 风格)"
    
    # 创建符号链接以保持一致性
    info "创建符号链接 /snap -> /var/lib/snapd/snap..."
    if [[ ! -e /snap ]]; then
        ln -s /var/lib/snapd/snap /snap 2>/dev/null || warn "符号链接创建失败（不影响使用）"
    fi
else
    err "lxd 命令不可用，安装失败"
fi

info "验证 LXD 安装..."
if [[ ! -f "$LXD_BIN_DIR/lxd" ]]; then
    err "lxd 命令不可用，安装失败"
fi

if [[ ! -f "$LXD_BIN_DIR/lxc" ]]; then
    err "lxc 命令不可用，安装失败"
fi

ok "LXD 安装验证通过"

print_step "4/7: 优化系统配置"

info "配置性能优化..."
snap set lxd daemon.debug=false 2>/dev/null || warn "性能优化配置失败"

info "重启 LXD 服务..."
snap restart lxd 2>/dev/null || warn "LXD 服务重启失败"

info "等待 LXD 服务就绪..."
sleep 3

echo
ok "LXD 安装完成！"
echo -e "  ${CYAN}安装路径:${NC} $LXD_BIN_DIR"
echo -e "  ${CYAN}LXD 版本:${NC} $($LXD_BIN_DIR/lxd --version 2>/dev/null || echo '未知')"
echo -e "  ${CYAN}LXC 版本:${NC} $($LXD_BIN_DIR/lxc --version 2>/dev/null || echo '未知')"
echo -e "  ${CYAN}性能优化:${NC} 已关闭调试日志"

print_step "5/7: 收集配置参数"

info "请根据提示输入配置参数（直接回车使用默认值）"
echo

# 收集用户输入的参数
echo -e "${YELLOW}[1/7]${NC} 镜像存储路径 ${BLUE}(用于存放容器镜像文件)${NC}"
read -p "      路径 [默认: /opt/oidc/lxcapi/images]: " IMAGES_PATH
IMAGES_PATH=${IMAGES_PATH:-/opt/oidc/lxcapi/images}
echo

echo -e "${YELLOW}[2/7]${NC} 系统存储路径 ${BLUE}(用于存放容器系统文件)${NC}"
read -p "      路径 [默认: /opt/oidc/lxcapi/system]: " SYSTEM_PATH
SYSTEM_PATH=${SYSTEM_PATH:-/opt/oidc/lxcapi/system}
echo

echo -e "${YELLOW}[3/7]${NC} 备份存储路径 ${BLUE}(用于存放容器备份文件)${NC}"
read -p "      路径 [默认: /opt/oidc/lxcapi/backup]: " BACKUP_PATH
BACKUP_PATH=${BACKUP_PATH:-/opt/oidc/lxcapi/backup}
echo

echo -e "${YELLOW}[4/7]${NC} API密钥存储路径 ${BLUE}(用于存放认证证书)${NC}"
read -p "      路径 [默认: /opt/oidc/lxcapi/apikey]: " LAUNCH_PATH
LAUNCH_PATH=${LAUNCH_PATH:-/opt/oidc/lxcapi/apikey}
echo

echo -e "${YELLOW}[5/7]${NC} 内网网桥名称 ${BLUE}(NAT网络接口)${NC}"
read -p "      名称 [默认: lxdbr0]: " NETWORK_NAT
NETWORK_NAT=${NETWORK_NAT:-lxdbr0}
echo

echo -e "${YELLOW}[6/7]${NC} 外网网桥名称 ${BLUE}(公网网络接口)${NC}"
read -p "      名称 [默认: lxdbr1]: " NETWORK_PUB
NETWORK_PUB=${NETWORK_PUB:-lxdbr1}
echo

echo -e "${YELLOW}[7/7]${NC} SSH密码 ${BLUE}(用于LXD API认证)${NC}"
read -s -p "      密码: " SERVER_PASS
echo
echo

# 创建必要的目录
info "创建配置目录..."
if mkdir -p "$IMAGES_PATH" 2>/dev/null; then
    ok "镜像目录: $IMAGES_PATH"
else
    err "创建镜像目录失败: $IMAGES_PATH"
fi

if mkdir -p "$SYSTEM_PATH" 2>/dev/null; then
    ok "系统目录: $SYSTEM_PATH"
else
    err "创建系统目录失败: $SYSTEM_PATH"
fi

if mkdir -p "$BACKUP_PATH" 2>/dev/null; then
    ok "备份目录: $BACKUP_PATH"
else
    err "创建备份目录失败: $BACKUP_PATH"
fi

if mkdir -p "$LAUNCH_PATH" 2>/dev/null; then
    ok "证书目录: $LAUNCH_PATH"
else
    err "创建证书目录失败: $LAUNCH_PATH"
fi

echo
ok "所有配置目录创建完成"

print_step "6/7: 初始化 LXD 环境"

info "使用 preseed 配置自动初始化 LXD..."
echo -e "  ${CYAN}存储后端:${NC} dir (路径: $SYSTEM_PATH)"
echo -e "  ${CYAN}内网网桥:${NC} $NETWORK_NAT (10.0.3.1/24)"
echo -e "  ${CYAN}HTTPS API:${NC} [::]:8443"
echo

# 检查并清理可能存在的冲突
info "检查现有 LXD 配置..."
if $LXD_BIN_DIR/lxc network list 2>/dev/null | grep -q "$NETWORK_NAT"; then
    warn "发现已存在的 $NETWORK_NAT 网络，正在清理..."
    $LXD_BIN_DIR/lxc network delete "$NETWORK_NAT" 2>/dev/null || true
fi

# 检查 dnsmasq 进程
if pgrep -f "dnsmasq.*$NETWORK_NAT" > /dev/null; then
    warn "发现运行中的 dnsmasq 进程，正在停止..."
    pkill -f "dnsmasq.*$NETWORK_NAT" 2>/dev/null || true
    sleep 2
fi

# 使用 preseed 配置自动初始化
cat <<EOF | $LXD_BIN_DIR/lxd init --preseed
config:
  core.https_address: '[::]:8443'
  core.trust_password: '$SERVER_PASS'
networks:
- config:
    ipv4.address: 10.10.10.1/24
    ipv4.nat: "true"
    ipv6.address: none
  description: "LXD internal network"
  name: $NETWORK_NAT
  type: bridge
  project: default
storage_pools:
- config:
    source: $SYSTEM_PATH
  name: default
  driver: dir
profiles:
- config: {}
  description: "Default LXD profile"
  devices:
    eth0:
      name: eth0
      nictype: bridged
      parent: $NETWORK_NAT
      type: nic
    root:
      path: /
      pool: default
      type: disk
  name: default
projects: []
EOF

if [[ $? -eq 0 ]]; then
    echo
    ok "LXD 初始化完成！"
    echo
    info "验证 LXD 配置..."
    $LXD_BIN_DIR/lxc network list 2>/dev/null && ok "网络配置正常"
    $LXD_BIN_DIR/lxc storage list 2>/dev/null && ok "存储池配置正常"
else
    echo
    warn "LXD 自动初始化失败，尝试交互式初始化..."
    echo
    warn "请按照提示配置 LXD："
    echo "  - 存储后端推荐: dir (使用 $SYSTEM_PATH 作为存储位置)"
    echo "  - 网络配置："
    echo "    * 内网网桥: $NETWORK_NAT"
    echo "    * 外网网桥: $NETWORK_PUB"
    echo "  - 建议配置："
    echo "    * Would you like to use LXD clustering? (yes/no) [default=no]: no"
    echo "    * Do you want to configure a new storage pool? (yes/no) [default=yes]: yes"
    echo "    * Name of the new storage pool [default=default]: default"
    echo "    * Name of the storage backend to use (dir, lvm, zfs, btrfs) [default=zfs]: dir"
    echo "    * Would you like to create a new local network bridge? (yes/no) [default=yes]: yes"
    echo "    * What should the new bridge be called? [default=lxdbr0]: $NETWORK_NAT"
    echo
    
    # 执行 lxd init 命令，让用户交互式配置
    $LXD_BIN_DIR/lxd init
    
    if [[ $? -eq 0 ]]; then
        echo
        ok "LXD 初始化完成！"
        echo
        info "验证 LXD 配置..."
        $LXD_BIN_DIR/lxc network list 2>/dev/null && ok "网络配置正常"
        $LXD_BIN_DIR/lxc storage list 2>/dev/null && ok "存储池配置正常"
    else
        echo
        err "LXD 初始化失败"
    fi
fi

print_step "7/7: 生成配置信息"

# 创建外网网桥（如果需要）
info "配置外网网桥..."
if ! $LXD_BIN_DIR/lxc network list 2>/dev/null | grep -q "$NETWORK_PUB"; then
    read -p "是否创建外网网桥 $NETWORK_PUB? (y/N): " CREATE_PUB
    if [[ $CREATE_PUB == "y" || $CREATE_PUB == "Y" ]]; then
        info "创建外网网桥: $NETWORK_PUB"
        $LXD_BIN_DIR/lxc network create "$NETWORK_PUB" ipv4.address=none ipv6.address=none 2>/dev/null && ok "外网网桥创建成功" || warn "外网网桥创建失败"
    else
        info "跳过外网网桥创建，可稍后手动执行："
        echo "  $LXD_BIN_DIR/lxc network create $NETWORK_PUB"
    fi
else
    ok "外网网桥 $NETWORK_PUB 已存在"
fi

# 配置防火墙
info "配置防火墙..."
case $DISTRO in
    ubuntu|debian)
        if command -v ufw &> /dev/null; then
            info "配置 UFW 防火墙..."
            ufw allow 8443/tcp comment "LXD HTTPS API" 2>/dev/null && ok "防火墙规则已添加" || warn "防火墙配置失败"
            ufw reload 2>/dev/null || true
        else
            warn "UFW 未安装，请手动配置防火墙开放 8443 端口"
        fi
        ;;
    centos|rhel|rocky|almalinux|fedora)
        if command -v firewall-cmd &> /dev/null; then
            info "配置 firewalld 防火墙..."
            firewall-cmd --permanent --add-port=8443/tcp 2>/dev/null && ok "防火墙规则已添加" || warn "防火墙配置失败"
            firewall-cmd --reload 2>/dev/null || true
        else
            warn "firewalld 未安装，请手动配置防火墙开放 8443 端口"
        fi
        ;;
    arch|manjaro)
        if command -v ufw &> /dev/null; then
            info "配置 UFW 防火墙..."
            ufw allow 8443/tcp comment "LXD HTTPS API" 2>/dev/null && ok "防火墙规则已添加" || warn "防火墙配置失败"
            ufw reload 2>/dev/null || true
        elif command -v firewall-cmd &> /dev/null; then
            info "配置 firewalld 防火墙..."
            firewall-cmd --permanent --add-port=8443/tcp 2>/dev/null && ok "防火墙规则已添加" || warn "防火墙配置失败"
            firewall-cmd --reload 2>/dev/null || true
        else
            warn "未检测到防火墙，请手动添加规则："
            echo "  iptables -A INPUT -p tcp --dport 8443 -j ACCEPT"
        fi
        ;;
    *)
        warn "未检测到防火墙或不支持的发行版，请手动配置防火墙以允许 8443/tcp 端口"
        ;;
esac

info "配置 LXD API 访问..."

# 设置 LXD 监听地址（如果 preseed 失败）
$LXD_BIN_DIR/lxc config set core.https_address "[::]:8443" 2>/dev/null || info "HTTPS 地址已配置"
$LXD_BIN_DIR/lxc config set core.trust_password "$SERVER_PASS" 2>/dev/null || info "信任密码已配置"

# 生成客户端证书
info "生成客户端证书..."
if [[ ! -f "$LAUNCH_PATH/client.crt" || ! -f "$LAUNCH_PATH/client.key" ]]; then
    openssl req -x509 -newkey rsa:4096 -keyout "$LAUNCH_PATH/client.key" -out "$LAUNCH_PATH/client.crt" -days 3650 -nodes -subj "/CN=lxd-client" 2>/dev/null
    if [[ $? -eq 0 ]]; then
        ok "客户端证书生成成功"
        chmod 600 "$LAUNCH_PATH/client.key"
        chmod 644 "$LAUNCH_PATH/client.crt"
        
        # 添加客户端证书到 LXD 信任列表
        info "添加客户端证书到 LXD 信任列表..."
        $LXD_BIN_DIR/lxc config trust add "$LAUNCH_PATH/client.crt" 2>/dev/null && ok "证书已添加到信任列表" || info "证书可能已添加"
    else
        warn "客户端证书生成失败，请手动生成"
    fi
else
    info "客户端证书已存在"
fi

# 获取本机外网地址
info "获取本机网络地址..."
SERVER_ADDR=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)
if [[ -z "$SERVER_ADDR" ]]; then
    warn "无法自动获取网络地址，请手动指定"
    echo -e "  ${BLUE}提示: 请输入服务器的外网IP地址或内网IP地址${NC}"
    read -p "  地址: " SERVER_ADDR
    if [[ -z "$SERVER_ADDR" ]]; then
        err "服务器地址不能为空"
    fi
else
    ok "检测到服务器地址: $SERVER_ADDR"
fi

# 获取 LXD API 端口
SERVER_PORT=8443
LXD_PORT=$($LXD_BIN_DIR/lxc config get core.https_address 2>/dev/null | grep -oP '\d+$')
if [[ -n "$LXD_PORT" ]]; then
    SERVER_PORT=$LXD_PORT
fi

print_title "✓ 安装完成！配置信息汇总"

ok "LXD 已成功安装并配置完成！"
echo

# 系统信息
print_line "═"
echo -e "${WHITE}系统信息${NC}"
print_line "─"
printf "  %-20s %s\n" "${CYAN}操作系统:${NC}" "$DISTRO ${VERSION:-未知版本}"
printf "  %-20s %s\n" "${CYAN}系统架构:${NC}" "$(uname -m)"
printf "  %-20s %s\n" "${CYAN}LXD 版本:${NC}" "$($LXD_BIN_DIR/lxd --version 2>/dev/null || echo '未知')"
printf "  %-20s %s\n" "${CYAN}安装路径:${NC}" "$LXD_BIN_DIR"
print_line "═"
echo

info "请将以下配置信息填写到 ${YELLOW}OpenIDCS Web 管理端${NC}："
echo

# 服务器基本配置
print_line "═"
echo -e "${WHITE}【服务器基本配置】${NC}"
print_line "─"
printf "  %-24s ${YELLOW}%-20s${NC} ${BLUE}%s${NC}\n" "服务器名称:" "<请自定义>" "(自定义一个易识别的名称)"
printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "服务器类型:" "LxContainer" "(固定值，请勿修改)"
printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "服务器地址:" "$SERVER_ADDR" "(本机IP地址)"
printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "服务器用户:" "root" "(固定为root用户)"
printf "  %-24s ${YELLOW}%-20s${NC} ${BLUE}%s${NC}\n" "服务器密码:" "<您输入的密码>" "(SSH密码)"
printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "服务器端口:" "$SERVER_PORT" "(LXD API端口)"
printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "前缀过滤名称:" "lxc_" "(容器名称前缀)"
print_line "═"
echo

# 存储路径配置
print_line "═"
echo -e "${WHITE}【存储路径配置】${NC}"
print_line "─"
printf "  %-24s ${GREEN}%s${NC}\n" "虚拟机的镜像:" "$IMAGES_PATH"
printf "  %-24s ${GREEN}%s${NC}\n" "虚拟机的系统:" "$SYSTEM_PATH"
printf "  %-24s ${GREEN}%s${NC}\n" "虚拟机的备份:" "$BACKUP_PATH"
printf "  %-24s ${YELLOW}%s${NC}\n" "虚拟机的路径:" "<需复制 $LAUNCH_PATH 到管理端>"
print_line "═"
echo

# 网络配置
print_line "═"
echo -e "${WHITE}【网络接口配置】${NC}"
print_line "─"
printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "内网IP设备名:" "$NETWORK_NAT" "(NAT网络接口)"
printf "  %-24s ${GREEN}%-20s${NC} ${BLUE}%s${NC}\n" "公网IP设备名:" "$NETWORK_PUB" "(公网网络接口)"
print_line "═"
echo
print_line "═"
echo -e "${WHITE}【重要操作步骤】${NC}"
print_line "─"
echo
echo -e "${YELLOW}步骤 1:${NC} 复制客户端证书到管理端服务器"
echo -e "  ${BLUE}scp -r $LAUNCH_PATH user@管理端IP:/path/to/destination${NC}"
echo
echo -e "${YELLOW}步骤 2:${NC} 在 Web 管理端添加服务器"
echo -e "  - 打开 OpenIDCS Web 管理界面"
echo -e "  - 进入【服务器管理】→【添加服务器】"
echo -e "  - 填写上述配置信息"
echo -e "  - ${YELLOW}虚拟机的路径${NC} 填写管理端的证书路径（步骤1中的目标路径）"
echo
echo -e "${YELLOW}步骤 3:${NC} 验证防火墙配置"
echo -e "  ${BLUE}# 测试端口连通性${NC}"
echo -e "  ${CYAN}telnet $SERVER_ADDR $SERVER_PORT${NC}"
echo -e "  ${BLUE}# 或使用 nc 命令${NC}"
echo -e "  ${CYAN}nc -zv $SERVER_ADDR $SERVER_PORT${NC}"
echo
echo -e "${YELLOW}步骤 4:${NC} 测试 LXD 连接（可选）"
echo -e "  ${CYAN}$LXD_BIN_DIR/lxc remote add myserver https://$SERVER_ADDR:$SERVER_PORT --accept-certificate --password=<您的密码>${NC}"
echo -e "  ${CYAN}$LXD_BIN_DIR/lxc remote list${NC}"
print_line "═"
echo

print_line "═"
echo -e "${WHITE}【常见问题处理】${NC}"
print_line "─"
echo
echo -e "${YELLOW}问题 1:${NC} 终端中 lxc/lxd 命令不可用"
echo -e "  ${GREEN}解决方案:${NC}"
echo -e "    ${CYAN}1.${NC} 重新登录系统"
echo -e "    ${CYAN}2.${NC} 执行: ${BLUE}source /etc/profile.d/snap.sh${NC}"
echo -e "    ${CYAN}3.${NC} 执行: ${BLUE}export PATH=\"/snap/bin:/var/lib/snapd/snap/bin:\$PATH\"${NC}"
echo
echo -e "${YELLOW}问题 2:${NC} 需要配置外网网桥"
echo -e "  ${GREEN}解决方案:${NC}"
echo -e "    ${BLUE}$LXD_BIN_DIR/lxc network create $NETWORK_PUB${NC}"
echo
echo -e "${YELLOW}问题 3:${NC} 无法连接到 LXD API"
echo -e "  ${GREEN}检查清单:${NC}"
echo -e "    ${CYAN}1.${NC} 确认防火墙已开放端口 $SERVER_PORT"
echo -e "    ${CYAN}2.${NC} 确认 LXD 服务正常运行: ${BLUE}systemctl status snap.lxd.daemon${NC}"
echo -e "    ${CYAN}3.${NC} 确认网络地址正确: ${BLUE}$SERVER_ADDR${NC}"
print_line "═"
echo

ok "安装完成！详细教程: ${CYAN}https://github.com/xkatld/zjmf-lxd-server/wiki${NC}"
echo
info "如有问题，请查看日志: ${BLUE}journalctl -u snap.lxd.daemon -f${NC}"
echo