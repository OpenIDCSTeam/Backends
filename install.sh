#!/bin/bash
# ============================================================================
# OpenIDCS-Client 一键安装脚本
# 支持: curl -fsSL https://raw.githubusercontent.com/OpenIDCSTeam/HostAgent/main/install.sh | sudo bash
#
# 用法:
#   安装（二进制，默认）:  curl -fsSL <URL> | sudo bash
#   安装（源码模式）:      curl -fsSL <URL> | sudo bash -s -- --source
# ============================================================================
set -euo pipefail
umask 027

# ======================== 解析参数 ========================
INSTALL_MODE="binary"   # 默认二进制安装
for arg in "$@"; do
    case "${arg}" in
        --source)
            INSTALL_MODE="source"
            ;;
    esac
done

# ======================== 配置 ========================
REPO_OWNER="OpenIDCSTeam"
REPO_NAME="HostAgent"
DOWNLOAD_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/download/alpha/OpenIDCS-Client-cxfreeze-Linux.tar.gz"
GITHUB_RAW="https://raw.githubusercontent.com/${REPO_OWNER}/HostAgent/main"
INSTALL_DIR="/opt/openidcs"
BIN_LINK="/usr/local/bin/openidcs"
SERVICE_NAME="openidcs"
DATA_DIR="${INSTALL_DIR}/DataSaving"
CONFIG_DIR="${INSTALL_DIR}/HostConfig"
LOG_FILE="/var/log/openidcs-install.log"
REQUIRED_PYTHON_VERSION="3.8"

# ======================== 颜色 ========================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ======================== 工具函数 ========================
info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
step()    { echo -e "${CYAN}[STEP]${NC} $*"; }

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "${LOG_FILE}" 2>/dev/null || true
}

die() {
    error "$*"
    log "FATAL: $*"
    exit 1
}

# ======================== 环境检测 ========================
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        die "请使用 root 权限运行此脚本，例如: sudo bash install.sh"
    fi
}

check_os() {
    if [ ! -f /etc/os-release ]; then
        die "无法检测操作系统，仅支持 Linux 系统"
    fi
    . /etc/os-release
    OS_ID="${ID}"
    OS_VERSION="${VERSION_ID}"
    OS_NAME="${PRETTY_NAME}"
    info "检测到操作系统: ${OS_NAME}"
    log "OS: ${OS_NAME} (${OS_ID} ${OS_VERSION})"

    case "${OS_ID}" in
        ubuntu|debian|centos|rhel|rocky|alma|fedora|opensuse*|sles|arch|manjaro)
            ;;
        *)
            warn "未经测试的发行版: ${OS_ID}，将尝试继续安装"
            ;;
    esac
}

check_arch() {
    ARCH="$(uname -m)"
    case "${ARCH}" in
        x86_64|amd64)
            ARCH="x86_64"
            ;;
        aarch64|arm64)
            ARCH="aarch64"
            ;;
        *)
            die "不支持的架构: ${ARCH}，仅支持 x86_64 和 aarch64"
            ;;
    esac
    info "系统架构: ${ARCH}"
}

# ======================== 依赖安装 ========================
install_deps() {
    step "安装系统依赖..."

    # 检测包管理器
    if command -v apt-get &>/dev/null; then
        PKG_MGR="apt"
        apt-get update -qq
        apt-get install -y -qq curl wget tar gzip python3 python3-pip python3-venv >/dev/null 2>&1
    elif command -v yum &>/dev/null; then
        PKG_MGR="yum"
        yum install -y -q curl wget tar gzip python3 python3-pip >/dev/null 2>&1
    elif command -v dnf &>/dev/null; then
        PKG_MGR="dnf"
        dnf install -y -q curl wget tar gzip python3 python3-pip >/dev/null 2>&1
    elif command -v pacman &>/dev/null; then
        PKG_MGR="pacman"
        pacman -Sy --noconfirm --quiet curl wget tar gzip python python-pip >/dev/null 2>&1
    elif command -v zypper &>/dev/null; then
        PKG_MGR="zypper"
        zypper -q install -y curl wget tar gzip python3 python3-pip >/dev/null 2>&1
    else
        warn "无法识别包管理器，请手动确保已安装: curl wget tar python3 python3-pip"
    fi

    info "系统依赖安装完成"
}

