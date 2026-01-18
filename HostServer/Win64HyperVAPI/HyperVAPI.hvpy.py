# Hyper-V API 实现 ###########################################################
# 通过hypy库（使用PowerShell接口）管理Hyper-V虚拟机
################################################################################

import os
import subprocess
import json
from typing import Optional, Dict, List, Any
from loguru import logger

try:
    from hypy.modules import hvclient
    HYPY_AVAILABLE = True
except ImportError:
    HYPY_AVAILABLE = False

from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMPowers import VMPowers


# Hyper-V API类 ###############################################################
# 用于管理Hyper-V虚拟机
################################################################################
class HyperVAPI:
    # 初始化Hyper-V API ############################################################
    # :param host: Hyper-V主机地址
    # :param user: 用户名
    # :param password: 密码
    # :param port: WinRM端口（默认5985 HTTP，5986 HTTPS）
    # :param use_ssl: 是否使用SSL
    ################################################################################
    def __init__(self, host: str, user: str = "", password: str = "", port: int = 5985, use_ssl: bool = False):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.is_local = (host in ['localhost', '127.0.0.1', '::1', ''])

        # 配置hypy
        if HYPY_AVAILABLE:
            hvclient.config = {
                'host': host,
                'user': user,
                'pass': password,
                'port': port,
                'use_ssl': use_ssl,
            }

        if not HYPY_AVAILABLE:
            logger.error("hypy库未安装，请运行: pip install hypy")

    # 连接到Hyper-V主机 ############################################################
    def connect(self) -> ZMessage:
        try:
            if not HYPY_AVAILABLE:
                return ZMessage(success=False, action="Connect", message="hypy库未安装，请运行: pip install hypy")

            # 测试连接 - 尝试获取虚拟机列表
            result = hvclient.get_vm(None)
            if result.status_code == 0:
                logger.info(f"成功连接到Hyper-V主机: {self.host}")
                return ZMessage(success=True, action="Connect", message="连接成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"连接Hyper-V主机失败: {error_msg}")
                return ZMessage(success=False, action="Connect", message=f"连接失败: {error_msg}")

        except Exception as e:
            logger.error(f"连接Hyper-V主机失败: {str(e)}")
            return ZMessage(success=False, action="Connect", message=str(e))

    # 断开连接 ####################################################################
    def disconnect(self):
        logger.info("已断开Hyper-V连接")

    # 执行PowerShell命令并解析结果 #################################################
    def _run_ps(self, script: str) -> Optional[Any]:
        try:
            if not HYPY_AVAILABLE:
                return None
            result = hvclient.run_ps(script)
            if result.status_code != 0:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"PowerShell命令执行失败: {error_msg}")
                return None
            if result.std_out:
                return json.loads(result.std_out.decode('latin-1'))
            return None
        except Exception as e:
            logger.error(f"执行PowerShell命令异常: {str(e)}")
            return None

    # 列出所有虚拟机 ###############################################################
    # :param filter_prefix: 名称前缀过滤
    # :return: 虚拟机列表
    ################################################################################
    def list_vms(self, filter_prefix: str = "") -> List[Dict[str, Any]]:
        try:
            result = hvclient.get_vm(None)
            if result.status_code != 0:
                return []

            data = json.loads(result.std_out.decode('latin-1'))
            vm_list = []

            # data可能是列表或单个字典
            vms = data if isinstance(data, list) else [data]

            for vm in vms:
                if not isinstance(vm, dict):
                    continue

                vm_info = {
                    'name': vm.get('Name', ''),
                    'state': vm.get('State', 'Unknown'),
                    'cpu': vm.get('ProcessorCount', 1) if hasattr(vm, 'ProcessorCount') else 1,
                    'memory_mb': 1024,  # hypy的get_vm不返回内存信息，使用默认值
                    'path': ''
                }

                # 过滤
                if filter_prefix:
                    if vm_info['name'].startswith(filter_prefix):
                        vm_list.append(vm_info)
                else:
                    vm_list.append(vm_info)

            return vm_list

        except Exception as e:
            logger.error(f"列出虚拟机失败: {str(e)}")
            return []

    # 获取虚拟机详细信息 ###########################################################
    # :param vm_name: 虚拟机名称
    # :return: 虚拟机信息
    ################################################################################
    def get_vm_info(self, vm_name: str) -> Optional[Dict[str, Any]]:
        try:
            result = hvclient.get_vm(vm_name)
            if result.status_code != 0:
                return None

            data = json.loads(result.std_out.decode('latin-1'))
            vm_data = data if isinstance(data, dict) else (data[0] if isinstance(data, list) and len(data) > 0 else None)

            if vm_data:
                return {
                    'Name': vm_data.get('Name', ''),
                    'State': vm_data.get('State', 'Unknown'),
                    'ProcessorCount': 1,
                    'MemoryStartup': 1073741824,
                    'Path': '',
                    'Id': vm_data.get('Id', ''),
                }
            return None

        except Exception as e:
            logger.error(f"获取虚拟机信息失败: {str(e)}")
            return None

    # 创建虚拟机 ##################################################################
    # :param vm_conf: 虚拟机配置
    # :param hs_config: 主机配置
    # :return: 操作结果
    ################################################################################
    def create_vm(self, vm_conf: VMConfig, hs_config: HSConfig) -> ZMessage:
        try:
            vm_name = vm_conf.vm_uuid
            vm_path = hs_config.system_path

            # 构建PowerShell命令
            ps_script = f"""
            New-VM -Name '{vm_name}' `
                -MemoryStartupBytes {vm_conf.mem_num}MB `
                -Generation 2 `
                -Path '{hs_config.system_path}' `
                -SwitchName 'Default Switch' -ErrorAction SilentlyContinue

            if ($?) {{
                Set-VM -Name '{vm_name}' -ProcessorCount {vm_conf.cpu_num}
            }}
            """

            # 如果有硬盘大小配置，创建虚拟硬盘
            if vm_conf.hdd_num > 0:
                vhd_path = f"{vm_path}\\{vm_name}\\Virtual Hard Disks\\{vm_name}.vhdx"
                ps_script += f"""
                if (-not (Test-Path '{os.path.dirname(vhd_path)}')) {{
                    New-Item -ItemType Directory -Path '{os.path.dirname(vhd_path)}' -Force | Out-Null
                }}
                New-VHD -Path '{vhd_path}' -SizeBytes {vm_conf.hdd_num}GB -Dynamic -ErrorAction SilentlyContinue
                if ($?) {{
                    Add-VMHardDiskDrive -VMName '{vm_name}' -Path '{vhd_path}'
                }}
                """

            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 创建成功")
                return ZMessage(success=True, action="CreateVM", message="虚拟机创建成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"创建虚拟机失败: {error_msg}")
                return ZMessage(success=False, action="CreateVM", message=error_msg)

        except Exception as e:
            logger.error(f"创建虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="CreateVM", message=str(e))

    # 删除虚拟机 ##################################################################
    # :param vm_name: 虚拟机名称
    # :param remove_files: 是否删除文件
    # :return: 操作结果
    ################################################################################
    def delete_vm(self, vm_name: str, remove_files: bool = True) -> ZMessage:
        try:
            # 先停止虚拟机
            result = hvclient.stop_vm(vm_name, force=True)
            if result.status_code != 0 and 'was not found' not in result.std_err.decode('utf-8', errors='replace').lower():
                logger.warning(f"停止虚拟机 {vm_name} 失败，继续删除操作")

            # 删除虚拟机
            ps_script = f"Remove-VM -Name '{vm_name}' -Force"
            if remove_files:
                ps_script += " -DeleteSavedState"

            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 删除成功")
                return ZMessage(success=True, action="DeleteVM", message="虚拟机删除成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"删除虚拟机失败: {error_msg}")
                return ZMessage(success=False, action="DeleteVM", message=error_msg)

        except Exception as e:
            logger.error(f"删除虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="DeleteVM", message=str(e))

    # 启动虚拟机 ##################################################################
    def power_on(self, vm_name: str) -> ZMessage:
        try:
            result = hvclient.start_vm(vm_name)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 已启动")
                return ZMessage(success=True, action="PowerOn", message="虚拟机已启动")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"启动虚拟机失败: {error_msg}")
                return ZMessage(success=False, action="PowerOn", message=error_msg)

        except Exception as e:
            logger.error(f"启动虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="PowerOn", message=str(e))

    # 关闭虚拟机 ##################################################################
    def power_off(self, vm_name: str, force: bool = False) -> ZMessage:
        try:
            result = hvclient.stop_vm(vm_name, force=force)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 已关闭")
                return ZMessage(success=True, action="PowerOff", message="虚拟机已关闭")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"关闭虚拟机失败: {error_msg}")
                return ZMessage(success=False, action="PowerOff", message=error_msg)

        except Exception as e:
            logger.error(f"关闭虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="PowerOff", message=str(e))

    # 暂停虚拟机 ##################################################################
    def suspend(self, vm_name: str) -> ZMessage:
        try:
            ps_script = f"Suspend-VM -Name '{vm_name}'"
            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 已暂停")
                return ZMessage(success=True, action="Suspend", message="虚拟机已暂停")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"暂停虚拟机失败: {error_msg}")
                return ZMessage(success=False, action="Suspend", message=error_msg)

        except Exception as e:
            logger.error(f"暂停虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="Suspend", message=str(e))

    # 恢复虚拟机 ##################################################################
    def resume(self, vm_name: str) -> ZMessage:
        try:
            ps_script = f"Resume-VM -Name '{vm_name}'"
            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 已恢复")
                return ZMessage(success=True, action="Resume", message="虚拟机已恢复")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"恢复虚拟机失败: {error_msg}")
                return ZMessage(success=False, action="Resume", message=error_msg)

        except Exception as e:
            logger.error(f"恢复虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="Resume", message=str(e))

    # 重启虚拟机 ##################################################################
    def reset(self, vm_name: str) -> ZMessage:
        try:
            ps_script = f"Restart-VM -Name '{vm_name}' -Force"
            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 已重启")
                return ZMessage(success=True, action="Reset", message="虚拟机已重启")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"重启虚拟机失败: {error_msg}")
                return ZMessage(success=False, action="Reset", message=error_msg)

        except Exception as e:
            logger.error(f"重启虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="Reset", message=str(e))

    # 更新虚拟机配置 ###############################################################
    # :param vm_name: 虚拟机名称
    # :param vm_conf: 新配置
    # :return: 操作结果
    ################################################################################
    def update_vm_config(self, vm_name: str, vm_conf: VMConfig) -> ZMessage:
        try:
            ps_script = f"""
            Set-VM -Name '{vm_name}' `
                -ProcessorCount {vm_conf.cpu_num} `
                -MemoryStartupBytes {vm_conf.mem_num}MB
            """
            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 配置已更新")
                return ZMessage(success=True, action="UpdateConfig", message="配置更新成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"更新虚拟机配置失败: {error_msg}")
                return ZMessage(success=False, action="UpdateConfig", message=error_msg)

        except Exception as e:
            logger.error(f"更新虚拟机配置失败: {str(e)}")
            return ZMessage(success=False, action="UpdateConfig", message=str(e))

    # 创建快照 ####################################################################
    def create_snapshot(self, vm_name: str, snapshot_name: str, description: str = "") -> ZMessage:
        try:
            result = hvclient.create_vm_snapshot(vm_name, snapshot_name)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 快照 {snapshot_name} 创建成功")
                return ZMessage(success=True, action="CreateSnapshot", message="快照创建成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"创建快照失败: {error_msg}")
                return ZMessage(success=False, action="CreateSnapshot", message=error_msg)

        except Exception as e:
            logger.error(f"创建快照失败: {str(e)}")
            return ZMessage(success=False, action="CreateSnapshot", message=str(e))

    # 恢复快照 ####################################################################
    def revert_snapshot(self, vm_name: str, snapshot_name: str) -> ZMessage:
        try:
            # 获取恢复前的虚拟机状态
            vm_info = self.get_vm_info(vm_name)
            was_running = vm_info and vm_info.get('State') == 'Running' if vm_info else False

            # 恢复快照
            result = hvclient.restore_vm_snap(vm_name, snapshot_name)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 已恢复到快照 {snapshot_name}")

                # 如果恢复前是运行状态，则自动开机
                if was_running:
                    logger.info(f"检测到恢复前虚拟机 {vm_name} 为运行状态，正在自动开机...")
                    import time
                    time.sleep(2)

                    power_on_result = self.power_on(vm_name)
                    if power_on_result.success:
                        logger.info(f"虚拟机 {vm_name} 已自动开机")
                        return ZMessage(success=True, action="RevertSnapshot",
                                      message="快照恢复成功，虚拟机已自动开机")
                    else:
                        logger.warning(f"虚拟机 {vm_name} 自动开机失败: {power_on_result.message}")
                        return ZMessage(success=True, action="RevertSnapshot",
                                      message=f"快照恢复成功，但自动开机失败: {power_on_result.message}")

                return ZMessage(success=True, action="RevertSnapshot", message="快照恢复成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"恢复快照失败: {error_msg}")
                return ZMessage(success=False, action="RevertSnapshot", message=error_msg)

        except Exception as e:
            logger.error(f"恢复快照失败: {str(e)}")
            return ZMessage(success=False, action="RevertSnapshot", message=str(e))

    # 删除快照 ####################################################################
    def delete_snapshot(self, vm_name: str, snapshot_name: str) -> ZMessage:
        try:
            result = hvclient.remove_vm_snapshot(vm_name, snapshot_name)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 快照 {snapshot_name} 已删除")
                return ZMessage(success=True, action="DeleteSnapshot", message="快照删除成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"删除快照失败: {error_msg}")
                return ZMessage(success=False, action="DeleteSnapshot", message=error_msg)

        except Exception as e:
            logger.error(f"删除快照失败: {str(e)}")
            return ZMessage(success=False, action="DeleteSnapshot", message=str(e))

    # 添加虚拟硬盘 #################################################################
    def add_disk(self, vm_name: str, size_gb: int, disk_name: str) -> ZMessage:
        try:
            vm_info = self.get_vm_info(vm_name)
            if not vm_info:
                return ZMessage(success=False, action="AddDisk", message="无法获取虚拟机信息")

            vm_path = vm_info.get('Path', '')
            vhd_path = os.path.join(vm_path, "Virtual Hard Disks", f"{disk_name}.vhdx")

            ps_script = f"""
            if (-not (Test-Path '{os.path.dirname(vhd_path)}')) {{
                New-Item -ItemType Directory -Path '{os.path.dirname(vhd_path)}' -Force | Out-Null
            }}
            New-VHD -Path '{vhd_path}' -SizeBytes {size_gb}GB -Dynamic
            Add-VMHardDiskDrive -VMName '{vm_name}' -Path '{vhd_path}'
            """

            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 添加磁盘 {disk_name} 成功")
                return ZMessage(success=True, action="AddDisk", message="磁盘添加成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"添加磁盘失败: {error_msg}")
                return ZMessage(success=False, action="AddDisk", message=error_msg)

        except Exception as e:
            logger.error(f"添加磁盘失败: {str(e)}")
            return ZMessage(success=False, action="AddDisk", message=str(e))

    # 挂载ISO #####################################################################
    def attach_iso(self, vm_name: str, iso_path: str) -> ZMessage:
        try:
            ps_script = f"Add-VMDvdDrive -VMName '{vm_name}' -Path '{iso_path}'"
            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} ISO挂载成功")
                return ZMessage(success=True, action="AttachISO", message="ISO挂载成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"挂载ISO失败: {error_msg}")
                return ZMessage(success=False, action="AttachISO", message=error_msg)

        except Exception as e:
            logger.error(f"挂载ISO失败: {str(e)}")
            return ZMessage(success=False, action="AttachISO", message=str(e))

    # 卸载ISO #####################################################################
    def detach_iso(self, vm_name: str) -> ZMessage:
        try:
            ps_script = f"Get-VMDvdDrive -VMName '{vm_name}' | Remove-VMDvdDrive"
            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} ISO卸载成功")
                return ZMessage(success=True, action="DetachISO", message="ISO卸载成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"卸载ISO失败: {error_msg}")
                return ZMessage(success=False, action="DetachISO", message=error_msg)

        except Exception as e:
            logger.error(f"卸载ISO失败: {str(e)}")
            return ZMessage(success=False, action="DetachISO", message=str(e))

    # 获取VNC端口 ##################################################################
    # Hyper-V使用增强会话模式，不是传统VNC
    # :param vm_name: 虚拟机名称
    # :return: 端口号
    ################################################################################
    def get_vnc_port(self, vm_name: str) -> Optional[int]:
        logger.warning("Hyper-V不支持VNC，请使用增强会话模式或RDP")
        return None

    # 设置网络适配器 ###############################################################
    # :param vm_name: 虚拟机名称
    # :param switch_name: 虚拟交换机名称
    # :param mac_address: MAC地址（可选）
    # :return: 操作结果
    ################################################################################
    def set_network_adapter(self, vm_name: str, switch_name: str, mac_address: str = None) -> ZMessage:
        try:
            ps_script = f"Get-VMNetworkAdapter -VMName '{vm_name}' | Connect-VMNetworkAdapter -SwitchName '{switch_name}'"
            if mac_address:
                ps_script += f"\nSet-VMNetworkAdapter -VMName '{vm_name}' -StaticMacAddress '{mac_address}'"

            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                logger.info(f"虚拟机 {vm_name} 网络适配器配置成功")
                return ZMessage(success=True, action="SetNetwork", message="网络配置成功")
            else:
                error_msg = result.std_err.decode('utf-8', errors='replace') if result.std_err else "未知错误"
                logger.error(f"配置网络适配器失败: {error_msg}")
                return ZMessage(success=False, action="SetNetwork", message=error_msg)

        except Exception as e:
            logger.error(f"配置网络适配器失败: {str(e)}")
            return ZMessage(success=False, action="SetNetwork", message=str(e))

    # 获取主机状态 #################################################################
    def get_host_status(self) -> Optional[Dict[str, Any]]:
        try:
            ps_script = """
            $host_info = Get-VMHost
            $cpu = Get-Counter '\\Processor(_Total)\\% Processor Time' | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue
            $mem = Get-Counter '\\Memory\\% Committed Bytes In Use' | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue

            @{
                cpu_usage_percent = [math]::Round($cpu, 2)
                memory_usage_percent = [math]::Round($mem, 2)
            } | ConvertTo-Json
            """

            result = hvclient.run_ps(ps_script)
            if result.status_code == 0:
                try:
                    return json.loads(result.std_out.decode('latin-1'))
                except json.JSONDecodeError:
                    pass
            return None

        except Exception as e:
            logger.error(f"获取主机状态失败: {str(e)}")
            return None
