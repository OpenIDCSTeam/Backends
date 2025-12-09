"""
RestManage - REST API管理模块
提供主机和虚拟机管理的API接口处理函数
"""
import json
import random
import string
import traceback
from functools import wraps
from flask import request, jsonify, session, redirect, url_for

from MainObject.Config.HSConfig import HSConfig
from MainObject.Server.HSEngine import HEConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Config.NCConfig import NCConfig
from MainObject.Public.HWStatus import HWStatus


# ============================================================================
# 认证装饰器和响应函数
# ============================================================================

def require_auth(f):
    """需要登录或Bearer Token认证的装饰器"""

    @wraps(f)
    def decorated(hs_manage, *args, **kwargs):
        # 检查Bearer Token
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if token and token == hs_manage.bearer:
                return f(hs_manage, *args, **kwargs)
        # 检查Session登录
        if session.get('logged_in'):
            return f(hs_manage, *args, **kwargs)
        # API请求返回JSON错误
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'code': 401, 'msg': '未授权访问', 'data': None}), 401
        # 页面请求重定向到登录页
        return redirect(url_for('login'))

    return decorated


def api_response(code=200, msg='success', data=None):
    """统一API响应格式"""
    return jsonify({'code': code, 'msg': msg, 'data': data})


# ============================================================================
# 系统管理API - /api/system/<option>
# ============================================================================

# 重置Token ########################################################################
def reset_token(hs_manage):
    """重置访问Token"""
    new_token = hs_manage.set_pass()
    return api_response(200, 'Token已重置', {'token': new_token})


# 设置Token ########################################################################
def set_token(hs_manage):
    """设置指定Token"""
    data = request.get_json() or {}
    new_token = data.get('token', '')
    result = hs_manage.set_pass(new_token)
    return api_response(200, 'Token已设置', {'token': result})


# 获取Token ########################################################################
def get_token(hs_manage):
    """获取当前Token"""
    return api_response(200, 'success', {'token': hs_manage.bearer})


# 引擎类型 ########################################################################
def get_engine_types(hs_manage):
    """获取支持的主机引擎类型"""
    types_data = {}
    for engine_type, config in HEConfig.items():
        types_data[engine_type] = {
            'name': engine_type,
            'description': config.get('Descript', ''),
            'enabled': config.get('isEnable', False),
            'platform': config.get('Platform', []),
            'arch': config.get('CPU_Arch', []),
            'options': config.get('Optional', {}),
            'message': config.get('Messages', '')
        }
    return api_response(200, 'success', types_data)


# 保存配置 ########################################################################
def save_system(hs_manage):
    """保存系统配置"""
    if hs_manage.all_save():
        return api_response(200, '配置已保存')
    return api_response(500, '保存失败')


# 加载配置 ########################################################################
def load_system(hs_manage):
    """加载系统配置"""
    try:
        hs_manage.all_load()
        return api_response(200, '配置已加载')
    except Exception as e:
        return api_response(500, f'加载失败: {str(e)}')


# 系统统计 ########################################################################
def get_system_stats(hs_manage):
    """获取系统统计信息"""
    total_vms = 0
    running_vms = 0

    for server in hs_manage.engine.values():
        total_vms += len(server.vm_saving)
        # 统计运行中的虚拟机数量（根据实际状态判断）

    return api_response(200, 'success', {
        'host_count': len(hs_manage.engine),
        'vm_count': total_vms,
        'running_vm_count': running_vms
    })


