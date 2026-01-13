#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

reading() {
    read -rp "$(echo -e "${GREEN}[INPUT]${NC} $1")" "$2"
}

API_URL="https://shared.pika.net.cn/api/fs/list"
API_PATH="/Mirrors/OSImages/PikaCloudOS/VmwareOS"
DOWNLOAD_BASE_URL="https://shared.pika.net.cn/d"

STORAGE_PATH=""

declare -a IMAGE_LIST=()
declare -a IMAGE_NAMES=()
declare -a IMAGE_SIZES=()

format_size() {
    local size=$1
    if [ $size -lt 1024 ]; then
        echo "${size}B"
    elif [ $size -lt 1048576 ]; then
        echo "$(awk "BEGIN {printf \"%.2f\", $size/1024}")KB"
    elif [ $size -lt 1073741824 ]; then
        echo "$(awk "BEGIN {printf \"%.2f\", $size/1048576}")MB"
    else
        echo "$(awk "BEGIN {printf \"%.2f\", $size/1073741824}")GB"
    fi
}

fetch_image_list() {
    info "正在获取镜像列表..."
    
    local response=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{\"path\":\"$API_PATH\",\"password\":\"\",\"page\":1,\"per_page\":0,\"refresh\":true}")
    
    if [ -z "$response" ]; then
        err "无法连接到服务器"
        return 1
    fi
    
    local code=$(echo "$response" | grep -o '"code":[0-9]*' | cut -d':' -f2)
    if [ "$code" != "200" ]; then
        err "获取镜像列表失败"
        return 1
    fi
    
    IMAGE_LIST=()
    IMAGE_NAMES=()
    IMAGE_SIZES=()
    
    local content=$(echo "$response" | grep -o '"content":\[.*\]' | sed 's/"content"://')
    
    while IFS= read -r line; do
        if echo "$line" | grep -q '"name".*img\.rar"'; then
            local name=$(echo "$line" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
            local size=$(echo "$line" | grep -o '"size":[0-9]*' | cut -d':' -f2)
            
            IMAGE_NAMES+=("$name")
            IMAGE_SIZES+=("$size")
            IMAGE_LIST+=("$name")
        fi
    done < <(echo "$content" | grep -o '{[^}]*}')
    
    if [ ${#IMAGE_LIST[@]} -eq 0 ]; then
        warn "未找到可用的镜像文件"
        return 1
    fi
    
    ok "找到 ${#IMAGE_LIST[@]} 个镜像文件"
    return 0
}

show_image_list() {
    echo
    echo "============================================================================================================"
    local idx=1
    for i in "${!IMAGE_NAMES[@]}"; do
        local size_str=$(format_size ${IMAGE_SIZES[$i]})
        printf "%3d) %-50s [%s]\n" "$idx" "${IMAGE_NAMES[$i]}" "$size_str"
        ((idx++))
    done
    echo "============================================================================================================"
    echo
}

download_image() {
    local image_name="$1"
    local download_url="${DOWNLOAD_BASE_URL}${API_PATH}/${image_name}"
    local output_file="${STORAGE_PATH}/${image_name}"
    
    info "下载: ${image_name}"
    info "URL: ${download_url}"
    
    if [ -f "$output_file" ]; then
        warn "文件已存在: $output_file"
        reading "是否覆盖？(y/n) [n]: " overwrite
        if [[ ! "$overwrite" =~ ^[yY]$ ]]; then
            info "跳过下载"
            return 0
        fi
    fi
    
    if wget --show-progress -O "$output_file" "$download_url" 2>&1; then
        ok "下载完成: $output_file"
        return 0
    else
        err "下载失败: $image_name"
        rm -f "$output_file"
        return 1
    fi
}

set_storage_path() {
    echo
    info "=== 设置镜像存储路径 ==="
    
    if [ -n "$STORAGE_PATH" ]; then
        info "当前存储路径: $STORAGE_PATH"
        reading "是否更改？(y/n) [n]: " change
        if [[ ! "$change" =~ ^[yY]$ ]]; then
            return 0
        fi
    fi
    
    reading "请输入镜像存储路径: " new_path
    
    if [ -z "$new_path" ]; then
        warn "路径不能为空"
        return 1
    fi
    
    new_path="${new_path/#\~/$HOME}"
    
    if [ ! -d "$new_path" ]; then
        reading "目录不存在，是否创建？(y/n) [y]: " create
        create=${create:-y}
        if [[ "$create" =~ ^[yY]$ ]]; then
            if mkdir -p "$new_path"; then
                ok "目录创建成功"
            else
                err "目录创建失败"
                return 1
            fi
        else
            return 1
        fi
    fi
    
    STORAGE_PATH="$new_path"
    ok "存储路径已设置: $STORAGE_PATH"
}

menu_download() {
    if [ -z "$STORAGE_PATH" ]; then
        warn "请先设置镜像存储路径"
        set_storage_path
        if [ -z "$STORAGE_PATH" ]; then
            return
        fi
    fi
    
    echo
    info "=== 下载镜像 ==="
    
    if ! fetch_image_list; then
        return
    fi
    
    show_image_list
    
    reading "输入编号，多个用逗号分隔，或 all 全部下载: " image_choices
    
    if [ -z "$image_choices" ]; then
        warn "未选择任何镜像"
        return
    fi
    
    local selected_indices=()
    if [[ "$image_choices" == "all" ]]; then
        for i in "${!IMAGE_LIST[@]}"; do
            selected_indices+=($((i + 1)))
        done
    else
        IFS=',' read -ra choices <<< "$image_choices"
        for choice in "${choices[@]}"; do
            choice=$(echo "$choice" | xargs)
            if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#IMAGE_LIST[@]} ]; then
                selected_indices+=("$choice")
            else
                warn "无效的编号: $choice"
            fi
        done
    fi
    
    if [ ${#selected_indices[@]} -eq 0 ]; then
        warn "未选择任何有效镜像"
        return
    fi
    
    ok "已选择 ${#selected_indices[@]} 个镜像"
    echo
    
    local current=0
    local success=0
    local failed=0
    
    for idx in "${selected_indices[@]}"; do
        ((current++))
        local array_idx=$((idx - 1))
        echo "[$current/${#selected_indices[@]}]"
        if download_image "${IMAGE_LIST[$array_idx]}"; then
            ((success++))
        else
            ((failed++))
        fi
        echo
    done
    
    ok "下载完成: 成功 $success 个, 失败 $failed 个"
}

menu_list() {
    echo
    info "=== 刷新镜像列表 ==="
    
    if ! fetch_image_list; then
        return
    fi
    
    show_image_list
}

main_menu() {
    while true; do
        echo
        echo "================================"
        echo "    VMware 镜像下载脚本"
        echo "   OpenIDCS by PikaCloud"
        echo "================================"
        echo "1. 设置存储路径"
        echo "2. 下载镜像"
        echo "3. 查看镜像列表"
        echo "0. 退出"
        echo "================================"
        if [ -n "$STORAGE_PATH" ]; then
            info "当前存储路径: $STORAGE_PATH"
        else
            warn "未设置存储路径"
        fi
        echo "================================"
        reading "请选择 [0-3]: " choice
        
        case "$choice" in
            1) set_storage_path ;;
            2) menu_download ;;
            3) menu_list ;;
            0) ok "退出"; exit 0 ;;
            *) warn "无效选择" ;;
        esac
    done
}

main_menu