check_python() {
    step "检查 Python 环境..."

    PYTHON_BIN=""
    for cmd in python3 python; do
        if command -v "${cmd}" &>/dev/null; then
            PY_VER=$("${cmd}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
            if [ -n "${PY_VER}" ]; then
                PY_MAJOR=$(echo "${PY_VER}" | cut -d. -f1)
                PY_MINOR=$(echo "${PY_VER}" | cut -d. -f2)
                REQ_MAJOR=$(echo "${REQUIRED_PYTHON_VERSION}" | cut -d. -f1)
                REQ_MINOR=$(echo "${REQUIRED_PYTHON_VERSION}" | cut -d. -f2)
                if [ "${PY_MAJOR}" -ge "${REQ_MAJOR}" ] && [ "${PY_MINOR}" -ge "${REQ_MINOR}" ]; then
                    PYTHON_BIN="${cmd}"
                    break
                fi
            fi
        fi
    done

    if [ -z "${PYTHON_BIN}" ]; then
        die "未找到 Python >=${REQUIRED_PYTHON_VERSION}，请先安装 Python"
    fi

    info "Python: $(${PYTHON_BIN} --version 2>&1) (${PYTHON_BIN})"
}

# ======================== 下载安装 ========================
install_binary() {
    step "下载预编译二进制包..."

    TMP_DIR=$(mktemp -d)
    trap "rm -rf ${TMP_DIR}" EXIT

    FILENAME=$(basename "${DOWNLOAD_URL}")
    info "下载地址: ${DOWNLOAD_URL}"
    info "正在下载: ${FILENAME}"
    curl -fSL --progress-bar -o "${TMP_DIR}/${FILENAME}" "${DOWNLOAD_URL}" \
        || die "二进制包下载失败，请检查网络连接。如需源码安装请使用 --source 参数"

    step "解压并安装到 ${INSTALL_DIR}..."
    mkdir -p "${INSTALL_DIR}"

    # 解压 tar.gz
    tar -xzf "${TMP_DIR}/${FILENAME}" -C "${INSTALL_DIR}" --strip-components=1 2>/dev/null \
        || tar -xzf "${TMP_DIR}/${FILENAME}" -C "${INSTALL_DIR}" 2>/dev/null \
        || die "解压失败，文件可能已损坏。请重新下载或使用 --source 参数进行源码安装"

    # 确保可执行文件有执行权限
    find "${INSTALL_DIR}" -name "OpenIDCS-Client" -type f -exec chmod +x {} \;
    find "${INSTALL_DIR}" -name "*.so" -type f -exec chmod +x {} \; 2>/dev/null || true

    info "二进制安装完成"
    INSTALL_TYPE="binary"
}

install_source() {
    step "使用源码方式安装..."

    TMP_DIR=$(mktemp -d)
    trap "rm -rf ${TMP_DIR}" EXIT

    # 克隆仓库或下载源码
    if command -v git &>/dev/null; then
        info "通过 Git 克隆源码..."
        git clone --depth 1 "https://github.com/${REPO_OWNER}/${REPO_NAME}.git" "${TMP_DIR}/source" 2>/dev/null \
            || die "Git 克隆失败"
    else
        info "通过下载压缩包获取源码..."
        BRANCH="main"
        curl -fsSL "https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/heads/${BRANCH}.tar.gz" \
            -o "${TMP_DIR}/source.tar.gz" || die "源码下载失败"
        mkdir -p "${TMP_DIR}/source"
        tar -xzf "${TMP_DIR}/source.tar.gz" -C "${TMP_DIR}/source" --strip-components=1
    fi

    step "部署源码到 ${INSTALL_DIR}..."
    mkdir -p "${INSTALL_DIR}"

    # 复制核心文件
    cp -r "${TMP_DIR}/source/"* "${INSTALL_DIR}/" 2>/dev/null || true

    step "创建 Python 虚拟环境..."
    "${PYTHON_BIN}" -m venv "${INSTALL_DIR}/venv" 2>/dev/null \
        || "${PYTHON_BIN}" -m virtualenv "${INSTALL_DIR}/venv" 2>/dev/null \
        || die "创建虚拟环境失败，请确保安装了 python3-venv 包"

    step "安装 Python 依赖..."
    VENV_PIP="${INSTALL_DIR}/venv/bin/pip"
    VENV_PYTHON="${INSTALL_DIR}/venv/bin/python"

    "${VENV_PIP}" install --upgrade pip -q 2>/dev/null || true

    if [ -f "${INSTALL_DIR}/HostConfig/pipinstall.txt" ]; then
        # 过滤掉 Windows 专用依赖
        grep -v -E '^\s*#|^pythonnet|^pywin32|^cx-freeze|^nuitka|^hypy' \
            "${INSTALL_DIR}/HostConfig/pipinstall.txt" > "${TMP_DIR}/requirements-linux.txt"
        "${VENV_PIP}" install -r "${TMP_DIR}/requirements-linux.txt" -q || warn "部分依赖安装失败，可能影响某些功能"
    fi

    info "源码安装完成"
    INSTALL_TYPE="source"
}

# ======================== 配置 ========================
setup_dirs() {
    step "配置目录和权限..."

    mkdir -p "${DATA_DIR}"
    mkdir -p "${CONFIG_DIR}"
    mkdir -p "/var/log/openidcs"

    # 记录安装信息
    cat > "${INSTALL_DIR}/.install_info" << EOF
INSTALL_TYPE=${INSTALL_TYPE}
INSTALL_DATE=$(date '+%Y-%m-%d %H:%M:%S')
INSTALL_VERSION=alpha
INSTALL_ARCH=${ARCH}
INSTALL_OS=${OS_NAME}
INSTALL_DIR=${INSTALL_DIR}
EOF

    info "目录配置完成"
}

install_management_script() {
    step "安装管理脚本 (openidcs)..."

    mkdir -p "$(dirname "${BIN_LINK}")"

    # 优先从安装目录复制
    if [ -f "${INSTALL_DIR}/bin/openidcs" ]; then
        cp "${INSTALL_DIR}/bin/openidcs" "${BIN_LINK}"
    else
        # 从 GitHub 下载
        curl -fsSL "https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/bin/openidcs" \
            -o "${BIN_LINK}" || die "管理脚本下载失败"
    fi

    chmod +x "${BIN_LINK}"
    info "管理脚本已安装到: ${BIN_LINK}"
}

install_systemd_service() {
    step "安装 systemd 服务..."

    # 检查 systemd
    if ! command -v systemctl &>/dev/null; then
        warn "未检测到 systemd，跳过服务安装"
        return
    fi

    # 根据安装类型确定启动命令
    if [ "${INSTALL_TYPE}" = "binary" ]; then
        EXEC_START="${INSTALL_DIR}/OpenIDCS-Client"
    else
        EXEC_START="${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/MainServer.py"
    fi

    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=OpenIDCS Client - IDC Virtualization Management Platform
Documentation=https://github.com/${REPO_OWNER}/HostAgent
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${EXEC_START}
Restart=on-failure
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# 环境变量
Environment=PYTHONUNBUFFERED=1
Environment=LANG=en_US.UTF-8

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=openidcs

# 安全限制
LimitNOFILE=65536
LimitNPROC=4096
UMask=0027
NoNewPrivileges=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}.service"
    systemctl restart "${SERVICE_NAME}.service" || systemctl start "${SERVICE_NAME}.service"
    info "systemd 服务已安装并启动"
}