# 获取日志 ########################################################################
def get_logs(hs_manage):
    """获取日志记录"""
    try:
        hs_name = request.args.get('hs_name')
        limit = int(request.args.get('limit', 100))

        # 直接从数据库查询以获取hs_name信息
        conn = hs_manage.save_data.get_db_sqlite()
        try:
            if hs_name:
                cursor = conn.execute(
                    "SELECT hs_name, log_level, log_data, created_at FROM hs_logger WHERE hs_name = ? ORDER BY created_at DESC LIMIT ?",
                    (hs_name, limit))
            else:
                cursor = conn.execute(
                    "SELECT hs_name, log_level, log_data, created_at FROM hs_logger ORDER BY created_at DESC LIMIT ?",
                    (limit,))

            processed_logs = []
            for row in cursor.fetchall():
                log_data = json.loads(row["log_data"])
                processed_log = {
                    'id': '',  # 可以添加rowid但暂时为空
                    'actions': log_data.get('actions', ''),
                    'message': log_data.get('message', '无消息内容'),
                    'success': log_data.get('success', True),
                    'results': log_data.get('results', {}),
                    'execute': log_data.get('execute', None),
                    'level': row['log_level'] or ('ERROR' if not log_data.get('success', True) else 'INFO'),
                    'timestamp': row['created_at'],
                    'host': row['hs_name'] or '系统',
                    'created_at': row['created_at']
                }
                processed_logs.append(processed_log)

            return api_response(200, '获取日志成功', processed_logs)
        finally:
            conn.close()
    except Exception as e:
        return api_response(500, f'获取日志失败: {str(e)}')


# 获取任务 ########################################################################
def get_tasks(hs_manage):
    """获取任务记录"""
    try:
        hs_name = request.args.get('hs_name')
        limit = int(request.args.get('limit', 100))

        # 从vm_tasker表获取任务数据
        conn = hs_manage.save_data.get_db_sqlite()
        try:
            if hs_name:
                cursor = conn.execute(
                    "SELECT task_data, created_at FROM vm_tasker WHERE hs_name = ? ORDER BY created_at DESC LIMIT ?",
                    (hs_name, limit))
            else:
                cursor = conn.execute("SELECT task_data, created_at FROM vm_tasker ORDER BY created_at DESC LIMIT ?",
                                      (limit,))

            tasks = []
            for row in cursor.fetchall():
                task_data = json.loads(row["task_data"])
                task_data['created_at'] = row["created_at"]
                tasks.append(task_data)

            return api_response(200, '获取任务成功', tasks)
        finally:
            conn.close()
    except Exception as e:
        return api_response(500, f'获取任务失败: {str(e)}')


# ============================================================================
# 主机管理API - /api/server/<option>/<key?>
# ============================================================================

# 主机列表 ########################################################################
def get_hosts(hs_manage):
    """获取所有主机列表"""
    hosts_data = {}
    for hs_name, server in hs_manage.engine.items():
        hosts_data[hs_name] = {
            'name': hs_name,
            'type': server.hs_config.server_type if server.hs_config else '',
            'addr': server.hs_config.server_addr if server.hs_config else '',
            'config': server.hs_config.__dict__() if server.hs_config else {},
            'vm_count': len(server.vm_saving),
            'status': 'active'  # 可以根据实际情况判断
        }
    return api_response(200, 'success', hosts_data)


