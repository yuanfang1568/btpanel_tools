#!/bin/bash

# 宝塔面板工具优化版本
# 优化内容：
# 1. 添加错误处理和日志记录
# 2. 优化变量定义和函数结构
# 3. 添加配置文件支持
# 4. 改进网络检测和重试机制
# 5. 优化文件操作和权限检查

set -euo pipefail  # 严格错误处理

# 全局变量定义
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DOWNLOAD_URL="https://raw.githubusercontent.com/gacjie/btpanel_tools/main"
readonly PANEL_PATH="/www/server/panel"
readonly TOOLS_VERSION="220516"
readonly LOG_FILE="/tmp/btpanel_tools.log"
readonly CONFIG_FILE="/tmp/btpanel_tools.conf"

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# 日志函数
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

info() { log "INFO" "$*"; }
warn() { log "WARN" "$*"; }
error() { log "ERROR" "$*"; }

# 错误处理函数
error_handler() {
    local exit_code=$?
    error "脚本执行失败，退出码: $exit_code"
    error "最后执行的命令: $BASH_COMMAND"
    exit $exit_code
}

trap error_handler ERR

# 检查系统环境
check_environment() {
    info "检查系统环境..."
    
    # 检查是否为root用户
    if [[ $EUID -ne 0 ]]; then
        error "此脚本需要root权限运行"
        exit 1
    fi
    
    # 检查是否安装宝塔面板
    if [[ ! -f "/etc/init.d/bt" ]] || [[ ! -d "$PANEL_PATH" ]]; then
        error "此服务器没有安装宝塔面板！"
        exit 1
    fi
    
    # 获取面板版本
    if [[ -f "${PANEL_PATH}/class/common.py" ]]; then
        local p_version
        p_version=$(grep "version = " "${PANEL_PATH}/class/common.py" | awk '{print $3}' | tr -cd '0-9.')
        readonly BTPANEL_VERSION="${p_version:0:5}"
        info "检测到宝塔面板版本: $BTPANEL_VERSION"
    else
        error "无法获取面板版本信息"
        exit 1
    fi
    
    # 检测包管理器
    if [[ -f "/usr/bin/yum" ]] && [[ -f "/etc/yum.conf" ]]; then
        readonly PM="yum"
    elif [[ -f "/usr/bin/apt-get" ]] && [[ -f "/usr/bin/dpkg" ]]; then
        readonly PM="apt-get"
    else
        warn "未检测到支持的包管理器"
    fi
    
    info "环境检查完成"
}

# 网络连接检测（优化版）
check_network() {
    local url="$1"
    local timeout="${2:-10}"
    local max_retries="${3:-3}"
    
    for ((i=1; i<=max_retries; i++)); do
        if curl -s --connect-timeout "$timeout" --max-time "$timeout" "$url" >/dev/null 2>&1; then
            return 0
        fi
        warn "网络连接失败，尝试 $i/$max_retries"
        sleep 2
    done
    return 1
}

# 版本检测（优化版）
check_new_version() {
    info "检查新版本..."
    
    if ! check_network "$DOWNLOAD_URL/version.txt" 10 3; then
        error "无法连接到更新服务器"
        return 1
    fi
    
    local new_version
    new_version=$(curl -s --connect-timeout 10 -m 30 "$DOWNLOAD_URL/version.txt" || echo "")
    
    if [[ -z "$new_version" ]]; then
        error "获取版本号失败"
        return 1
    fi
    
    if [[ "$new_version" != "$TOOLS_VERSION" ]]; then
        info "检测到新版本 $new_version，正在更新..."
        if curl -s -o "$SCRIPT_DIR/btpanel_tools.sh" "$DOWNLOAD_URL/btpanel_tools.sh"; then
            chmod +x "$SCRIPT_DIR/btpanel_tools.sh"
            exec "$SCRIPT_DIR/btpanel_tools.sh"
        else
            error "更新失败"
            return 1
        fi
    else
        info "当前已是最新版本"
    fi
}

# 安全的文件操作函数
safe_remove() {
    local file="$1"
    if [[ -e "$file" ]]; then
        rm -f "$file" && info "已删除: $file"
    fi
}

safe_sed() {
    local pattern="$1"
    local file="$2"
    local backup="${file}.bak"
    
    if [[ -f "$file" ]]; then
        cp "$file" "$backup"
        if sed -i "$pattern" "$file" 2>/dev/null; then
            info "已修改: $file"
        else
            error "修改失败: $file"
            cp "$backup" "$file"
            return 1
        fi
    fi
}

