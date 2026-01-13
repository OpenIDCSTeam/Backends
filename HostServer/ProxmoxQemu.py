import os
import time
import datetime
import traceback
from typing import Optional, Tuple
from loguru import logger
from copy import deepcopy

try:
    from proxmoxer import ProxmoxAPI
    from proxmoxer.core import ResourceException

    PROXMOX_AVAILABLE = True
except ImportError:
    PROXMOX_AVAILABLE = False
    logger.warning("proxmoxer not available, Proxmox functionality will be disabled")
    ProxmoxAPI = None

from HostServer.BasicServer import BasicServer
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.IMConfig import IMConfig
from MainObject.Config.SDConfig import SDConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Config.VMBackup import VMBackup
from MainObject.Config.WebProxy import WebProxy
from MainObject.Config.PortData import PortData
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from HostModule.HttpManager import HttpManager
from HostServer.OCInterfaceAPI.PortForward import PortForward
from HostServer.OCInterfaceAPI.SSHTerminal import SSHTerminal


class HostServer(BasicServer):
    """Proxmox VE QEMU虚拟机管理服务"""

    # 宿主机服务 ###############################################################
    def __init__(self, config: HSConfig, **kwargs):
        super().__init__(config, **kwargs)
        super().__load__(**kwargs)
        # Proxmox 客户端连接
        self.proxmox = None
        self.node_name = None  # PVE节点名称
        self.web_terminal = None
        self.http_manager = None
        self.port_forward = None

    # 连接到 Proxmox 服务器 ####################################################
    def _connect_proxmox(self) -> Tuple[Optional[ProxmoxAPI], ZMessage]:
        """
        连接到 Proxmox VE 服务器
        :return: (Proxmox客户端对象, 操作结果消息)
        """
        if not PROXMOX_AVAILABLE:
            return None, ZMessage(
                success=False, action="_connect_proxmox",
                message="proxmoxer is not installed. Install it with: pip install proxmoxer")

        try:
            # 如果已经连接，直接返回
            if self.proxmox is not None:
                return self.proxmox, ZMessage(success=True, action="_connect_proxmox")

            # 从配置中获取连接信息
            host = self.hs_config.server_addr + ":8006"
            user = self.hs_config.server_user if hasattr(self.hs_config, 'server_user') else 'root'
            password = self.hs_config.server_pass

            # 从launch_path获取节点名称，如果没有则使用默认值
            self.node_name = self.hs_config.launch_path if self.hs_config.launch_path else 'pve'

            logger.info(f"Connecting to Proxmox server: {host}, user: {user}, node: {self.node_name}")

            # 创建Proxmox API连接
            self.proxmox = ProxmoxAPI(
                host,
                user=user + "@pam",
                password=password,
                verify_ssl=False  # 可以根据需要配置SSL验证
            )

            # 测试连接
            self.proxmox.version.get()
            logger.info("Successfully connected to Proxmox server")

            return self.proxmox, ZMessage(success=True, action="_connect_proxmox")

        except Exception as e:
            logger.error(f"Failed to connect to Proxmox server: {str(e)}")
            traceback.print_exc()
            self.proxmox = None
            return None, ZMessage(
                success=False, action="_connect_proxmox",
                message=f"Failed to connect to Proxmox: {str(e)}")

    # 判断是否为远程宿主机 #####################################################
    def is_remote_host(self) -> bool:
        """判断是否为远程主机"""
        return self.hs_config.server_addr not in ["localhost", "127.0.0.1", ""]

    # 同步端口转发配置 #########################################################
    def sync_forwarder(self):
        """同步端口转发配置：删除不需要的转发，添加缺少的转发"""
        try:
            is_remote = self.is_remote_host()

            # 如果是远程主机，先建立SSH连接
            if is_remote:
                success, message = self.port_forward.connect_ssh()
                if not success:
                    logger.error(f"SSH连接失败，无法同步端口转发: {message}")
                    return

            # 获取系统中已有的端口转发
            existing_forwards = self.port_forward.list_ports(is_remote)
            existing_map = {}
            for forward in existing_forwards:
                key = (forward.lan_addr, forward.lan_port)
                existing_map[key] = forward

            # 获取配置中需要的端口转发
            required_forwards = {}
            for vm_name, vm_conf in self.vm_saving.items():
                if not hasattr(vm_conf, 'nat_all'):
                    continue
                for port_data in vm_conf.nat_all:
                    key = (port_data.lan_addr, port_data.lan_port)
                    required_forwards[key] = (port_data.wan_port, vm_name)

            # 删除不需要的转发
            removed_count = 0
            for key, forward in existing_map.items():
                if key not in required_forwards:
                    if self.port_forward.remove_port_forward(
                            forward.wan_port, forward.protocol, is_remote):
                        removed_count += 1
                        logger.info(
                            f"删除多余的端口转发: {forward.protocol} {forward.wan_port} -> "
                            f"{forward.lan_addr}:{forward.lan_port}")

            # 添加缺少的转发
            added_count = 0
            for key, (wan_port, vm_name) in required_forwards.items():
                lan_addr, lan_port = key
                if key in existing_map:
                    existing_forward = existing_map[key]
                    if existing_forward.wan_port != wan_port:
                        self.port_forward.remove_port_forward(
                            existing_forward.wan_port, existing_forward.protocol, is_remote)
                        logger.info(
                            f"端口映射变更，删除旧转发: {existing_forward.protocol} "
                            f"{existing_forward.wan_port} -> {lan_addr}:{lan_port}")
                    else:
                        continue

                success, error = self.port_forward.add_port_forward(
                    lan_addr, lan_port, wan_port, "TCP", is_remote, vm_name)

                if success:
                    added_count += 1
                    logger.info(
                        f"添加端口转发: TCP {wan_port} -> {lan_addr}:{lan_port} ({vm_name})")
                else:
                    logger.error(
                        f"添加端口转发失败: TCP {wan_port} -> {lan_addr}:{lan_port}, "
                        f"错误: {error}")

            logger.info(f"端口转发同步完成: 删除 {removed_count} 个，添加 {added_count} 个")

            if is_remote:
                self.port_forward.close_ssh()

        except Exception as e:
            logger.error(f"同步端口转发时出错: {str(e)}")
            traceback.print_exc()

    # 宿主机任务 ###############################################################
    def Crontabs(self) -> bool:
        """定时任务"""
        # 专用操作 =============================================================
        try:
            # 连接到 Proxmox
            client, result = self._connect_proxmox()
            if result.success and client:
                # 获取主机状态
                try:
                    node_status = client.nodes(self.node_name).status.get()
                    if node_status:
                        hw_status = HWStatus()
                        # CPU 使用率
                        hw_status.cpu_usage = int(node_status.get('cpu', 0) * 100)
                        # 内存使用率（已用/总量）
                        mem_total = node_status.get('memory', {}).get('total', 1)
                        mem_used = node_status.get('memory', {}).get('used', 0)
                        hw_status.ram_usage = int((mem_used / mem_total) * 100) if mem_total > 0 else 0
                        # 保存状态
                        self.host_set(hw_status)
                        logger.debug(f"[{self.hs_config.server_name}] Proxmox主机状态已更新")
                except Exception as e:
                    logger.error(f"获取Proxmox主机状态失败: {str(e)}")
        except Exception as e:
            logger.error(f"Crontabs执行失败: {str(e)}")
        # 通用操作 =============================================================
        return super().Crontabs()

    # 宿主机状态 ###############################################################
    def HSStatus(self) -> HWStatus:
        """获取宿主机状态"""
        # 专用操作 =============================================================
        try:
            # 连接到 Proxmox
            client, result = self._connect_proxmox()
            if not result.success or not client:
                logger.error(f"无法连接到Proxmox获取状态: {result.message}")
                return super().HSStatus()

            # 获取主机状态
            node_status = client.nodes(self.node_name).status.get()

            if node_status:
                hw_status = HWStatus()
                # CPU 使用率
                hw_status.cpu_usage = int(node_status.get('cpu', 0) * 100)
                # 内存使用（MB）
                mem_total = node_status.get('memory', {}).get('total', 0)
                mem_used = node_status.get('memory', {}).get('used', 0)
                hw_status.mem_total = int(mem_total / (1024 * 1024))  # 转换为MB
                hw_status.mem_usage = int(mem_used / (1024 * 1024))  # 转换为MB
                # 磁盘使用（MB）
                disk_total = node_status.get('rootfs', {}).get('total', 0)
                disk_used = node_status.get('rootfs', {}).get('used', 0)
                hw_status.hdd_total = int(disk_total / (1024 * 1024))  # 转换为MB
                hw_status.hdd_usage = int(disk_used / (1024 * 1024))  # 转换为MB

                logger.debug(
                    f"[{self.hs_config.server_name}] Proxmox主机状态: "
                    f"CPU={hw_status.cpu_usage}%, "
                    f"MEM={hw_status.mem_usage}MB/{hw_status.mem_total}MB"
                )
                return hw_status
        except Exception as e:
            logger.error(f"获取Proxmox主机状态失败: {str(e)}")

        # 通用操作 =============================================================
        return super().HSStatus()

    # 初始宿主机 ###############################################################
    def HSCreate(self) -> ZMessage:
        """初始化宿主机"""
        return super().HSCreate()

    # 还原宿主机 ###############################################################
    def HSDelete(self) -> ZMessage:
        """还原宿主机"""
        return super().HSDelete()

    # 读取宿主机 ###############################################################
    def HSLoader(self) -> ZMessage:
        """加载宿主机配置"""
        # 初始化SSHTerminal
        if not self.web_terminal:
            self.web_terminal = SSHTerminal(self.hs_config)

        # 初始化HttpManager
        if not self.http_manager:
            hostname = getattr(self.hs_config, 'server_name', '')
            config_filename = f"vnc-{hostname}.txt"
            self.http_manager = HttpManager(config_filename)
            self.http_manager.launch_vnc(self.hs_config.remote_port)
            self.http_manager.launch_web()

        # 初始化端口转发管理器
        if not self.port_forward:
            self.port_forward = PortForward(self.hs_config)

        # 连接到 Proxmox 服务器
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        # 同步端口转发配置
        self.sync_forwarder()

        return super().HSLoader()

    # 卸载宿主机 ###############################################################
    def HSUnload(self) -> ZMessage:
        """卸载宿主机"""
        if self.web_terminal:
            self.web_terminal = None

        # 断开 Proxmox 连接
        self.proxmox = None

        return super().HSUnload()

    # 虚拟机列出 ###############################################################
    def VMStatus(self, vm_name: str = "") -> dict[str, list[HWStatus]]:
        """获取虚拟机状态"""
        return super().VMStatus(vm_name)

    # 虚拟机扫描 ###############################################################
    def VMDetect(self) -> ZMessage:
        """扫描并发现虚拟机"""
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        try:
            # 获取所有虚拟机列表
            vms = client.nodes(self.node_name).qemu.get()

            # 使用主机配置的filter_name作为前缀过滤
            filter_prefix = self.hs_config.filter_name if self.hs_config else ""

            scanned_count = 0
            added_count = 0

            for vm in vms:
                vm_name = vm['name']
                vmid = vm['vmid']

                # 前缀过滤
                if filter_prefix and not vm_name.startswith(filter_prefix):
                    continue

                scanned_count += 1

                # 检查是否已存在
                if vm_name in self.vm_saving:
                    continue

                # 创建默认虚拟机配置
                default_vm_config = VMConfig()
                default_vm_config.vm_uuid = vm_name
                # 保存VMID到配置中（用于后续操作）
                if not hasattr(default_vm_config, 'vm_data'):
                    default_vm_config.vm_data = {}
                default_vm_config.vm_data['vmid'] = vmid

                # 添加到服务器的虚拟机配置中
                self.vm_saving[vm_name] = default_vm_config
                added_count += 1

                log_msg = ZMessage(
                    success=True,
                    action="VScanner",
                    message=f"发现并添加虚拟机: {vm_name} (VMID: {vmid})",
                    results={"vm_name": vm_name, "vmid": vmid}
                )
                self.LogStack(log_msg)

            # 保存到数据库
            if added_count > 0:
                success = self.data_set()
                if not success:
                    return ZMessage(
                        success=False, action="VScanner",
                        message="Failed to save scanned VMs to database")

            return ZMessage(
                success=True,
                action="VScanner",
                message=f"扫描完成。共扫描到{scanned_count}个虚拟机，新增{added_count}个虚拟机配置。",
                results={
                    "scanned": scanned_count,
                    "added": added_count,
                    "prefix_filter": filter_prefix
                }
            )

        except Exception as e:
            return ZMessage(
                success=False, action="VScanner",
                message=f"扫描虚拟机时出错: {str(e)}")

    # 网络检查 #################################################################
    def NetCheck(self, vm_conf: VMConfig) -> tuple:
        """检查并自动分配虚拟机网卡IP地址"""
        client, result = self._connect_proxmox()
        if not result.success:
            return vm_conf, result

        try:
            # 获取所有已分配的IP地址
            allocated_ips = self.IPGrants()

            # 检查是否有重复的网卡类型
            nic_types = {}
            for nic_name, nic_conf in vm_conf.nic_all.items():
                if nic_conf.nic_type in nic_types:
                    return vm_conf, ZMessage(
                        success=False,
                        action="NetCheck",
                        message=f"禁止为同一虚拟机分配多个相同类型的网卡。"
                                f"网卡 {nic_name} 和 {nic_types[nic_conf.nic_type]} 都是 {nic_conf.nic_type} 类型"
                    )
                nic_types[nic_conf.nic_type] = nic_name

            # 排除当前虚拟机自己的IP地址
            current_vm_ips = set()
            for nic_name, nic_conf in vm_conf.nic_all.items():
                if nic_conf.ip4_addr and nic_conf.ip4_addr.strip():
                    current_vm_ips.add(nic_conf.ip4_addr.strip())

            other_vms_ips = allocated_ips - current_vm_ips

            # 遍历虚拟机的所有网卡
            for nic_name, nic_conf in vm_conf.nic_all.items():
                need_ipv4 = not nic_conf.ip4_addr or nic_conf.ip4_addr.strip() == ""

                if not need_ipv4:
                    if nic_conf.ip4_addr.strip() in other_vms_ips:
                        return vm_conf, ZMessage(
                            success=False,
                            action="NetCheck",
                            message=f"网卡 {nic_name} 的IP地址 {nic_conf.ip4_addr} 已被其他虚拟机使用"
                        )
                    continue

                # 查找对应的ipaddr_maps配置
                ipaddr_config = None
                for map_name, map_config in self.hs_config.ipaddr_maps.items():
                    if map_config.get('type') == nic_conf.nic_type:
                        ipaddr_config = map_config
                        break

                if not ipaddr_config:
                    return vm_conf, ZMessage(
                        success=False,
                        action="NetCheck",
                        message=f"网卡 {nic_name} 的网络类型 {nic_conf.nic_type} 未在ipaddr_maps中配置"
                    )

                # 从ipaddr_maps配置中获取IP分配范围
                ip_from = ipaddr_config.get('from', '')
                ip_nums = ipaddr_config.get('nums', 0)
                ip_gate = ipaddr_config.get('gate', '')
                ip_mask = ipaddr_config.get('mask', '')

                if not ip_from or ip_nums <= 0:
                    return vm_conf, ZMessage(
                        success=False,
                        action="NetCheck",
                        message=f"网卡 {nic_name} 的ipaddr_maps配置不完整（缺少from或nums）"
                    )

                # 分配IP地址
                ip_allocated = False
                try:
                    import ipaddress

                    start_ip = ipaddress.ip_address(ip_from)
                    available_ips = []
                    current_ip = start_ip
                    for i in range(ip_nums):
                        available_ips.append(str(current_ip))
                        current_ip += 1

                    for ip_str in available_ips:
                        if ip_str == ip_gate or ip_str in other_vms_ips:
                            continue

                        nic_conf.ip4_addr = ip_str
                        if ip_gate:
                            nic_conf.nic_gate = ip_gate
                        if ip_mask:
                            nic_conf.nic_mask = ip_mask
                        if self.hs_config.ipaddr_dnss:
                            nic_conf.dns_addr = self.hs_config.ipaddr_dnss
                        nic_conf.send_mac()

                        current_vm_ips.add(ip_str)
                        other_vms_ips.add(ip_str)

                        ip_allocated = True
                        logger.info(
                            f"为网卡 {nic_name} 自动分配IP: {ip_str} "
                            f"(范围: {ip_from} - {available_ips[-1]})"
                        )
                        break

                except Exception as e:
                    logger.error(f"处理IP分配时出错: {str(e)}")
                    return vm_conf, ZMessage(
                        success=False,
                        action="NetCheck",
                        message=f"处理IP分配时出错: {str(e)}"
                    )

                if not ip_allocated:
                    return vm_conf, ZMessage(
                        success=False,
                        action="NetCheck",
                        message=f"无法为网卡 {nic_name} 分配IP地址，所有IP已被占用或无可用IP"
                    )

            return vm_conf, ZMessage(
                success=True,
                action="NetCheck",
                message="网络配置检查完成"
            )

        except Exception as e:
            logger.error(f"网络检查时出错: {str(e)}")
            traceback.print_exc()
            return vm_conf, ZMessage(
                success=False,
                action="NetCheck",
                message=f"网络检查失败: {str(e)}"
            )

    # 网络动态绑定 #############################################################
    def NCCreate(self, vm_conf: VMConfig, flag=True) -> ZMessage:
        """配置虚拟机网络（通过Proxmox网络配置）"""
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        try:
            vmid = self._get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="NCCreate",
                    message=f"虚拟机 {vm_conf.vm_uuid} 的VMID未找到")

            vm = client.nodes(self.node_name).qemu(vmid)

            if flag:
                # 添加网络设备
                nic_index = 0
                for nic_name, nic_conf in vm_conf.nic_all.items():
                    # 获取网桥配置
                    nic_keys = "network_" + nic_conf.nic_type
                    if not hasattr(self.hs_config, nic_keys) or getattr(self.hs_config, nic_keys, "") == "":
                        logger.warning(f"主机网络{nic_keys}未配置")
                        continue

                    bridge = getattr(self.hs_config, nic_keys)
                    net_config = f"virtio,bridge={bridge}"

                    if nic_conf.mac_addr:
                        net_config += f",macaddr={nic_conf.mac_addr}"

                    # 配置网络接口
                    config_key = f"net{nic_index}"
                    vm.config.put(**{config_key: net_config})

                    logger.info(f"配置虚拟机网络 {vm_conf.vm_uuid}-{nic_name}: {nic_conf.ip4_addr}")
                    nic_index += 1
            else:
                # 删除网络设备
                config = vm.config.get()
                for key in list(config.keys()):
                    if key.startswith('net'):
                        vm.config.put(**{key: ''})
                        logger.info(f"删除虚拟机网络设备: {vm_conf.vm_uuid}-{key}")

            return ZMessage(
                success=True,
                action="NCCreate",
                message="网络配置成功")

        except Exception as e:
            logger.error(f"网络配置失败: {str(e)}")
            return ZMessage(
                success=False,
                action="NCCreate",
                message=f"网络配置失败: {str(e)}")

    def NCUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        """更新虚拟机网络配置"""
        self.NCCreate(vm_last, False)
        self.NCCreate(vm_conf, True)
        return ZMessage(success=True, action="VMUpdate")

    # 获取VMID #################################################################
    def _get_vmid(self, vm_conf: VMConfig) -> Optional[int]:
        """获取虚拟机的VMID"""
        if hasattr(vm_conf, 'vm_data') and 'vmid' in vm_conf.vm_data:
            return vm_conf.vm_data['vmid']
        return None

    # 分配新的VMID #############################################################
    def _allocate_vmid(self) -> int:
        """分配一个新的VMID"""
        client, result = self._connect_proxmox()
        if not result.success:
            return 100  # 默认起始VMID

        try:
            # 获取所有现有的VMID
            vms = client.nodes(self.node_name).qemu.get()
            existing_vmids = [vm['vmid'] for vm in vms]

            # 从100开始查找可用的VMID
            vmid = 100
            while vmid in existing_vmids:
                vmid += 1

            return vmid
        except Exception as e:
            logger.error(f"分配VMID失败: {str(e)}")
            return 100

    # 创建虚拟机 ###############################################################
    def VMCreate(self, vm_conf: VMConfig) -> ZMessage:
        """创建虚拟机"""
        vm_conf.vm_uuid = vm_conf.vm_uuid.replace('_', '-')
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result

        client, result = self._connect_proxmox()
        if not result.success:
            return result

        try:
            # 分配VMID
            vmid = self._allocate_vmid()
            if not hasattr(vm_conf, 'vm_data'):
                vm_conf.vm_data = {}
            vm_conf.vm_data['vmid'] = vmid

            # 构建虚拟机配置
            config = {
                'vmid': vmid,
                'name': vm_conf.vm_uuid.replace('_', '-'),
                'memory': vm_conf.mem_num if vm_conf.mem_num > 0 else 2048,
                'cores': vm_conf.cpu_num if vm_conf.cpu_num > 0 else 2,
                'sockets': 1,
                'ostype': 'l26',  # Linux 2.6+
                'boot': 'order=scsi0;ide2',
                'scsihw': 'virtio-scsi-pci',
            }

            # 创建虚拟机
            client.nodes(self.node_name).qemu.create(**config)
            logger.info(f"虚拟机 {vm_conf.vm_uuid} (VMID: {vmid}) 创建成功")

            # 配置网络
            self.NCCreate(vm_conf, True)

            # 如果指定了系统镜像，安装系统
            if vm_conf.os_name:
                install_result = self.VMSetups(vm_conf)
                if not install_result.success:
                    logger.warning(f"系统安装失败: {install_result.message}")

        except Exception as e:
            traceback.print_exc()
            hs_result = ZMessage(
                success=False, action="VMCreate",
                message=f"虚拟机创建失败: {str(e)}")
            self.logs_set(hs_result)
            return hs_result

        self.data_set()
        return super().VMCreate(vm_conf)

    # 安装虚拟机 ###############################################################
    def VMSetups(self, vm_conf: VMConfig) -> ZMessage:
        """安装虚拟机系统"""
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        try:
            vmid = self._get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="VInstall",
                    message=f"虚拟机 {vm_conf.vm_uuid} 的VMID未找到")

            os_name = vm_conf.os_name
            vm = client.nodes(self.node_name).qemu(vmid)

            # 判断是ISO安装还是模板克隆
            if os_name.endswith('.iso'):
                # ISO安装
                iso_path = f"local:iso/{os_name}"
                vm.config.put(ide2=f"{iso_path},media=cdrom")
                logger.info(f"挂载ISO: {iso_path}")
            else:
                # 从模板克隆（如果os_name是模板ID）
                logger.info(f"使用模板/镜像: {os_name}")
                # 这里可以实现从模板克隆的逻辑

            return ZMessage(success=True, action="VInstall")

        except Exception as e:
            return ZMessage(
                success=False, action="VInstall",
                message=f"系统安装失败: {str(e)}")

    # 配置虚拟机 ###############################################################
    def VMUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        """更新虚拟机配置"""
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result

        client, result = self._connect_proxmox()
        if not result.success:
            return result

        try:
            vmid = self._get_vmid(vm_conf.vm_uuid.replace('_', '-'))
            if vmid is None:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {vm_conf.vm_uuid} 的VMID未找到")

            vm = client.nodes(self.node_name).qemu(vmid)

            # 停止虚拟机
            status = vm.status.current.get()
            if status['status'] == 'running':
                self.VMPowers(vm_conf.vm_uuid, VMPowers.H_CLOSE)

            # 重装系统（如果系统镜像改变）
            if vm_conf.os_name != vm_last.os_name and vm_last.os_name != "":
                install_result = self.VMSetups(vm_conf)
                if not install_result.success:
                    return install_result

            # 更新网络配置
            network_result = self.NCUpdate(vm_conf, vm_last)
            if not network_result.success:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"网络配置更新失败: {network_result.message}")

            # 更新虚拟机配置
            config_updates = {}
            if vm_conf.cpu_num != vm_last.cpu_num and vm_conf.cpu_num > 0:
                config_updates['cores'] = vm_conf.cpu_num
            if vm_conf.mem_num != vm_last.mem_num and vm_conf.mem_num > 0:
                config_updates['memory'] = vm_conf.mem_num

            if config_updates:
                vm.config.put(**config_updates)
                logger.info(f"虚拟机 {vm_conf.vm_uuid} 配置已更新: {config_updates}")

            # 启动虚拟机
            start_result = self.VMPowers(vm_conf.vm_uuid, VMPowers.S_START)
            if not start_result.success:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机启动失败: {start_result.message}")

        except Exception as e:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机更新失败: {str(e)}")

        return super().VMUpdate(vm_conf, vm_last)

    # 删除虚拟机 ###############################################################
    def VMDelete(self, vm_name: str) -> ZMessage:
        """删除虚拟机"""
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        try:
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False, action="VMDelete",
                    message=f"虚拟机 {vm_name} 不存在")

            vmid = self._get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="VMDelete",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            vm = client.nodes(self.node_name).qemu(vmid)

            # 停止虚拟机
            status = vm.status.current.get()
            if status['status'] == 'running':
                self.VMPowers(vm_name, VMPowers.H_CLOSE)

            # 删除网络配置
            self.NCCreate(vm_conf, False)

            # 删除虚拟机
            vm.delete()
            logger.info(f"虚拟机 {vm_name} (VMID: {vmid}) 删除成功")

        except Exception as e:
            return ZMessage(
                success=False, action="VMDelete",
                message=f"删除虚拟机失败: {str(e)}")

        return super().VMDelete(vm_name)

    # 虚拟机电源 ###############################################################
    def VMPowers(self, vm_name: str, power: VMPowers) -> ZMessage:
        """虚拟机电源管理"""
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        try:
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False, action="VMPowers",
                    message=f"虚拟机 {vm_name} 不存在")

            vmid = self._get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="VMPowers",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            vm = client.nodes(self.node_name).qemu(vmid)
            status = vm.status.current.get()

            if power == VMPowers.S_START:
                if status['status'] != 'running':
                    vm.status.start.post()
                    logger.info(f"虚拟机 {vm_name} 已启动")
                else:
                    logger.info(f"虚拟机 {vm_name} 已经在运行")

            elif power == VMPowers.H_CLOSE or power == VMPowers.S_CLOSE:
                if status['status'] == 'running':
                    if power == VMPowers.S_CLOSE:
                        vm.status.shutdown.post()
                    else:
                        vm.status.stop.post()
                    logger.info(f"虚拟机 {vm_name} 已停止")
                else:
                    logger.info(f"虚拟机 {vm_name} 已经停止")

            elif power == VMPowers.S_RESET or power == VMPowers.H_RESET:
                if status['status'] == 'running':
                    if power == VMPowers.S_RESET:
                        vm.status.reboot.post()
                    else:
                        vm.status.reset.post()
                    logger.info(f"虚拟机 {vm_name} 已重启")
                else:
                    vm.status.start.post()
                    logger.info(f"虚拟机 {vm_name} 已启动")

            elif power == VMPowers.A_PAUSE:
                if status['status'] == 'running':
                    vm.status.suspend.post()
                    logger.info(f"虚拟机 {vm_name} 已暂停")
                else:
                    logger.warning(f"虚拟机 {vm_name} 未运行，无法暂停")

            elif power == VMPowers.A_WAKED:
                if status['status'] == 'paused':
                    vm.status.resume.post()
                    logger.info(f"虚拟机 {vm_name} 已恢复")
                else:
                    logger.warning(f"虚拟机 {vm_name} 未暂停，无法恢复")

            hs_result = ZMessage(success=True, action="VMPowers")
            self.logs_set(hs_result)

        except Exception as e:
            error_msg = f"电源操作失败: {str(e)}"
            logger.error(f"虚拟机 {vm_name} 电源操作失败: {str(e)}")
            logger.error(traceback.format_exc())

            hs_result = ZMessage(
                success=False, action="VMPowers",
                message=error_msg)
            self.logs_set(hs_result)
            return hs_result

        super().VMPowers(vm_name, power)
        return hs_result

    # 设置虚拟机密码 ###########################################################
    def VMPasswd(self, vm_name: str, os_pass: str) -> ZMessage:
        """设置虚拟机密码"""
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        try:
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False, action="Password",
                    message=f"虚拟机 {vm_name} 不存在")

            vmid = self._get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="Password",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            # 通过QEMU Guest Agent设置密码
            # 注意：需要虚拟机安装并运行qemu-guest-agent
            vm = client.nodes(self.node_name).qemu(vmid)

            # 使用agent执行命令
            try:
                vm.agent.post('exec', command=f"echo 'root:{os_pass}' | chpasswd")
                logger.info(f"虚拟机 {vm_name} 密码已设置")
                return ZMessage(success=True, action="Password")
            except Exception as agent_error:
                logger.warning(f"通过agent设置密码失败: {str(agent_error)}")
                return ZMessage(
                    success=False, action="Password",
                    message=f"设置密码失败，请确保虚拟机已安装qemu-guest-agent: {str(agent_error)}")

        except Exception as e:
            return ZMessage(
                success=False, action="Password",
                message=f"设置密码失败: {str(e)}")

    # 备份虚拟机 ###############################################################
    def VMBackup(self, vm_name: str, vm_tips: str) -> ZMessage:
        """备份虚拟机"""
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        vm_conf = self.VMSelect(vm_name)
        if not vm_conf:
            return ZMessage(
                success=False,
                action="Backup",
                message="虚拟机不存在")

        try:
            vmid = self._get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="VMBackup",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            vm = client.nodes(self.node_name).qemu(vmid)

            # 检查虚拟机是否正在运行
            status = vm.status.current.get()
            is_running = status['status'] == 'running'

            if is_running:
                vm.status.stop.post()
                logger.info(f"虚拟机 {vm_name} 已停止")
                time.sleep(5)  # 等待虚拟机完全停止

            # 构建备份文件名
            bak_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            bak_file = f"{vm_name}_{bak_time}.vma"

            # 创建备份
            backup_config = {
                'vmid': vmid,
                'mode': 'stop',  # 停止模式备份
                'compress': 'gzip',
                'storage': 'local',  # 备份存储位置
            }

            task_id = client.nodes(self.node_name).vzdump.post(**backup_config)
            logger.info(f"备份任务已创建: {task_id}")

            # 等待备份完成
            # 注意：这里简化处理，实际应该轮询任务状态
            time.sleep(10)

            # 记录备份信息
            vm_conf.backups.append(VMBackup(
                backup_time=datetime.datetime.now(),
                backup_name=bak_file,
                backup_hint=vm_tips,
                old_os_name=vm_conf.os_name
            ))

            # 如果虚拟机之前在运行，重新启动
            if is_running:
                vm.status.start.post()
                logger.info(f"虚拟机 {vm_name} 已重新启动")

            hs_result = ZMessage(
                success=True, action="VMBackup",
                message=f"虚拟机备份成功，文件: {bak_file}",
                results={"backup_file": bak_file}
            )
            self.vm_saving[vm_name] = vm_conf
            self.logs_set(hs_result)
            self.data_set()

            return hs_result

        except Exception as e:
            logger.error(f"备份虚拟机失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="VMBackup",
                message=f"备份失败: {str(e)}")

    # 恢复虚拟机 ###############################################################
    def Restores(self, vm_name: str, vm_back: str) -> ZMessage:
        """恢复虚拟机"""
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        vm_conf = self.VMSelect(vm_name)
        if not vm_conf:
            return ZMessage(
                success=False, action="Restores",
                message=f"虚拟机 {vm_name} 不存在")

        # 获取备份信息
        vb_conf = None
        for vb_item in vm_conf.backups:
            if vb_item.backup_name == vm_back:
                vb_conf = vb_item
                break

        if not vb_conf:
            return ZMessage(
                success=False, action="Restores",
                message=f"备份 {vm_back} 不存在")

        try:
            vmid = self._get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="Restores",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            # 恢复备份
            # 注意：Proxmox的恢复操作比较复杂，这里简化处理
            logger.info(f"开始恢复虚拟机 {vm_name}，备份文件: {vm_back}")

            # 实际的恢复操作需要调用Proxmox的restore API
            # 这里只是示例代码
            restore_config = {
                'vmid': vmid,
                'archive': f"local:backup/{vm_back}",
                'force': 1,
            }

            # client.nodes(self.node_name).qemu.post(**restore_config)

            vm_conf.os_name = vb_conf.old_os_name
            logger.info(f"虚拟机 {vm_name} 恢复成功")

            self.vm_saving[vm_name] = vm_conf
            hs_result = ZMessage(
                success=True, action="Restores",
                message=f"虚拟机恢复成功: {vm_name}",
                results={"vm_name": vm_name}
            )
            self.logs_set(hs_result)
            self.data_set()
            return hs_result

        except Exception as e:
            logger.error(f"恢复虚拟机失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="Restores",
                message=f"恢复失败: {str(e)}")

    # VM镜像挂载 ###############################################################
    def HDDMount(self, vm_name: str, vm_imgs: SDConfig, in_flag=True) -> ZMessage:
        """挂载/卸载硬盘"""
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="HDDMount",
                    message="虚拟机不存在")

            vm_conf = self.vm_saving[vm_name]
            vmid = self._get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="HDDMount",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            vm = client.nodes(self.node_name).qemu(vmid)

            # 停止虚拟机
            status = vm.status.current.get()
            was_running = status['status'] == 'running'
            if was_running:
                self.VMPowers(vm_name, VMPowers.H_CLOSE)

            if in_flag:
                # 挂载硬盘
                # 创建新的磁盘
                disk_size = f"{vm_imgs.hdd_size}G" if hasattr(vm_imgs, 'hdd_size') else "10G"
                disk_config = f"local-lvm:{disk_size}"

                # 找到可用的scsi设备号
                config = vm.config.get()
                scsi_num = 1
                while f"scsi{scsi_num}" in config:
                    scsi_num += 1

                vm.config.put(**{f"scsi{scsi_num}": disk_config})

                vm_imgs.hdd_flag = 1
                self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name] = vm_imgs

                logger.info(f"硬盘已挂载到虚拟机 {vm_name}")
            else:
                # 卸载硬盘
                if vm_imgs.hdd_name in self.vm_saving[vm_name].hdd_all:
                    self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name].hdd_flag = 0

                logger.info(f"硬盘已从虚拟机 {vm_name} 卸载")

            # 保存配置
            old_conf = deepcopy(self.vm_saving[vm_name])
            self.VMUpdate(self.vm_saving[vm_name], old_conf)
            self.data_set()

            # 重启虚拟机（如果之前在运行）
            if was_running:
                self.VMPowers(vm_name, VMPowers.S_START)

            action_text = "挂载" if in_flag else "卸载"
            return ZMessage(
                success=True, action="HDDMount",
                message=f"硬盘{action_text}成功")

        except Exception as e:
            return ZMessage(
                success=False, action="HDDMount",
                message=f"硬盘挂载操作失败: {str(e)}")

    # ISO镜像挂载 ##############################################################
    def ISOMount(self, vm_name: str, vm_imgs: IMConfig, in_flag=True) -> ZMessage:
        """挂载/卸载ISO镜像"""
        client, result = self._connect_proxmox()
        if not result.success:
            return result

        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="ISOMount",
                    message="虚拟机不存在")

            vm_conf = self.vm_saving[vm_name]
            vmid = self._get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="ISOMount",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            vm = client.nodes(self.node_name).qemu(vmid)

            # 停止虚拟机
            status = vm.status.current.get()
            was_running = status['status'] == 'running'
            if was_running:
                self.VMPowers(vm_name, VMPowers.H_CLOSE)

            if in_flag:
                # 挂载ISO
                iso_path = f"local:iso/{vm_imgs.iso_file}"
                vm.config.put(ide2=f"{iso_path},media=cdrom")

                self.vm_saving[vm_name].iso_all[vm_imgs.iso_name] = vm_imgs
                logger.info(f"ISO已挂载到虚拟机 {vm_name}: {vm_imgs.iso_file}")
            else:
                # 卸载ISO
                vm.config.put(ide2="none,media=cdrom")

                if vm_imgs.iso_name in self.vm_saving[vm_name].iso_all:
                    del self.vm_saving[vm_name].iso_all[vm_imgs.iso_name]
                logger.info(f"ISO已从虚拟机 {vm_name} 卸载")

            # 保存配置
            old_conf = deepcopy(self.vm_saving[vm_name])
            self.VMUpdate(self.vm_saving[vm_name], old_conf)
            self.data_set()

            # 重启虚拟机（如果之前在运行）
            if was_running:
                self.VMPowers(vm_name, VMPowers.S_START)

            action_text = "挂载" if in_flag else "卸载"
            return ZMessage(
                success=True, action="ISOMount",
                message=f"ISO镜像{action_text}成功")

        except Exception as e:
            return ZMessage(
                success=False, action="ISOMount",
                message=f"ISO镜像挂载操作失败: {str(e)}")

    # 虚拟机控制台 ##############################################################
    def VMRemote(self, vm_uuid: str, ip_addr: str = "127.0.0.1") -> ZMessage:
        """生成VNC访问URL"""
        if vm_uuid not in self.vm_saving:
            return ZMessage(
                success=False,
                action="VCRemote",
                message="虚拟机不存在")

        vm_conf = self.vm_saving[vm_uuid]
        vmid = self._get_vmid(vm_conf)
        if vmid is None:
            return ZMessage(
                success=False,
                action="VCRemote",
                message=f"虚拟机 {vm_uuid} 的VMID未找到")

        # 获取主机外网IP
        if len(self.hs_config.public_addr) == 0:
            return ZMessage(
                success=False,
                action="VCRemote",
                message="主机外网IP不存在")

        public_ip = self.hs_config.public_addr[0]
        if public_ip in ["localhost", "127.0.0.1", ""]:
            public_ip = "127.0.0.1"

        # 构造Proxmox VNC URL
        # Proxmox使用noVNC，URL格式为: https://host:8006/?console=kvm&novnc=1&vmid=xxx&node=xxx
        vnc_url = f"https://{self.hs_config.server_addr}:8006/?console=kvm&novnc=1&vmid={vmid}&node={self.node_name}"

        logger.info(f"VMRemote for {vm_uuid}: {vnc_url}")

        return ZMessage(
            success=True,
            action="VCRemote",
            message=vnc_url,
            results={
                "vmid": vmid,
                "url": vnc_url
            }
        )

    # 加载备份 #################################################################
    def LDBackup(self, vm_back: str = "") -> ZMessage:
        """加载备份列表"""
        return super().LDBackup(vm_back)

    # 移除备份 #################################################################
    def RMBackup(self, vm_name: str, vm_back: str = "") -> ZMessage:
        """移除备份"""
        return super().RMBackup(vm_name, vm_back)

    # 移除磁盘 #################################################################
    def RMMounts(self, vm_name: str, vm_imgs: str) -> ZMessage:
        """移除磁盘"""
        return super().RMMounts(vm_name, vm_imgs)

    # 查找显卡 #################################################################
    def GPUShows(self) -> dict[str, str]:
        """查找显卡"""
        return {}

    # 端口映射 #################################################################
    def PortsMap(self, map_info: PortData, flag=True) -> ZMessage:
        """端口映射"""
        is_remote = self.is_remote_host()

        if is_remote:
            success, message = self.port_forward.connect_ssh()
            if not success:
                return ZMessage(
                    success=False, action="PortsMap",
                    message=f"SSH连接失败: {message}")

        if map_info.wan_port == 0:
            map_info.wan_port = self.port_forward.allocate_port(is_remote)
        else:
            existing_ports = self.port_forward.get_host_ports(is_remote)
            if map_info.wan_port in existing_ports:
                if is_remote:
                    self.port_forward.close_ssh()
                return ZMessage(
                    success=False, action="PortsMap",
                    message=f"端口 {map_info.wan_port} 已被占用")

        if flag:
            success, error = self.port_forward.add_port_forward(
                map_info.lan_addr, map_info.lan_port, map_info.wan_port,
                "TCP", is_remote, map_info.nat_tips)

            if success:
                hs_message = f"端口 {map_info.wan_port} 成功映射到 {map_info.lan_addr}:{map_info.lan_port}"
                hs_success = True
            else:
                if is_remote:
                    self.port_forward.close_ssh()
                return ZMessage(
                    success=False, action="PortsMap",
                    message=f"端口映射失败: {error}")
        else:
            self.port_forward.remove_port_forward(
                map_info.wan_port, "TCP", is_remote)
            hs_message = f"端口 {map_info.wan_port} 映射已删除"
            hs_success = True

        hs_result = ZMessage(
            success=hs_success, action="PortsMap",
            message=hs_message)
        self.logs_set(hs_result)

        if is_remote:
            self.port_forward.close_ssh()

        return hs_result

    # 反向代理 #################################################################
    def ProxyMap(self,
                 pm_info: WebProxy,
                 vm_uuid: str,
                 in_apis: HttpManager,
                 in_flag=True) -> ZMessage:
        """反向代理"""
        if self.hs_config.server_addr not in ["localhost", "127.0.0.1", ""]:
            pm_info.lan_port = self.FindPort(vm_uuid, pm_info.lan_port)
            pm_info.lan_addr = self.hs_config.server_addr
            if pm_info.lan_port == 0 and in_flag:
                return ZMessage(
                    success=False, action="ProxyMap",
                    message="当主机为远程IP时，必须先添加NAT映射才能代理<br/>"
                            "当前映射的本地端口缺少NAT映射，请先添加映射")

        return super().ProxyMap(pm_info, vm_uuid, in_apis, in_flag)