# 主机详情 ########################################################################
def get_host(hs_manage, hs_name):
    """获取单个主机详情"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    # 检查是否需要详细信息（通过查询参数控制）
    include_status = request.args.get('status', 'false').lower() == 'true'

    # 构建基础响应数据（快速获取）
    host_data = {
        'name': hs_name,
        'type': server.hs_config.server_type if server.hs_config else '',
        'addr': server.hs_config.server_addr if server.hs_config else '',
        'config': server.hs_config.__dict__() if server.hs_config else {},
        'vm_count': len(server.vm_saving),
        'vm_list': list(server.vm_saving.keys()),
        'last_updated': getattr(server, '_status_cache_time', 0)
    }

    # 只有明确要求时才获取状态信息（避免每次调用都执行耗时的系统检查）
    if include_status:
        try:
            cached_status = getattr(server, '_status_cache', None)
            cache_time = getattr(server, '_status_cache_time', 0)

            # 检查缓存是否有效（30秒内的数据认为是新鲜的）
            import time
            current_time = int(time.time())
            if cached_status and (current_time - cache_time) < 30:
                host_data['status'] = cached_status
                host_data['status_source'] = 'cached'
            else:
                # 获取新状态并缓存
                status_obj = server.HSStatus()
                if status_obj:
                    host_data['status'] = status_obj.__dict__()
                    host_data['status_source'] = 'fresh'
                    # 缓存状态数据
                    server._status_cache = status_obj.__dict__()
                    server._status_cache_time = current_time
                else:
                    host_data['status'] = {}
                    host_data['status_source'] = 'unavailable'
        except Exception as e:
            host_data['status'] = {}
            host_data['status_source'] = 'error'
            host_data['status_error'] = str(e)
    else:
        host_data['status'] = None
        host_data['status_note'] = 'Use ?status=true to get detailed host status'

    return api_response(200, 'success', host_data)


# 添加主机 ########################################################################
def add_host(hs_manage):
    """添加主机"""
    data = request.get_json() or {}
    hs_name = data.get('name', '')
    hs_type = data.get('type', '')

    if not hs_name or not hs_type:
        return api_response(400, '主机名称和类型不能为空')

    # 构建配置
    config_data = data.get('config', {})
    config_data['server_type'] = hs_type
    hs_conf = HSConfig(**config_data)

    result = hs_manage.add_host(hs_name, hs_type, hs_conf)

    if result.success:
        hs_manage.all_save()
        return api_response(200, result.message)
    return api_response(400, result.message)


# 修改主机 ########################################################################
def update_host(hs_manage, hs_name):
    """修改主机配置"""
    data = request.get_json() or {}
    config_data = data.get('config', {})

    if not config_data:
        return api_response(400, '配置不能为空')

    hs_conf = HSConfig(**config_data)
    result = hs_manage.set_host(hs_name, hs_conf)

    if result.success:
        hs_manage.all_save()
        return api_response(200, result.message)
    return api_response(400, result.message)


# 删除主机 ########################################################################
def delete_host(hs_manage, hs_name):
    """删除主机"""
    if hs_manage.del_host(hs_name):
        hs_manage.all_save()
        return api_response(200, '主机已删除')
    return api_response(404, '主机不存在')


# 电源控制 ########################################################################
def host_power(hs_manage, hs_name):
    """主机电源控制（启用/禁用）"""
    data = request.get_json() or {}
    enable = data.get('enable', True)

    result = hs_manage.pwr_host(hs_name, enable)

    if result.success:
        hs_manage.all_save()
        return api_response(200, result.message)
    return api_response(400, result.message)


# 主机状态 ########################################################################
def get_host_status(hs_manage, hs_name):
    """获取主机状态"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    # 检查是否强制刷新缓存
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'

    import time
    current_time = int(time.time())
    cache_time = getattr(server, '_status_cache_time', 0)
    cached_status = getattr(server, '_status_cache', None)

    # 检查缓存是否有效（60秒内的数据认为是新鲜的）
    if not force_refresh and cached_status and (current_time - cache_time) < 60:
        return api_response(200, 'success', {
            'status': cached_status,
            'source': 'cached',
            'cached_at': cache_time,
            'age_seconds': current_time - cache_time
        })

    # 获取新状态
    try:
        status = server.HSStatus()
        if status:
            status_data = status.__dict__()
            # 更新缓存
            server._status_cache = status_data
            server._status_cache_time = current_time

            return api_response(200, 'success', {
                'status': status_data,
                'source': 'fresh' if force_refresh else 'auto_refreshed',
                'cached_at': current_time,
                'cache_duration': 60
            })
        else:
            return api_response(500, 'failed', {
                'message': '无法获取主机状态',
                'source': 'error'
            })
    except Exception as e:
        return api_response(500, 'failed', {
            'message': f'获取主机状态时出错: {str(e)}',
            'source': 'error'
        })


# ============================================================================
# 虚拟机管理API - /api/client/<option>/<key?>
# ============================================================================

