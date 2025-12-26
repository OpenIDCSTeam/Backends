#!/bin/bash

# LXD 服务端初始化脚本
# 用于在 Linux 服务器上配置 LXD 环境
# 支持远程管理（从 Windows 客户端）
# 支持多个 Linux 发行版：Ubuntu/Debian、CentOS/RHEL/Rocky、Fedora、Arch Linux

set -e

# 颜色定义
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

NAME="LXD"
FORCE=false
DELETE=false

# 日志函数
log() { echo -e "$1"; }
ok() { log "${GREEN}[OK]${NC} $1"; }
info() { log "${BLUE}[INFO]${NC} $1"; }
warn() { log "${YELLOW}[WARN]${NC} $1"; }
err() { log "${RED}[ERR]${NC} $1"; exit 1; }

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    err "请使用 root 运行"
fi

# 处理命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    -f|--force) FORCE=true; shift;;
    -d|--delete) DELETE=true; shift;;
    -h|--help)
      echo "========================================"
      echo "        LXD 服务端配置脚本"
      echo "========================================"
      echo
      echo "用法: $0 [选项]"
      echo
      echo "选项:"
      echo "  -f, --force    强制重新安装（即使已安装 LXD）"
      echo "  -d, --delete   卸载 LXD 及所有数据"
      echo "  -h, --help     显示此帮助信息"
      echo
      echo "示例:"
      echo "  $0              # 安装并配置 LXD"
      echo "  $0 -f           # 强制重新安装"
      echo "  $0 -d           # 卸载 LXD"
      echo
      exit 0;;
    *) err "未知参数: $1 (使用 -h 查看帮助)";;
  esac
done

# 卸载 LXD 功能
if [[ $DELETE == true ]]; then
  echo
  echo "========================================"
  echo "          卸载 LXD"
  echo "========================================"
  echo
  
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
  
  info "清理网桥配置..."
  ip link show br-pub 2>/dev/null && ip link delete br-pub 2>/dev/null || true
  ip link show br-nat 2>/dev/null && ip link delete br-nat 2>/dev/null || true
  
  echo
  ok "LXD 卸载完成！"
  echo
  warn "环境变量已清理，建议重新登录系统或重启终端"
  exit 0
fi

echo
echo "========================================"
echo "LXD 服务端初始化脚本"
echo "========================================"
echo

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
    
    err "无法启用 squashfs 支持"
    warn "snap 将无法正常工作，将尝试使用原生包管理器"
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
    
    info "系统: $DISTRO $VERSION"
    
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
}

