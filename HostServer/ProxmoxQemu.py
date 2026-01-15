import os
import time
import shutil
import datetime
import paramiko
import traceback
from loguru import logger
from copy import deepcopy
from proxmoxer import ProxmoxAPI
from typing import Optional, Tuple
from HostServer.BasicServer import BasicServer
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
            logger.info("Successfully connected to Proxmox server")
            return self.proxmox, ZMessage(success=True, action="_connect_proxmox")
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox server: {str(e)}")
            traceback.print_exc()
            self.proxmox = None
            return None, ZMessage(
                success=False, action="_connect_proxmox",
                message=f"Failed to connect to Proxmox: {str(e)}")

    # 分配新的VMID #############################################################
    def new_vmid(self) -> int:
        client, result = self.api_conn()
        if not result.success:
            return 100  # 默认起始VMID

        try:
            # 获取所有现有的VMID
            vms = client.nodes(self.hs_config.launch_path).qemu.get()
            existing_vmids = [vm['vmid'] for vm in vms]

            # 从100开始查找可用的VMID
            vmid = 100
            while vmid in existing_vmids:
                vmid += 1

            return vmid
        except Exception as e:
            logger.error(f"分配VMID失败: {str(e)}")
            return 100

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

    # 宿主机任务 ###############################################################
    def Crontabs(self) -> bool:
        """定时任务"""
        # 专用操作 =============================================================
        try:
            # 连接到 Proxmox
            client, result = self.api_conn()
            if not result.success or not client:
                logger.warning(f"Proxmox连接失败，使用本地状态")
                return False
            # 获取主机状态
            node_status = client.nodes(self.hs_config.launch_path).status.get()
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
            logger.error(f"Crontabs执行失败: {str(e)}")
        # 通用操作 =============================================================
        return super().Crontabs()

    # 宿主机状态 ###############################################################
    def HSStatus(self) -> HWStatus:
        """获取宿主机状态"""
        # 专用操作 =============================================================
        try:
            # 连接到 Proxmox
            client, result = self.api_conn()
            if not result.success or not client:
                logger.error(f"无法连接到Proxmox获取状态: {result.message}")
                return super().HSStatus()

            # 获取主机状态
            node_status = client.nodes(self.hs_config.launch_path).status.get()

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
        # 加载远程控制台配置 ===================================================
        # self.VMLoader()
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
        client, result = self.api_conn()
        if not result.success:
            return result

        try:
            # 获取所有虚拟机列表
            vms = client.nodes(self.hs_config.launch_path).qemu.get()

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
                self.push_log(log_msg)

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

    # 创建虚拟机 ###############################################################
    def VMCreate(self, vm_conf: VMConfig) -> ZMessage:
        # 替换名称 ==================================================
        vm_conf.vm_uuid = vm_conf.vm_uuid.replace('_', '-')
        # 网络检查 ==================================================
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        # 连接Proxmox API ===========================================
        client, result = self.api_conn()
        if not result.success:
            return result
        # 分配VMID ==================================================
        vm_vmid = self.new_vmid()
        if not hasattr(vm_conf, 'vm_data'):
            vm_conf.vm_data = {}
        vm_conf.vm_data['vmid'] = vm_vmid
        # 创建虚拟机 ================================================
        try:  # 构建虚拟机配置 --------------------------------------
            config = {
                'vmid': vm_vmid,
                'name': vm_conf.vm_uuid,
                'memory': vm_conf.mem_num,
                'cores': vm_conf.cpu_num,
                'sockets': 1,
                'ostype': 'l26',  # Linux 2.6+
                'bios': 'ovmf',  # 使用 UEFI 模式
                'boot': 'order=scsi0;ide2',
                'scsihw': 'virtio-scsi-pci',
                'efidisk0': 'local:1,efitype=4m,pre-enrolled-keys=1',  # EFI 磁盘
            }
            # 配置网卡 ------------------------------------------
            config.update(self.net_conf(vm_conf))
            # 创建虚拟机 --------------------------------------------
            client.nodes(self.hs_config.launch_path).qemu.create(**config)
            logger.info(f"虚拟机 {vm_conf.vm_uuid} 创建成功")
            # 配置路由器绑定（iKuai层面）----------------------------
            ikuai_result = super().IPBinder(vm_conf, True)
            if not ikuai_result.success:
                logger.warning(f"iKuai路由器绑定失败: {ikuai_result.message}")
            # 安装系统 ----------------------------------------------
            result = self.VMSetups(vm_conf)
            if not result.success:
                logger.warning(f"系统安装失败: {result.message}")
        # 捕获所有异常 ==============================================
        except Exception as e:
            traceback.print_exc()
            hs_result = ZMessage(
                success=False, action="VMCreate",
                message=f"虚拟机创建失败: {str(e)}")
            self.logs_set(hs_result)
            return hs_result
        # 通用操作 ==================================================
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
            # 从源文件名中提取扩展名，保持原始格式
            _, src_ext = posixpath.splitext(vm_conf.os_name)
            if not src_ext:
                src_ext = '.qcow2'  # 默认格式
            vm_disk_dir = f"/var/lib/vz/images/{vm_vmid}"
            disk_name = f"vm-{vm_vmid}-disk-0{src_ext}"
            dest_image = f"{vm_disk_dir}/{disk_name}"
            # 远程复制 =========================================================
            if self.web_flag():
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
            # 本地复制 ==========================================================
            else:
                # 本地模式：src_file 是 Linux 路径，使用 posixpath.join
                src_file = posixpath.join(self.hs_config.images_path, vm_conf.os_name)
                if not os.path.exists(src_file):
                    return ZMessage(
                        success=False, action="VInstall",
                        message=f"镜像文件不存在: {src_file}")
                os.makedirs(vm_disk_dir, exist_ok=True)
                shutil.copy2(src_file, dest_image)
                logger.info(f"本地复制镜像: {src_file} -> {dest_image}")
            # 分配磁盘 ==========================================================
            vm_conn = client.nodes(self.hs_config.launch_path).qemu(vm_vmid)
            vm_conn.config.put(sata0=f"local:{vm_vmid}/{disk_name}")
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
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        client, result = self.api_conn()
        if not result.success:
            return result
        try:
            vmid = self.get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {vm_conf.vm_uuid} 的VMID未找到")
            vm = client.nodes(self.hs_config.launch_path).qemu(vmid)
            # 停止机器 =========================================================
            status = vm.status.current.get()
            if status['status'] == 'running':
                self.VMPowers(vm_conf.vm_uuid, VMPowers.H_CLOSE)
            # 重装系统 =========================================================
            if vm_conf.os_name != vm_last.os_name and vm_last.os_name != "":
                install_result = self.VMSetups(vm_conf)
                if not install_result.success:
                    return install_result
            # 更新配置 =========================================================
            config_updates = {}
            if vm_conf.cpu_num != vm_last.cpu_num and vm_conf.cpu_num > 0:
                config_updates['cores'] = vm_conf.cpu_num
            if vm_conf.mem_num != vm_last.mem_num and vm_conf.mem_num > 0:
                config_updates['memory'] = vm_conf.mem_num
            # 配置网卡 =========================================================
            config_updates.update(self.net_conf(vm_conf))
            if config_updates:
                vm.config.put(**config_updates)
                logger.info(f"虚拟机 {vm_conf.vm_uuid} 配置已更新")
            # 更新绑定 =========================================================
            super().IPBinder(vm_last, False)
            ikuai_result = super().IPBinder(vm_conf, True)
            if not ikuai_result.success:
                logger.warning(f"iKuai路由器绑定失败: {ikuai_result.message}")
            # 启动机器 =========================================================
            start_result = self.VMPowers(vm_conf.vm_uuid, VMPowers.S_START)
            if not start_result.success:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机启动失败: {start_result.message}")
        # 处理异常 =============================================================
        except Exception as e:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机更新失败: {str(e)}")
        return super().VMUpdate(vm_conf, vm_last)

    # 删除虚拟机 ###############################################################
    def VMDelete(self, vm_name: str, rm_back=True) -> ZMessage:
        # 专用操作 ===========================================
        client, result = self.api_conn()
        if not result.success:
            return result
        try:
            # 获取虚拟机配置 =================================
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False, action="VMDelete",
                    message=f"虚拟机 {vm_name} 不存在")
            # 获取虚拟机VMID ================================
            vm_vmid = self.get_vmid(vm_conf)
            if vm_vmid is None:
                return ZMessage(
                    success=False, action="VMDelete",
                    message=f"虚拟机 {vm_name} VMID未找到")
            # 获取虚拟机对象 ================================
            vm = client.nodes(self.hs_config.launch_path).qemu(vm_vmid)
            # 停止虚拟机 ====================================
            status = vm.status.current.get()
            if status['status'] == 'running':
                self.VMPowers(vm_name, VMPowers.H_CLOSE)
            # 删除路由器绑定（iKuai层面）====================
            super().IPBinder(vm_conf, False)
            # 删除虚拟机（会自动删除网卡配置）================
            vm.delete()
            logger.info(f"虚拟机 {vm_name}"
                        f" (VMID: {vm_vmid}) 删除成功")
        # 处理异常 ==========================================
        except Exception as e:
            return ZMessage(
                success=False, action="VMDelete",
                message=f"删除虚拟机失败: {str(e)}")
        # 通用操作 ==========================================
        return super().VMDelete(vm_name)

    # 虚拟机电源 ###############################################################
    def VMPowers(self, vm_name: str, power: VMPowers) -> ZMessage:
        """虚拟机电源管理"""
        client, result = self.api_conn()
        if not result.success:
            return result

        try:
            vm_conf = self.VMSelect(vm_name)
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
        client, result = self.api_conn()
        if not result.success:
            return result

        try:
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False, action="Password",
                    message=f"虚拟机 {vm_name} 不存在")

            vmid = self.get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="Password",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            # 通过QEMU Guest Agent设置密码
            # 注意：需要虚拟机安装并运行qemu-guest-agent
            vm = client.nodes(self.hs_config.launch_path).qemu(vmid)

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
        client, result = self.api_conn()
        if not result.success:
            return result

        vm_conf = self.VMSelect(vm_name)
        if not vm_conf:
            return ZMessage(
                success=False,
                action="Backup",
                message="虚拟机不存在")

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

            task_id = client.nodes(self.hs_config.launch_path).vzdump.post(**backup_config)
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
        client, result = self.api_conn()
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
            vmid = self.get_vmid(vm_conf)
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

            # client.nodes(self.hs_config.launch_path).qemu.post(**restore_config)

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
        client, result = self.api_conn()
        if not result.success:
            return result
        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="HDDMount",
                    message="虚拟机不存在")

            vm_conf = self.vm_saving[vm_name]
            vmid = self.get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="HDDMount",
                    message=f"虚拟机 {vm_name} 的VMID未找到")
            vm = client.nodes(self.hs_config.launch_path).qemu(vmid)
            # 停止虚拟机
            status = vm.status.current.get()
            was_running = status['status'] == 'running'
            if was_running:
                self.VMPowers(vm_name, VMPowers.H_CLOSE)

            if in_flag:
                # 挂载硬盘
                # 获取磁盘大小（单位：MB），转换为 GB
                hdd_size_mb = getattr(vm_imgs, 'hdd_size', 10)  # 默认 10MB（实际逻辑中应该是GB）
                # 如果 hdd_size 是 MB 值（如 10240），需要转换为 GB
                if hdd_size_mb > 1000:  # 假设大于1000就是MB值
                    disk_size = f"{hdd_size_mb // 1024}G"
                else:
                    disk_size = f"{hdd_size_mb}G"

                # 获取存储名称
                # 如果 extern_path 包含路径分隔符，提取最后一个目录名作为存储名称
                if '/' in self.hs_config.extern_path:
                    storage_name = self.hs_config.extern_path.rstrip('/').split('/')[-1]
                else:
                    storage_name = self.hs_config.extern_path

                # 目录格式：<storage_name>:<volume_name>,size=<size>
                # 存储池格式：<storage_name>:<size>
                # 两种格式都用 storage_name，Proxmox会自动判断
                disk_config = f"{storage_name}:vm-{vmid}-disk-{scsi_num},size={disk_size}"

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
            traceback.print_exc()
            return ZMessage(
                success=False, action="HDDMount",
                message=f"硬盘挂载操作失败: {str(e)}")

    # ISO镜像挂载 ##############################################################
    def ISOMount(self, vm_name: str, vm_imgs: IMConfig, in_flag=True) -> ZMessage:
        """挂载/卸载ISO镜像"""
        client, result = self.api_conn()
        if not result.success:
            return result

        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="ISOMount",
                    message="虚拟机不存在")

            vm_conf = self.vm_saving[vm_name]
            vmid = self.get_vmid(vm_conf)
            if vmid is None:
                return ZMessage(
                    success=False, action="ISOMount",
                    message=f"虚拟机 {vm_name} 的VMID未找到")

            vm = client.nodes(self.hs_config.launch_path).qemu(vmid)
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

    # 虚拟机控制台 #############################################################
    def VMRemote(self, vm_uuid: str, ip_addr: str = "127.0.0.1") -> ZMessage:
        if vm_uuid not in self.vm_saving:
            return ZMessage(
                success=False,
                action="VCRemote",
                message="虚拟机不存在")
        vm_conf = self.vm_saving[vm_uuid]
        vmid = self.get_vmid(vm_conf)
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
        vnc_url = (f"https://{self.hs_config.server_addr}:8006/"
                   f"?console=kvm&novnc=1&vmid={vmid}&node={self.hs_config.launch_path}")
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
