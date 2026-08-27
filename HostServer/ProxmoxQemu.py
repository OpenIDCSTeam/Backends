import os
import time
import shutil
import datetime
import paramiko
import traceback
from loguru import logger
from copy import deepcopy
from proxmoxer import ProxmoxAPI
from typing import Optional, Tuple, Dict
from HostServer.BasicServer import BasicServer
from HostModule.CommandSafe import safe_shell_exec, safe_list_exec
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.IMConfig import IMConfig
from MainObject.Config.SDConfig import SDConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Config.VMBackup import VMBackup
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig


class HostServer(BasicServer):
    # 宿主机服务 ###############################################################
    def __init__(self, config: HSConfig, **kwargs):
        super().__init__(config, **kwargs)
        super().__load__(**kwargs)
        # Proxmox 客户端连接
        self.proxmox = None

    # 连接到 Proxmox 服务器 ####################################################
    def api_conn(self) -> Tuple[Optional[ProxmoxAPI], ZMessage]:
        try:
            # 如果已经连接直接返回 =============================================
            if self.proxmox is not None:
                return self.proxmox, ZMessage(
                    success=True, action="_connect_proxmox")
            # 从配置中获取连接信息 =============================================
            host = self.hs_config.server_addr + ":8006"
            user = self.hs_config.server_user \
                if hasattr(self.hs_config, 'server_user') else 'root'
            password = self.hs_config.server_pass
            # 连接到Proxmox服务器 ==============================================
            logger.info(f"连接PVE: {host}, user: {user},"
                        f" node: {self.hs_config.launch_path}")
            # 创建Proxmox API连接 ==============================================
            self.proxmox = ProxmoxAPI(
                host, user=user + "@pam", password=password, verify_ssl=False)
            # 测试连接 =========================================================
            self.proxmox.version.get()
            logger.info("PVE连接成功")
            return self.proxmox, ZMessage(success=True, action="api_conn")
        except Exception as e:
            logger.error(f"PVE连接失败: {str(e)}")
            # traceback.print_exc()
            self.proxmox = None
            return None, ZMessage(
                success=False, action="_connect_proxmox",
                message=f"Failed to connect to Proxmox: {str(e)}")

    # 分配新的VMID #############################################################
    def new_vmid(self) -> int:
        """分配新的VMID"""
        try:
            # 连接Proxmox API ==================================================
            client, result = self.api_conn()
            if not result.success:
                logger.warning("无法连接Proxmox，使用默认VMID 100")
                return 100  # 默认起始VMID
            
            # 检查节点名是否配置 ================================================
            if not self.hs_config.launch_path:
                logger.warning("launch_path（PVE节点名）未配置，使用默认VMID 100")
                return 100
            # 获取所有现有的VMID ===============================================
            vms = client.nodes(self.hs_config.launch_path).qemu.get()
            now_vmid = [vm.get('vmid', 0) for vm in vms if vm.get('vmid')]
            
            # 从200开始查找可用的VMID ===========================================
            vmid = 200
            while vmid in now_vmid:
                vmid += 1
            
            logger.info(f"分配新VMID: {vmid}")
            return vmid
            
        except Exception as e:
            logger.error(f"分配VMID失败: {str(e)}")
            traceback.print_exc()
            return 200

    # 获取VMID #################################################################
    def get_vmid(self, vm_conf: VMConfig) -> Optional[int]:
        try:
            # 首先尝试从配置中获取（作为缓存）
            if hasattr(vm_conf, 'vm_data') and 'vmid' in vm_conf.vm_data:
                cached_vmid = vm_conf.vm_data['vmid']
                if cached_vmid:
                    return cached_vmid

            # 如果配置中没有，从API获取
            client, result = self.api_conn()
            if not result.success or not client:
                logger.error(f"无法连接到Proxmox获取VMID: {result.message}")
                return None
            # 获取虚拟机名称（处理下划线转横线的情况）
            vm_name = vm_conf.vm_uuid.replace('_', '-')
            # 从API获取所有虚拟机列表
            vms = client.nodes(self.hs_config.launch_path).qemu.get()
            # 查找匹配的虚拟机
            for vm in vms:
                if vm['name'] == vm_name:
                    vmid = vm['vmid']
                    # 缓存到配置中
                    if not hasattr(vm_conf, 'vm_data'):
                        vm_conf.vm_data = {}
                    vm_conf.vm_data['vmid'] = vmid
                    logger.debug(f"从API获取到虚拟机 {vm_name} 的VMID: {vmid}")
                    return vmid
            logger.warning(f"未找到虚拟机 {vm_name} 的VMID")
            return None
        except Exception as e:
            logger.error(f"获取VMID时出错: {str(e)}")
            traceback.print_exc()
            return None

    # 公共辅助方法 - 获取虚拟机连接和配置 ####################################
    def _get_vm_connection(self, vm_name: str) -> Tuple[Optional[object], Optional[int], Optional[VMConfig], ZMessage]:
        """获取虚拟机连接、VMID和配置的统一方法
        
        Returns:
            (vm_conn, vm_vmid, vm_conf, result_message)
        """
        try:
            # 连接Proxmox API ==============================================
            client, result = self.api_conn()
            if not result.success:
                return None, None, None, result
            
            # 检查虚拟机是否存在 ===========================================
            if vm_name not in self.vm_saving:
                return None, None, None, ZMessage(
                    success=False, action="操作",
                    message=f"虚拟机 {vm_name} 不存在")
            
            # 获取虚拟机配置 ===============================================
            vm_conf = self.vm_saving[vm_name]
            vm_vmid = self.get_vmid(vm_conf)
            if vm_vmid is None:
                return None, None, None, ZMessage(
                    success=False, action="操作",
                    message=f"虚拟机 {vm_name} 的VMID未找到")
            
            # 获取虚拟机连接对象 ===========================================
            vm_conn = client.nodes(self.hs_config.launch_path).qemu(vm_vmid)
            
            return vm_conn, vm_vmid, vm_conf, ZMessage(success=True)
            
        except Exception as e:
            logger.error(f"获取虚拟机连接失败: {str(e)}")
            traceback.print_exc()
            return None, None, None, ZMessage(
                success=False, action="操作",
                message=f"获取虚拟机连接失败: {str(e)}")
    
    # 公共辅助方法 - 检查虚拟机状态 ############################################
    def _check_vm_status(self, vm_conn) -> Optional[str]:
        """检查虚拟机运行状态
        
        Returns:
            虚拟机状态字符串，如'running', 'stopped'等，失败返回None
        """
        try:
            status = vm_conn.status.current.get()
            return status.get('status')
        except Exception as e:
            logger.error(f"检查虚拟机状态失败: {str(e)}")
            traceback.print_exc()
            return None
    
    # 构建网卡配置 #############################################################
    def net_conf(self, vm_conf: VMConfig) -> dict:
        network_config = {}
        nic_index = 0
        for nic_name, nic_conf in vm_conf.nic_all.items():
            nic_keys = "network_" + nic_conf.nic_type
            if hasattr(self.hs_config, nic_keys) \
                    and getattr(self.hs_config, nic_keys, ""):
                bridge = getattr(self.hs_config, nic_keys)
                net_config = f"e1000e,bridge={bridge}"
                if nic_conf.mac_addr:
                    net_config += f",macaddr={nic_conf.mac_addr}"
                network_config[f"net{nic_index}"] = net_config
                nic_index += 1
        return network_config

    # 生成Proxmox启动顺序字符串 ################################################
    # 根据efi_all生成Proxmox boot order字符串，格式如 order=scsi0;scsi1;ide2
    # 设备映射：vm_uuid->scsi0，vm_uuid-hdd_name->scsi1/2...，iso->ide2
    # #########################################################################
    def _proxmox_boot_order(self, vm_conf: VMConfig) -> str:
        if not vm_conf.efi_all:
            return 'order=ide0;ide2'
        # 构建 efi_name -> proxmox设备名 的映射
        device_map = {}
        device_map[vm_conf.vm_uuid] = 'ide0'  # 系统盘
        scsi_idx = 1
        for hdd_name, hdd_data in vm_conf.hdd_all.items():
            if hdd_data.hdd_flag == 0:
                continue
            device_map[f"{vm_conf.vm_uuid}-{hdd_name}"] = f"scsi{scsi_idx}"
            scsi_idx += 1
        ide_idx = 2
        for iso_name in vm_conf.iso_all:
            device_map[iso_name] = f"ide{ide_idx}"
            ide_idx += 1
        # 按efi_all顺序生成设备列表
        ordered = []
        seen = set()
        for efi_item in vm_conf.efi_all:
            dev = device_map.get(efi_item.efi_name)
            if dev and dev not in seen:
                ordered.append(dev)
                seen.add(dev)
        # 将未在efi_all中的设备追加到末尾
        for dev in device_map.values():
            if dev not in seen:
                ordered.append(dev)
                seen.add(dev)
        if not ordered:
            return 'order=ide0;ide2'
        return 'order=' + ';'.join(ordered)

    # 宿主机任务 ###############################################################
    def Crontabs(self) -> bool:
        """定时任务"""
        # 通用操作 =============================================================
        return super().Crontabs()

    # 宿主机状态 ###############################################################
    def HSStatus(self) -> HWStatus:
        """获取宿主机状态"""
        try:
            # 连接到 Proxmox ===================================================
            client, result = self.api_conn()
            if not result.success or not client:
                logger.error(f"无法连接到Proxmox获取状态: {result.message}")
                return super().HSStatus()

            # 获取主机状态 =====================================================
            node_status = client.nodes(self.hs_config.launch_path).status.get()
            # API 可能返回列表，取第一个元素
            if isinstance(node_status, list):
                node_status = node_status[0] if node_status else None

            if node_status:
                hw_status = HWStatus()
                # CPU 使用率 ===================================================
                hw_status.cpu_usage = int(node_status.get('cpu', 0) * 100)
                # 内存使用（MB）================================================
                mem_total = node_status.get('memory', {}).get('total', 0)
                mem_used = node_status.get('memory', {}).get('used', 0)
                hw_status.mem_total = int(mem_total / (1024 * 1024))  # 转换为MB
                hw_status.mem_usage = int(mem_used / (1024 * 1024))  # 转换为MB
                # 磁盘使用（MB）================================================
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
            traceback.print_exc()

        # 通用操作 =============================================================
        return super().HSStatus()

    # 初始宿主机 ###############################################################
    def HSCreate(self) -> ZMessage:
        return super().HSCreate()

    # 还原宿主机 ###############################################################
    def HSDelete(self) -> ZMessage:
        return super().HSDelete()

    # 读取宿主机 ###############################################################
    def HSLoader(self) -> ZMessage:
        # 连接到 Proxmox 服务器
        client, result = self.api_conn()
        if not result.success:
            return result
        # 加载远程控制台配置（websockify + noVNC）==============================
        self.VMLoader()
        # 同步端口转发配置
        # self.ssh_sync()
        return super().HSLoader()

    # 卸载宿主机 ###############################################################
    def HSUnload(self) -> ZMessage:
        # 断开 Proxmox 连接
        self.proxmox = None
        return super().HSUnload()

    # 虚拟机扫描 ###############################################################
    def VMDetect(self) -> ZMessage:
        """扫描并发现虚拟机"""
        try:
            # 连接Proxmox API ==================================================
            client, result = self.api_conn()
            if not result.success:
                return result

            # 获取所有虚拟机列表 ===============================================
            vms = client.nodes(self.hs_config.launch_path).qemu.get()

            # 使用主机配置的filter_name作为前缀过滤 ===========================
            filter_prefix = self.hs_config.filter_name if self.hs_config else ""

            scanned_count = 0
            added_count = 0
            scanned_names = set()

            # 遍历虚拟机列表 ===================================================
            for vm in vms:
                vm_name = vm['name']
                vmid = vm['vmid']

                # 前缀过滤 =====================================================
                if filter_prefix and not vm_name.startswith(filter_prefix):
                    continue

                scanned_count += 1
                scanned_names.add(vm_name)

                # 检查是否已存在 ===============================================
                if vm_name in self.vm_saving:
                    continue

                # 创建默认虚拟机配置 ===========================================
                default_vm_config = VMConfig()
                default_vm_config.vm_uuid = vm_name
                # 保存VMID到配置中（用于后续操作）==============================
                if not hasattr(default_vm_config, 'vm_data'):
                    default_vm_config.vm_data = {}
                default_vm_config.vm_data['vmid'] = vmid

                # 添加到服务器的虚拟机配置中 ===================================
                self.vm_saving[vm_name] = default_vm_config
                added_count += 1

                log_msg = ZMessage(
                    success=True,
                    action="VScanner",
                    message=f"发现并添加虚拟机: {vm_name} (VMID: {vmid})",
                    results={"vm_name": vm_name, "vmid": vmid}
                )
                self.push_log(log_msg)

            # 标记消失/恢复的虚拟机 ============================================
            marked_count, recovered_count = self._mark_missing_vms(scanned_names)

            # 保存到数据库 =====================================================
            if added_count > 0 or marked_count > 0 or recovered_count > 0:
                success = self.data_set()
                if not success:
                    return ZMessage(
                        success=False, action="VScanner",
                        message="保存扫描的虚拟机到数据库失败")

            return ZMessage(
                success=True,
                action="VScanner",
                message=f"扫描完成。共扫描到{scanned_count}个虚拟机，新增{added_count}个，标记删除{marked_count}个，恢复{recovered_count}个。",
                results={
                    "scanned": scanned_count,
                    "added": added_count,
                    "marked_deleted": marked_count,
                    "recovered": recovered_count,
                    "prefix_filter": filter_prefix
                }
            )

        except Exception as e:
            logger.error(f"扫描虚拟机时出错: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="VScanner",
                message=f"扫描虚拟机时出错: {str(e)}")

    # 创建虚拟机 ###############################################################
    def VMCreate(self, vm_conf: VMConfig) -> ZMessage:
        logger.info(f"[{self.hs_config.server_name}] 开始创建虚拟机: {vm_conf.vm_uuid}")
        logger.info(f"  - CPU: {vm_conf.cpu_num}核, 内存: {vm_conf.mem_num}MB")
        logger.info(f"  - 网卡数量: {len(vm_conf.nic_all)}个")
        logger.info(f"  - 系统镜像: {vm_conf.os_name}")
        
        # 替换名称 ==================================================
        vm_conf.vm_uuid = vm_conf.vm_uuid.replace('_', '-')
        # 网络检查 ==================================================
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            logger.error(f"[{self.hs_config.server_name}] 网络检查失败: {net_result.message}")
            return net_result
        # 连接Proxmox API ===========================================
        client, result = self.api_conn()
        if not result.success:
            logger.error(f"[{self.hs_config.server_name}] Proxmox连接失败: {result.message}")
            return result
        # 分配VMID ==================================================
        vm_vmid = self.new_vmid()
        logger.info(f"[{self.hs_config.server_name}] 分配VMID: {vm_vmid}")
        if not hasattr(vm_conf, 'vm_data'):
            vm_conf.vm_data = {}
        vm_conf.vm_data['vmid'] = vm_vmid
        # 创建虚拟机 ================================================
        try:  # 构建虚拟机配置 --------------------------------------
            # 填充efi_all默认启动项顺序 ============================
            if not vm_conf.efi_all:
                vm_conf.efi_all = self.efi_build(vm_conf)
            # 生成Proxmox启动顺序 ==================================
            boot_order = self._proxmox_boot_order(vm_conf)
            # 根据镜像名判断操作系统类型
            os_name_lower = (vm_conf.os_name or '').lower()
            if any(k in os_name_lower for k in ('win', 'windows')):
                ostype = 'win11' if 'win11' in os_name_lower or 'win-11' in os_name_lower else 'win10'
            else:
                ostype = 'l26'
            config = {
                'vmid': vm_vmid,
                'name': vm_conf.vm_uuid,
                'memory': vm_conf.mem_num,
                'cores': vm_conf.cpu_num,
                'sockets': 1,
                'cpu': 'host',  # 使用宿主机CPU特性，兼容性最佳
                'ostype': ostype,
                'bios': 'ovmf',  # 使用 UEFI 模式
                'scsihw': 'virtio-scsi-single',
                'efidisk0': 'local:1,efitype=4m',  # EFI 磁盘，不预置Secure Boot密钥
            }
            # 配置网卡 ------------------------------------------
            config.update(self.net_conf(vm_conf))
            # 创建虚拟机 --------------------------------------------
            # 检查节点名是否配置 ============================================
            if not self.hs_config.launch_path:
                raise ValueError("launch_path（PVE节点名）未配置，请在服务器配置中填写PVE节点名称（如: pve）")
            logger.info(f"[{self.hs_config.server_name}] 正在创建虚拟机配置...")
            client.nodes(self.hs_config.launch_path).qemu.create(**config)
            logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_conf.vm_uuid} (VMID: {vm_vmid}) 创建成功")
            
            # 配置GPU直通 -------------------------------------------
            if vm_conf.pci_num > 0 and vm_conf.pci_all:
                logger.info(f"[{self.hs_config.server_name}] 配置PCI直通，共 {len(vm_conf.pci_all)} 个设备")
                try:
                    vm_conn = client.nodes(self.hs_config.launch_path).qemu(vm_vmid)
                    # 遍历pci_all，逐个添加PCI设备直通
                    # 格式: hostpci0: 01:00.0,pcie=1
                    gpu_config = {}
                    for idx, (pci_key, pci_cfg) in enumerate(vm_conf.pci_all.items()):
                        if pci_cfg.gpu_uuid:
                            gpu_config[f'hostpci{idx}'] = f"{pci_cfg.gpu_uuid},pcie=1"
                            logger.info(f"[{self.hs_config.server_name}] PCI设备{idx}: {pci_cfg.gpu_uuid}")
                    if gpu_config:
                        vm_conn.config.put(**gpu_config)
                        logger.info(f"[{self.hs_config.server_name}] PCI直通配置成功")
                except Exception as gpu_error:
                    logger.warning(f"[{self.hs_config.server_name}] PCI直通配置失败: {str(gpu_error)}")
            
            # 配置路由器绑定（iKuai层面）----------------------------
            logger.info(f"[{self.hs_config.server_name}] 配置路由器IP绑定...")
            ikuai_result = super().IPBinder(vm_conf, True)
            if not ikuai_result.success:
                logger.warning(f"[{self.hs_config.server_name}] iKuai路由器绑定失败: {ikuai_result.message}")
            else:
                logger.info(f"[{self.hs_config.server_name}] 路由器IP绑定成功")
            
            # 安装系统 ----------------------------------------------
            logger.info(f"[{self.hs_config.server_name}] 开始安装系统镜像...")
            result = self.VMSetups(vm_conf)
            if not result.success:
                logger.warning(f"[{self.hs_config.server_name}] 系统安装失败: {result.message}")
            else:
                logger.info(f"[{self.hs_config.server_name}] 系统安装完成")

            # 配置VNC直通端口（创建时立即写入，无需重启）--------------
            try:
                vnc_port = int(vm_conf.vc_port) if hasattr(vm_conf, 'vc_port') and vm_conf.vc_port else (5900 + int(vm_vmid))
                vnc_id = vnc_port - 5900
                vnc_arg = f"-vnc 0.0.0.0:{vnc_id}"
                vm_conn = client.nodes(self.hs_config.launch_path).qemu(vm_vmid)
                current_config = vm_conn.config.get()
                current_args = current_config.get('args', '')
                if vnc_arg not in current_args:
                    import re
                    new_args = re.sub(r'-vnc\s+\S+', '', current_args).strip()
                    new_args = f"{new_args} {vnc_arg}".strip()
                    vm_conn.config.put(args=new_args)
                    logger.info(f"[{self.hs_config.server_name}] 已为VM {vm_vmid} 配置VNC直通: {vnc_arg} (端口:{vnc_port})")
                # 同步vc_port到vm_conf
                vm_conf.vc_port = str(vnc_port)
            except Exception as vnc_err:
                logger.warning(f"[{self.hs_config.server_name}] VNC配置写入失败: {vnc_err}")

            # 启动虚拟机 --------------------------------------------
            # 注意：此时 vm_conf 尚未写入 self.vm_saving（将在 super().VMCreate 中写入），
            # 因此不能走 self.VMPowers（其内部通过 vm_finds 查 vm_saving 会返回 None）。
            # 直接通过 PVE API 启动虚拟机，避免时序问题。
            logger.info(f"[{self.hs_config.server_name}] 启动虚拟机...")
            try:
                vm_conn = client.nodes(self.hs_config.launch_path).qemu(vm_vmid)
                cur_status = vm_conn.status.current.get()
                if cur_status.get('status') != 'running':
                    vm_conn.status.start.post()
                    logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_conf.vm_uuid} 启动指令已下发")
                else:
                    logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_conf.vm_uuid} 已在运行")
            except Exception as start_err:
                logger.warning(f"[{self.hs_config.server_name}] 启动虚拟机失败: {start_err}")
        # 捕获所有异常 ==============================================
        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] 虚拟机创建失败: {str(e)}")
            logger.error(f"[{self.hs_config.server_name}] 错误详情:", exc_info=True)
            traceback.print_exc()
            hs_result = ZMessage(
                success=False, action="VMCreate",
                message=f"虚拟机创建失败: {str(e)}")
            self.logs_set(hs_result)
            return hs_result
        # 通用操作 ==================================================
        logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_conf.vm_uuid} 创建流程完成")
        self.data_set()
        return super().VMCreate(vm_conf)

    # 安装虚拟机 ###############################################################
    def VMSetups(self, vm_conf: VMConfig) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self.api_conn()
        if not result.success:
            return result
        # 获取VMID =============================================================
        vm_vmid = self.get_vmid(vm_conf)
        if vm_vmid is None:
            return ZMessage(
                success=False, action="VInstall",
                message=f"虚拟机 {vm_conf.vm_uuid} 的VMID未找到")
        # 检查配置 =============================================================
        if not vm_conf.os_name:
            return ZMessage(success=False, action="VInstall", message="未指定系统镜像")
        if not self.hs_config.images_path:
            return ZMessage(
                success=False, action="VInstall", message="未配置镜像路径")
        # 复制镜像 =============================================================
        try:
            import posixpath
            # 计算启动顺序（磁盘挂载后设置）====================================
            if not vm_conf.efi_all:
                vm_conf.efi_all = self.efi_build(vm_conf)
            boot_order = self._proxmox_boot_order(vm_conf)
            # 从源文件名中提取扩展名，保持原始格式
            _, src_ext = posixpath.splitext(vm_conf.os_name)
            if not src_ext:
                src_ext = '.qcow2'  # 默认格式
            vm_disk_dir = f"/var/lib/vz/images/{vm_vmid}"
            system_storage = self.hs_config.system_path or "local"
            # 查询当前虚拟机已有磁盘编号，计算下一个可用编号 ==================
            # （EFI磁盘会占用disk-0，系统盘需要用disk-1）
            next_disk_idx = self._get_next_disk_index(client, vm_vmid)
            disk_name = f"vm-{vm_vmid}-disk-{next_disk_idx}{src_ext}"
            dest_image = f"{vm_disk_dir}/{disk_name}"
            # 判断是否为PVE存储名（不含/则视为存储名，走import流程）=============
            images_is_storage = '/' not in self.hs_config.images_path
            if images_is_storage:
                # import模式：images_path为PVE存储名，通过API查询存储物理路径 ==
                import_storage = self.hs_config.images_path
                # 通过PVE API获取存储配置，拿到真实物理路径 =====================
                storage_path = None
                try:
                    storage_info = client.nodes(self.hs_config.launch_path).storage(import_storage).get()
                    # API 可能返回 dict 或 list，兼容处理 =======================
                    if isinstance(storage_info, list):
                        for item in storage_info:
                            if item.get('storage') == import_storage or 'path' in item:
                                storage_path = item.get('path')
                                break
                    elif isinstance(storage_info, dict):
                        storage_path = storage_info.get('path')
                    # 回退：从全局存储配置中查找 ================================
                    if not storage_path:
                        all_storages = client.storage.get()
                        for st in all_storages:
                            if st.get('storage') == import_storage:
                                storage_path = st.get('path')
                                break
                except Exception as se:
                    logger.warning(f"查询存储 {import_storage} 路径失败: {se}")
                # 默认回退路径（local存储）=====================================
                if not storage_path:
                    storage_path = "/var/lib/vz" if import_storage == "local" else f"/mnt/pve/{import_storage}"
                    logger.warning(f"未从API获取到存储路径，使用默认路径: {storage_path}")
                # 拼接 import 目录的绝对路径 ===================================
                src_file_abs = posixpath.join(storage_path, "template", "import", vm_conf.os_name)
                # 兼容旧目录结构：部分用户直接放 <storage_path>/import/xxx ====
                src_file_alt = posixpath.join(storage_path, "import", vm_conf.os_name)
                import_cmd = (f"qm importdisk {vm_vmid} {src_file_abs} "
                              f"{system_storage} --format qcow2")
                if self.flag_web():
                    # 远程模式：通过SSH执行importdisk ===========================
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        self.hs_config.server_addr,
                        username=self.hs_config.server_user,
                        password=self.hs_config.server_pass)
                    # 检查主路径是否存在，不存在则尝试备用路径 =================
                    stdin, stdout, stderr = ssh.exec_command(
                        f"test -f {src_file_abs} && echo 'exists' || echo 'not_exists'")
                    if stdout.read().decode().strip() != 'exists':
                        stdin, stdout, stderr = ssh.exec_command(
                            f"test -f {src_file_alt} && echo 'exists' || echo 'not_exists'")
                        if stdout.read().decode().strip() == 'exists':
                            src_file_abs = src_file_alt
                            import_cmd = (f"qm importdisk {vm_vmid} {src_file_abs} "
                                          f"{system_storage} --format qcow2")
                        else:
                            ssh.close()
                            return ZMessage(
                                success=False, action="VInstall",
                                message=f"镜像文件不存在: {src_file_abs} 或 {src_file_alt}")
                    stdin, stdout, stderr = ssh.exec_command(import_cmd)
                    exit_status = stdout.channel.recv_exit_status()
                    if exit_status != 0:
                        error_msg = stderr.read().decode()
                        ssh.close()
                        return ZMessage(
                            success=False, action="VInstall",
                            message=f"importdisk失败: {error_msg}")
                    ssh.close()
                    logger.info(f"通过SSH importdisk: {src_file_abs} -> {system_storage}")
                else:
                    # 本地模式：直接执行importdisk ==============================
                    if not os.path.exists(src_file_abs):
                        if os.path.exists(src_file_alt):
                            src_file_abs = src_file_alt
                            import_cmd = (f"qm importdisk {vm_vmid} {src_file_abs} "
                                          f"{system_storage} --format qcow2")
                        else:
                            return ZMessage(
                                success=False, action="VInstall",
                                message=f"镜像文件不存在: {src_file_abs} 或 {src_file_alt}")
                    ok, out, err = safe_shell_exec(import_cmd, timeout=120, allow_pipe=True)
                    if not ok:
                        # 本地执行失败，回退到SSH方式执行 ========================
                        logger.warning(f"本地importdisk失败(exit={exit_status})，尝试SSH回退执行...")
                        try:
                            ssh = paramiko.SSHClient()
                            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                            ssh.connect(
                                self.hs_config.server_addr,
                                username=self.hs_config.server_user,
                                password=self.hs_config.server_pass)
                            # SSH检查文件是否存在 ===============================
                            stdin, stdout, stderr = ssh.exec_command(
                                f"test -f {src_file_abs} && echo 'exists' || echo 'not_exists'")
                            if stdout.read().decode().strip() != 'exists':
                                stdin, stdout, stderr = ssh.exec_command(
                                    f"test -f {src_file_alt} && echo 'exists' || echo 'not_exists'")
                                if stdout.read().decode().strip() == 'exists':
                                    src_file_abs = src_file_alt
                                    import_cmd = (f"qm importdisk {vm_vmid} {src_file_abs} "
                                                  f"{system_storage} --format qcow2")
                                else:
                                    ssh.close()
                                    return ZMessage(
                                        success=False, action="VInstall",
                                        message=f"SSH回退: 镜像文件不存在: {src_file_abs} 或 {src_file_alt}")
                            stdin, stdout, stderr = ssh.exec_command(import_cmd)
                            ssh_exit = stdout.channel.recv_exit_status()
                            if ssh_exit != 0:
                                error_msg = stderr.read().decode()
                                ssh.close()
                                return ZMessage(
                                    success=False, action="VInstall",
                                    message=f"SSH回退importdisk也失败: {error_msg}")
                            ssh.close()
                            logger.info(f"SSH回退importdisk成功: {src_file_abs} -> {system_storage}")
                        except Exception as ssh_err:
                            return ZMessage(
                                success=False, action="VInstall",
                                message=f"SSH回退执行异常: {str(ssh_err)}")
                    else:
                        logger.info(f"本地importdisk: {src_file_abs} -> {system_storage}")
                # importdisk后磁盘进入unused状态，需挂载 ========================
                # 刷新存储，确保PVE识别到新磁盘文件 ============================
                self._refresh_storage(client, system_storage)
                vm_conn = client.nodes(self.hs_config.launch_path).qemu(vm_vmid)
                # 查询实际的unused磁盘路径（importdisk自动分配编号）============
                actual_disk = self._find_unused_disk(vm_conn, system_storage, vm_vmid)
                if not actual_disk:
                    actual_disk = f"{system_storage}:{vm_vmid}/{disk_name}"
                vm_conn.config.put(ide0=actual_disk)
                # 设置启动项（磁盘挂载后才能生效）================================
                vm_conn.config.put(boot=boot_order, bootdisk='ide0')
                # 根据 hdd_num(MB) 扩容系统盘到目标大小 ==========================
                self._resize_system_disk(vm_conn, 'ide0', vm_conf.hdd_num)
            else:
                # 复制模式：images_path为物理路径，直接cp复制 ===================
                if self.flag_web():
                    # 远程模式：src_file 是远程服务器上的路径，使用 posixpath.join
                    src_file = posixpath.join(self.hs_config.images_path, vm_conf.os_name)
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        self.hs_config.server_addr,
                        username=self.hs_config.server_user,
                        password=self.hs_config.server_pass)
                    # 检查远程镜像文件是否存在
                    stdin, stdout, stderr = ssh.exec_command(f"test -f {src_file} && echo 'exists' || echo 'not_exists'")
                    file_check = stdout.read().decode().strip()
                    if file_check != 'exists':
                        ssh.close()
                        return ZMessage(
                            success=False, action="VInstall",
                            message=f"镜像文件不存在: {src_file}")
                    # 在远程服务器上复制镜像文件
                    ssh.exec_command(f"mkdir -p {vm_disk_dir}")
                    copy_cmd = f"cp {src_file} {dest_image}"
                    stdin, stdout, stderr = ssh.exec_command(copy_cmd)
                    exit_status = stdout.channel.recv_exit_status()
                    if exit_status != 0:
                        error_msg = stderr.read().decode()
                        ssh.close()
                        return ZMessage(
                            success=False, action="VInstall",
                            message=f"复制镜像失败: {error_msg}")
                    ssh.close()
                    logger.info(f"通过SSH复制镜像: {src_file} -> {dest_image}")
                else:
                    # 本地模式：src_file 是 Linux 路径，使用 posixpath.join
                    src_file = posixpath.join(self.hs_config.images_path, vm_conf.os_name)
                    local_ok = False
                    try:
                        if not os.path.exists(src_file):
                            raise FileNotFoundError(f"镜像文件不存在: {src_file}")
                        os.makedirs(vm_disk_dir, exist_ok=True)
                        shutil.copy2(src_file, dest_image)
                        local_ok = True
                        logger.info(f"本地复制镜像: {src_file} -> {dest_image}")
                    except Exception as local_err:
                        logger.warning(f"本地复制镜像失败({local_err})，尝试SSH回退执行...")
                    if not local_ok:
                        # 本地执行失败，回退到SSH方式执行 ========================
                        try:
                            ssh = paramiko.SSHClient()
                            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                            ssh.connect(
                                self.hs_config.server_addr,
                                username=self.hs_config.server_user,
                                password=self.hs_config.server_pass)
                            # SSH检查文件是否存在 ===============================
                            stdin, stdout, stderr = ssh.exec_command(
                                f"test -f {src_file} && echo 'exists' || echo 'not_exists'")
                            if stdout.read().decode().strip() != 'exists':
                                ssh.close()
                                return ZMessage(
                                    success=False, action="VInstall",
                                    message=f"SSH回退: 镜像文件不存在: {src_file}")
                            ssh.exec_command(f"mkdir -p {vm_disk_dir}")
                            copy_cmd = f"cp {src_file} {dest_image}"
                            stdin, stdout, stderr = ssh.exec_command(copy_cmd)
                            ssh_exit = stdout.channel.recv_exit_status()
                            if ssh_exit != 0:
                                error_msg = stderr.read().decode()
                                ssh.close()
                                return ZMessage(
                                    success=False, action="VInstall",
                                    message=f"SSH回退复制镜像也失败: {error_msg}")
                            ssh.close()
                            logger.info(f"SSH回退复制镜像成功: {src_file} -> {dest_image}")
                        except Exception as ssh_err:
                            return ZMessage(
                                success=False, action="VInstall",
                                message=f"SSH回退执行异常: {str(ssh_err)}")
                # 分配磁盘 ======================================================
                # 刷新存储，确保PVE识别到新复制的磁盘文件 ======================
                self._refresh_storage(client, system_storage)
                vm_conn = client.nodes(self.hs_config.launch_path).qemu(vm_vmid)
                # 查询实际的unused磁盘路径（cp后PVE可能分配不同编号）==========
                actual_disk = self._find_unused_disk(vm_conn, system_storage, vm_vmid)
                if not actual_disk:
                    actual_disk = f"{system_storage}:{vm_vmid}/{disk_name}"
                vm_conn.config.put(ide0=actual_disk)
                # 设置启动项（磁盘挂载后才能生效）================================
                vm_conn.config.put(boot=boot_order, bootdisk='ide0')
                # 根据 hdd_num(MB) 扩容系统盘到目标大小 ==========================
                self._resize_system_disk(vm_conn, 'ide0', vm_conf.hdd_num)
            logger.info(f"虚拟机 {vm_conf.vm_uuid} 系统安装完成")
            return ZMessage(success=True, action="VInstall", message="安装成功")
        # 处理异常 ==============================================================
        except Exception as e:
            traceback.print_exc()
            return ZMessage(
                success=False, action="VInstall",
                message=f"系统安装失败: {str(e)}")

    # 配置虚拟机 ###############################################################
    def VMUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        logger.info(f"[{self.hs_config.server_name}] 开始更新虚拟机配置: {vm_conf.vm_uuid}")
        try:
            # 网络检查 =========================================================
            vm_conf, net_result = self.NetCheck(vm_conf)
            if not net_result.success:
                logger.error(f"[{self.hs_config.server_name}] 网络检查失败: {net_result.message}")
                return net_result
            
            # 连接Proxmox API ==================================================
            client, result = self.api_conn()
            if not result.success:
                return result
            
            # 获取VMID =========================================================
            vmid = self.get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {vm_conf.vm_uuid} 的VMID未找到")
            
            vm = client.nodes(self.hs_config.launch_path).qemu(vmid)
            
            # 停止机器 =========================================================
            status = vm.status.current.get()
            if status['status'] == 'running':
                logger.info(f"[{self.hs_config.server_name}] 停止虚拟机以进行配置更新...")
                self.VMPowers(vm_conf.vm_uuid, VMPowers.H_CLOSE)
                # 等待虚拟机真正停止（最多等待30秒）
                for _wait in range(30):
                    _status = vm.status.current.get()
                    if _status.get('status') == 'stopped':
                        logger.info(f"[{self.hs_config.server_name}] 虚拟机已停止，耗时{_wait+1}秒")
                        break
                    time.sleep(1)
                else:
                    logger.warning(f"[{self.hs_config.server_name}] 等待虚拟机停止超时(30秒)，继续执行")
            
            # 重装系统 =========================================================
            if vm_conf.os_name and vm_conf.os_name != vm_last.os_name and vm_last.os_name != "":
                logger.info(f"[{self.hs_config.server_name}] 检测到系统镜像变更，重新安装系统...")
                logger.info(f"  - 旧镜像: {vm_last.os_name}")
                logger.info(f"  - 新镜像: {vm_conf.os_name}")
                install_result = self.VMSetups(vm_conf)
                if not install_result.success:
                    logger.error(f"[{self.hs_config.server_name}] 系统重装失败: {install_result.message}")
                    return install_result
            elif not vm_conf.os_name:
                # 用户选择"不变更系统"，保持原系统名称
                vm_conf.os_name = vm_last.os_name
            
            # 更新配置 =========================================================
            config_updates = {}
            if vm_conf.cpu_num != vm_last.cpu_num and vm_conf.cpu_num > 0:
                logger.info(f"[{self.hs_config.server_name}] CPU配置变更: {vm_last.cpu_num}核 -> {vm_conf.cpu_num}核")
                config_updates['cores'] = vm_conf.cpu_num
            if vm_conf.mem_num != vm_last.mem_num and vm_conf.mem_num > 0:
                logger.info(f"[{self.hs_config.server_name}] 内存配置变更: {vm_last.mem_num}MB -> {vm_conf.mem_num}MB")
                config_updates['memory'] = vm_conf.mem_num
            
            # 配置网卡 =========================================================
            config_updates.update(self.net_conf(vm_conf))
            
            # 更新启动项顺序 ===================================================
            if vm_conf.efi_all:
                boot_order = self._proxmox_boot_order(vm_conf)
                config_updates['boot'] = boot_order
                logger.info(f"[{self.hs_config.server_name}] 更新启动顺序: {boot_order}")
            
            # 配置PCI直通 =======================================================
            if vm_conf.pci_num > 0 and vm_conf.pci_all:
                # 检查PCI配置是否变更
                new_pci_keys = set(vm_conf.pci_all.keys())
                old_pci_keys = set(vm_last.pci_all.keys()) if vm_last.pci_all else set()
                if new_pci_keys != old_pci_keys:
                    logger.info(f"[{self.hs_config.server_name}] PCI配置变更: {old_pci_keys} -> {new_pci_keys}")
                    try:
                        # 移除旧的PCI配置
                        for idx in range(len(old_pci_keys)):
                            try:
                                vm.config.put(delete=f'hostpci{idx}')
                            except Exception:
                                pass
                        logger.info(f"[{self.hs_config.server_name}] 已移除旧PCI配置")

                        # 添加新的PCI配置
                        for idx, (pci_key, pci_cfg) in enumerate(vm_conf.pci_all.items()):
                            if pci_cfg.gpu_uuid:
                                config_updates[f'hostpci{idx}'] = f"{pci_cfg.gpu_uuid},pcie=1"
                                logger.info(f"[{self.hs_config.server_name}] 已添加PCI配置{idx}: {pci_cfg.gpu_uuid}")
                    except Exception as gpu_error:
                        logger.warning(f"[{self.hs_config.server_name}] PCI配置更新失败: {str(gpu_error)}")
            elif vm_conf.pci_num == 0 and vm_last.pci_all:
                # 移除PCI直通
                logger.info(f"[{self.hs_config.server_name}] 移除PCI直通配置")
                try:
                    for idx in range(len(vm_last.pci_all)):
                        try:
                            vm.config.put(delete=f'hostpci{idx}')
                        except Exception:
                            pass
                    logger.info(f"[{self.hs_config.server_name}] PCI直通已移除")
                except Exception as gpu_error:
                    logger.warning(f"[{self.hs_config.server_name}] 移除GPU配置失败: {str(gpu_error)}")
            
            if config_updates:
                logger.info(f"[{self.hs_config.server_name}] 应用配置更新...")
                vm.config.put(**config_updates)
                logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_conf.vm_uuid} 配置已更新")
            
            # 更新绑定 =========================================================
            logger.info(f"[{self.hs_config.server_name}] 更新路由器IP绑定...")
            super().IPBinder(vm_last, False)
            ikuai_result = super().IPBinder(vm_conf, True)
            if not ikuai_result.success:
                logger.warning(f"[{self.hs_config.server_name}] iKuai路由器绑定失败: {ikuai_result.message}")
            else:
                logger.info(f"[{self.hs_config.server_name}] 路由器IP绑定更新成功")
            
            # 配置VNC直通端口（更新时同步写入，兼容旧虚拟机）=====================
            try:
                vnc_port = int(vm_conf.vc_port) if hasattr(vm_conf, 'vc_port') and vm_conf.vc_port else (5900 + int(vmid))
                vnc_id = vnc_port - 5900
                vnc_arg = f"-vnc 0.0.0.0:{vnc_id}"
                current_config = vm.config.get()
                current_args = current_config.get('args', '')
                if vnc_arg not in current_args:
                    import re
                    new_args = re.sub(r'-vnc\s+\S+', '', current_args).strip()
                    new_args = f"{new_args} {vnc_arg}".strip()
                    vm.config.put(args=new_args)
                    logger.info(f"[{self.hs_config.server_name}] 已为VM {vmid} 补写VNC配置: {vnc_arg} (端口:{vnc_port})")
                # 同步vc_port到vm_conf
                vm_conf.vc_port = str(vnc_port)
            except Exception as vnc_err:
                logger.warning(f"[{self.hs_config.server_name}] VNC配置写入失败: {vnc_err}")

            # 启动机器 =========================================================
            logger.info(f"[{self.hs_config.server_name}] 启动虚拟机...")
            start_result = self.VMPowers(vm_conf.vm_uuid, VMPowers.S_START)
            if not start_result.success:
                logger.error(f"[{self.hs_config.server_name}] 虚拟机启动失败: {start_result.message}")
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机启动失败: {start_result.message}")
            
            return super().VMUpdate(vm_conf, vm_last)
            
        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] 虚拟机更新失败: {str(e)}")
            logger.error(f"[{self.hs_config.server_name}] 错误详情:", exc_info=True)
            traceback.print_exc()
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机更新失败: {str(e)}")

    # 删除虚拟机 ###############################################################
    def VMDelete(self, vm_name: str, rm_back=True) -> ZMessage:
        logger.info(f"[{self.hs_config.server_name}] 开始删除虚拟机: {vm_name}")
        try:
            # 连接Proxmox API ==================================================
            client, result = self.api_conn()
            if not result.success:
                logger.error(f"[{self.hs_config.server_name}] Proxmox连接失败: {result.message}")
                return result
            
            # 获取虚拟机配置 ===================================================
            vm_conf = self.vm_finds(vm_name)
            if vm_conf is None:
                logger.error(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} 不存在")
                return ZMessage(
                    success=False, action="VMDelete",
                    message=f"虚拟机 {vm_name} 不存在")
            
            # 获取虚拟机VMID ===================================================
            vm_vmid = self.get_vmid(vm_conf)
            if vm_vmid is None:
                return ZMessage(
                    success=False, action="VMDelete",
                    message=f"虚拟机 {vm_name} VMID未找到")
            
            # 获取虚拟机对象 ===================================================
            vm = client.nodes(self.hs_config.launch_path).qemu(vm_vmid)
            
            # 停止虚拟机 =======================================================
            status = vm.status.current.get()
            if status['status'] == 'running':
                logger.info(f"[{self.hs_config.server_name}] 虚拟机正在运行，先停止...")
                self.VMPowers(vm_name, VMPowers.H_CLOSE)
                # 等待虚拟机完全停止（最多等待60秒）
                for i in range(30):
                    time.sleep(2)
                    cur_status = vm.status.current.get()
                    if cur_status['status'] == 'stopped':
                        logger.info(f"[{self.hs_config.server_name}] 虚拟机已停止")
                        break
                else:
                    logger.warning(f"[{self.hs_config.server_name}] 等待超时，尝试强制停止...")
                    vm.status.stop.post()
                    time.sleep(5)
            
            # 删除路由器绑定（iKuai层面）=======================================
            logger.info(f"[{self.hs_config.server_name}] 删除路由器IP绑定...")
            super().IPBinder(vm_conf, False)
            
            # 删除虚拟机（会自动删除网卡配置）==================================
            logger.info(f"[{self.hs_config.server_name}] 正在删除虚拟机 (VMID: {vm_vmid})...")
            vm.delete()
            logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} (VMID: {vm_vmid}) 删除成功")
            
            # 通用操作 =========================================================
            return super().VMDelete(vm_name)
            
        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] 删除虚拟机失败: {str(e)}")
            logger.error(f"[{self.hs_config.server_name}] 错误详情:", exc_info=True)
            traceback.print_exc()
            return ZMessage(
                success=False, action="VMDelete",
                message=f"删除虚拟机失败: {str(e)}")

    # 虚拟机电源 ###############################################################
    def VMPowers(self, vm_name: str, power: VMPowers) -> ZMessage:
        """虚拟机电源管理"""
        # 先调用父类方法设置中间状态
        super().VMPowers(vm_name, power)
        
        client, result = self.api_conn()
        if not result.success:
            return result

        try:
            vm_conf = self.vm_finds(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False, action="VMPowers",
                    message=f"虚拟机 {vm_name} 不存在")

            vmid = self.get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="VMPowers",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            vm = client.nodes(self.hs_config.launch_path).qemu(vmid)
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
                    # 启动监控线程，等待状态变为 SUSPEND
                    self._monitor_power_operation(vm_name, VMPowers.A_PAUSE, VMPowers.ON_SAVE, VMPowers.SUSPEND)
                else:
                    logger.warning(f"虚拟机 {vm_name} 未运行，无法暂停")

            elif power == VMPowers.A_WAKED:
                if status['status'] == 'paused':
                    vm.status.resume.post()
                    logger.info(f"虚拟机 {vm_name} 已恢复")
                    # 启动监控线程，等待状态变为 STARTED
                    self._monitor_power_operation(vm_name, VMPowers.A_WAKED, VMPowers.ON_WAKE, VMPowers.STARTED)
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

        return hs_result

    # 获取虚拟机实际状态（从API）==============================================
    def GetPower(self, vm_name: str) -> str:
        """从Proxmox API获取虚拟机实际状态"""
        try:
            client, result = self.api_conn()
            if not result.success:
                return ""
            
            vm_conf = self.vm_finds(vm_name)
            if vm_conf is None:
                return ""
            
            vmid = self.get_vmid(vm_conf)
            if vmid is None:
                return ""
            
            vm = client.nodes(self.hs_config.launch_path).qemu(vmid)
            status = vm.status.current.get()
            
            if status:
                vm_status = status.get('status', '')
                # 映射Proxmox状态到中文状态
                state_map = {
                    'running': '运行中',
                    'stopped': '已关机',
                    'paused': '已暂停'
                }
                return state_map.get(vm_status, '未知')
        except Exception as e:
            logger.warning(f"从API获取虚拟机 {vm_name} 状态失败: {str(e)}")
        return ""

    # 设置虚拟机密码 ###########################################################
    def VMPasswd(self, vm_name: str, os_pass: str) -> ZMessage:
        """设置虚拟机密码（同时修改数据库和通过GuestAgent修改虚拟机内部密码）"""
        try:
            # 查找本地配置 =====================================================
            vm_config: VMConfig | None = self.vm_saving.get(vm_name)
            if vm_config is None:
                return ZMessage(
                    success=False, action="Password",
                    message=f"虚拟机 {vm_name} 不存在")

            # 通过QEMU Guest Agent修改虚拟机内部密码 ===========================
            ga_success = False
            ga_message = ""
            try:
                client, result = self.api_conn()
                if result.success and client:
                    vmid = self.get_vmid(vm_config)
                    if vmid is not None:
                        vm_conn = client.nodes(
                            self.hs_config.launch_path).qemu(vmid)
                        # 检查虚拟机是否运行中 ================================
                        status = vm_conn.status.current.get()
                        if status.get('status') == 'running':
                            # 使用PVE API通过Guest Agent设置密码 ===============
                            # 默认使用root用户
                            os_user = "root"
                            try:
                                vm_conn.agent('set-user-password').post(
                                    username=os_user,
                                    password=os_pass)
                                ga_success = True
                                logger.info(
                                    f"虚拟机 {vm_name} 通过GuestAgent"
                                    f"修改{os_user}密码成功")
                            except Exception as ga_err:
                                ga_message = str(ga_err)
                                logger.warning(
                                    f"虚拟机 {vm_name} GuestAgent修改密码失败"
                                    f"（可能未安装qemu-guest-agent）: {ga_err}")
                        else:
                            ga_message = "虚拟机未运行，无法通过GuestAgent修改密码"
                            logger.warning(
                                f"虚拟机 {vm_name} 未运行，"
                                f"跳过GuestAgent修改密码")
                    else:
                        ga_message = "VMID未找到"
                else:
                    ga_message = "Proxmox连接失败"
            except Exception as conn_err:
                ga_message = str(conn_err)
                logger.warning(
                    f"虚拟机 {vm_name} GuestAgent修改密码异常: {conn_err}")

            # 更新数据库密码（无论GuestAgent是否成功都要更新）===================
            vm_config.os_pass = os_pass
            self.data_set()
            logger.info(f"虚拟机 {vm_name} 数据库密码已更新")

            # 返回结果 =========================================================
            if ga_success:
                return ZMessage(
                    success=True, action="Password",
                    message="密码修改成功（数据库+虚拟机内部）")
            else:
                return ZMessage(
                    success=True, action="Password",
                    message=f"数据库密码已更新，但虚拟机内部密码修改失败: "
                            f"{ga_message}")

        except Exception as e:
            logger.error(f"设置密码失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="Password",
                message=f"设置密码失败: {str(e)}")

    # 备份虚拟机 ###############################################################
    def VMBackup(self, vm_name: str, vm_tips: str, cancel_event=None) -> ZMessage:
        logger.info(f"[{self.hs_config.server_name}] 开始备份虚拟机: {vm_name}")
        logger.info(f"  - 备份说明: {vm_tips}")
        
        # 连接到 Proxmox 服务器 ================================================
        client, result = self.api_conn()
        if not result.success:
            logger.error(f"[{self.hs_config.server_name}] Proxmox连接失败: {result.message}")
            return result
        # 获取虚拟机配置 =======================================================
        vm_conf = self.vm_finds(vm_name)
        if not vm_conf:
            logger.error(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} 不存在")
            return ZMessage(
                success=False,
                action="Backup",
                message="虚拟机不存在")
        # 备份虚拟机 ========================================================
        try:
            vmid = self.get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="VMBackup",
                    message=f"虚拟机 {vm_name} 的VMID未找到")
            vm = client.nodes(self.hs_config.launch_path).qemu(vmid)
            # 检查虚拟机是否正在运行
            status = vm.status.current.get()
            is_running = status['status'] == 'running'
            if is_running:
                logger.info(f"[{self.hs_config.server_name}] 虚拟机正在运行，先停止以进行备份...")
                vm.status.stop.post()
                logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} 已停止")
                time.sleep(5)  # 等待虚拟机完全停止
            # 构建备份文件名
            bak_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            bak_file = f"{vm_name}_{bak_time}.vma"
            logger.info(f"[{self.hs_config.server_name}] 备份文件名: {bak_file}")
            
            # 创建备份
            backup_config = {
                'vmid': vmid,
                'mode': 'stop',  # 停止模式备份
                'compress': 'gzip',
                'storage': 'local',  # 备份存储位置
            }
            logger.info(f"[{self.hs_config.server_name}] 正在创建备份任务...")
            task_id = client.nodes(
                self.hs_config.launch_path
            ).vzdump.post(**backup_config)
            logger.info(f"[{self.hs_config.server_name}] 备份任务已创建，任务ID: {task_id}")
            # 等待备份完成 ==================================================
            max_wait_time = 3600  # 最大等待时间（秒），1小时
            check_interval = 5  # 检查间隔（秒）
            all_time = 0
            while all_time < max_wait_time:
                # 检查是否被取消 ------------------------------------------------
                if cancel_event and cancel_event.is_set():
                    logger.info(f"[{self.hs_config.server_name}] 备份任务被取消，正在停止PVE端任务...")
                    try:
                        client.nodes(self.hs_config.launch_path).tasks(task_id).delete()
                        logger.info(f"[{self.hs_config.server_name}] PVE备份任务已停止: {task_id}")
                    except Exception as stop_err:
                        logger.warning(f"[{self.hs_config.server_name}] 停止PVE备份任务失败: {stop_err}")
                    # 如果之前停止了虚拟机，重新启动
                    if is_running:
                        try:
                            vm.status.start.post()
                            logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} 已重新启动")
                        except Exception as start_err:
                            logger.warning(f"[{self.hs_config.server_name}] 重启虚拟机失败: {start_err}")
                    return ZMessage(
                        success=False, action="VMBackup",
                        message="备份任务已被用户取消")
                # 查询任务状态 ----------------------------------------------
                task_status = client.nodes(
                    self.hs_config.launch_path
                ).tasks(task_id).status.get()
                status_value = task_status.get('status', '')
                logger.info(f"[{self.hs_config.server_name}] 备份{status_value}已等待: {all_time}秒")
                # 任务成功完成 ----------------------------------------------
                if status_value == 'stopped':
                    logger.info(f"[{self.hs_config.server_name}] 备份完成，总耗时: {all_time}秒")
                    break
                time.sleep(check_interval)
                all_time += check_interval
                # 超时检查 --------------------------------------------------
                if all_time >= max_wait_time:
                    logger.error(f"[{self.hs_config.server_name}] 备份任务超时，已等待{max_wait_time}秒")
                    raise TimeoutError(f"备份超时，已等待{max_wait_time}秒")
            # 从PVE存储中查询实际生成的备份文件名 ============================
            actual_bak_file = bak_file  # 默认使用自定义名称
            try:
                storage_content = client.nodes(
                    self.hs_config.launch_path
                ).storage('local').content.get(content='backup')
                # 查找最新的属于该vmid的备份文件
                vm_backups = [item for item in storage_content if item.get('vmid') == vmid]
                if vm_backups:
                    # 按创建时间排序，取最新的
                    vm_backups.sort(key=lambda x: x.get('ctime', 0), reverse=True)
                    actual_bak_file = vm_backups[0].get('volid', '').replace('local:backup/', '')
                    logger.info(f"[{self.hs_config.server_name}] PVE实际备份文件: {actual_bak_file}")
            except Exception as query_err:
                logger.warning(f"[{self.hs_config.server_name}] 查询PVE备份文件名失败: {query_err}，使用默认名称")

            # 记录备份信息 ==================================================
            vm_conf.backups.append(VMBackup(
                backup_time=datetime.datetime.now(),
                backup_name=actual_bak_file,
                backup_hint=vm_tips,
                old_os_name=vm_conf.os_name
            ))
            # 重新启动 ======================================================
            if is_running:
                logger.info(f"[{self.hs_config.server_name}] 重新启动虚拟机...")
                vm.status.start.post()
                logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} 已重新启动")
            # 记录备份结果 ==================================================
            logger.info(f"[{self.hs_config.server_name}] 虚拟机备份成功: {bak_file}，耗时: {all_time}秒")
            hs_result = ZMessage(
                success=True, action="VMBackup",
                message=f"虚拟机备份成功: {bak_file}，耗时: {all_time}秒",
                results={"backup_file": bak_file, "elapsed_time": all_time}
            )
            # 保存虚拟机配置 ================================================
            self.vm_saving[vm_name] = vm_conf
            self.logs_set(hs_result)
            self.data_set()
            return hs_result
        # 备份失败 ==========================================================
        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] 备份虚拟机失败: {str(e)}")
            logger.error(f"[{self.hs_config.server_name}] 错误详情:", exc_info=True)
            traceback.print_exc()
            return ZMessage(
                success=False, action="VMBackup",
                message=f"备份失败: {str(e)}")

    # 恢复虚拟机 ###############################################################
    def Restores(self, vm_name: str, vm_back: str) -> ZMessage:
        """恢复虚拟机"""
        client, result = self.api_conn()
        if not result.success:
            return result

        vm_conf = self.vm_finds(vm_name)
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
            vmid = self.get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="Restores",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            vm = client.nodes(self.hs_config.launch_path).qemu(vmid)

            # 先停止虚拟机（恢复前必须停止）
            status = vm.status.current.get()
            is_running = status['status'] == 'running'
            if is_running:
                logger.info(f"[{self.hs_config.server_name}] 虚拟机正在运行，先停止以进行恢复...")
                vm.status.stop.post()
                time.sleep(5)  # 等待虚拟机完全停止

            logger.info(f"[{self.hs_config.server_name}] 开始恢复虚拟机 {vm_name}，备份文件: {vm_back}")

            # 从PVE存储中查找匹配的备份volume
            archive_path = f"local:backup/{vm_back}"
            try:
                storage_content = client.nodes(
                    self.hs_config.launch_path
                ).storage('local').content.get(content='backup')
                # 精确匹配volid或文件名
                matched = None
                for item in storage_content:
                    volid = item.get('volid', '')
                    if volid == archive_path or volid.endswith(f'/{vm_back}'):
                        matched = volid
                        break
                if matched:
                    archive_path = matched
                    logger.info(f"[{self.hs_config.server_name}] 找到备份volume: {archive_path}")
                else:
                    # 尝试模糊匹配（备份文件可能带.gz后缀）
                    for item in storage_content:
                        volid = item.get('volid', '')
                        if vm_back in volid:
                            archive_path = volid
                            logger.info(f"[{self.hs_config.server_name}] 模糊匹配到备份volume: {archive_path}")
                            break
            except Exception as query_err:
                logger.warning(f"[{self.hs_config.server_name}] 查询PVE存储失败: {query_err}，使用默认路径")

            # 调用Proxmox恢复API
            restore_config = {
                'vmid': vmid,
                'archive': archive_path,
                'force': 1,
            }
            task_id = client.nodes(self.hs_config.launch_path).qemu.post(**restore_config)
            logger.info(f"[{self.hs_config.server_name}] 恢复任务已创建，任务ID: {task_id}")

            # 等待恢复完成
            max_wait_time = 3600  # 最大等待1小时
            check_interval = 5
            all_time = 0
            while all_time < max_wait_time:
                task_status = client.nodes(
                    self.hs_config.launch_path
                ).tasks(task_id).status.get()
                status_value = task_status.get('status', '')
                logger.info(f"[{self.hs_config.server_name}] 恢复{status_value}已等待: {all_time}秒")

                if status_value == 'stopped':
                    logger.info(f"[{self.hs_config.server_name}] 恢复完成，总耗时: {all_time}秒")
                    break

                time.sleep(check_interval)
                all_time += check_interval

                if all_time >= max_wait_time:
                    raise TimeoutError(f"恢复超时，已等待{max_wait_time}秒")

            # 恢复成功，更新配置
            vm_conf.os_name = vb_conf.old_os_name

            # 重新启动虚拟机
            if is_running:
                logger.info(f"[{self.hs_config.server_name}] 重新启动虚拟机...")
                vm.status.start.post()
                logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} 已重新启动")

            logger.info(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} 恢复成功，耗时: {all_time}秒")

            self.vm_saving[vm_name] = vm_conf
            hs_result = ZMessage(
                success=True, action="Restores",
                message=f"虚拟机恢复成功: {vm_name}，耗时: {all_time}秒",
                results={"vm_name": vm_name, "elapsed_time": all_time}
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

    # 查找SCSI设备 #############################################################
    def get_scsi(self, vm_apis, vm_name: str, disk_file: str = None) -> Optional[str]:
        """从Proxmox配置中查找SCSI设备号
        
        Args:
            vm_apis: Proxmox虚拟机API对象
            vm_name: 虚拟机名称
            disk_file: 磁盘文件名（可选，用于匹配）
        
        Returns:
            找到的SCSI设备号（如'scsi1'），未找到返回None
        """
        try:
            # 获取虚拟机配置 ===================================================
            config = vm_apis.config.get()
            logger.info(f"尝试从Proxmox配置中查找虚拟机 {vm_name} 的SCSI设备")

            # 遍历所有scsi设备 =================================================
            for key, value in config.items():
                if key.startswith('scsi') and isinstance(value, str):
                    logger.debug(f"检查设备 {key}: {value}")

                    # 如果提供了disk_file，通过磁盘文件名匹配 ===================
                    if disk_file and disk_file in value:
                        logger.info(f"通过磁盘文件名 {disk_file} 找到设备: {key}")
                        return key

            logger.warning(f"未找到匹配的SCSI设备")
            return None

        except Exception as e:
            logger.error(f"查找SCSI设备时出错: {str(e)}")
            traceback.print_exc()
            return None

    # 获取下一个可用磁盘编号 ###################################################
    def _get_next_disk_index(self, client, vm_vmid: int) -> int:
        """查询虚拟机当前已有的磁盘，计算下一个可用的磁盘编号。
        
        EFI磁盘会占用disk-0，所以系统盘需要用更高的编号。
        """
        import re
        try:
            vm_conn = client.nodes(self.hs_config.launch_path).qemu(vm_vmid)
            config = vm_conn.config.get()
            # 扫描所有已存在的磁盘编号（从配置值中提取 vm-XXX-disk-N 的编号）
            used_indices = set()
            disk_pattern = re.compile(rf'vm-{vm_vmid}-disk-(\d+)')
            for key, value in config.items():
                if isinstance(value, str):
                    match = disk_pattern.search(value)
                    if match:
                        used_indices.add(int(match.group(1)))
            # 同时检查unused磁盘 ===============================================
            for key in config:
                if key.startswith('unused'):
                    value = config[key]
                    if isinstance(value, str):
                        match = disk_pattern.search(value)
                        if match:
                            used_indices.add(int(match.group(1)))
            # 找到下一个可用编号 ===============================================
            next_idx = 0
            while next_idx in used_indices:
                next_idx += 1
            logger.info(f"虚拟机 {vm_vmid} 已用磁盘编号: {used_indices}, 下一个可用: {next_idx}")
            return next_idx
        except Exception as e:
            logger.warning(f"查询磁盘编号失败({e})，默认使用1（跳过EFI的disk-0）")
            return 1

    # 查找unused磁盘 ###########################################################
    def _find_unused_disk(self, vm_conn, storage_name: str, vm_vmid: int) -> str:
        """查询虚拟机配置中的unused磁盘，返回实际的磁盘路径。
        
        importdisk/cp后磁盘会以unused状态出现在配置中，
        通过此方法获取实际的磁盘路径用于挂载。
        """
        try:
            config = vm_conn.config.get()
            # 查找所有unused磁盘，优先匹配目标存储 =============================
            unused_disks = []
            for key, value in config.items():
                if key.startswith('unused') and isinstance(value, str):
                    # unused磁盘格式: "local:200/vm-200-disk-1.qcow2"
                    if str(vm_vmid) in value:
                        unused_disks.append(value)
            if unused_disks:
                # 如果有多个unused磁盘，选择最新的（编号最大的）
                unused_disks.sort()
                selected = unused_disks[-1]
                logger.info(f"找到unused磁盘: {selected}")
                return selected
            logger.warning(f"未找到虚拟机 {vm_vmid} 的unused磁盘")
            return ""
        except Exception as e:
            logger.warning(f"查询unused磁盘失败: {e}")
            return ""

    # 刷新PVE存储 #############################################################
    def _refresh_storage(self, client, storage_name: str):
        """刷新PVE存储，确保新复制/导入的磁盘文件被PVE识别。

        通过API调用 pvesm scan 或直接SSH执行 pvesm refresh，
        解决直接cp文件后PVE未识别volume的问题。
        """
        import time
        try:
            # 方式1：通过PVE API刷新存储内容 ====================================
            node = client.nodes(self.hs_config.launch_path)
            node.storage(storage_name).content.get()
            logger.info(f"通过API刷新存储 {storage_name} 内容列表")
        except Exception as api_err:
            logger.warning(f"API刷新存储失败({api_err})，尝试SSH执行pvesm refresh...")
            # 方式2：通过SSH执行pvesm命令刷新 ==================================
            try:
                if self.flag_web():
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        self.hs_config.server_addr,
                        username=self.hs_config.server_user,
                        password=self.hs_config.server_pass)
                    stdin, stdout, stderr = ssh.exec_command(
                        f"pvesm scan dir {storage_name} 2>/dev/null; pvesm status {storage_name}")
                    stdout.channel.recv_exit_status()
                    ssh.close()
                else:
                    safe_shell_exec(f"pvesm scan dir {storage_name} 2>/dev/null; pvesm status {storage_name}",
                                   allow_pipe=False)
                logger.info(f"通过命令刷新存储 {storage_name}")
            except Exception as ssh_err:
                logger.warning(f"SSH刷新存储也失败: {ssh_err}")
        # 短暂等待PVE内部索引更新 ==============================================
        time.sleep(1)

    # 扩容系统盘 ###############################################################
    def _resize_system_disk(self, vm_conn, disk_id: str, target_mb: int) -> bool:
        """根据 target_mb(MB) 扩容指定磁盘到目标大小。

        Proxmox resize 仅支持增大, 不允许缩小; 若目标 <= 当前大小则跳过。
        优先使用 proxmoxer API, 失败时回退 SSH qm resize 命令。
        """
        try:
            if not target_mb or target_mb <= 0:
                return True
            # Proxmox resize size 参数使用 +<N>G / <N>G 语法, 这里用绝对值 ====
            target_gb = max(1, int(target_mb) // 1024)
            size_str = f"{target_gb}G"
            # 先检查当前磁盘大小, 避免"shrink not allowed" ===================
            try:
                cur_cfg = vm_conn.config.get() or {}
                cur_val = cur_cfg.get(disk_id, '')
                # 形如 "local:100/vm-100-disk-0.qcow2,size=10G"
                if isinstance(cur_val, str) and 'size=' in cur_val:
                    cur_size = cur_val.split('size=')[-1].strip()
                    # 统一转为 GB 做比较 (支持 G / M / T)
                    def _to_mb(s: str) -> int:
                        s = s.strip()
                        if s.endswith('T'):
                            return int(float(s[:-1]) * 1024 * 1024)
                        if s.endswith('G'):
                            return int(float(s[:-1]) * 1024)
                        if s.endswith('M'):
                            return int(float(s[:-1]))
                        return int(float(s))
                    cur_mb = _to_mb(cur_size)
                    if cur_mb >= target_mb:
                        logger.info(f"磁盘 {disk_id} 当前 {cur_size} 已 >= 目标 {size_str}, 跳过扩容")
                        return True
            except Exception as ce:
                logger.warning(f"读取 {disk_id} 当前大小失败, 继续尝试扩容: {ce}")
            # 通过 proxmoxer API 扩容 =======================================
            try:
                vm_conn.resize.put(disk=disk_id, size=size_str)
                logger.info(f"通过API扩容磁盘 {disk_id} 到 {size_str}")
                return True
            except Exception as ae:
                logger.warning(f"API扩容失败, 尝试SSH: {ae}")
            # SSH 回退 ======================================================
            vmid = getattr(vm_conn, '_store', {}).get('vmid') if hasattr(vm_conn, '_store') else None
            if not vmid:
                # 兼容不同 proxmoxer 版本, 从 URL 解析 vmid
                try:
                    vmid = int(str(vm_conn).rstrip('/').split('/')[-1])
                except Exception:
                    vmid = None
            if not vmid:
                logger.error(f"扩容 {disk_id} 失败: 无法解析 vmid")
                return False
            cmd = f"qm resize {vmid} {disk_id} {size_str}"
            if self.flag_web():
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    self.hs_config.server_addr,
                    username=self.hs_config.server_user,
                    password=self.hs_config.server_pass)
                stdin, stdout, stderr = ssh.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                err = stderr.read().decode()
                ssh.close()
                if exit_status != 0:
                    logger.error(f"SSH扩容失败: {err}")
                    return False
            else:
                ok, _, _ = safe_shell_exec(cmd, timeout=60, allow_pipe=False)
                if not ok:
                    logger.error(f"本地扩容命令失败: {cmd}")
                    return False
            logger.info(f"通过命令扩容磁盘 {disk_id} 到 {size_str}")
            return True
        except Exception as e:
            logger.error(f"扩容磁盘 {disk_id} 异常: {e}")
            traceback.print_exc()
            return False

    # 获取存储池实际路径 ########################################################
    def _get_storage_path(self, storage_name: str, vm_vmid: int) -> str:
        """通过pvesm命令获取存储池的实际文件系统路径。

        Args:
            storage_name: Proxmox存储池名称（如'nvme1', 'local'）
            vm_vmid: 虚拟机VMID

        Returns:
            存储池中该虚拟机的images目录路径
        """
        # 默认回退路径
        fallback_dir = f"/var/lib/vz/images/{vm_vmid}"
        if not storage_name:
            return fallback_dir
        try:
            # 通过pvesm path解析存储池路径 =====================================
            # pvesm path <storage>:<vmid>/test.qcow2 会返回完整文件路径
            probe_cmd = f"pvesm path {storage_name}:{vm_vmid}/probe.qcow2"
            if self.flag_web():
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    self.hs_config.server_addr,
                    username=self.hs_config.server_user,
                    password=self.hs_config.server_pass)
                stdin, stdout, stderr = ssh.exec_command(probe_cmd)
                stdout.channel.recv_exit_status()
                result = stdout.read().decode().strip()
                ssh.close()
            else:
                ok, out, _ = safe_shell_exec(probe_cmd, timeout=30, allow_pipe=False)
                result = out.strip() if ok else ""
            # 结果形如: /mnt/nvme1/images/202/probe.qcow2
            if result and '/' in result:
                # 取目录部分（去掉文件名）
                disk_dir = result.rsplit('/', 1)[0]
                logger.info(f"存储池 {storage_name} 实际路径: {disk_dir}")
                return disk_dir
        except Exception as e:
            logger.warning(f"获取存储池路径失败({e})，使用默认路径: {fallback_dir}")
        return fallback_dir

    # 创建QCOW2磁盘文件 ########################################################
    def hdd_init(self, vm_vmid: int, disk_name: str, disk_size: str) -> ZMessage:
        """创建QCOW2格式的磁盘文件
        
        Args:
            vm_vmid: 虚拟机VMID
            disk_name: 磁盘文件名（如'vm-100-disk-1.qcow2'）
            disk_size: 磁盘大小（如'10G'）
        
        Returns:
            ZMessage对象，包含操作结果
        """
        try:
            # 通过pvesm获取存储池的实际文件系统路径 =============================
            storage_name = self.hs_config.extern_path
            disk_dir = self._get_storage_path(storage_name, vm_vmid)

            # 远程模式 =========================================================
            if self.flag_web():
                # 远程模式：通过SSH创建qcow2文件
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    self.hs_config.server_addr,
                    username=self.hs_config.server_user,
                    password=self.hs_config.server_pass)

                # 创建目录 =====================================================
                ssh.exec_command(f"mkdir -p {disk_dir}")

                # 创建qcow2文件 ================================================
                create_cmd = f"qemu-img create -f qcow2 {disk_dir}/{disk_name} {disk_size}"
                stdin, stdout, stderr = ssh.exec_command(create_cmd)
                exit_status = stdout.channel.recv_exit_status()

                if exit_status != 0:
                    error_msg = stderr.read().decode()
                    ssh.close()
                    return ZMessage(
                        success=False, action="CreateQcow2",
                        message=f"创建qcow2文件失败: {error_msg}")

                ssh.close()
                logger.info(f"通过SSH创建qcow2文件: {disk_dir}/{disk_name}, 大小: {disk_size}")

            # 本地模式 =========================================================
            else:
                # 本地模式：直接创建qcow2文件
                os.makedirs(disk_dir, exist_ok=True)
                create_cmd = f"qemu-img create -f qcow2 {disk_dir}/{disk_name} {disk_size}"
                ok, _, err = safe_shell_exec(create_cmd, timeout=60, allow_pipe=False)
                if not ok:
                    # 本地执行失败，回退到SSH方式执行 ========================
                    logger.warning(f"本地创建qcow2失败(exit={exit_status})，尝试SSH回退执行...")
                    try:
                        ssh = paramiko.SSHClient()
                        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        ssh.connect(
                            self.hs_config.server_addr,
                            username=self.hs_config.server_user,
                            password=self.hs_config.server_pass)
                        ssh.exec_command(f"mkdir -p {disk_dir}")
                        stdin, stdout, stderr = ssh.exec_command(create_cmd)
                        ssh_exit = stdout.channel.recv_exit_status()
                        if ssh_exit != 0:
                            error_msg = stderr.read().decode()
                            ssh.close()
                            return ZMessage(
                                success=False, action="CreateQcow2",
                                message=f"SSH回退创建qcow2也失败: {error_msg}")
                        ssh.close()
                        logger.info(f"SSH回退创建qcow2成功: {disk_dir}/{disk_name}, 大小: {disk_size}")
                    except Exception as ssh_err:
                        return ZMessage(
                            success=False, action="CreateQcow2",
                            message=f"SSH回退执行异常: {str(ssh_err)}")
                else:
                    logger.info(f"本地创建qcow2文件: {disk_dir}/{disk_name}, 大小: {disk_size}")

            # 刷新存储，确保PVE识别新创建的磁盘文件 ============================
            try:
                client, _ = self.api_conn()
                if client:
                    self._refresh_storage(client, storage_name)
            except Exception as ref_err:
                logger.warning(f"创建磁盘后刷新存储失败: {ref_err}")

            return ZMessage(
                success=True, action="CreateQcow2",
                message=f"成功创建qcow2文件: {disk_name}")

        except Exception as e:
            logger.error(f"创建qcow2文件异常: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="CreateQcow2",
                message=f"创建qcow2文件异常: {str(e)}")

    # VM镜像挂载 ###############################################################
    def HDDMount(self, vm_name: str, vm_imgs: SDConfig, in_flag=True) -> ZMessage:
        action_name = "挂载" if in_flag else "卸载"
        logger.info(f"[{self.hs_config.server_name}] 开始{action_name}硬盘: {vm_imgs.hdd_name} -> 虚拟机 {vm_name}")
        
        # 获取虚拟机信息 =======================================================
        result = self.get_info(vm_name)
        if not result.success:
            logger.error(f"[{self.hs_config.server_name}] 获取虚拟机信息失败: {result.message}")
            return result
        vm_conn = result.results[0]
        vm_vmid = result.results[1]
        # 挂载硬盘 =============================================================
        try:
            # 停止虚拟机 =======================================================
            vm_flag = vm_conn.status.current.get()
            vm_flag = vm_flag['status'] == 'running'
            if vm_flag:
                self.VMPowers(vm_name, VMPowers.H_CLOSE)
            # 获取可用的scsi设备号 =============================================
            if in_flag:
                # 找到可用的scsi设备号 =========================================
                config = vm_conn.config.get()
                scsi_num = 1
                while f"scsi{scsi_num}" in config:
                    scsi_num += 1
                # 检查是否是重新挂载已卸载的硬盘 ===============================
                disk_name = None
                if vm_imgs.hdd_name in self.vm_saving[vm_name].hdd_all:
                    now_disk = self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name]
                    # 已卸载的硬盘，重新挂载 -----------------------------------
                    if now_disk.hdd_flag == 0 and now_disk.hdd_file:
                        disk_name = now_disk.hdd_file
                        logger.info(f"重新挂载已卸载的硬盘: {disk_name}")
                    # 已挂载的硬盘，不能再挂载 ---------------------------------
                    elif now_disk.hdd_flag == 1:
                        return ZMessage(
                            success=False, action="HDDMount",
                            message=f"硬盘 {vm_imgs.hdd_name} 已经挂载")
                # 需要创建新硬盘 ===============================================
                if disk_name is None:
                    hdd_size_mb = getattr(vm_imgs, 'hdd_size', 10)
                    disk_size = f"{hdd_size_mb // 1024}G"
                    disk_name = f"vm-{vm_vmid}-disk-{scsi_num}.qcow2"
                    # 创建磁盘文件 =============================================
                    create_result = self.hdd_init(vm_vmid, disk_name, disk_size)
                    if not create_result.success:
                        return create_result
                    logger.info(f"创建新硬盘: {disk_name}, 大小: {disk_size}")
                # 确保disk_name已赋值 ==========================================
                if disk_name is None:
                    return ZMessage(
                        success=False, action="HDDMount",
                        message="无法确定磁盘文件名")
                # 挂载硬盘 =====================================================
                storage_name = self.hs_config.extern_path
                disk_config = f"{storage_name}:{vm_vmid}/{disk_name}"
                vm_conn.config.put(**{f"scsi{scsi_num}": disk_config})
                logger.info(f"硬盘挂载到虚拟机 {vm_name}，设备: scsi{scsi_num}")
                # 保存scsi设备号和状态 =========================================
                vm_imgs.hdd_flag = 1  # 1表示已挂载
                vm_imgs.hdd_scsi = f"scsi{scsi_num}"
                vm_imgs.hdd_file = disk_name
                self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name] = vm_imgs
            # 卸载硬盘 =========================================================
            else:
                # 检查硬盘是否在虚拟机配置中 -----------------------------------
                if vm_imgs.hdd_name not in self.vm_saving[vm_name].hdd_all:
                    return ZMessage(
                        success=False, action="HDDMount",
                        message=f"硬盘 {vm_imgs.hdd_name} 不在虚拟机配置中")
                # 获取硬盘配置信息 ---------------------------------------------
                mounted_disk = self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name]
                scsi_device = getattr(mounted_disk, 'hdd_scsi', None)
                disk_file = getattr(mounted_disk, 'hdd_file', None)
                # 如果没有scsi设备号，尝试从Proxmox配置中查找 ------------------
                if not scsi_device:
                    scsi_device = self.get_scsi(vm_conn, vm_name, disk_file)
                # 如果还是找不到scsi设备，返回错误 -----------------------------
                if not scsi_device:
                    logger.error(f"无法找到硬盘 {vm_imgs.hdd_name} scsi设备号")
                    return ZMessage(
                        success=False, action="HDDMount",
                        message=f"无法找到硬盘 {vm_imgs.hdd_name} scsi设备号")
                # 执行卸载操作 -------------------------------------------------
                vm_conn.config.put(**{scsi_device: "none"})
                vm_conn.config.put(delete=scsi_device)
                logger.info(f"已从Proxmox配置中卸载 {scsi_device} 设备")
                # 标记为已卸载 -------------------------------------------------
                mounted_disk.hdd_flag = 0  # 0表示已卸载
                mounted_disk.hdd_scsi = ""  # 清除设备号，下次挂载时会重新分配
                self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name] = mounted_disk
                logger.info(f"硬盘{vm_imgs.hdd_name}已从虚拟机 {vm_name} 卸载")
            # 保存配置到数据库 =================================================
            self.data_set()
            logger.info(f"[{self.hs_config.server_name}] 硬盘配置已保存到数据库")
            
            # 重启虚拟机 =======================================================
            if vm_flag:
                logger.info(f"[{self.hs_config.server_name}] 重新启动虚拟机...")
                self.VMPowers(vm_name, VMPowers.S_START)
            
            logger.info(f"[{self.hs_config.server_name}] 硬盘{action_name}成功: {vm_imgs.hdd_name}")
            return ZMessage(
                success=True, action="HDDMount",
                message=f"硬盘{action_name}成功")
        # 捕获所有异常 =========================================================
        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] 硬盘{action_name}操作失败: {str(e)}")
            logger.error(f"[{self.hs_config.server_name}] 错误详情:", exc_info=True)
            traceback.print_exc()
            return ZMessage(
                success=False, action="HDDMount",
                message=f"硬盘挂载操作失败: {str(e)}")

    # ISO镜像挂载 ##############################################################
    def ISOMount(self, vm_name: str,
                 vm_imgs: IMConfig, in_flag=True) -> ZMessage:
        action_name = "挂载" if in_flag else "卸载"
        logger.info(f"[{self.hs_config.server_name}] 开始{action_name}ISO镜像: {vm_imgs.iso_name if in_flag else '所有ISO'} -> 虚拟机 {vm_name}")
        try:
            # 获取虚拟机信息 ===================================================
            result = self.get_info(vm_name)
            if not result.success:
                logger.error(f"[{self.hs_config.server_name}] 获取虚拟机信息失败: {result.message}")
                return result
            vm_conn = result.results[0]
            
            # 停止虚拟机 =======================================================
            status = vm_conn.status.current.get()
            was_running = status['status'] == 'running'
            if was_running:
                self.VMPowers(vm_name, VMPowers.H_CLOSE)
            
            # 执行挂载/卸载操作 ================================================
            if in_flag:
                # 挂载ISO ======================================================
                dvdrom_storage = self.hs_config.dvdrom_path or "local:iso"
                iso_path = f"{dvdrom_storage}/{vm_imgs.iso_file}"
                vm_conn.config.put(ide2=f"{iso_path},media=cdrom")
                self.vm_saving[vm_name].iso_all[vm_imgs.iso_name] = vm_imgs
                logger.info(f"ISO已挂载到虚拟机 {vm_name}: {vm_imgs.iso_file}")
            else:
                # 卸载ISO ======================================================
                vm_conn.config.put(ide2="none,media=cdrom")
                if vm_imgs.iso_name in self.vm_saving[vm_name].iso_all:
                    del self.vm_saving[vm_name].iso_all[vm_imgs.iso_name]
                logger.info(f"ISO已从虚拟机 {vm_name} 卸载")
            
            # 保存配置 =========================================================
            vm_conf = deepcopy(self.vm_saving[vm_name])
            self.VMUpdate(self.vm_saving[vm_name], vm_conf)
            self.data_set()
            
            # 重启虚拟机 =======================================================
            if was_running:
                self.VMPowers(vm_name, VMPowers.S_START)
            
            # 返回结果 =========================================================
            return ZMessage(
                success=True, action="ISOMount",
                message=f"ISO镜像{action_name}成功")
            
        except Exception as e:
            logger.error(f"ISO镜像挂载操作失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="ISOMount",
                message=f"ISO镜像挂载操作失败: {str(e)}")

    # 虚拟机控制台 #############################################################
    def VMRemote(self, vm_uuid: str, ip_addr: str = "127.0.0.1") -> ZMessage:
        """使用QEMU VNC直通端口 + websockify + noVNC（与VMware方案一致）"""
        try:
            import random, string
            # 获取虚拟机连接 ===================================================
            vm_conn, vmid, vm_conf, result = self._get_vm_connection(vm_uuid)
            if not result.success:
                return result

            # 获取主机外网IP ===================================================
            if len(self.hs_config.public_addr) == 0:
                return ZMessage(
                    success=False,
                    action="VCRemote",
                    message="主机外网IP不存在")

            public_ip = self.hs_config.public_addr[0]
            if public_ip in ["localhost", "127.0.0.1", ""]:
                public_ip = "127.0.0.1"

            # 确定VNC端口 =====================================================
            # 优先使用vm_saving中配置的vc_port，否则使用 5900 + VMID
            pve_host = self.hs_config.server_addr
            if vm_uuid in self.vm_saving and self.vm_saving[vm_uuid].vc_port:
                vnc_port = int(self.vm_saving[vm_uuid].vc_port)
            else:
                vnc_port = 5900 + int(vmid)
            # VNCID = 端口 - 5900（QEMU -vnc 参数使用的是display number）
            vnc_id = vnc_port - 5900
            logger.info(f"[{self.hs_config.server_name}] VM {vmid} VNC配置: vnc_id={vnc_id}, vnc_port={vnc_port}")

            # 兼容旧虚拟机：检查并写入VNC端口配置到PVE conf ====================
            try:
                current_config = vm_conn.config.get()
                current_args = current_config.get('args', '')
                vnc_arg = f"-vnc 0.0.0.0:{vnc_id}"
                if vnc_arg not in current_args:
                    import re
                    new_args = re.sub(r'-vnc\s+\S+', '', current_args).strip()
                    new_args = f"{new_args} {vnc_arg}".strip()
                    vm_conn.config.put(args=new_args)
                    logger.info(f"[{self.hs_config.server_name}] 已为VM {vmid} 补写VNC配置: {vnc_arg} (端口:{vnc_port})")
            except Exception as vnc_err:
                logger.warning(f"[{self.hs_config.server_name}] VNC配置补写失败: {vnc_err}")

            # 初始化websockify（与VMware方案一致）==============================
            self.VMLoader()

            # 生成随机token用于websockify端口映射 ==============================
            rand_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

            # 删除旧端口映射 ===================================================
            self.vm_remote.exec.del_port(pve_host, vnc_port)

            # 添加新端口映射（rand_pass -> PVE主机VNC端口）=====================
            self.vm_remote.exec.add_port(pve_host, vnc_port, rand_pass)

            # 构造noVNC访问URL（与VMware方案一致，带token和websockify路径）=====
            url = (
                f"http://{public_ip}:{self.hs_config.remote_port}"
                f"/vnc.html?autoconnect=true&path=websockify?"
                f"token={rand_pass}"
            )
            logger.info(f"VMRemote for {vm_uuid}: VNC({pve_host}:{vnc_port}) -> {url}")

            return ZMessage(
                success=True,
                action="VCRemote",
                message=url,
                results={
                    "vmid": vmid,
                    "vnc_port": vnc_port,
                    "url": url
                }
            )

        except Exception as e:
            logger.error(f"获取虚拟机远程控制台失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False,
                action="VCRemote",
                message=f"获取远程控制台失败: {str(e)}")

    # [旧方案-已废弃] 通过Caddy反向代理PVE Web界面实现noVNC =====================
    # def VMRemote_PVE_OLD(self, vm_uuid, ip_addr="127.0.0.1"):
    #     """旧方案：通过Caddy代理整个PVE Web界面（存在路由匹配和WebSocket问题）"""
    #     # 1. 获取PVE认证ticket
    #     # 2. 获取VNC proxy ticket
    #     # 3. 通过HttpManager.create_pve()注册Caddy反向代理
    #     # 4. 返回 https://{ip}:{port}/{token}/?console=kvm&novnc=1&vmid=...
    #     # 问题：Caddy handle_path路由匹配不生效、WebSocket代理失败、reload不生效
    #     pass

    # 加载备份 #################################################################
    def LDBackup(self, vm_back: str = "") -> ZMessage:
        return super().LDBackup(vm_back)

    # 移除备份 #################################################################
    def RMBackup(self, vm_name: str, vm_back: str = "") -> ZMessage:
        return super().RMBackup(vm_name, vm_back)

    def get_info(self, vm_name: str) -> ZMessage:
        """获取虚拟机信息的统一方法"""
        try:
            # 使用公共辅助方法获取虚拟机连接 =================================
            vm_conn, vm_vmid, vm_conf, result = self._get_vm_connection(vm_name)
            if not result.success:
                return result
            
            # 返回虚拟机配置 ===================================================
            return ZMessage(
                success=True, action="get_info",
                message=f"成功获取虚拟机 {vm_name} 信息",
                results=(vm_conn, vm_vmid, vm_conf))
        
        except Exception as e:
            logger.error(f"获取虚拟机信息失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="get_info",
                message=f"获取虚拟机信息失败: {str(e)}")

    # 硬盘所有权移交 ###########################################################
    def HDDTrans(self, vm_name: str, vm_imgs: SDConfig, ex_name: str) -> ZMessage:
        # 检查情况 =============================================================
        check_result = self.HDDCheck(vm_name, vm_imgs, ex_name)
        if not check_result.success:
            return check_result
        # 获取虚拟机信息 =======================================================
        result = self.get_info(vm_name)
        if not result.success:
            return ZMessage(
                success=False, action="HDDTrans",
                message=f"获取源虚拟机信息失败: {result.message}")
        src_vm_conn = result.results[0]
        src_vmid = result.results[1]
        # 获取目标虚拟机信息 ===================================================
        result = self.get_info(ex_name)
        if not result.success:
            return ZMessage(
                success=False, action="HDDTrans",
                message=f"获取目标虚拟机信息失败: {result.message}")
        dst_vm_conn = result.results[0]
        dst_vmid = result.results[1]
        # 执行移交操作 =========================================================
        try:
            hdd_config = self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name]
            disk_file = getattr(hdd_config, 'hdd_file', None)
            if not disk_file:
                return ZMessage(
                    success=False, action="HDDTrans",
                    message="磁盘文件信息不存在，无法移交")

            # 获取源虚拟机配置，找到磁盘对应的设备 =============================
            src_config = src_vm_conn.config.get()
            # 查找包含该磁盘文件的unused disk
            source_disk = None
            for key, value in src_config.items():
                if key.startswith('unused') and isinstance(value, str):
                    if disk_file in value:
                        source_disk = key
                        logger.info(f"找到源磁盘: {key} = {value}")
                        break
            if not source_disk:
                return ZMessage(
                    success=False, action="HDDTrans",
                    message=f"未找到磁盘文件 {disk_file} 对应的unused disk")
            # 找到目标虚拟机可用的scsi编号 =====================================
            dst_config = dst_vm_conn.config.get()
            scsi_num = 1
            while f"scsi{scsi_num}" in dst_config:
                scsi_num += 1
            target_disk = f"scsi{scsi_num}"
            # 获取存储名称 =====================================================
            storage_name = self.hs_config.extern_path
            # 使用PVE API的move_disk功能 =======================================
            # 注意：proxmoxer库可能不直接支持move_disk，需要通过SSH执行qm命令
            logger.info(f"准备移动磁盘: 从VM {src_vmid}({source_disk}) "
                        f"到VM {dst_vmid}({target_disk})")
            # 通过SSH执行qm move-disk命令 ======================================
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.hs_config.server_addr,
                username=self.hs_config.server_user,
                password=self.hs_config.server_pass)
            # 执行qm move-disk命令 =============================================
            move_cmd = (
                f"qm move-disk {src_vmid} {source_disk} "
                f"--target-vmid {dst_vmid} --target-disk {target_disk}"
            )
            logger.info(f"执行命令: {move_cmd}")
            stdin, stdout, stderr = ssh.exec_command(move_cmd)
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode()
            error_output = stderr.read().decode()
            ssh.close()
            if exit_status != 0:
                logger.error(f"移动磁盘失败: {error_output}")
                return ZMessage(
                    success=False, action="HDDTrans",
                    message=f"移动磁盘失败: {error_output}")
            logger.info(f"磁盘移动成功: {output}")
            # 获取新的磁盘文件名 ===============================================
            dst_config_new = dst_vm_conn.config.get()
            new_disk_value = dst_config_new.get(target_disk, "")
            import posixpath
            if ":" in new_disk_value and "/" in new_disk_value:
                # 先分割出路径部分（去掉storage前缀）
                path_part = new_disk_value.split(":")[-1]
                # 再去掉size等参数（用逗号分割）
                path_part = path_part.split(",")[0]
                new_disk_name = posixpath.basename(path_part)
            else:
                # 如果无法解析，使用默认命名
                _, disk_ext = posixpath.splitext(disk_file)
                new_disk_name = f"vm-{dst_vmid}-disk-{scsi_num}{disk_ext}"
            logger.info(f"新磁盘文件名: {new_disk_name}")
            # 立即卸载目标虚拟机上的磁盘，使其变为unused状态 ===================
            logger.info(f"卸载目标虚拟机上的磁盘 {target_disk}")
            dst_vm_conn.config.put(**{target_disk: "none"})
            dst_vm_conn.config.put(delete=target_disk)
            logger.info(f"磁盘 {target_disk} 已在PVE中卸载，现在处于unused状态")
            # 从源虚拟机移除磁盘配置 ===========================================
            self.vm_saving[vm_name].hdd_all.pop(vm_imgs.hdd_name)
            # 添加到目标虚拟机（保持未挂载状态）================================
            vm_imgs.hdd_flag = 0  # 移交后保持未挂载状态
            vm_imgs.hdd_scsi = ""  # 清空设备号，等待下次挂载时分配
            vm_imgs.hdd_file = new_disk_name  # 更新文件名
            self.vm_saving[ex_name].hdd_all[vm_imgs.hdd_name] = vm_imgs
            # 保存配置 =========================================================
            self.data_set()
            logger.info(
                f"磁盘 {vm_imgs.hdd_name} 已从虚拟机 {vm_name} "
                f"(VMID: {src_vmid}) 移交到 {ex_name} (VMID: {dst_vmid})")
            # 返回结果 =========================================================
            return ZMessage(
                success=True, action="HDDTrans",
                message="磁盘移交成功",
                results={
                    "source_vmid": src_vmid,
                    "target_vmid": dst_vmid,
                    "source_disk": source_disk,
                    "target_disk": target_disk,
                    "new_disk_name": new_disk_name,
                    "src_vm": vm_name,
                    "dst_vm": ex_name
                })
        # 捕获异常 ==============================================================
        except Exception as e:
            logger.error(f"磁盘移交失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="HDDTrans",
                message=f"磁盘移交失败: {str(e)}")

    # 移除磁盘 #################################################################
    def RMMounts(self, vm_name: str, vm_imgs: str) -> ZMessage:
        # 获取虚拟机信息 =======================================================
        result = self.get_info(vm_name)
        if not result.success:
            return result
        vm_conn = result.results[0]
        vm_vmid = result.results[1]
        # 获取虚拟机配置 =======================================================
        try:
            # 获取硬盘配置信息 =================================================
            mounted_disk = deepcopy(self.vm_saving[vm_name].hdd_all[vm_imgs])
            scsi_device = getattr(mounted_disk, 'hdd_scsi', None)
            disk_file = getattr(mounted_disk, 'hdd_file', None)
            # 停止虚拟机 =======================================================
            status = vm_conn.status.current.get()
            was_running = status['status'] == 'running'
            if was_running:
                self.VMPowers(vm_name, VMPowers.H_CLOSE)
            # 卸载磁盘（更新本地配置状态）======================================
            self.HDDMount(vm_name, mounted_disk, False)
            time.sleep(3)  # 等待配置更新
            # 移除配置 =========================================================
            if scsi_device and disk_file:
                config = vm_conn.config.get()
                # 查找磁盘 =================================================
                del_disk = None
                for key, value in config.items():
                    if key.startswith('unused') and isinstance(value, str):
                        if disk_file in value:
                            del_disk = key
                            logger.info(f"找到匹配的unused disk: {key}")
                            break
                # 删除找到的unused disk ====================================
                if del_disk:
                    vm_conn.config.put(delete=del_disk)
                    logger.info(f"已彻底删除磁盘文件: {del_disk}")
            else:
                logger.warning(f"未找到包含{disk_file}unused disk")
            # 从配置删除 =======================================================
            del self.vm_saving[vm_name].hdd_all[vm_imgs]
            logger.info(f"已从配置列表中删除硬盘 {vm_imgs}")
            # 保存数据库 =======================================================
            self.data_set()
            logger.info(f"虚拟机 {vm_name} 配置已保存到数据库")
            # 重启虚拟机 =======================================================
            if was_running:
                self.VMPowers(vm_name, VMPowers.S_START)
            # 返回结果 =========================================================
            return ZMessage(
                success=True, action="RMMounts",
                message=f"硬盘 {vm_imgs} 删除成功")
        # 处理异常 =============================================================
        except Exception as e:
            traceback.print_exc()
            return ZMessage(
                success=False, action="RMMounts",
                message=f"删除硬盘失败: {str(e)}")

    # PPM(P6) 转 PNG 辅助方法（纯Python，不依赖PIL） ##########################
    @staticmethod
    def _ppm_to_png_base64(ppm_data: bytes) -> str:
        """将PPM(P6)二进制数据转换为PNG的base64字符串
        
        使用纯Python标准库实现，不依赖PIL/Pillow。
        仅支持P6(二进制RGB)格式，maxval=255。
        """
        import struct
        import zlib
        import base64

        try:
            # 解析PPM头部：P6\n<width> <height>\n<maxval>\n<pixel_data>
            # 跳过注释行（以#开头）
            idx = 0
            # 读取magic
            if not ppm_data[:2] == b'P6':
                logger.warning("PPM格式不是P6，无法转换")
                return ""
            idx = 2
            # 跳过空白
            tokens = []
            while len(tokens) < 3:
                # 跳过空白和注释
                while idx < len(ppm_data):
                    if ppm_data[idx:idx + 1] in (b' ', b'\t', b'\r', b'\n'):
                        idx += 1
                    elif ppm_data[idx:idx + 1] == b'#':
                        # 跳过注释行
                        while idx < len(ppm_data) and ppm_data[idx:idx + 1] != b'\n':
                            idx += 1
                        idx += 1  # 跳过换行
                    else:
                        break
                # 读取token
                token_start = idx
                while idx < len(ppm_data) and ppm_data[idx:idx + 1] not in (
                        b' ', b'\t', b'\r', b'\n'):
                    idx += 1
                if idx > token_start:
                    tokens.append(ppm_data[token_start:idx].decode('ascii'))
            # tokens = [width, height, maxval]
            width = int(tokens[0])
            height = int(tokens[1])
            # maxval = int(tokens[2])  # 通常为255
            # 跳过header后的一个空白字符
            idx += 1
            pixel_data = ppm_data[idx:]

            # 构建PNG
            # PNG由: signature + IHDR + IDAT + IEND 组成
            def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
                chunk = chunk_type + data
                crc = struct.pack('>I', zlib.crc32(chunk) & 0xFFFFFFFF)
                return struct.pack('>I', len(data)) + chunk + crc

            png_signature = b'\x89PNG\r\n\x1a\n'

            # IHDR: width(4) + height(4) + bit_depth(1) + color_type(1)
            #       + compression(1) + filter(1) + interlace(1)
            ihdr_data = struct.pack('>IIBBBBB', width, height,
                                    8, 2, 0, 0, 0)  # 8bit, RGB, deflate
            ihdr = _png_chunk(b'IHDR', ihdr_data)

            # IDAT: 每行前加filter byte(0=None)，然后zlib压缩
            raw_rows = bytearray()
            row_bytes = width * 3
            for y in range(height):
                raw_rows.append(0)  # filter type: None
                row_start = y * row_bytes
                raw_rows.extend(pixel_data[row_start:row_start + row_bytes])

            compressed = zlib.compress(bytes(raw_rows), 6)
            idat = _png_chunk(b'IDAT', compressed)

            # IEND
            iend = _png_chunk(b'IEND', b'')

            png_bytes = png_signature + ihdr + idat + iend
            return base64.b64encode(png_bytes).decode('utf-8')

        except Exception as e:
            logger.warning(f"PPM转PNG失败: {e}")
            return ""

    # 虚拟机截图 ###############################################################
    def VMScreen(self, vm_name: str = "") -> str:
        """获取虚拟机截图
        
        :param vm_name: 虚拟机名称
        :return: base64编码的截图字符串（纯base64，不含data:前缀），失败则返回空字符串
        """
        try:
            logger.info(f"[{self.hs_config.server_name}] 开始获取虚拟机 {vm_name} 截图")
            
            # 1. 检查虚拟机是否存在
            if vm_name not in self.vm_saving:
                logger.error(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} 不存在")
                return ""
            
            # 2. 获取虚拟机信息
            result = self.get_info(vm_name)
            if not result.success:
                logger.error(f"[{self.hs_config.server_name}] 获取虚拟机信息失败: {result.message}")
                return ""
            
            vm_conn = result.results[0]
            vmid = self.get_vmid(self.vm_saving[vm_name])
            if vmid is None:
                logger.error(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} VMID未找到")
                return ""
            
            # 3. 检查虚拟机是否正在运行
            status = vm_conn.status.current.get()
            if status.get('status') != 'running':
                logger.warning(f"[{self.hs_config.server_name}] 虚拟机 {vm_name} 未运行，无法获取截图")
                return ""
            
            # 4. 通过 SSH + qm screendump 获取截图（PNG格式）
            import base64
            import io

            ssh = None
            try:
                remote_png = f"/tmp/screen-{vmid}.png"
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    self.hs_config.server_addr,
                    username=self.hs_config.server_user,
                    password=self.hs_config.server_pass,
                    timeout=10)

                # 5. 先清理旧文件，避免读到过期截图
                ssh.exec_command(f"rm -f {remote_png}")
                time.sleep(0.3)

                # 6. 使用 pvesh 调用 PVE API 获取截图（输出PNG到文件）
                #    pvesh create /nodes/{node}/qemu/{vmid}/monitor 
                #    --command 'screendump {file}'
                #    或直接使用 qm screendump 命令（PVE 8.x+）
                #    回退方案：qm monitor + screendump
                screenshot_ok = False

                # 方案1: 尝试 qm guest screendump（需要 qemu-guest-agent）
                # 方案2: 使用 qm monitor screendump（通用方案）
                remote_ppm = f"/tmp/screen-{vmid}.ppm"
                ssh.exec_command(f"rm -f {remote_ppm}")
                time.sleep(0.2)

                cmd = (f"echo 'screendump {remote_ppm}' "
                       f"| qm monitor {vmid}")
                stdin, stdout, stderr = ssh.exec_command(cmd)
                stdout.channel.recv_exit_status()

                # 等待文件生成（screendump是异步的，需要等待）
                time.sleep(1.5)

                # 检查PPM文件是否存在且非空
                check_cmd = (f"test -s {remote_ppm} "
                             f"&& echo 'ok' || echo 'fail'")
                stdin, stdout, stderr = ssh.exec_command(check_cmd)
                check_result = stdout.read().decode().strip()

                if check_result == 'ok':
                    # 7. 先通过SFTP读取PPM文件到内存（避免后续操作破坏源文件）
                    #    增加重试机制，防止screendump异步写入与读取之间的竞态
                    ppm_data = b''
                    for _retry in range(3):
                        try:
                            sftp = ssh.open_sftp()
                            buf = io.BytesIO()
                            sftp.getfo(remote_ppm, buf)
                            sftp.close()
                            ppm_data = buf.getvalue()
                            break
                        except (IOError, OSError) as sftp_err:
                            logger.warning(
                                f"[{self.hs_config.server_name}] "
                                f"SFTP读取PPM文件失败(重试{_retry+1}/3): {sftp_err}")
                            try:
                                sftp.close()
                            except Exception:
                                pass
                            time.sleep(1.0)
                            ppm_data = b''

                    if ppm_data:
                        # 8. PPM转PNG：优先PIL，回退纯Python实现
                        try:
                            from PIL import Image
                            img = Image.open(io.BytesIO(ppm_data))
                            out = io.BytesIO()
                            img.save(out, format='PNG')
                            screenshot_base64 = base64.b64encode(
                                out.getvalue()).decode('utf-8')
                        except (ImportError, Exception):
                            # PIL不可用或转换异常，使用纯Python转PNG
                            screenshot_base64 = self._ppm_to_png_base64(
                                ppm_data)
                        screenshot_ok = bool(screenshot_base64)

                # 8. 清理临时文件
                ssh.exec_command(
                    f"rm -f {remote_ppm} {remote_png}")
                ssh.close()
                ssh = None

                if screenshot_ok:
                    logger.info(
                        f"[{self.hs_config.server_name}] "
                        f"成功获取虚拟机 {vm_name} 截图")
                    return screenshot_base64
                else:
                    logger.error(
                        f"[{self.hs_config.server_name}] "
                        f"screendump未生成有效文件")
                    return ""

            except Exception as e:
                logger.error(
                    f"[{self.hs_config.server_name}] "
                    f"获取截图失败: {str(e)}")
                traceback.print_exc()
                if ssh:
                    try:
                        ssh.close()
                    except Exception:
                        pass
                return ""
                
        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] 获取虚拟机截图时出错: {str(e)}")
            traceback.print_exc()
            return ""

    # 查找PCI设备 #################################################################
    def PCIShows(self) -> Dict[str, 'VFConfig']:
        """获取可用的PCI直通设备列表
        通过SSH lspci -nn列出所有PCI设备及其IOMMU组
        Returns:
            dict: {pci_id: VFConfig}
        """
        from MainObject.Config.VFConfig import VFConfig
        try:
            logger.info(f"[{self.hs_config.server_name}] 开始获取PCI设备列表")

            client, result = self.api_conn()
            if not result.success:
                return {}

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                ssh.connect(
                    self.hs_config.server_addr,
                    username=self.hs_config.server_user,
                    password=self.hs_config.server_pass
                )

                # 列出所有PCI设备（包含设备ID）
                cmd = "lspci -nn"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                output = stdout.read().decode('utf-8')

                device_dict = {}
                if output:
                    for line in output.strip().split('\n'):
                        parts = line.split(' ', 1)
                        if len(parts) >= 2:
                            pci_id = parts[0]  # 如: 01:00.0
                            device_info = parts[1]
                            # 提取设备名称和类型
                            device_name = device_info.strip()
                            device_dict[pci_id] = VFConfig(
                                gpu_uuid=pci_id,
                                gpu_mdev="PVE_Passthrough",
                                gpu_hint=device_name
                            )

                ssh.close()
                logger.info(f"[{self.hs_config.server_name}] 共找到 {len(device_dict)} 个PCI设备")
                return device_dict

            except Exception as ssh_error:
                logger.error(f"[{self.hs_config.server_name}] SSH连接失败: {str(ssh_error)}")
                try:
                    ssh.close()
                except Exception as e_close:
                    logger.warning(f"[{self.hs_config.server_name}] 关闭SSH连接失败: {str(e_close)}")
                return {}

        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] 获取PCI设备列表失败: {str(e)}")
            traceback.print_exc()
            return {}

    # PCI设备直通 ##################################################################
    def PCISetup(self, vm_name: str, config, pci_key: str, in_flag=True):
        """PVE PCI直通 - 通过API设置hostpci参数"""
        from MainObject.Public.ZMessage import ZMessage
        try:
            if vm_name not in self.vm_saving:
                return ZMessage(success=False, action="PCISetup", message="虚拟机不存在")

            from MainObject.Config.VMPowers import VMPowers
            vm_config = self.vm_saving[vm_name]
            if vm_config.vm_flag not in [VMPowers.STOPPED, VMPowers.ON_STOP, VMPowers.UNKNOWN]:
                return ZMessage(success=False, action="PCISetup", message="PCI直通需要先关闭虚拟机")

            client, result = self.api_conn()
            if not result.success:
                return ZMessage(success=False, action="PCISetup", message=f"PVE连接失败: {result.message}")

            # 获取虚拟机VMID
            vm_conf_pci = self.vm_saving[vm_name]
            vmid = self.get_vmid(vm_conf_pci)
            if not vmid:
                return ZMessage(success=False, action="PCISetup", message="无法获取虚拟机VMID")

            node = self.hs_config.launch_path

            pci_id = config.gpu_uuid

            if in_flag:
                # 添加PCI直通 - 找一个空闲的hostpci槽位
                slot = 0
                existing_config = client.nodes(node).qemu(vmid).config.get()
                while f'hostpci{slot}' in existing_config:
                    slot += 1
                    if slot > 15:
                        return ZMessage(success=False, action="PCISetup", message="PCI直通槽位已满")

                client.nodes(node).qemu(vmid).config.put(**{
                    f'hostpci{slot}': f'{pci_id},pcie=1'
                })
            else:
                # 移除PCI直通 - 找到对应的hostpci槽位并删除
                existing_config = client.nodes(node).qemu(vmid).config.get()
                delete_key = None
                for i in range(16):
                    key = f'hostpci{i}'
                    if key in existing_config:
                        val = existing_config[key]
                        if pci_id in str(val):
                            delete_key = key
                            break

                if delete_key:
                    client.nodes(node).qemu(vmid).config.put(delete=delete_key)

            # 调用基类写入配置
            return super().PCISetup(vm_name, config, pci_key, in_flag)

        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] PCI直通操作失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(success=False, action="PCISetup", message=str(e))

    # 查找USB设备 ##################################################################
    def USBShows(self) -> Dict[str, 'USBInfos']:  # noqa
        """获取PVE主机上的USB设备列表"""
        from MainObject.Config.USBInfos import USBInfos
        try:
            client, result = self.api_conn()
            if not result.success:
                return {}

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                ssh.connect(
                    self.hs_config.server_addr,
                    username=self.hs_config.server_user,
                    password=self.hs_config.server_pass
                )

                cmd = "lsusb"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                output = stdout.read().decode('utf-8')

                usb_dict = {}
                if output:
                    for line in output.strip().split('\n'):
                        if 'ID ' in line:
                            id_part = line.split('ID ')[1]
                            vid_pid = id_part.split(' ')[0]
                            name = id_part.split(' ', 1)[1] if ' ' in id_part else vid_pid
                            if ':' in vid_pid:
                                vid, pid = vid_pid.split(':')
                                usb_dict[vid_pid] = USBInfos(
                                    vid_uuid=vid, pid_uuid=pid, usb_hint=name.strip())

                ssh.close()
                logger.info(f"[{self.hs_config.server_name}] 发现 {len(usb_dict)} 个USB设备")
                return usb_dict

            except Exception as ssh_error:
                logger.error(f"[{self.hs_config.server_name}] SSH获取USB设备失败: {str(ssh_error)}")
                try:
                    ssh.close()
                except Exception as e_close:
                    logger.warning(f"[{self.hs_config.server_name}] 关闭SSH连接失败: {str(e_close)}")
                return {}

        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] 获取USB设备列表失败: {str(e)}")
            return {}

    # USB设备直通 ##################################################################
    def USBSetup(self, vm_name: str, ud_info, ud_keys: str, in_flag=True):
        """PVE USB直通 - 通过API设置usb参数（支持热插拔）"""
        from MainObject.Public.ZMessage import ZMessage
        try:
            if vm_name not in self.vm_saving:
                return ZMessage(success=False, action="USBSetup", message="虚拟机不存在")

            client, result = self.api_conn()
            if not result.success:
                return ZMessage(success=False, action="USBSetup", message=f"PVE连接失败: {result.message}")

            vm_conf_usb = self.vm_saving[vm_name]
            vmid = self.get_vmid(vm_conf_usb)
            if not vmid:
                return ZMessage(success=False, action="USBSetup", message="无法获取虚拟机VMID")

            node = self.hs_config.launch_path

            vid = ud_info.vid_uuid
            pid = ud_info.pid_uuid

            if in_flag:
                # 找空闲usb槽位
                slot = 0
                existing_config = client.nodes(node).qemu(vmid).config.get()
                while f'usb{slot}' in existing_config:
                    slot += 1
                    if slot > 4:
                        return ZMessage(success=False, action="USBSetup", message="USB槽位已满")

                client.nodes(node).qemu(vmid).config.put(**{
                    f'usb{slot}': f'host={vid}:{pid}'
                })
            else:
                # 移除USB - 找到对应槽位
                existing_config = client.nodes(node).qemu(vmid).config.get()
                delete_key = None
                for i in range(5):
                    key = f'usb{i}'
                    if key in existing_config:
                        val = str(existing_config[key])
                        if f'{vid}:{pid}' in val:
                            delete_key = key
                            break

                if delete_key:
                    client.nodes(node).qemu(vmid).config.put(delete=delete_key)

            # 更新虚拟机配置中的USB设备列表（不触发VMUpdate）
            vm_conf = self.vm_saving[vm_name]
            if in_flag:
                # 添加USB设备到配置
                if ud_keys not in vm_conf.usb_all:
                    vm_conf.usb_all[ud_keys] = ud_info
                    logger.info(f"[{self.hs_config.server_name}] 添加USB设备到配置: {ud_keys}")
            else:
                # 从配置中移除USB设备
                if ud_keys in vm_conf.usb_all:
                    del vm_conf.usb_all[ud_keys]
                    logger.info(f"[{self.hs_config.server_name}] 从配置中移除USB设备: {ud_keys}")

            logger.info(f"[{self.hs_config.server_name}] USB设备{'添加' if in_flag else '移除'}成功: {ud_keys}")
            return ZMessage(success=True, action="USBSetup", message="USB设备操作成功")

        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] USB直通操作失败: {str(e)}")
            return ZMessage(success=False, action="USBSetup", message=str(e))

    # 虚拟机状态 ################################################################
    def VMStatus(self,
                 vm_name: str = "",
                 s_t: int = None,
                 e_t: int = None) -> dict[str, list[HWStatus]]:
        # 专用操作 =============================================================
        # TODO: 增加此主机需要执行的任务
        # 通用操作 =============================================================
        return super().VMStatus(vm_name, s_t, e_t)
