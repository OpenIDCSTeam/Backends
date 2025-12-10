"""
OpenIDCS Flask Server
提供主机和虚拟机管理的Web界面和API接口
"""
import secrets
import threading
import traceback
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

from loguru import logger
from HostModule.HostManage import HostManage
from HostModule.RestManage import RestManager

app = Flask(__name__, template_folder='WebDesigns', static_folder='static')
app.secret_key = secrets.token_hex(32)

# 全局主机管理实例
hs_manage = HostManage()
# 全局REST管理器实例
rest_manager = RestManager(hs_manage)


# ============================================================================
# 认证装饰器（保持向后兼容）
# ============================================================================
def require_auth(f):
    """需要登录或Bearer Token认证的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 检查Bearer Token
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if token and token == hs_manage.bearer:
                return f(*args, **kwargs)
        # 检查Session登录
        if session.get('logged_in'):
            return f(*args, **kwargs)
        # API请求返回JSON错误
        if request.is_json or request.path.startswith('/api/'):
            return rest_manager.api_response(401, '未授权访问', None)
        # 页面请求重定向到登录页
        return redirect(url_for('login'))
    return decorated


def api_response_wrapper(code=200, msg='success', data=None):
    """统一API响应格式包装器"""
    return rest_manager.api_response(code, msg, data)


# ============================================================================
# 页面路由
# ============================================================================
@app.route('/')
def index():
    """首页重定向"""
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'GET':
        return render_template('login.html', title='OpenIDCS - 登录')

    # POST登录处理
    data = request.get_json() or request.form
    token = data.get('token', '')

    if token and token == hs_manage.bearer:
        session['logged_in'] = True
        session['username'] = 'admin'
        return api_response_wrapper(200, '登录成功', {'redirect': '/admin'})

    return api_response_wrapper(401, 'Token错误')


@app.route('/exitd')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin')
@require_auth
def dashboard():
    """仪表盘页面"""
    return render_template('dashboard.html',
                           title='OpenIDCS - 仪表盘',
                           username=session.get('username', 'admin'))


@app.route('/hosts')
@require_auth
def hosts_page():
    """主机管理页面"""
    from MainObject.Server.HSEngine import HEConfig
    return render_template('hosts.html',
                           title='OpenIDCS - 主机管理',
                           username=session.get('username', 'admin'),
                           engine_config=HEConfig)


@app.route('/debug')
@require_auth
def logs_page():
    """日志管理页面"""
    return render_template('logs.html',
                           title='OpenIDCS - 日志管理',
                           username=session.get('username', 'admin'))


@app.route('/tasks')
@require_auth
def tasks_page():
    """任务管理页面"""
    return render_template('tasks.html',
                           title='OpenIDCS - 任务管理',
                           username=session.get('username', 'admin'))


@app.route('/hosts/<hs_name>/vms')
@require_auth
def vms_page(hs_name):
    """虚拟机管理页面"""
    return render_template('vms.html',
                           title=f'OpenIDCS - 虚拟机管理 - {hs_name}',
                           username=session.get('username', 'admin'),
                           hs_name=hs_name)


@app.route('/hosts/<hs_name>/vms/<vm_uuid>')
@require_auth
def vm_detail_page(hs_name, vm_uuid):
    """虚拟机详情页面"""
    return render_template('vm_detail.html',
                           title=f'OpenIDCS - {vm_uuid}',
                           username=session.get('username', 'admin'),
                           hs_name=hs_name,
                           vm_uuid=vm_uuid)


@app.route('/settings')
@require_auth
def settings_page():
    """设置页面"""
    return render_template('settings.html',
                           title='OpenIDCS - 系统设置',
                           username=session.get('username', 'admin'))


# ============================================================================
# 系统管理API - /api/system/<option>
# ============================================================================

# 重置Token ########################################################################
@app.route('/api/system/resets', methods=['POST'])
@require_auth
def api_reset_token():
    """重置访问Token"""
    return rest_manager.reset_token()


# 设置Token ########################################################################
@app.route('/api/system/create', methods=['POST'])
@require_auth
def api_set_token():
    """设置指定Token"""
    return rest_manager.set_token()


# 获取Token ########################################################################
@app.route('/api/system/tquery', methods=['GET'])
@require_auth
def api_get_token():
    """获取当前Token"""
    return rest_manager.get_token()


# 引擎类型 ########################################################################
@app.route('/api/system/engine', methods=['GET'])
@require_auth
def api_get_engine_types():
    """获取支持的主机引擎类型"""
    return rest_manager.get_engine_types()


# 保存配置 ########################################################################
@app.route('/api/system/saving', methods=['POST'])
@require_auth
def api_save_system():
    """保存系统配置"""
    return rest_manager.save_system()


# 加载配置 ########################################################################
@app.route('/api/system/loader', methods=['POST'])
@require_auth
def api_load_system():
    """加载系统配置"""
    return rest_manager.load_system()


# 系统统计 ########################################################################
@app.route('/api/system/statis', methods=['GET'])
@require_auth
def api_get_system_stats():
    """获取系统统计信息"""
    return rest_manager.get_system_stats()


# 获取日志 ########################################################################
@app.route('/api/system/logger/detail', methods=['GET'])
@require_auth
def api_get_logs():
    """获取日志记录"""
    return rest_manager.get_logs()


# 获取任务 ########################################################################
@app.route('/api/system/tasker', methods=['GET'])
@require_auth
def api_get_tasks():
    """获取任务记录"""
    return rest_manager.get_tasks()


# ============================================================================
# 主机管理API - /api/server/<option>/<key?>
# ============================================================================

# 主机列表 ########################################################################
@app.route('/api/server/detail', methods=['GET'])
@require_auth
def api_get_hosts():
    """获取所有主机列表"""
    return rest_manager.get_hosts()


# 主机详情 ########################################################################
@app.route('/api/server/detail/<hs_name>', methods=['GET'])
@require_auth
def api_get_host(hs_name):
    """获取单个主机详情"""
    return rest_manager.get_host(hs_name)


# 添加主机 ########################################################################
@app.route('/api/server/create', methods=['POST'])
@require_auth
def api_add_host():
    """添加主机"""
    return rest_manager.add_host()


# 修改主机 ########################################################################
@app.route('/api/server/update/<hs_name>', methods=['PUT'])
@require_auth
def api_update_host(hs_name):
    """修改主机配置"""
    return rest_manager.update_host(hs_name)


# 删除主机 ########################################################################
@app.route('/api/server/delete/<hs_name>', methods=['DELETE'])
@require_auth
def api_delete_host(hs_name):
    """删除主机"""
    return rest_manager.delete_host(hs_name)


# 电源控制 ########################################################################
@app.route('/api/server/powers/<hs_name>', methods=['POST'])
@require_auth
def api_host_power(hs_name):
    """主机电源控制（启用/禁用）"""
    return rest_manager.host_power(hs_name)


# 主机状态 ########################################################################
@app.route('/api/server/status/<hs_name>', methods=['GET'])
@require_auth
def api_get_host_status(hs_name):
    """获取主机状态"""
    return rest_manager.get_host_status(hs_name)


# ============================================================================
# 虚拟机管理API - /api/client/<option>/<key?>
# ============================================================================

# 虚拟机列表 ########################################################################
@app.route('/api/client/detail/<hs_name>', methods=['GET'])
@require_auth
def api_get_vms(hs_name):
    """获取主机下所有虚拟机"""
    return rest_manager.get_vms(hs_name)


# 虚拟机详情 ########################################################################
@app.route('/api/client/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm(hs_name, vm_uuid):
    """获取单个虚拟机详情"""
    return rest_manager.get_vm(hs_name, vm_uuid)


# 创建虚拟机 ########################################################################
@app.route('/api/client/create/<hs_name>', methods=['POST'])
@require_auth
def api_create_vm(hs_name):
    """创建虚拟机"""
    return rest_manager.create_vm(hs_name)


# 修改虚拟机 ########################################################################
@app.route('/api/client/update/<hs_name>/<vm_uuid>', methods=['PUT'])
@require_auth
def api_update_vm(hs_name, vm_uuid):
    """修改虚拟机配置"""
    return rest_manager.update_vm(hs_name, vm_uuid)


# 删除虚拟机 ########################################################################
@app.route('/api/client/delete/<hs_name>/<vm_uuid>', methods=['DELETE'])
@require_auth
def api_delete_vm(hs_name, vm_uuid):
    """删除虚拟机"""
    return rest_manager.delete_vm(hs_name, vm_uuid)


# 电源控制 ########################################################################
@app.route('/api/client/powers/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_vm_power(hs_name, vm_uuid):
    """虚拟机电源控制"""
    return rest_manager.vm_power(hs_name, vm_uuid)


# VNC控制台 ########################################################################
@app.route('/api/client/remote/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_vm_console(hs_name, vm_uuid):
    """获取虚拟机VNC控制台URL"""
    return rest_manager.vm_console(hs_name, vm_uuid)


# 修改密码 ########################################################################
@app.route('/api/client/password/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_vm_password(hs_name, vm_uuid):
    """修改虚拟机密码"""
    return rest_manager.vm_password(hs_name, vm_uuid)


# 虚拟机状态 ########################################################################
@app.route('/api/client/status/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_status(hs_name, vm_uuid):
    """获取虚拟机状态"""
    return rest_manager.get_vm_status(hs_name, vm_uuid)


# 扫描虚拟机 ########################################################################
@app.route('/api/client/scaner/<hs_name>', methods=['POST'])
@require_auth
def api_scan_vms(hs_name):
    """扫描主机上的虚拟机"""
    return rest_manager.scan_vms(hs_name)


# 上报状态 ########################################################################
@app.route('/api/client/upload', methods=['POST'])
def api_vm_upload():
    """虚拟机上报状态数据（无需认证）"""
    return rest_manager.vm_upload()


# ============================================================================
# 虚拟机网络配置API - NAT端口转发
# ============================================================================

# 获取NAT规则 ########################################################################
@app.route('/api/client/natget/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_nat_rules(hs_name, vm_uuid):
    """获取虚拟机NAT端口转发规则"""
    return rest_manager.get_vm_nat_rules(hs_name, vm_uuid)


# 添加NAT规则 ########################################################################
@app.route('/api/client/natadd/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_add_vm_nat_rule(hs_name, vm_uuid):
    """添加虚拟机NAT端口转发规则"""
    return rest_manager.add_vm_nat_rule(hs_name, vm_uuid)


# 删除NAT规则 ########################################################################
@app.route('/api/client/natdel/<hs_name>/<vm_uuid>/<int:rule_index>', methods=['DELETE'])
@require_auth
def api_delete_vm_nat_rule(hs_name, vm_uuid, rule_index):
    """删除虚拟机NAT端口转发规则"""
    return rest_manager.delete_vm_nat_rule(hs_name, vm_uuid, rule_index)


# ============================================================================
# 虚拟机网络配置API - IP地址管理
# ============================================================================

# 获取IP列表 ########################################################################
@app.route('/api/client/ipaddr/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_ip_addresses(hs_name, vm_uuid):
    """获取虚拟机IP地址列表"""
    return rest_manager.get_vm_ip_addresses(hs_name, vm_uuid)


# 添加IP地址 ########################################################################
@app.route('/api/client/ipaddr/create/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_add_vm_ip_address(hs_name, vm_uuid):
    """添加虚拟机IP地址"""
    return rest_manager.add_vm_ip_address(hs_name, vm_uuid)


# 删除IP地址 ########################################################################
@app.route('/api/client/ipaddr/delete/<hs_name>/<vm_uuid>/<int:ip_index>', methods=['DELETE'])
@require_auth
def api_delete_vm_ip_address(hs_name, vm_uuid, ip_index):
    """删除虚拟机IP地址"""
    return rest_manager.delete_vm_ip_address(hs_name, vm_uuid, ip_index)


# ============================================================================
# 虚拟机网络配置API - 反向代理管理
# ============================================================================

# 获取代理配置 ########################################################################
@app.route('/api/client/proxys/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_proxy_configs(hs_name, vm_uuid):
    """获取虚拟机反向代理配置列表"""
    return rest_manager.get_vm_proxy_configs(hs_name, vm_uuid)


# 添加代理配置 ########################################################################
@app.route('/api/client/proxys/create/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_add_vm_proxy_config(hs_name, vm_uuid):
    """添加虚拟机反向代理配置"""
    return rest_manager.add_vm_proxy_config(hs_name, vm_uuid)


# 删除代理配置 ########################################################################
@app.route('/api/client/proxys/delete/<hs_name>/<vm_uuid>/<int:proxy_index>', methods=['DELETE'])
@require_auth
def api_delete_vm_proxy_config(hs_name, vm_uuid, proxy_index):
    """删除虚拟机反向代理配置"""
    return rest_manager.delete_vm_proxy_config(hs_name, vm_uuid, proxy_index)


# ============================================================================
# 定时任务
# ============================================================================
def cron_scheduler():
    """定时任务调度器，每分钟执行一次exe_cron"""
    try:
        hs_manage.exe_cron()
    except Exception as e:
        traceback.print_exc()
        logger.error(f"[Cron] 执行定时任务出错: {e}")

    # 设置下一次执行（60秒后）
    timer = threading.Timer(60, cron_scheduler)
    timer.daemon = True  # 设为守护线程，主程序退出时自动结束
    timer.start()


def start_cron_scheduler():
    """启动定时任务调度器，立即执行一次并开始定时循环（非阻塞）"""

    def initial_run():
        """初始执行，在单独线程中运行以避免阻塞启动"""
        try:
            hs_manage.exe_cron()
            logger.info("[Cron] 初始执行完成")
        except Exception as e:
            logger.error(f"[Cron] 初始执行出错: {e}")

        # 初始执行完成后，60秒后开始定时循环
        timer = threading.Timer(60, cron_scheduler)
        timer.daemon = True
        timer.start()

    logger.info("[Cron] 启动定时任务调度器...")
    # 在单独线程中执行初始化，不阻塞主程序启动
    init_thread = threading.Thread(target=initial_run, daemon=True)
    init_thread.start()
    logger.info("[Cron] 定时任务已启动（后台运行），每60秒执行一次")


# ============================================================================
# 启动服务
# ============================================================================
def init_app():
    """初始化应用"""
    # 加载已保存的配置
    try:
        hs_manage.all_load()
    except Exception as e:
        logger.error(f"加载配置失败: {e}")

    # 如果没有Token，生成一个
    if not hs_manage.bearer:
        hs_manage.set_pass()
        logger.info(f"已生成访问Token: {hs_manage.bearer}")

    # 启动定时任务调度器
    start_cron_scheduler()


if __name__ == '__main__':
    init_app()
    logger.info(f"\n{'=' * 60}")
    logger.info(f"OpenIDCS Server 启动中...")
    logger.info(f"访问地址: http://127.0.0.1:1880")
    logger.info(f"访问Token: {hs_manage.bearer}")
    logger.info(f"{'=' * 60}\n")

    app.run(host='0.0.0.0', port=1880, debug=True)