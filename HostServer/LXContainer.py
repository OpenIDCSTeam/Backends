import os
import shutil
import tarfile
import random
import string
import time
import subprocess
from copy import deepcopy
from typing import Optional, Tuple
from loguru import logger

try:
    import pylxd
    from pylxd import Client
    from pylxd.exceptions import LXDAPIException, NotFound
    LXD_AVAILABLE = True
except ImportError:
    LXD_AVAILABLE = False
    logger.warning("pylxd not available, LXD functionality will be disabled")
    Client = None  # 定义一个占位符，避免类型注解错误

from HostServer.BasicServer import BasicServer
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.IMConfig import IMConfig
from MainObject.Config.SDConfig import SDConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig


class HostServer(BasicServer):
    # 宿主机服务 ###############################################################
    def __init__(self, config: HSConfig, **kwargs):
        super().__init__(config, **kwargs)
        super().__load__(**kwargs)
        # LXD 客户端连接
        self.lxd_client = None
        self.ttyd_process = None  # ttyd Web Terminal 进程
        self.ttyd_tokens = {}  # 存储容器名称到token的映射

    # 连接到 LXD 服务器 ########################################################
    def _connect_lxd(self) -> Tuple[Optional[Client], ZMessage]:
        """
        连接到 LXD 服务器（支持本地和远程）
        :return: (LXD客户端对象, 操作结果消息)
        """
        if not LXD_AVAILABLE:
            return None, ZMessage(
                success=False, action="_connect_lxd",
                message="pylxd is not installed")
        
        try:
            # 如果已经连接，直接返回
            if self.lxd_client is not None:
                return self.lxd_client, ZMessage(success=True, action="_connect_lxd")
            
            # 判断是本地连接还是远程连接
            if self.hs_config.server_addr in ["localhost", "127.0.0.1", ""]:
                # 本地连接
                logger.info("Connecting to local LXD server")
                self.lxd_client = Client()
            else:
                # 远程连接（使用 HTTPS）
                endpoint = f"https://{self.hs_config.server_addr}:8443"
                logger.info(f"Connecting to remote LXD server: {endpoint}")
                
                # 证书路径（从 launch_path 获取）
                cert_path = os.path.join(self.hs_config.launch_path, "client.crt")
                key_path = os.path.join(self.hs_config.launch_path, "client.key")
                
                if not os.path.exists(cert_path) or not os.path.exists(key_path):
                    return None, ZMessage(
                        success=False, action="_connect_lxd",
                        message=f"Client certificates not found in {self.hs_config.launch_path}")
                
                self.lxd_client = Client(
                    endpoint=endpoint,
                    cert=(cert_path, key_path),
                    verify=False  # 可以设置为服务器证书路径以验证
                )
            
            # 测试连接
            self.lxd_client.containers.all()
            logger.info("Successfully connected to LXD server")
            
            return self.lxd_client, ZMessage(success=True, action="_connect_lxd")
            
        except Exception as e:
            logger.error(f"Failed to connect to LXD server: {str(e)}")
            self.lxd_client = None
            return None, ZMessage(
                success=False, action="_connect_lxd",
                message=f"Failed to connect to LXD: {str(e)}")

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
        # 连接到 LXD 服务器
        client, result = self._connect_lxd()
        if not result.success:
            return result
        
        # 启动 ttyd Web Terminal 服务（仅本地模式）
        if self.hs_config.server_addr in ["localhost", "127.0.0.1", ""]:
            try:
                # 检查 ttyd 是否安装
                result = subprocess.run(
                    ["which", "ttyd"],
                    capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.warning("ttyd not found, Web Terminal will not be available")
                else:
                    # 启动 ttyd 服务
                    self.ttyd_process = subprocess.Popen(
                        ["ttyd", "-p", str(self.hs_config.remote_port), "-W", "bash"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                    logger.info(f"ttyd Web Terminal started on port {self.hs_config.remote_port}")
            except Exception as e:
                logger.warning(f"Failed to start ttyd: {str(e)}")
        
        # 通用操作 =============================================================
        return super().HSLoader()

    # 卸载宿主机 ###############################################################
    def HSUnload(self) -> ZMessage:
        # 专用操作 =============================================================
        # 停止 ttyd 服务
        if self.ttyd_process:
            try:
                self.ttyd_process.terminate()
                self.ttyd_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ttyd_process.kill()
            finally:
                self.ttyd_process = None
                logger.info("ttyd Web Terminal stopped")
        
        # 断开 LXD 连接
        self.lxd_client = None
        
        # 通用操作 =============================================================
        return super().HSUnload()

    # 虚拟机列出 ###############################################################
    def VMStatus(self, vm_name: str = "") -> dict[str, list[HWStatus]]:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().VMStatus(vm_name)

    # 虚拟机扫描 ###############################################################
    def VScanner(self) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result
        
        try:
            # 获取所有容器列表
            containers = client.containers.all()
            
            # 使用主机配置的filter_name作为前缀过滤
            filter_prefix = self.hs_config.filter_name if self.hs_config else ""
            
            scanned_count = 0
            added_count = 0
            
            for container in containers:
                container_name = container.name
                
                # 前缀过滤
                if filter_prefix and not container_name.startswith(filter_prefix):
                    continue
                
                scanned_count += 1
                
                # 检查是否已存在
                if container_name in self.vm_saving:
                    continue
                
                # 创建默认虚拟机配置
                default_vm_config = VMConfig()
                default_vm_config.vm_uuid = container_name
                
                # 添加到服务器的虚拟机配置中
                self.vm_saving[container_name] = default_vm_config
                added_count += 1
                
                # 记录日志
                log_msg = ZMessage(
                    success=True,
                    action="VScanner",
                    message=f"发现并添加容器: {container_name}",
                    results={"container_name": container_name}
                )
                self.LogStack(log_msg)
            
            # 保存到数据库
            if added_count > 0:
                success = self.data_set()
                if not success:
                    return ZMessage(
                        success=False, action="VScanner",
                        message="Failed to save scanned containers to database")
            
            return ZMessage(
                success=True,
                action="VScanner",
                message=f"扫描完成。共扫描到{scanned_count}个容器，新增{added_count}个容器配置。",
                results={
                    "scanned": scanned_count,
                    "added": added_count,
                    "prefix_filter": filter_prefix
                }
            )
        
        except Exception as e:
            return ZMessage(
                success=False, action="VScanner",
                message=f"扫描容器时出错: {str(e)}")

    # 创建虚拟机 ###############################################################
    def VMCreate(self, vm_conf: VMConfig) -> ZMessage:
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.NCCreate(vm_conf, True)
        
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result
        
        try:
            container_name = vm_conf.vm_uuid
            
            # 检查容器是否已存在
            try:
                client.containers.get(container_name)
                return ZMessage(
                    success=False, action="VMCreate",
                    message=f"Container {container_name} already exists")
            except NotFound:
                pass  # 容器不存在，继续创建
            
            # 创建容器配置
            config = {
                "name": container_name,
                "source": {
                    "type": "none"  # 先创建空容器，稍后安装系统
                },
                "config": self._build_container_config(vm_conf),
                "devices": self._build_container_devices(vm_conf)
            }
            
            # 创建容器
            container = client.containers.create(config, wait=True)
            
            # 安装系统（从模板）
            install_result = self.VInstall(vm_conf)
            if not install_result.success:
                # 清理失败的容器
                container.delete(wait=True)
                raise Exception(f"Failed to install system: {install_result.message}")
            
            # 启动容器
            container.start(wait=True)
            
            logger.info(f"Container {container_name} created successfully")
            
        except Exception as e:
            hs_result = ZMessage(
                success=False, action="VMCreate",
                message=f"容器创建失败: {str(e)}")
            self.logs_set(hs_result)
            return hs_result
        
        # 通用操作 =============================================================
        return super().VMCreate(vm_conf)

    # 构建容器配置 #############################################################
    def _build_container_config(self, vm_conf: VMConfig) -> dict:
        """构建 LXD 容器配置"""
        config = {
            "security.nesting": "true",
            "security.privileged": "false"  # 非特权容器
        }
        
        # CPU 限制
        if vm_conf.cpu_num > 0:
            config["limits.cpu"] = str(vm_conf.cpu_num)
        
        # 内存限制
        if vm_conf.ram_num > 0:
            config["limits.memory"] = f"{vm_conf.ram_num}GB"
        
        return config

    # 构建容器设备 #############################################################
    def _build_container_devices(self, vm_conf: VMConfig) -> dict:
        """构建 LXD 容器设备配置"""
        devices = {}
        
        # 网络设备
        nic_index = 0
        for nic_name, nic_config in vm_conf.nic_all.items():
            # 选择网桥（根据配置选择 nat 或 pub）
            bridge = self.hs_config.network_nat
            # 可以根据某些条件选择 network_pub
            # 例如：if nic_config.is_public: bridge = self.hs_config.network_pub
            
            device_name = f"eth{nic_index}"
            devices[device_name] = {
                "type": "nic",
                "nictype": "bridged",
                "parent": bridge,
                "name": device_name
            }
            
            if nic_config.mac_addr:
                devices[device_name]["hwaddr"] = nic_config.mac_addr
            
            if nic_config.ip4_addr:
                devices[device_name]["ipv4.address"] = nic_config.ip4_addr
            
            nic_index += 1
        
        # 根文件系统
        devices["root"] = {
            "type": "disk",
            "path": "/",
            "pool": "default"  # 使用默认存储池
        }
        
        # 如果指定了硬盘大小
        if vm_conf.hdd_num > 0:
            devices["root"]["size"] = f"{vm_conf.hdd_num}GB"
        
        return devices

    # 安装虚拟机 ###############################################################
    def VInstall(self, vm_conf: VMConfig) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result
        
        try:
            # 模板文件路径
            template_file = os.path.join(self.hs_config.images_path, vm_conf.os_name)
            
            if not os.path.exists(template_file):
                return ZMessage(
                    success=False, action="VInstall",
                    message=f"Template file not found: {template_file}")
            
            container_name = vm_conf.vm_uuid
            container = client.containers.get(container_name)
            
            # 停止容器（如果正在运行）
            if container.status == "Running":
                container.stop(wait=True)
            
            # 上传并解压模板到容器
            logger.info(f"Installing template {template_file} to container {container_name}")
            
            # 读取 tar.gz 文件并推送到容器
            with open(template_file, "rb") as f:
                container.files.put("/", f.read())
            
            logger.info(f"Template installed successfully")
            
            return ZMessage(success=True, action="VInstall")
            
        except Exception as e:
            return ZMessage(
                success=False, action="VInstall",
                message=f"Failed to install system: {str(e)}")

    # 配置虚拟机 ###############################################################
    def VMUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.NCCreate(vm_conf, True)
        
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result
        
        try:
            container_name = vm_conf.vm_uuid
            container = client.containers.get(container_name)
            
            # 停止容器
            if container.status == "Running":
                self.VMPowers(container_name, VMPowers.H_CLOSE)
            
            # 重装系统（如果系统镜像改变）
            if vm_conf.os_name != vm_last.os_name and vm_last.os_name != "":
                install_result = self.VInstall(vm_conf)
                if not install_result.success:
                    return install_result
            
            # 更新网络配置
            network_result = self.NCUpdate(vm_conf, vm_last)
            if not network_result.success:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"网络配置更新失败: {network_result.message}")
            
            # 更新容器配置
            container.config.update(self._build_container_config(vm_conf))
            container.devices.update(self._build_container_devices(vm_conf))
            container.save(wait=True)
            
            # 启动容器
            start_result = self.VMPowers(container_name, VMPowers.S_START)
            if not start_result.success:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"容器启动失败: {start_result.message}")
            
        except Exception as e:
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"容器更新失败: {str(e)}")
        
        # 通用操作 =============================================================
        return super().VMUpdate(vm_conf, vm_last)

    # 删除虚拟机 ###############################################################
    def VMDelete(self, vm_name: str) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result
        
        try:
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False, action="VMDelete",
                    message=f"容器 {vm_name} 不存在")
            
            container = client.containers.get(vm_name)
            
            # 停止容器
            if container.status == "Running":
                self.VMPowers(vm_name, VMPowers.H_CLOSE)
            
            # 删除网络配置
            self.NCCreate(vm_conf, False)
            
            # 删除容器
            container.delete(wait=True)
            
            logger.info(f"Container {vm_name} deleted successfully")
            
        except NotFound:
            logger.warning(f"Container {vm_name} not found in LXD")
        except Exception as e:
            return ZMessage(
                success=False, action="VMDelete",
                message=f"删除容器失败: {str(e)}")
        
        # 通用操作 =============================================================
        return super().VMDelete(vm_name)

    # 虚拟机电源 ###############################################################
    def VMPowers(self, vm_name: str, power: VMPowers) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result
        
        try:
            container = client.containers.get(vm_name)
            
            if power == VMPowers.S_START:
                if container.status != "Running":
                    container.start(wait=True)
                    logger.info(f"Container {vm_name} started")
                else:
                    logger.info(f"Container {vm_name} is already running")
            
            elif power == VMPowers.H_CLOSE:
                if container.status == "Running":
                    container.stop(wait=True, force=True)
                    logger.info(f"Container {vm_name} stopped")
                else:
                    logger.info(f"Container {vm_name} is already stopped")
            
            elif power == VMPowers.S_RESET or power == VMPowers.H_RESET:
                if container.status == "Running":
                    container.restart(wait=True)
                else:
                    container.start(wait=True)
                logger.info(f"Container {vm_name} restarted")
            
            hs_result = ZMessage(success=True, action="VMPowers")
            self.logs_set(hs_result)
            
        except NotFound:
            hs_result = ZMessage(
                success=False, action="VMPowers",
                message=f"Container {vm_name} does not exist")
            self.logs_set(hs_result)
            return hs_result
        except Exception as e:
            hs_result = ZMessage(
                success=False, action="VMPowers",
                message=f"电源操作失败: {str(e)}")
            self.logs_set(hs_result)
            return hs_result
        
        # 通用操作 =============================================================
        super().VMPowers(vm_name, power)
        return hs_result

    # 设置虚拟机密码 ###########################################################
    def Password(self, vm_name: str, os_pass: str) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result
        
        try:
            container = client.containers.get(vm_name)
            
            if container.status != "Running":
                return ZMessage(
                    success=False, action="Password",
                    message=f"Container {vm_name} is not running")
            
            # 执行命令设置密码
            command = ["chpasswd"]
            stdin_data = f"root:{os_pass}\n"
            
            result = container.execute(
                command,
                stdin_payload=stdin_data,
                stdin_raw=True
            )
            
            if result.exit_code != 0:
                raise Exception(f"chpasswd command failed: {result.stderr}")
            
            logger.info(f"Password set for container {vm_name}")
            
            return ZMessage(success=True, action="Password")
            
        except NotFound:
            return ZMessage(
                success=False, action="Password",
                message=f"Container {vm_name} does not exist")
        except Exception as e:
            return ZMessage(
                success=False, action="Password",
                message=f"设置密码失败: {str(e)}")

    # 备份虚拟机 ###############################################################
    def VMBackup(self, vm_name: str, vm_tips: str) -> ZMessage:
        # 专用操作 =============================================================
        # 使用 BaseServer 的备份逻辑（7z 压缩）
        # 通用操作 =============================================================
        return super().VMBackup(vm_name, vm_tips)

    # 恢复虚拟机 ###############################################################
    def Restores(self, vm_name: str, vm_back: str) -> ZMessage:
        # 专用操作 =============================================================
        # 使用 BaseServer 的恢复逻辑（7z 解压）
        # 通用操作 =============================================================
        return super().Restores(vm_name, vm_back)

    # VM镜像挂载 ###############################################################
    def HDDMount(self, vm_name: str, vm_imgs: SDConfig, in_flag=True) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_lxd()
        if not result.success:
            return result
        
        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="HDDMount",
                    message="容器不存在")
            
            container = client.containers.get(vm_name)
            
            # 停止容器
            was_running = container.status == "Running"
            if was_running:
                self.VMPowers(vm_name, VMPowers.H_CLOSE)
            
            # 挂载点路径
            host_path = os.path.join(self.hs_config.extern_path, vm_imgs.hdd_name)
            container_path = f"/mnt/{vm_imgs.hdd_name}"
            
            if in_flag:
                # 挂载磁盘
                # 确保主机路径存在
                os.makedirs(host_path, exist_ok=True)
                
                # 添加磁盘设备
                device_name = f"disk-{vm_imgs.hdd_name}"
                container.devices[device_name] = {
                    "type": "disk",
                    "source": host_path,
                    "path": container_path
                }
                container.save(wait=True)
                
                vm_imgs.hdd_flag = 1
                self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name] = vm_imgs
                
                logger.info(f"Mounted {host_path} to container {vm_name} at {container_path}")
            else:
                # 卸载磁盘
                device_name = f"disk-{vm_imgs.hdd_name}"
                if device_name in container.devices:
                    del container.devices[device_name]
                    container.save(wait=True)
                
                if vm_imgs.hdd_name in self.vm_saving[vm_name].hdd_all:
                    self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name].hdd_flag = 0
                
                logger.info(f"Unmounted {host_path} from container {vm_name}")
            
            # 保存配置
            old_conf = deepcopy(self.vm_saving[vm_name])
            self.VMUpdate(self.vm_saving[vm_name], old_conf)
            self.data_set()
            
            # 重启容器（如果之前在运行）
            if was_running:
                self.VMPowers(vm_name, VMPowers.S_START)
            
            action_text = "挂载" if in_flag else "卸载"
            return ZMessage(
                success=True, action="HDDMount",
                message=f"磁盘{action_text}成功")
            
        except NotFound:
            return ZMessage(
                success=False, action="HDDMount",
                message=f"Container {vm_name} does not exist")
        except Exception as e:
            return ZMessage(
                success=False, action="HDDMount",
                message=f"磁盘挂载操作失败: {str(e)}")

    # ISO镜像挂载 ##############################################################
    def ISOMount(self, vm_name: str, vm_imgs: IMConfig, in_flag=True) -> ZMessage:
        # 专用操作 =============================================================
        # LXD 容器不需要 ISO 挂载，返回成功但不执行操作
        return ZMessage(
            success=True, action="ISOMount",
            message="LXD containers do not support ISO mounting")

    # 虚拟机控制台 ##############################################################
    def VCRemote(self, vm_uuid: str, ip_addr: str = "127.0.0.1") -> str:
        """生成 Web Terminal 访问 URL"""
        if vm_uuid not in self.vm_saving:
            return ""
        
        # 对于远程 LXD，返回 LXD 控制台 URL
        if self.hs_config.server_addr not in ["localhost", "127.0.0.1", ""]:
            # 使用 LXD 的 Web 控制台
            public_addr = self.hs_config.public_addr[0] if self.hs_config.public_addr else self.hs_config.server_addr
            # LXD 控制台 URL 格式
            url = f"https://{public_addr}:8443/1.0/containers/{vm_uuid}/console"
            return url
        
        # 本地模式使用 ttyd
        if not self.ttyd_process:
            logger.warning("ttyd service is not running")
            return ""
        
        # 生成随机 token
        rand_token = ''.join(random.sample(string.ascii_letters + string.digits, 32))
        self.ttyd_tokens[vm_uuid] = rand_token
        
        # 构造访问 URL
        public_addr = self.hs_config.public_addr[0] if self.hs_config.public_addr else "127.0.0.1"
        
        # 使用 lxc exec 连接到容器
        url = f"http://{public_addr}:{self.hs_config.remote_port}/" \
              f"?arg=lxc&arg=exec&arg={vm_uuid}&arg=--&arg=/bin/bash&token={rand_token}"
        
        return url

    # 加载备份 #################################################################
    def LDBackup(self, vm_back: str = "") -> ZMessage:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().LDBackup(vm_back)

    # 移除备份 #################################################################
    def RMBackup(self, vm_back: str) -> ZMessage:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().RMBackup(vm_back)

    # 移除磁盘 #################################################################
    def RMMounts(self, vm_name: str, vm_imgs: str) -> ZMessage:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().RMMounts(vm_name, vm_imgs)

    # 查找显卡 #################################################################
    def GPUShows(self) -> dict[str, str]:
        # 专用操作 =============================================================
        # LXD 容器不需要 GPU 管理，返回空字典
        # 通用操作 =============================================================
        return {}
