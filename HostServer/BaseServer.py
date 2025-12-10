import os
import random
import shutil
import string
from loguru import logger
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from HostModule.NetsManage import NetsManage
from MainObject.Server.HSStatus import HSStatus

from VNCConsole.VNCManager import VNCStart, VProcess


class BaseServer:
    # 初始化 ########################################################################
    # :params config: 物理机配置
    # ###############################################################################
    def __init__(self, config: HSConfig, **kwargs):
        # 宿主机配置 =========================================
        self.hs_config: HSConfig | None = config  # 物理机配置
        # 虚拟机配置 =========================================
        self.vm_saving: dict[str, VMConfig] = {}  # 存储的配置
        self.vm_remote: VProcess | None = None  # 远程连接记录
        # 数据库引用 =========================================
        self.save_data = kwargs.get('db', None)
        # 加载数据 ===========================================
        self.__load__(**kwargs)
        # 日志系统配置 =======================================
        self.LogSetup()

    # 转换字典 ######################################################################
    # :return: 字典
    # ###############################################################################
    def __dict__(self):
        return {
            "hs_config": self.__save__(self.hs_config),
            "vm_saving": {
                string: self.__save__(saving)
                for string, saving in self.vm_saving.items()
            }
        }

    # 转换为字典 ####################################################################
    # :params obj: 需要转换的对象
    # :return: 字典
    # ###############################################################################
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

    # 加载数据 ######################################################################
    # :params kwargs: 关键字参数
    # :return: None
    # ###############################################################################
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # ###############################################################################
    # 内置的方法
    # ###############################################################################

    # 配置日志系统 ##################################################################
    # :return: None
    # ###############################################################################
    def LogSetup(self) -> None:
        if self.hs_config.server_name:
            # 为每个主机创建独立的日志文件
            log_file = f"./DataSaving/log-{self.hs_config.server_name}.log"
            logger.add(
                log_file,
                rotation="10 MB",  # 日志文件达到10MB时轮转
                retention="7 days",  # 保留7天的日志
                compression="zip",  # 压缩旧日志
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
                level="INFO"
            )
            logger.info(f"[{self.hs_config.server_name}] 日志系统已初始化")

    # 清理过期日志 ##################################################################
    # :param days: 保留天数，默认7天
    # ###############################################################################
    def LogClean(self, days: int = 7) -> int:
        if self.save_data and self.hs_config.server_name:
            return self.save_data.del_hs_logger(self.hs_config.server_name, days)
        return 0

    # 添加日志记录 ##################################################################
    # :params log: 日志消息对象
    # ###############################################################################
    def LogStack(self, log: ZMessage):
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

    # 网络检查 ######################################################################
    def NetCheck(self, vm_conf: VMConfig) -> (VMConfig, ZMessage):
        pass

    # 保存主机状态数据 ##############################################################
    # :return: 保存是否成功
    # ###############################################################################

    def host_get(self) -> list[HSStatus]:
        if self.save_data and self.hs_config.server_name:
            return self.save_data.get_hs_status(self.hs_config.server_name)
        return []

    # 保存主机状态数据 ##############################################################
    # :return: 保存是否成功
    # ###############################################################################
    def host_set(self, hs_status: HSStatus) -> bool:
        if self.save_data and self.hs_config.server_name:
            try:
                success = self.save_data.add_hs_status(
                    self.hs_config.server_name, hs_status.status())
                if success:
                    logger.debug(f"[{self.hs_config.server_name}] 主机状态已保存")
                return success
            except Exception as e:
                logger.error(f"[{self.hs_config.server_name}] 保存数据失败: {e}")
                return False
        return False

    # 保存日志到数据库 ##############################################################
    # :return: 保存是否成功
    # ###############################################################################
    def logs_set(self, in_logs) -> bool:
        if self.save_data and self.hs_config.server_name:
            try:
                # 保存VM配置数据
                success = self.save_data.add_hs_logger(
                    self.hs_config.server_name, in_logs)
                if success:
                    logger.debug(f"[{self.hs_config.server_name}] 主机日志已保存")
                return success
            except Exception as e:
                logger.error(f"[{self.hs_config.server_name}] 保存数据失败: {e}")
                return False
        return False

    # 保存数据到数据库 ##############################################################
    # :return: 保存是否成功
    # ###############################################################################
    def data_set(self) -> bool:
        if self.save_data and self.hs_config.server_name:
            try:
                # 保存VM配置数据
                success = self.save_data.set_vm_saving(
                    self.hs_config.server_name, self.vm_saving)
                if success:
                    logger.debug(f"[{self.hs_config.server_name}] 虚拟机配置已保存")
                return success
            except Exception as e:
                logger.error(f"[{self.hs_config.server_name}] 保存数据失败: {e}")
                return False
        return False

    # 从数据库重新加载数据 ##########################################################
    # :return: 加载是否成功
    # ###############################################################################
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
    # 获取虚拟机配置 ########################################################################
    def VMSelect(self, select: str) -> VMConfig | None:
        if select in self.vm_saving:
            return self.vm_saving[select]
        return None

    # 读取远程 ########################################################################
    # :param ip_addr: 远程IP地址
    # :returns: 是否成功
    # ###############################################################################
    def VCLoader(self) -> bool:
        cfg_name = "vnc_" + self.hs_config.server_name
        cfg_full = "DataSaving/" + cfg_name + ".cfg"
        if os.path.exists(cfg_full):
            os.remove(cfg_full)
        tp_remote = VNCStart(self.hs_config.remote_port, cfg_name)
        self.vm_remote = VProcess(tp_remote)
        self.vm_remote.start()
        return True

    # 虚拟机控制台 ########################################################################
    # :params vm_uuid: 虚拟机UUID
    # ###############################################################################
    def VCRemote(self, vm_uuid: str, ip_addr: str = "127.0.0.1") -> str:
        if vm_uuid not in self.vm_saving:
            return ""
        print(f"[DEBUG VCRemote] vm_saving 内容: {self.vm_saving}")
        print(f"[DEBUG VCRemote] {vm_uuid} 的类型: {type(self.vm_saving[vm_uuid])}")
        print(f"[DEBUG VCRemote] {vm_uuid} 的值: {self.vm_saving[vm_uuid]}")
        if self.vm_saving[vm_uuid].vc_port == "":
            print(f"[VCRemote] {vm_uuid} 的 vc_port 为空")
            return ""
        if self.vm_saving[vm_uuid].vc_pass == "":
            print(f"[VCRemote] {vm_uuid} 的 vc_pass 为空")
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

    # 网络静态绑定 ########################################################################
    # :params ip: IP地址
    # :params mac: MAC地址
    # :params uuid: 虚拟机UUID
    # :params flag: True为添加，False为删除
    # ###############################################################################
    def NCStatic(self, ip, mac, uuid, flag=True, dns1=None, dns2=None) -> ZMessage:
        nc_server = NetsManage(
            self.hs_config.i_kuai_addr,
            self.hs_config.i_kuai_user,
            self.hs_config.i_kuai_pass)
        nc_server.login()
        if flag:
            nc_server.add_dhcp(ip, mac, comment=uuid, dns1=dns1, dns2=dns2)
            nc_server.add_arp(ip, mac)
        else:
            nc_server.del_dhcp(ip)
            nc_server.del_arp(ip)
        return ZMessage(success=True, action="NCStatic")

    # 配置虚拟机 ########################################################################
    # :params vm_conf: 虚拟机配置对象
    # ###############################################################################
    def NCUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        # 删除旧的网络绑定
        if vm_last is not None:
            for nic_name in vm_last.nic_all:
                nic_data = vm_last.nic_all[nic_name]
                self.NCStatic(
                    nic_data.ip4_addr, nic_data.mac_addr,
                    vm_last.vm_uuid, False)
        # 添加新的网络绑定
        for nic_name in vm_conf.nic_all:
            nic_data = vm_conf.nic_all[nic_name]
            self.NCStatic(
                nic_data.ip4_addr, nic_data.mac_addr,
                vm_conf.vm_uuid, True)
        return ZMessage(success=True, action="VMUpdate")

    # 端口映射 ########################################################################
    # :params ip: 内网IP地址
    # :params in_pt: 内网端口
    # :params ex_pt: 外网端口
    # :params flag: True为添加，False为删除
    # ###############################################################################
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

    # ###############################################################################
    # 需实现方法
    # ###############################################################################

    # 执行定时任务 ########################################################################
    def Crontabs(self) -> bool:
        hs_status = HSStatus()
        self.host_set(hs_status)
        return True

    # 宿主机状态 ########################################################################
    def HSStatus(self) -> HWStatus:
        status_list = self.host_get()
        if len(status_list) > 0:
            # 将 dict 重新构造成 HWStatus 对象
            raw = status_list[-1]
            hw = HWStatus()
            for k, v in raw.items():
                setattr(hw, k, v)
            return hw
        # 如果没有记录，返回当前状态
        hs_status = HSStatus()
        return hs_status.status()

    # 初始宿主机 ########################################################################
    def HSCreate(self) -> ZMessage:
        hs_result = ZMessage(success=True, action="HSCreate")
        self.logs_set(hs_result)
        return hs_result

    # 还原宿主机 ########################################################################
    def HSDelete(self) -> ZMessage:
        hs_result = ZMessage(success=True, action="HSDelete")
        self.logs_set(hs_result)
        return hs_result

    # 读取宿主机 ########################################################################
    def HSLoader(self) -> ZMessage:
        hs_result = ZMessage(success=True, action="HSLoader", message="宿主机加载成功")
        self.logs_set(hs_result)
        return hs_result

    # 卸载宿主机 ########################################################################
    def HSUnload(self) -> ZMessage:
        hs_result = ZMessage(
            success=True,
            action="HSUnload",
            message="VM Rest Server stopped",
        )
        self.logs_set(hs_result)
        return hs_result

    # 创建虚拟机 ########################################################################
    # :params vm_conf: 虚拟机配置对象
    # ###############################################################################
    def VMCreate(self, vm_conf: VMConfig) -> ZMessage:
        # 只有在所有操作都成功后才保存配置到vm_saving
        self.vm_saving[vm_conf.vm_uuid] = vm_conf
        # 保存到数据库 =====================================================
        self.data_set()
        # 返回结果 =========================================================
        hs_result = ZMessage(
            success=True, action="VMCreate", message="虚拟机创建成功")
        self.logs_set(hs_result)
        return hs_result

    # 配置虚拟机 ########################################################################
    # :params vm_conf: 虚拟机配置对象
    # ###############################################################################
    def VMUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        # 保存到数据库 =========================================================
        self.data_set()
        # 记录日志 =============================================================
        hs_result = ZMessage(
            success=True, action="VMUpdate",
            message=f"虚拟机 {vm_conf.vm_uuid} 配置已更新")
        self.logs_set(hs_result)
        return hs_result

    # 虚拟机状态 ########################################################################
    # :params select: 虚拟机UUID，为空则返回所有虚拟机状态
    # ###############################################################################
    def VMStatus(self, vm_name: str = "") -> dict[str, list[HWStatus]]:
        if self.save_data and self.hs_config.server_name:
            all_status = self.save_data.get_vm_status(self.hs_config.server_name)
            if vm_name:
                return {vm_name: all_status.get(vm_name, [])}
            return all_status
        return {}

    # 删除虚拟机 ########################################################################
    # :params select: 虚拟机UUID
    # ###############################################################################
    def VMDelete(self, vm_name: str) -> ZMessage:
        """删除指定虚拟机"""
        vm_saving = os.path.join(self.hs_config.system_path, vm_name)
        # 删除虚拟文件 =========================================================
        if os.path.exists(vm_saving):
            shutil.rmtree(vm_saving)
        # 删除存储信息 =========================================================
        if vm_name in self.vm_saving:
            del self.vm_saving[vm_name]
        # 保存到数据库 =========================================================
        if self.save_data and self.hs_config.server_name:
            self.save_data.set_vm_saving(
                self.hs_config.server_name, self.vm_saving)
            self.save_data.add_hs_logger(
                self.hs_config.server_name, ZMessage(success=True, action="VMDelete"))

    # 虚拟机电源 ########################################################################
    # :params select: 虚拟机UUID
    # :params p: 电源操作类型
    # ###############################################################################
    def VMPowers(self, vm_name: str, p: VMPowers) -> ZMessage:
        return ZMessage(
            success=False, action="VMPowers",
            message="操作成功完成")

    # 安装虚拟机 ########################################################################
    # :params select: 虚拟机UUID
    # ###############################################################################
    def VInstall(self, vm_conf: VMConfig) -> ZMessage:
        pass

    # 设置虚拟机密码 ########################################################################
    # :params select: 虚拟机UUID
    # :params os_pass: 密码
    # ###############################################################################
    def Password(self, vm_name: str, os_pass: str) -> ZMessage:
        vm_config = self.VMSelect(vm_name)
        if vm_config is None:
            return ZMessage(
                success=False, action="Password",
                message="虚拟机不存在")
        # 使用__dict__()方法创建新配置，避免copy.deepcopy的问题
        ap_config_dict = vm_config.__dict__()
        ap_config = VMConfig(**ap_config_dict)
        ap_config.os_pass = os_pass
        return self.VMUpdate(ap_config, vm_config)
