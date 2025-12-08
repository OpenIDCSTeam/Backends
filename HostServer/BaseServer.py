import abc
import os.path
import random
import string
import threading
from datetime import datetime, timedelta
from loguru import logger
from MainObject.Config.HSConfig import HSConfig
from MainObject.Server.HSTasker import HSTasker
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from HostModule.NetsManage import NetsManage
from VNCConsole.VNCManager import VNCStart, VProcess


class BaseServer(abc.ABC):
    def __init__(self, config: HSConfig, **kwargs):
        # 宿主机配置 =========================================
        self.hs_config: HSConfig | None = config  # 物理机配置
        self.hs_status: list[HWStatus] = []  # Hosts主机使用率
        self.hs_logger: list[ZMessage] = []  # SUB搜集日志记录
        # 虚拟机配置 =========================================
        self.vm_saving: dict[str, VMConfig] = {}  # 存储的配置
        self.vm_status: dict[str, list[HWStatus]] = {}  # 状态
        self.vm_tasker: list[HSTasker] = []  # SUB搜集任务列表
        self.vm_remote: VProcess | None = None  # 远程连接记录
        # 数据库引用 =========================================
        self.save_time = None
        self.save_data = kwargs.get('db', None)  # 数据库操作
        self.hs_server = kwargs.get('hs_name', '')  # 主机名称
        # 加载数据 ===========================================
        self.__load__(**kwargs)
        # 日志系统配置 =======================================
        self.LogSetup()
        self.OpenSave()

    # 转换字典 ##########################################################################
    def __dict__(self):
        return {
            "hs_config": self.__save__(self.hs_config),
            "hs_status": [
                self.__save__(status)
                for status in self.hs_status
            ],
            "vm_saving": {
                string: self.__save__(saving)
                for string, saving in self.vm_saving.items()
            },
            "vm_status": {
                string: self.__save__(record)
                for string, record in self.vm_status.items()
            },
            "vm_tasker": [
                self.__save__(tasker)
                for tasker in self.vm_tasker
            ],
            "save_logs": [
                self.__save__(logger)
                for logger in self.hs_logger
            ]
        }

    # 转换为字典 ########################################################################
    # :params obj: 需要转换的对象
    # ###################################################################################
    @staticmethod
    def __save__(obj):
        """辅助方法：将对象转换为可序列化的字典"""
        if obj is None:
            return None
        # 处理列表类型，递归转换每个元素
        if isinstance(obj, list):
            return [BaseServer.__save__(item) for item in obj]
        if hasattr(obj, '__dict__'):
            if callable(getattr(obj, '__dict__')):
                return obj.__dict__()
        return obj

    # 加载数据 ##########################################################################
    # :params kwargs: 关键字参数
    # ###################################################################################
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # 读取数据 ##########################################################################
    # :params data: 数据字典
    # ###################################################################################
    def __read__(self, data: dict):
        self.hs_config = HSConfig(data["hs_config"])
        self.hs_status = data["hs_status"]
        # 将字典转换为 VMConfig 对象
        self.vm_saving = {}
        for vm_uuid, vm_config in data["vm_saving"].items():
            if isinstance(vm_config, dict):
                self.vm_saving[vm_uuid] = VMConfig(**vm_config)
                print(f"[DEBUG __read__] {vm_uuid} 转换为 VMConfig: {type(self.vm_saving[vm_uuid])}")
            else:
                self.vm_saving[vm_uuid] = vm_config
                print(f"[DEBUG __read__] {vm_uuid} 直接赋值: {type(self.vm_saving[vm_uuid])}")
        self.vm_status = data["vm_status"]
        self.vm_tasker = data["vm_tasker"]
        self.hs_logger = data["save_logs"]

    #####################################################################################
    #####################################################################################
    # 内置的方法 ########################################################################
    #####################################################################################
    #####################################################################################

    # 启动自动保存定时器 ################################################################
    def OpenSave(self):
        """启动自动保存定时器，每5分钟自动保存一次"""

        def auto_save_task():
            try:
                if self.data_set():
                    logger.info(f"[{self.hs_server}] 自动保存成功")
                else:
                    logger.warning(f"[{self.hs_server}] 自动保存失败")
            except Exception as e:
                logger.error(f"[{self.hs_server}] 自动保存异常: {e}")
            # 继续下一次定时
            self.save_time = threading.Timer(300, auto_save_task)
            self.save_time.daemon = True
            self.save_time.start()

        # 启动定时器
        self.save_time = threading.Timer(300, auto_save_task)
        self.save_time.daemon = True
        self.save_time.start()

    # 停止自动保存定时器 ################################################################
    def StopSave(self):
        """停止自动保存定时器"""
        if self.save_time:
            self.save_time.cancel()
            self.save_time = None

    # 配置日志系统 ######################################################################
    def LogSetup(self):
        """配置loguru日志系统"""
        if self.hs_server:
            # 为每个主机创建独立的日志文件
            log_file = f"./logs/{self.hs_server}.log"
            logger.add(
                log_file,
                rotation="10 MB",  # 日志文件达到10MB时轮转
                retention="7 days",  # 保留7天的日志
                compression="zip",  # 压缩旧日志
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
                level="INFO"
            )
            logger.info(f"[{self.hs_server}] 日志系统已初始化")

    # 清理过期日志 ######################################################################
    # :param days: 保留天数，默认7天
    # ###################################################################################
    def LogClean(self, days: int = 7):
        """
        清理指定天数之前的日志记录
        :param days: 保留天数，默认7天
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            original_count = len(self.hs_logger)

            # 过滤日志，保留最近的记录
            self.hs_logger = [
                log for log in self.hs_logger
                if hasattr(log, 'execute') and log.execute and
                   datetime.fromisoformat(log.execute) > cutoff_time
            ]

            removed_count = original_count - len(self.hs_logger)
            if removed_count > 0:
                logger.info(f"[{self.hs_server}] 清理了 {removed_count} 条过期日志（{days}天前）")
                # 立即保存
                self.data_set()

            return removed_count
        except Exception as e:
            logger.error(f"[{self.hs_server}] 清理日志失败: {e}")
            return 0

    # 添加日志记录 ######################################################################
    # :params log: 日志消息对象
    # ###################################################################################
    def LogStack(self, log: ZMessage):
        """
        添加日志记录并立即保存到数据库
        :param log: ZMessage日志对象
        """
        self.hs_logger.append(log)

        # 使用loguru记录日志
        log_level = "ERROR" if not log.success else "INFO"
        log_msg = f"[{self.hs_server}] {log.actions}: {log.message}"

        if log_level == "ERROR":
            logger.error(log_msg)
        else:
            logger.info(log_msg)

        # 立即保存到数据库
        if self.save_data and self.hs_server:
            try:
                self.save_data.save_logger(self.hs_server, self.hs_logger)
                self.data_set(immediate=True)
            except Exception as e:
                logger.error(f"[{self.hs_server}] 保存日志失败: {e}")

    # 保存数据到数据库 ##################################################################
    # :params immediate: 是否立即保存（默认True）
    # :return: 保存是否成功
    # ###################################################################################
    def data_set(self, immediate: bool = True) -> bool:
        """
        保存当前数据到数据库
        :param immediate: 是否立即保存，True则立即写入数据库
        :return: 保存是否成功
        """
        if self.save_data and self.hs_server:
            try:
                success = self.save_data.save_host_full_data(self.hs_server, self.__dict__())
                if success and immediate:
                    logger.debug(f"[{self.hs_server}] 数据已立即保存到数据库")
                return success
            except Exception as e:
                logger.error(f"[{self.hs_server}] 保存数据失败: {e}")
                return False
        return False

    # 从数据库重新加载数据 ##############################################################
    # :return: 加载是否成功
    # ###################################################################################
    def data_get(self) -> bool:
        """从数据库重新加载虚拟机数据"""
        if self.save_data and self.hs_server:
            try:
                # 从数据库获取主机状态
                hs_status_data = self.save_data.get_hs_status(self.hs_server)
                if hs_status_data:
                    self.hs_status = []
                    for status_data in hs_status_data:
                        if isinstance(status_data, dict):
                            self.hs_status.append(HWStatus(**status_data))
                        else:
                            self.hs_status.append(status_data)

                # 从数据库获取虚拟机配置
                vm_saving_data = self.save_data.get_vm_saving(self.hs_server)
                if vm_saving_data:
                    self.vm_saving = {}
                    for vm_uuid, vm_config in vm_saving_data.items():
                        print(f"[DEBUG data_get] {vm_uuid} 原始数据类型: {type(vm_config)}")
                        if isinstance(vm_config, dict):
                            self.vm_saving[vm_uuid] = VMConfig(**vm_config)
                            print(f"[DEBUG data_get] {vm_uuid} 转换为 VMConfig: {type(self.vm_saving[vm_uuid])}")
                        else:
                            self.vm_saving[vm_uuid] = vm_config
                            print(f"[DEBUG data_get] {vm_uuid} 直接赋值: {type(self.vm_saving[vm_uuid])}")

                # 从数据库获取虚拟机状态
                vm_status_data = self.save_data.get_vm_status(self.hs_server)
                if vm_status_data:
                    self.vm_status = {}
                    for vm_uuid, status_list in vm_status_data.items():
                        self.vm_status[vm_uuid] = []
                        if isinstance(status_list, list):
                            for status_data in status_list:
                                if isinstance(status_data, dict):
                                    self.vm_status[vm_uuid].append(HWStatus(**status_data))
                                else:
                                    self.vm_status[vm_uuid].append(status_data)
                        else:
                            self.vm_status[vm_uuid] = status_list

                # 从数据库获取虚拟机任务
                vm_tasker_data = self.save_data.get_vm_tasker(self.hs_server)
                if vm_tasker_data:
                    self.vm_tasker = []
                    for tasker_data in vm_tasker_data:
                        if isinstance(tasker_data, dict):
                            self.vm_tasker.append(HSTasker(**tasker_data))
                        else:
                            self.vm_tasker.append(tasker_data)

                # 从数据库获取日志记录
                logger_data = self.save_data.get_logger(self.hs_server)
                if logger_data:
                    self.hs_logger = []
                    for log_data in logger_data:
                        if isinstance(log_data, dict):
                            self.hs_logger.append(ZMessage(**log_data))
                        else:
                            self.hs_logger.append(log_data)

                return True
            except Exception as e:
                print(f"从数据库加载数据失败: {e}")
                return False
        return False

    #####################################################################################
    #####################################################################################
    # 默认的方法 ########################################################################
    #####################################################################################
    #####################################################################################

    # 读取远程 ##########################################################################
    # :param ip_addr: 远程IP地址
    # :returns: 是否成功
    # ###################################################################################
    def VNCLoads(self, ip_addr: str = "127.0.0.1") -> bool:
        cfg_name = "vnc_" + self.hs_config.server_name
        cfg_full = "DataSaving/" + cfg_name + ".cfg"
        # if os.path.exists(cfg_full):
        #     os.remove(cfg_full)
        tp_remote = VNCStart(self.hs_config.remote_port, cfg_name)
        self.vm_remote = VProcess(tp_remote)
        self.vm_remote.start()
        # for vm_name, vm_config in self.vm_saving.items():
        #     if vm_config.vc_port is None or vm_config.vc_port == "":
        #         continue
        #     self.vm_remote.exec.add_port(
        #         ip_addr, int(vm_config.vc_port), vm_config.vc_pass
        #     )
        return True

    # 虚拟机控制台 ######################################################################
    # :params vm_uuid: 虚拟机UUID
    # ###################################################################################
    def VConsole(self, vm_uuid: str, ip_addr: str = "127.0.0.1") -> str:
        if vm_uuid not in self.vm_saving:
            return ""
        print(f"[DEBUG VConsole] vm_saving 内容: {self.vm_saving}")
        print(f"[DEBUG VConsole] {vm_uuid} 的类型: {type(self.vm_saving[vm_uuid])}")
        print(f"[DEBUG VConsole] {vm_uuid} 的值: {self.vm_saving[vm_uuid]}")
        if self.vm_saving[vm_uuid].vc_port == "":
            print(f"[VConsole] {vm_uuid} 的 vc_port 为空")
            return ""
        if self.vm_saving[vm_uuid].vc_pass == "":
            print(f"[VConsole] {vm_uuid} 的 vc_pass 为空")
            return ""
        public_addr = self.hs_config.public_addr[0]
        if len(self.vm_saving[vm_uuid].vc_pass) == 0:
            public_addr = "127.0.0.1"
        rand_pass = ''.join(random.sample(string.ascii_letters + string.digits, 16))
        self.vm_remote.exec.del_port(ip_addr, int(self.vm_saving[vm_uuid].vc_port))
        self.vm_remote.exec.add_port(
            ip_addr, int(self.vm_saving[vm_uuid].vc_port), rand_pass
        )
        return f"http://{public_addr}:{self.hs_config.remote_port}" \
               f"/vnc.html?autoconnect=true&path=websockify?" \
               f"token={rand_pass}"

    # 网卡网络映射 #####################################################################
    # :params nic_config: 网卡配置对象
    # ###################################################################################
    def _get_network_device(self, nic_config) -> str:
        """根据nic_type和nic_devs获取对应的网络设备"""
        if nic_config.nic_type == 'nat':
            return self.hs_config.network_nat
        elif nic_config.nic_type == 'pub':
            return self.hs_config.network_pub
        else:
            # 对于其他类型（如bridged），直接返回空或使用nic_devs
            return nic_config.nic_devs

    # 网络静态绑定 #####################################################################
    # :params ip: IP地址
    # :params mac: MAC地址
    # :params uuid: 虚拟机UUID
    # :params flag: True为添加，False为删除
    # ###################################################################################
    def NCStatic(self, ip, mac, uuid, flag=True) -> ZMessage:
        nc_server = NetsManage(
            self.hs_config.i_kuai_addr,
            self.hs_config.i_kuai_user,
            self.hs_config.i_kuai_pass)
        nc_server.login()
        if flag:
            nc_server.add_dhcp(ip, mac, comment=uuid)
            nc_server.add_arp(ip, mac)
        else:
            nc_server.del_dhcp(ip)
            nc_server.del_arp(ip)
        return ZMessage(success=True, action="NCStatic")

    # 端口映射 ##########################################################################
    # :params ip: 内网IP地址
    # :params in_pt: 内网端口
    # :params ex_pt: 外网端口
    # :params flag: True为添加，False为删除
    # ###################################################################################
    def PortsMap(self, ip, in_pt, ex_pt=None,
                 flag=True) -> ZMessage:
        nc_server = NetsManage(
            self.hs_config.i_kuai_addr,
            self.hs_config.i_kuai_user,
            self.hs_config.i_kuai_pass)
        nc_server.login()
        if flag:
            nc_server.add_port(ex_pt, ip, in_pt)
        else:
            nc_server.del_port(ex_pt, ip)
        return ZMessage(success=True, action="PortsMap")

    #####################################################################################
    #####################################################################################
    # 需实现方法 ########################################################################
    #####################################################################################
    #####################################################################################

    # 执行定时任务 ######################################################################
    def Crontabs(self) -> ZMessage:
        """执行定时任务，更新主机和虚拟机状态"""
        pass

    # 宿主机状态 ########################################################################
    def HSStatus(self) -> HWStatus:
        """获取宿主机当前状态"""
        pass

    # 初始宿主机 ########################################################################
    def HSCreate(self) -> ZMessage:
        """初始化宿主机配置"""
        pass

    # 还原宿主机 ########################################################################
    def HSDelete(self) -> ZMessage:
        """还原宿主机到初始状态"""
        pass

    # 读取宿主机 ########################################################################
    def HSLoader(self) -> ZMessage:
        """加载宿主机服务"""
        pass

    # 卸载宿主机 ########################################################################
    def HSUnload(self) -> ZMessage:
        """卸载宿主机服务"""
        pass

    # 创建虚拟机 ########################################################################
    # :params config: 虚拟机配置对象
    # ###################################################################################
    def VMCreate(self, config: VMConfig) -> ZMessage:
        """创建新的虚拟机"""
        pass

    # 配置虚拟机 ########################################################################
    # :params config: 虚拟机配置对象
    #####################################################################################
    def VMUpdate(self, config: VMConfig, old: VMConfig = None) -> ZMessage:
        # 删除旧的网络绑定
        if old is not None:
            for nic_name in old.nic_all:
                nic_data = old.nic_all[nic_name]
                self.NCStatic(nic_data.ip4_addr, nic_data.mac_addr, old.vm_uuid, False)
        # 添加新的网络绑定
        for nic_name in config.nic_all:
            nic_data = config.nic_all[nic_name]
            self.NCStatic(nic_data.ip4_addr, nic_data.mac_addr, config.vm_uuid, True)
        return ZMessage(success=True, action="VMUpdate")

    # 虚拟机状态 ########################################################################
    # :params select: 虚拟机UUID，为空则返回所有虚拟机状态
    # ###################################################################################
    def VMStatus(self, select: str = "") -> dict[str, list[HWStatus]]:
        """获取虚拟机状态列表"""
        pass

    # 删除虚拟机 ########################################################################
    # :params select: 虚拟机UUID
    # ###################################################################################
    def VMDelete(self, select: str) -> ZMessage:
        """删除指定虚拟机"""
        pass

    # 虚拟机电源 ########################################################################
    # :params select: 虚拟机UUID
    # :params p: 电源操作类型
    # ###################################################################################
    def VMPowers(self, select: str, p: VMPowers) -> ZMessage:
        """控制虚拟机电源状态"""
        pass

    # 安装虚拟机 ########################################################################
    # :params select: 虚拟机UUID
    # ###################################################################################
    def VInstall(self, select: str) -> ZMessage:
        """安装虚拟机系统"""
        pass

    # 设置虚拟机密码 ####################################################################
    # :params select: 虚拟机UUID
    # :params password: 密码
    # ###################################################################################
    def Password(self, select: str, password: str) -> ZMessage:
        pass