# 虚拟机列表 ########################################################################
def get_vms(hs_manage, hs_name):
    """获取主机下所有虚拟机"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    # 从数据库重新加载数据
    server.data_get()

    def serialize_obj(obj):
        """将对象序列化为可JSON化的格式"""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, dict):
            return {k: serialize_obj(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [serialize_obj(item) for item in obj]
        # 检查是否为函数对象
        if callable(obj):
            return f"<function: {getattr(obj, '__name__', 'unknown')}>"
        # 尝试调用__dict__()方法
        if hasattr(obj, '__dict__') and callable(obj.__dict__):
            try:
                return obj.__dict__()
            except (TypeError, AttributeError):
                pass
        # 尝试使用vars()获取属性字典
        try:
            return {k: serialize_obj(v) for k, v in vars(obj).items()}
        except (TypeError, AttributeError):
            return str(obj)

    vms_data = {}
    for vm_uuid, vm_config in server.vm_saving.items():
        # 从 DataManage 获取状态（直接从数据库读取）=================
        status = None
        if server.save_data and server.hs_config.server_name:
            all_vm_status = server.save_data.get_vm_status(server.hs_config.server_name)
            status = all_vm_status.get(vm_uuid, [])
            # 只取最新的一条状态
            if status and len(status) > 0:
                status = [status[-1]]
        vms_data[vm_uuid] = {
            'uuid': vm_uuid,
            'config': serialize_obj(vm_config),
            'status': serialize_obj(status)
        }

    return api_response(200, 'success', vms_data)


# 虚拟机详情 ########################################################################
def get_vm(hs_manage, hs_name, vm_uuid):
    """获取单个虚拟机详情"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    vm_config = server.vm_saving.get(vm_uuid)
    if not vm_config:
        return api_response(404, '虚拟机不存在')

    status_dict = server.VMStatus(vm_uuid)
    # VMStatus返回dict[str, list[HWStatus]]，需要将每个HWStatus对象转换为字典
    status_result = []
    if status_dict and vm_uuid in status_dict:
        status_list = status_dict[vm_uuid]
        for hw_status in status_list:
            if hw_status is not None:
                # 如果已经是字典则直接使用，否则调用__dict__()方法
                if isinstance(hw_status, dict):
                    status_result.append(hw_status)
                elif hasattr(hw_status, '__dict__') and callable(getattr(hw_status, '__dict__', None)):
                    status_result.append(hw_status.__dict__())
                else:
                    status_result.append(hw_status)
            else:
                status_result.append(None)

    # 如果vm_config已经是字典则直接使用，否则调用__dict__()方法
    if isinstance(vm_config, dict):
        config_data = vm_config
    elif hasattr(vm_config, '__dict__') and callable(getattr(vm_config, '__dict__', None)):
        config_data = vm_config.__dict__()
    else:
        config_data = vm_config if vm_config else {}

    return api_response(200, 'success', {
        'uuid': vm_uuid,
        'config': config_data,
        'status': status_result
    })


# 创建虚拟机 ########################################################################
def create_vm(hs_manage, hs_name):
    """创建虚拟机"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    data = request.get_json() or {}

    # 处理网卡配置
    nic_all = {}
    nic_data = data.pop('nic_all', {})
    for nic_name, nic_conf in nic_data.items():
        nic_all[nic_name] = NCConfig(**nic_conf)

    # 创建虚拟机配置
    vm_config = VMConfig(**data, nic_all=nic_all)
    vm_config.vc_port = random.randint(10000, 59999)
    vm_config.vc_pass = ''.join(random.sample(string.ascii_letters + string.digits, 16))
    result = server.VMCreate(vm_config)

    if result and result.success:
        # 绑定静态IP ========================================================
        # 遍历所有网卡配置，如果指定了IP地址，则调用NCStatic绑定静态IP
        for nic_name, nic_config in vm_config.nic_all.items():
            if hasattr(nic_config, 'ip4_addr') and nic_config.ip4_addr:
                # 获取MAC地址
                mac_addr = nic_config.mac_addr if hasattr(nic_config, 'mac_addr') else ""
                if mac_addr and mac_addr != "00:00:00:00:00:00":
                    try:
                        print(f"[API] 绑定静态IP: {nic_config.ip4_addr} -> {mac_addr}")
                        nc_result = server.NCStatic(nic_config.ip4_addr, mac_addr, vm_config.vm_uuid, flag=True)
                        if nc_result.success:
                            print(f"[API] 静态IP绑定成功: {nic_config.ip4_addr}")
                        else:
                            print(f"[API] 静态IP绑定失败: {nc_result.message}")
                    except Exception as e:
                        print(f"[API] 静态IP绑定异常: {str(e)}")

        hs_manage.all_save()
        return api_response(200, result.message if result.message else '虚拟机创建成功')

    return api_response(400, result.message if result else '创建失败')


# 修改虚拟机 ########################################################################
def update_vm(hs_manage, hs_name, vm_uuid):
    """修改虚拟机配置"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    # 获取旧的虚拟机配置
    old_vm_config = None
    if hasattr(server, 'vm_saving') and vm_uuid in server.vm_saving:
        old_vm_config = server.vm_saving[vm_uuid]

    data = request.get_json() or {}
    data['vm_uuid'] = vm_uuid

    # 处理网卡配置
    nic_all = {}
    nic_data = data.pop('nic_all', {})
    for nic_name, nic_conf in nic_data.items():
        nic_all[nic_name] = NCConfig(**nic_conf)

    vm_config = VMConfig(**data, nic_all=nic_all)

    # old_vm_config = VMConfig(**old_vm_config)
    result = server.VMUpdate(vm_config, old_vm_config)

    if result and result.success:
        hs_manage.all_save()
        return api_response(200, result.message if result.message else '虚拟机更新成功')

    return api_response(400, result.message if result else '更新失败')


