import os
import shutil
import subprocess

from HostServer.Template import BaseServer
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
        super().__init__(config)
        super().__load__(**kwargs)
        self.vmrest_pid = None
        self.vmrest_api = VRestAPI(
            self.hs_config.server_addr,
            self.hs_config.server_user,
            self.hs_config.server_pass,
        )

    # 宿主机状态 ###########################################################
    def HSStatus(self) -> HWStatus:
        if len(self.hs_status) == 0:
            hs_status = HSStatus()
            return hs_status.status()
        return self.hs_status[-1]

    # 宿主机状态 ###########################################################
    def Crontabs(self) -> bool:
        # 宿主机状态 ===============================
        hs_status = HSStatus()
        self.hs_status.append(hs_status.status())
        # 虚拟机状态 ===============================
        self.vm_status: dict[str, list[HWStatus]] = {}
        # 电源状态映射（VMRest API返回值 -> VMPowers枚举）
        power_map = {
            "poweredOn": VMPowers.STARTED,
            "poweredOff": VMPowers.STOPPED,
            "suspended": VMPowers.SUSPEND,
            "paused": VMPowers.SUSPEND,
        }
        all_vms = self.vmrest_api.return_vmx()
        if not all_vms.success:
            return False
        for now_vmx in all_vms.results:
            vm_path = now_vmx.get("path", "")
            # 从路径中提取虚拟机名称 =================================
            vm_name = os.path.splitext(os.path.basename(vm_path))[0]
            # 过滤虚拟机名称 =========================================
            if self.hs_config.filter_name != "":
                if not vm_name.startswith(self.hs_config.filter_name):
                    continue
            # 获取电源状态 ===========================================
            self.vm_status[vm_name] = []
            power_result = self.vmrest_api.powers_get(vm_name)
            ac_status = VMPowers.UNKNOWN
            if power_result.success:
                power_state = power_result.results.get("power_state", "")
                ac_status = power_map.get(power_state, VMPowers.UNKNOWN)
            self.vm_status[vm_name].append(HWStatus(ac_status=ac_status))
        return True

    # 初始宿主机 ###########################################################
    def HSCreate(self) -> ZMessage:
        hs_result = ZMessage(success=True, action="HSCreate")
        self.hs_logger.append(hs_result)
        return hs_result

    # 还原宿主机 ###########################################################
    def HSDelete(self) -> ZMessage:
        hs_result = ZMessage(success=True, action="HSDelete")
        self.hs_logger.append(hs_result)
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
        self.hs_logger.append(hs_result)
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
        self.hs_logger.append(hs_result)
        return hs_result

    # 宿主机操作 ###########################################################
    def HSAction(self, action: str = "") -> ZMessage:
        hs_result = ZMessage(success=True, action="HSAction")
        self.hs_logger.append(hs_result)
        return hs_result



    # 虚拟机列出 ###########################################################
    def VMStatus(self, select: str = "") -> dict[str, list[HWStatus]]:
        if len(select) > 0:
            if select not in self.vm_status:
                return {select: [HWStatus()]}
            return {select: self.vm_status[select]}
        return self.vm_status

    # 创建虚拟机 ###########################################################
    def VMCreate(self, config: VMConfig) -> ZMessage:
        self.vm_saving[config.vm_uuid] = config
        # 路径处理 =========================================================
        vm_saving = os.path.join(self.hs_config.system_path, config.vm_uuid)
        os.mkdir(vm_saving) if not os.path.exists(vm_saving) else None
        # VM文件名 =========================================================
        vm_file_name = os.path.join(vm_saving, config.vm_uuid)
        # VM配置 ===========================================================
        vm_save_conf = self.vmrest_api.create_vmx(config)
        with open(os.path.join(vm_file_name + ".vmx"), "w") as vm_save_file:
            vm_save_file.write(vm_save_conf)
        # 复制镜像 =========================================================
        im = os.path.join(self.hs_config.images_path, config.os_name + ".vmdk")
        shutil.copy(im, vm_file_name + ".vmdk")
        # 注册机器 =========================================================
        self.vmrest_api.loader_vmx(vm_file_name + ".vmx")
        # 返回结果 =========================================================
        hs_result = ZMessage(success=True, action="VMCreate", message="OK")
        self.hs_logger.append(hs_result)
        return hs_result

    # 安装虚拟机 ###########################################################
    def VInstall(self, config: VMConfig) -> ZMessage:
        pass

    # 配置虚拟机 ###########################################################
    def VMUpdate(self, config: VMConfig) -> ZMessage:
        vm_uuid = config.vm_uuid
        # 检查虚拟机是否存在
        if vm_uuid not in self.vm_saving:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机 {vm_uuid} 不存在")
        # 更新vm_saving中的配置
        self.vm_saving[vm_uuid] = config
        # 记录日志
        hs_result = ZMessage(
            success=True, action="VMUpdate",
            message=f"虚拟机 {vm_uuid} 配置已更新")
        self.hs_logger.append(hs_result)
        # 保存到数据库
        if self.db and self.hs_name:
            self.db.save_vm_saving(self.hs_name, self.vm_saving)
        return hs_result

    # 删除虚拟机 ###########################################################
    def VMDelete(self, select: str) -> ZMessage:
        hs_result = self.vmrest_api.delete_vmx(select)
        if hs_result.success:
            shutil.rmtree(os.path.join(self.hs_config.system_path, select))
        self.hs_logger.append(hs_result)
        return hs_result

    # 虚拟机电源 ###########################################################
    def VMPowers(self, select: str, power: VMPowers) -> ZMessage:
        hs_result = self.vmrest_api.powers_set(select, power)
        self.hs_logger.append(hs_result)
        return hs_result

    # 虚拟机电源 ###########################################################
    def VConsole(self, select: str) -> str:
        return ""


# 测试代码 ========================================================================
if __name__ == "__main__":
    hs_config = HSConfig(
        server_type="Win64VMW",
        server_addr="localhost:8697",
        server_user="root",
        server_pass="VmD55!MkW@%Q",
        filter_name="",
        images_path=r"G:\OIDCS\Win64VMW\images",
        system_path=r"G:\OIDCS\Win64VMW\system",
        backup_path=r"G:\OIDCS\Win64VMW\backup",
        extern_path=r"G:\OIDCS\Win64VMW\extern",
        launch_path=r"C:\Program Files (x86)\VMware\VMware Workstation",
        network_nat="nat",
        network_pub="",
        public_addr="42.42.42.42",
        extend_data={

        }
    )
    vm_config = VMConfig(
        vm_uuid="Tests-All",
        os_name="windows10x64",
        cpu_num=4,
        mem_num=2048,
        hdd_num=10240,
        gpu_num=0,
        net_num=100,
        flu_num=100,
        nat_num=100,
        web_num=100,
        gpu_mem=8192,
        speed_u=100,
        speed_d=100,
        nic_all={
            "ethernet0": NCConfig(
                ip4_addr="192.168.4.101",
                nic_type="nat",
            )
        }
    )
    hs_server = HostServer(hs_config)
    hs_server.HSCreate()
    hs_server.HSLoader()
    # hs_server.VMCreate(vm_config)
    # hs_server.VMPowers(vm_config.vm_uuid, VMPowers.S_START)
    # hs_server.VMPowers(vm_config.vm_uuid, VMPowers.S_CLOSE)
    # hs_server.VMDelete(vm_config.vm_uuid)
    do_result = hs_server.VMStatus()
    for i in do_result:
        print(i)
    hs_server.HSUnload()
