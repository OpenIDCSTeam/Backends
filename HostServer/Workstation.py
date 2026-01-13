# Workstation - VMware Workstation虚拟化平台管理 ##################################
# 提供VMware Workstation虚拟机的创建、管理和监控功能
################################################################################
import os
import shutil
import subprocess

from HostServer.BasicServer import BasicServer
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.IMConfig import IMConfig
from MainObject.Config.SDConfig import SDConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from HostServer.WorkstationAPI.VMWRestAPI import VRestAPI
from VNCConsole.VNCManager import VNCStart, VProcess


class HostServer(BasicServer):
    # 宿主机服务 ###############################################################
    def __init__(self, config: HSConfig, **kwargs):
        super().__init__(config, **kwargs)  # 传递 kwargs，确保 db 参数能正确传递
        super().__load__(**kwargs)
        self.vmrest_pid = None
        self.vmrest_api = VRestAPI(
            self.hs_config.server_addr,
            self.hs_config.server_user,
            self.hs_config.server_pass,
            self.hs_config.launch_path,
        )

    def VMLoader(self) -> bool:
        cfg_name = "vnc_" + self.hs_config.server_name
        cfg_full = "DataSaving/" + cfg_name + ".cfg"
        if os.path.exists(cfg_full):
            os.remove(cfg_full)
        tp_remote = VNCStart(self.hs_config.remote_port, cfg_name)
        self.vm_remote = VProcess(tp_remote)
        self.vm_remote.start()
        return True

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
        # 启动VM Rest Server
        vmrest_path = os.path.join(
            self.hs_config.launch_path, "vmrest.exe")
        # 检查文件是否存在 ================================================
        if not os.path.exists(vmrest_path):
            return ZMessage(success=False, action="HSLoader",
                            message=f"vmrest.exe not found")
        # 配置后台运行隐藏窗口 ============================================
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        # 启动进程 ========================================================
        self.vmrest_pid = subprocess.Popen(
            [vmrest_path],
            cwd=self.hs_config.launch_path,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW)
        # 通用操作 =============================================================
        return super().HSLoader()

    # 卸载宿主机 ###############################################################
    def HSUnload(self) -> ZMessage:
        # 专用操作 =============================================================
        if self.vmrest_pid is None:  # VM Rest Server未启动 ================
            return ZMessage(
                success=False, action="HSUnload",
                message="VM Rest Server is not running", )
        try:
            self.vmrest_pid.terminate()  # 尝试正常终止
            self.vmrest_pid.wait(timeout=5)  # 等待最多5秒
        except subprocess.TimeoutExpired:
            self.vmrest_pid.kill()  # 强制终止
        finally:
            self.vmrest_pid = None
        # 通用操作 =============================================================
        return super().HSUnload()

    # 虚拟机列出 ###############################################################
    def VMStatus(self, vm_name: str = "") -> dict[str, list[HWStatus]]:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().VMStatus(vm_name)

    # 虚拟机扫描 ###############################################################
    def VMDetect(self) -> ZMessage:
        try:
            # 使用主机配置的filter_name作为前缀过滤
            filter_prefix = self.hs_config.filter_name if self.hs_config else ""

            # 获取所有虚拟机列表
            vms_result = self.vmrest_api.return_vmx()
            if not vms_result.success:
                return ZMessage(
                    success=False, action="VScanner",
                    message=f"Failed to get VM list: {vms_result.message}")

            vms_list = vms_result.results \
                if isinstance(vms_result.results, list) else []
            scanned_count = 0  # 符合过滤条件的虚拟机数量
            added_count = 0  # 新增的虚拟机数量
            # 处理每个虚拟机
            for vm_info in vms_list:
                vm_path = vm_info.get("path", "")
                vm_id = vm_info.get("id", "")
                if not vm_path:
                    continue
                # 从路径中提取虚拟机名称
                vmx_name = os.path.splitext(os.path.basename(vm_path))[0]
                # 前缀过滤（使用主机配置的filter_name）
                if filter_prefix and not vmx_name.startswith(filter_prefix):
                    continue
                # 符合过滤条件的虚拟机计数
                scanned_count += 1
                # 检查是否已存在
                if vmx_name in self.vm_saving:
                    continue
                # 创建默认虚拟机配置
                default_vm_config = VMConfig()
                # 添加到服务器的虚拟机配置中
                self.vm_saving[vmx_name] = default_vm_config
                added_count += 1
                # 记录日志
                log_msg = ZMessage(
                    success=True,
                    action="VScanner",
                    message=f"发现并添加虚拟机: {vmx_name}",
                    results={
                        "vm_name": vmx_name,
                        "vm_id": vm_id,
                        "vm_path": vm_path}
                )
                self.LogStack(log_msg)

            # 保存到数据库
            if added_count > 0:
                success = self.data_set()
                if not success:
                    return ZMessage(
                        success=False, action="VScanner",
                        message="Failed to save scanned VMs to database")
            # 返回成功消息 =====================================================
            return ZMessage(
                success=True,
                action="VScanner",
                message=f"扫描完成。"
                        f"共扫描到{scanned_count}台虚拟机，"
                        f"新增{added_count}台虚拟机配置。",
                results={
                    "scanned": scanned_count,
                    "added": added_count,
                    "prefix_filter": filter_prefix
                }
            )

        except Exception as e:
            return ZMessage(success=False, action="VScanner",
                            message=f"扫描虚拟机时出错: {str(e)}")

    # 创建虚拟机 ###############################################################
    def VMCreate(self, vm_conf: VMConfig) -> ZMessage:
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.NCCreate(vm_conf, True)
        # 专用操作 =============================================================
        try:
            # 路径处理 =========================================================
            vm_path = os.path.join(self.hs_config.system_path, vm_conf.vm_uuid)
            os.mkdir(vm_path) if not os.path.exists(vm_path) else None
            # VM文件名 =========================================================
            vm_file = os.path.join(vm_path, vm_conf.vm_uuid)  # 不含后缀.VMX名称
            # VM配置 ===========================================================
            vm_text = self.vmrest_api.create_vmx(vm_conf, self.hs_config)
            with open(os.path.join(vm_file + ".vmx"), "w") as vm_save_file:
                vm_save_file.write(vm_text)
            # 安装系统 =========================================================
            # results = self.VInstall(vm_conf.os_name, vm_file, vm_conf.hdd_num)
            results = self.VMSetups(vm_conf)
            if not results.success:
                raise Exception(f"安装系统失败: {results.message}")
            # 注册机器 =========================================================
            register_result = self.vmrest_api.loader_vmx(vm_file + ".vmx")
            if not register_result.success:
                raise Exception(f"注册虚拟机失败: {register_result.message}")
            self.VMPowers(vm_conf.vm_uuid, VMPowers.S_START)
        except Exception as e:  # 创建失败时清理已创建的文件 ===================
            vm_path = os.path.join(self.hs_config.system_path, vm_conf.vm_uuid)
            if os.path.exists(vm_path):
                shutil.rmtree(vm_path)
            # 返回错误信息 =====================================================
            hs_result = ZMessage(
                success=False, action="VMCreate",
                message=f"虚拟机创建失败: {str(e)}")
            # 保存到数据库 =====================================================
            self.logs_set(hs_result)
            return hs_result
        # 通用操作 =============================================================
        return super().VMCreate(vm_conf)

    # 安装虚拟机 ###############################################################
    def VMSetups(self, vm_conf: VMConfig) -> ZMessage:
        # 复制镜像 =============================================================
        vm_tail = vm_conf.os_name.split(".")[-1]
        im_file = os.path.join(self.hs_config.images_path, vm_conf.os_name)
        vm_file = os.path.join(self.hs_config.system_path, vm_conf.vm_uuid)
        vm_file = os.path.join(vm_file, vm_conf.vm_uuid + "." + vm_tail)
        if os.path.exists(vm_file):
            os.remove(vm_file)
        shutil.copy(im_file, vm_file)
        # 拓展硬盘 =============================================================
        return self.vmrest_api.extend_hdd(vm_file, vm_conf.hdd_num)
        # 通用操作 =============================================================

    # 配置虚拟机 ###############################################################
    def VMUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.NCCreate(vm_conf, True)
        # 专用操作 =============================================================
        vm_saving = os.path.join(self.hs_config.system_path, vm_conf.vm_uuid)
        vm_locker = os.path.join(vm_saving, vm_conf.vm_uuid + ".vmx.lck")
        if os.path.exists(vm_locker):
            shutil.rmtree(vm_locker)
        # 检查虚拟机是否存在 ===================================================
        if vm_conf.vm_uuid not in self.vm_saving:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机 {vm_conf.vm_uuid} 不存在")
        # 更新虚拟机配置存储 ===================================================
        self.vm_saving[vm_conf.vm_uuid] = vm_conf
        vm_path = os.path.join(vm_saving, vm_conf.vm_uuid)
        # 关闭虚拟机 ===========================================================
        self.VMPowers(vm_conf.vm_uuid, VMPowers.H_CLOSE)
        # 重装系统 =============================================================
        if vm_conf.os_name != vm_last.os_name and vm_last.os_name != "":
            self.VMSetups(vm_conf)
        # 更新硬盘 =============================================================
        if vm_conf.hdd_num > vm_last.hdd_num:
            disk_file = f"{vm_path}.{vm_conf.os_name.split('.')[-1]}"
            back_data = self.vmrest_api.extend_hdd(
                disk_file, vm_conf.hdd_num)
        # 更新网卡 =============================================================
        network_result = self.NCUpdate(vm_conf, vm_last)
        if not network_result.success:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机 {vm_conf.vm_uuid} "
                        f"网络配置更新失败: {network_result.message}")
        # 读取现有VMX ==========================================================
        vm_save_name = os.path.join(vm_saving, vm_conf.vm_uuid + ".vmx")
        if os.path.exists(vm_save_name):
            with open(vm_save_name, "r", encoding="utf-8") as vm_file:
                existing_vmx_content = vm_file.read()
                vm_text = self.vmrest_api.update_vmx(
                    existing_vmx_content, vm_conf, self.hs_config)
        else:  # 如果文件不存在重新创建 ========================================
            vm_text = self.vmrest_api.create_vmx(vm_conf, self.hs_config)
        # 写入VMX文件 ==========================================================
        try:
            with open(vm_save_name, "w", encoding="utf-8") as vm_save_file:
                vm_save_file.write(vm_text)
        except Exception as e:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机 {vm_conf.vm_uuid} VMX文件写入失败: {e}")
        # 启动虚拟机 ===========================================================
        start_result = self.VMPowers(vm_conf.vm_uuid, VMPowers.S_START)
        if not start_result.success:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机 {vm_conf.vm_uuid} "
                        f"启动失败: {start_result.message}")
        # 通用操作 =============================================================
        return super().VMUpdate(vm_conf, vm_last)

    # 删除虚拟机 ###############################################################
    def VMDelete(self, vm_name: str) -> ZMessage:
        # 专用操作 =============================================================
        vm_conf = self.VMSelect(vm_name)
        if vm_conf is None:
            return ZMessage(
                success=False,
                action="VMDelete",
                messages=f"虚拟机 {vm_name} 不存在")
        self.VMPowers(vm_name, VMPowers.H_CLOSE)
        self.NCCreate(vm_conf, False)
        vm_saving = os.path.join(self.hs_config.system_path, vm_name)
        vm_locker = os.path.join(vm_saving, vm_name + ".vmx.lck")
        if os.path.exists(vm_locker):
            shutil.rmtree(vm_locker)
        hs_result = self.vmrest_api.delete_vmx(vm_name)
        # 通用操作 =============================================================
        super().VMDelete(vm_name)
        return hs_result

    # 虚拟机电源 ###############################################################
    def VMPowers(self, vm_name: str, power: VMPowers) -> ZMessage:
        # 专用操作 =============================================================
        if power == VMPowers.H_RESET or power == VMPowers.S_RESET:
            self.vmrest_api.powers_set(vm_name, VMPowers.H_CLOSE)
            hs_result = self.vmrest_api.powers_set(vm_name, VMPowers.S_START)
        else:
            hs_result = self.vmrest_api.powers_set(vm_name, power)
        self.logs_set(hs_result)
        # 通用操作 =============================================================
        super().VMPowers(vm_name, power)
        return hs_result

    # 备份虚拟机 ###############################################################
    def VMBackup(self, vm_name: str, vm_tips: str) -> ZMessage:
        return super().VMBackup(vm_name, vm_tips)

    # 恢复虚拟机 ###############################################################
    def Restores(self, vm_name: str, vm_back: str) -> ZMessage:
        return super().Restores(vm_name, vm_back)

    # VM镜像挂载 ###############################################################
    def HDDMount(self, vm_name: str, vm_imgs: SDConfig, in_flag=True) -> ZMessage:
        return super().HDDMount(vm_name, vm_imgs, in_flag)

    # ISO镜像挂载 ##############################################################
    def ISOMount(self, vm_name: str, vm_imgs: IMConfig, in_flag=True) -> ZMessage:
        return super().ISOMount(vm_name, vm_imgs, in_flag)

    # 加载备份 #################################################################
    def LDBackup(self, vm_back: str = "") -> ZMessage:
        return super().LDBackup(vm_back)

    # 移除备份 #################################################################
    def RMBackup(self, vm_name: str, vm_back: str = "") -> ZMessage:
        return super().RMBackup(vm_back)

    # 移除磁盘 #################################################################
    def RMMounts(self, vm_name: str, vm_imgs: str) -> ZMessage:
        return super().RMMounts(vm_name, vm_imgs)

    # 查找显卡 #################################################################
    def GPUShows(self) -> dict[str, str]:
        return {}