# 删除虚拟机 ########################################################################
def delete_vm(hs_manage, hs_name, vm_uuid):
    """删除虚拟机"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    result = server.VMDelete(vm_uuid)

    if result and result.success:
        hs_manage.all_save()
        return api_response(200, result.message if result.message else '虚拟机已删除')

    return api_response(400, result.message if result else '删除失败')


# 电源控制 ########################################################################
def vm_power(hs_manage, hs_name, vm_uuid):
    """虚拟机电源控制"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    data = request.get_json() or {}
    action = data.get('action', 'start')

    # 映射操作到VMPowers枚举
    power_map = {
        'start': VMPowers.S_START,
        'stop': VMPowers.S_CLOSE,
        'hard_stop': VMPowers.H_CLOSE,
        'reset': VMPowers.S_RESET,
        'hard_reset': VMPowers.H_RESET,
        'pause': VMPowers.A_PAUSE,
        'resume': VMPowers.A_WAKED
    }

    power_action = power_map.get(action)
    if not power_action:
        return api_response(400, f'不支持的操作: {action}')

    result = server.VMPowers(vm_uuid, power_action)

    if result and result.success:
        return api_response(200, result.message if result.message else f'电源操作 {action} 成功')

    return api_response(400, result.message if result else '操作失败')


# VNC控制台 ########################################################################
def vm_console(hs_manage, hs_name, vm_uuid):
    """获取虚拟机VNC控制台URL"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')
    try:
        console_url = server.VConsole(vm_uuid)
        print("[VNC控制台地址]", console_url)
        if console_url:
            return api_response(200, '获取成功', console_url)
        return api_response(400, '无法获取VNC控制台地址')
    except Exception as e:
        traceback.print_exc()
        return api_response(500, f'获取VNC控制台失败: {str(e)}')


# 虚拟机状态 ########################################################################
def get_vm_status(hs_manage, hs_name, vm_uuid):
    """获取虚拟机状态"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    status_dict = server.VMStatus(vm_uuid)
    # VMStatus返回dict[str, list[HWStatus]]，需要将每个HWStatus对象转换为字典
    if vm_uuid not in status_dict:
        return api_response(404, '虚拟机不存在')

    # 处理HWStatus列表
    status_list = status_dict[vm_uuid]
    result = []
    if status_list:
        for hw_status in status_list:
            if hw_status is not None:
                try:
                    result.append(hw_status.__dict__())
                except (TypeError, AttributeError):
                    result.append(vars(hw_status))
            else:
                result.append(None)
    return api_response(200, 'success', result)


# 扫描虚拟机 ########################################################################
def scan_vms(hs_manage, hs_name):
    """扫描主机上的虚拟机"""
    server = hs_manage.get_host(hs_name)
    if server:
        # 扫描前先从数据库重新加载数据
        server.data_get()

    data = request.get_json() or {}
    prefix = data.get('prefix', '')  # 前缀过滤，为空则使用主机配置的filter_name

    result = hs_manage.vms_scan(hs_name, prefix)

    if result.success:
        # 保存系统配置
        hs_manage.all_save()
        return api_response(200, result.message, result.results)

    return api_response(400, result.message)


# 上报状态 ########################################################################
def vm_upload(hs_manage):
    """虚拟机上报状态数据（无需认证）"""
    # 获取MAC地址参数
    mac_addr = request.args.get('nic', '')
    if not mac_addr:
        return api_response(400, 'MAC地址参数缺失')

    # 获取上报的状态数据
    status_data = request.get_json() or {}
    if not status_data:
        return api_response(400, '状态数据为空')

    print(f"[虚拟机上报] 收到MAC地址: {mac_addr}")

    # 遍历所有主机，查找匹配MAC地址的虚拟机
    found = False
    for hs_name, server in hs_manage.engine.items():
        if not server:
            continue

        # 从数据库重新加载虚拟机配置
        try:
            server.data_get()
            print(f"[虚拟机上报] 主机 {hs_name} 已加载 {len(server.vm_saving)} 个虚拟机配置")
        except Exception as e:
            print(f"[虚拟机上报] 主机 {hs_name} 加载配置失败: {e}")
            continue

        # 遍历该主机下的所有虚拟机配置
        for vm_uuid, vm_config in server.vm_saving.items():
            # 处理vm_config可能是字典或VMConfig对象的情况
            nic_all = vm_config.nic_all if hasattr(vm_config, 'nic_all') else vm_config.get('nic_all', {})

            print(f"[虚拟机上报] 检查虚拟机 {vm_uuid}, 网卡数量: {len(nic_all)}")

            # 检查虚拟机的网卡配置
            for nic_name, nic_config in nic_all.items():
                # 处理nic_config可能是字典或NCConfig对象的情况
                nic_mac = nic_config.mac_addr if hasattr(nic_config, 'mac_addr') else nic_config.get('mac_addr', '')

                print(f"[虚拟机上报] 网卡 {nic_name} MAC: {nic_mac} vs 上报MAC: {mac_addr}")

                if nic_mac.lower() == mac_addr.lower():
                    # 找到匹配的虚拟机，创建HWStatus对象
                    print(f"[虚拟机上报] 找到匹配的虚拟机! 主机: {hs_name}, UUID: {vm_uuid}")
                    print(f"[虚拟机上报] 状态数据: {status_data}")
                    try:
                        hw_status = HWStatus(**status_data)
                        print(f"[虚拟机上报] HWStatus对象创建成功: {hw_status}")

                        # 直接使用 DataManage 保存状态（立即写入数据库）=================
                        if server.save_data and server.hs_config.server_name:
                            print(f"[虚拟机上报] 开始调用 DataManage.add_vm_status")
                            result = server.save_data.add_vm_status(server.hs_config.server_name, vm_uuid, hw_status)
                            print(f"[虚拟机上报] add_vm_status 返回结果: {result}")
                            if result:
                                print(f"[虚拟机上报] 状态已成功保存到数据库")
                            else:
                                print(f"[虚拟机上报] 状态保存失败")
                        else:
                            print(f"[虚拟机上报] 警告: 数据库未初始化，save_data={server.save_data}, server_name={server.hs_config.server_name if server.hs_config else 'None'}")

                        found = True
                        # 获取虚拟机密码
                        vm_pass = vm_config.vc_pass if hasattr(vm_config, 'vc_pass') else vm_config.get('vc_pass', '')
                        return api_response(200, f'虚拟机 {vm_uuid} 状态已更新', {
                            'hs_name': hs_name,
                            'vm_uuid': vm_uuid,
                            'vm_pass': vm_pass
                        })
                    except Exception as e:
                        print(f"[虚拟机上报] 状态数据处理失败: {e}")
                        return api_response(500, f'状态数据处理失败: {str(e)}')

    if not found:
        print(f"[虚拟机上报] 未找到MAC地址为 {mac_addr} 的虚拟机")
        return api_response(404, f'未找到MAC地址为 {mac_addr} 的虚拟机')


# ============================================================================
# 虚拟机网络配置API - NAT端口转发
# ============================================================================

