import os
import sys
import platform
import subprocess
import datetime
import random
import shutil
import string
from copy import deepcopy
from random import randint
from loguru import logger

from HostModule.HttpManage import HttpManage
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.IMConfig import IMConfig
from MainObject.Config.PortData import PortData
from MainObject.Config.SDConfig import SDConfig
from MainObject.Config.VMBackup import VMBackup
from MainObject.Config.VMPowers import VMPowers
from MainObject.Config.WebProxy import WebProxy
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from HostModule.NetsManage import NetsManage
from MainObject.Config.IPConfig import IPConfig
from MainObject.Server.HSStatus import HSStatus

from VNCConsole.VNCManager import VNCStart, VProcess


class BasicServer:
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
    def __save__(self):
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
            return [BasicServer.__save__(item) for item in obj]
        if hasattr(obj, '__save__'):
            if callable(getattr(obj, '__save__')):
                return obj.__save__()
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

    # 获取虚拟机配置 ################################################################
    def VMSelect(self, select: str) -> VMConfig | None:
        if select in self.vm_saving:
            return self.vm_saving[select]
        return None

    # 读取远程 ######################################################################
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

    # 虚拟机控制台 ##################################################################
    # :params vm_uuid: 虚拟机UUID
    # ###############################################################################
    def VCRemote(self, vm_uuid: str, ip_addr: str = "127.0.0.1") -> str:
        if vm_uuid not in self.vm_saving:
            return ""
        logger.debug(f"[DEBUG VCRemote] vm_saving 内容: {self.vm_saving}")
        logger.debug(f"[DEBUG VCRemote] {vm_uuid} 的类型: {type(self.vm_saving[vm_uuid])}")
        logger.debug(f"[DEBUG VCRemote] {vm_uuid} 的值: {self.vm_saving[vm_uuid]}")
        if self.vm_saving[vm_uuid].vc_port == "":
            logger.warning(f"[VCRemote] {vm_uuid} 的 vc_port 为空")
            return ""
        if self.vm_saving[vm_uuid].vc_pass == "":
            logger.warning(f"[VCRemote] {vm_uuid} 的 vc_pass 为空")
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

    # 获取当前主机所有虚拟机已分配的IP地址 ##########################################
    # :returns: IP地址列表
    # ###############################################################################
    def IPGrants(self) -> set:
        allocated = set()
        for vm_uuid, vm_config in self.vm_saving.items():
            for nic_name, nic_config in vm_config.nic_all.items():
                if nic_config.ip4_addr:
                    allocated.add(nic_config.ip4_addr.strip())
                if nic_config.ip6_addr:
                    allocated.add(nic_config.ip6_addr.strip())
        return allocated

    # 网络检查 ######################################################################
    def NetCheck(self, vm_conf: VMConfig) -> (VMConfig, ZMessage):
        """
        检查并自动分配虚拟机网卡IP地址
        :param vm_conf: 虚拟机配置对象
        :return: (更新后的虚拟机配置, 操作结果消息)
        """
        ip_config = IPConfig(self.hs_config.ipaddr_maps, self.hs_config.ipaddr_dnss)
        allocated_ips = self.IPGrants()
        return ip_config.check_and_allocate(vm_conf, allocated_ips)

    # 网络静态绑定 ##################################################################
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
            nc_server.add_dhcp(ip, mac, comment=uuid, lan_dns1=dns1, lan_dns2=dns2)
            nc_server.add_arps(ip, mac)
        else:
            nc_server.del_dhcp(ip)
            nc_server.del_arps(ip)
        return ZMessage(success=True, action="NCStatic")

    # 网络动态绑定 ##################################################################
    def NCCreate(self, vm_conf: VMConfig, flag=True) -> ZMessage:
        for nic_name, nic_conf in vm_conf.nic_all.items():
            try:
                logger.info(f"[API] 绑定静态IP: {nic_conf.ip4_addr} -> {nic_conf.mac_addr}")
                nc_result = self.NCStatic(
                    nic_conf.ip4_addr,
                    nic_conf.mac_addr,
                    vm_conf.vm_uuid,
                    flag=flag,
                    dns1=self.hs_config.ipaddr_dnss[0],
                    dns2=self.hs_config.ipaddr_dnss[1]
                )
                if nc_result.success:
                    logger.success(f"[API] 静态IP绑定成功: {nic_conf.ip4_addr}")
                else:
                    logger.warning(f"[API] 静态IP绑定失败: {nc_result.message}")
                return nc_result
            except Exception as e:
                logger.error(f"[API] 静态IP绑定异常: {str(e)}")
                return ZMessage(success=False, action="NCStatic", message=str(e))
        return ZMessage(success=False, action="NCStatic", message="No IP address found")

    # 配置虚拟机 ####################################################################
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
                vm_conf.vm_uuid, True,
                nic_data.dns_addr[0] if len(nic_data.dns_addr) > 0 else "119.29.29.29",
                nic_data.dns_addr[1] if len(nic_data.dns_addr) > 1 else "223.5.5.5"
            )
        return ZMessage(success=True, action="VMUpdate")

    # 端口映射 ######################################################################
    # :params map_info: 端口映射信息
    # ###############################################################################
    def PortsMap(self, map_info: PortData, flag=True) -> ZMessage:
        nc_server = NetsManage(
            self.hs_config.i_kuai_addr,
            self.hs_config.i_kuai_user,
            self.hs_config.i_kuai_pass)
        nc_server.login()
        port_result = nc_server.get_port()
        # 处理get_port返回值，提取端口列表
        wan_list = []
        if port_result and isinstance(port_result, dict):
            data = port_result.get('Data', {})
            if isinstance(data, dict):
                now_list = data.get('data', [])
                if isinstance(now_list, list):
                    wan_list = [int(i.get("wan_port", 0)) for i in now_list if isinstance(i, dict)]

        # 如果wan_port为0，自动分配一个未使用的端口
        if map_info.wan_port == 0:
            wan_port = randint(self.hs_config.ports_start, self.hs_config.ports_close)
            while wan_port in wan_list:
                wan_port = randint(self.hs_config.ports_start, self.hs_config.ports_close)
            map_info.wan_port = wan_port
        else:
            if map_info.wan_port in wan_list:
                return ZMessage(
                    success=False, action="PortsMap", message="端口已被占用")
        if flag:
            result = nc_server.add_port(map_info.wan_port, map_info.lan_port,
                                        map_info.lan_addr, map_info.nat_tips)
        else:
            result = nc_server.del_port(map_info.lan_port, map_info.lan_addr)
        hs_result = ZMessage(
            success=result, action="ProxyMap",
            messages=str(map_info.wan_port) + "端口%s操作%s" % (
                "添加" if flag else "删除",
                "成功" if result else "失败"))
        self.data_set()
        return hs_result

    # 反向代理 ######################################################################
    # :params ip: 内网IP地址
    # :params in_pt: 内网端口
    # :params ex_pt: 外网端口
    # :params flag: True为添加，False为删除
    # ###############################################################################
    def ProxyMap(self, web_info: WebProxy, proxys: HttpManage, flag=True) -> ZMessage:

        if flag:
            result = proxys.proxy_add((web_info.lan_port, web_info.lan_addr),
                                      web_info.web_addr, web_info.is_https)
        else:
            result = proxys.proxy_del(web_info.web_addr)
        self.data_set()
        hs_result = ZMessage(success=result, action="ProxyMap",
                             messages=web_info.web_addr + "%s操作%s" % (
                                 "添加" if flag else "删除",
                                 "成功" if result else "失败"))
        self.logs_set(hs_result)
        return hs_result

    # ###############################################################################
    # 需实现方法
    # ###############################################################################

    # 执行定时任务 ##################################################################
    def Crontabs(self) -> bool:
        hs_status = HSStatus()
        self.host_set(hs_status)
        return True

    # 宿主机状态 ####################################################################
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

    # 初始宿主机 ####################################################################
    def HSCreate(self) -> ZMessage:
        hs_result = ZMessage(success=True, action="HSCreate")
        self.logs_set(hs_result)
        return hs_result

    # 还原宿主机 ####################################################################
    def HSDelete(self) -> ZMessage:
        hs_result = ZMessage(success=True, action="HSDelete")
        self.logs_set(hs_result)
        return hs_result

    # 读取宿主机 ####################################################################
    def HSLoader(self) -> ZMessage:
        hs_result = ZMessage(
            success=True,
            action="HSLoader",
            message="宿主机加载成功")
        self.logs_set(hs_result)
        return hs_result

    # 卸载宿主机 ####################################################################
    def HSUnload(self) -> ZMessage:
        hs_result = ZMessage(
            success=True,
            action="HSUnload",
            message="VM Rest Server stopped",
        )
        self.logs_set(hs_result)
        return hs_result

    # 虚拟机扫描 ####################################################################
    def VScanner(self) -> ZMessage:
        pass

    # 创建虚拟机 ####################################################################
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

    # 配置虚拟机 ####################################################################
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

    # 虚拟机状态 ####################################################################
    # :params select: 虚拟机UUID，为空则返回所有虚拟机状态
    # ###############################################################################
    def VMStatus(self, vm_name: str = "") -> dict[str, list[HWStatus]]:
        if self.save_data and self.hs_config.server_name:
            all_status = self.save_data.get_vm_status(self.hs_config.server_name)
            if vm_name:
                return {vm_name: all_status.get(vm_name, [])}
            return all_status
        return {}

    # 删除虚拟机 ####################################################################
    # :params select: 虚拟机UUID
    # ###############################################################################
    def VMDelete(self, vm_name: str) -> ZMessage:
        vm_saving = os.path.join(self.hs_config.system_path, vm_name)
        # 删除虚拟文件 ==============================================================
        if os.path.exists(vm_saving):
            shutil.rmtree(vm_saving)
        # 删除存储信息 ==============================================================
        if vm_name in self.vm_saving:
            del self.vm_saving[vm_name]
        # 保存到数据库 ==============================================================
        self.data_set()
        hs_result = ZMessage(success=True, action="VMDelete")
        self.logs_set(hs_result)
        return hs_result

    # 虚拟机电源 ####################################################################
    # :params select: 虚拟机UUID
    # :params p: 电源操作类型
    # ###############################################################################
    def VMPowers(self, vm_name: str, p: VMPowers) -> ZMessage:
        return ZMessage(
            success=False, action="VMPowers",
            message="操作成功完成")

    # 安装虚拟机 ####################################################################
    # :params select: 虚拟机UUID
    # ###############################################################################
    def VInstall(self, vm_conf: VMConfig) -> ZMessage:
        pass

    # 设置虚拟机密码 ################################################################
    # :params select: 虚拟机UUID
    # :params os_pass: 密码
    # ###############################################################################
    def Password(self, vm_name: str, os_pass: str) -> ZMessage:
        vm_config = self.VMSelect(vm_name)
        if vm_config is None:
            return ZMessage(
                success=False, action="Password",
                message="虚拟机不存在")
        # 使用__save__()方法创建新配置，避免copy.deepcopy的问题
        ap_config_dict = vm_config.__save__()
        ap_config = VMConfig(**ap_config_dict)
        ap_config.os_pass = os_pass
        return self.VMUpdate(ap_config, vm_config)

    # 获取7z可执行文件路径 ##########################################################
    # :return: 7z可执行文件的完整路径
    # ###############################################################################
    def get_path(self) -> str:
        """根据操作系统返回对应的7z可执行文件路径"""
        system = platform.system().lower()
        if system == "windows":
            return os.path.join("HostConfig", "7zipwinx64", "7z.exe")
        elif system == "linux":
            return os.path.join("HostConfig", "7ziplinx64", "7zz")
        elif system == "darwin":  # macOS
            return os.path.join("HostConfig", "7zipmacu2b", "7zz")
        else:
            raise OSError(f"不支持的操作系统: {system}")

    # 备份虚拟机 ####################################################################
    # :params vm_name: 虚拟机UUID
    # :params vm_tips: 备份的说明
    # ###############################################################################
    def VMBackup(self, vm_name: str, vm_tips: str) -> ZMessage:
        bak_time = datetime.datetime.now()
        bak_name = vm_name + "-" + bak_time.strftime("%Y%m%d%H%M%S") + ".7z"
        org_path = os.path.join(self.hs_config.system_path, vm_name)
        zip_path = os.path.join(self.hs_config.backup_path, bak_name)
        try:
            self.VMPowers(vm_name, VMPowers.H_CLOSE)

            # 获取7z可执行文件路径
            seven_zip = self.get_path()
            if not os.path.exists(seven_zip):
                raise FileNotFoundError(f"7z可执行文件不存在: {seven_zip}")

            # 使用subprocess调用7z进行压缩
            # 命令格式: 7z a -t7z <压缩包路径> <源目录>
            cmd = [seven_zip, "a", "-t7z", zip_path, org_path]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"7z压缩失败: {result.stderr}")

            self.VMPowers(vm_name, VMPowers.S_START)
            self.vm_saving[vm_name].backups.append(
                VMBackup(
                    backup_name=bak_name,
                    backup_time=bak_time,
                    backup_tips=vm_tips
                )
            )
            self.data_set()
            return ZMessage(success=True, action="VMBackup")
        except Exception as e:
            self.VMPowers(vm_name, VMPowers.S_START)
            return ZMessage(success=False, action="VMBackup", message=str(e))

    # 恢复虚拟机 ####################################################################
    # :params vm_name: 虚拟机UUID
    # :params vm_back: 备份文件名
    # ###############################################################################
    def Restores(self, vm_name: str, vm_back: str) -> ZMessage:
        org_path = os.path.join(self.hs_config.system_path, vm_name)
        zip_path = os.path.join(self.hs_config.backup_path, vm_back)
        try:
            self.VMPowers(vm_name, VMPowers.H_CLOSE)
            shutil.rmtree(org_path)
            os.makedirs(org_path)

            # 获取7z可执行文件路径
            seven_zip = self.get_path()
            if not os.path.exists(seven_zip):
                raise FileNotFoundError(f"7z可执行文件不存在: {seven_zip}")

            # 使用subprocess调用7z进行解压
            # 命令格式: 7z x <压缩包路径> -o<输出目录> -y
            cmd = [seven_zip, "x", zip_path, f"-o{self.hs_config.system_path}", "-y"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"7z解压失败: {result.stderr}")

            self.VMPowers(vm_name, VMPowers.S_START)
            return ZMessage(success=True, action="Restores")
        except Exception as e:
            self.VMPowers(vm_name, VMPowers.S_START)
            return ZMessage(success=False, action="Restores", message=str(e))

    # VM镜像挂载 ####################################################################
    # :params vm_name: 虚拟机UUID
    # :params vm_imgs: 镜像的配置
    # :params in_flag: 挂载或卸载
    # ###############################################################################
    def HDDMount(self, vm_name: str, vm_imgs: SDConfig, in_flag=True) -> ZMessage:
        if vm_name not in self.vm_saving:
            return ZMessage(
                success=False, action="HDDMount", message="虚拟机不存在")
        old_conf = deepcopy(self.vm_saving[vm_name])
        # 关闭虚拟机 ===============================================================
        self.VMPowers(vm_name, VMPowers.H_CLOSE)
        if in_flag:  # 挂载磁盘 ====================================================
            vm_imgs.hdd_flag = 1
            self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name] = vm_imgs
        else:  # 卸载磁盘 ==========================================================
            if vm_imgs.hdd_name not in self.vm_saving[vm_name].hdd_all:
                self.VMPowers(vm_name, VMPowers.S_START)
                return ZMessage(
                    success=False, action="HDDMount", message="磁盘不存在")
            self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name].hdd_flag = 0
        # 保存配置 =================================================================
        self.VMUpdate(self.vm_saving[vm_name], old_conf)
        self.data_set()
        action_text = "挂载" if in_flag else "卸载"
        return ZMessage(
            success=True,
            action="HDDMount",
            message=f"磁盘{action_text}成功")

    # ISO镜像挂载 ###################################################################
    # :params vm_name: 虚拟机UUID
    # :params vm_imgs: 镜像的配置
    # :params in_flag: 挂载或卸载
    # ###############################################################################
    def ISOMount(self, vm_name: str, vm_imgs: IMConfig, in_flag=True) -> ZMessage:
        if vm_name not in self.vm_saving:
            return ZMessage(
                success=False, action="ISOMount", message="虚拟机不存在")

        old_conf = deepcopy(self.vm_saving[vm_name])
        # 关闭虚拟机
        logger.info(f"[{self.hs_config.server_name}] 准备{'挂载' if in_flag else '卸载'}ISO: {vm_imgs.iso_name}")
        self.VMPowers(vm_name, VMPowers.H_CLOSE)

        if in_flag:  # 挂载ISO =================================================
            # 使用iso_file作为文件名检查
            iso_full = os.path.join(self.hs_config.images_path, vm_imgs.iso_file)
            if not os.path.exists(iso_full):
                self.VMPowers(vm_name, VMPowers.S_START)
                logger.error(f"[{self.hs_config.server_name}] ISO文件不存在: {iso_full}")
                return ZMessage(
                    success=False, action="ISOMount", message="ISO镜像文件不存在")

            # 检查挂载名称是否已存在
            if vm_imgs.iso_name in self.vm_saving[vm_name].iso_all:
                self.VMPowers(vm_name, VMPowers.S_START)
                return ZMessage(
                    success=False, action="ISOMount", message="挂载名称已存在")

            # 使用iso_name作为key存储
            self.vm_saving[vm_name].iso_all[vm_imgs.iso_name] = vm_imgs
            logger.info(f"[{self.hs_config.server_name}] ISO挂载成功: {vm_imgs.iso_name} -> {vm_imgs.iso_file}")
        else:
            # 卸载ISO ==========================================================
            if vm_imgs.iso_name not in self.vm_saving[vm_name].iso_all:
                self.VMPowers(vm_name, VMPowers.S_START)
                return ZMessage(
                    success=False, action="ISOMount", message="ISO镜像不存在")

            # 从字典中移除
            del self.vm_saving[vm_name].iso_all[vm_imgs.iso_name]
            logger.info(f"[{self.hs_config.server_name}] ISO卸载成功: {vm_imgs.iso_name}")

        # 保存配置 =============================================================
        self.VMUpdate(self.vm_saving[vm_name], old_conf)
        self.data_set()

        # 启动虚拟机
        self.VMPowers(vm_name, VMPowers.S_START)

        action_text = "挂载" if in_flag else "卸载"
        return ZMessage(
            success=True,
            action="ISOMount",
            message=f"ISO镜像{action_text}成功")

    # 移交所有权 ####################################################################
    # :params vm_name: 虚拟机UUID
    # :params vm_imgs: 镜像的配置
    # :params ex_name: 新虚拟机名
    # ###############################################################################
    def HDDTrans(self, vm_name: str, vm_imgs: SDConfig, ex_name: str) -> ZMessage:
        # 检查源虚拟机是否存在
        if vm_name not in self.vm_saving:
            return ZMessage(
                success=False, action="HDDTrans", message="源虚拟机不存在")

        # 检查目标虚拟机是否存在
        if ex_name not in self.vm_saving:
            return ZMessage(
                success=False, action="HDDTrans", message="目标虚拟机不存在")

        # 检查磁盘是否存在
        if vm_imgs.hdd_name not in self.vm_saving[vm_name].hdd_all:
            return ZMessage(
                success=False, action="HDDTrans", message="磁盘不存在")

        # 检查磁盘是否已挂载
        hdd_config = self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name]
        hdd_flag = getattr(hdd_config, 'hdd_flag', 0)
        if hdd_flag == 1:
            return ZMessage(
                success=False, action="HDDTrans",
                message="磁盘已挂载，无法移交。请先卸载磁盘后再进行移交操作")

        # 执行移交操作
        old_path = os.path.join(self.hs_config.system_path, vm_name)
        new_path = os.path.join(self.hs_config.system_path, ex_name)
        old_file = os.path.join(old_path, vm_name + "-" + vm_imgs.hdd_name + ".vmdk")
        new_file = os.path.join(new_path, ex_name + "-" + vm_imgs.hdd_name + ".vmdk")

        try:
            # 从源虚拟机移除磁盘配置
            self.vm_saving[vm_name].hdd_all.pop(vm_imgs.hdd_name)

            # 移动物理文件
            if os.path.exists(old_file):
                shutil.move(old_file, new_file)
                logger.info(f"[{self.hs_config.server_name}] 磁盘文件已从 {old_file} 移动到 {new_file}")
            else:
                logger.warning(f"[{self.hs_config.server_name}] 源磁盘文件 {old_file} 不存在")

            # 添加到目标虚拟机（保持未挂载状态）
            vm_imgs.hdd_flag = 0
            self.vm_saving[ex_name].hdd_all[vm_imgs.hdd_name] = vm_imgs

            # 保存配置
            self.data_set()

            logger.info(f"[{self.hs_config.server_name}] 磁盘 {vm_imgs.hdd_name} 已从虚拟机 {vm_name} 移交到 {ex_name}")
            return ZMessage(success=True, action="HDDTrans", message="磁盘移交成功")
        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] 磁盘移交失败: {str(e)}")
            return ZMessage(success=False, action="HDDTrans", message=str(e))

    # 移除备份 ######################################################################
    def RMBackup(self, vm_back: str) -> ZMessage:
        bak_path = os.path.join(self.hs_config.backup_path, vm_back)
        if not os.path.exists(bak_path):
            return ZMessage(
                success=False, action="RMBackup",
                message="备份文件不存在")
        os.remove(bak_path)
        return ZMessage(
            success=True, action="RMBackup",
            message="备份文件已删除")

    # 加载备份 ######################################################################
    def LDBackup(self, vm_back: str = "") -> ZMessage:
        for vm_name in self.vm_saving:
            self.vm_saving[vm_name].backups = []
        bal_nums = 0
        for bak_name in os.listdir(self.hs_config.backup_path):
            # 只处理.7z备份文件
            if not bak_name.endswith(".7z"):
                continue
            bal_nums += 1
            # 去掉.7z后缀再解析
            name_without_ext = bak_name[:-3]  # 移除.7z
            parts = name_without_ext.split("-")
            if len(parts) < 2:
                logger.warning(f"备份文件名格式不正确: {bak_name}")
                continue
            vm_name = parts[0]
            vm_time = parts[1]
            if vm_name in self.vm_saving:
                try:
                    self.vm_saving[vm_name].backups.append(
                        VMBackup(
                            backup_name=bak_name,
                            backup_time=datetime.datetime.strptime(
                                vm_time, "%Y%m%d%H%M%S")
                        )
                    )
                except ValueError as e:
                    logger.error(f"解析备份时间失败 {bak_name}: {e}")
                    continue
        self.data_set()
        return ZMessage(
            success=True,
            action="LDBackup",
            message=f"{bal_nums}个备份文件已加载")

    # 移除磁盘 ######################################################################
    def RMMounts(self, vm_name: str, vm_imgs: str) -> ZMessage:
        if vm_name not in self.vm_saving:
            return ZMessage(
                success=False, action="RMMounts", message="虚拟机不存在")
        if vm_imgs not in self.vm_saving[vm_name].hdd_all:
            return ZMessage(
                success=False, action="RMMounts", message="虚拟盘不存在")
        # 获取虚拟磁盘数据 ===============================================
        hd_data = self.vm_saving[vm_name].hdd_all[vm_imgs]
        hd_path = os.path.join(
            self.hs_config.system_path, vm_name,
            vm_name + "-" + hd_data.hdd_name + ".vmdk")
        # 卸载虚拟磁盘 ===================================================
        if hd_data.hdd_flag == 1:
            self.HDDMount(vm_name, hd_data, False)
        # 从配置中移除 ===================================================
        self.vm_saving[vm_name].hdd_all.pop(vm_imgs)
        self.data_set()
        # 删除物理文件 ===================================================
        if os.path.exists(hd_path):
            os.remove(hd_path)
        # 返回结果 =======================================================
        return ZMessage(
            success=True, action="RMMounts",
            message="磁盘删除成功")

    # 查找显卡 ######################################################################
    def GPUShows(self) -> dict[str, str]:
        return {}

    # 转移用户 ######################################################################
    def Transfer(self, vm_name: str, new_owner: str, keep_access: bool = False) -> ZMessage:
        """
        移交虚拟机所有权
        
        :param vm_name: 虚拟机UUID
        :param new_owner: 新所有者用户名
        :param keep_access: 是否保留原所有者的访问权限
        :return: 操作结果消息
        """
        # 检查虚拟机是否存在
        if vm_name not in self.vm_saving:
            return ZMessage(
                success=False, 
                action="Transfer", 
                message="虚拟机不存在"
            )
        
        vm_config = self.vm_saving[vm_name]
        owners = vm_config.own_all.copy()

        # 检查新所有者是否已经在所有者列表中
        if new_owner == owners[0]:
            return ZMessage(
                success=False,
                action="Transfer", 
                message="用户已经是虚拟机所有者"
            )
        
        # 获取当前主所有者
        current_primary_owner = owners[0]
        
        # 移交所有权：将新所有者移到第一位
        owners.remove(new_owner) if new_owner in owners else None
        owners.insert(0, new_owner)
        
        # 如果不保留原所有者权限，从列表中移除原主所有者
        if not keep_access and current_primary_owner in owners:
            owners.remove(current_primary_owner)
        
        # 更新所有者列表
        vm_config.own_all = owners
        
        # 保存配置
        self.data_set()
        
        logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} 所有权从 {current_primary_owner} 移交给 {new_owner}，保留权限: {keep_access}")
        
        return ZMessage(
            success=True,
            action="Transfer",
            message=f"虚拟机所有权已成功移交给 {new_owner}"
        )
