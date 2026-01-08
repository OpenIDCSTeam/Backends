import os
import random
import subprocess
from loguru import logger

try:
    import docker
    from docker.errors import DockerException, NotFound, APIError
    from docker.types import Mount
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logger.warning("docker SDK not available, Docker functionality will be disabled")

from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Public.ZMessage import ZMessage
from HostModule.SSHDManager import SSHDManager


class OCIConnects:
    """Docker/OpenContainer Initiative 容器操作API封装类"""

    def __init__(self, hs_config: HSConfig):
        """
        初始化 OCI 容器 API
        
        :param hs_config: 宿主机配置对象
        """
        self.hs_config = hs_config
        self.docker_client = None
        self.ssh_forward = SSHDManager()
    
    # 连接到 Docker 服务器 #####################################################
    def connect_docker(self) -> tuple[docker.DockerClient | None, ZMessage]:
        """
        连接到 Docker 服务器（支持本地、远程TCP和SSH转发）
        :return: (Docker客户端对象, 操作结果消息)
        """
        if not DOCKER_AVAILABLE:
            return None, ZMessage(
                success=False, action="connect_docker",
                message="docker SDK is not installed")
        
        try:
            # 如果已经连接，直接返回
            if self.docker_client is not None:
                return self.docker_client, ZMessage(success=True, action="connect_docker")
            
            # 判断连接方式
            server_addr = self.hs_config.server_addr
            
            # SSH 转发模式
            if server_addr.startswith("ssh://"):
                return self._connect_via_ssh(server_addr)
            
            # 本地连接模式
            elif server_addr in ["localhost", "127.0.0.1", ""]:
                logger.info("Connecting to local Docker server")
                self.docker_client = docker.from_env()
            
            # 远程 TLS 连接模式
            else:
                return self._connect_via_tls(server_addr)
            
            # 测试连接
            self.docker_client.ping()
            logger.info("Successfully connected to Docker server")
            
            return self.docker_client, ZMessage(success=True, action="connect_docker")
            
        except Exception as e:
            logger.error(f"Failed to connect to Docker server: {str(e)}")
            self.docker_client = None
            self.ssh_forward.close()
            return None, ZMessage(
                success=False, action="connect_docker",
                message=f"Failed to connect to Docker: {str(e)}")

    # 通过SSH转发连接 #########################################################
    def _connect_via_ssh(self, server_addr: str) -> tuple[docker.DockerClient | None, ZMessage]:
        """
        通过SSH转发连接到远程Docker
        :param server_addr: SSH服务器地址（格式: ssh://hostname）
        :return: (Docker客户端对象, 操作结果消息)
        """
        try:
            from HostModule.SSHDManager import SSHDManager
            PARAMIKO_AVAILABLE = True
        except ImportError:
            PARAMIKO_AVAILABLE = False
            logger.warning("paramiko not available, remote SSH execution will be disabled")
        
        if not PARAMIKO_AVAILABLE:
            return None, ZMessage(
                success=False, action="connect_docker",
                message="SSH 转发需要 paramiko 库，但未安装")
        
        # 提取 SSH 主机地址（去掉 ssh:// 前缀）
        ssh_hostname = server_addr.replace("ssh://", "")
        
        logger.info(f"使用 SSH 转发连接 Docker: {ssh_hostname}")
        
        # 建立 SSH 连接
        success, message = self.ssh_forward.connect(
            hostname=ssh_hostname,
            username=self.hs_config.server_user,
            password=self.hs_config.server_pass,
            port=22
        )
        
        if not success:
            return None, ZMessage(
                success=False, action="connect_docker",
                message=f"SSH 连接失败: {message}")
        
        # 启动端口转发：远程 2376 -> 本地随机端口
        success, message, local_port = self.ssh_forward.start_port_forward(
            remote_port=2376,
            local_port_range=(9000, 9999),
            remote_host="127.0.0.1"
        )
        
        if not success:
            self.ssh_forward.close()
            return None, ZMessage(
                success=False, action="connect_docker",
                message=f"端口转发失败: {message}")
        
        logger.info(f"SSH 端口转发已建立: 本地 127.0.0.1:{local_port} -> {ssh_hostname}:2376")
        
        # 连接到本地转发的端口
        self.docker_client = docker.DockerClient(
            base_url=f"tcp://127.0.0.1:{local_port}",
            timeout=60
        )
        
        return self.docker_client, ZMessage(success=True, action="connect_docker")

    # 通过TLS连接远程Docker ####################################################
    def _connect_via_tls(self, server_addr: str) -> tuple[docker.DockerClient | None, ZMessage]:
        """
        通过TLS连接到远程Docker
        :param server_addr: 远程服务器地址
        :return: (Docker客户端对象, 操作结果消息)
        """
        # 远程连接（使用 TLS）
        endpoint = server_addr
        if not endpoint.startswith("tcp://"):
            endpoint = f"tcp://{endpoint}"
        if not endpoint.endswith(":2376"):
            endpoint += ":2376"
        logger.info(f"Connecting to remote Docker server: {endpoint}")
        
        # 证书路径（从 launch_path 获取）
        ca_cert = os.path.join(self.hs_config.launch_path, "ca.pem")
        client_cert = os.path.join(self.hs_config.launch_path, "client-cert.pem")
        client_key = os.path.join(self.hs_config.launch_path, "client-key.pem")
        
        if not os.path.exists(ca_cert) or not os.path.exists(client_cert) or not os.path.exists(client_key):
            return None, ZMessage(
                success=False, action="connect_docker",
                message=f"TLS certificates not found in {self.hs_config.launch_path}")
        
        # 配置 TLS
        tls_config = docker.tls.TLSConfig(
            client_cert=(client_cert, client_key),
            ca_cert=ca_cert,
            verify=True
        )
        
        self.docker_client = docker.DockerClient(
            base_url=endpoint,
            tls=tls_config
        )
        
        return self.docker_client, ZMessage(success=True, action="connect_docker")

    # 断开Docker连接 ##########################################################
    def disconnect_docker(self) -> ZMessage:
        """
        断开Docker连接
        :return: 操作结果消息
        """
        if self.docker_client:
            self.docker_client.close()
            self.docker_client = None
        if self.ssh_forward:
            self.ssh_forward.close()
        return ZMessage(success=True, action="disconnect_docker", message="Docker连接已断开")

    # 构建容器配置 #############################################################
    def build_container_config(self, vm_conf: VMConfig) -> dict:
        """
        构建 Docker 容器配置
        :param vm_conf: 虚拟机配置对象
        :return: 容器配置字典
        """
        config = {
            "environment": {},
            "volumes": {},
            "network_mode": "bridge"
        }
        
        # CPU 限制
        if vm_conf.cpu_num > 0:
            config["nano_cpus"] = int(vm_conf.cpu_num * 1e9)
        
        # 内存限制
        if vm_conf.mem_num > 0:
            config["mem_limit"] = f"{vm_conf.mem_num}g"
        
        # 网络配置
        nic_index = 0
        for nic_name, nic_config in vm_conf.nic_all.items():
            # 根据配置选择网桥
            if nic_index == 0:
                # 设置 MAC 地址
                if nic_config.mac_addr:
                    config["mac_address"] = nic_config.mac_addr
                
                # 设置网络（使用 network_nat 或 network_pub）
                bridge = self.hs_config.network_nat
                if bridge:
                    config["network"] = bridge
            
            nic_index += 1
        
        return config

    # 加载/拉取镜像 ############################################################
    def load_or_pull_image(self, vm_conf: VMConfig) -> ZMessage:
        """
        加载或拉取Docker镜像
        :param vm_conf: 虚拟机配置对象（包含os_name）
        :return: 操作结果消息
        """
        client, result = self.connect_docker()
        if not result.success:
            return result
        
        try:
            image_name = vm_conf.os_name
            
            # 判断是否为 tar/tar.gz 文件
            if image_name.endswith('.tar') or image_name.endswith('.tar.gz'):
                # 从本地 tar 文件加载镜像
                image_file = os.path.join(self.hs_config.images_path, image_name)
                
                if not os.path.exists(image_file):
                    return ZMessage(
                        success=False, action="load_image",
                        message=f"Image file not found: {image_file}")
                
                logger.info(f"Loading image from {image_file}")
                
                with open(image_file, 'rb') as f:
                    client.images.load(f.read())
                
                # 获取加载的镜像名称（从 tar 中提取）
                vm_conf.os_name = image_name.replace('.tar.gz', '').replace('.tar', '')
                
                logger.info(f"Image loaded successfully: {vm_conf.os_name}")
            else:
                # 从 Docker Hub 或本地镜像库加载
                try:
                    # 先检查本地是否存在
                    client.images.get(image_name)
                    logger.info(f"Image {image_name} already exists locally")
                except NotFound:
                    # 本地不存在，尝试拉取
                    logger.info(f"Pulling image {image_name} from registry")
                    client.images.pull(image_name)
                    logger.info(f"Image {image_name} pulled successfully")
            
            return ZMessage(success=True, action="load_image")
            
        except Exception as e:
            return ZMessage(
                success=False, action="load_image",
                message=f"Failed to load image: {str(e)}")

    # 获取所有容器列表 ##########################################################
    def list_containers(self, all_containers: bool = True) -> list:
        """
        获取所有容器列表
        :param all_containers: 是否包含停止的容器
        :return: 容器列表
        """
        client, result = self.connect_docker()
        if not result.success:
            return []
        
        try:
            containers = client.containers.list(all=all_containers)
            return containers
        except Exception as e:
            logger.error(f"Failed to list containers: {str(e)}")
            return []

    # 获取容器对象 ##############################################################
    def get_container(self, container_name: str):
        """
        获取指定容器对象
        :param container_name: 容器名称
        :return: 容器对象，不存在返回None
        """
        client, result = self.connect_docker()
        if not result.success:
            return None
        
        try:
            return client.containers.get(container_name)
        except NotFound:
            return None
        except Exception as e:
            logger.error(f"Failed to get container {container_name}: {str(e)}")
            return None

    # 创建容器 ##################################################################
    def create_container(self, vm_conf: VMConfig) -> ZMessage:
        """
        创建Docker容器
        :param vm_conf: 虚拟机配置对象
        :return: 操作结果消息
        """
        client, result = self.connect_docker()
        if not result.success:
            return result
        
        try:
            container_name = vm_conf.vm_uuid
            
            # 检查容器是否已存在
            if self.get_container(container_name):
                return ZMessage(
                    success=False, action="create_container",
                    message=f"Container {container_name} already exists")
            
            # 先加载镜像
            install_result = self.load_or_pull_image(vm_conf)
            if not install_result.success:
                return ZMessage(
                    success=False, action="create_container",
                    message=f"Failed to load image: {install_result.message}")
            
            # 构建容器配置
            container_config = self.build_container_config(vm_conf)
            
            # 创建容器
            container = client.containers.create(
                image=vm_conf.os_name,
                name=container_name,
                detach=True,
                hostname=container_name,
                **container_config
            )
            
            # 启动容器
            container.start()
            
            logger.info(f"Container {container_name} created successfully")
            
            return ZMessage(success=True, action="create_container", 
                          message=f"容器 {container_name} 创建成功")
            
        except Exception as e:
            logger.error(f"Failed to create container: {str(e)}")
            return ZMessage(
                success=False, action="create_container",
                message=f"容器创建失败: {str(e)}")

    # 删除容器 ##################################################################
    def remove_container(self, container_name: str, force: bool = True) -> ZMessage:
        """
        删除Docker容器
        :param container_name: 容器名称
        :param force: 是否强制删除
        :return: 操作结果消息
        """
        container = self.get_container(container_name)
        if not container:
            return ZMessage(
                success=False, action="remove_container",
                message=f"Container {container_name} does not exist")
        
        try:
            # 停止容器（如果正在运行）
            if container.status == "running":
                container.stop(timeout=10)
            
            # 删除容器
            container.remove(v=True, force=force)
            
            logger.info(f"Container {container_name} deleted successfully")
            
            return ZMessage(success=True, action="remove_container", 
                          message=f"容器 {container_name} 删除成功")
            
        except Exception as e:
            logger.error(f"Failed to remove container: {str(e)}")
            return ZMessage(
                success=False, action="remove_container",
                message=f"删除容器失败: {str(e)}")

    # 电源操作 ##################################################################
    def power_operation(self, container_name: str, action: str) -> ZMessage:
        """
        执行容器电源操作
        :param container_name: 容器名称
        :param action: 操作类型 (start, stop, restart)
        :return: 操作结果消息
        """
        container = self.get_container(container_name)
        if not container:
            return ZMessage(
                success=False, action="power_operation",
                message=f"Container {container_name} does not exist")
        
        try:
            if action == "start":
                if container.status != "running":
                    container.start()
                    logger.info(f"Container {container_name} started")
                else:
                    logger.info(f"Container {container_name} is already running")
            
            elif action == "stop":
                if container.status == "running":
                    container.stop(timeout=10)
                    logger.info(f"Container {container_name} stopped")
                else:
                    logger.info(f"Container {container_name} is already stopped")
            
            elif action == "restart":
                if container.status == "running":
                    container.restart(timeout=10)
                else:
                    container.start()
                logger.info(f"Container {container_name} restarted")
            
            return ZMessage(success=True, action="power_operation", 
                          message=f"容器 {container_name} {action} 操作成功")
            
        except Exception as e:
            logger.error(f"Failed to {action} container: {str(e)}")
            return ZMessage(
                success=False, action="power_operation",
                message=f"电源操作失败: {str(e)}")

    # 在容器中执行命令 ##########################################################
    def exec_command(self, container_name: str, cmd: list[str]) -> tuple[int, str]:
        """
        在容器中执行命令
        :param container_name: 容器名称
        :param cmd: 命令列表
        :return: (退出码, 输出内容)
        """
        container = self.get_container(container_name)
        if not container:
            return -1, f"Container {container_name} does not exist"
        
        try:
            if container.status != "running":
                return -1, f"Container {container_name} is not running"
            
            exec_result = container.exec_run(cmd=cmd)
            return exec_result.exit_code, exec_result.output.decode()
            
        except Exception as e:
            logger.error(f"Failed to exec command: {str(e)}")
            return -1, str(e)

    # 设置容器密码 ##############################################################
    def set_password(self, container_name: str, password: str) -> ZMessage:
        """
        设置容器root密码
        :param container_name: 容器名称
        :param password: 新密码
        :return: 操作结果消息
        """
        exit_code, output = self.exec_command(
            container_name,
            ["sh", "-c", f"echo 'root:{password}' | chpasswd"]
        )
        
        if exit_code != 0:
            return ZMessage(
                success=False, action="set_password",
                message=f"设置密码失败: {output}")
        
        logger.info(f"Password set for container {container_name}")
        return ZMessage(success=True, action="set_password", 
                      message="密码设置成功")

    # 重新创建容器（带新的挂载配置）############################################
    def recreate_with_mounts(self, container_name: str, vm_conf: VMConfig, 
                             was_running: bool = False) -> ZMessage:
        """
        重新创建容器（用于添加/移除挂载卷）
        :param container_name: 容器名称
        :param vm_conf: 虚拟机配置对象
        :param was_running: 容器之前是否在运行
        :return: 操作结果消息
        """
        client, result = self.connect_docker()
        if not result.success:
            return result
        
        try:
            # 获取容器
            container = self.get_container(container_name)
            if not container:
                return ZMessage(
                    success=False, action="recreate_container",
                    message=f"Container {container_name} does not exist")
            
            # 停止并删除旧容器
            if container.status == "running":
                container.stop(timeout=10)
            container.remove(force=True)
            
            # 构建新的容器配置
            container_config = self.build_container_config(vm_conf)
            
            # 添加挂载卷
            volumes = {}
            for hdd_name, hdd_conf in vm_conf.hdd_all.items():
                if hdd_conf.hdd_flag == 1:
                    h_path = os.path.join(self.hs_config.extern_path, hdd_name)
                    c_path = f"/mnt/{hdd_name}"
                    volumes[h_path] = {'bind': c_path, 'mode': 'rw'}
            
            if volumes:
                container_config['volumes'] = volumes
            
            # 重新创建容器
            container = client.containers.create(
                image=vm_conf.os_name,
                name=container_name,
                detach=True,
                hostname=container_name,
                **container_config
            )
            
            # 如果之前在运行，重启容器
            if was_running:
                container.start()
            
            return ZMessage(success=True, action="recreate_container", 
                          message="容器重新创建成功")
            
        except Exception as e:
            logger.error(f"Failed to recreate container: {str(e)}")
            return ZMessage(
                success=False, action="recreate_container",
                message=f"容器重新创建失败: {str(e)}")

    # 获取容器IP地址 ##########################################################
    def get_container_ip(self, container_name: str) -> str | None:
        """
        获取容器的IP地址
        :param container_name: 容器名称
        :return: IP地址，获取失败返回None
        """
        container = self.get_container(container_name)
        if not container:
            return None
        
        try:
            container.reload()  # 刷新容器状态
            # 从容器网络配置中获取IP地址
            networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
            for net_name, net_config in networks.items():
                ip = net_config.get('IPAddress')
                if ip:
                    return ip
        except Exception as e:
            logger.warning(f"Failed to get container IP: {str(e)}")
        
        return None

    # 扫描容器 ##################################################################
    def scan_containers(self, filter_prefix: str = "") -> list[str]:
        """
        扫描所有容器（用于VScanner）
        :param filter_prefix: 容器名称前缀过滤
        :return: 容器名称列表
        """
        containers = self.list_containers(all_containers=True)
        container_names = []
        
        for container in containers:
            container_name = container.name
            
            # 前缀过滤
            if filter_prefix and not container_name.startswith(filter_prefix):
                continue
            
            container_names.append(container_name)
        
        return container_names

    # 检查容器是否存在 ##########################################################
    def container_exists(self, container_name: str) -> bool:
        """
        检查容器是否存在
        :param container_name: 容器名称
        :return: 是否存在
        """
        return self.get_container(container_name) is not None