# 获取NAT规则 ########################################################################
def get_vm_nat_rules(hs_manage, hs_name, vm_uuid):
    """获取虚拟机NAT端口转发规则"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    vm_config = server.vm_saving.get(vm_uuid)
    if not vm_config:
        return api_response(404, '虚拟机不存在')

    # 从vm_config中获取NAT规则
    nat_rules = []
    if hasattr(vm_config, 'nat_all') and vm_config.nat_all:
        for idx, rule in enumerate(vm_config.nat_all):
            if hasattr(rule, '__dict__') and callable(rule.__dict__):
                nat_rules.append(rule.__dict__())
            elif isinstance(rule, dict):
                nat_rules.append(rule)
            else:
                nat_rules.append({
                    'protocol': getattr(rule, 'protocol', 'tcp'),
                    'external_port': getattr(rule, 'external_port', 0),
                    'internal_port': getattr(rule, 'internal_port', 0),
                    'internal_ip': getattr(rule, 'internal_ip', ''),
                    'description': getattr(rule, 'description', '')
                })

    return api_response(200, 'success', nat_rules)


# 添加NAT规则 ########################################################################
def add_vm_nat_rule(hs_manage, hs_name, vm_uuid):
    """添加虚拟机NAT端口转发规则"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    vm_config = server.vm_saving.get(vm_uuid)
    if not vm_config:
        return api_response(404, '虚拟机不存在')

    data = request.get_json() or {}

    # 创建NAT规则
    nat_rule = {
        'protocol': data.get('protocol', 'tcp'),
        'external_port': data.get('external_port', 0),
        'internal_port': data.get('internal_port', 0),
        'internal_ip': data.get('internal_ip', ''),
        'description': data.get('description', '')
    }

    # 添加到vm_config
    if not hasattr(vm_config, 'nat_all') or vm_config.nat_all is None:
        vm_config.nat_all = []
    vm_config.nat_all.append(nat_rule)

    hs_manage.all_save()
    return api_response(200, 'NAT规则添加成功')


# 删除NAT规则 ########################################################################
def delete_vm_nat_rule(hs_manage, hs_name, vm_uuid, rule_index):
    """删除虚拟机NAT端口转发规则"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    vm_config = server.vm_saving.get(vm_uuid)
    if not vm_config:
        return api_response(404, '虚拟机不存在')

    if not hasattr(vm_config, 'nat_all') or not vm_config.nat_all:
        return api_response(404, 'NAT规则不存在')

    if rule_index < 0 or rule_index >= len(vm_config.nat_all):
        return api_response(404, 'NAT规则索引无效')

    vm_config.nat_all.pop(rule_index)
    hs_manage.all_save()
    return api_response(200, 'NAT规则已删除')


# ============================================================================
# 虚拟机网络配置API - IP地址管理
# ============================================================================

# 获取IP列表 ########################################################################
def get_vm_ip_addresses(hs_manage, hs_name, vm_uuid):
    """获取虚拟机IP地址列表"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    vm_config = server.vm_saving.get(vm_uuid)
    if not vm_config:
        return api_response(404, '虚拟机不存在')

    # 从vm_config中获取IP地址列表
    ip_list = []
    if hasattr(vm_config, 'ip_all') and vm_config.ip_all:
        for ip in vm_config.ip_all:
            if hasattr(ip, '__dict__') and callable(ip.__dict__):
                ip_list.append(ip.__dict__())
            elif isinstance(ip, dict):
                ip_list.append(ip)
            else:
                ip_list.append({
                    'type': getattr(ip, 'type', 'ipv4'),
                    'address': getattr(ip, 'address', ''),
                    'netmask': getattr(ip, 'netmask', ''),
                    'gateway': getattr(ip, 'gateway', ''),
                    'nic': getattr(ip, 'nic', ''),
                    'description': getattr(ip, 'description', '')
                })

    return api_response(200, 'success', ip_list)


