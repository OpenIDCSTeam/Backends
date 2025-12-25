import os
import ssl
import time
from typing import Optional, List, Dict, Any
from loguru import logger

try:
    from pyVim.connect import SmartConnect, Disconnect
    from pyVim.task import WaitForTask
    from pyVmomi import vim, vmodl
except ImportError:
    logger.error("pyvmomi库未安装，请运行: pip install pyvmomi")
    raise

from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.ZMessage import ZMessage


class vSphereAPI:
    """vSphere ESXi API封装类"""

    def __init__(self, host: str, user: str, password: str, port: int = 443, 
                 datastore_name: str = "datastore1"):
        """
        初始化vSphere API连接
        
        :param host: ESXi主机地址
        :param user: 用户名
        :param password: 密码
        :param port: API端口，默认443
        :param datastore_name: 数据存储名称
        """
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.datastore_name = datastore_name
        self.si = None  # ServiceInstance
        self.content = None
        
    def connect(self) -> ZMessage:
        """连接到ESXi主机"""
        try:
            # 禁用SSL证书验证（生产环境建议启用）
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.verify_mode = ssl.CERT_NONE
            
            # 连接到ESXi
            self.si = SmartConnect(
                host=self.host,
                user=self.user,
                pwd=self.password,
                port=self.port,
                sslContext=context
            )
            
            if not self.si:
                return ZMessage(success=False, action="connect", 
                              message="无法连接到ESXi主机")
            
            self.content = self.si.RetrieveContent()
            logger.info(f"成功连接到ESXi主机: {self.host}")
            return ZMessage(success=True, action="connect", 
                          message="连接成功")
            
        except Exception as e:
            logger.error(f"连接ESXi失败: {str(e)}")
            return ZMessage(success=False, action="connect", 
                          message=f"连接失败: {str(e)}")
    
    def disconnect(self) -> ZMessage:
        """断开与ESXi的连接"""
        try:
            if self.si:
                Disconnect(self.si)
                self.si = None
                self.content = None
                logger.info(f"已断开与ESXi主机的连接: {self.host}")
            return ZMessage(success=True, action="disconnect", 
                          message="断开连接成功")
        except Exception as e:
            logger.error(f"断开连接失败: {str(e)}")
            return ZMessage(success=False, action="disconnect", 
                          message=f"断开连接失败: {str(e)}")
    
    def _get_obj(self, vimtype, name: str = None):
        """
        获取vSphere对象
        
        :param vimtype: 对象类型（如vim.VirtualMachine）
        :param name: 对象名称，如果为None则返回所有对象
        :return: 对象或对象列表
        """
        if not self.content:
            return None
            
        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, [vimtype], True)
        
        obj_list = container.view
        container.Destroy()
        
        if name:
            for obj in obj_list:
                if obj.name == name:
                    return obj
            return None
        return obj_list
    
    def _wait_for_task(self, task) -> ZMessage:
        """等待任务完成"""
        try:
            WaitForTask(task)
            if task.info.state == vim.TaskInfo.State.success:
                return ZMessage(success=True, action="task", 
                              message="任务执行成功")
            else:
                error_msg = str(task.info.error) if task.info.error else "未知错误"
                return ZMessage(success=False, action="task", 
                              message=f"任务失败: {error_msg}")
        except Exception as e:
            return ZMessage(success=False, action="task", 
                          message=f"任务执行异常: {str(e)}")
    
    def get_vm(self, vm_name: str):
        """获取虚拟机对象"""
        return self._get_obj(vim.VirtualMachine, vm_name)
    
    def list_vms(self, filter_prefix: str = "") -> List[Dict[str, Any]]:
        """
        列出所有虚拟机
        
        :param filter_prefix: 名称前缀过滤
        :return: 虚拟机信息列表
        """
        vms = self._get_obj(vim.VirtualMachine)
        vm_list = []
        
        for vm in vms:
            if filter_prefix and not vm.name.startswith(filter_prefix):
                continue
                
            vm_info = {
                "name": vm.name,
                "power_state": vm.runtime.powerState,
                "guest_os": vm.config.guestFullName if vm.config else "Unknown",
                "cpu": vm.config.hardware.numCPU if vm.config else 0,
                "memory_mb": vm.config.hardware.memoryMB if vm.config else 0,
            }
            vm_list.append(vm_info)
        
        return vm_list
    
    def get_datastore(self, datastore_name: str = None):
        """获取数据存储对象"""
        ds_name = datastore_name or self.datastore_name
        return self._get_obj(vim.Datastore, ds_name)
    
    def get_resource_pool(self):
        """获取资源池"""
        host = self._get_obj(vim.HostSystem)
        if host and len(host) > 0:
            return host[0].parent.resourcePool
        return None
    
    def get_network(self, network_name: str):
        """获取网络对象"""
        networks = self._get_obj(vim.Network)
        for network in networks:
            if network.name == network_name:
                return network
        return None
    
    def create_vm(self, vm_conf: VMConfig, hs_config: HSConfig) -> ZMessage:
        """
        创建虚拟机
        
        :param vm_conf: 虚拟机配置
        :param hs_config: 主机配置
        :return: 操作结果
        """
        try:
            # 获取必要的对象
            datastore = self.get_datastore()
            if not datastore:
                return ZMessage(success=False, action="create_vm", 
                              message=f"数据存储 {self.datastore_name} 不存在")
            
            resource_pool = self.get_resource_pool()
            if not resource_pool:
                return ZMessage(success=False, action="create_vm", 
                              message="无法获取资源池")
            
            # 获取虚拟机文件夹
            vm_folder = self.content.rootFolder.childEntity[0].vmFolder
            
            # 创建虚拟机配置规格
            config_spec = vim.vm.ConfigSpec()
            config_spec.name = vm_conf.vm_uuid
            config_spec.memoryMB = vm_conf.ram_num
            config_spec.numCPUs = vm_conf.cpu_num
            config_spec.guestId = self._get_guest_id(vm_conf.os_name)
            
            # 虚拟机文件位置
            files = vim.vm.FileInfo()
            files.vmPathName = f"[{self.datastore_name}] {vm_conf.vm_uuid}/"
            config_spec.files = files
            
            # 添加SCSI控制器
            scsi_spec = vim.vm.device.VirtualDeviceSpec()
            scsi_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            scsi_ctrl = vim.vm.device.ParaVirtualSCSIController()
            scsi_ctrl.key = 1000
            scsi_ctrl.busNumber = 0
            scsi_ctrl.sharedBus = vim.vm.device.VirtualSCSIController.Sharing.noSharing
            scsi_spec.device = scsi_ctrl
            
            device_changes = [scsi_spec]
            
            # 添加网卡
            for nic_name, nic_conf in vm_conf.nic_all.items():
                # 确定网络名称
                if nic_conf.net_mode == "nat":
                    network_name = hs_config.network_nat
                else:
                    network_name = hs_config.network_pub
                
                network = self.get_network(network_name)
                if not network:
                    logger.warning(f"网络 {network_name} 不存在，跳过网卡 {nic_name}")
                    continue
                
                nic_spec = vim.vm.device.VirtualDeviceSpec()
                nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
                nic = vim.vm.device.VirtualVmxnet3()
                nic.addressType = 'manual'
                nic.macAddress = nic_conf.mac_addr
                
                # 网络连接
                nic.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                nic.backing.network = network
                nic.backing.deviceName = network_name
                
                nic.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
                nic.connectable.startConnected = True
                nic.connectable.allowGuestControl = True
                nic.connectable.connected = True
                
                nic_spec.device = nic
                device_changes.append(nic_spec)
            
            config_spec.deviceChange = device_changes
            
            # 创建虚拟机
            task = vm_folder.CreateVM_Task(config=config_spec, pool=resource_pool)
            result = self._wait_for_task(task)
            
            if result.success:
                logger.info(f"虚拟机 {vm_conf.vm_uuid} 创建成功")
            
            return result
            
        except Exception as e:
            logger.error(f"创建虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="create_vm", 
                          message=f"创建失败: {str(e)}")
    
    def delete_vm(self, vm_name: str) -> ZMessage:
        """
        删除虚拟机
        
        :param vm_name: 虚拟机名称
        :return: 操作结果
        """
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="delete_vm", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            # 如果虚拟机正在运行，先关闭
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                power_result = self.power_off(vm_name)
                if not power_result.success:
                    return power_result
                time.sleep(2)  # 等待关机完成
            
            # 删除虚拟机
            task = vm.Destroy_Task()
            result = self._wait_for_task(task)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 删除成功")
            
            return result
            
        except Exception as e:
            logger.error(f"删除虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="delete_vm", 
                          message=f"删除失败: {str(e)}")
    
    def power_on(self, vm_name: str) -> ZMessage:
        """开机"""
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="power_on", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                return ZMessage(success=True, action="power_on", 
                              message="虚拟机已经在运行")
            
            task = vm.PowerOn()
            return self._wait_for_task(task)
            
        except Exception as e:
            logger.error(f"开机失败: {str(e)}")
            return ZMessage(success=False, action="power_on", 
                          message=f"开机失败: {str(e)}")
    
    def power_off(self, vm_name: str) -> ZMessage:
        """关机"""
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="power_off", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
                return ZMessage(success=True, action="power_off", 
                              message="虚拟机已经关闭")
            
            task = vm.PowerOff()
            return self._wait_for_task(task)
            
        except Exception as e:
            logger.error(f"关机失败: {str(e)}")
            return ZMessage(success=False, action="power_off", 
                          message=f"关机失败: {str(e)}")
    
    def suspend(self, vm_name: str) -> ZMessage:
        """挂起"""
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="suspend", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            task = vm.Suspend()
            return self._wait_for_task(task)
            
        except Exception as e:
            logger.error(f"挂起失败: {str(e)}")
            return ZMessage(success=False, action="suspend", 
                          message=f"挂起失败: {str(e)}")
    
    def reset(self, vm_name: str) -> ZMessage:
        """重启"""
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="reset", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            task = vm.Reset()
            return self._wait_for_task(task)
            
        except Exception as e:
            logger.error(f"重启失败: {str(e)}")
            return ZMessage(success=False, action="reset", 
                          message=f"重启失败: {str(e)}")
    
    def create_snapshot(self, vm_name: str, snapshot_name: str, 
                       description: str = "") -> ZMessage:
        """
        创建快照
        
        :param vm_name: 虚拟机名称
        :param snapshot_name: 快照名称
        :param description: 快照描述
        :return: 操作结果
        """
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="create_snapshot", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            task = vm.CreateSnapshot(
                name=snapshot_name,
                description=description,
                memory=False,  # 不包含内存状态
                quiesce=False  # 不静默文件系统
            )
            result = self._wait_for_task(task)
            
            if result.success:
                logger.info(f"快照 {snapshot_name} 创建成功")
            
            return result
            
        except Exception as e:
            logger.error(f"创建快照失败: {str(e)}")
            return ZMessage(success=False, action="create_snapshot", 
                          message=f"创建快照失败: {str(e)}")
    
    def revert_snapshot(self, vm_name: str, snapshot_name: str) -> ZMessage:
        """
        恢复快照
        
        :param vm_name: 虚拟机名称
        :param snapshot_name: 快照名称
        :return: 操作结果
        """
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="revert_snapshot", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            # 查找快照
            snapshot = self._find_snapshot(vm.snapshot.rootSnapshotList, snapshot_name)
            if not snapshot:
                return ZMessage(success=False, action="revert_snapshot", 
                              message=f"快照 {snapshot_name} 不存在")
            
            task = snapshot.snapshot.Revert()
            result = self._wait_for_task(task)
            
            if result.success:
                logger.info(f"快照 {snapshot_name} 恢复成功")
            
            return result
            
        except Exception as e:
            logger.error(f"恢复快照失败: {str(e)}")
            return ZMessage(success=False, action="revert_snapshot", 
                          message=f"恢复快照失败: {str(e)}")
    
    def delete_snapshot(self, vm_name: str, snapshot_name: str) -> ZMessage:
        """
        删除快照
        
        :param vm_name: 虚拟机名称
        :param snapshot_name: 快照名称
        :return: 操作结果
        """
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="delete_snapshot", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            # 查找快照
            snapshot = self._find_snapshot(vm.snapshot.rootSnapshotList, snapshot_name)
            if not snapshot:
                return ZMessage(success=False, action="delete_snapshot", 
                              message=f"快照 {snapshot_name} 不存在")
            
            task = snapshot.snapshot.Remove(removeChildren=False)
            result = self._wait_for_task(task)
            
            if result.success:
                logger.info(f"快照 {snapshot_name} 删除成功")
            
            return result
            
        except Exception as e:
            logger.error(f"删除快照失败: {str(e)}")
            return ZMessage(success=False, action="delete_snapshot", 
                          message=f"删除快照失败: {str(e)}")
    
    def _find_snapshot(self, snapshots, snapshot_name: str):
        """递归查找快照"""
        for snapshot in snapshots:
            if snapshot.name == snapshot_name:
                return snapshot
            if hasattr(snapshot, 'childSnapshotList'):
                result = self._find_snapshot(snapshot.childSnapshotList, snapshot_name)
                if result:
                    return result
        return None
    
    def add_disk(self, vm_name: str, size_gb: int, disk_name: str) -> ZMessage:
        """
        添加磁盘
        
        :param vm_name: 虚拟机名称
        :param size_gb: 磁盘大小（GB）
        :param disk_name: 磁盘名称
        :return: 操作结果
        """
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="add_disk", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            # 查找SCSI控制器
            scsi_controller = None
            for device in vm.config.hardware.device:
                if isinstance(device, vim.vm.device.VirtualSCSIController):
                    scsi_controller = device
                    break
            
            if not scsi_controller:
                return ZMessage(success=False, action="add_disk", 
                              message="未找到SCSI控制器")
            
            # 获取下一个可用的单元号
            unit_number = len([d for d in vm.config.hardware.device 
                             if isinstance(d, vim.vm.device.VirtualDisk)])
            
            # 创建磁盘规格
            disk_spec = vim.vm.device.VirtualDeviceSpec()
            disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            disk_spec.fileOperation = vim.vm.device.VirtualDeviceSpec.FileOperation.create
            
            disk = vim.vm.device.VirtualDisk()
            disk.capacityInKB = size_gb * 1024 * 1024
            disk.controllerKey = scsi_controller.key
            disk.unitNumber = unit_number
            
            disk.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
            disk.backing.diskMode = 'persistent'
            disk.backing.fileName = f"[{self.datastore_name}] {vm_name}/{disk_name}.vmdk"
            disk.backing.thinProvisioned = True
            
            disk_spec.device = disk
            
            # 应用配置
            config_spec = vim.vm.ConfigSpec()
            config_spec.deviceChange = [disk_spec]
            
            task = vm.Reconfigure(config_spec)
            result = self._wait_for_task(task)
            
            if result.success:
                logger.info(f"磁盘 {disk_name} 添加成功")
            
            return result
            
        except Exception as e:
            logger.error(f"添加磁盘失败: {str(e)}")
            return ZMessage(success=False, action="add_disk", 
                          message=f"添加磁盘失败: {str(e)}")
    
    def attach_iso(self, vm_name: str, iso_path: str) -> ZMessage:
        """
        挂载ISO
        
        :param vm_name: 虚拟机名称
        :param iso_path: ISO文件路径（数据存储路径格式）
        :return: 操作结果
        """
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="attach_iso", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            # 查找CD/DVD设备
            cdrom = None
            for device in vm.config.hardware.device:
                if isinstance(device, vim.vm.device.VirtualCdrom):
                    cdrom = device
                    break
            
            # 如果没有CD/DVD设备，创建一个
            if not cdrom:
                # 查找IDE控制器
                ide_controller = None
                for device in vm.config.hardware.device:
                    if isinstance(device, vim.vm.device.VirtualIDEController):
                        ide_controller = device
                        break
                
                if not ide_controller:
                    return ZMessage(success=False, action="attach_iso", 
                                  message="未找到IDE控制器")
                
                cdrom_spec = vim.vm.device.VirtualDeviceSpec()
                cdrom_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
                
                cdrom = vim.vm.device.VirtualCdrom()
                cdrom.controllerKey = ide_controller.key
                cdrom.unitNumber = 0
                
                cdrom.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
                cdrom.backing.fileName = iso_path
                
                cdrom.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
                cdrom.connectable.startConnected = True
                cdrom.connectable.allowGuestControl = True
                cdrom.connectable.connected = True
                
                cdrom_spec.device = cdrom
            else:
                # 修改现有CD/DVD设备
                cdrom_spec = vim.vm.device.VirtualDeviceSpec()
                cdrom_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                cdrom_spec.device = cdrom
                
                cdrom.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
                cdrom.backing.fileName = iso_path
                
                cdrom.connectable.startConnected = True
                cdrom.connectable.connected = True
            
            # 应用配置
            config_spec = vim.vm.ConfigSpec()
            config_spec.deviceChange = [cdrom_spec]
            
            task = vm.Reconfigure(config_spec)
            result = self._wait_for_task(task)
            
            if result.success:
                logger.info(f"ISO {iso_path} 挂载成功")
            
            return result
            
        except Exception as e:
            logger.error(f"挂载ISO失败: {str(e)}")
            return ZMessage(success=False, action="attach_iso", 
                          message=f"挂载ISO失败: {str(e)}")
    
    def update_vm_config(self, vm_name: str, vm_conf: VMConfig) -> ZMessage:
        """
        更新虚拟机配置
        
        :param vm_name: 虚拟机名称
        :param vm_conf: 新的虚拟机配置
        :return: 操作结果
        """
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return ZMessage(success=False, action="update_vm_config", 
                              message=f"虚拟机 {vm_name} 不存在")
            
            # 创建配置规格
            config_spec = vim.vm.ConfigSpec()
            config_spec.memoryMB = vm_conf.ram_num
            config_spec.numCPUs = vm_conf.cpu_num
            
            # 应用配置
            task = vm.Reconfigure(config_spec)
            result = self._wait_for_task(task)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 配置更新成功")
            
            return result
            
        except Exception as e:
            logger.error(f"更新虚拟机配置失败: {str(e)}")
            return ZMessage(success=False, action="update_vm_config", 
                          message=f"更新配置失败: {str(e)}")
    
    def _get_guest_id(self, os_name: str) -> str:
        """
        根据操作系统名称获取GuestId
        
        :param os_name: 操作系统名称
        :return: GuestId
        """
        os_lower = os_name.lower()
        
        # Ubuntu/Debian
        if 'ubuntu' in os_lower or 'debian' in os_lower:
            if '64' in os_lower or 'x64' in os_lower or 'amd64' in os_lower:
                return 'ubuntu64Guest'
            return 'ubuntuGuest'
        
        # CentOS/RHEL
        if 'centos' in os_lower or 'rhel' in os_lower or 'redhat' in os_lower:
            if '64' in os_lower or 'x64' in os_lower:
                return 'centos64Guest'
            return 'centosGuest'
        
        # Windows
        if 'windows' in os_lower or 'win' in os_lower:
            if '2019' in os_lower or '2022' in os_lower:
                return 'windows9Server64Guest'
            if '2016' in os_lower:
                return 'windows9Server64Guest'
            if '2012' in os_lower:
                return 'windows8Server64Guest'
            if '10' in os_lower or '11' in os_lower:
                return 'windows9_64Guest'
            if '64' in os_lower or 'x64' in os_lower:
                return 'windows7_64Guest'
            return 'windows7Guest'
        
        # 默认
        return 'otherGuest64'
    
    def get_vm_status(self, vm_name: str) -> Dict[str, Any]:
        """
        获取虚拟机状态
        
        :param vm_name: 虚拟机名称
        :return: 虚拟机状态信息
        """
        try:
            vm = self.get_vm(vm_name)
            if not vm:
                return {}
            
            status = {
                "name": vm.name,
                "power_state": str(vm.runtime.powerState),
                "guest_os": vm.config.guestFullName if vm.config else "Unknown",
                "cpu": vm.config.hardware.numCPU if vm.config else 0,
                "memory_mb": vm.config.hardware.memoryMB if vm.config else 0,
                "ip_address": vm.guest.ipAddress if vm.guest else "",
                "tools_status": str(vm.guest.toolsStatus) if vm.guest else "Unknown",
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取虚拟机状态失败: {str(e)}")
            return {}
    
    def get_host_status(self) -> Dict[str, Any]:
        """
        获取ESXi主机状态
        
        :return: 主机状态信息
        """
        try:
            host = self._get_obj(vim.HostSystem)
            if not host or len(host) == 0:
                return {}
            
            host = host[0]
            
            # CPU信息
            cpu_usage = host.summary.quickStats.overallCpuUsage
            cpu_total = host.summary.hardware.numCpuCores * host.summary.hardware.cpuMhz
            
            # 内存信息
            memory_usage = host.summary.quickStats.overallMemoryUsage
            memory_total = host.summary.hardware.memorySize / (1024 * 1024)
            
            status = {
                "name": host.name,
                "cpu_cores": host.summary.hardware.numCpuCores,
                "cpu_usage_mhz": cpu_usage,
                "cpu_total_mhz": cpu_total,
                "cpu_usage_percent": round((cpu_usage / cpu_total) * 100, 2) if cpu_total > 0 else 0,
                "memory_usage_mb": memory_usage,
                "memory_total_mb": int(memory_total),
                "memory_usage_percent": round((memory_usage / memory_total) * 100, 2) if memory_total > 0 else 0,
                "connection_state": str(host.runtime.connectionState),
                "power_state": str(host.runtime.powerState),
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取主机状态失败: {str(e)}")
            return {}