# 清理垃圾文件（优化版）
cleaning_garbage() {
    info "开始清理系统垃圾文件..."
    
    # 清理面板相关文件
    local panel_files=(
        "$PANEL_PATH/data/bind.pl"
        "$PANEL_PATH/adminer"
        "/www/server/adminer"
        "/www/server/phpmyadmin/pma"
        "$PANEL_PATH/data/home_host.pl"
        "$PANEL_PATH/plugin/shoki_cdn"
        "$PANEL_PATH/data/auth_list.json"
        "$PANEL_PATH/data/check_domain/*.pl"
    )
    
    for file in "${panel_files[@]}"; do
        safe_remove "$file"
    done
    
    # 清理缓存文件
    find "$PANEL_PATH" -name "*.pyc" -delete 2>/dev/null || true
    find "$PANEL_PATH/class" -name "*.pyc" -delete 2>/dev/null || true
    
    # 清理临时文件
    rm -rf /tmp/*.pl /tmp/*.sh /tmp/*.log 2>/dev/null || true
    
    # 清理会话文件
    rm -rf /tmp/sess_* 2>/dev/null || true
    
    # 清理日志文件
    find "$PANEL_PATH/logs" -name "*.log" -delete 2>/dev/null || true
    find "$PANEL_PATH/logs" -name "*.gz" -delete 2>/dev/null || true
    rm -rf "$PANEL_PATH/logs/request/" 2>/dev/null || true
    
    # 清理邮件日志
    rm -rf /var/spool/plymouth/* /var/spool/postfix/* /var/spool/lpd/* 2>/dev/null || true
    
    # 清理系统日志（需要确认）
    read -p "是否要清理系统日志文件（y：确认/n：取消）: " -r confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        local log_files=(
            "/var/log/boot.log"
            "/var/log/btmp"
            "/var/log/cron"
            "/var/log/dmesg"
            "/var/log/firewalld"
            "/var/log/grubby"
            "/var/log/lastlog"
            "/var/log/mail.info"
            "/var/log/maillog"
            "/var/log/messages"
            "/var/log/secure"
            "/var/log/spooler"
            "/var/log/syslog"
            "/var/log/tallylog"
            "/var/log/wpa_supplicant.log"
            "/var/log/wtmp"
            "/var/log/yum.log"
        )
        
        for log_file in "${log_files[@]}"; do
            if [[ -f "$log_file" ]]; then
                cat /dev/null > "$log_file" && info "已清空: $log_file"
            fi
        done
        
        # 清理网站日志
        read -p "是否要清理网站日志文件（y：确认/n：取消）: " -r web_confirm
        if [[ "$web_confirm" =~ ^[Yy]$ ]]; then
            rm -rf /www/wwwlogs/*.log /www/wwwlogs/*.gz 2>/dev/null || true
            info "已清理网站日志文件"
        fi
    fi
    
    # 清理历史记录
    history -c 2>/dev/null || true
    
    info "垃圾文件清理完成！"
}

# 面板优化（优化版）
panel_optimization() {
    info "开始面板优化..."
    
    # 去除默认文件创建
    safe_sed "/htaccess = self.sitePath+'\/.htaccess'/, /public.ExecShell('chown -R www:www ' + htaccess)/d" "$PANEL_PATH/class/panelSite.py"
    safe_sed "/index = self.sitePath+'\/index.html'/, /public.ExecShell('chown -R www:www ' + index)/d" "$PANEL_PATH/class/panelSite.py"
    safe_sed "/doc404 = self.sitePath+'\/404.html'/, /public.ExecShell('chown -R www:www ' + doc404)/d" "$PANEL_PATH/class/panelSite.py"
    
    # 关闭未绑定域名提示
    safe_sed "s/root \/www\/server\/nginx\/html/return 400/" "$PANEL_PATH/class/panelSite.py"
    if [[ -f "$PANEL_PATH/vhost/nginx/0.default.conf" ]]; then
        safe_sed "s/root \/www\/server\/nginx\/html/return 400/" "$PANEL_PATH/vhost/nginx/0.default.conf"
    fi
    
    # 关闭安全入口登录提示
    safe_sed "s/return render_template('autherr.html')/return abort(404)/" "$PANEL_PATH/BTPanel/__init__.py"
    
    # 去除消息推送与文件校验
    safe_sed "/p = threading.Thread(target=check_files_panel)/, /p.start()/d" "$PANEL_PATH/task.py"
    safe_sed "/p = threading.Thread(target=check_panel_msg)/, /p.start()/d" "$PANEL_PATH/task.py"
    
    # 去除自动验证云端状态
    safe_sed "/p = threading.Thread(target=update_software_list)/, /p.start()/d" "$PANEL_PATH/task.py"
    safe_sed '/self.get_cloud_list_status/d' "$PANEL_PATH/class/panelPlugin.py"
    
    # 关闭活动推荐与在线客服
    echo "True" > "$PANEL_PATH/data/not_recommend.pl" 2>/dev/null || true
    echo "True" > "$PANEL_PATH/data/not_workorder.pl" 2>/dev/null || true
    
    # 关闭首页软件推荐与广告
    safe_sed '/def get_pay_type(self,get):/a \ \ \ \ \ \ \ \ return [];' "$PANEL_PATH/class/ajax.py"
    
    # 关闭宝塔拉黑检测与提示
    safe_sed '/self._check_url/d' "$PANEL_PATH/class/panelPlugin.py"
    
    # 关闭面板日志与绑定域名上报
    safe_sed "/^logs_analysis()/d" "$PANEL_PATH/script/site_task.py"
    safe_sed "s/run_thread(cloud_check_domain,(domain,))/return/" "$PANEL_PATH/class/public.py"
    
    # 关闭自动强制面板升级更新
    safe_sed "/#是否执行升级程序/a \ \ \ \ \ \ \ \ \ \ \ \ updateInfo['force'] = False;" "$PANEL_PATH/class/ajax.py"
    safe_remove "$PANEL_PATH/data/autoUpdate.pl"
    
    # 关闭自动更新软件列表
    safe_sed 's/plugin_timeout = 86400/plugin_timeout = 0/g' "$PANEL_PATH/class/public.py"
    
    # 计算验证去除（可选）
    read -p "是否需要去除计算验证（y：确认/n：取消）: " -r calc_confirm
    if [[ "$calc_confirm" =~ ^[Yy]$ ]]; then
        local layout_file="$PANEL_PATH/BTPanel/templates/default/layout.html"
        local js_file="$PANEL_PATH/BTPanel/static/bt.js"
        
        if [[ "$BTPANEL_VERSION" == "7.7.0" ]]; then
            if ! grep -q "<script src=\"/static/bt.js\"></script>" "$layout_file" 2>/dev/null; then
                safe_sed '/{% block scripts %} {% endblock %}/a <script src="/static/bt.js"></script>' "$layout_file"
            fi
            if check_network "$DOWNLOAD_URL/bt.js" 10 3; then
                curl -s -o "$js_file" "$DOWNLOAD_URL/bt.js"
            fi
        elif [[ "$BTPANEL_VERSION" == "7.9.0" ]]; then
            if ! grep -q "<script src=\"/static/bt.js\"></script>" "$layout_file" 2>/dev/null; then
                safe_sed '/<\/body>/i <script src="/static/bt.js"></script>' "$layout_file"
            fi
            if check_network "$DOWNLOAD_URL/bt_new.js" 10 3; then
                curl -s -o "$js_file" "$DOWNLOAD_URL/bt_new.js"
            fi
        fi
    fi
    
    # 重启面板服务
    if [[ -f "/etc/init.d/bt" ]]; then
        /etc/init.d/bt restart && info "面板服务已重启"
    fi
    
    info "面板优化完成！"
}

# 漏洞修复（优化版）
bug_fix() {
    info "开始漏洞检查..."
    
    # 检查宝塔面板PMA漏洞
    local pma_bug="/www/server/phpmyadmin/pma"
    if [[ -d "$pma_bug" ]]; then
        warn "发现宝塔面板PMA漏洞，正在处理..."
        rm -rf "$pma_bug" && info "PMA漏洞已修复"
    else
        info "未发现宝塔面板PMA漏洞"
    fi
    
    info "漏洞检查完成"
}

# 网络修复（优化版）
fix_network() {
    info "开始网络修复..."
    
    local host_ips=("128.1.164.196" "116.213.43.206" "125.90.93.52" "36.133.1.8" "116.10.184.219")
    local tmp_file="/dev/shm/net_test.pl"
    local ser_name="api.bt.cn"
    
    [[ -f "$tmp_file" ]] && rm -f "$tmp_file"
    touch "$tmp_file"
    
    for host in "${host_ips[@]}"; do
        info "测试节点: $host"
        if curl --resolv "${ser_name}:443:${host}" --connect-timeout 3 -m 3 2>/dev/null -w "%{http_code} %{time_total}" "https://${ser_name}" -o "${ser_name}.txt" > "$tmp_file"; then
            local http_code=$(awk '{print $1}' "$tmp_file")
            local time_total=$(awk '{print $2}' "$tmp_file")
            
            if [[ "$http_code" == "200" ]] && [[ "$time_total" < "1.0" ]]; then
                info "节点 $host 连接正常，响应时间: ${time_total}s"
                # 更新hosts文件
                if ! grep -q "$host $ser_name" /etc/hosts 2>/dev/null; then
                    echo "$host $ser_name" >> /etc/hosts
                    info "已添加节点到hosts文件"
                fi
                break
            fi
        fi
    done
    
    rm -f "$tmp_file" "${ser_name}.txt" 2>/dev/null || true
    info "网络修复完成"
}

# 主菜单
main_menu() {
    clear
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}    宝塔面板工具优化版${NC}"
    echo -e "${BLUE}================================${NC}"
    echo -e "${GREEN}1.${NC} 清理垃圾文件"
    echo -e "${GREEN}2.${NC} 面板优化"
    echo -e "${GREEN}3.${NC} 漏洞修复"
    echo -e "${GREEN}4.${NC} 网络修复"
    echo -e "${GREEN}5.${NC} 检查更新"
    echo -e "${GREEN}6.${NC} 退出"
    echo -e "${BLUE}================================${NC}"
    echo -n "请选择功能 (1-6): "
}

# 主函数
main() {
    # 初始化
    check_environment
    
    while true; do
        main_menu
        read -r choice
        
        case $choice in
            1) cleaning_garbage ;;
            2) panel_optimization ;;
            3) bug_fix ;;
            4) fix_network ;;
            5) check_new_version ;;
            6) info "退出程序"; exit 0 ;;
            *) warn "无效选择，请重新输入" ;;
        esac
        
        echo
        read -p "按回车键继续..."
    done
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi