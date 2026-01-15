import random
import subprocess
from loguru import logger

from MainObject.Config.HSConfig import HSConfig
from MainObject.Public.ZMessage import ZMessage
from HostModule.SSHDManager import SSHDManager


class IPTablesAPI:
    """IPTables端口映射管理API"""

    def __init__(self, hs_config: HSConfig):
        """
        初始化 IPTables API
        
        :param hs_config: 宿主机配置对象
        """
        self.hs_config = hs_config
        self.ssh_forward = None

    # 获取已分配的端口列表 #####################################################
    def get_host_ports(self, is_remote: bool = False) -> set[int]:
        """
        获取主机已分配的端口列表
        :param is_remote: 是否为远程主机
        :return: 端口集合
        """
        try:
            if is_remote:
                # 远程执行
                success, stdout, stderr = self.ssh_forward.execute_command(
                    "iptables -t nat -L PREROUTING -n --line-numbers"
                )
                if not success:
                    return set()
                output = stdout
            else:
                # 本地执行
                result = subprocess.run(
                    ["iptables", "-t", "nat", "-L", "PREROUTING", "-n", "--line-numbers"],
                    capture_output=True, text=True, check=True)
                output = result.stdout
            
            ports = set()
            for line in output.split('\n'):
                # 查找 DNAT 规则中的 dpt (destination port)
                if 'dpt:' in line:
                    parts = line.split()
                    for part in parts:
                        if part.startswith('dpt:'):
                            port = part.replace('dpt:', '')
                            if port.isdigit():
                                ports.add(int(port))
            return ports
        except subprocess.CalledProcessError:
            return set()
        except Exception as e:
            logger.warning(f"获取主机端口失败: {str(e)}")
            return set()

    # 执行iptables命令 #########################################################
    def execute_iptables_command(self, cmd: list[str], is_remote: bool = False) -> tuple[bool, str]:
        """
        执行iptables命令
        :param cmd: 命令列表
        :param is_remote: 是否为远程执行
        :return: (是否成功, 错误信息)
        """
        try:
            if is_remote:
                # 远程执行：将命令列表转换为字符串
                cmd_str = ' '.join(cmd)
                success, stdout, stderr = self.ssh_forward.execute_command(cmd_str)
                if not success:
                    return False, stderr
                return True, ""
            else:
                # 本地执行
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return True, ""
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except Exception as e:
            return False, str(e)

    # 分配可用端口 ##############################################################
    def allocate_port(self) -> int:
        """
        自动分配可用端口
        :return: 分配的端口号
        """
        is_remote = (self.hs_config.server_addr not in ["localhost", "127.0.0.1", ""] and 
                    not self.hs_config.server_addr.startswith("ssh://"))
        
        wan_port = random.randint(self.hs_config.ports_start, self.hs_config.ports_close)
        existing_ports = self.get_host_ports(is_remote)
        max_attempts = 100
        attempts = 0
        while wan_port in existing_ports and attempts < max_attempts:
            wan_port = random.randint(self.hs_config.ports_start, self.hs_config.ports_close)
            attempts += 1
        return wan_port

    # 添加端口映射规则 #########################################################
    def add_port_mapping(self, container_ip: str, lan_port: int, wan_port: int, 
                         is_remote: bool = False, vm_name: str = "") -> tuple[bool, str]:
        """
        添加端口映射规则
        :param container_ip: 容器IP地址
        :param lan_port: 容器端口
        :param wan_port: 主机端口
        :param is_remote: 是否为远程主机
        :param vm_name: 虚拟机名（用于注释）
        :return: (是否成功, 错误信息)
        """
        # 构建注释：源IP-端口-目标端口#虚拟机名
        comment = f"{container_ip}-{wan_port}-{lan_port}#{vm_name}" if vm_name else f"{container_ip}-{wan_port}-{lan_port}"
        
        # 1. PREROUTING DNAT 规则
        success, error = self.execute_iptables_command([
            "iptables", "-t", "nat", "-A", "PREROUTING",
            "-p", "tcp", "--dport", str(wan_port),
            "-j", "DNAT", "--to-destination",
            f"{container_ip}:{lan_port}",
            "-m", "comment", "--comment", comment
        ], is_remote)
        
        if not success:
            return False, f"添加 PREROUTING 规则失败: {error}"
        
        # 2. OUTPUT DNAT 规则
        # success, error = self.execute_iptables_command([
        #     "iptables", "-t", "nat", "-A", "OUTPUT",
        #     "-p", "tcp", "--dport", str(wan_port),
        #     "-j", "DNAT", "--to-destination",
        #     f"{container_ip}:{lan_port}",
        #     "-m", "comment", "--comment", comment
        # ], is_remote)
        
        if not success:
            # 回滚 PREROUTING 规则
            self.remove_port_mapping(container_ip, lan_port, wan_port, is_remote)
            return False, f"添加 OUTPUT 规则失败: {error}"
        
        # 3. FORWARD 规则
        success, error = self.execute_iptables_command([
            "iptables", "-A", "FORWARD",
            "-p", "tcp", "-d", container_ip,
            "--dport", str(lan_port),
            "-j", "ACCEPT",
            "-m", "comment", "--comment", comment
        ], is_remote)
        
        if not success:
            # 回滚前面的规则
            self.remove_port_mapping(container_ip, lan_port, wan_port, is_remote)
            return False, f"添加 FORWARD 规则失败: {error}"
        
        logger.info(
            f"端口映射已添加: 主机 {wan_port} -> 容器 {container_ip}:{lan_port}")
        
        return True, ""

    # 删除端口映射规则 #########################################################
    def remove_port_mapping(self, container_ip: str, lan_port: int, wan_port: int, 
                            is_remote: bool = False) -> bool:
        """
        删除端口映射规则
        :param container_ip: 容器IP地址
        :param lan_port: 容器端口
        :param wan_port: 主机端口
        :param is_remote: 是否为远程主机
        :return: 是否成功
        """
        # 1. 删除 FORWARD 规则
        # self.execute_iptables_command([
        #     "iptables", "-D", "FORWARD",
        #     "-p", "tcp", "-d", container_ip,
        #     "--dport", str(lan_port),
        #     "-j", "ACCEPT"
        # ], is_remote)
        
        # 2. 删除 OUTPUT DNAT 规则
        # self.execute_iptables_command([
        #     "iptables", "-t", "nat", "-D", "OUTPUT",
        #     "-p", "tcp", "--dport", str(wan_port),
        #     "-j", "DNAT", "--to-destination",
        #     f"{container_ip}:{lan_port}"
        # ], is_remote)
        
        # 3. 删除 PREROUTING DNAT 规则
        self.execute_iptables_command([
            "iptables", "-t", "nat", "-D", "PREROUTING",
            "-p", "tcp", "--dport", str(wan_port),
            "-j", "DNAT", "--to-destination",
            f"{container_ip}:{lan_port}"
        ], is_remote)
        
        logger.info(
            f"端口映射已删除: 主机 {wan_port} -> 容器 {container_ip}:{lan_port}")
        
        return True

    # 连接SSH ##################################################################
    def connect_ssh(self) -> tuple[bool, str]:
        """
        连接SSH（用于远程端口映射）
        :return: (是否成功, 消息)
        """
        self.ssh_forward = SSHDManager()
        success, message = self.ssh_forward.connect(
            hostname=self.hs_config.server_addr,
            username=self.hs_config.server_user,
            password=self.hs_config.server_pass,
            port=22
        )
        
        if not success:
            return False, message
        
        return True, "SSH连接成功"

    # 关闭SSH连接 ##############################################################
    def close_ssh(self):
        """关闭SSH连接"""
        if self.ssh_forward:
            self.ssh_forward.close()
            self.ssh_forward = None
