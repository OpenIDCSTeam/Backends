import os
import shutil
import subprocess
from HostServer.BaseServer import BaseServer
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from HostServer.VMRestHost.VRestAPI import VRestAPI


class HostServer(BaseServer):
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

    # 创建虚拟机 ###############################################################
    def VMCreate(self, vm_conf: VMConfig) -> ZMessage:
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
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
            results = self.VInstall(vm_conf)
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
    def VInstall(self, vm_conf: VMConfig) -> ZMessage:
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
        if vm_conf.os_name != vm_last.os_name:
            self.VInstall(vm_conf.os_name, vm_path, vm_conf.hdd_num)
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
        self.VMPowers(vm_name, VMPowers.H_CLOSE)
        vm_saving = os.path.join(self.hs_config.system_path, vm_name)
        vm_locker = os.path.join(vm_saving, vm_name + ".vmx.lck")
        if os.path.exists(vm_locker):
            shutil.rmtree(vm_locker)
        hs_result = self.vmrest_api.delete_vmx(vm_name)
        # 通用操作 =============================================================
        super().VMDelete(vm_name)
        return hs_result

    # 虚拟机电源 ###############################################################
    # :params vm_name: 虚拟机UUID
    # :params power: 虚拟机电源状态
    # ##########################################################################
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

    # 设置虚拟机密码 ###########################################################
    # :params vm_name: 虚拟机UUID
    # :params os_pass: 虚拟机密码
    # ##########################################################################
    def Password(self, vm_name: str, os_pass: str) -> ZMessage:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().Password(vm_name, os_pass)