# 安装 LXD 的函数
install_lxd() {
    # 检查 squashfs 支持（snap 需要）
    check_squashfs_support
    SQUASHFS_SUPPORTED=$?
    
    case $DISTRO in
        ubuntu|debian)
            echo "使用 APT 包管理器安装..."
            apt-get update
            
            # 严格检查 LXD 是否真的可以安装（Ubuntu 24.04+ 没有 LXD 包）
            if apt-cache policy lxd 2>/dev/null | grep -q "Candidate:" && \
               apt-cache policy lxd 2>/dev/null | grep "Candidate:" | grep -vq "(none)"; then
                # APT 仓库中有 LXD，使用 APT 安装（Ubuntu 20.04 及之前版本）
                apt-get install -y lxd lxd-client bridge-utils
                echo "✓ 通过 APT 安装 LXD 成功"
            else
                # APT 仓库中没有 LXD（Ubuntu 24.04+），使用 snap 安装
                echo "APT 仓库中没有 LXD，通过 snap 安装..."
                
                # 检查是否支持 squashfs
                if [ $SQUASHFS_SUPPORTED -eq 0 ]; then
                    echo "安装 snapd..."
                    apt-get install -y snapd bridge-utils
                    
                    # 启用并启动 snapd
                    systemctl enable --now snapd.socket
                    
                    # 确保 /snap 符号链接存在（某些系统需要）
                    ln -sf /var/lib/snapd/snap /snap 2>/dev/null || true
                    
                    # 等待 snapd 完全启动
                    echo "等待 snapd 服务启动..."
                    sleep 5
                    
                    # 安装 LXD
                    echo "通过 snap 安装 LXD（这可能需要几分钟）..."
                    snap install lxd --classic 2>/dev/null || snap install lxd
                    
                    echo "✓ 通过 snap 安装 LXD 成功"
                else
                    echo "⚠ 警告: 系统不支持 squashfs"
                    echo "  在不支持的 squashfs 的环境中，可以尝试以下方案："
                    echo "  1. 安装 linux-modules-extra 包："
                    echo "     apt-get install -y linux-modules-extra-$(uname -r)"
                    echo "     modprobe squashfs"
                    echo ""
                    echo "  2. 或者添加 LXD 官方 PPA（适用于 Ubuntu 20.04 及之前版本）："
                    echo "     add-apt-repository ppa:ubuntu-lxc/lxd-daily"
                    echo "     apt-get update"
                    echo "     apt-get install -y lxd lxd-client"
                    echo ""
                    echo "  3. 对于 Ubuntu 24.04+，snap 是推荐的安装方式"
                    echo ""
                    echo "尝试继续安装 snapd（snap 可能在您的环境中能工作）..."
                    apt-get install -y snapd bridge-utils
                    systemctl enable --now snapd.socket
                    ln -sf /var/lib/snapd/snap /snap 2>/dev/null || true
                    sleep 5
                    echo "尝试通过 snap 安装 LXD..."
                    snap install lxd --classic 2>/dev/null || snap install lxd || {
                        echo ""
                        echo "✗ 错误: 无法安装 LXD"
                        echo "  请检查："
                        echo "  1. 系统是否支持 snap（某些云环境或容器可能不支持）"
                        echo "  2. 网络连接是否正常"
                        echo "  3. 是否在 LXC 容器中运行（需要在宿主机配置 apparmor 和权限）"
                        exit 1
                    }
                    echo "✓ 通过 snap 安装 LXD 成功"
                fi
            fi
            ;;
        centos|rhel|rocky|almalinux)
            echo "使用 YUM/DNF 包管理器安装..."
            
            # CentOS/RHEL 通常需要通过 snap 安装 LXD
            if [ $SQUASHFS_SUPPORTED -ne 0 ]; then
                echo "✗ 错误: 系统不支持 squashfs，无法使用 snap 安装 LXD"
                echo ""
                echo "解决方案："
                echo "  1. 如果在 LXC 容器中运行，请在宿主机上配置容器："
                echo "     - 添加 lxc.mount.auto = proc:rw sys:rw cgroup:rw"
                echo "     - 添加 lxc.apparmor.profile = unconfined"
                echo "     - 添加 lxc.cap.drop ="
                echo ""
                echo "  2. 或者使用支持 LXD 原生包的发行版（如 Ubuntu）"
                echo ""
                echo "  3. 或者在物理机/虚拟机上运行而非容器"
                exit 1
            fi
            
            # 安装 EPEL 仓库
            if command -v dnf &> /dev/null; then
                dnf install -y epel-release
                dnf install -y snapd bridge-utils
            else
                yum install -y epel-release
                yum install -y snapd bridge-utils
            fi
            
            # 启动 snapd
            systemctl enable --now snapd.socket
            ln -sf /var/lib/snapd/snap /snap || true
            
            # 等待 snapd 完全启动
            echo "等待 snapd 服务启动..."
            sleep 5
            
            # 通过 snap 安装 LXD
            snap install lxd
            echo "✓ 通过 snap 安装 LXD 成功"
            ;;
        fedora)
            echo "使用 DNF 包管理器安装..."
            
            if [ $SQUASHFS_SUPPORTED -ne 0 ]; then
                echo "✗ 错误: 系统不支持 squashfs，无法使用 snap 安装 LXD"
                echo "  请参考上述 CentOS/RHEL 的解决方案"
                exit 1
            fi
            
            dnf install -y snapd bridge-utils
            systemctl enable --now snapd.socket
            ln -sf /var/lib/snapd/snap /snap || true
            
            echo "等待 snapd 服务启动..."
            sleep 5
            
            snap install lxd
            echo "✓ 通过 snap 安装 LXD 成功"
            ;;
        arch|manjaro)
            echo "使用 Pacman 包管理器安装..."
            pacman -Sy --noconfirm lxd bridge-utils
            systemctl enable --now lxd.socket
            echo "✓ 通过 Pacman 安装 LXD 成功"
            ;;
        opensuse*|sles)
            echo "使用 Zypper 包管理器安装..."
            zypper install -y lxd lxd-client bridge-utils
            echo "✓ 通过 Zypper 安装 LXD 成功"
            ;;
        *)
            echo "错误: 不支持的发行版 $DISTRO"
            
            if [ $SQUASHFS_SUPPORTED -eq 0 ]; then
                echo "尝试通过 snap 安装..."
                if ! command -v snap &> /dev/null; then
                    echo "✗ 错误: snap 未安装，无法继续"
                    exit 1
                fi
                snap install lxd
                echo "✓ 通过 snap 安装 LXD 成功"
            else
                echo "✗ 错误: 系统不支持 squashfs，且没有原生 LXD 包"
                exit 1
            fi
            ;;
    esac
}

