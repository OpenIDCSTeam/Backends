import os
import shutil
import datetime
import traceback
from copy import deepcopy
from typing import Optional, Tuple
from loguru import logger

try:
    import pylxd
    from pylxd import Client
    from pylxd.exceptions import LXDAPIException, NotFound

    LXD_AVAILABLE = True
except ImportError:
    LXD_AVAILABLE = False
    logger.warning("pylxd not available, LXD functionality will be disabled")
    Client = None  # 定义一个占位符，避免类型注解错误

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
    # 宿主机服务 ###############################################################
    def __init__(self, config: HSConfig, **kwargs):
        super().__init__(config, **kwargs)
        super().__load__(**kwargs)
        # LXD 客户端连接
        self.lxd_client = None
        self.web_terminal = None
        self.http_manager = None
        self.port_forward = None

    @staticmethod
    def change_under(vm_data: VMConfig | str, flag=True):
        vm_conf = vm_data
        if isinstance(vm_conf, VMConfig):
            vm_data = vm_data.vm_uuid
        if flag:
            vm_data = vm_data.replace("_", "-")
        else:
            vm_data = vm_data.replace("-", "_")
        if isinstance(vm_conf, VMConfig):
            vm_conf.vm_uuid = vm_data
            return vm_conf
        return vm_data

    def VMLoader(self) -> bool:
        pass

    # 连接到 LXD 服务器 ########################################################
    def _connect_lxd(self) -> Tuple[Optional[Client], ZMessage]:
        """
        连接到 LXD 服务器（支持本地和远程）
        :return: (LXD客户端对象, 操作结果消息)
        """
        if not LXD_AVAILABLE:
            return None, ZMessage(
                success=False, action="_connect_lxd",
                message="pylxd is not installed")

        try:
            # 如果已经连接，直接返回
            if self.lxd_client is not None:
                return self.lxd_client, ZMessage(success=True, action="_connect_lxd")

            # 判断是本地连接还是远程连接
            if self.hs_config.server_addr in ["localhost", "127.0.0.1", ""]:
                # 本地连接
                logger.info("Connecting to local LXD server")
                self.lxd_client = Client()
            else:
                # 远程连接
                # 如果是SSH转发模式
                if self.hs_config.server_addr.startswith("ssh://"):
                    # 使用SSH转发连接LXD
                    logger.info(f"Connecting to LXD via SSH: {self.hs_config.server_addr}")
                    self.lxd_client = Client(endpoint=self.hs_config.server_addr)
                else:
                    # 直接HTTPS连接
                    endpoint = f"https://{self.hs_config.server_addr}:8443"
                    logger.info(f"Connecting to remote LXD server: {endpoint}")

                    # 证书路径（从 launch_path 获取）
                    cert_path = os.path.join(self.hs_config.launch_path, "client.crt")
                    key_path = os.path.join(self.hs_config.launch_path, "client.key")
                    if self.hs_config.launch_path == "":
                        return None, ZMessage(
                            success=False, action="_connect_lxd",
                            message=f"缺少证书路径，请设置启动路径为证书路径")
                    if not os.path.exists(cert_path) or not os.path.exists(key_path):
                        return None, ZMessage(
                            success=False, action="_connect_lxd",
                            message=f"证书文件未找到，请检查 {self.hs_config.launch_path}")

                    self.lxd_client = Client(
                        endpoint=endpoint,
                        cert=(cert_path, key_path),
                        verify=False  # 可以设置为服务器证书路径以验证
                    )

            # 测试连接
            self.lxd_client.containers.all()
            logger.info("Successfully connected to LXD server")

            return self.lxd_client, ZMessage(success=True, action="_connect_lxd")

        except Exception as e:
            logger.error(f"Failed to connect to LXD server: {str(e)}")
            self.lxd_client = None
            return None, ZMessage(
                success=False, action="_connect_lxd",
                message=f"Failed to connect to LXD: {str(e)}")

    # 判断是否为远程宿主机 #####################################################
    def is_remote_host(self) -> bool:
        if self.hs_config.server_addr not in ["localhost", "127.0.0.1", ""]:
            if not self.hs_config.server_addr.startswith("ssh://"):
                return True
        return False

    # 同步端口转发配置 #########################################################
    def sync_forwarder(self):
        """同步端口转发配置：删除不需要的转发，添加缺少的转发"""
        try:
            # 判断是否为远程主机
            is_remote = self.is_remote_host()

            # 如果是远程主机，先建立SSH连接
            if is_remote:
                success, message = self.port_forward.connect_ssh()
                if not success:
                    logger.error(f"SSH连接失败，无法同步端口转发: {message}")
                    return

            # 获取系统中已有的端口转发
            existing_forwards = self.port_forward.list_ports(is_remote)
            existing_map = {}  # {(lan_addr, lan_port): forward_info}
            for forward in existing_forwards:
                key = (forward.lan_addr, forward.lan_port)
                existing_map[key] = forward

            # 获取配置中需要的端口转发
            required_forwards = {}  # {(lan_addr, lan_port): (wan_port, vm_name)}
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
                    # 这个转发不在配置中，删除它
                    if self.port_forward.remove_port_forward(
                            forward.wan_port, forward.protocol, is_remote
                    ):
                        removed_count += 1
                        logger.info(
                            f"删除多余的端口转发: {forward.protocol} {forward.wan_port} -> "
                            f"{forward.lan_addr}:{forward.lan_port}"
                        )

            # 添加缺少的转发
            added_count = 0
            for key, (wan_port, vm_name) in required_forwards.items():
                lan_addr, lan_port = key

                # 检查是否已存在
                if key in existing_map:
                    existing_forward = existing_map[key]
                    # 如果wan_port不同，需要先删除旧的再添加新的
                    if existing_forward.wan_port != wan_port:
                        self.port_forward.remove_port_forward(
                            existing_forward.wan_port, existing_forward.protocol, is_remote
                        )
                        logger.info(
                            f"端口映射变更，删除旧转发: {existing_forward.protocol} "
                            f"{existing_forward.wan_port} -> {lan_addr}:{lan_port}"
                        )
                    else:
                        # 端口转发已存在且配置正确，跳过
                        continue

                # 添加新的端口转发
                success, error = self.port_forward.add_port_forward(
                    lan_addr, lan_port, wan_port, "TCP", is_remote, vm_name
                )

                if success:
                    added_count += 1
                    logger.info(
                        f"添加端口转发: TCP {wan_port} -> {lan_addr}:{lan_port} ({vm_name})"
                    )
                else:
                    logger.error(
                        f"添加端口转发失败: TCP {wan_port} -> {lan_addr}:{lan_port}, "
                        f"错误: {error}"
                    )

            logger.info(
                f"端口转发同步完成: 删除 {removed_count} 个，添加 {added_count} 个"
            )

            # 关闭SSH连接
            if is_remote:
                self.port_forward.close_ssh()

        except Exception as e:
            logger.error(f"同步端口转发时出错: {str(e)}")
            traceback.print_exc()

    # 宿主机任务 ###############################################################
    def Crontabs(self) -> bool:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().Crontabs()

    # 宿主机状态 ###############################################################
    def HSStatus(self) -> HWStatus:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().HSStatus()

    # 初始宿主机 ###############################################################
    def HSCreate(self) -> ZMessage:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().HSCreate()

    # 还原宿主机 ###############################################################
    def HSDelete(self) -> ZMessage:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().HSDelete()

    # 读取宿主机 ###############################################################
    def HSLoader(self) -> ZMessage:
        # 专用操作 =============================================================
        # 初始化SSHTerminal
        if not self.web_terminal:
            self.web_terminal = SSHTerminal(self.hs_config)

        # 初始化HttpManager，使用vnc_主机名.txt作为配置文件名
        if not self.http_manager:
            # 获取主机名，使用server_name，如果没有则使用默认值
            hostname = getattr(self.hs_config, 'server_name', '')
            config_filename = f"vnc-{hostname}.txt"
            self.http_manager = HttpManager(config_filename)
            # 初始化SSH代理管理
            self.http_manager.start_ssh(self.hs_config.remote_port)
            self.http_manager.start_web()

        # 初始化端口转发管理器
        if not self.port_forward:
            self.port_forward = PortForward(self.hs_config)

        # 连接到 LXD 服务器
        client, result = self._connect_lxd()
        if not result.success:
            return result

        # 同步端口转发配置
        self.sync_forwarder()

        # 通用操作 =============================================================
        return super().HSLoader()

    # 卸载宿主机 ###############################################################
    def HSUnload(self) -> ZMessage:
        # 专用操作 =============================================================
        if self.web_terminal:
            self.web_terminal = None

        # 断开 LXD 连接
        self.lxd_client = None

        # 通用操作 =============================================================
        return super().HSUnload()

    # 虚拟机列出 ###############################################################
    def VMStatus(self, vm_name: str = "") -> dict[str, list[HWStatus]]:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().VMStatus(vm_name)

    # 虚拟机扫描 ###############################################################
    def VMDetect(self) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result

        try:
            # 获取所有容器列表
            containers = client.containers.all()

            # 使用主机配置的filter_name作为前缀过滤
            filter_prefix = self.hs_config.filter_name if self.hs_config else ""

            scanned_count = 0
            added_count = 0

            for container in containers:
                container_name = container.name

                # 前缀过滤
                if filter_prefix and not container_name.startswith(filter_prefix):
                    continue

                scanned_count += 1

                # 规范化容器名（将下划线转换为连字符）
                normalized_name = self.change_under(container_name, flag=True)

                # 检查是否已存在（使用规范化后的名称）
                if normalized_name in self.vm_saving:
                    continue

                # 创建默认虚拟机配置
                default_vm_config = VMConfig()
                default_vm_config.vm_uuid = normalized_name  # 使用规范化后的名称

                # 添加到服务器的虚拟机配置中
                self.vm_saving[normalized_name] = default_vm_config
                added_count += 1

                # 记录日志
                log_msg = ZMessage(
                    success=True,
                    action="VScanner",
                    message=f"发现并添加容器: {container_name} (规范化为: {normalized_name})",
                    results={"container_name": container_name, "normalized_name": normalized_name}
                )
                self.LogStack(log_msg)

            # 保存到数据库
            if added_count > 0:
                success = self.data_set()
                if not success:
                    return ZMessage(
                        success=False, action="VScanner",
                        message="Failed to save scanned containers to database")

            return ZMessage(
                success=True,
                action="VScanner",
                message=f"扫描完成。共扫描到{scanned_count}个容器，新增{added_count}个容器配置。",
                results={
                    "scanned": scanned_count,
                    "added": added_count,
                    "prefix_filter": filter_prefix
                }
            )

        except Exception as e:
            return ZMessage(
                success=False, action="VScanner",
                message=f"扫描容器时出错: {str(e)}")

    # 网络检查 #################################################################
    def NetCheck(self, vm_conf: VMConfig) -> tuple:
        """检查并自动分配虚拟机网卡IP地址"""
        # 连接到 LXD 服务器
        client, result = self._connect_lxd()
        if not result.success:
            return vm_conf, result

        try:
            # 获取所有已分配的IP地址（包括其他虚拟机）
            allocated_ips = self.IPGrants()

            # 检查是否有重复的网卡类型（禁止同一容器分配多个相同类型的网卡）
            nic_types = {}
            for nic_name, nic_conf in vm_conf.nic_all.items():
                if nic_conf.nic_type in nic_types:
                    return vm_conf, ZMessage(
                        success=False,
                        action="NetCheck",
                        message=f"禁止为同一容器分配多个相同类型的网卡。"
                                f"网卡 {nic_name} 和 {nic_types[nic_conf.nic_type]} 都是 {nic_conf.nic_type} 类型"
                    )
                nic_types[nic_conf.nic_type] = nic_name

            # 排除当前虚拟机自己的IP地址，避免误判为冲突
            current_vm_ips = set()
            for nic_name, nic_conf in vm_conf.nic_all.items():
                if nic_conf.ip4_addr and nic_conf.ip4_addr.strip():
                    current_vm_ips.add(nic_conf.ip4_addr.strip())

            # 只保留其他虚拟机的IP地址
            other_vms_ips = allocated_ips - current_vm_ips

            # 遍历虚拟机的所有网卡
            for nic_name, nic_conf in vm_conf.nic_all.items():
                # 检查是否需要分配IP
                need_ipv4 = not nic_conf.ip4_addr or nic_conf.ip4_addr.strip() == ""

                if not need_ipv4:
                    # 如果已经有IP，检查是否被其他虚拟机占用
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

                    # 解析起始IP地址
                    start_ip = ipaddress.ip_address(ip_from)

                    # 生成可用的IP地址列表（从起始IP开始，数量为nums）
                    available_ips = []
                    current_ip = start_ip
                    for i in range(ip_nums):
                        available_ips.append(str(current_ip))
                        current_ip += 1

                    # 遍历可用IP地址
                    for ip_str in available_ips:
                        # 跳过网关地址和已分配的IP
                        if ip_str == ip_gate or ip_str in other_vms_ips:
                            continue

                        # 分配这个IP
                        nic_conf.ip4_addr = ip_str
                        if ip_gate:
                            nic_conf.nic_gate = ip_gate
                        # 设置子网掩码
                        if ip_mask:
                            nic_conf.nic_mask = ip_mask
                        # 设置DNS
                        if self.hs_config.ipaddr_dnss:
                            nic_conf.dns_addr = self.hs_config.ipaddr_dnss
                        # 更新MAC地址
                        nic_conf.send_mac()

                        # 将新分配的IP添加到当前虚拟机IP集合和其他虚拟机IP集合中
                        # 避免后续网卡分配到相同IP
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

                # 如果没有分配到IP，返回失败
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
        """配置容器网络（通过LXD设备配置）"""
        # 连接服务
        client, result = self._connect_lxd()
        if not result.success:
            return result

        try:
            container = client.containers.get(vm_conf.vm_uuid)
        except NotFound:
            return ZMessage(
                success=False, action="NCCreate",
                message=f"容器 {vm_conf.vm_uuid} 不存在")

        # 配置网络设备
        try:
            if flag:
                # 添加网络设备
                nic_index = 0
                for nic_name, nic_conf in vm_conf.nic_all.items():
                    # 获取网络配置
                    nic_keys = "network_" + nic_conf.nic_type
                    if not hasattr(self.hs_config, nic_keys) or getattr(self.hs_config, nic_keys, "") == "":
                        logger.warning(f"主机网络{nic_keys}未配置")
                        continue

                    network_name = getattr(self.hs_config, nic_keys)
                    device_name = f"eth{nic_index}"

                    # 配置网络设备
                    container.devices[device_name] = {
                        "type": "nic",
                        "nictype": "bridged",
                        "parent": network_name,
                        "name": device_name
                    }

                    if nic_conf.mac_addr:
                        container.devices[device_name]["hwaddr"] = nic_conf.mac_addr

                    if nic_conf.ip4_addr:
                        container.devices[device_name]["ipv4.address"] = nic_conf.ip4_addr

                    nic_index += 1
                    logger.info(f"连接容器网络 {vm_conf.vm_uuid}-{nic_name}: {nic_conf.ip4_addr}")

                # 保存配置
                container.save(wait=True)
            else:
                # 删除网络设备
                devices_to_remove = []
                for device_name, device_config in container.devices.items():
                    if device_config.get("type") == "nic" and device_name.startswith("eth"):
                        devices_to_remove.append(device_name)

                for device_name in devices_to_remove:
                    del container.devices[device_name]
                    logger.info(f"删除容器网络设备: {vm_conf.vm_uuid}-{device_name}")

                # 保存配置
                if devices_to_remove:
                    container.save(wait=True)

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
        """更新容器网络配置"""
        self.NCCreate(vm_last, False)
        self.NCCreate(vm_conf, True)
        return ZMessage(success=True, action="VMUpdate")

    # 创建虚拟机 ###############################################################
    def VMCreate(self, vm_conf: VMConfig) -> ZMessage:
        # 规范化容器名（将下划线转换为连字符）
        original_name = vm_conf.vm_uuid
        vm_conf = self.change_under(vm_conf, flag=True)

        # 如果名称发生了变化，记录日志
        if original_name != vm_conf.vm_uuid:
            logger.info(f"容器名已规范化: {original_name} -> {vm_conf.vm_uuid}")

        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.NCCreate(vm_conf, True)

        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result

        try:
            container_name = vm_conf.vm_uuid

            # 检查容器是否已存在
            try:
                client.containers.get(container_name)
                return ZMessage(
                    success=False, action="VMCreate",
                    message=f"Container {container_name} already exists")
            except NotFound:
                pass  # 容器不存在，继续创建

            # 创建容器配置
            config = {
                "name": container_name,
                "source": {
                    "type": "none"  # 先创建空容器，稍后安装系统
                },
                "config": self._build_container_config(vm_conf),
                "devices": self._build_container_devices(vm_conf)
            }

            # 创建容器
            container = client.containers.create(config, wait=True)

            # 安装系统（从模板）
            install_result = self.VMSetups(vm_conf)
            if not install_result.success:
                # 清理失败的容器
                container.delete(wait=True)
                raise Exception(f"Failed to install system: {install_result.message}")

            # 启动容器
            container.start(wait=True)

            logger.info(f"Container {container_name} created successfully")

        except Exception as e:
            hs_result = ZMessage(
                success=False, action="VMCreate",
                message=f"容器创建失败: {str(e)}")
            self.logs_set(hs_result)
            return hs_result

        # 通用操作 =============================================================
        return super().VMCreate(vm_conf)

    # 构建容器配置 #############################################################
    def _build_container_config(self, vm_conf: VMConfig) -> dict:
        """构建 LXD 容器配置"""
        config = {
            "security.nesting": "true",
            "security.privileged": "false"  # 非特权容器
        }

        # CPU 限制
        if vm_conf.cpu_num > 0:
            config["limits.cpu"] = str(vm_conf.cpu_num)

        # 内存限制（转换为MB）
        if vm_conf.mem_num > 0:
            config["limits.memory"] = f"{vm_conf.mem_num}MB"

        return config

    # 构建容器设备 #############################################################
    def _build_container_devices(self, vm_conf: VMConfig) -> dict:
        """构建 LXD 容器设备配置"""
        devices = {}

        # 网络设备
        nic_index = 0
        for nic_name, nic_config in vm_conf.nic_all.items():
            # 选择网桥（根据配置选择 nat 或 pub）
            bridge = self.hs_config.network_nat
            # 可以根据某些条件选择 network_pub
            # 例如：if nic_config.is_public: bridge = self.hs_config.network_pub

            device_name = f"eth{nic_index}"
            devices[device_name] = {
                "type": "nic",
                "nictype": "bridged",
                "parent": bridge,
                "name": device_name
            }

            if nic_config.mac_addr:
                devices[device_name]["hwaddr"] = nic_config.mac_addr

            if nic_config.ip4_addr:
                devices[device_name]["ipv4.address"] = nic_config.ip4_addr

            nic_index += 1

        # 根文件系统
        devices["root"] = {
            "type": "disk",
            "path": "/",
            "pool": "default"  # 使用默认存储池
        }

        # 如果指定了硬盘大小
        if vm_conf.hdd_num > 0:
            devices["root"]["size"] = f"{vm_conf.hdd_num}GB"

        return devices

    # 安装虚拟机 ###############################################################
    def VMSetups(self, vm_conf: VMConfig) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result

        try:
            os_name = vm_conf.os_name
            container_name = vm_conf.vm_uuid

            # 判断是使用文件模板还是LXD镜像
            if os_name.endswith('.tar.gz'):
                # 模式1: 从文件系统加载 tar.gz 模板
                template_file = os.path.join(self.hs_config.images_path, os_name)

                if not os.path.exists(template_file):
                    # 提供更友好的错误提示
                    available_templates = []
                    if os.path.exists(self.hs_config.images_path):
                        try:
                            available_templates = [
                                f for f in os.listdir(self.hs_config.images_path)
                                if f.endswith('.tar.gz')
                            ]
                        except Exception:
                            pass

                    error_msg = f"模板文件未找到: {os_name}\n"
                    error_msg += f"搜索路径: {self.hs_config.images_path}\n"
                    if available_templates:
                        error_msg += f"可用模板: {', '.join(available_templates)}"
                    else:
                        error_msg += "该目录下没有可用的 .tar.gz 模板文件"

                    return ZMessage(
                        success=False, action="VInstall",
                        message=error_msg)

                container = client.containers.get(container_name)

                # 停止容器（如果正在运行）
                if container.status == "Running":
                    container.stop(wait=True)

                # 上传并解压模板到容器
                logger.info(f"Installing template {template_file} to container {container_name}")

                # 读取 tar.gz 文件并推送到容器
                with open(template_file, "rb") as f:
                    container.files.put("/", f.read())

                logger.info(f"Template installed successfully from file: {template_file}")

            else:
                # 模式2: 使用LXD镜像列表中的镜像（通过别名）
                logger.info(f"Using LXD image alias: {os_name} for container {container_name}")

                # 检查镜像是否存在
                try:
                    image = client.images.get_by_alias(os_name)
                    logger.info(f"Found image: {image.fingerprint[:12]} with alias {os_name}")
                except NotFound:
                    # 列出可用的镜像
                    available_images = []
                    try:
                        for img in client.images.all():
                            if img.aliases:
                                available_images.extend([alias['name'] for alias in img.aliases])
                    except Exception:
                        pass

                    error_msg = f"LXD镜像未找到: {os_name}\n"
                    if available_images:
                        error_msg += f"可用镜像别名: {', '.join(available_images)}"
                    else:
                        error_msg += "没有可用的LXD镜像，请使用 'lxc image list' 查看"

                    return ZMessage(
                        success=False, action="VInstall",
                        message=error_msg)

                # 删除旧容器（如果存在）
                try:
                    container = client.containers.get(container_name)
                    if container.status == "Running":
                        container.stop(wait=True, timeout=5)
                    container.delete(wait=True)
                    logger.info(f"Deleted existing container {container_name}")
                except NotFound:
                    pass

                # 从镜像创建新容器
                config = {
                    "name": container_name,
                    "source": {
                        "type": "image",
                        "alias": os_name
                    },
                    "config": self._build_container_config(vm_conf),
                    "devices": self._build_container_devices(vm_conf)
                }

                container = client.containers.create(config, wait=True)
                logger.info(f"Container created successfully from LXD image: {os_name}")

            return ZMessage(success=True, action="VInstall")

        except Exception as e:
            return ZMessage(
                success=False, action="VInstall",
                message=f"Failed to install system: {str(e)}")

    # 配置虚拟机 ###############################################################
    def VMUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.NCCreate(vm_conf, True)

        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result

        try:
            container_name = vm_conf.vm_uuid
            container = client.containers.get(container_name)

            # 停止容器
            if container.status == "Running":
                self.VMPowers(container_name, VMPowers.H_CLOSE)

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

            # 更新容器配置
            container.config.update(self._build_container_config(vm_conf))
            container.devices.update(self._build_container_devices(vm_conf))
            container.save(wait=True)

            # 启动容器
            start_result = self.VMPowers(container_name, VMPowers.S_START)
            if not start_result.success:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"容器启动失败: {start_result.message}")

        except Exception as e:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"容器更新失败: {str(e)}")

        # 通用操作 =============================================================
        return super().VMUpdate(vm_conf, vm_last)

    # 删除虚拟机 ###############################################################
    def VMDelete(self, vm_name: str) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result

        try:
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False, action="VMDelete",
                    message=f"容器 {vm_name} 不存在")

            container = client.containers.get(vm_name)

            # 停止容器
            if container.status == "Running":
                self.VMPowers(vm_name, VMPowers.H_CLOSE)

            # 删除网络配置
            self.NCCreate(vm_conf, False)

            # 删除容器
            container.delete(wait=True)

            logger.info(f"Container {vm_name} deleted successfully")

        except NotFound:
            logger.warning(f"Container {vm_name} not found in LXD")
        except Exception as e:
            return ZMessage(
                success=False, action="VMDelete",
                message=f"删除容器失败: {str(e)}")

        # 通用操作 =============================================================
        return super().VMDelete(vm_name)

    # 虚拟机电源 ###############################################################
    def VMPowers(self, vm_name: str, power: VMPowers) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result

        try:
            container = client.containers.get(vm_name)

            if power == VMPowers.S_START:
                if container.status != "Running":
                    container.start(wait=True)
                    logger.info(f"Container {vm_name} started")
                else:
                    logger.info(f"Container {vm_name} is already running")

            elif power == VMPowers.H_CLOSE or power == VMPowers.S_CLOSE:
                logger.info(f"Attempting to stop container {vm_name} with current status: {container.status}")

                if container.status == "Running":
                    timeout = 30 if power == VMPowers.S_CLOSE else 5
                    container.stop(wait=True, timeout=timeout, force=(power == VMPowers.H_CLOSE))
                    logger.info(f"Container {vm_name} stopped successfully")
                elif container.status == "Frozen":
                    # 如果容器处于冻结状态，先解冻再停止
                    container.unfreeze(wait=True)
                    logger.info(f"Container {vm_name} unfrozen")
                    timeout = 30 if power == VMPowers.S_CLOSE else 5
                    container.stop(wait=True, timeout=timeout, force=(power == VMPowers.H_CLOSE))
                    logger.info(f"Container {vm_name} stopped successfully after unfreezing")
                elif container.status in ["Stopped"]:
                    logger.info(f"Container {vm_name} is already stopped")
                else:
                    logger.warning(f"Container {vm_name} has unknown status: {container.status}")

            elif power == VMPowers.S_RESET or power == VMPowers.H_RESET:
                if container.status == "Running":
                    timeout = 30 if power == VMPowers.S_RESET else 5
                    container.restart(wait=True, timeout=timeout, force=(power == VMPowers.H_RESET))
                elif container.status == "Frozen":
                    # 如果容器处于冻结状态，先解冻再重启
                    container.unfreeze(wait=True)
                    timeout = 30 if power == VMPowers.S_RESET else 5
                    container.restart(wait=True, timeout=timeout, force=(power == VMPowers.H_RESET))
                else:
                    container.start(wait=True)
                logger.info(f"Container {vm_name} restarted")

            elif power == VMPowers.A_PAUSE:
                if container.status == "Running":
                    container.freeze(wait=True)
                    logger.info(f"Container {vm_name} frozen (paused)")
                elif container.status == "Frozen":
                    logger.info(f"Container {vm_name} is already frozen")
                else:
                    logger.warning(f"Cannot freeze container {vm_name} with status: {container.status}")
                    return ZMessage(
                        success=False, action="VMPowers",
                        message=f"无法冻结容器 {vm_name}，当前状态: {container.status}")

            elif power == VMPowers.A_WAKED:
                if container.status == "Frozen":
                    container.unfreeze(wait=True)
                    logger.info(f"Container {vm_name} unfrozen (resumed)")
                elif container.status == "Running":
                    logger.info(f"Container {vm_name} is already running")
                else:
                    logger.warning(f"Cannot unfreeze container {vm_name} with status: {container.status}")
                    return ZMessage(
                        success=False, action="VMPowers",
                        message=f"无法解冻容器 {vm_name}，当前状态: {container.status}")

            hs_result = ZMessage(success=True, action="VMPowers")
            self.logs_set(hs_result)

        except NotFound:
            hs_result = ZMessage(
                success=False, action="VMPowers",
                message=f"Container {vm_name} does not exist")
            self.logs_set(hs_result)
            return hs_result
        except Exception as e:
            error_msg = f"电源操作失败: {str(e)}"
            logger.error(f"Power operation failed for container {vm_name}: {str(e)}")
            logger.error(traceback.format_exc())

            hs_result = ZMessage(
                success=False, action="VMPowers",
                message=error_msg)
            self.logs_set(hs_result)
            return hs_result

        # 通用操作 =============================================================
        super().VMPowers(vm_name, power)
        return hs_result

    # 设置虚拟机密码 ###########################################################
    def VMPasswd(self, vm_name: str, os_pass: str) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result

        try:
            container = client.containers.get(vm_name)

            if container.status != "Running":
                return ZMessage(
                    success=False, action="Password",
                    message=f"Container {vm_name} is not running")

            # 执行命令设置密码
            command = ["chpasswd"]
            stdin_data = f"root:{os_pass}\n"

            result = container.execute(
                command,
                stdin_payload=stdin_data,
                stdin_raw=True
            )

            if result.exit_code != 0:
                raise Exception(f"chpasswd command failed: {result.stderr}")

            logger.info(f"Password set for container {vm_name}")

            return ZMessage(success=True, action="Password")

        except NotFound:
            return ZMessage(
                success=False, action="Password",
                message=f"Container {vm_name} does not exist")
        except Exception as e:
            return ZMessage(
                success=False, action="Password",
                message=f"设置密码失败: {str(e)}")

    # 备份虚拟机 ###############################################################
    def VMBackup(self, vm_name: str, vm_tips: str) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result

        vm_conf = self.VMSelect(vm_name)
        if not vm_conf:
            return ZMessage(
                success=False,
                action="Backup",
                message="虚拟机不存在")

        try:
            # 获取容器
            container = client.containers.get(vm_name)

            # 检查容器是否正在运行
            is_running = container.status == "Running"
            if is_running:
                # 先停止容器以确保数据一致性
                container.stop(wait=True, timeout=30)
                logger.info(f"容器 {vm_name} 已停止")

            # 构建备份文件名
            bak_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            bak_file = f"{vm_name}_{bak_time}.tar.gz"
            bak_path = f"{self.hs_config.backup_path}/{bak_file}"

            # 确保备份目录存在
            if self.hs_config.backup_path == "":
                return ZMessage(
                    success=False,
                    action="Backup",
                    message="主机备份目录未设置，请联系管理员")
            if not os.path.exists(self.hs_config.backup_path):
                os.makedirs(self.hs_config.backup_path, exist_ok=True)

            # 导出容器为tar.gz
            logger.info(f"开始备份容器 {vm_name} 到 {bak_path}")

            # 使用LXD的publish功能创建镜像，然后导出
            # 创建临时镜像别名
            image_alias = f"backup-{vm_name}-{bak_time}"
            
            # 先删除可能存在的同名别名镜像
            try:
                old_image = client.images.get_by_alias(image_alias)
                old_image.delete(wait=True)
                logger.info(f"删除旧的临时镜像: {image_alias}")
            except NotFound:
                pass  # 镜像不存在，继续
            
            # 创建新镜像（带别名）
            image = container.publish(wait=True)
            
            # 为镜像添加别名（方便后续清理）
            image.add_alias(image_alias, "Temporary backup image")
            
            # 导出镜像到文件
            # image.export() 返回一个文件对象，需要读取其内容
            exported_data = image.export()
            with open(bak_path, 'wb') as f:
                f.write(exported_data.read())

            # 删除临时镜像
            image.delete(wait=True)
            logger.info(f"临时镜像已删除: {image.fingerprint[:12]}")

            logger.info(
                f"容器 {vm_name} 备份完成，"
                f"文件大小: "
                f"{os.path.getsize(bak_path) / 1024 / 1024:.2f} MB")

            # 记录备份信息
            vm_conf.backups.append(VMBackup(
                backup_time=datetime.datetime.now(),
                backup_name=bak_file,
                backup_hint=vm_tips,
                old_os_name=vm_conf.os_name
            ))

            # 记录备份结果
            hs_result = ZMessage(
                success=True, action="VMBackup",
                message=f"容器备份成功，文件: {bak_file}",
                results={"backup_file": bak_file, "backup_path": bak_path}
            )
            self.vm_saving[vm_name] = vm_conf
            self.logs_set(hs_result)
            self.data_set()
            
            # 如果容器之前在运行，重新启动
            if is_running:
                try:
                    container.start(wait=True)
                    logger.info(f"容器 {vm_name} 已重新启动")
                except Exception as e:
                    logger.warning(f"容器 {vm_name} 重新启动失败: {str(e)}")
            
            return hs_result

        except NotFound:
            return ZMessage(
                success=False, action="VMBackup",
                message=f"容器 {vm_name} 不存在")
        except Exception as e:
            logger.error(f"备份容器失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="VMBackup",
                message=f"备份失败: {str(e)}")

    # 恢复虚拟机 ###############################################################
    def Restores(self, vm_name: str, vm_back: str) -> ZMessage:
        # 连接接口
        client, result = self._connect_lxd()
        if not result.success:
            return result

        # 获取VM配置
        vm_conf = self.VMSelect(vm_name)
        if not vm_conf:
            return ZMessage(
                success=False, action="Restores",
                message=f"容器 {vm_name} 不存在")

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

        # 完整路径
        backup_file = f"{self.hs_config.backup_path}/{vm_back}"

        # 检查备份文件是否存在
        if not os.path.exists(backup_file):
            return ZMessage(
                success=False, action="Restores",
                message=f"备份文件不存在: {vm_back}")

        # 恢复容器
        try:
            # 删除旧容器
            try:
                container = client.containers.get(vm_name)
                # 如果容器正在运行，先停止
                if container.status == "Running":
                    container.stop(wait=True, timeout=5)
                # 删除容器
                container.delete(wait=True)
                logger.info(f"已删除旧容器 {vm_name}")
            except NotFound:
                pass

            # 开始恢复
            logger.info(f"开始恢复容器 {vm_name}，备份文件: {backup_file}")

            # 导入镜像前，先删除可能存在的同名临时镜像
            restore_alias = f"restore-{vm_name}-{vm_back.replace('.tar.gz', '')}"
            try:
                old_image = client.images.get_by_alias(restore_alias)
                old_image.delete(wait=True)
                logger.info(f"删除旧的还原临时镜像: {restore_alias}")
            except NotFound:
                pass  # 镜像不存在，继续
            
            # 导入镜像
            with open(backup_file, 'rb') as f:
                image = client.images.create(f.read(), wait=True)
            
            # 为镜像添加别名（方便识别和后续清理）
            image.add_alias(restore_alias, f"Restore image for {vm_name}")

            logger.info(f"镜像导入成功: {image.fingerprint[:12]}")

            # 从镜像创建容器
            config = {
                "name": vm_name,
                "source": {
                    "type": "image",
                    "fingerprint": image.fingerprint
                }
            }

            container = client.containers.create(config, wait=True)

            # 网络配置
            network_result = self.NCCreate(vm_conf, flag=True)
            if not network_result.success:
                logger.warning(f"网络配置失败: {network_result.message}")

            # 启动容器
            container.start(wait=True)
            vm_conf.os_name = vb_conf.old_os_name
            logger.info(f"容器 {vm_name} 恢复成功")
            
            # 删除临时镜像（还原完成后清理）
            try:
                image.delete(wait=True)
                logger.info(f"还原临时镜像已删除: {image.fingerprint[:12]}")
            except Exception as e:
                logger.warning(f"删除还原临时镜像失败: {str(e)}")

            # 保存配置
            self.vm_saving[vm_name] = vm_conf
            hs_result = ZMessage(
                success=True, action="Restores",
                message=f"容器恢复成功: {vm_name}",
                results={"container_name": vm_name, "image_fingerprint": image.fingerprint[:12]}
            )
            self.logs_set(hs_result)
            self.data_set()
            return hs_result

        except Exception as e:
            logger.error(f"恢复容器失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="Restores",
                message=f"恢复失败: {str(e)}")

    # VM镜像挂载 ###############################################################
    def HDDMount(self, vm_name: str, vm_imgs: SDConfig, in_flag=True) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result

        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="HDDMount",
                    message="容器不存在")

            container = client.containers.get(vm_name)

            # 停止容器
            was_running = container.status == "Running"
            if was_running:
                self.VMPowers(vm_name, VMPowers.H_CLOSE)

            # 挂载点路径
            host_path = os.path.join(self.hs_config.extern_path, vm_imgs.hdd_name)
            container_path = f"/mnt/{vm_imgs.hdd_name}"

            if in_flag:
                # 挂载磁盘
                # 确保主机路径存在
                os.makedirs(host_path, exist_ok=True)

                # 添加磁盘设备
                device_name = f"disk-{vm_imgs.hdd_name}"
                container.devices[device_name] = {
                    "type": "disk",
                    "source": host_path,
                    "path": container_path
                }
                container.save(wait=True)

                vm_imgs.hdd_flag = 1
                self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name] = vm_imgs

                logger.info(f"Mounted {host_path} to container {vm_name} at {container_path}")
            else:
                # 卸载磁盘
                device_name = f"disk-{vm_imgs.hdd_name}"
                if device_name in container.devices:
                    del container.devices[device_name]
                    container.save(wait=True)

                if vm_imgs.hdd_name in self.vm_saving[vm_name].hdd_all:
                    self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name].hdd_flag = 0

                logger.info(f"Unmounted {host_path} from container {vm_name}")

            # 保存配置
            old_conf = deepcopy(self.vm_saving[vm_name])
            self.VMUpdate(self.vm_saving[vm_name], old_conf)
            self.data_set()

            # 重启容器（如果之前在运行）
            if was_running:
                self.VMPowers(vm_name, VMPowers.S_START)

            action_text = "挂载" if in_flag else "卸载"
            return ZMessage(
                success=True, action="HDDMount",
                message=f"磁盘{action_text}成功")

        except NotFound:
            return ZMessage(
                success=False, action="HDDMount",
                message=f"Container {vm_name} does not exist")
        except Exception as e:
            return ZMessage(
                success=False, action="HDDMount",
                message=f"磁盘挂载操作失败: {str(e)}")

    # ISO镜像挂载 ##############################################################
    def ISOMount(self, vm_name: str, vm_imgs: IMConfig, in_flag=True) -> ZMessage:
        # 专用操作 =============================================================
        # LXD 容器不需要 ISO 挂载，返回成功但不执行操作
        return ZMessage(
            success=True, action="ISOMount",
            message="LXD containers do not support ISO mounting")

    # 虚拟机控制台 ##############################################################
    def VMRemote(self, vm_uuid: str, ip_addr: str = "127.0.0.1") -> ZMessage:
        """生成 Web Terminal 访问 URL"""
        # 专用操作 =============================================================
        if vm_uuid not in self.vm_saving:
            return ZMessage(
                success=False,
                action="VCRemote",
                message="虚拟机不存在")

        # 获取虚拟机配置
        vm_conf = self.vm_saving[vm_uuid]
        container_name = vm_conf.vm_uuid

        # 获取虚拟机SSH端口
        wan_port = None
        try:
            all_port = vm_conf.nat_all
            for now_port in all_port:
                if now_port.lan_port == 22:
                    wan_port = now_port.wan_port
                    break
        except Exception as e:
            logger.warning(f"无法获取SSH端口: {container_name}: {str(e)}")

        if not wan_port and self.hs_config.server_pass == "":
            return ZMessage(
                success=False,
                action="VCRemote",
                message="当未设置主机密码时，必须添加一个端口映射到22端口<br/>"
                        "未找到当前虚拟机22端口对应端口映射信息，无法继续")

        # 获取主机外网IP
        if len(self.hs_config.public_addr) == 0:
            return ZMessage(
                success=False,
                action="VCRemote",
                message="主机外网IP不存在")

        public_ip = self.hs_config.public_addr[0]
        if public_ip in ["localhost", "127.0.0.1", ""]:
            public_ip = "127.0.0.1"  # 默认使用本地

        # 启动tty会话web
        tty_port, token = self.web_terminal.open_tty(
            self.hs_config, wan_port, HostServer.change_under(vm_uuid),
            vm_type="lxclxd")
        if tty_port <= 0:
            return ZMessage(
                success=False,
                action="VCRemote",
                message="启动tty会话失败"
            )

        # 添加SSH代理
        try:
            # 使用新的SSH代理管理方法
            target_ip = "127.0.0.1"  # ttyd运行在本机
            success = self.http_manager.proxy_ssh(token, target_ip, tty_port)
            if not success:
                self.web_terminal.stop_tty(tty_port)  # 清理tty
                return ZMessage(
                    success=False,
                    action="VCRemote",
                    message="添加SSH代理失败")
        except Exception as e:
            logger.error(f"SSH代理配置失败: {str(e)}")
            self.web_terminal.stop_tty(tty_port)
            return ZMessage(
                success=False,
                action="VCRemote",
                message=f"SSH代理配置失败: {str(e)}")

        # 构造返回URL
        vnc_port = self.hs_config.remote_port  # SSH代理统一使用1884端口
        url = f"http://{public_ip}:{vnc_port}/{token}"
        logger.info(
            f"VMRemote for {vm_uuid}: "
            f"SSH({public_ip}:{wan_port}) "
            f"-> tty({tty_port}) -> proxy(/{token}) -> {url}")

        # 返回结果
        return ZMessage(
            success=True,
            action="VCRemote",
            message=url,
            results={
                "tty_port": tty_port,
                "token": token,
                "vnc_port": vnc_port,
                "url": url,
                "ssh_port": wan_port
            }
        )

    # 加载备份 #################################################################
    def LDBackup(self, vm_back: str = "") -> ZMessage:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().LDBackup(vm_back)

    # 移除备份 #################################################################
    def RMBackup(self, vm_name: str, vm_back: str = "") -> ZMessage:
        # 删除虚拟机备份文件
        del_files = []
        if os.path.exists(self.hs_config.backup_path):
            try:
                # 扫描备份目录
                for bk_file in os.listdir(self.hs_config.backup_path):
                    # 检查文件名是否以虚拟机名开头
                    if bk_file.startswith(f"{vm_name}_") and \
                            (bk_file == vm_back or vm_back == ""):
                        bk_path = os.path.join(
                            self.hs_config.backup_path, bk_file)
                        os.remove(bk_path)
                        del_files.append(bk_file)
                        logger.info(f"删除备份: {bk_file}")
            except Exception as e:
                logger.warning(f"扫描备份目录失败: {str(e)}")

        # 记录删除的备份文件
        logger.info(f"共删除 {len(del_files)} 个备份文件")
        return ZMessage(success=True,
                        message=f"已删除 {len(del_files)} 个备份文件")

    # 移除磁盘 #################################################################
    def RMMounts(self, vm_name: str, vm_imgs: str = "") -> ZMessage:
        if vm_imgs != "":
            return ZMessage(
                success=True, action="RMMounts",
                message="指定磁盘已删除")

        # 删除容器挂载路径
        if not self.hs_config.extern_path:
            pass  # 没有配置挂载路径，跳过
        else:
            ct_path = f"{self.hs_config.extern_path}/{vm_name}"
            try:
                if os.path.exists(ct_path):
                    shutil.rmtree(ct_path)
                    logger.info(f"删除挂载路径: {ct_path}")
            except Exception as e:
                logger.warning(f"删除挂载失败 {ct_path}: {str(e)}")

        # 返回结果
        return ZMessage(success=True, action="RMMounts", message="删除成功")

    # 端口映射 #################################################################
    def PortsMap(self, map_info: PortData, flag=True) -> ZMessage:
        # 判断是否为远程主机（排除 SSH 转发模式）
        is_remote = (self.hs_config.server_addr not in ["localhost", "127.0.0.1", ""] and
                     not self.hs_config.server_addr.startswith("ssh://"))

        # 如果是远程主机，先建立SSH连接
        if is_remote:
            success, message = self.port_forward.connect_ssh()
            if not success:
                return ZMessage(
                    success=False, action="PortsMap",
                    message=f"SSH 连接失败: {message}")

        # 如果wan_port为0，自动分配一个未使用的端口
        if map_info.wan_port == 0:
            map_info.wan_port = self.port_forward.allocate_port(is_remote)
        else:
            # 检查端口是否已被占用
            existing_ports = self.port_forward.get_host_ports(is_remote)
            if map_info.wan_port in existing_ports:
                if is_remote:
                    self.port_forward.close_ssh()
                return ZMessage(
                    success=False, action="PortsMap",
                    message=f"端口 {map_info.wan_port} 已被占用")

        # 执行端口映射操作
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

        # 关闭 SSH 连接
        if is_remote:
            self.port_forward.close_ssh()

        return hs_result

    # 反向代理 #################################################################
    def ProxyMap(self,
                 pm_info: WebProxy,
                 vm_uuid: str,
                 in_apis: HttpManager,
                 in_flag=True) -> ZMessage:
        # 获取虚拟机端口 ============================================================
        if self.hs_config.server_addr not in ["localhost", "127.0.0.1", ""]:
            pm_info.lan_port = self.FindPort(vm_uuid, pm_info.lan_port)
            pm_info.lan_addr = self.hs_config.server_addr
            if pm_info.lan_port == 0 and in_flag:
                return ZMessage(
                    success=False, action="ProxyMap",
                    message="当主机为远程IP时，必须先添加NAT映射才能代理<br/>"
                            "当前映射的本地端口缺少NAT映射，请先添加映射")
        # 调用父类方法 ==============================================================
        return super().ProxyMap(pm_info, vm_uuid, in_apis, in_flag)