# ======================== 主流程 ========================
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}║     ${GREEN}OpenIDCS-Client 一键安装程序${BLUE}                        ║${NC}"
    echo -e "${BLUE}║     ${NC}开源 IDC 虚拟化统一管理平台${BLUE}                         ║${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    log "========== 安装开始 =========="

    # 1. 环境检测
    check_root
    check_os
    check_arch

    # 2. 检查是否已安装（升级提示）
    if [ -d "${INSTALL_DIR}" ] && [ -f "${INSTALL_DIR}/.install_info" ]; then
        warn "检测到已有安装，将进行升级"
        OLD_VERSION=$(grep 'INSTALL_VERSION' "${INSTALL_DIR}/.install_info" 2>/dev/null | cut -d= -f2)
        info "当前版本: ${OLD_VERSION:-unknown}"
        # 备份数据目录
        if [ -d "${DATA_DIR}" ]; then
            info "备份数据目录..."
            cp -r "${DATA_DIR}" "${DATA_DIR}.bak.$(date +%s)" 2>/dev/null || true
        fi
    fi

    # 3. 安装系统依赖
    install_deps

    # 4. 检查 Python 环境
    check_python

    # 5. 下载并安装
    info "安装模式: ${INSTALL_MODE}"
    if [ "${INSTALL_MODE}" = "source" ]; then
        install_source
    else
        install_binary
    fi

    # 6. 配置目录
    setup_dirs

    # 7. 安装管理脚本
    install_management_script

    # 8. 安装 systemd 服务
    install_systemd_service

    # 9. 完成
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     ✅ OpenIDCS-Client 安装完成！                         ║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  安装模式:  ${CYAN}${INSTALL_TYPE}${NC}"
    echo -e "${GREEN}║${NC}  安装目录:  ${CYAN}${INSTALL_DIR}${NC}"
    echo -e "${GREEN}║${NC}  管理命令:  ${CYAN}openidcs${NC}"
    echo -e "${GREEN}║${NC}  访问地址:  ${CYAN}http://<服务器IP>:1880${NC}"
    echo -e "${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${YELLOW}常用命令:${NC}"
    echo -e "${GREEN}║${NC}    openidcs start            启动服务"
    echo -e "${GREEN}║${NC}    openidcs stop             停止服务"
    echo -e "${GREEN}║${NC}    openidcs status           查看状态"
    echo -e "${GREEN}║${NC}    openidcs restart          重启服务"
    echo -e "${GREEN}║${NC}    openidcs update           更新版本"
    echo -e "${GREEN}║${NC}    openidcs uninstall        卸载程序"
    echo -e "${GREEN}║${NC}    openidcs log              查看日志"
    echo -e "${GREEN}║${NC}    openidcs service enable   开机自启"
    echo -e "${GREEN}║${NC}    openidcs help             查看帮助"
    echo -e "${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${YELLOW}快速开始:${NC}"
    echo -e "${GREEN}║${NC}    sudo openidcs start   启动后访问 http://IP:1880"
    echo -e "${GREEN}║${NC}    首次启动查看控制台输出获取访问 Token"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    log "========== 安装完成 =========="
}

main "$@"