# 检测发行版
detect_distro

# 1. 安装 LXD 和依赖
echo ""
echo "[1/6] 安装 LXD 和依赖..."
install_lxd

# 2. 初始化 LXD
echo ""
echo "[2/6] 初始化 LXD..."

# 检查并清理可能存在的冲突
echo "检查现有 LXD 配置..."
if lxc network list 2>/dev/null | grep -q lxdbr0; then
    echo "⚠ 发现已存在的 lxdbr0 网络，正在清理..."
    lxc network delete lxdbr0 2>/dev/null || true
fi

# 检查 dnsmasq 进程
if pgrep -f "dnsmasq.*lxdbr0" > /dev/null; then
    echo "⚠ 发现运行中的 dnsmasq 进程，正在停止..."
    pkill -f "dnsmasq.*lxdbr0" 2>/dev/null || true
    sleep 2
fi

# 检查端口占用
if netstat -tuln 2>/dev/null | grep -q ":53 " || ss -tuln 2>/dev/null | grep -q ":53 "; then
    echo "⚠ 警告: 端口 53 (DNS) 已被占用"
    echo "  正在检查占用进程..."
    netstat -tulnp 2>/dev/null | grep ":53 " || ss -tulnp 2>/dev/null | grep ":53 " || true
fi

echo "使用 preseed 配置自动初始化 LXD..."

# 使用 preseed 配置自动初始化

# lxd init
cat <<EOF | lxd init --preseed
config:
  core.https_address: '[::]:8443'
networks:
- config:
    ipv4.address: 10.10.10.1/24
    ipv4.nat: "true"
    ipv6.address: none
  description: "LXD bridge network"
  name: lxdbr0
  type: bridge
  project: default
storage_pools:
- config: {}
  name: default
  driver: dir
profiles:
- config: {}
  description: "Default LXD profile"
  devices:
    eth0:
      name: eth0
      nictype: bridged
      parent: lxdbr0
      type: nic
    root:
      path: /
      pool: default
      type: disk
  name: default
projects: []
EOF

if [ $? -eq 0 ]; then
    echo "✓ LXD 初始化完成！"
else
    echo "✗ LXD 初始化失败，尝试手动初始化..."
    echo "  如果遇到网络冲突，请检查："
    echo "  1. 是否有其他服务占用端口 53 (DNS)"
    echo "  2. 是否有其他网桥使用 10.10.10.0/24 网段"
    echo "  3. 运行 'systemctl status dnsmasq' 检查 dnsmasq 状态"
    exit 1
fi

# 设置信任密码（新版本 LXD 的方式）
echo "设置 LXD 信任密码..."
if lxc config set core.trust_password changeme 2>/dev/null; then
    echo "✓ 使用旧版方式设置信任密码成功"
else
    # 新版本 LXD 使用不同的方式
    echo "旧版信任密码方式不支持，使用新版本方式..."
    # 对于新版本，可以通过环境变量或配置文件设置
    # 或者提示用户手动添加信任的客户端
    echo "⚠ 注意: 新版本 LXD 已弃用 trust_password"
    echo "  如需远程访问，请使用以下命令添加信任的客户端："
    echo "  lxc config trust add <client-name>"
    echo "  或者使用客户端证书进行认证"
fi

# 3. 配置网桥
echo ""
echo "[3/6] 配置网桥..."

# 读取用户输入的网桥名称
read -p "请输入公网网桥名称 (默认: br-pub): " BRIDGE_PUB
BRIDGE_PUB=${BRIDGE_PUB:-br-pub}

read -p "请输入内网网桥名称 (默认: br-nat): " BRIDGE_NAT
BRIDGE_NAT=${BRIDGE_NAT:-br-nat}

# 创建公网网桥
if ! ip link show $BRIDGE_PUB &> /dev/null; then
    echo "创建公网网桥: $BRIDGE_PUB"
    ip link add name $BRIDGE_PUB type bridge
    ip link set $BRIDGE_PUB up

    # 持久化配置（根据发行版选择配置方式）
    case $DISTRO in
        ubuntu|debian)
            # 使用 Netplan（Ubuntu 18.04+）
            if [ -d /etc/netplan ]; then
                cat > /etc/netplan/99-lxd-bridges.yaml <<EOF
network:
  version: 2
  bridges:
    $BRIDGE_PUB:
      dhcp4: no
      dhcp6: no
    $BRIDGE_NAT:
      dhcp4: no
      dhcp6: no
      addresses:
        - 10.0.0.1/24
EOF
                netplan apply
            # 使用传统的 /etc/network/interfaces（Debian/旧版 Ubuntu）
            elif [ -f /etc/network/interfaces ]; then
                cat >> /etc/network/interfaces <<EOF

auto $BRIDGE_PUB
iface $BRIDGE_PUB inet manual
    bridge_ports none
    bridge_stp off
    bridge_fd 0

auto $BRIDGE_NAT
iface $BRIDGE_NAT inet static
    address 10.0.0.1
    netmask 255.255.255.0
    bridge_ports none
    bridge_stp off
    bridge_fd 0
EOF
            fi
            ;;
        centos|rhel|rocky|almalinux|fedora)
            # 使用 NetworkManager 或传统的网络脚本
            if command -v nmcli &> /dev/null; then
                echo "使用 NetworkManager 配置网桥..."
                nmcli connection add type bridge ifname $BRIDGE_PUB con-name $BRIDGE_PUB
                nmcli connection add type bridge ifname $BRIDGE_NAT con-name $BRIDGE_NAT
                nmcli connection modify $BRIDGE_NAT ipv4.addresses 10.0.0.1/24
                nmcli connection modify $BRIDGE_NAT ipv4.method manual
                nmcli connection up $BRIDGE_PUB
                nmcli connection up $BRIDGE_NAT
            else
                # 使用传统的网络脚本
                cat > /etc/sysconfig/network-scripts/ifcfg-$BRIDGE_PUB <<EOF
DEVICE=$BRIDGE_PUB
TYPE=Bridge
BOOTPROTO=none
ONBOOT=yes
STP=off
EOF
                cat > /etc/sysconfig/network-scripts/ifcfg-$BRIDGE_NAT <<EOF
DEVICE=$BRIDGE_NAT
TYPE=Bridge
BOOTPROTO=static
IPADDR=10.0.0.1
NETMASK=255.255.255.0
ONBOOT=yes
STP=off
EOF
                systemctl restart network || service network restart
            fi
            ;;
        arch|manjaro)
            # 使用 systemd-networkd
            cat > /etc/systemd/network/99-$BRIDGE_PUB.netdev <<EOF
[NetDev]
Name=$BRIDGE_PUB
Kind=bridge
EOF
            cat > /etc/systemd/network/99-$BRIDGE_NAT.netdev <<EOF
[NetDev]
Name=$BRIDGE_NAT
Kind=bridge
EOF
            cat > /etc/systemd/network/99-$BRIDGE_NAT.network <<EOF
[Match]
Name=$BRIDGE_NAT

[Network]
Address=10.0.0.1/24
EOF
            systemctl restart systemd-networkd
            ;;
        *)
            echo "警告: 未知发行版，网桥配置可能不会持久化"
            echo "请手动配置网桥以确保重启后生效"
            ;;
    esac
else
    echo "公网网桥 $BRIDGE_PUB 已存在"
fi

# 创建内网网桥
if ! ip link show $BRIDGE_NAT &> /dev/null; then
    echo "创建内网网桥: $BRIDGE_NAT"
    ip link add name $BRIDGE_NAT type bridge
    ip link set $BRIDGE_NAT up
    ip addr add 10.0.0.1/24 dev $BRIDGE_NAT
else
    echo "内网网桥 $BRIDGE_NAT 已存在"
fi

echo "网桥配置完成！"

# 4. 配置存储池
echo ""
echo "[4/6] 配置存储池..."