# 添加IP地址 ########################################################################
def add_vm_ip_address(hs_manage, hs_name, vm_uuid):
    """添加虚拟机IP地址"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    vm_config = server.vm_saving.get(vm_uuid)
    if not vm_config:
        return api_response(404, '虚拟机不存在')

    data = request.get_json() or {}

    # 创建IP地址配置
    ip_config = {
        'type': data.get('type', 'ipv4'),
        'address': data.get('address', ''),
        'netmask': data.get('netmask', ''),
        'gateway': data.get('gateway', ''),
        'nic': data.get('nic', ''),
        'description': data.get('description', '')
    }

    # 添加到vm_config
    if not hasattr(vm_config, 'ip_all') or vm_config.ip_all is None:
        vm_config.ip_all = []
    vm_config.ip_all.append(ip_config)

    hs_manage.all_save()
    return api_response(200, 'IP地址添加成功')


# 删除IP地址 ########################################################################
def delete_vm_ip_address(hs_manage, hs_name, vm_uuid, ip_index):
    """删除虚拟机IP地址"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    vm_config = server.vm_saving.get(vm_uuid)
    if not vm_config:
        return api_response(404, '虚拟机不存在')

    if not hasattr(vm_config, 'ip_all') or not vm_config.ip_all:
        return api_response(404, 'IP地址不存在')

    if ip_index < 0 or ip_index >= len(vm_config.ip_all):
        return api_response(404, 'IP地址索引无效')

    vm_config.ip_all.pop(ip_index)
    hs_manage.all_save()
    return api_response(200, 'IP地址已删除')


# ============================================================================
# 虚拟机网络配置API - 反向代理管理
# ============================================================================

# 获取代理配置 ########################################################################
def get_vm_proxy_configs(hs_manage, hs_name, vm_uuid):
    """获取虚拟机反向代理配置列表"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    vm_config = server.vm_saving.get(vm_uuid)
    if not vm_config:
        return api_response(404, '虚拟机不存在')

    # 从vm_config中获取代理配置列表
    proxy_list = []
    if hasattr(vm_config, 'proxy_all') and vm_config.proxy_all:
        for proxy in vm_config.proxy_all:
            if hasattr(proxy, '__dict__') and callable(proxy.__dict__):
                proxy_list.append(proxy.__dict__())
            elif isinstance(proxy, dict):
                proxy_list.append(proxy)
            else:
                proxy_list.append({
                    'domain': getattr(proxy, 'domain', ''),
                    'backend_ip': getattr(proxy, 'backend_ip', ''),
                    'backend_port': getattr(proxy, 'backend_port', 80),
                    'ssl_enabled': getattr(proxy, 'ssl_enabled', False),
                    'ssl_type': getattr(proxy, 'ssl_type', ''),
                    'description': getattr(proxy, 'description', '')
                })

    return api_response(200, 'success', proxy_list)


# 添加代理配置 ########################################################################
def add_vm_proxy_config(hs_manage, hs_name, vm_uuid):
    """添加虚拟机反向代理配置"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    vm_config = server.vm_saving.get(vm_uuid)
    if not vm_config:
        return api_response(404, '虚拟机不存在')

    data = request.get_json() or {}

    # 创建代理配置
    proxy_config = {
        'domain': data.get('domain', ''),
        'backend_ip': data.get('backend_ip', ''),
        'backend_port': data.get('backend_port', 80),
        'ssl_enabled': data.get('ssl_enabled', False),
        'ssl_type': data.get('ssl_type', ''),
        'ssl_cert': data.get('ssl_cert', ''),
        'ssl_key': data.get('ssl_key', ''),
        'description': data.get('description', '')
    }

    # 添加到vm_config
    if not hasattr(vm_config, 'proxy_all') or vm_config.proxy_all is None:
        vm_config.proxy_all = []
    vm_config.proxy_all.append(proxy_config)

    hs_manage.all_save()
    return api_response(200, '代理配置添加成功')


# 删除代理配置 ########################################################################
def delete_vm_proxy_config(hs_manage, hs_name, vm_uuid, proxy_index):
    """删除虚拟机反向代理配置"""
    server = hs_manage.get_host(hs_name)
    if not server:
        return api_response(404, '主机不存在')

    vm_config = server.vm_saving.get(vm_uuid)
    if not vm_config:
        return api_response(404, '虚拟机不存在')

    if not hasattr(vm_config, 'proxy_all') or not vm_config.proxy_all:
        return api_response(404, '代理配置不存在')

    if proxy_index < 0 or proxy_index >= len(vm_config.proxy_all):
        return api_response(404, '代理配置索引无效')

    vm_config.proxy_all.pop(proxy_index)
    hs_manage.all_save()
    return api_response(200, '代理配置已删除')
