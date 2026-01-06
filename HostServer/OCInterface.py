import os
import random
import traceback
from loguru import logger
from pyexpat.errors import messages

from MainObject.Config.PortData import PortData

from HostServer.BasicServer import BasicServer
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.IMConfig import IMConfig
from MainObject.Config.SDConfig import SDConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from HostServer.OCInterfaceAPI import OCIConnects
from HostServer.OCInterfaceAPI.IPTablesAPI import IPTablesAPI
from HostServer.OCInterfaceAPI.SSHTerminal import SSHTerminal

try:
    from docker.errors import NotFound
except ImportError:
    NotFound = Exception  # Fallback if docker is not available


class HostServer(BasicServer):
    # 连接到 Docker 服务器 #####################################################
    def _connect_docker(self) -> tuple:
        if not self.oci_connects:
            self.oci_connects = OCIConnects(self.hs_config)

        return self.oci_connects.connect_docker()

    # 读取宿主机 ###############################################################
    def __init__(self, config: HSConfig, **kwargs):
        super().__init__(config, **kwargs)
        self.web_terminal = None
        self.oci_connects = None
        self.ssh_forwards = None
        self.http_manager = None

    def HSLoader(self) -> ZMessage:
        # 专用操作 =============================================================
        if not self.web_terminal:
            self.web_terminal = SSHTerminal(self.hs_config)

        # 初始化HttpManage，使用caddy_主机名.txt作为配置文件名
        if not self.http_manager:
            from HostModule.HttpManage import HttpManage
            # 获取主机名，使用server_name，如果没有则使用默认值
            hostname = getattr(self.hs_config, 'server_name', 'localhost')
            if not hostname:
                hostname = 'localhost'
            config_filename = f"vnc-{hostname}.txt"
            self.http_manager = HttpManage(config_filename)

        # 连接到 Docker 服务器 =================================================
        client, result = self._connect_docker()
        if not result.success:
            return result
        # 通用操作 =============================================================
        return super().HSLoader()

    def VMLoader(self) -> bool:
        pass

    # 卸载宿主机 ###############################################################
    def HSUnload(self) -> ZMessage:
        # 专用操作 =============================================================
        if self.web_terminal:
            self.web_terminal = None
        # 断开 Docker 连接 =====================================================
        if self.oci_connects:
            self.oci_connects.close()
            self.oci_connects = None
        # 关闭 SSH 转发连接 ====================================================
        if self.ssh_forwards:
            self.ssh_forwards.close()
        # 通用操作 =============================================================
        return super().HSUnload()

    # 虚拟机列出 ###############################################################
    def VMStatus(self, vm_name: str = "") -> dict[str, list[HWStatus]]:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return super().VMStatus(vm_name)

    # 虚拟机扫描 ###############################################################
    def VMDetect(self) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_docker()
        if not result.success:
            return result
        try:
            # 获取所有容器列表（包括停止的）
            containers = client.containers.list(all=True)
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
        client, result = self._connect_docker()
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

            # 先加载镜像
            install_result = self.VMSetups(vm_conf)
            if not install_result.success:
                raise Exception(f"Failed to load image: {install_result.message}")

            # 构建容器配置
            container_config, fixed_ip = self._build_container_config(vm_conf)

            # 获取网络名称
            network_name = container_config.get("network")

            # 创建容器（如果配置了固定IP，先创建但不连接网络）
            if fixed_ip and network_name:
                # 创建容器但不连接网络
                container = client.containers.create(
                    image=vm_conf.os_name,
                    name=container_name,
                    detach=True,
                    hostname=container_name,
                    mac_address=container_config.get("mac_address"),
                    environment=container_config.get("environment", {}),
                    volumes=container_config.get("volumes", {}),
                    ports=container_config.get("ports", {}),
                    nano_cpus=container_config.get("nano_cpus"),
                    mem_limit=container_config.get("mem_limit"),
                    cpu_shares=container_config.get("cpu_shares"),
                    stdin_open=container_config.get("stdin_open", True),
                    tty=container_config.get("tty", True),
                    privileged=container_config.get("privileged", True),
                    shm_size=container_config.get("shm_size", "1024m"),
                    cap_add=container_config.get("cap_add", ["SYS_ADMIN", "SYS_PTRACE"])
                )

                # 连接到网络并分配固定 IP
                try:
                    network = client.networks.get(network_name)
                    network.connect(container, ipv4_address=fixed_ip)
                    logger.info(f"Assigned fixed IP {fixed_ip} to container {container_name}")
                except Exception as ip_error:
                    logger.warning(f"Failed to assign fixed IP {fixed_ip}: {str(ip_error)}")
            else:
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

        except Exception as e:
            hs_result = ZMessage(
                success=False, action="VMCreate",
                message=f"容器创建失败: {str(e)}")
            traceback.print_exc()
            self.logs_set(hs_result)
            return hs_result

        # 通用操作 =============================================================
        return super().VMCreate(vm_conf)

    # 构建容器配置 #############################################################
    def _build_container_config(self, vm_conf: VMConfig) -> tuple[dict, str]:
        """构建 Docker 容器配置
        
        返回:
            tuple: (容器配置字典, 固定IP地址字符串)
        """
        config = {
            "environment": {},
            "volumes": {},
            "network_mode": "bridge",
            # 必需参数，使容器可以交互运行
            "stdin_open": True,  # -i: 保持 STDIN 打开
            "tty": True,  # -t: 分配伪终端
            # 特权模式，让容器拥有几乎与宿主机相同的权限
            "privileged": True,
            # 共享内存大小，避免某些应用运行问题
            "shm_size": "1024m",
            # 添加容器能力
            "cap_add": [
                "SYS_ADMIN",  # 系统管理权限
                "SYS_PTRACE"  # 进程调试权限
            ]
        }

        # CPU 限制
        if vm_conf.cpu_num > 0:
            config["nano_cpus"] = int(vm_conf.cpu_num * 1e9)

        # 内存限制 (转换为字节)
        if vm_conf.mem_num > 0:
            config["mem_limit"] = f"{vm_conf.mem_num}m"

        # CPU 份额（可选，用于相对权重）
        if vm_conf.cpu_per > 0:
            config["cpu_shares"] = int(vm_conf.cpu_per * 10)  # 2-1024 范围

        # 数据卷挂载配置
        container_name = vm_conf.vm_uuid
        if self.hs_config.extern_path:
            # 确保基础目录存在
            base_path = os.path.join(self.hs_config.extern_path, container_name)
            os.makedirs(os.path.join(base_path, "root"), exist_ok=True)
            os.makedirs(os.path.join(base_path, "user"), exist_ok=True)

            # 挂载 root 目录
            config["volumes"][os.path.join(base_path, "root")] = {
                "bind": "/root",
                "mode": "rw"
            }

            # 挂载 user 目录
            config["volumes"][os.path.join(base_path, "user")] = {
                "bind": "/home/user",
                "mode": "rw"
            }

            logger.info(f"Configured volumes for {container_name}:")
            logger.info(f"  {os.path.join(base_path, 'root')}:/root")
            logger.info(f"  {os.path.join(base_path, 'user')}:/home/user")

        # SSH端口映射配置（22端口映射到随机端口）
        # if self.hs_config.ports_start > 0 and self.hs_config.ports_close > 0:
        #     # 生成随机SSH端口映射
        #     import random
        #     ssh_port = random.randint(self.hs_config.ports_start, self.hs_config.ports_close)
        #
        #     # 添加端口映射：容器22端口 -> 宿主机随机端口
        #     config["ports"][22] = ssh_port
        #
        #     logger.info(f"Configured SSH port mapping for {container_name}: 22 -> {ssh_port}")
        # else:
        #     logger.warning(f"SSH port mapping not configured for {container_name}: ports_start/ports_close not set")

        # 网络配置
        fixed_ip = ""  # 固定IP地址
        nic_index = 0
        for nic_name, nic_config in vm_conf.nic_all.items():
            # 根据配置选择网桥
            if nic_index == 0:
                # 设置 MAC 地址
                if nic_config.mac_addr:
                    config["mac_address"] = nic_config.mac_addr

                # 保存固定 IP 地址（如果有）
                if nic_config.ip4_addr:
                    fixed_ip = nic_config.ip4_addr

                # 设置网络（使用 network_nat 或 network_pub）
                # 默认使用 nat 网络
                bridge = self.hs_config.network_nat if self.hs_config else ""
                if bridge:
                    config["network"] = bridge

                # 如果配置了固定IP，使用自定义网络模式
                if fixed_ip:
                    config["network_mode"] = None  # 移除默认的 bridge 模式

            nic_index += 1

        return config, fixed_ip

    # 安装虚拟机 ###############################################################
    def VMSetups(self, vm_conf: VMConfig) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_docker()
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
                        success=False, action="VInstall",
                        message=f"Image file not found: {image_file}")

                logger.info(f"Loading image from {image_file}")

                with open(image_file, 'rb') as f:
                    client.images.load(f.read())

                # 获取加载的镜像名称（从 tar 中提取）
                # 这里假设镜像名称与文件名相同（去掉后缀）
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

            return ZMessage(success=True, action="VInstall")

        except Exception as e:
            return ZMessage(
                success=False, action="VInstall",
                message=f"Failed to install image: {str(e)}")

    # 配置虚拟机 ###############################################################
    def VMUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.NCCreate(vm_conf, True)

        # 专用操作 =============================================================
        client, result = self._connect_docker()
        if not result.success:
            return result

        try:
            container_name = vm_conf.vm_uuid

            # 获取容器
            try:
                container = client.containers.get(container_name)
            except NotFound:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"Container {container_name} does not exist")

            # 重装系统（如果系统镜像改变）
            if vm_conf.os_name != vm_last.os_name and vm_last.os_name != "":
                # Docker 容器需要重建才能更换镜像
                # 停止并删除旧容器
                if container.status == "running":
                    self.VMPowers(container_name, VMPowers.H_CLOSE)
                container.remove()

                # 重新创建
                return self.VMCreate(vm_conf)

            # 检查是否需要更新资源配置
            cpu_changed = vm_conf.cpu_num != vm_last.cpu_num
            ram_changed = vm_conf.ram_num != vm_last.mem_num

            if cpu_changed or ram_changed:
                # 使用 docker update 接口动态更新容器资源限制
                update_kwargs = {}

                # CPU 限制
                if cpu_changed and vm_conf.cpu_num > 0:
                    update_kwargs['nano_cpus'] = int(vm_conf.cpu_num * 1e9)

                # 内存限制（转换为字节）
                if ram_changed and vm_conf.mem_num > 0:
                    update_kwargs['mem_limit'] = f"{vm_conf.mem_num}m"

                # 执行更新
                if update_kwargs:
                    container.update(**update_kwargs)
                    logger.info(f"容器 {container_name} 资源配置已更新: {update_kwargs}")

                # 如果容器正在运行，需要重启以应用资源限制变更
                if container.status == "running":
                    self.VMPowers(container_name, VMPowers.H_RESET)
                    logger.info(f"容器 {container_name} 已重启以应用资源限制")

            # 更新网络配置
            network_result = self.NCUpdate(vm_conf, vm_last)
            if not network_result.success:
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"网络配置更新失败: {network_result.message}")

            hs_result = ZMessage(
                success=True, action="VMUpdate",
                message=f"容器 {container_name} 配置更新成功")
            self.logs_set(hs_result)
            return hs_result

        except Exception as e:
            traceback.print_exc()
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"容器更新失败: {str(e)}")

        # 通用操作 =============================================================
        return super().VMUpdate(vm_conf, vm_last)

    # 删除虚拟机 ###############################################################
    def VMDelete(self, vm_name: str) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_docker()
        if not result.success:
            return result

        try:
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False, action="VMDelete",
                    message=f"容器 {vm_name} 不存在")

            try:
                container = client.containers.get(vm_name)

                # 停止容器
                if container.status == "running":
                    self.VMPowers(vm_name, VMPowers.H_CLOSE)

                # 删除容器（包括卷）
                container.remove(v=True, force=True)

                logger.info(f"Container {vm_name} deleted successfully")
            except NotFound:
                logger.warning(f"Container {vm_name} not found in Docker")

            # 删除网络配置
            self.NCCreate(vm_conf, False)

        except Exception as e:
            return ZMessage(
                success=False, action="VMDelete",
                message=f"删除容器失败: {str(e)}")

        # 通用操作 =============================================================
        return super().VMDelete(vm_name)

    # 虚拟机电源 ###############################################################
    def VMPowers(self, vm_name: str, power: VMPowers) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_docker()
        if not result.success:
            return result

        try:
            container = client.containers.get(vm_name)

            if power == VMPowers.S_START:
                if container.status != "running":
                    container.start()
                    logger.info(f"Container {vm_name} started")
                else:
                    logger.info(f"Container {vm_name} is already running")

            elif power == VMPowers.H_CLOSE:
                if container.status == "running":
                    container.stop(timeout=10)
                    logger.info(f"Container {vm_name} stopped")
                else:
                    logger.info(f"Container {vm_name} is already stopped")

            elif power == VMPowers.S_RESET or power == VMPowers.H_RESET:
                if container.status == "running":
                    container.restart(timeout=10)
                else:
                    container.start()
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
    def VMPasswd(self, vm_name: str, os_pass: str) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_docker()
        if not result.success:
            return result

        try:
            container = client.containers.get(vm_name)

            if container.status != "running":
                return ZMessage(
                    success=False, action="Password",
                    message=f"容器 {vm_name} 未运行，请先启动容器")

            # 执行命令设置root密码
            exec_result = container.exec_run(
                cmd=["sh", "-c", f"echo 'root:{os_pass}' | chpasswd"],
                stdin=True
            )

            if exec_result.exit_code != 0:
                output = exec_result.output.decode() if exec_result.output else "未知错误"
                return ZMessage(
                    success=False, action="Password",
                    message=f"设置密码失败: {output}")

            logger.info(f"容器 {vm_name} 的root密码已更新")

            hs_result = ZMessage(success=True, action="Password", message="密码设置成功")
            self.logs_set(hs_result)
            return hs_result

        except NotFound:
            return ZMessage(
                success=False, action="Password",
                message=f"容器 {vm_name} 不存在")
        except Exception as e:
            return ZMessage(
                success=False, action="Password",
                message=f"设置密码失败: {str(e)}")

    # 备份虚拟机 ###############################################################
    def VMBackup(self, vm_name: str, vm_tips: str) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_docker()
        if not result.success:
            return result

        try:
            # 获取容器
            container = client.containers.get(vm_name)

            # 检查容器是否正在运行
            was_running = container.status == "running"
            if was_running:
                # 先停止容器以确保数据一致性
                container.stop(timeout=30)
                logger.info(f"容器 {vm_name} 已停止，准备备份")

            # 构建备份文件名
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{vm_name}_{timestamp}.tar.gz"
            backup_path = os.path.join(self.hs_config.backup_path, backup_filename)

            # 确保备份目录存在
            os.makedirs(self.hs_config.backup_path, exist_ok=True)

            # 导出容器
            logger.info(f"开始备份容器 {vm_name} 到 {backup_path}")

            # 使用export导出容器文件系统（会自动处理tar.gz压缩）
            with open(backup_path, 'wb') as f:
                # 生成比特流并直接写入文件
                bits, stat = container.get_archive('/')
                for chunk in bits:
                    f.write(chunk)

            # 压缩为tar.gz（如果导出的是tar）
            if not backup_path.endswith('.tar.gz'):
                import gzip
                tar_gz_path = backup_path + '.gz'
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(tar_gz_path, 'wb') as f_out:
                        f_out.writelines(f_in)
                os.remove(backup_path)
                backup_path = tar_gz_path

            logger.info(f"容器 {vm_name} 备份完成，文件大小: {os.path.getsize(backup_path) / 1024 / 1024:.2f} MB")

            # 如果容器之前在运行，重新启动
            if was_running:
                container.start()
                logger.info(f"容器 {vm_name} 已重新启动")

            hs_result = ZMessage(
                success=True, action="VMBackup",
                message=f"容器备份成功，文件: {backup_filename}",
                results={"backup_file": backup_filename, "backup_path": backup_path}
            )
            self.logs_set(hs_result)
            return hs_result

        except NotFound:
            return ZMessage(
                success=False, action="VMBackup",
                message=f"容器 {vm_name} 不存在")
        except Exception as e:
            logger.error(f"备份容器失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="VMBackup",
                message=f"备份失败: {str(e)}")

    # 恢复虚拟机 ###############################################################
    def Restores(self, vm_name: str, vm_back: str) -> ZMessage:
        # 专用操作 =============================================================
        client, result = self._connect_docker()
        if not result.success:
            return result

        try:
            # 构建备份文件完整路径
            backup_file = os.path.join(self.hs_config.backup_path, vm_back)

            # 检查备份文件是否存在
            if not os.path.exists(backup_file):
                return ZMessage(
                    success=False, action="Restores",
                    message=f"备份文件不存在: {vm_back}")

            # 检查目标容器是否已存在
            try:
                existing_container = client.containers.get(vm_name)
                return ZMessage(
                    success=False, action="Restores",
                    message=f"容器 {vm_name} 已存在，请先删除或使用其他名称")
            except NotFound:
                pass  # 容器不存在，可以恢复

            logger.info(f"开始从备份恢复容器 {vm_name}，备份文件: {backup_file}")

            # 使用docker import导入tar.gz文件为镜像
            # 备份文件格式: container_name_timestamp.tar.gz
            # 需要解压tar.gz并使用docker load导入
            import tarfile
            import tempfile

            # 如果是tar.gz，先解压
            if backup_file.endswith('.tar.gz'):
                # 使用docker import直接导入tar.gz为镜像
                with open(backup_file, 'rb') as f:
                    # import_image会读取文件并创建镜像
                    image = client.images.load(f.read())[0]
                logger.info(f"从备份文件导入镜像: {image.id}")
            else:
                # 直接导入tar文件
                with open(backup_file, 'rb') as f:
                    image = client.images.load(f.read())[0]
                logger.info(f"从备份文件导入镜像: {image.id}")

            # 获取VM配置
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                # 如果配置不存在，使用镜像创建默认配置
                vm_conf = VMConfig()
                vm_conf.vm_uuid = vm_name
                vm_conf.os_name = image.id

            # 构建容器配置
            container_config, fixed_ip = self._build_container_config(vm_conf)

            # 获取网络名称
            network_name = container_config.get("network")

            # 创建容器
            if fixed_ip and network_name:
                # 创建容器但不连接网络
                container = client.containers.create(
                    image=image.id,
                    name=vm_name,
                    detach=True,
                    hostname=vm_name,
                    environment=container_config.get("environment", {}),
                    volumes=container_config.get("volumes", {}),
                    ports=container_config.get("ports", {}),
                    nano_cpus=container_config.get("nano_cpus"),
                    mem_limit=container_config.get("mem_limit"),
                    cpu_shares=container_config.get("cpu_shares"),
                    stdin_open=container_config.get("stdin_open", True),
                    tty=container_config.get("tty", True),
                    privileged=container_config.get("privileged", True),
                    shm_size=container_config.get("shm_size", "1024m"),
                    cap_add=container_config.get("cap_add", ["SYS_ADMIN", "SYS_PTRACE"])
                )

                # 连接到网络并分配固定 IP
                try:
                    network = client.networks.get(network_name)
                    network.connect(container, ipv4_address=fixed_ip)
                    logger.info(f"恢复容器 {vm_name} 并分配固定IP {fixed_ip}")
                except Exception as ip_error:
                    logger.warning(f"恢复容器时无法分配固定IP {fixed_ip}: {str(ip_error)}")
            else:
                # 创建容器
                container = client.containers.create(
                    image=image.id,
                    name=vm_name,
                    detach=True,
                    hostname=vm_name,
                    **container_config
                )

            logger.info(f"容器 {vm_name} 恢复成功")

            # 保存配置到 vm_saving（包括SSH端口配置）
            self.vm_saving[vm_name] = vm_conf
            self.data_set()

            hs_result = ZMessage(
                success=True, action="Restores",
                message=f"容器恢复成功: {vm_name}",
                results={"container_id": container.id, "image_id": image.id}
            )
            self.logs_set(hs_result)
            return hs_result

        except Exception as e:
            logger.error(f"恢复容器失败: {str(e)}")
            traceback.print_exc()
            return ZMessage(
                success=False, action="Restores",
                message=f"恢复失败: {str(e)}")

    # VM镜像挂载 ###############################################################
    def HDDMount(self, vm_name: str, vm_imgs: SDConfig, in_flag=True) -> ZMessage:
        # 专用操作 =============================================================
        # Docker容器不支持动态挂载/卸载磁盘
        return ZMessage(
            success=False, action="HDDMount",
            message="Docker容器不支持动态磁盘挂载")

    # ISO镜像挂载 ##############################################################
    def ISOMount(self, vm_name: str, vm_imgs: IMConfig, in_flag=True) -> ZMessage:
        # 专用操作 =============================================================
        # Docker 容器不需要 ISO 挂载，返回成功但不执行操作
        return ZMessage(
            success=True, action="ISOMount",
            message="Docker containers do not support ISO mounting")

    # 虚拟机远程访问 ###########################################################
    def VMRemote(self, vm_uuid: str, ip_addr: str = "127.0.0.1") -> ZMessage:
        # 专用操作 =============================================================
        if vm_uuid not in self.vm_saving:
            return ZMessage(
                success=False,
                action="VCRemote",
                message="虚拟机不存在")
        # 获取虚拟机配置 =======================================================
        vm_conf = self.vm_saving[vm_uuid]
        container_name = vm_conf.vm_uuid
        # 获取虚拟机SSH端口 ====================================================
        wan_port = None
        try:
            all_port = vm_conf.nat_all
            for now_port in all_port:
                if now_port.lan_port == 22:
                    wan_port = now_port.wan_port
                    break
        except Exception as e:
            logger.warning(f"无法获取SSH端口: {container_name}: {str(e)}")
        if not wan_port:
            return ZMessage(
                success=False, 
                action="VCRemote",
                message="虚拟机SSH端口映射不存在")
        # 2. 获取主机外网IP ====================================================
        if len(self.hs_config.public_addr) == 0:
            return ZMessage(
                success=False,
                action="VCRemote",
                message="主机外网IP不存在")
        public_ip = self.hs_config.public_addr[0]
        if public_ip in ["localhost", "127.0.0.1", ""]:
            public_ip = "127.0.0.1"  # 默认使用本地
        # 3. 启动tty会话web ====================================================
        tty_port, token = self.web_terminal.open_tty(
            self.hs_config.server_addr, wan_port)
        if tty_port <= 0:
            return ZMessage(
                success=False,
                action="VCRemote",
                message="启动tty会话失败"
            )
        # 4. 添加IP反向代理 ====================================================
        try:
            # 代理路径：---------------------------------------
            target_ip = self.hs_config.server_addr
            proxy_uri = f":{self.hs_config.remote_port}/{token}"
            # 添加代理 ----------------------------------------
            success = self.http_manager.proxy_add(
                (tty_port, target_ip),
                proxy_uri, is_https=False)
            if not success:
                self.web_terminal.stop_tty(tty_port) # 清理tty
                return ZMessage(
                    success=False,
                    action="VCRemote",
                    message="添加反向代理失败")
            # 重载配置 ---------------------------------------
            self.http_manager.loads_web()
        except Exception as e:
            logger.error(f"代理配置失败: {str(e)}")
            self.web_terminal.stop_tty(tty_port)
            return ZMessage(
                success=False,
                action="VCRemote",
                message=f"代理配置失败: {str(e)}")
        # 5. 构造返回URL =======================================================
        vnc_port = self.hs_config.remote_port
        url = f"http://{public_ip}:{vnc_port}/{token}"
        logger.info(
            f"VMRemote for {vm_uuid}: "
            f"SSH({public_ip}:{wan_port}) "
            f"-> tty({tty_port}) -> proxy(/{token}) -> {url}")
        # 6. 返回结果 ==========================================================
        return ZMessage(
            success=True,
            action="VCRemote",
            message=url,
            results={
                "tty_port": tty_port,
                "token": token,
                "vnc_port": vnc_port,
                "url": url,
                "ssh_port": wan_port
            }
        )

    # 移除磁盘 #################################################################
    def RMMounts(self, vm_name: str, vm_imgs: str) -> ZMessage:
        # 专用操作 =============================================================
        # 通用操作 =============================================================
        return ZMessage(
            success=True, action="ISOMount",
            message="Docker containers do not support SSD mounting")

    # 查找显卡 #################################################################
    def GPUShows(self) -> dict[str, str]:
        # 专用操作 =============================================================
        # Docker 容器不需要 GPU 管理，返回空字典
        # 通用操作 =============================================================
        return {}

    # 端口映射 #################################################################
    def PortsMap(self, map_info: PortData, flag=True) -> ZMessage:
        # 专用操作 =============================================================
        # 直接使用 IPTables API 进行端口转发，不获取虚拟机信息
        iptables_api = IPTablesAPI(self.hs_config)

        # 判断是否为远程主机（排除 SSH 转发模式）
        is_remote = (self.hs_config.server_addr not in ["localhost", "127.0.0.1", ""] and
                     not self.hs_config.server_addr.startswith("ssh://"))

        # 如果是远程主机，先建立SSH连接
        if is_remote:
            success, message = iptables_api.connect_ssh()
            if not success:
                return ZMessage(
                    success=False, action="PortsMap",
                    message=f"SSH 连接失败: {message}")

        # 如果wan_port为0，自动分配一个未使用的端口
        if map_info.wan_port == 0:
            map_info.wan_port = iptables_api.allocate_port()
        else:
            # 检查端口是否已被占用
            existing_ports = iptables_api.get_host_ports(is_remote)
            if map_info.wan_port in existing_ports:
                if is_remote:
                    iptables_api.close_ssh()
                return ZMessage(
                    success=False, action="PortsMap",
                    message=f"端口 {map_info.wan_port} 已被占用")

        # 执行端口映射操作
        if flag:
            success, error = iptables_api.add_port_mapping(
                map_info.lan_addr, map_info.lan_port, map_info.wan_port, is_remote, map_info.nat_tips)

            if success:
                hs_message = f"端口 {map_info.wan_port} 成功映射到 {map_info.lan_addr}:{map_info.lan_port}"
                hs_success = True
            else:
                if is_remote:
                    iptables_api.close_ssh()
                return ZMessage(
                    success=False, action="PortsMap",
                    message=f"端口映射失败: {error}")
        else:
            iptables_api.remove_port_mapping(
                map_info.lan_addr, map_info.lan_port, map_info.wan_port, is_remote)
            hs_message = f"端口 {map_info.wan_port} 映射已删除"
            hs_success = True

        hs_result = ZMessage(
            success=hs_success, action="PortsMap",
            message=hs_message)
        self.logs_set(hs_result)

        # 关闭 SSH 连接
        if is_remote:
            iptables_api.close_ssh()

        return hs_result
