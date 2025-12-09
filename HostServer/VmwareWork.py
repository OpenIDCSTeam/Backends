import os
import shutil
import subprocess
import time

from HostServer.BaseServer import BaseServer
from MainObject.Config.HSConfig import HSConfig
from MainObject.Server.HSStatus import HSStatus
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Config.NCConfig import NCConfig
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from HostServer.VMRestHost.VRestAPI import VRestAPI


class HostServer(BaseServer):
    # 宿主机服务 ###########################################################
    def __init__(self, config: HSConfig, **kwargs):
        super().__init__(config, **kwargs)  # 传递 kwargs，确保 db 参数能正确传递
        super().__load__(**kwargs)
        self.vmrest_pid = None
        self.vmrest_api = VRestAPI(
            self.hs_config.server_addr,
            self.hs_config.server_user,
            self.hs_config.server_pass,
        )

    # 宿主机任务 =================
    def Crontabs(self) -> bool:
        # 宿主机状态 =================
        hs_status = HSStatus()
        if self.save_data and self.hs_config.server_name:
            self.save_data.add_hs_status(self.hs_config.server_name, hs_status.status())
        all_vms = self.vmrest_api.return_vmx()
        if not all_vms.success:
            return False
        return True

    # 宿主机状态 =================
    def HSStatus(self) -> HWStatus:
        if self.save_data and self.hs_config.server_name:
            status_list = self.save_data.get_hs_status(self.hs_config.server_name)
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

    # 初始宿主机 =================
    def HSCreate(self) -> ZMessage:
        hs_result = ZMessage(success=True, action="HSCreate")
        if self.save_data and self.hs_config.server_name:
            self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)
        return hs_result

    # 还原宿主机 =================
    def HSDelete(self) -> ZMessage:
        hs_result = ZMessage(success=True, action="HSDelete")
        if self.save_data and self.hs_config.server_name:
            self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)
        return hs_result

    # 读取宿主机 ###########################################################
    def HSLoader(self) -> ZMessage:
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
        hs_result = ZMessage(success=True, action="HSLoader", message="OK")
        if self.save_data and self.hs_config.server_name:
            self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)
        return hs_result

    # 卸载宿主机 ###########################################################
    def HSUnload(self) -> ZMessage:
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
        hs_result = ZMessage(
            success=True,
            action="HSUnload",
            message="VM Rest Server stopped",
        )
        if self.save_data and self.hs_config.server_name:
            self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)
        return hs_result

    # 虚拟机列出 =================
    def VMStatus(self, select: str = "") -> dict[str, list[HWStatus]]:
        if self.save_data and self.hs_config.server_name:
            all_status = self.save_data.get_vm_status(self.hs_config.server_name)
            if select:
                return {select: all_status.get(select, [])}
            return all_status
        return {}

    # 创建虚拟机 ###########################################################
    def VMCreate(self, config: VMConfig) -> ZMessage:
        try:
            # 路径处理 =========================================================
            vm_saving = os.path.join(self.hs_config.system_path, config.vm_uuid)
            os.mkdir(vm_saving) if not os.path.exists(vm_saving) else None
            # VM文件名 =========================================================
            vm_file_name = os.path.join(vm_saving, config.vm_uuid)
            # VM配置 ===========================================================
            vm_save_conf = self.vmrest_api.create_vmx(config, self.hs_config)
            with open(os.path.join(vm_file_name + ".vmx"), "w") as vm_save_file:
                vm_save_file.write(vm_save_conf)
            # 复制镜像 =========================================================
            im = os.path.join(self.hs_config.images_path, config.os_name)
            shutil.copy(im, vm_file_name + "." + config.os_name.split(".")[-1])
            # 拓展硬盘 =========================================================
            vm_disk = os.path.join(
                self.hs_config.launch_path, "vmware-vdiskmanager.exe")
            disk_file = f"{vm_file_name}.{config.os_name.split('.')[-1]}"

            print(f"[VMCreate] 开始扩展硬盘: {config.hdd_num}MB")
            print(f"[VMCreate] 执行命令: {vm_disk} -x {config.hdd_num}MB {disk_file}")

            vm_exec = subprocess.Popen(
                [vm_disk, "-x", f"{config.hdd_num}MB", disk_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = vm_exec.communicate(timeout=60)

            if vm_exec.returncode != 0:
                error_msg = f"硬盘扩展失败: {stderr.strip() if stderr else '未知错误'}"
                print(f"[VMCreate] {error_msg}")
                raise Exception(error_msg)

            print(f"[VMCreate] 硬盘扩展完成: {config.hdd_num}MB")

            # 注册机器 =========================================================
            register_result = self.vmrest_api.loader_vmx(vm_file_name + ".vmx")
            if not register_result.success:
                raise Exception(f"注册虚拟机失败: {register_result.message}")

            # 只有在所有操作都成功后才保存配置到vm_saving
            self.vm_saving[config.vm_uuid] = config

            # 保存到数据库 =====================================================
            if self.save_data and self.hs_config.server_name:
                self.save_data.set_vm_saving(self.hs_config.server_name, self.vm_saving)

            # 返回结果 =========================================================
            hs_result = ZMessage(success=True, action="VMCreate",
                                 message="虚拟机创建成功")
            if self.save_data and self.hs_config.server_name:
                self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)
            return hs_result
        except Exception as e:
            # 创建失败时清理已创建的文件
            vm_saving = os.path.join(self.hs_config.system_path, config.vm_uuid)
            if os.path.exists(vm_saving):
                try:
                    shutil.rmtree(vm_saving)
                except:
                    pass
            # 返回错误信息
            error_msg = f"虚拟机创建失败: {str(e)}"
            hs_result = ZMessage(success=False, action="VMCreate", message=error_msg)
            if self.save_data and self.hs_config.server_name:
                self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)
            return hs_result

    # 安装虚拟机 ###########################################################
    def VInstall(self, config: VMConfig) -> ZMessage:
        pass

    # 配置虚拟机 ###########################################################
    def VMUpdate(self, config: VMConfig, old: VMConfig = None) -> ZMessage:

        vm_saving = os.path.join(self.hs_config.system_path, config.vm_uuid)
        vm_locker = os.path.join(vm_saving, config.vm_uuid + ".vmx.lck")
        if os.path.exists(vm_locker):
            shutil.rmtree(vm_locker)
        # 检查虚拟机是否存在
        if config.vm_uuid not in self.vm_saving:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机 {config.vm_uuid} 不存在")
        # 更新vm_saving中的配置
        self.vm_saving[config.vm_uuid] = config
        # 关闭虚拟机 =======================================
        self.VMPowers(config.vm_uuid, VMPowers.H_CLOSE)
        time.sleep(1)
        # 更新网卡
        network_result = super().VMUpdate(config, old)
        if not network_result.success:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机 {config.vm_uuid} 网络配置更新失败: {network_result.message}")

        # 读取现有的VMX文件内容
        vm_save_name = os.path.join(vm_saving, config.vm_uuid + ".vmx")
        if os.path.exists(vm_save_name):
            try:
                with open(vm_save_name, "r", encoding="utf-8") as vm_file:
                    existing_vmx_content = vm_file.read()
                # 使用update_vmx方法合并配置
                vm_save_conf = self.vmrest_api.update_vmx(existing_vmx_content, config, self.hs_config)
            except Exception as e:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {config.vm_uuid} 配置更新失败: {e}")
        else:
            # 如果文件不存在，重新创建
            vm_save_conf = self.vmrest_api.create_vmx(config, self.hs_config)

        # 写入VMX文件
        try:
            with open(vm_save_name, "w", encoding="utf-8") as vm_save_file:
                vm_save_file.write(vm_save_conf)
        except Exception as e:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机 {config.vm_uuid} VMX文件写入失败: {e}")

        # 启动虚拟机
        start_result = self.VMPowers(config.vm_uuid, VMPowers.S_START)
        if not start_result.success:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机 {config.vm_uuid} 启动失败: {start_result.message}")

        # 保存到数据库（在所有操作成功后）
        if self.save_data and self.hs_config.server_name:
            if not self.save_data.set_vm_saving(self.hs_config.server_name, self.vm_saving):
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {config.vm_uuid} 配置保存到数据库失败")

        # 记录日志
        hs_result = ZMessage(
            success=True, action="VMUpdate",
            message=f"虚拟机 {config.vm_uuid} 配置已更新")
        if self.save_data and self.hs_config.server_name:
            self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)

        return hs_result

    # 删除虚拟机 ###########################################################
    def VMDelete(self, select: str) -> ZMessage:
        vm_saving = os.path.join(self.hs_config.system_path, select)
        vm_locker = os.path.join(vm_saving, select + ".vmx.lck")
        if os.path.exists(vm_locker):
            shutil.rmtree(vm_locker)
        hs_result = self.vmrest_api.delete_vmx(select)
        # 删除虚拟机文件
        if os.path.exists(vm_saving):
            shutil.rmtree(vm_saving)
        # 从vm_saving中删除
        if select in self.vm_saving:
            del self.vm_saving[select]
        # 保存到数据库
        if self.save_data and self.hs_config.server_name:
            self.save_data.set_vm_saving(self.hs_config.server_name, self.vm_saving)
            self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)
        return hs_result

    # 虚拟机电源 =================
    def VMPowers(self, select: str, power: VMPowers) -> ZMessage:
        hs_result = self.vmrest_api.powers_set(select, power)
        if self.save_data and self.hs_config.server_name:
            self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)
        return hs_result

    def Password(self, hs_name: str, vm_uuid: str, new_password: str) -> ZMessage:
        """
        修改虚拟机密码API
        :param hs_name: 主机名（用于日志记录）
        :param vm_uuid: 虚拟机UUID
        :param new_password: 新密码
        :return: 操作结果
        """
        try:
            # 检查虚拟机是否存在
            if vm_uuid not in self.vm_saving:
                return ZMessage(
                    success=False, action="Password",
                    message=f"虚拟机 {vm_uuid} 不存在"
                )

            # 获取当前虚拟机配置
            current_config = self.vm_saving[vm_uuid]
            if not isinstance(current_config, VMConfig):
                # 如果从数据库读取的是字典，需要转换为VMConfig对象
                if isinstance(current_config, dict):
                    current_config = VMConfig(**current_config)
                else:
                    return ZMessage(
                        success=False, action="Password",
                        message=f"虚拟机 {vm_uuid} 配置格式错误"
                    )

            # 验证新密码（可选，如果前端已经验证过可以跳过）
            if len(new_password) < 12:
                return ZMessage(
                    success=False, action="Password",
                    message="密码长度不得低于12位"
                )

            # 检查密码复杂度
            type_count = 0
            import re
            if re.search(r'[a-zA-Z]', new_password):
                type_count += 1
            if re.search(r'[0-9]', new_password):
                type_count += 1
            if re.search(r'[^a-zA-Z0-9]', new_password):
                type_count += 1

            if type_count < 2:
                return ZMessage(
                    success=False, action="Password",
                    message="密码必须至少包含字母、数字、特殊符号中的两种"
                )

            # 保存旧配置用于VMUpdate
            old_config = VMConfig(**current_config.__dict__())

            # 更新密码（同时更新系统密码和VNC密码）
            current_config.os_pass = new_password
            current_config.vc_pass = new_password

            # 强制关闭虚拟机
            close_result = self.VMPowers(vm_uuid, VMPowers.H_CLOSE)
            if not close_result.success:
                return ZMessage(
                    success=False, action="Password",
                    message=f"强制关闭虚拟机失败: {close_result.message}"
                )

            # 等待虚拟机关闭
            time.sleep(2)

            # 调用VMUpdate更新配置
            update_result = self.VMUpdate(current_config, old_config)
            if not update_result.success:
                # 如果更新失败，恢复旧密码
                self.vm_saving[vm_uuid] = old_config
                return ZMessage(
                    success=False, action="Password",
                    message=f"更新虚拟机配置失败: {update_result.message}"
                )

            # 保存到数据库
            if self.save_data and self.hs_config.server_name:
                self.save_data.set_vm_saving(self.hs_config.server_name, self.vm_saving)

            # 记录日志
            hs_result = ZMessage(
                success=True, action="Password",
                message=f"虚拟机 {vm_uuid} 密码修改成功"
            )
            if self.save_data and self.hs_config.server_name:
                self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)

            return hs_result

        except Exception as e:
            error_msg = f"虚拟机 {vm_uuid} 密码修改失败: {str(e)}"
            hs_result = ZMessage(success=False, action="Password", message=error_msg)
            if self.save_data and self.hs_config.server_name:
                self.save_data.add_hs_logger(self.hs_config.server_name, hs_result)
            return hs_result
