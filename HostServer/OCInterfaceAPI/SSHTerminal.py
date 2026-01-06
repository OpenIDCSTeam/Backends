import os
import random
import string
import subprocess
import platform
from loguru import logger

from MainObject.Config.HSConfig import HSConfig


class SSHTerminal:
    """Web Terminal (ttyd) 管理API - 修改为直接启动ttyd进程"""

    def __init__(self, hs_config: HSConfig):
        self.hs_config = hs_config
        self.ttyd_processes = {}  # 存储ttyd进程 {port: process}
        self.ttyd_tokens = {}  # 存储token映射 {port: token}
        # 根据系统获取ttyd可执行文件路径
        self.ttyd_path = self.path_tty()

    # 获取ttyd可执行文件路径 #############################################
    def path_tty(self) -> str:
        # 获取脚本所在目录的父目录（项目根目录）
        # current_dir = os.path.dirname(os.path.abspath(__file__))
        # project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        ttyd_dir = os.path.join(os.getcwd(), "HostConfig", "ttydserver")

        system = platform.system().lower()
        machine = platform.machine().lower()

        # 根据系统选择合适的ttyd可执行文件
        if system == "windows":
            ttyd_file = "ttyd.win32.exe"
        elif system == "linux":
            if "aarch64" in machine or "arm64" in machine:
                ttyd_file = "ttyd.aarch64"
            else:
                ttyd_file = "ttyd.x86_64"
        else:
            logger.warning(f"Unsupported platform: {system} {machine}")
            return ""

        ttyd_path = os.path.join(ttyd_dir, ttyd_file)

        # 检查文件是否存在
        if os.path.exists(ttyd_path):
            logger.info(f"Found ttyd at: {ttyd_path}")
            return ttyd_path
        else:
            logger.warning(f"ttyd not found at: {ttyd_path}")
            return ""

    # 启动 ttyd SSH会话 ##################################################
    def open_tty(self, host_ip: str, ssh_port: str) -> tuple[int, str]:
        """
        启动ttyd进程连接SSH
        :param host_ip: 目标主机IP（容器IP或外网IP）
        :param ssh_port: SSH端口
        :return: (端口号, token)
        """
        if not self.ttyd_path:
            logger.error("ttyd executable not found")
            return -1, ""

        # 生成随机端口（7000-8000）
        random_port = random.randint(7000, 8000)

        # 生成随机token
        token = ''.join(random.sample(string.ascii_letters + string.digits, 32))

        try:
            # 构建SSH命令：ssh root@host_ip -p ssh_port
            ssh_cmd = f"ssh root@{host_ip} -p {ssh_port}"

            # 启动ttyd进程，工作目录设为C:\（Windows兼容）
            cmd = [self.ttyd_path, "--writable", "-w", "C:\\", "-p", str(22), ssh_cmd]
            logger.info(f"Starting ttyd SSH session with command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 存储进程信息
            self.ttyd_processes[random_port] = process
            self.ttyd_tokens[random_port] = token

            logger.info(f"Started ttyd SSH session on port {random_port} for {host_ip}:{ssh_port}")
            return random_port, token

        except Exception as e:
            logger.error(f"Failed to start ttyd SSH session: {str(e)}")
            return -1, ""

    # 停止 ttyd 会话 #####################################################
    def stop_tty(self, port: int):
        """
        停止指定端口的ttyd进程
        :param port: ttyd进程监听的端口
        """
        if port in self.ttyd_processes:
            process = None
            try:
                process = self.ttyd_processes[port]
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if process:
                    process.kill()
            finally:
                del self.ttyd_processes[port]
                if port in self.ttyd_tokens:
                    del self.ttyd_tokens[port]
                logger.info(f"Stopped ttyd session on port {port}")
