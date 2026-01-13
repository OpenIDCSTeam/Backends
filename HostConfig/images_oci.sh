#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CONTAINER_CMD=""

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

reading() {
    read -rp "$(echo -e "${GREEN}[INPUT]${NC} $1")" "$2"
}

detect_container_runtime() {
    info "检测容器运行时..."
    
    if command -v docker &> /dev/null; then
        info "检测到 Docker"
        DOCKER_AVAILABLE=true
    else
        DOCKER_AVAILABLE=false
    fi
    
    if command -v podman &> /dev/null; then
        info "检测到 Podman"
        PODMAN_AVAILABLE=true
    else
        PODMAN_AVAILABLE=false
    fi
    
    if [[ "$DOCKER_AVAILABLE" == false && "$PODMAN_AVAILABLE" == false ]]; then
        err "未检测到 Docker 或 Podman，请先安装"
        exit 1
    fi
}

select_container_runtime() {
    echo
    info "=== 选择容器运行时 ==="
    
    if [[ "$DOCKER_AVAILABLE" == true && "$PODMAN_AVAILABLE" == true ]]; then
        echo "1. Docker"
        echo "2. Podman"
        reading "请选择 [1-2]: " runtime_choice
        
        case "$runtime_choice" in
            1) CONTAINER_CMD="docker" ;;
            2) CONTAINER_CMD="podman" ;;
            *) 
                warn "无效选择，默认使用 Docker"
                CONTAINER_CMD="docker"
                ;;
        esac
    elif [[ "$DOCKER_AVAILABLE" == true ]]; then
        CONTAINER_CMD="docker"
        ok "使用 Docker"
    else
        CONTAINER_CMD="podman"
        ok "使用 Podman"
    fi
    
    ok "已选择: $CONTAINER_CMD"
}

declare -A IMAGE_REPOS=(
    ["debian"]="pikachuim/debian"
    ["ubuntu"]="pikachuim/ubuntu"
    ["alpine"]="pikachuim/alpine"
    ["fedora"]="pikachuim/fedora"
)

fetch_image_tags() {
    local repo="$1"
    local namespace=$(echo "$repo" | cut -d'/' -f1)
    local repository=$(echo "$repo" | cut -d'/' -f2)
    local url="https://hub.docker.com/v2/repositories/${namespace}/${repository}/tags?page_size=100"
    
    info "获取 $repo 的镜像标签..." >&2
    
    local tags=()
    while [ -n "$url" ]; do
        local response=$(curl -s "$url" 2>/dev/null)
        if [ $? -ne 0 ] || [ -z "$response" ]; then
            warn "无法获取 $repo 的标签" >&2
            return 1
        fi
        
        local page_tags=$(echo "$response" | grep -o '"name":"[^"]*-server"' | sed 's/"name":"//g' | sed 's/"//g')
        if [ -n "$page_tags" ]; then
            tags+=($page_tags)
        fi
        
        url=$(echo "$response" | grep -o '"next":"[^"]*"' | sed 's/"next":"//g' | sed 's/"//g' | sed 's/\\//g')
    done
    
    if [ ${#tags[@]} -eq 0 ]; then
        warn "$repo 没有找到 *-server 标签" >&2
        return 1
    fi
    
    echo "${tags[@]}"
    return 0
}

pull_image() {
    local image_full="$1"
    
    info "拉取镜像: $image_full"
    
    if $CONTAINER_CMD pull "$image_full"; then
        ok "成功拉取: $image_full"
        return 0
    else
        err "拉取失败: $image_full"
        return 1
    fi
}

menu_import() {
    echo
    info "=== 导入镜像 ==="
    info "正在获取所有镜像仓库的标签信息..."
    echo
    
    # 收集所有镜像
    declare -a all_images=()
    declare -A image_map=()
    
    for key in "${!IMAGE_REPOS[@]}"; do
        local repo="${IMAGE_REPOS[$key]}"
        local tags=$(fetch_image_tags "$repo")
        
        if [ $? -eq 0 ] && [ -n "$tags" ]; then
            local tags_array=($tags)
            for tag in "${tags_array[@]}"; do
                all_images+=("${repo}:${tag}")
            done
        fi
    done
    
    if [[ ${#all_images[@]} -eq 0 ]]; then
        err "未找到任何可用镜像"
        return
    fi
    
    # 显示所有镜像
    echo "============================================================================================================"
    echo " 可用的 OCI 镜像 (共 ${#all_images[@]} 个):"
    echo "============================================================================================================"
    
    local idx=1
    for img in "${all_images[@]}"; do
        printf "%3d) %-50s" "$idx" "$img"
        if (( idx % 2 == 0 )); then
            echo
        fi
        ((idx++))
    done
    if (( (${#all_images[@]}) % 2 != 0 )); then
        echo
    fi
    
    echo "============================================================================================================"
    echo
    
    reading "输入编号，多个用逗号分隔，或 all 全部导入 [1]: " image_choices
    image_choices=${image_choices:-"1"}
    
    local selected_images=()
    
    if [[ "$image_choices" == "all" ]]; then
        selected_images=("${all_images[@]}")
    else
        IFS=',' read -ra choices <<< "$image_choices"
        for choice in "${choices[@]}"; do
            choice=$(echo "$choice" | xargs)
            idx=$((choice - 1))
            if [[ $idx -ge 0 && $idx -lt ${#all_images[@]} ]]; then
                selected_images+=("${all_images[$idx]}")
            else
                warn "无效编号: $choice"
            fi
        done
    fi
    
    if [[ ${#selected_images[@]} -eq 0 ]]; then
        warn "未选择任何镜像"
        return
    fi
    
    ok "已选择 ${#selected_images[@]} 个镜像"
    echo
    
    local current=0
    for img in "${selected_images[@]}"; do
        ((current++))
        echo "[$current/${#selected_images[@]}]"
        pull_image "$img"
        echo
    done
    
    ok "镜像导入完成"
}

menu_list() {
    echo
    info "=== 已有镜像 ==="
    $CONTAINER_CMD images
}

menu_delete() {
    echo
    info "=== 删除镜像 ==="
    $CONTAINER_CMD images
    echo
    reading "输入要删除的镜像名称或ID: " image_id
    if [ -z "$image_id" ]; then
        return
    fi
    
    warn "确认删除镜像 $image_id？"
    reading "确认？(y/n) [n]: " confirm
    if [[ "$confirm" =~ ^[yY]$ ]]; then
        if $CONTAINER_CMD rmi "$image_id"; then
            ok "镜像已删除"
        else
            err "删除失败"
        fi
    else
        info "已取消"
    fi
}

main_menu() {
    while true; do
        echo
        echo "================================"
        echo "    OCI 镜像管理脚本"
        echo "   OpenIDCS by OpenIDCSTeam"
        echo "================================"
        echo "容器运行时: $CONTAINER_CMD"
        echo "================================"
        echo "1. 下载新的镜像"
        echo "2. 查看已有镜像"
        echo "3. 删除已有镜像"
        echo "4. 切换VM运行时"
        echo "0. 退出"
        echo "================================"
        reading "请选择 [0-4]: " choice
        
        case "$choice" in
            1) menu_import ;;
            2) menu_list ;;
            3) menu_delete ;;
            4) select_container_runtime ;;
            0) ok "退出"; exit 0 ;;
            *) warn "无效选择" ;;
        esac
    done
}

detect_container_runtime
select_container_runtime
main_menu
