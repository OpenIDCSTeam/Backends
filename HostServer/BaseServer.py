
import random
import string
from loguru import logger
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from HostModule.NetsManage import NetsManage

from VNCConsole.VNCManager import VNCStart, VProcess


class BaseServer:
    def __init__(self, config: HSConfig, **kwargs):
        # 宿主机配置 =========================================
        self.hs_config: HSConfig | None = config  # 物理机配置
        # 虚拟机配置 =========================================
        self.vm_saving: dict[str, VMConfig] = {}  # 存储的配置
        self.vm_remote: VProcess | None = None  # 远程连接记录
        # 数据库引用 =========================================
        self.save_data = kwargs.get('db', None)  # 数据库操作
        # 加载数据 ===========================================
        self.__load__(**kwargs)
        # 日志系统配置 =======================================
        self.LogSetup()

    # 转换字典 =================
    def __dict__(self):
        return {
            "hs_config": self.__save__(self.hs_config),
            "vm_saving": {
                string: self.__save__(saving)
                for string, saving in self.vm_saving.items()
            }
        }

    # 转换为字典 =================
    # :params obj: 需要转换的对象
    # =================
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

    # 加载数据 =================
    # :params kwargs: 关键字参数
    # =================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # =================
    # 内置的方法 =================
    # =================

    # 配置日志系统 =================
    def LogSetup(self):
        """配置loguru日志系统"""
        if self.hs_config.server_name:
            # 为每个主机创建独立的日志文件
            log_file = f"./logs/{self.hs_config.server_name}.log"
            logger.add(
                log_file,
                rotation="10 MB",  # 日志文件达到10MB时轮转
                retention="7 days",  # 保留7天的日志
                compression="zip",  # 压缩旧日志
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
                level="INFO"
            )
            logger.info(f"[{self.hs_config.server_name}] 日志系统已初始化")

    # 清理过期日志 =================
    # :param days: 保留天数，默认7天
    # =================
    def LogClean(self, days: int = 7):
        """
        清理指定天数之前的日志记录
        :param days: 保留天数，默认7天
        """
        if self.save_data and self.hs_config.server_name:
            return self.save_data.del_hs_logger(self.hs_config.server_name, days)
        return 0

    # 添加日志记录 =================
    # :params log: 日志消息对象
    # =================
    def LogStack(self, log: ZMessage):
        """
        添加日志记录并立即保存到数据库
        :param log: ZMessage日志对象
        """
        # 使用loguru记录日志
        log_level = "ERROR" if not log.success else "INFO"
        log_msg = f"[{self.hs_config.server_name}] {log.actions}: {log.message}"

        if log_level == "ERROR":
            logger.error(log_msg)
        else:
            logger.info(log_msg)

        # 立即保存到数据库
        if self.save_data and self.hs_config.server_name:
            self.save_data.add_hs_logger(self.hs_config.server_name, log)

    # 保存数据到数据库 =================
    # :return: 保存是否成功
    # =================
    def data_set(self) -> bool:
        """
        保存虚拟机配置到数据库
        :return: 保存是否成功
        """
        if self.save_data and self.hs_config.server_name:
            try:
                # 只保存配置数据（vm_saving）
                success = self.save_data.set_vm_saving(self.hs_config.server_name, self.vm_saving)
                if success:
                    logger.debug(f"[{self.hs_config.server_name}] 虚拟机配置已保存到数据库")
                return success
            except Exception as e:
                logger.error(f"[{self.hs_config.server_name}] 保存数据失败: {e}")
                return False
        return False

    # 从数据库重新加载数据 =================
    # :return: 加载是否成功
    # =================
    def data_get(self) -> bool:
        """从数据库重新加载虚拟机配置"""
        if self.save_data and self.hs_config.server_name:
            try:
                # 从数据库获取虚拟机配置
                vm_saving_data = self.save_data.get_vm_saving(self.hs_config.server_name)
                if vm_saving_data:
                    self.vm_saving = {}
                    for vm_uuid, vm_config in vm_saving_data.items():
                        if isinstance(vm_config, dict):
                            self.vm_saving[vm_uuid] = VMConfig(**vm_config)
                        else:
                            self.vm_saving[vm_uuid] = vm_config

                return True
            except Exception as e:
                logger.error(f"[{self.hs_config.server_name}] 从数据库加载数据失败: {e}")
                return False
        return False

    # =================
    # 默认的方法 
    # =================

    # 读取远程 =================
    # :param ip_addr: 远程IP地址
    # :returns: 是否成功
    # =================
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

    # 虚拟机控制台 =================
    # :params vm_uuid: 虚拟机UUID
    # =================
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

    # 网卡网络映射 =================
    # :params nic_config: 网卡配置对象
    # =================
    def _get_network_device(self, nic_config) -> str:
        """根据nic_type和nic_devs获取对应的网络设备"""
        if nic_config.nic_type == 'nat':
            return self.hs_config.network_nat
        elif nic_config.nic_type == 'pub':
            return self.hs_config.network_pub
        else:
            # 对于其他类型（如bridged），直接返回空或使用nic_devs
            return nic_config.nic_devs

    # 网络静态绑定 =================
    # :params ip: IP地址
    # :params mac: MAC地址
    # :params uuid: 虚拟机UUID
    # :params flag: True为添加，False为删除
    # =================
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

    # 端口映射 =================
    # :params ip: 内网IP地址
    # :params in_pt: 内网端口
    # :params ex_pt: 外网端口
    # :params flag: True为添加，False为删除
    # =================
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

    # =================
    # 需实现方法 =================
    # =================

    # 执行定时任务 =================
    def Crontabs(self) -> ZMessage:
        """执行定时任务，更新主机和虚拟机状态"""
        pass

    # 宿主机状态 =================
    def HSStatus(self) -> HWStatus:
        """获取宿主机当前状态"""
        pass

    # 初始宿主机 =================
    def HSCreate(self) -> ZMessage:
        """初始化宿主机配置"""
        pass

    # 还原宿主机 =================
    def HSDelete(self) -> ZMessage:
        """还原宿主机到初始状态"""
        pass

    # 读取宿主机 =================
    def HSLoader(self) -> ZMessage:
        """加载宿主机服务"""
        pass

    # 卸载宿主机 =================
    def HSUnload(self) -> ZMessage:
        """卸载宿主机服务"""
        pass

    # 创建虚拟机 =================
    # :params config: 虚拟机配置对象
    # =================
    def VMCreate(self, config: VMConfig) -> ZMessage:
        """创建新的虚拟机"""
        pass

    # 配置虚拟机 =================
    # :params config: 虚拟机配置对象
    # =================
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

    # 虚拟机状态 =================
    # :params select: 虚拟机UUID，为空则返回所有虚拟机状态
    # =================
    def VMStatus(self, select: str = "") -> dict[str, list[HWStatus]]:
        """获取虚拟机状态列表"""
        pass

    # 删除虚拟机 =================
    # :params select: 虚拟机UUID
    # =================
    def VMDelete(self, select: str) -> ZMessage:
        """删除指定虚拟机"""
        pass

    # 虚拟机电源 =================
    # :params select: 虚拟机UUID
    # :params p: 电源操作类型
    # =================
    def VMPowers(self, select: str, p: VMPowers) -> ZMessage:
        """控制虚拟机电源状态"""
        pass

    # 安装虚拟机 =================
    # :params select: 虚拟机UUID
    # =================
    def VInstall(self, select: str) -> ZMessage:
        """安装虚拟机系统"""
        pass

    # 设置虚拟机密码 =================
    # :params select: 虚拟机UUID
    # :params password: 密码
    # =================
    def Password(self, select: str, password: str) -> ZMessage:
        pass
