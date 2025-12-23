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
from loguru import logger
import psutil

from MainObject.Config.HSConfig import HSConfig
from MainObject.Server.HSEngine import HEConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Config.NCConfig import NCConfig
from MainObject.Config.PortData import PortData
from MainObject.Config.WebProxy import WebProxy
from MainObject.Public.HWStatus import HWStatus


class RestManager:
    """REST API管理器 - 封装所有主机和虚拟机管理的API接口"""

    def __init__(self, hs_manage):
        """
        初始化RestManager
        
        Args:
            hs_manage: 主机管理对象，用于实际的主机和虚拟机操作
        """
        self.hs_manage = hs_manage

    # ========================================================================
    # 认证装饰器和响应函数
    # ========================================================================

    @staticmethod
    # 认证装饰器，检查Bearer Token或Session登录 ########################################
    # :param f: 被装饰的函数
    # :return: 装饰后的函数
    # ####################################################################################
    def require_auth(self, f):

        @wraps(f)
        def decorated(*args, **kwargs):
            # 检查Bearer Token
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                if token and token == self.hs_manage.bearer:
                    return f(*args, **kwargs)
            # 检查Session登录
            if session.get('logged_in'):
                return f(*args, **kwargs)
            # API请求返回JSON错误
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'code': 401, 'msg': '未授权访问', 'data': None}), 401
            # 页面请求重定向到登录页
            return redirect(url_for('login'))

        return decorated

    # 统一API响应格式 ####################################################################
    # :param code: 响应状态码，默认为200
    # :param msg: 响应消息，默认为'success'
    # :param data: 响应数据，默认为None
    # :return: JSON格式的响应对象
    # ####################################################################################
    def api_response(self, code=200, msg='success', data=None):
        """统一API响应格式"""
        return jsonify({'code': code, 'msg': msg, 'data': data})

    # ========================================================================
    # 系统管理API - /api/system/<option>
    # ========================================================================

    # 重置访问令牌 ########################################################################
    # :return: 包含新token的API响应
    # ####################################################################################
    def reset_token(self):
        """重置访问Token"""
        new_token = self.hs_manage.set_pass()
        return self.api_response(200, 'Token已重置', {'token': new_token})

    # 设置访问令牌 ########################################################################
    # :return: 包含设置token的API响应
    # ####################################################################################
    def set_token(self):
        """设置指定Token"""
        data = request.get_json() or {}
        new_token = data.get('token', '')
        result = self.hs_manage.set_pass(new_token)
        return self.api_response(200, 'Token已设置', {'token': result})

    # 获取访问令牌 ########################################################################
    # :return: 包含当前token的API响应
    # ####################################################################################
    def get_token(self):
        """获取当前Token"""
        return self.api_response(200, 'success', {'token': self.hs_manage.bearer})

    # 获取引擎类型 ########################################################################
    # :return: 包含支持的主机引擎类型列表的API响应
    # ####################################################################################
    def get_engine_types(self):
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
        return self.api_response(200, 'success', types_data)

    # 保存系统配置 ########################################################################
    # :return: 保存结果的API响应
    # ####################################################################################
    def save_system(self):
        """保存系统配置"""
        if self.hs_manage.all_save():
            return self.api_response(200, '配置已保存')
        return self.api_response(500, '保存失败')

    # 加载系统配置 ########################################################################
    # :return: 加载结果的API响应
    # ####################################################################################
    def load_system(self):
        """加载系统配置"""
        try:
            self.hs_manage.all_load()
            return self.api_response(200, '配置已加载')
        except Exception as e:
            return self.api_response(500, f'加载失败: {str(e)}')

    # 获取系统统计 ########################################################################
    # :return: 包含系统统计信息的API响应
    # ####################################################################################
    def get_system_stats(self):
        """获取系统统计信息"""
        total_vms = 0
        running_vms = 0

        for server in self.hs_manage.engine.values():
            total_vms += len(server.vm_saving)
            # 统计运行中的虚拟机数量（根据实际状态判断）

        return self.api_response(200, 'success', {
            'host_count': len(self.hs_manage.engine),
            'vm_count': total_vms,
            'running_vm_count': running_vms
        })

    # 获取日志记录 ########################################################################
    # :return: 包含日志记录列表的API响应
    # ####################################################################################
    def get_logs(self):
        """获取日志记录"""
        try:
            hs_name = request.args.get('hs_name')
            limit = int(request.args.get('limit', 100))

            # 使用 DataManage 的 get_hs_logger 函数获取日志
            logs = self.hs_manage.saving.get_hs_logger(hs_name)

            # 处理日志数据并限制数量
            processed_logs = []
            for log_data in logs[:limit]:
                processed_log = {
                    'id': '',  # 可以添加rowid但暂时为空
                    'actions': log_data.get('actions', ''),
                    'message': log_data.get('message', '无消息内容'),
                    'success': log_data.get('success', True),
                    'results': log_data.get('results', {}),
                    'execute': log_data.get('execute', None),
                    'level': log_data.get('level', 'ERROR' if not log_data.get('success', True) else 'INFO'),
                    'timestamp': log_data.get('created_at'),
                    'host': hs_name or '系统',
                    'created_at': log_data.get('created_at')
                }
                processed_logs.append(processed_log)

            return self.api_response(200, '获取日志成功', processed_logs)
        except Exception as e:
            return self.api_response(500, f'获取日志失败: {str(e)}')

    # 获取任务记录 ########################################################################
    # :return: 包含任务记录列表的API响应
    # ####################################################################################
    def get_tasks(self):
        """获取任务记录"""
        try:
            hs_name = request.args.get('hs_name')
            limit = int(request.args.get('limit', 100))

            if not hs_name:
                return self.api_response(400, '主机名称不能为空')

            # 使用 DataManage 的 get_vm_tasker 函数获取任务
            tasks = self.hs_manage.saving.get_vm_tasker(hs_name)

            # 限制数量并返回
            limited_tasks = tasks[:limit]
            return self.api_response(200, '获取任务成功', limited_tasks)
        except Exception as e:
            return self.api_response(500, f'获取任务失败: {str(e)}')

    # ========================================================================
    # 主机管理API - /api/server/<option>/<key?>
    # ========================================================================

    # 获取主机列表 ########################################################################
    # :return: 包含所有主机信息的API响应
    # ####################################################################################
    def get_hosts(self):
        """获取所有主机列表"""
        hosts_data = {}
        for hs_name, server in self.hs_manage.engine.items():
            hosts_data[hs_name] = {
                'name': hs_name,
                'type': server.hs_config.server_type if server.hs_config else '',
                'addr': server.hs_config.server_addr if server.hs_config else '',
                'config': server.hs_config.__save__() if server.hs_config else {},
                'vm_count': len(server.vm_saving),
                'status': 'active'  # 可以根据实际情况判断
            }
        return self.api_response(200, 'success', hosts_data)

    # 获取主机详情 ########################################################################
    # :param hs_name: 主机名称
    # :return: 包含单个主机详细信息的API响应
    # ####################################################################################
    def get_host(self, hs_name):
        """获取单个主机详情"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        # 检查是否需要详细信息（通过查询参数控制）
        include_status = request.args.get('status', 'false').lower() == 'true'

        # 构建基础响应数据（快速获取）
        host_data = {
            'name': hs_name,
            'type': server.hs_config.server_type if server.hs_config else '',
            'addr': server.hs_config.server_addr if server.hs_config else '',
            'config': server.hs_config.__save__() if server.hs_config else {},
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
                        host_data['status'] = status_obj.__save__()
                        host_data['status_source'] = 'fresh'
                        # 缓存状态数据
                        server._status_cache = status_obj.__save__()
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

        return self.api_response(200, 'success', host_data)

    # 添加主机 ########################################################################
    # :return: 主机添加结果的API响应
    # ####################################################################################
    def add_host(self):
        """添加主机"""
        data = request.get_json() or {}
        hs_name = data.get('name', '')
        hs_type = data.get('type', '')

        if not hs_name or not hs_type:
            return self.api_response(400, '主机名称和类型不能为空')

        # 构建配置
        config_data = data.get('config', {})
        config_data['server_type'] = hs_type
        
        # 调试日志：打印images_maps
        logger.debug(f"[add_host] 接收到的config_data.images_maps: {config_data.get('images_maps')}")
        logger.debug(f"[add_host] images_maps类型: {type(config_data.get('images_maps'))}")
        
        hs_conf = HSConfig(**config_data)
        hs_conf.server_name = hs_name  # 设置server_name，确保save_data能正常工作
        
        # 调试日志：打印HSConfig对象的images_maps
        logger.debug(f"[add_host] HSConfig.images_maps: {hs_conf.images_maps}")
        logger.debug(f"[add_host] HSConfig.images_maps类型: {type(hs_conf.images_maps)}")

        result = self.hs_manage.add_host(hs_name, hs_type, hs_conf)

        if result.success:
            self.hs_manage.all_save()
            return self.api_response(200, result.message)
        return self.api_response(400, result.message)

    # 修改主机配置 ########################################################################
    # :param hs_name: 主机名称
    # :return: 主机配置修改结果的API响应
    # ####################################################################################
    def update_host(self, hs_name):
        """修改主机配置"""
        data = request.get_json() or {}
        config_data = data.get('config', {})

        if not config_data:
            return self.api_response(400, '配置不能为空')

        hs_conf = HSConfig(**config_data)
        result = self.hs_manage.set_host(hs_name, hs_conf)

        if result.success:
            self.hs_manage.all_save()
            return self.api_response(200, result.message)
        return self.api_response(400, result.message)

    # 删除主机 ########################################################################
    # :param hs_name: 主机名称
    # :return: 主机删除结果的API响应
    # ####################################################################################
    def delete_host(self, hs_name):
        """删除主机"""
        if self.hs_manage.del_host(hs_name):
            self.hs_manage.all_save()
            return self.api_response(200, '主机已删除')
        return self.api_response(404, '主机不存在')

    # 主机电源控制 ########################################################################
    # :param hs_name: 主机名称
    # :return: 主机电源控制结果的API响应
    # ####################################################################################
    def host_power(self, hs_name):
        """主机电源控制（启用/禁用）"""
        data = request.get_json() or {}
        enable = data.get('enable', True)

        result = self.hs_manage.pwr_host(hs_name, enable)

        if result.success:
            self.hs_manage.all_save()
            return self.api_response(200, result.message)
        return self.api_response(400, result.message)

    # 获取主机状态 ########################################################################
    # :param hs_name: 主机名称
    # :return: 包含主机状态的API响应
    # ####################################################################################
    def get_host_status(self, hs_name):
        """获取主机状态"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        # 检查是否强制刷新缓存
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'

        import time
        current_time = int(time.time())
        cache_time = getattr(server, '_status_cache_time', 0)
        cached_status = getattr(server, '_status_cache', None)

        # 检查缓存是否有效（60秒内的数据认为是新鲜的）
        if not force_refresh and cached_status and (current_time - cache_time) < 60:
            return self.api_response(200, 'success', {
                'status': cached_status,
                'source': 'cached',
                'cached_at': cache_time,
                'age_seconds': current_time - cache_time
            })

        # 获取新状态
        try:
            status = server.HSStatus()
            if status:
                status_data = status.__save__()
                # 更新缓存
                server._status_cache = status_data
                server._status_cache_time = current_time

                return self.api_response(200, 'success', {
                    'status': status_data,
                    'source': 'fresh' if force_refresh else 'auto_refreshed',
                    'cached_at': current_time,
                    'cache_duration': 60
                })
            else:
                return self.api_response(500, 'failed', {
                    'message': '无法获取主机状态',
                    'source': 'error'
                })
        except Exception as e:
            return self.api_response(500, 'failed', {
                'message': f'获取主机状态时出错: {str(e)}',
                'source': 'error'
            })

    # ========================================================================
    # 虚拟机管理API - /api/client/<option>/<key?>
    # ========================================================================

    # 获取虚拟机列表 ########################################################################
    # :param hs_name: 主机名称
    # :return: 包含主机下所有虚拟机信息的API响应
    # ####################################################################################
    def get_vms(self, hs_name):
        """获取主机下所有虚拟机"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

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
            # 尝试调用__save__()方法
            if hasattr(obj, '__save__') and callable(obj.__save__):
                try:
                    return obj.__save__()
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

        return self.api_response(200, 'success', vms_data)

    # 获取虚拟机详情 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 包含单个虚拟机详细信息的API响应
    # ####################################################################################
    def get_vm(self, hs_name, vm_uuid):
        """获取单个虚拟机详情"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        status_dict = server.VMStatus(vm_uuid)
        # VMStatus返回dict[str, list[HWStatus]]，需要将每个HWStatus对象转换为字典
        status_result = []
        if status_dict and vm_uuid in status_dict:
            status_list = status_dict[vm_uuid]
            for hw_status in status_list:
                if hw_status is not None:
                    # 如果已经是字典则直接使用，否则调用__save__()方法
                    if isinstance(hw_status, dict):
                        status_result.append(hw_status)
                    elif hasattr(hw_status, '__save__') and callable(getattr(hw_status, '__save__', None)):
                        status_result.append(hw_status.__save__())
                    else:
                        status_result.append(hw_status)
                else:
                    status_result.append(None)

        # 如果vm_config已经是字典则直接使用，否则调用__save__()方法
        if isinstance(vm_config, dict):
            config_data = vm_config
        elif hasattr(vm_config, '__save__') and callable(getattr(vm_config, '__save__', None)):
            config_data = vm_config.__save__()
        else:
            config_data = vm_config if vm_config else {}

        return self.api_response(200, 'success', {
            'uuid': vm_uuid,
            'config': config_data,
            'status': status_result
        })

    # 创建虚拟机 ########################################################################
    # :param hs_name: 主机名称
    # :return: 虚拟机创建结果的API响应
    # ####################################################################################
    def create_vm(self, hs_name):
        """创建虚拟机"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        data = request.get_json() or {}
        # 处理网卡配置
        nic_all = {}
        nic_data = data.pop('nic_all', {})
        for nic_name, nic_conf in nic_data.items():
            nic_all[nic_name] = NCConfig(**nic_conf)
        # 创建虚拟机配置
        vm_config = VMConfig(**data, nic_all=nic_all)
        vm_config.vc_port = random.randint(10000, 59999)
        if vm_config.vc_pass == '':
            vm_config.vc_pass = ''.join(
                random.sample(string.ascii_letters + string.digits, 8))
        result = server.VMCreate(vm_config)
        self.hs_manage.all_save()
        return self.api_response(200 if result and result.success else 400, result.message)

    # 修改虚拟机配置 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 虚拟机配置修改结果的API响应
    # ####################################################################################
    def update_vm(self, hs_name, vm_uuid):
        """修改虚拟机配置"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

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
            self.hs_manage.all_save()
            return self.api_response(200, result.message if result.message else '虚拟机更新成功')

        return self.api_response(400, result.message if result else '更新失败')

    # 删除虚拟机 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 虚拟机删除结果的API响应
    # ####################################################################################
    def delete_vm(self, hs_name, vm_uuid):
        """删除虚拟机"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        result = server.VMDelete(vm_uuid)

        if result and result.success:
            self.hs_manage.all_save()
            return self.api_response(200, result.message if result.message else '虚拟机已删除')

        return self.api_response(400, result.message if result else '操作失败')

    # 虚拟机密码修改 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 虚拟机密码修改结果的API响应
    # ####################################################################################
    def vm_password(self, hs_name, vm_uuid):
        """修改虚拟机密码"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        data = request.get_json() or {}
        new_password = data.get('password', '').strip()

        # 验证新密码是否提供
        if not new_password:
            return self.api_response(400, '新密码不能为空')
        # vm_conf = server.VMSelect(vm_uuid)
        # if not vm_conf:
        #     return self.api_response(404, '虚拟机不存在')
        result = server.Password(vm_uuid, new_password)
        if result and result.success:
            self.hs_manage.all_save()
            return self.api_response(200, result.message if result.message else '密码修改成功')

        return self.api_response(400, result.message if result else '密码修改失败')

    # 虚拟机控制台 ######################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 虚拟机电源控制结果的API响应
    # ####################################################################################
    def vm_power(self, hs_name, vm_uuid):
        """虚拟机电源控制"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

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
            return self.api_response(400, f'不支持的操作: {action}')

        result = server.VMPowers(vm_uuid, power_action)

        if result and result.success:
            return self.api_response(200, result.message if result.message else f'电源操作 {action} 成功')

        return self.api_response(400, result.message if result else '操作失败')

    # 获取虚拟机VNC控制台URL ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 包含VNC控制台URL的API响应
    # ####################################################################################
    def vm_console(self, hs_name, vm_uuid):
        """获取虚拟机VNC控制台URL"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')
        try:
            console_url = server.VCRemote(vm_uuid)
            logger.info(f"[VNC控制台地址] {console_url}")
            if console_url:
                return self.api_response(200, '获取成功', console_url)
            return self.api_response(400, '无法获取VNC控制台地址')
        except Exception as e:
            traceback.print_exc()
            return self.api_response(500, f'获取VNC控制台失败: {str(e)}')

    # 获取虚拟机状态 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 包含虚拟机状态的API响应
    # ####################################################################################
    def get_vm_status(self, hs_name, vm_uuid):
        """获取虚拟机状态"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        status_dict = server.VMStatus(vm_uuid)
        # VMStatus返回dict[str, list[HWStatus]]，需要将每个HWStatus对象转换为字典
        if vm_uuid not in status_dict:
            return self.api_response(404, '虚拟机不存在')

        # 处理HWStatus列表
        status_list = status_dict[vm_uuid]
        result = []
        if status_list:
            for hw_status in status_list:
                if hw_status is not None:
                    try:
                        result.append(hw_status.__save__())
                    except (TypeError, AttributeError):
                        result.append(vars(hw_status))
                else:
                    result.append(None)
        return self.api_response(200, 'success', result)

    # 扫描主机上的虚拟机 ########################################################################
    # :param hs_name: 主机名称
    # :return: 虚拟机扫描结果的API响应
    # ####################################################################################
    def scan_vms(self, hs_name):
        """扫描主机上的虚拟机"""
        server = self.hs_manage.get_host(hs_name)
        if server:
            # 扫描前先从数据库重新加载数据
            server.data_get()

        data = request.get_json() or {}
        prefix = data.get('prefix', '')  # 前缀过滤，为空则使用主机配置的filter_name

        result = self.hs_manage.vms_scan(hs_name, prefix)

        if result.success:
            # 保存系统配置
            self.hs_manage.all_save()
            return self.api_response(200, result.message, result.results)

        return self.api_response(400, result.message)

    # 虚拟机上报状态数据 ########################################################################
    # :return: 虚拟机状态上报结果的API响应（无需认证）
    # ####################################################################################
    def vm_upload(self):
        """虚拟机上报状态数据（无需认证）"""
        # 获取MAC地址参数
        mac_addr = request.args.get('nic', '')
        if not mac_addr:
            return self.api_response(400, 'MAC地址参数缺失')

        # 获取上报的状态数据
        status_data = request.get_json() or {}
        if not status_data:
            return self.api_response(400, '状态数据为空')

        logger.info(f"[虚拟机上报] 收到MAC地址: {mac_addr}")

        # 遍历所有主机，查找匹配MAC地址的虚拟机
        found = False
        for hs_name, server in self.hs_manage.engine.items():
            if not server:
                continue

            # 从数据库重新加载虚拟机配置
            try:
                server.data_get()
                logger.info(f"[虚拟机上报] 主机 {hs_name} 已加载 {len(server.vm_saving)} 个虚拟机配置")
            except Exception as e:
                logger.error(f"[虚拟机上报] 主机 {hs_name} 加载配置失败: {e}")
                continue

            # 遍历该主机下的所有虚拟机配置
            for vm_uuid, vm_config in server.vm_saving.items():
                # 处理vm_config可能是字典或VMConfig对象的情况
                nic_all = vm_config.nic_all if hasattr(vm_config, 'nic_all') else vm_config.get('nic_all', {})

                logger.debug(f"[虚拟机上报] 检查虚拟机 {vm_uuid}, 网卡数量: {len(nic_all)}")

                # 检查虚拟机的网卡配置
                for nic_name, nic_config in nic_all.items():
                    # 处理nic_config可能是字典或NCConfig对象的情况
                    nic_mac = nic_config.mac_addr if hasattr(nic_config, 'mac_addr') else nic_config.get('mac_addr', '')

                    logger.debug(f"[虚拟机上报] 网卡 {nic_name} MAC: {nic_mac} vs 上报MAC: {mac_addr}")

                    if nic_mac.lower() == mac_addr.lower():
                        # 找到匹配的虚拟机，创建HWStatus对象
                        logger.info(f"[虚拟机上报] 找到匹配的虚拟机! 主机: {hs_name}, UUID: {vm_uuid}")
                        logger.debug(f"[虚拟机上报] 状态数据: {status_data}")
                        try:
                            hw_status = HWStatus(**status_data)
                            logger.debug(f"[虚拟机上报] HWStatus对象创建成功: {hw_status}")

                            # 直接使用 DataManage 保存状态（立即写入数据库）=================
                            if server.save_data and server.hs_config.server_name:
                                logger.debug(f"[虚拟机上报] 开始调用 DataManage.add_vm_status")
                                result = server.save_data.add_vm_status(server.hs_config.server_name, vm_uuid,
                                                                        hw_status)
                                logger.debug(f"[虚拟机上报] add_vm_status 返回结果: {result}")
                                if result:
                                    logger.success(f"[虚拟机上报] 状态已成功保存到数据库")
                                else:
                                    logger.warning(f"[虚拟机上报] 状态保存失败")
                            else:
                                logger.warning(
                                    f"[虚拟机上报] 警告: 数据库未初始化，save_data={server.save_data}, server_name={server.hs_config.server_name if server.hs_config else 'None'}")

                            found = True
                            # 获取虚拟机密码
                            vm_pass = vm_config.os_pass
                            return self.api_response(200, f'虚拟机 {vm_uuid} 状态已更新', {
                                'hs_name': hs_name,
                                'vm_uuid': vm_uuid,
                                'vm_pass': vm_pass
                            })
                        except Exception as e:
                            logger.error(f"[虚拟机上报] 状态数据处理失败: {e}")
                            return self.api_response(500, f'状态数据处理失败: {str(e)}')

        if not found:
            logger.warning(f"[虚拟机上报] 未找到MAC地址为 {mac_addr} 的虚拟机")
            return self.api_response(404, f'未找到MAC地址为 {mac_addr} 的虚拟机')

    # ========================================================================
    # 虚拟机网络配置API - NAT端口转发
    # ========================================================================

    # 获取虚拟机NAT端口转发规则 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 包含NAT规则列表的API响应
    # ####################################################################################
    def get_vm_nat_rules(self, hs_name, vm_uuid):
        """获取虚拟机NAT端口转发规则"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        # 从vm_config中获取NAT规则
        nat_rules = []
        if hasattr(vm_config, 'nat_all') and vm_config.nat_all:
            for idx, rule in enumerate(vm_config.nat_all):
                if hasattr(rule, '__save__') and callable(rule.__save__):
                    nat_rules.append(rule.__save__())
                elif isinstance(rule, dict):
                    nat_rules.append(rule)
                else:
                    # 兼容旧格式
                    nat_rules.append({
                        'lan_port': getattr(rule, 'lan_port', 0),
                        'wan_port': getattr(rule, 'wan_port', 0),
                        'lan_addr': getattr(rule, 'lan_addr', ''),
                        'nat_tips': getattr(rule, 'nat_tips', '')
                    })

        return self.api_response(200, 'success', nat_rules)

    # 添加虚拟机NAT端口转发规则 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: NAT规则添加结果的API响应
    # ####################################################################################
    def add_vm_nat_rule(self, hs_name, vm_uuid):
        """添加虚拟机NAT端口转发规则"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}

        # 创建PortData对象
        port_data = PortData()
        port_data.lan_port = data.get('lan_port', 0)
        port_data.wan_port = data.get('wan_port', 0)
        port_data.lan_addr = data.get('lan_addr', '')
        port_data.nat_tips = data.get('nat_tips', '')

        # 添加到vm_config
        if not hasattr(vm_config, 'nat_all') or vm_config.nat_all is None:
            vm_config.nat_all = []
        vm_config.nat_all.append(port_data)

        # 调用PortsMap创建端口映射
        try:
            result = server.PortsMap(map_info=port_data, flag=True)
            if not result.success:
                # 如果创建失败，从列表中移除
                vm_config.nat_all.pop()
                return self.api_response(500, f'端口映射创建失败: {result.message}')
        except Exception as e:
            # 如果创建失败，从列表中移除
            vm_config.nat_all.pop()
            logger.error(f"创建端口映射失败: {e}")
            return self.api_response(500, f'端口映射创建失败: {str(e)}')

        self.hs_manage.all_save()
        return self.api_response(200, 'NAT规则添加成功')

    # 删除虚拟机NAT端口转发规则 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :param rule_index: NAT规则索引
    # :return: NAT规则删除结果的API响应
    # ####################################################################################
    def delete_vm_nat_rule(self, hs_name, vm_uuid, rule_index):
        """删除虚拟机NAT端口转发规则"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        if not hasattr(vm_config, 'nat_all') or not vm_config.nat_all:
            return self.api_response(404, 'NAT规则不存在')

        if rule_index < 0 or rule_index >= len(vm_config.nat_all):
            return self.api_response(404, 'NAT规则索引无效')

        # 获取要删除的端口映射信息
        port_data = vm_config.nat_all[rule_index]
        
        # 调用PortsMap删除端口映射
        try:
            if hasattr(port_data, 'lan_addr') and hasattr(port_data, 'lan_port') and hasattr(port_data, 'wan_port'):
                result = server.PortsMap(map_info=port_data, flag=False)
                if not result.success:
                    logger.warning(f'端口映射删除失败: {result.message}')
        except Exception as e:
            logger.error(f"删除端口映射失败: {e}")

        # 从列表中移除
        vm_config.nat_all.pop(rule_index)
        self.hs_manage.all_save()
        return self.api_response(200, 'NAT规则已删除')

    # ========================================================================
    # 虚拟机网络配置API - IP地址管理
    # ========================================================================

    # 获取虚拟机IP地址列表 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 包含IP地址列表的API响应
    # ####################################################################################
    def get_vm_ip_addresses(self, hs_name, vm_uuid):
        """获取虚拟机网卡列表（IP地址管理）"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        # 从vm_config.nic_all中获取网卡列表
        nic_list = []
        if hasattr(vm_config, 'nic_all') and vm_config.nic_all:
            for nic_name, nic_config in vm_config.nic_all.items():
                nic_info = {
                    'nic_name': nic_name,
                    'mac_addr': nic_config.mac_addr if hasattr(nic_config, 'mac_addr') else '',
                    'ip4_addr': nic_config.ip4_addr if hasattr(nic_config, 'ip4_addr') else '',
                    'ip6_addr': nic_config.ip6_addr if hasattr(nic_config, 'ip6_addr') else '',
                    'nic_gate': nic_config.nic_gate if hasattr(nic_config, 'nic_gate') else '',
                    'nic_mask': nic_config.nic_mask if hasattr(nic_config, 'nic_mask') else '255.255.255.0',
                    'nic_type': nic_config.nic_type if hasattr(nic_config, 'nic_type') else '',
                    'dns_addr': nic_config.dns_addr if hasattr(nic_config, 'dns_addr') else []
                }
                nic_list.append(nic_info)

        return self.api_response(200, 'success', nic_list)

    # 添加虚拟机IP地址 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: IP地址添加结果的API响应
    # ####################################################################################
    def add_vm_ip_address(self, hs_name, vm_uuid):
        """添加虚拟机网卡（新增网卡）"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}

        # 从数据库读取vm_conf
        server.data_get()
        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        # 拷贝并修改vm_conf
        vm_config_dict = vm_config.__save__()
        old_vm_config = VMConfig(**vm_config_dict)

        # 生成新的网卡名称
        nic_index = len(vm_config.nic_all)
        nic_name = f"nic{nic_index}"
        while nic_name in vm_config.nic_all:
            nic_index += 1
            nic_name = f"nic{nic_index}"

        # 创建网卡配置
        nic_config = NCConfig(
            nic_type=data.get('nic_type', 'nat'),
            ip4_addr=data.get('ip4_addr', ''),
            ip6_addr=data.get('ip6_addr', ''),
            nic_gate=data.get('nic_gate', ''),
            nic_mask=data.get('nic_mask', '255.255.255.0'),
            dns_addr=data.get('dns_addr', server.hs_config.ipaddr_dnss if hasattr(server.hs_config, 'ipaddr_dnss') else [])
        )

        # 如果没有填写IP地址，则自动分配
        if not nic_config.ip4_addr or nic_config.ip4_addr.strip() == '':
            # 调用NetCheck自动分配IP
            vm_config.nic_all[nic_name] = nic_config
            vm_config, net_result = server.NetCheck(vm_config)
            if not net_result.success:
                return self.api_response(400, f'自动分配IP失败: {net_result.message}')
        else:
            # 手动指定IP，生成MAC地址
            vm_config.nic_all[nic_name] = nic_config
            nic_config.mac_addr = nic_config.send_mac()

        # 执行NCCreate绑定静态IP
        nc_result = server.NCCreate(vm_config, True)
        if not nc_result.success:
            return self.api_response(400, f'绑定静态IP失败: {nc_result.message}')

        # 调用VMUpdate更新
        result = server.VMUpdate(vm_config, old_vm_config)
        
        if result and result.success:
            self.hs_manage.all_save()
            return self.api_response(200, f'网卡 {nic_name} 添加成功')
        
        return self.api_response(400, result.message if result else '添加网卡失败')

    # 删除虚拟机IP地址 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :param ip_index: IP地址索引
    # :return: IP地址删除结果的API响应
    # ####################################################################################
    def delete_vm_ip_address(self, hs_name, vm_uuid, nic_name):
        """删除虚拟机网卡"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        if not hasattr(vm_config, 'nic_all') or not vm_config.nic_all:
            return self.api_response(404, '网卡列表为空')

        if nic_name not in vm_config.nic_all:
            return self.api_response(404, f'网卡 {nic_name} 不存在')

        # 从数据库读取vm_conf
        server.data_get()
        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        # 拷贝并修改vm_conf
        vm_config_dict = vm_config.__save__()
        old_vm_config = VMConfig(**vm_config_dict)
        
        # 删除网卡
        del vm_config.nic_all[nic_name]
        
        # 调用VMUpdate更新
        result = server.VMUpdate(vm_config, old_vm_config)
        
        if result and result.success:
            # 确保数据保存成功
            save_success = self.hs_manage.all_save()
            if not save_success:
                logger.warning(f"删除网卡 {nic_name} 后保存数据失败")
            return self.api_response(200, f'网卡 {nic_name} 已删除')
        
        return self.api_response(400, result.message if result else '删除网卡失败')

    # 修改虚拟机网卡配置 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :param nic_name: 网卡名称
    # :return: 网卡修改结果的API响应
    # ####################################################################################
    def update_vm_ip_address(self, hs_name, vm_uuid, nic_name):
        """修改虚拟机网卡配置"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        if not hasattr(vm_config, 'nic_all') or not vm_config.nic_all:
            return self.api_response(404, '网卡列表为空')

        if nic_name not in vm_config.nic_all:
            return self.api_response(404, f'网卡 {nic_name} 不存在')

        data = request.get_json() or {}

        # 从数据库读取vm_conf
        server.data_get()
        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        # 拷贝并修改vm_conf
        vm_config_dict = vm_config.__save__()
        old_vm_config = VMConfig(**vm_config_dict)

        # 获取要修改的网卡
        nic_config = vm_config.nic_all[nic_name]

        # 更新网卡配置
        if 'ip4_addr' in data:
            nic_config.ip4_addr = data['ip4_addr']
        if 'ip6_addr' in data:
            nic_config.ip6_addr = data['ip6_addr']
        if 'nic_gate' in data:
            nic_config.nic_gate = data['nic_gate']
        if 'nic_mask' in data:
            nic_config.nic_mask = data['nic_mask']
        if 'nic_type' in data:
            nic_config.nic_type = data['nic_type']
        if 'dns_addr' in data:
            nic_config.dns_addr = data['dns_addr']

        # 如果修改了IP地址，需要重新生成MAC地址
        if 'ip4_addr' in data or 'ip6_addr' in data:
            nic_config.mac_addr = nic_config.send_mac()

        # 调用VMUpdate更新
        result = server.VMUpdate(vm_config, old_vm_config)
        
        if result and result.success:
            self.hs_manage.all_save()
            return self.api_response(200, f'网卡 {nic_name} 配置已更新')
        
        return self.api_response(400, result.message if result else '修改网卡失败')

    # ========================================================================
    # 虚拟机网络配置API - 反向代理管理
    # ========================================================================

    # 获取虚拟机反向代理配置列表 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 包含反向代理配置列表的API响应
    # ####################################################################################
    def get_vm_proxy_configs(self, hs_name, vm_uuid):
        """获取虚拟机反向代理配置列表"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        # 从vm_config.web_all中获取代理配置列表
        proxy_list = []
        if hasattr(vm_config, 'web_all') and vm_config.web_all:
            for proxy in vm_config.web_all:
                # 将WebProxy对象的字段映射为前端期望的格式
                proxy_dict = {
                    'domain': getattr(proxy, 'web_addr', ''),
                    'backend_ip': getattr(proxy, 'lan_addr', ''),
                    'backend_port': getattr(proxy, 'lan_port', 80),
                    'ssl_enabled': getattr(proxy, 'is_https', False),
                    'description': getattr(proxy, 'web_tips', '')
                }
                proxy_list.append(proxy_dict)

        return self.api_response(200, 'success', proxy_list)

    # 添加虚拟机反向代理配置 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: 反向代理配置添加结果的API响应
    # ####################################################################################
    def add_vm_proxy_config(self, hs_name, vm_uuid):
        """添加虚拟机反向代理配置"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}

        # 创建WebProxy对象
        proxy_config = WebProxy()
        proxy_config.web_addr = data.get('domain', '')
        proxy_config.lan_addr = data.get('backend_ip', '')
        proxy_config.lan_port = int(data.get('backend_port', 80))
        proxy_config.is_https = data.get('ssl_enabled', False)
        proxy_config.web_tips = data.get('description', '')

        # 初始化web_all列表
        if not hasattr(vm_config, 'web_all') or vm_config.web_all is None:
            vm_config.web_all = []

        # 检查域名是否已存在
        for proxy in vm_config.web_all:
            if proxy.web_addr == proxy_config.web_addr:
                return self.api_response(400, f'域名 {proxy_config.web_addr} 已存在')

        # 调用ProxyMap添加代理
        result = server.ProxyMap(proxy_config, self.hs_manage.proxys, flag=True)

        if not result.success:
            return self.api_response(500, f'添加代理失败: {result.messages}')

        # 添加到vm_config.web_all
        vm_config.web_all.append(proxy_config)

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, '代理配置添加成功')

    # 删除虚拟机反向代理配置 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :param proxy_index: 反向代理配置索引
    # :return: 反向代理配置删除结果的API响应
    # ####################################################################################
    def delete_vm_proxy_config(self, hs_name, vm_uuid, proxy_index):
        """删除虚拟机反向代理配置"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        if not hasattr(vm_config, 'web_all') or not vm_config.web_all:
            return self.api_response(404, '代理配置不存在')

        if proxy_index < 0 or proxy_index >= len(vm_config.web_all):
            return self.api_response(404, '代理配置索引无效')

        # 获取要删除的代理配置
        proxy_config = vm_config.web_all[proxy_index]

        # 调用ProxyMap删除代理
        result = server.ProxyMap(proxy_config, self.hs_manage.proxys, flag=False)
        if not result.success:
            return self.api_response(500, f'删除代理失败: {result.message}')

        # 从web_all中删除
        vm_config.web_all.pop(proxy_index)

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, '代理配置已删除')

    # ========================================================================
    # 数据盘管理API - /api/client/hdd/<action>/<hs_name>/<vm_uuid>
    # ========================================================================

    # 挂载数据盘 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: API响应
    # ####################################################################################
    def mount_vm_hdd(self, hs_name, vm_uuid):
        """挂载数据盘到虚拟机"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}
        hdd_name = data.get('hdd_name', '')
        hdd_size = data.get('hdd_size', 0)
        hdd_type = data.get('hdd_type', 0)

        if not hdd_name:
            return self.api_response(400, '磁盘名称不能为空')
        
        # 验证磁盘名称：只能包含数字、字母和下划线
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', hdd_name):
            return self.api_response(400, '磁盘名称只能包含数字、字母和下划线，不能包含特殊符号和中文')

        # 检查磁盘是否已存在
        hdd_config = None
        if hdd_name in vm_config.hdd_all:
            # 磁盘已存在，检查挂载状态
            existing_hdd = vm_config.hdd_all[hdd_name]
            hdd_flag = getattr(existing_hdd, 'hdd_flag', 0)
            
            if hdd_flag == 1:
                # 已挂载，不允许重复挂载
                return self.api_response(400, '磁盘已挂载，无需重复挂载')
            
            # 未挂载（hdd_flag=0），使用已有配置进行挂载
            hdd_config = existing_hdd
            logger.info(f"挂载已存在的未挂载磁盘: {hdd_name}")
        else:
            # 磁盘不存在，创建新磁盘
            if hdd_size < 1024:
                return self.api_response(400, '磁盘大小至少为1024MB')
            
            # 创建SDConfig对象
            from MainObject.Config.SDConfig import SDConfig
            hdd_config = SDConfig(hdd_name=hdd_name, hdd_size=hdd_size, hdd_type=hdd_type)
            logger.info(f"创建新磁盘: {hdd_name}, 大小: {hdd_size}MB, 类型: {hdd_type}")

        # 调用HDDMount挂载
        result = server.HDDMount(vm_uuid, hdd_config, in_flag=True)
        if not result.success:
            return self.api_response(500, f'挂载失败: {result.message}')

        # 如果是新磁盘，添加到vm_config.hdd_all
        if hdd_name not in vm_config.hdd_all:
            vm_config.hdd_all[hdd_name] = hdd_config

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, '数据盘挂载成功')

    # 卸载数据盘 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: API响应
    # ####################################################################################
    def unmount_vm_hdd(self, hs_name, vm_uuid):
        """卸载虚拟机数据盘"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}
        hdd_name = data.get('hdd_name', '')

        if not hdd_name or hdd_name not in vm_config.hdd_all:
            return self.api_response(404, '数据盘不存在')

        hdd_config = vm_config.hdd_all[hdd_name]

        # 调用HDDMount卸载
        result = server.HDDMount(vm_uuid, hdd_config, in_flag=False)
        if not result.success:
            return self.api_response(500, f'卸载失败: {result.message}')

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, '数据盘已卸载')

    # 移交数据盘所有权 ##################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: API响应
    # ####################################################################################
    def transfer_vm_hdd(self, hs_name, vm_uuid):
        """移交数据盘所有权到另一个虚拟机"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}
        hdd_name = data.get('hdd_name', '')
        target_vm = data.get('target_vm', '')

        if not hdd_name or hdd_name not in vm_config.hdd_all:
            return self.api_response(404, '数据盘不存在')
        if not target_vm:
            return self.api_response(400, '目标虚拟机不能为空')

        # 检查目标虚拟机是否存在
        if target_vm not in server.vm_saving:
            return self.api_response(404, '目标虚拟机不存在')

        hdd_config = vm_config.hdd_all[hdd_name]

        # 调用HDDTrans移交所有权
        result = server.HDDTrans(vm_uuid, hdd_config, target_vm)
        if not result.success:
            return self.api_response(500, f'移交失败: {result.message}')

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, '数据盘所有权移交成功')

    # 删除数据盘 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: API响应
    # ####################################################################################
    def delete_vm_hdd(self, hs_name, vm_uuid):
        """删除虚拟机数据盘"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}
        hdd_name = data.get('hdd_name', '')

        if not hdd_name or hdd_name not in vm_config.hdd_all:
            return self.api_response(404, '数据盘不存在')

        hdd_config = vm_config.hdd_all[hdd_name]

        # 调用RMMounts删除磁盘
        result = server.RMMounts(vm_uuid, hdd_name)
        if not result.success:
            return self.api_response(500, f'删除失败: {result.message}')

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, '数据盘已删除')

    # ========================================================================
    # ISO管理API - /api/client/iso/<action>/<hs_name>/<vm_uuid>
    # ========================================================================

    # 挂载ISO ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: API响应
    # ####################################################################################
    def mount_vm_iso(self, hs_name, vm_uuid):
        """挂载ISO镜像到虚拟机"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}
        iso_name = data.get('iso_name', '')  # 挂载名称（英文+数字）
        iso_file = data.get('iso_file', '')  # ISO文件名（xxx.iso）
        iso_hint = data.get('iso_hint', '')  # 备注

        if not iso_name:
            return self.api_response(400, '挂载名称不能为空')
        
        if not iso_file:
            return self.api_response(400, 'ISO文件不能为空')

        # 创建IMConfig对象
        from MainObject.Config.IMConfig import IMConfig
        iso_config = IMConfig(
            iso_name=iso_name,
            iso_file=iso_file,
            iso_hint=iso_hint
        )

        # 调用ISOMount挂载
        result = server.ISOMount(vm_uuid, iso_config, in_flag=True)
        if not result.success:
            return self.api_response(500, f'挂载失败: {result.message}')

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, 'ISO挂载成功')

    # 卸载ISO ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :param iso_index: ISO索引
    # :return: API响应
    # ####################################################################################
    def unmount_vm_iso(self, hs_name, vm_uuid, iso_name):
        """卸载虚拟机ISO镜像"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        if not hasattr(vm_config, 'iso_all') or not vm_config.iso_all:
            return self.api_response(404, 'ISO配置不存在')

        # iso_all现在是字典，使用iso_name作为key
        if iso_name not in vm_config.iso_all:
            return self.api_response(404, 'ISO不存在')

        iso_config = vm_config.iso_all[iso_name]

        # 调用ISOMount卸载
        result = server.ISOMount(vm_uuid, iso_config, in_flag=False)
        if not result.success:
            return self.api_response(500, f'卸载失败: {result.message}')

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, 'ISO已卸载')

    # ========================================================================
    # 备份管理API - /api/client/backup/<action>/<hs_name>/<vm_uuid>
    # ========================================================================

    # 创建备份 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: API响应
    # ####################################################################################
    def create_vm_backup(self, hs_name, vm_uuid):
        """创建虚拟机备份"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}
        vm_tips = data.get('vm_tips', '')

        if not vm_tips:
            return self.api_response(400, '备份说明不能为空')

        # 调用VMBackup创建备份
        result = server.VMBackup(vm_uuid, vm_tips)
        if not result.success:
            return self.api_response(500, f'备份失败: {result.message}')

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, '备份创建成功')

    # 还原备份 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: API响应
    # ####################################################################################
    def restore_vm_backup(self, hs_name, vm_uuid):
        """还原虚拟机备份"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}
        vm_back = data.get('vm_back', '')

        if not vm_back:
            return self.api_response(400, '备份名称不能为空')

        # 调用Restores还原备份
        result = server.Restores(vm_uuid, vm_back)
        if not result.success:
            return self.api_response(500, f'还原失败: {result.message}')

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, '备份还原成功')

    # 删除备份 ########################################################################
    # :param hs_name: 主机名称
    # :param vm_uuid: 虚拟机UUID
    # :return: API响应
    # ####################################################################################
    def delete_vm_backup(self, hs_name, vm_uuid):
        """删除虚拟机备份"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        vm_config = server.vm_saving.get(vm_uuid)
        if not vm_config:
            return self.api_response(404, '虚拟机不存在')

        data = request.get_json() or {}
        vm_back = data.get('vm_back', '')

        if not vm_back:
            return self.api_response(400, '备份名称不能为空')

        # 调用RMBackup删除备份
        result = server.RMBackup(vm_uuid, vm_back)
        if not result.success:
            return self.api_response(500, f'删除失败: {result.message}')

        # 从backups中删除
        vm_config.backups = [b for b in vm_config.backups if b.backup_name != vm_back]

        # 保存配置
        self.hs_manage.all_save()
        return self.api_response(200, '备份已删除')

    # 扫描备份 ########################################################################
    # :param hs_name: 主机名称
    # :return: API响应
    # ####################################################################################
    def scan_backups(self, hs_name):
        """扫描主机备份文件"""
        server = self.hs_manage.get_host(hs_name)
        if not server:
            return self.api_response(404, '主机不存在')

        try:
            # 调用LDBackup扫描备份
            result = server.LDBackup("")
            
            # 保存配置
            self.hs_manage.all_save()
            return self.api_response(200, '备份扫描成功')
        except Exception as e:
            logger.error(f"扫描备份失败: {e}")
            return self.api_response(500, f'扫描失败: {str(e)}')

    # 获取全局反向代理配置列表 ########################################################################
    # :return: 包含全局反向代理配置列表的API响应
    # ####################################################################################
    def get_global_proxy_configs(self):
        """获取全局反向代理配置列表"""
        try:
            proxy_list = []
            for proxy in self.hs_manage.web_all:
                if hasattr(proxy, '__save__'):
                    proxy_list.append(proxy.__save__())
                elif hasattr(proxy, '__save__') and callable(proxy.__save__):
                    proxy_list.append(proxy.__save__())
                else:
                    proxy_list.append({
                        'lan_port': getattr(proxy, 'lan_port', 0),
                        'lan_addr': getattr(proxy, 'lan_addr', ''),
                        'web_addr': getattr(proxy, 'web_addr', ''),
                        'web_tips': getattr(proxy, 'web_tips', ''),
                        'is_https': getattr(proxy, 'is_https', False)
                    })

            return self.api_response(200, 'success', proxy_list)
        except Exception as e:
            logger.error(f"获取全局代理配置失败: {e}")
            return self.api_response(500, f'获取全局代理配置失败: {str(e)}')

    # 添加全局反向代理配置 ########################################################################
    # :return: 全局反向代理配置添加结果的API响应
    # ####################################################################################
    def add_global_proxy_config(self):
        """添加全局反向代理配置"""
        try:
            data = request.get_json() or {}

            # 验证必填字段
            if not data.get('web_addr'):
                return self.api_response(400, '域名地址不能为空')
            if not data.get('lan_addr'):
                return self.api_response(400, '内网地址不能为空')
            if not data.get('lan_port'):
                return self.api_response(400, '内网端口不能为空')

            # 创建代理配置
            proxy_data = {
                'lan_port': int(data.get('lan_port', 0)),
                'lan_addr': data.get('lan_addr', ''),
                'web_addr': data.get('web_addr', ''),
                'web_tips': data.get('web_tips', ''),
                'is_https': bool(data.get('is_https', True))
            }

            # 调用HostManage添加代理
            result = self.hs_manage.add_proxy(proxy_data)
            if result.success:
                return self.api_response(200, result.message)
            else:
                return self.api_response(400, result.message)

        except Exception as e:
            logger.error(f"添加全局代理配置失败: {e}")
            traceback.print_exc()
            return self.api_response(500, f'添加全局代理配置失败: {str(e)}')

    # 删除全局反向代理配置 ########################################################################
    # :param web_addr: 代理域名地址
    # :return: 全局反向代理配置删除结果的API响应
    # ####################################################################################
    def delete_global_proxy_config(self, web_addr):
        """删除全局反向代理配置"""
        try:
            if not web_addr:
                return self.api_response(400, '域名地址不能为空')

            # 调用HostManage删除代理
            result = self.hs_manage.del_proxy(web_addr)
            if result.success:
                return self.api_response(200, result.message)
            else:
                return self.api_response(404, result.message)

        except Exception as e:
            logger.error(f"删除全局代理配置失败: {e}")
            traceback.print_exc()
            return self.api_response(500, f'删除全局代理配置失败: {str(e)}')

    # 获取系统网卡IPv4地址列表 ########################################################################
    # :return: 包含网卡IPv4地址列表的API响应
    # ####################################################################################

