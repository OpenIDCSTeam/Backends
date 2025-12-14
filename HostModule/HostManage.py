import json
import secrets
import traceback

from loguru import logger

from HostModule.HttpManage import HttpManage
from HostServer.BaseServer import BaseServer
from MainObject.Config.HSConfig import HSConfig
from MainObject.Server.HSEngine import HEConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.WebProxy import WebProxy
from MainObject.Public.ZMessage import ZMessage
from HostModule.DataManage import HostDatabase


class HostManage:
    # 初始化 #####################################################################
    def __init__(self):
        self.engine: dict[str, BaseServer] = {}
        self.logger: list[ZMessage] = []
        self.bearer: str = ""  # 先初始化saving变量
        self.saving = HostDatabase("./DataSaving/hostmanage.db")
        self.proxys: HttpManage | None = None
        self.web_all: list[WebProxy] = []  # 全局代理配置列表
        self.set_conf()

    # 字典化 #####################################################################
    def __dict__(self):
        return {
            "engine": {
                string: server.__dict__() for string, server in self.engine.items()
            },
            "logger": [
                logger.__dict__() for logger in self.logger
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
    def get_host(self, hs_name: str) -> BaseServer | None:
        if hs_name not in self.engine:
            return None
        return self.engine[hs_name]

    # 添加主机 ###################################################################
    def add_host(self, hs_name: str, hs_type: str, hs_conf: HSConfig) -> ZMessage:
        if hs_name in self.engine:
            return ZMessage(success=False, message="Host already add")
        if hs_type not in HEConfig:
            return ZMessage(success=False, message="Host unsupported")
        # 设置server_name（关键！）=================
        hs_conf.server_name = hs_name
        self.engine[hs_name] = HEConfig[hs_type]["Imported"](hs_conf, db=self.saving)
        self.engine[hs_name].HSCreate()
        self.engine[hs_name].HSLoader()
        # 保存主机配置到数据库
        self.saving.set_hs_config(hs_name, hs_conf)
        return ZMessage(success=True, message="Host added successful")

    # 删除主机 ###################################################################
    def del_host(self, server):
        if server in self.engine:
            del self.engine[server]
            # 从数据库删除主机配置
            self.saving.del_hs_config(server)
            return True
        return False

    # 修改主机 ###################################################################
    def set_host(self, hs_name: str, hs_conf: HSConfig) -> ZMessage:
        if hs_name not in self.engine:
            return ZMessage(success=False, message="Host not found")

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
        return ZMessage(success=True, message="Host updated successful")

    # 修改主机 ###################################################################
    def pwr_host(self, hs_name: str, hs_flag: bool) -> ZMessage:
        if hs_name not in self.engine:
            return ZMessage(success=False, message="Host not found")
        if hs_flag:
            self.engine[hs_name].HSLoader()
        else:
            self.engine[hs_name].HSUnload()
        return ZMessage(success=True, message="Host enable=" + str(hs_flag))

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
            self.proxys = HttpManage()
            self.proxys.start_web()

            # 加载全局代理配置
            self.web_all = []
            web_proxy_list = self.saving.get_web_proxy()
            for proxy_data in web_proxy_list:
                web_proxy = WebProxy()
                web_proxy.lan_port = proxy_data.get('lan_port', 0)
                web_proxy.lan_addr = proxy_data.get('lan_addr', '')
                web_proxy.web_addr = proxy_data.get('web_addr', '')
                web_proxy.web_tips = proxy_data.get('web_tips', '')
                web_proxy.is_https = proxy_data.get('is_https', True)
                self.web_all.append(web_proxy)
                # 添加到HttpManage
                self.proxys.proxy_add(
                    (web_proxy.lan_port, web_proxy.lan_addr),
                    web_proxy.web_addr,
                    web_proxy.is_https
                )

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
                        self.proxys.proxy_add(
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
                    self.engine[hs_name].VCLoader()

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
                self.proxys.close_web()
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

        try:
            # 获取VMRestAPI实例（假设是Vmware类型）
            if not hasattr(server, 'vmrest_api'):
                return ZMessage(success=False, message="Host does not support VM scanning")

            # 使用主机配置的filter_name作为前缀过滤（如果prefix参数为空）
            filter_prefix = prefix if prefix else (server.hs_config.filter_name if server.hs_config else "")

            # 获取所有虚拟机列表
            vms_result = server.vmrest_api.return_vmx()
            if not vms_result.success:
                return ZMessage(success=False, message=f"Failed to get VM list: {vms_result.message}")

            vms_list = vms_result.results if isinstance(vms_result.results, list) else []
            scanned_count = 0  # 符合过滤条件的虚拟机数量
            added_count = 0  # 新增的虚拟机数量

            # 处理每个虚拟机
            for vm_info in vms_list:
                vm_path = vm_info.get("path", "")
                vm_id = vm_info.get("id", "")

                if not vm_path:
                    continue

                # 从路径中提取虚拟机名称
                import os
                vmx_name = os.path.splitext(os.path.basename(vm_path))[0]

                # 前缀过滤（使用主机配置的filter_name或传入的prefix）
                if filter_prefix and not vmx_name.startswith(filter_prefix):
                    continue

                # 符合过滤条件的虚拟机计数
                scanned_count += 1

                # 检查是否已存在
                if vmx_name in server.vm_saving:
                    continue

                # 创建默认虚拟机配置
                default_vm_config = VMConfig()
                # 添加到服务器的虚拟机配置中
                server.vm_saving[vmx_name] = default_vm_config

                # 虚拟机状态由DataManage管理，立即保存到数据库 =================

                added_count += 1

                # 记录日志
                log_msg = ZMessage(
                    success=True,
                    actions="scan_vm",
                    message=f"发现并添加虚拟机: {vmx_name}",
                    results={"vm_name": vmx_name, "vm_id": vm_id, "vm_path": vm_path}
                )
                server.LogStack(log_msg)

            # 保存到数据库
            if added_count > 0:
                success = server.data_set()
                if not success:
                    return ZMessage(success=False, message="Failed to save scanned VMs to database")

            return ZMessage(
                success=True,
                message=f"扫描完成。共扫描到{scanned_count}台虚拟机，新增{added_count}台虚拟机配置。",
                results={
                    "scanned": scanned_count,
                    "added": added_count,
                    "prefix_filter": filter_prefix
                }
            )

        except Exception as e:
            return ZMessage(success=False, message=f"扫描虚拟机时出错: {str(e)}")

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
                result = self.proxys.proxy_add(
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
                    self.proxys.proxy_del(web_proxy.web_addr)
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
                result = self.proxys.proxy_del(web_addr)
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
                    self.proxys.proxy_add(
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
        logger.debug('[Cron] 执行定时任务完成')