# 检查默认存储池
if ! lxc storage list | grep -q "default"; then
    echo "创建默认存储池..."
    lxc storage create default dir
else
    echo "默认存储池已存在"
fi

echo "存储池配置完成！"

# 5. 生成客户端证书
echo ""
echo "[5/6] 生成客户端证书..."

CERT_DIR="./lxd_certs"
mkdir -p $CERT_DIR

# 生成客户端证书
if [ ! -f "$CERT_DIR/client.crt" ]; then
    echo "生成客户端证书..."
    openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/client.key" \
        -out "$CERT_DIR/client.crt" -days 3650 -nodes \
        -subj "/CN=lxd-client"

    echo "客户端证书已生成: $CERT_DIR/client.crt"
    echo "客户端密钥已生成: $CERT_DIR/client.key"
else
    echo "客户端证书已存在"
fi

# 添加客户端证书到 LXD 信任列表
echo "添加客户端证书到 LXD 信任列表..."
lxc config trust add "$CERT_DIR/client.crt" || echo "证书可能已添加"

echo "证书配置完成！"

# 6. 配置防火墙
echo ""
echo "[6/6] 配置防火墙..."

# 允许 LXD API 端口
case $DISTRO in
    ubuntu|debian)
        if command -v ufw &> /dev/null; then
            echo "配置 UFW 防火墙..."
            ufw allow 8443/tcp comment "LXD HTTPS API"
            ufw reload || true
        else
            echo "UFW 未安装，跳过防火墙配置"
        fi
        ;;
    centos|rhel|rocky|almalinux|fedora)
        if command -v firewall-cmd &> /dev/null; then
            echo "配置 firewalld 防火墙..."
            firewall-cmd --permanent --add-port=8443/tcp
            firewall-cmd --reload
        else
            echo "firewalld 未安装，跳过防火墙配置"
        fi
        ;;
    arch|manjaro)
        if command -v ufw &> /dev/null; then
            echo "配置 UFW 防火墙..."
            ufw allow 8443/tcp comment "LXD HTTPS API"
            ufw reload || true
        elif command -v firewall-cmd &> /dev/null; then
            echo "配置 firewalld 防火墙..."
            firewall-cmd --permanent --add-port=8443/tcp
            firewall-cmd --reload
        else
            echo "未检测到防火墙，跳过配置"
            echo "如果使用 iptables，请手动添加规则："
            echo "  iptables -A INPUT -p tcp --dport 8443 -j ACCEPT"
        fi
        ;;
    *)
        echo "未检测到防火墙或不支持的发行版，跳过配置"
        echo "请手动配置防火墙以允许 8443/tcp 端口"
        ;;
esac

echo "防火墙配置完成！"

# 7. 显示配置信息
echo ""
echo "========================================="
echo "LXD 服务端配置完成！"
echo "========================================="
echo ""
echo "系统信息："
echo "  - 发行版: $DISTRO $VERSION"
echo "  - LXD 版本: $(lxd --version 2>/dev/null || echo '未知')"
echo ""
echo "配置信息："
echo "  - LXD API 地址: https://$(hostname -I | awk '{print $1}'):8443"
echo "  - 公网网桥: $BRIDGE_PUB"
echo "  - 内网网桥: $BRIDGE_NAT"
echo "  - 存储池: default"
echo "  - 客户端证书: $CERT_DIR/client.crt"
echo "  - 客户端密钥: $CERT_DIR/client.key"
echo ""
echo "下一步操作："
echo "  1. 将客户端证书和密钥复制到 Windows 客户端"
echo "  2. 在 HSConfig 中配置："
echo "     - server_addr: $(hostname -I | awk '{print $1}')"
echo "     - network_pub: $BRIDGE_PUB"
echo "     - network_nat: $BRIDGE_NAT"
echo "     - launch_path: <证书存放目录>"
echo "  3. 运行 Python 客户端连接到此服务器"
echo ""
echo "测试连接："
echo "  lxc remote add myserver https://$(hostname -I | awk '{print $1}'):8443 --accept-certificate --password=changeme"
echo "  lxc remote list"
echo ""
echo "注意事项："
echo "  - 请修改默认密码 'changeme' 以提高安全性"
echo "  - 确保防火墙允许 8443 端口访问"
echo "  - 如果网桥配置未持久化，请根据您的发行版手动配置"
echo ""
echo "========================================="