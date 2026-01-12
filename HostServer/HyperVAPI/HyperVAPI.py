"""
Hyper-V API 实现
通过PowerShell和WinRM远程管理Hyper-V虚拟机
"""

import json
import subprocess
import winrm
from typing import Optional, Dict, List, Any
from loguru import logger

from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMPowers import VMPowers


class HyperVAPI:
    """Hyper-V API类，用于管理Hyper-V虚拟机"""
    
    def __init__(self, host: str, user: str, password: str, port: int = 5985, use_ssl: bool = False):
        """
        初始化Hyper-V API
        
        :param host: Hyper-V主机地址
        :param user: 用户名
        :param password: 密码
        :param port: WinRM端口（默认5985 HTTP，5986 HTTPS）
        :param use_ssl: 是否使用SSL
        """
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.session: Optional[winrm.Session] = None
        self.is_local = (host in ['localhost', '127.0.0.1', '::1'])
        
    def connect(self) -> ZMessage:
        """连接到Hyper-V主机"""
        try:
            if self.is_local:
                # 本地连接，不需要WinRM
                logger.info("使用本地PowerShell连接")
                return ZMessage(success=True, action="Connect", message="本地连接成功")
            
            # 远程连接使用WinRM
            protocol = 'https' if self.use_ssl else 'http'
            endpoint = f"{protocol}://{self.host}:{self.port}/wsman"
            
            self.session = winrm.Session(
                endpoint,
                auth=(self.user, self.password),
                transport='ntlm',
                server_cert_validation='ignore' if self.use_ssl else None
            )
            
            # 测试连接
            result = self._run_powershell("Get-VMHost")
            if result.success:
                logger.info(f"成功连接到Hyper-V主机: {self.host}")
                return ZMessage(success=True, action="Connect", message="连接成功")
            else:
                return ZMessage(success=False, action="Connect", message=f"连接失败: {result.message}")
                
        except Exception as e:
            logger.error(f"连接Hyper-V主机失败: {str(e)}")
            return ZMessage(success=False, action="Connect", message=str(e))
    
    def disconnect(self):
        """断开连接"""
        self.session = None
        logger.info("已断开Hyper-V连接")
    
    def _run_powershell(self, command: str, parse_json: bool = False) -> ZMessage:
        """
        执行PowerShell命令
        
        :param command: PowerShell命令
        :param parse_json: 是否解析JSON输出
        :return: 执行结果
        """
        try:
            if self.is_local:
                # 本地执行
                result = subprocess.run(
                    ['powershell', '-Command', command],
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    if parse_json and output:
                        try:
                            data = json.loads(output)
                            return ZMessage(success=True, action="PowerShell", results=data)
                        except json.JSONDecodeError:
                            return ZMessage(success=True, action="PowerShell", message=output)
                    return ZMessage(success=True, action="PowerShell", message=output)
                else:
                    error = result.stderr.strip()
                    logger.error(f"PowerShell命令执行失败: {error}")
                    return ZMessage(success=False, action="PowerShell", message=error)
            else:
                # 远程执行
                if not self.session:
                    return ZMessage(success=False, action="PowerShell", message="未连接到远程主机")
                
                result = self.session.run_ps(command)
                
                if result.status_code == 0:
                    output = result.std_out.decode('utf-8').strip()
                    if parse_json and output:
                        try:
                            data = json.loads(output)
                            return ZMessage(success=True, action="PowerShell", results=data)
                        except json.JSONDecodeError:
                            return ZMessage(success=True, action="PowerShell", message=output)
                    return ZMessage(success=True, action="PowerShell", message=output)
                else:
                    error = result.std_err.decode('utf-8').strip()
                    logger.error(f"PowerShell命令执行失败: {error}")
                    return ZMessage(success=False, action="PowerShell", message=error)
                    
        except Exception as e:
            logger.error(f"执行PowerShell命令异常: {str(e)}")
            return ZMessage(success=False, action="PowerShell", message=str(e))
    
    def list_vms(self, filter_prefix: str = "") -> List[Dict[str, Any]]:
        """
        列出所有虚拟机
        
        :param filter_prefix: 名称前缀过滤
        :return: 虚拟机列表
        """
        try:
            command = "Get-VM | Select-Object Name, State, ProcessorCount, MemoryStartup, Path | ConvertTo-Json"
            result = self._run_powershell(command, parse_json=True)
            
            if not result.success:
                return []
            
            vms = result.results if isinstance(result.results, list) else [result.results]
            
            # 过滤
            if filter_prefix:
                vms = [vm for vm in vms if vm.get('Name', '').startswith(filter_prefix)]
            
            # 转换格式
            vm_list = []
            for vm in vms:
                vm_list.append({
                    'name': vm.get('Name', ''),
                    'state': vm.get('State', 'Unknown'),
                    'cpu': vm.get('ProcessorCount', 1),
                    'memory_mb': vm.get('MemoryStartup', 0) // (1024 * 1024),
                    'path': vm.get('Path', '')
                })
            
            return vm_list
            
        except Exception as e:
            logger.error(f"列出虚拟机失败: {str(e)}")
            return []
    
    def get_vm_info(self, vm_name: str) -> Optional[Dict[str, Any]]:
        """
        获取虚拟机详细信息
        
        :param vm_name: 虚拟机名称
        :return: 虚拟机信息
        """
        try:
            command = f"Get-VM -Name '{vm_name}' | Select-Object * | ConvertTo-Json"
            result = self._run_powershell(command, parse_json=True)
            
            if result.success:
                return result.results
            return None
            
        except Exception as e:
            logger.error(f"获取虚拟机信息失败: {str(e)}")
            return None
    
    def create_vm(self, vm_conf: VMConfig, hs_config: HSConfig) -> ZMessage:
        """
        创建虚拟机
        
        :param vm_conf: 虚拟机配置
        :param hs_config: 主机配置
        :return: 操作结果
        """
        try:
            vm_name = vm_conf.vm_uuid
            vm_path = f"{hs_config.system_path}\\{vm_name}"
            
            # 构建创建命令
            command = f"""
            New-VM -Name '{vm_name}' `
                -MemoryStartupBytes {vm_conf.ram_num}MB `
                -Generation 2 `
                -Path '{hs_config.system_path}' `
                -SwitchName 'Default Switch'
            
            Set-VM -Name '{vm_name}' -ProcessorCount {vm_conf.cpu_num}
            """
            
            # 如果有硬盘大小配置，创建虚拟硬盘
            if vm_conf.hdd_num > 0:
                vhd_path = f"{vm_path}\\Virtual Hard Disks\\{vm_name}.vhdx"
                command += f"""
                New-VHD -Path '{vhd_path}' -SizeBytes {vm_conf.hdd_num}GB -Dynamic
                Add-VMHardDiskDrive -VMName '{vm_name}' -Path '{vhd_path}'
                """
            
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 创建成功")
                return ZMessage(success=True, action="CreateVM", message="虚拟机创建成功")
            else:
                return ZMessage(success=False, action="CreateVM", message=result.message)
                
        except Exception as e:
            logger.error(f"创建虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="CreateVM", message=str(e))
    
    def delete_vm(self, vm_name: str, remove_files: bool = True) -> ZMessage:
        """
        删除虚拟机
        
        :param vm_name: 虚拟机名称
        :param remove_files: 是否删除文件
        :return: 操作结果
        """
        try:
            # 先停止虚拟机
            self.power_off(vm_name, force=True)
            
            # 删除虚拟机
            if remove_files:
                command = f"Remove-VM -Name '{vm_name}' -Force"
            else:
                command = f"Remove-VM -Name '{vm_name}' -Force"
            
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 删除成功")
                return ZMessage(success=True, action="DeleteVM", message="虚拟机删除成功")
            else:
                return ZMessage(success=False, action="DeleteVM", message=result.message)
                
        except Exception as e:
            logger.error(f"删除虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="DeleteVM", message=str(e))
    
    def power_on(self, vm_name: str) -> ZMessage:
        """启动虚拟机"""
        try:
            command = f"Start-VM -Name '{vm_name}'"
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 已启动")
                return ZMessage(success=True, action="PowerOn", message="虚拟机已启动")
            else:
                return ZMessage(success=False, action="PowerOn", message=result.message)
                
        except Exception as e:
            logger.error(f"启动虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="PowerOn", message=str(e))
    
    def power_off(self, vm_name: str, force: bool = False) -> ZMessage:
        """关闭虚拟机"""
        try:
            if force:
                command = f"Stop-VM -Name '{vm_name}' -Force"
            else:
                command = f"Stop-VM -Name '{vm_name}'"
            
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 已关闭")
                return ZMessage(success=True, action="PowerOff", message="虚拟机已关闭")
            else:
                return ZMessage(success=False, action="PowerOff", message=result.message)
                
        except Exception as e:
            logger.error(f"关闭虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="PowerOff", message=str(e))
    
    def suspend(self, vm_name: str) -> ZMessage:
        """暂停虚拟机"""
        try:
            command = f"Suspend-VM -Name '{vm_name}'"
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 已暂停")
                return ZMessage(success=True, action="Suspend", message="虚拟机已暂停")
            else:
                return ZMessage(success=False, action="Suspend", message=result.message)
                
        except Exception as e:
            logger.error(f"暂停虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="Suspend", message=str(e))
    
    def resume(self, vm_name: str) -> ZMessage:
        """恢复虚拟机"""
        try:
            command = f"Resume-VM -Name '{vm_name}'"
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 已恢复")
                return ZMessage(success=True, action="Resume", message="虚拟机已恢复")
            else:
                return ZMessage(success=False, action="Resume", message=result.message)
                
        except Exception as e:
            logger.error(f"恢复虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="Resume", message=str(e))
    
    def reset(self, vm_name: str) -> ZMessage:
        """重启虚拟机"""
        try:
            command = f"Restart-VM -Name '{vm_name}' -Force"
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 已重启")
                return ZMessage(success=True, action="Reset", message="虚拟机已重启")
            else:
                return ZMessage(success=False, action="Reset", message=result.message)
                
        except Exception as e:
            logger.error(f"重启虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="Reset", message=str(e))
    
    def update_vm_config(self, vm_name: str, vm_conf: VMConfig) -> ZMessage:
        """
        更新虚拟机配置
        
        :param vm_name: 虚拟机名称
        :param vm_conf: 新配置
        :return: 操作结果
        """
        try:
            command = f"""
            Set-VM -Name '{vm_name}' `
                -ProcessorCount {vm_conf.cpu_num} `
                -MemoryStartupBytes {vm_conf.ram_num}MB
            """
            
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 配置已更新")
                return ZMessage(success=True, action="UpdateConfig", message="配置更新成功")
            else:
                return ZMessage(success=False, action="UpdateConfig", message=result.message)
                
        except Exception as e:
            logger.error(f"更新虚拟机配置失败: {str(e)}")
            return ZMessage(success=False, action="UpdateConfig", message=str(e))
    
    def create_snapshot(self, vm_name: str, snapshot_name: str, description: str = "") -> ZMessage:
        """创建快照"""
        try:
            command = f"Checkpoint-VM -Name '{vm_name}' -SnapshotName '{snapshot_name}'"
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 快照 {snapshot_name} 创建成功")
                return ZMessage(success=True, action="CreateSnapshot", message="快照创建成功")
            else:
                return ZMessage(success=False, action="CreateSnapshot", message=result.message)
                
        except Exception as e:
            logger.error(f"创建快照失败: {str(e)}")
            return ZMessage(success=False, action="CreateSnapshot", message=str(e))
    
    def revert_snapshot(self, vm_name: str, snapshot_name: str) -> ZMessage:
        """恢复快照"""
        try:
            command = f"Restore-VMSnapshot -Name '{snapshot_name}' -VMName '{vm_name}' -Confirm:$false"
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 已恢复到快照 {snapshot_name}")
                return ZMessage(success=True, action="RevertSnapshot", message="快照恢复成功")
            else:
                return ZMessage(success=False, action="RevertSnapshot", message=result.message)
                
        except Exception as e:
            logger.error(f"恢复快照失败: {str(e)}")
            return ZMessage(success=False, action="RevertSnapshot", message=str(e))
    
    def delete_snapshot(self, vm_name: str, snapshot_name: str) -> ZMessage:
        """删除快照"""
        try:
            command = f"Remove-VMSnapshot -VMName '{vm_name}' -Name '{snapshot_name}' -Confirm:$false"
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 快照 {snapshot_name} 已删除")
                return ZMessage(success=True, action="DeleteSnapshot", message="快照删除成功")
            else:
                return ZMessage(success=False, action="DeleteSnapshot", message=result.message)
                
        except Exception as e:
            logger.error(f"删除快照失败: {str(e)}")
            return ZMessage(success=False, action="DeleteSnapshot", message=str(e))
    
    def add_disk(self, vm_name: str, size_gb: int, disk_name: str) -> ZMessage:
        """添加虚拟硬盘"""
        try:
            # 获取虚拟机路径
            vm_info = self.get_vm_info(vm_name)
            if not vm_info:
                return ZMessage(success=False, action="AddDisk", message="无法获取虚拟机信息")
            
            vm_path = vm_info.get('Path', '')
            vhd_path = f"{vm_path}\\Virtual Hard Disks\\{disk_name}.vhdx"
            
            command = f"""
            New-VHD -Path '{vhd_path}' -SizeBytes {size_gb}GB -Dynamic
            Add-VMHardDiskDrive -VMName '{vm_name}' -Path '{vhd_path}'
            """
            
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 添加磁盘 {disk_name} 成功")
                return ZMessage(success=True, action="AddDisk", message="磁盘添加成功")
            else:
                return ZMessage(success=False, action="AddDisk", message=result.message)
                
        except Exception as e:
            logger.error(f"添加磁盘失败: {str(e)}")
            return ZMessage(success=False, action="AddDisk", message=str(e))
    
    def attach_iso(self, vm_name: str, iso_path: str) -> ZMessage:
        """挂载ISO"""
        try:
            command = f"Add-VMDvdDrive -VMName '{vm_name}' -Path '{iso_path}'"
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} ISO挂载成功")
                return ZMessage(success=True, action="AttachISO", message="ISO挂载成功")
            else:
                return ZMessage(success=False, action="AttachISO", message=result.message)
                
        except Exception as e:
            logger.error(f"挂载ISO失败: {str(e)}")
            return ZMessage(success=False, action="AttachISO", message=str(e))
    
    def detach_iso(self, vm_name: str) -> ZMessage:
        """卸载ISO"""
        try:
            command = f"Get-VMDvdDrive -VMName '{vm_name}' | Remove-VMDvdDrive"
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} ISO卸载成功")
                return ZMessage(success=True, action="DetachISO", message="ISO卸载成功")
            else:
                return ZMessage(success=False, action="DetachISO", message=result.message)
                
        except Exception as e:
            logger.error(f"卸载ISO失败: {str(e)}")
            return ZMessage(success=False, action="DetachISO", message=str(e))
    
    def get_vnc_port(self, vm_name: str) -> Optional[int]:
        """
        获取VNC端口（Hyper-V使用增强会话模式，不是传统VNC）
        
        :param vm_name: 虚拟机名称
        :return: 端口号
        """
        # Hyper-V不使用VNC，而是使用增强会话模式或RDP
        # 这里返回None，表示不支持VNC
        logger.warning("Hyper-V不支持VNC，请使用增强会话模式或RDP")
        return None
    
    def set_network_adapter(self, vm_name: str, switch_name: str, mac_address: str = None) -> ZMessage:
        """
        设置网络适配器
        
        :param vm_name: 虚拟机名称
        :param switch_name: 虚拟交换机名称
        :param mac_address: MAC地址（可选）
        :return: 操作结果
        """
        try:
            command = f"Get-VMNetworkAdapter -VMName '{vm_name}' | Connect-VMNetworkAdapter -SwitchName '{switch_name}'"
            
            if mac_address:
                command += f"\nSet-VMNetworkAdapter -VMName '{vm_name}' -StaticMacAddress '{mac_address}'"
            
            result = self._run_powershell(command)
            
            if result.success:
                logger.info(f"虚拟机 {vm_name} 网络适配器配置成功")
                return ZMessage(success=True, action="SetNetwork", message="网络配置成功")
            else:
                return ZMessage(success=False, action="SetNetwork", message=result.message)
                
        except Exception as e:
            logger.error(f"配置网络适配器失败: {str(e)}")
            return ZMessage(success=False, action="SetNetwork", message=str(e))
    
    def get_host_status(self) -> Optional[Dict[str, Any]]:
        """获取主机状态"""
        try:
            command = """
            $host_info = Get-VMHost
            $cpu = Get-Counter '\\Processor(_Total)\\% Processor Time' | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue
            $mem = Get-Counter '\\Memory\\% Committed Bytes In Use' | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue
            
            @{
                cpu_usage_percent = [math]::Round($cpu, 2)
                memory_usage_percent = [math]::Round($mem, 2)
            } | ConvertTo-Json
            """
            
            result = self._run_powershell(command, parse_json=True)
            
            if result.success:
                return result.results
            return None
            
        except Exception as e:
            logger.error(f"获取主机状态失败: {str(e)}")
            return None
