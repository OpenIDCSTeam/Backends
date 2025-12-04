import requests
from requests.auth import HTTPBasicAuth

from HostObject.VMConfig import VMConfig
from HostObject.ZMConfig import NCConfig
from HostObject.ZMessage import ZMessage
from HostObject.VMPowers import VMPowers


class VRestAPI:
    def __init__(self,
                 host_addr="localhost:8697",
                 host_user="root",
                 host_pass="password",
                 ver_agent=21):
        self.host_addr = host_addr
        self.host_user = host_user
        self.host_pass = host_pass
        self.ver_agent = ver_agent

    @staticmethod
    # 创建vmx文本 #########################################################
    # :param config: 配置字典
    # :param prefix: 前缀字符串
    # :return: vmx文本
    # #####################################################################
    def create_txt(config: dict, prefix: str = "") -> str:
        result = ""
        for key, value in config.items():
            if isinstance(value, dict):  # 如果值是字典，递归处理 =========
                new_prefix = f"{prefix}{key}." if prefix else f"{key}."
                result += VRestAPI.create_txt(value, new_prefix)
            else:  # 如果值不是字典，直接生成配置行 =======================
                full_key = f"{prefix}{key}" if prefix else key
                if type(value) == str:
                    result += f"{full_key} = \"{value}\"\n"
                else:
                    result += f"{full_key} = {value}\n"
        return result

    # VMRestAPI ###########################################################
    # 发送VMRest API请求
    # :param url: API端点路径 (如 /vms, /vms/{id}/power)
    # :param data: 请求体数据 (用于POST/PUT请求)
    # :param method: HTTP方法 (GET, POST, PUT, DELETE)
    # :return: ZMessage对象
    # #####################################################################
    def vmrest_api(self, url: str, data=None, m: str = "GET") -> ZMessage:
        full_url = f"http://{self.host_addr}/api{url}"
        auth = HTTPBasicAuth(self.host_user, self.host_pass)
        # 设置请求头 ======================================================
        head = {"Content-Type": "application/vnd.vmware.vmw.rest-v1+json"}
        methods = {"GET": requests.get, "POST": requests.post,
                   "PUT": requests.put, "DELETE": requests.delete}
        try:  # 无效请求 ==================================================
            if m.upper() not in methods:
                return ZMessage(success=False, actions="vmrest_api",
                                message=f"不支持的HTTP方法: {m}")
            # 发送请求 ====================================================
            response = methods[m.upper()](
                full_url, auth=auth, headers=head, json=data)
            response.raise_for_status()
            # 返回成功消息 ================================================
            return ZMessage(
                success=True, actions="vmrest_api", message="请求成功",
                results=response.json() if response.text else {})
        # 处理请求异常 ====================================================
        except requests.exceptions.RequestException as e:
            return ZMessage(success=False, actions="vmrest_api",
                            message=str(e), execute=e)

    # VMRest电源操作API  ##################################################
    # 发送VMRest电源操作请求（PUT请求体为纯字符串）
    # :param url: API端点路径
    # :param power: 电源状态字符串 (on, off, shutdown, suspend, pause, unpause)
    # :return: ZMessage对象
    # #####################################################################
    def powers_api(self, url: str, power: str) -> ZMessage:
        full_url = f"http://{self.host_addr}/api{url}"
        auth = HTTPBasicAuth(self.host_user, self.host_pass)
        head = {"Content-Type": "application/vnd.vmware.vmw.rest-v1+json"}
        try:
            response = requests.put(
                full_url,
                auth=auth,
                headers=head,
                data=power)
            response.raise_for_status()
            return ZMessage(
                success=True,
                actions="vmrest_api_power",
                message="电源操作成功",
                results=response.json() if response.text else {}
            )
        except requests.exceptions.RequestException as e:
            return ZMessage(
                success=False,
                actions="vmrest_api_power",
                message=str(e),
                execute=e
            )

    # 获取所有虚拟机列表 ##################################################
    # return: ZMessage对象
    # #####################################################################
    def return_vmx(self) -> ZMessage:
        return self.vmrest_api("/vms")

    # 选择虚拟机ID ########################################################
    # 根据虚拟机名称获取虚拟机ID
    # :param vm_name: 虚拟机名称
    # :return: 虚拟机ID，未找到返回空字符串
    # #####################################################################
    def select_vid(self, vm_name: str) -> str:
        result = self.return_vmx()
        if not result.success:
            return ""
        vms = result.results if isinstance(result.results, list) else []
        for vm in vms:
            # VMRest API返回的虚拟机信息包含id和path字段
            # 从path中提取虚拟机名称进行匹配
            vm_path = vm.get("path", "")
            vm_id = vm.get("id", "")
            # 方式1：直接匹配路径中的虚拟机名称
            if vm_name in vm_path:
                return vm_id
            # 方式2：提取.vmx文件名进行匹配
            import os
            vmx_name = os.path.splitext(os.path.basename(vm_path))[0]
            if vmx_name == vm_name:
                return vm_id
        return ""

    # 获取虚拟机电源状态 ##################################################
    # 获取指定虚拟机的电源状态
    # :param vm_name: 虚拟机名称
    # #####################################################################
    def powers_get(self, vm_name: str) -> ZMessage:
        vm_id = self.select_vid(vm_name)
        if not vm_id:
            return ZMessage(
                success=False,
                actions="get_powers",
                message=f"未找到虚拟机: {vm_name}"
            )
        return self.vmrest_api(f"/vms/{vm_id}/power")

    # 设置虚拟机电源状态 ##################################################
    # :param vm_name: 虚拟机名称
    # :param power_state: VMPowers枚举类型
    # :param vm_password: 加密虚拟机的密码（可选）
    # :return: ZMessage对象
    # #####################################################################
    def powers_set(self, vmx_name: str, power: VMPowers) -> ZMessage:
        # 电源状态映射
        power_map = {
            VMPowers.S_START: "on",
            VMPowers.S_CLOSE: "shutdown",
            VMPowers.S_RESET: "reset",
            VMPowers.H_CLOSE: "off",
            VMPowers.H_RESET: "reset",
            VMPowers.A_PAUSE: "pause",
            VMPowers.A_WAKED: "unpause",
        }
        state_str = power_map.get(power, "on")
        vm_id = self.select_vid(vmx_name)
        if not vm_id:
            return ZMessage(
                success=False,
                actions="set_powers",
                message=f"未找到虚拟机: {vmx_name}"
            )
        # 构建URL，如果有密码则添加查询参数
        url = f"/vms/{vm_id}/power"
        if self.host_pass:
            url += f"?vmPassword={self.host_pass}"
        # VMRest API要求PUT请求体为纯字符串
        return self.powers_api(url, state_str)

    # 注册虚拟机 ##########################################################
    # 注册虚拟机到VMware Workstation
    # :param vmx_path: .vmx文件的完整路径
    # :param vm_name: 虚拟机名称（可选，默认使用vmx文件名）
    # #####################################################################
    def loader_vmx(self, vmx_path: str, vm_name: str = None) -> ZMessage:
        import os
        if vm_name is None:
            # 从路径中提取虚拟机名称（不含扩展名）
            vm_name = os.path.splitext(os.path.basename(vmx_path))[0]
        return self.vmrest_api(
            "/vms/registration",
            {"name": vm_name, "path": vmx_path},
            "POST")

    # 删除虚拟机 ##########################################################
    # 从VMware Workstation中删除虚拟机
    # :param vm_name: 虚拟机名称
    # #####################################################################
    def delete_vmx(self, vm_name: str) -> ZMessage:
        vm_id = self.select_vid(vm_name)
        if not vm_id:
            return ZMessage(
                success=False,
                actions="delete_vmx",
                message=f"未找到虚拟机: {vm_name}"
            )
        return self.vmrest_api(f"/vms/{vm_id}", m="DELETE")

    # 获取虚拟机配置 ######################################################
    # 获取虚拟机配置信息
    # :param vm_name: 虚拟机名称
    # #####################################################################
    def config_get(self, vm_name: str) -> ZMessage:
        vm_id = self.select_vid(vm_name)
        if not vm_id:
            return ZMessage(
                success=False,
                actions="get_config",
                message=f"未找到虚拟机: {vm_name}"
            )
        return self.vmrest_api(f"/vms/{vm_id}")

    # 更新虚拟机配置 ######################################################
    # 更新虚拟机配置
    # :param vm_name: 虚拟机名称
    # :param config: 配置字典
    # #####################################################################
    def config_set(self, vm_name: str, config: dict) -> ZMessage:
        vm_id = self.select_vid(vm_name)
        if not vm_id:
            return ZMessage(
                success=False,
                actions="set_config",
                message=f"未找到虚拟机: {vm_name}"
            )
        return self.vmrest_api(f"/vms/{vm_id}", config, "PUT")

    # 获取网络列表 ########################################################
    # 获取所有虚拟网络
    # #####################################################################
    def return_net(self) -> ZMessage:
        return self.vmrest_api("/vmnet")

    # 创建虚拟机 ##########################################################
    # :param vm_conf: VMConfig对象
    # :return: 虚拟机名称
    # #####################################################################
    def create_vmx(self, vm_conf: VMConfig = None) -> str:
        vmx_config = {
            # 编码配置 ============================================
            ".encoding": "GBK",
            "config.version": "8",
            "virtualHW.version": str(self.ver_agent),
            # 基本配置 ============================================
            "displayName": vm_conf.vm_uuid,
            "firmware": "efi",
            "guestOS": "windows9-64",
            # 硬件配置 ============================================
            "numvcpus": str(vm_conf.cpu_num),
            "cpuid.coresPerSocket": str(vm_conf.cpu_num),
            "memsize": str(vm_conf.mem_num),
            "mem.hotadd": "TRUE",
            "mks.enable3d": "TRUE",
            "svga.graphicsMemoryKB": str(vm_conf.gpu_mem * 1024),
            # 设备配置 ============================================
            "vmci0.present": "TRUE",
            "hpet0.present": "TRUE",
            "usb.present": "TRUE",
            "ehci.present": "TRUE",
            "usb_xhci.present": "TRUE",
            "tools.syncTime": "TRUE",
            "nvram": vm_conf.vm_uuid + ".nvram",
            "virtualHW.productCompatibility": "hosted",
            "extendedConfigFile": vm_conf.vm_uuid + ".vmxf",
            # PCI桥接配置 =========================================
            "pciBridge0": {
                "present": "TRUE"
            },
            "pciBridge4": {
                "present": "TRUE",
                "virtualDev": "pcieRootPort",
                "functions": "8"
            },
            # 系统盘配置 ==========================================
            "nvme0.present": "TRUE",
            "nvme0:0": {
                "fileName": vm_conf.vm_uuid + ".vmdk",
                "present": "TRUE"
            },
            # 远程显示配置 ========================================
            "RemoteDisplay": {
                "vnc": {
                    "enabled": "TRUE",
                    "port": vm_config.vc_port,
                    "password": vm_config.vc_pass,
                }
            }
        }
        nic_uuid = 0  # 网卡配置 ==========================================
        for nic_name, nic_data in vm_conf.nic_all.items():
            use_auto = nic_data.mac_addr is None or nic_data.mac_addr == ""
            vmx_config[f"ethernet{nic_uuid}"] = {
                "connectionType": "nat" if nic_data.nic_type == "nat" else "",
                "addressType": "generated" if use_auto else "static",
                "address": nic_data.mac_addr if not use_auto else "",
                "virtualDev": "e1000e",
                "present": "TRUE",
                "txbw.limit": str(vm_conf.speed_u * 1024),
                "rxbw.limit": str(vm_conf.speed_d * 1024),
            }
            nic_uuid += 1
        hdd_uuid = 1  # 数据磁盘 ==========================================
        for hdd_name, hdd_data in vm_conf.hdd_all.items():
            # todo: 创建VMDK文件
            vmx_config[f"nvme0:{hdd_uuid}"] = {
                "fileName": vm_conf.vm_uuid + f"-{hdd_uuid}.vmdk",
                "present": "TRUE"
            }
            hdd_uuid += 1
        return VRestAPI.create_txt(vmx_config)


# 测试代码 ################################################################
if __name__ == "__main__":
    vm_client = VRestAPI()
    vm_config = VMConfig(
        vm_uuid="Tests-All",
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
                ip4_addr="192.168.1.1",
            )
        }
    )
    vm_string = vm_client.create_vmx(vm_config)
    print(vm_string)
    with open(vm_config.vm_uuid + ".vmx", "w", encoding="utf-8") as save_file:
        save_file.write(vm_string)
