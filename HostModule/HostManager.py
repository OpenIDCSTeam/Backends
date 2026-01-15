import json
import secrets
import traceback

from loguru import logger

from HostModule.HttpManager import HttpManager
from HostServer.BasicServer import BasicServer
from MainObject.Config.HSConfig import HSConfig
from MainObject.Server.HSEngine import HEConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.WebProxy import WebProxy
from MainObject.Public.ZMessage import ZMessage
from HostModule.DataManager import DataManager


class HostManage:
    # 初始化 #####################################################################
    def __init__(self):
        self.engine: dict[str, BasicServer] = {}
        self.logger: list[ZMessage] = []
        self.bearer: str = ""  # 先初始化saving变量
        self.saving = DataManager("./DataSaving/hostmanage.db")
        self.proxys: HttpManager | None = None
        self.web_all: list[WebProxy] = []  # 全局代理配置列表
        self.set_conf()

    # 字典化 #####################################################################
    def __save__(self):
        return {
            "engine": {
                string: server.__save__() for string, server in self.engine.items()
            },
            "logger": [
                logger.__save__() for logger in self.logger
            ],
            "bearer": self.bearer
        }

    # 加载全局配置 ###############################################################
    def set_conf(self):
        global_config = self.saving.get_ap_config()
        self.bearer = global_config.get("bearer", "")
        # 如果Token为空，自动生成一个新的Token
        if not self.bearer:
            self.bearer = secrets.token_hex(8)
            # 保存到数据库
            self.saving.set_ap_config(bearer=self.bearer)
            logger.info(f"[HostManage] 自动生成新Token: {self.bearer}")

    # 设置/重置访问Token #########################################################
    def set_pass(self, bearer: str = "") -> str:
        if bearer:
            self.bearer = bearer
        else:
            # 生成16位随机Token（包含字母和数字）
            self.bearer = secrets.token_hex(8)
        # 保存到数据库
        self.saving.set_ap_config(bearer=self.bearer)
        return self.bearer

    # 验证Token ##################################################################
    def aka_pass(self, token: str) -> bool:
        return token and token == self.bearer

    # 获取主机 ###################################################################
    def get_host(self, hs_name: str) -> BasicServer | None:
        if hs_name not in self.engine:
            return None
        return self.engine[hs_name]

    # 添加主机 ###################################################################
    def add_host(self, hs_name: str, hs_type: str, hs_conf: HSConfig) -> ZMessage:
        try:
            if hs_name in self.engine:
                return ZMessage(success=False, message="主机已添加")
            if hs_type not in HEConfig:
                return ZMessage(success=False, message="不支持的主机类型")
            # 设置server_name（关键！）=================
            hs_conf.server_name = hs_name
            self.engine[hs_name] = HEConfig[hs_type]["Imported"](hs_conf, db=self.saving)
            self.engine[hs_name].HSCreate()
            self.engine[hs_name].HSLoader()
            # 保存主机配置到数据库
            self.saving.set_hs_config(hs_name, hs_conf)
            return ZMessage(success=True, message="主机添加成功")
        except Exception as e:
            logger.error(f"添加主机失败: {e}")
            traceback.print_exc()
            return ZMessage(success=False, message=f"添加主机失败: {str(e)}")

    # 删除主机 ###################################################################
    def del_host(self, server):
        try:
            if server in self.engine:
                del self.engine[server]
                # 从数据库删除主机配置
                self.saving.del_hs_config(server)
                return True
            return False
        except Exception as e:
            logger.error(f"删除主机失败: {e}")
            traceback.print_exc()
            return False

    # 修改主机 ###################################################################
    def set_host(self, hs_name: str, hs_conf: HSConfig) -> ZMessage:
        try:
            if hs_name not in self.engine:
                return ZMessage(success=False, message="主机未找到")

            # 保存原有的虚拟机配置
            old_server = self.engine[hs_name]
            old_vm_saving = old_server.vm_saving

            # 设置server_name（关键！）=================
            hs_conf.server_name = hs_name
            # 重新创建主机实例
            self.engine[hs_name] = HEConfig[hs_conf.server_type]["Imported"](hs_conf, db=self.saving)

            # 恢复虚拟机配置（状态数据已在数据库中）
            self.engine[hs_name].vm_saving = old_vm_saving

            self.engine[hs_name].HSUnload()
            self.engine[hs_name].HSLoader()
            # 保存主机配置到数据库
            self.saving.set_hs_config(hs_name, hs_conf)
            return ZMessage(success=True, message="主机更新成功")
        except Exception as e:
            logger.error(f"修改主机失败: {e}")
            traceback.print_exc()
            return ZMessage(success=False, message=f"修改主机失败: {str(e)}")

    # 修改主机 ###################################################################
    def pwr_host(self, hs_name: str, hs_flag: bool) -> ZMessage:
        try:
            if hs_name not in self.engine:
                return ZMessage(success=False, message="主机未找到")
            if hs_flag:
                self.engine[hs_name].HSLoader()
            else:
                self.engine[hs_name].HSUnload()
            return ZMessage(success=True, message="主机启用状态=" + str(hs_flag))
        except Exception as e:
            logger.error(f"修改主机状态失败: {e}")
            traceback.print_exc()
            return ZMessage(success=False, message=f"修改主机状态失败: {str(e)}")

    # 加载信息 ###################################################################
    def all_load(self):
        """从数据库加载所有信息"""
        try:
            # 加载全局日志
            self.logger = []
            global_logs = self.saving.get_hs_logger()
            for log_data in global_logs:
                self.logger.append(ZMessage(**log_data) if isinstance(log_data, dict) else log_data)

            # 启动Http实例
            self.proxys = HttpManager()
            self.proxys.global_get()
            self.proxys.config_all()
            self.proxys.launch_web()

            # 加载全局代理配置
            # self.web_all = []
            self.web_all = self.saving.get_web_proxy()

            # for proxy_data in web_proxy_list:
            #     web_proxy = WebProxy()
            #     web_proxy.lan_port = proxy_data.get('lan_port', 0)
            #     web_proxy.lan_addr = proxy_data.get('lan_addr', '')
            #     web_proxy.web_addr = proxy_data.get('web_addr', '')
            #     web_proxy.web_tips = proxy_data.get('web_tips', '')
            #     web_proxy.is_https = proxy_data.get('is_https', True)
            #     self.web_all.append(web_proxy)
            #     # 添加到HttpManage
            #     self.proxys.proxy_add(
            #         (web_proxy.lan_port, web_proxy.lan_addr),
            #         web_proxy.web_addr,
            #         web_proxy.is_https
            #     )

            # 加载所有主机配置
            host_configs = self.saving.all_hs_config()
            for host_config in host_configs:
                hs_name = host_config["hs_name"]

                # 重建HSConfig对象
                hs_conf_data = dict(host_config)
                hs_conf_data["extend_data"] = json.loads(host_config["extend_data"]) if host_config[
                    "extend_data"] else {}
                # 解析新字段的JSON数据
                hs_conf_data["system_maps"] = json.loads(host_config["system_maps"]) if host_config.get(
                    "system_maps") else {}
                hs_conf_data["images_maps"] = json.loads(host_config["images_maps"]) if host_config.get(
                    "images_maps") else {}
                hs_conf_data["public_addr"] = json.loads(host_config["public_addr"]) if host_config.get(
                    "public_addr") else []
                hs_conf_data["server_dnss"] = json.loads(host_config["server_dnss"]) if host_config.get(
                    "server_dnss") else []
                hs_conf_data["ipaddr_maps"] = json.loads(host_config["ipaddr_maps"]) if host_config.get(
                    "ipaddr_maps") else {}
                hs_conf_data["ipaddr_dnss"] = json.loads(host_config["ipaddr_dnss"]) if host_config.get(
                    "ipaddr_dnss") else ["119.29.29.29", "223.5.5.5"]

                # 移除数据库字段，只保留配置字段
                for field in ["id", "hs_name", "created_at", "updated_at"]:
                    hs_conf_data.pop(field, None)

                hs_conf = HSConfig(**hs_conf_data)
                # 设置server_name（关键！）=================
                hs_conf.server_name = hs_name

                # 获取主机完整数据
                host_full_data = self.saving.get_ap_server(hs_name)

                # 转换 vm_saving 字典为 VMConfig 对象
                vm_saving_converted = {}
                for vm_uuid, vm_config in host_full_data["vm_saving"].items():
                    if isinstance(vm_config, dict):
                        vm_saving_converted[vm_uuid] = VMConfig(**vm_config)
                    else:
                        vm_saving_converted[vm_uuid] = vm_config
                    for web_data in vm_saving_converted[vm_uuid].web_all:
                        self.proxys.create_web(
                            (web_data.lan_port, web_data.lan_addr),
                            web_data.web_addr, is_https=web_data.is_https
                        )

                # 创建BaseServer实例（状态数据由DataManage立即保存）=================
                if hs_conf.server_type in HEConfig:
                    server_class = HEConfig[hs_conf.server_type]["Imported"]
                    self.engine[hs_name] = server_class(
                        hs_conf,
                        db=self.saving,
                        vm_saving=vm_saving_converted
                    )
                    self.engine[hs_name].HSLoader()
        except Exception as e:
            logger.error(f"加载数据时出错: {e}")
            traceback.print_exc()

    # 保存信息 ###################################################################
    def all_save(self) -> bool:
        """保存所有信息到数据库"""
        try:
            success = True
            # 保存全局日志
            if self.logger:
                self.saving.set_hs_logger(None, self.logger)

            # 保存每个主机的配置数据（状态数据由DataManage立即保存）=================
            for hs_name, server in self.engine.items():
                success &= server.data_set()
            # 关闭web服务器
            if self.proxys is not None:
                self.proxys.closed_web()
            return success
        except Exception as e:
            logger.error(f"保存数据时出错: {e}")
            traceback.print_exc()
            return False

    # 退出程序 ###################################################################
    def all_exit(self):
        for server in self.engine:
            self.engine[server].HSUnload()

    # 扫描虚拟机 #################################################################
    def vms_scan(self, hs_name: str, prefix: str = "") -> ZMessage:
        """
        扫描主机上的虚拟机并保存到数据库
        :param hs_name: 主机名称
        :param prefix: 虚拟机名称前缀过滤（如果为空，则使用主机配置的filter_name）
        :return: 操作结果
        """
        if hs_name not in self.engine:
            return ZMessage(success=False, message=f"Host {hs_name} not found")

        server = self.engine[hs_name]

        # 检查是否支持VScanner方法
        if not hasattr(server, 'VScanner'):
            return ZMessage(success=False, message="Host does not support VM scanning")

        # 如果指定了prefix参数，临时修改主机配置的filter_name
        original_filter_name = None
        if prefix:
            original_filter_name = server.hs_config.filter_name if server.hs_config else None
            if server.hs_config:
                server.hs_config.filter_name = prefix

        try:
            # 调用服务器的VScanner方法
            result = server.VMDetect()
            return result
        finally:
            # 恢复原始的filter_name
            if original_filter_name is not None and server.hs_config:
                server.hs_config.filter_name = original_filter_name

    # 添加全局代理 ###################################################################
    def add_proxy(self, proxy_data: dict) -> ZMessage:
        """
        添加全局代理配置
        :param proxy_data: 代理配置数据字典
        :return: 操作结果
        """
        try:
            # 创建WebProxy对象
            web_proxy = WebProxy()
            web_proxy.lan_port = proxy_data.get('lan_port', 0)
            web_proxy.lan_addr = proxy_data.get('lan_addr', '')
            web_proxy.web_addr = proxy_data.get('web_addr', '')
            web_proxy.web_tips = proxy_data.get('web_tips', '')
            web_proxy.is_https = proxy_data.get('is_https', True)

            # 检查代理是否已存在
            for proxy in self.web_all:
                if proxy.web_addr == web_proxy.web_addr:
                    return ZMessage(success=False, message=f"代理域名 {web_proxy.web_addr} 已存在")

            # 调用HttpManage添加代理
            if self.proxys:
                result = self.proxys.create_web(
                    (web_proxy.lan_port, web_proxy.lan_addr),
                    web_proxy.web_addr,
                    web_proxy.is_https
                )
                if not result:
                    return ZMessage(success=False, message="添加代理到HttpManage失败")
            else:
                return ZMessage(success=False, message="HttpManage未初始化")

            # 添加到web_all列表
            self.web_all.append(web_proxy)

            # 保存到数据库
            success = self.saving.add_web_proxy(proxy_data)
            if not success:
                # 如果保存失败，回滚操作
                self.web_all.remove(web_proxy)
                if self.proxys:
                    self.proxys.remove_web(web_proxy.web_addr)
                return ZMessage(success=False, message="保存代理配置到数据库失败")

            return ZMessage(success=True, message=f"代理 {web_proxy.web_addr} 添加成功")

        except Exception as e:
            logger.error(f"添加全局代理失败: {e}")
            traceback.print_exc()
            return ZMessage(success=False, message=f"添加代理失败: {str(e)}")

    # 删除全局代理 ###################################################################
    def del_proxy(self, web_addr: str) -> ZMessage:
        """
        删除全局代理配置
        :param web_addr: 代理域名
        :return: 操作结果
        """
        try:
            # 查找代理
            web_proxy = None
            for proxy in self.web_all:
                if proxy.web_addr == web_addr:
                    web_proxy = proxy
                    break

            if not web_proxy:
                return ZMessage(success=False, message=f"代理域名 {web_addr} 不存在")

            # 调用HttpManage删除代理
            if self.proxys:
                result = self.proxys.remove_web(web_addr)
                if not result:
                    return ZMessage(success=False, message="从HttpManage删除代理失败")
            else:
                return ZMessage(success=False, message="HttpManage未初始化")

            # 从web_all列表移除
            self.web_all.remove(web_proxy)

            # 从数据库删除
            success = self.saving.del_web_proxy(web_addr)
            if not success:
                # 如果删除失败，回滚操作
                self.web_all.append(web_proxy)
                if self.proxys:
                    self.proxys.create_web(
                        (web_proxy.lan_port, web_proxy.lan_addr),
                        web_proxy.web_addr,
                        web_proxy.is_https
                    )
                return ZMessage(success=False, message="从数据库删除代理配置失败")

            return ZMessage(success=True, message=f"代理 {web_addr} 删除成功")

        except Exception as e:
            logger.error(f"删除全局代理失败: {e}")
            traceback.print_exc()
            return ZMessage(success=False, message=f"删除代理失败: {str(e)}")

    # 定时任务 ###################################################################
    def exe_cron(self):
        """
        执行定时任务
        注意：状态数据已通过 DataManage 立即保存，无需在定时任务中保存 =================
        """
        for server in self.engine:
            logger.debug(f'[Cron] 执行{server}的定时任务')
            self.engine[server].Crontabs()
        
        # 清理已删除虚拟机的状态数据
        self._cleanup_deleted_vm_status()
        
        # 重新计算所有用户的资源配额
        self._recalculate_user_quotas()
        
        logger.debug('[Cron] 执行定时任务完成')
    
    def _recalculate_user_quotas(self):
        """
        遍历所有虚拟机，重新计算用户资源配额
        只有虚拟机 own_all 列表中的第一个用户才占用配额
        """
        try:
            # 获取所有用户
            all_users = self.saving.get_all_users()
            if not all_users:
                return
            
            # 初始化所有用户的资源使用量为0
            user_resources = {}
            for user in all_users:
                user_resources[user['username']] = {
                    'user_id': user['id'],
                    'cpu': 0,
                    'ram': 0,
                    'ssd': 0,
                    'gpu': 0,
                    'traffic': 0,
                    'nat_ports': 0,
                    'web_proxy': 0,
                    'bandwidth_up': 0,
                    'bandwidth_down': 0
                }
            
            # 遍历所有主机的所有虚拟机
            for server_name, server in self.engine.items():
                if not hasattr(server, 'vm_saving'):
                    continue
                
                for vm_uuid, vm_config in server.vm_saving.items():
                    # 获取虚拟机的第一个所有者
                    owners = getattr(vm_config, 'own_all', [])
                    if not owners:
                        continue
                    
                    first_owner = owners[0]
                    
                    # 跳过admin用户
                    if first_owner == 'admin':
                        continue
                    
                    # 如果用户不在用户列表中，跳过
                    if first_owner not in user_resources:
                        continue
                    
                    # 累加该用户的资源使用量
                    user_resources[first_owner]['cpu'] += getattr(vm_config, 'cpu_num', 0)
                    # 虚拟机的mem_num字段单位是MB，需要转换为GB存储到用户表
                    ram_mb = getattr(vm_config, 'mem_num', 0)
                    user_resources[first_owner]['ram'] += ram_mb
                    # 虚拟机的hdd_num字段单位是MB，需要转换为GB存储到用户表
                    hdd_mb = getattr(vm_config, 'hdd_num', 0)
                    user_resources[first_owner]['ssd'] += hdd_mb
                    # 虚拟机的gpu_mem字段单位是MB，需要转换为GB存储到用户表
                    gpu_mem_mb = getattr(vm_config, 'gpu_mem', 0)
                    user_resources[first_owner]['gpu'] += gpu_mem_mb
                    # 虚拟机的flu_num字段单位是MB，需要转换为GB存储到用户表
                    flu_mb = getattr(vm_config, 'flu_num', 0)
                    user_resources[first_owner]['traffic'] += flu_mb
                    user_resources[first_owner]['nat_ports'] += getattr(vm_config, 'nat_num', 0)
                    user_resources[first_owner]['web_proxy'] += getattr(vm_config, 'web_num', 0)
                    # 虚拟机的speed_u和speed_d字段单位是Mbps，直接使用
                    user_resources[first_owner]['bandwidth_up'] += getattr(vm_config, 'speed_u', 0)
                    user_resources[first_owner]['bandwidth_down'] += getattr(vm_config, 'speed_d', 0)
            
            # 更新所有用户的资源使用量
            for username, resources in user_resources.items():
                self.saving.update_user_resource_usage(
                    resources['user_id'],
                    used_cpu=resources['cpu'],
                    used_ram=resources['ram'],
                    used_ssd=resources['ssd'],
                    used_gpu=resources['gpu'],
                    used_traffic=resources['traffic'],
                    used_nat_ports=resources['nat_ports'],
                    used_web_proxy=resources['web_proxy'],
                    used_bandwidth_up=resources['bandwidth_up'],
                    used_bandwidth_down=resources['bandwidth_down']
                )
            
            logger.debug('[Cron] 用户资源配额重新计算完成')
            
        except Exception as e:
            logger.error(f'[Cron] 重新计算用户配额失败: {e}')
            traceback.print_exc()

    def _cleanup_deleted_vm_status(self):
        """
        清理已删除虚拟机的状态数据
        遍历数据库中的vm_status表，删除不存在于vm_saving中的虚拟机状态
        """
        try:
            logger.debug('[Cron] 开始清理已删除虚拟机的状态数据')
            
            # 获取所有主机配置
            all_hosts = self.saving.all_hs_config()
            
            # 构建所有现有虚拟机的集合 (主机名, 虚拟机UUID)
            existing_vms = set()
            for host_config in all_hosts:
                hs_name = host_config['hs_name']
                vm_saving = self.saving.get_vm_saving(hs_name)
                for vm_uuid in vm_saving.keys():
                    existing_vms.add((hs_name, vm_uuid))
            
            # 获取数据库中所有虚拟机状态
            conn = self.saving.get_db_sqlite()
            try:
                cursor = conn.execute("SELECT DISTINCT hs_name, vm_uuid FROM vm_status")
                db_vms = cursor.fetchall()
                
                deleted_count = 0
                for hs_name, vm_uuid in db_vms:
                    if (hs_name, vm_uuid) not in existing_vms:
                        # 这个虚拟机不存在于vm_saving中，说明已被删除，清理其状态数据
                        if self.saving.delete_vm_status(hs_name, vm_uuid):
                            deleted_count += 1
                            logger.debug(f'[Cron] 已清理已删除虚拟机状态: 主机={hs_name}, 虚拟机={vm_uuid}')
                
                if deleted_count > 0:
                    logger.info(f'[Cron] 清理完成，共删除 {deleted_count} 个已删除虚拟机的状态数据')
                else:
                    logger.debug('[Cron] 没有需要清理的虚拟机状态数据')
                    
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f'[Cron] 清理已删除虚拟机状态数据失败: {e}')
            import traceback
            traceback.print_exc()

    def recalculate_user_quotas(self):
        """
        公共方法：手动触发用户资源配额重新计算
        可用于立即更新用户资源使用统计
        """
        logger.info('[手动] 触发用户资源配额重新计算')
        self._recalculate_user_quotas()
        logger.info('[手动] 用户资源配额重新计算完成')
