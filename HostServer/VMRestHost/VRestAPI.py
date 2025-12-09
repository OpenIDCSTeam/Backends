import requests
from requests.auth import HTTPBasicAuth

from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMPowers import VMPowers


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
                full_url, auth=auth, headers=head, json=data, timeout=30)
            response.raise_for_status()
            # 返回成功消息 ================================================
            return ZMessage(
                success=True, actions="vmrest_api", message="请求成功",
                results=response.json() if response.text else {})
        # 处理HTTP错误 ====================================================
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP错误 {e.response.status_code}: {e.response.reason}"
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {e.response.text}"
            return ZMessage(success=False, actions="vmrest_api",
                            message=error_msg, execute=e)
        # 处理连接错误 ====================================================
        except requests.exceptions.ConnectionError as e:
            return ZMessage(success=False, actions="vmrest_api",
                            message=f"连接失败: 无法连接到 {self.host_addr}", execute=e)
        # 处理超时错误 ====================================================
        except requests.exceptions.Timeout as e:
            return ZMessage(success=False, actions="vmrest_api",
                            message=f"请求超时: 操作耗时过长", execute=e)
        # 处理其他请求异常 ================================================
        except requests.exceptions.RequestException as e:
            return ZMessage(success=False, actions="vmrest_api",
                            message=f"请求异常: {str(e)}", execute=e)
        # 处理所有其他异常 ================================================
        except Exception as e:
            return ZMessage(success=False, actions="vmrest_api",
                            message=f"未知错误: {type(e).__name__} - {str(e)}", execute=e)

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
                data=power,
                timeout=30  # 添加超时设置
            )
            response.raise_for_status()
            return ZMessage(
                success=True,
                actions="vmrest_api_power",
                message="电源操作成功",
                results=response.json() if response.text else {}
            )
        except requests.exceptions.HTTPError as e:
            # HTTP错误（4xx, 5xx）
            error_msg = f"HTTP错误 {e.response.status_code}: {e.response.reason}"
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {e.response.text}"
            return ZMessage(
                success=False,
                actions="vmrest_api_power",
                message=error_msg,
                execute=e
            )
        except requests.exceptions.ConnectionError as e:
            # 连接错误
            return ZMessage(
                success=False,
                actions="vmrest_api_power",
                message=f"连接失败: 无法连接到 {self.host_addr}，请检查VMware REST API服务是否启动",
                execute=e
            )
        except requests.exceptions.Timeout as e:
            # 超时错误
            return ZMessage(
                success=False,
                actions="vmrest_api_power",
                message=f"请求超时: 操作耗时过长，请稍后重试",
                execute=e
            )
        except requests.exceptions.RequestException as e:
            # 其他请求异常
            return ZMessage(
                success=False,
                actions="vmrest_api_power",
                message=f"请求异常: {str(e)}",
                execute=e
            )
        except Exception as e:
            # 捕获所有其他异常
            return ZMessage(
                success=False,
                actions="vmrest_api_power",
                message=f"未知错误: {type(e).__name__} - {str(e)}",
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
    def powers_set(self, vmx_name: str, power: VMPowers, vm_password: str = None) -> ZMessage:
        try:
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
            # 构建URL，如果有虚拟机密码则添加查询参数
            url = f"/vms/{vm_id}/power"
            if vm_password:
                # 对密码进行URL编码
                from urllib.parse import quote
                url += f"?vmPassword={quote(vm_password)}"
            # VMRest API要求PUT请求体为纯字符串
            return self.powers_api(url, state_str)
        except Exception as e:
            # 捕获powers_set方法内的所有异常
            return ZMessage(
                success=False,
                actions="set_powers",
                message=f"设置电源状态失败: {type(e).__name__} - {str(e)}",
                execute=e
            )

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

    # 更新VMX配置文件 ######################################################
    # 读取现有VMX文件内容，与新配置合并后返回
    # :param existing_vmx: 现有VMX文件内容
    # :param vm_conf: VMConfig对象
    # :return: 合并后的VMX内容
    # #####################################################################
    def update_vmx(self, existing_vmx: str, vm_conf: VMConfig, hs_config: HSConfig = None) -> str:
        # 生成新的配置内容
        new_vmx_content = self.create_vmx(vm_conf, hs_config)
        new_config_lines = new_vmx_content.strip().split('\n')

        # 解析现有VMX文件
        existing_config = {}
        existing_lines = existing_vmx.strip().split('\n')

        for line in existing_lines:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key_part = line.split('=')[0].strip()
                value_part = line.split('=', 1)[1].strip()
                existing_config[key_part] = value_part

        # 解析新配置并创建更新后的配置
        updated_config = existing_config.copy()

        for line in new_config_lines:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key_part = line.split('=')[0].strip()
                value_part = line.split('=', 1)[1].strip()
                # 用新配置替换现有配置
                updated_config[key_part] = value_part

        # 重新构建VMX内容
        result_lines = []
        for line in existing_lines:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key_part = line.split('=')[0].strip()
                if key_part in updated_config:
                    result_lines.append(f"{key_part} = {updated_config[key_part]}")
                    del updated_config[key_part]
                else:
                    result_lines.append(line)
            else:
                # 保留注释和空行
                result_lines.append(line)

        # 添加新配置中不存在的项
        for key, value in sorted(updated_config.items()):
            result_lines.append(f"{key} = {value}")

        return '\n'.join(result_lines) + '\n'

    # 获取网络列表 ########################################################
    # 获取所有虚拟网络
    # #####################################################################
    def return_net(self) -> ZMessage:
        return self.vmrest_api("/vmnet")

    # 创建虚拟机 ##########################################################
    # :param vm_conf: VMConfig对象
    # :return: 虚拟机名称
    # #####################################################################
    def create_vmx(self, vm_conf: VMConfig = None, hs_config: HSConfig = None) -> str:
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
                    "port": vm_conf.vc_port,
                    "password": vm_conf.vc_pass,
                }
            }
        }
        nic_uuid = 0  # 网卡配置 ==========================================
        for nic_name, nic_data in vm_conf.nic_all.items():
            use_auto = nic_data.mac_addr is None or nic_data.mac_addr == ""
            nic_types = ""
            if nic_data.nic_type == 'nat':
                nic_types = hs_config.network_nat
            elif nic_data.nic_type == 'pub':
                nic_types = hs_config.network_pub

            vmx_config[f"ethernet{nic_uuid}"] = {
                "connectionType": nic_types,
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
