import os
import random
import string
import subprocess
import platform
from loguru import logger

from MainObject.Config.HSConfig import HSConfig


class WebTerminalAPI:
    """Web Terminal (ttyd) 管理API"""

    def __init__(self, hs_config: HSConfig):
        """
        初始化 Web Terminal API
        
        :param hs_config: 宿主机配置对象
        """
        self.hs_config = hs_config
        self.ttyd_process = None
        self.ttyd_tokens = {}
        # 根据系统获取ttyd可执行文件路径
        self.ttyd_path = self._get_ttyd_path()

    def _get_ttyd_path(self) -> str:
        """
        获取当前系统的ttyd可执行文件路径
        :return: ttyd可执行文件路径，如果找不到则返回空字符串
        """
        # 获取脚本所在目录的父目录（项目根目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        ttyd_dir = os.path.join(project_root, "HostConfig", "ttydserver")
        
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

    # 启动 ttyd 服务 #####################################################
    def start_ttydserver(self) -> bool:
        """
        启动 ttyd Web Terminal 服务
        :return: 是否成功
        """
        # 仅本地模式启动（不包括 SSH 转发模式）
        is_local = self.hs_config.server_addr in ["localhost", "127.0.0.1", ""]
        if self.hs_config.server_addr.startswith("ssh://") or not is_local:
            return True
        
        # 检查ttyd是否存在
        if not self.ttyd_path:
            logger.warning("ttyd not found, Web Terminal will not be available")
            return False
        
        try:
            # 启动 ttyd 服务（监听所有接口）
            self.ttyd_process = subprocess.Popen(
                [self.ttyd_path, "-p", str(self.hs_config.remote_port), "-W", "bash"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            logger.info(f"ttyd Web Terminal started on port {self.hs_config.remote_port}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to start ttyd: {str(e)}")
            return False

    # 停止 ttyd 服务 #####################################################
    def stop_ttydserver(self):
        """停止 ttyd 服务"""
        if self.ttyd_process:
            try:
                self.ttyd_process.terminate()
                self.ttyd_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ttyd_process.kill()
            finally:
                self.ttyd_process = None
                logger.info("ttyd Web Terminal stopped")

    # 检查 ttyd 是否运行 #################################################
    def is_running(self) -> bool:
        """
        检查 ttyd 是否正在运行
        :return: 是否运行中
        """
        return self.ttyd_process is not None

    # 生成终端访问URL ##########################################################
    def generate_terminal_url(self, vm_uuid: str, ssh_port: str = None) -> str:
        """
        生成 Web Terminal 访问 URL
        :param vm_uuid: 虚拟机/容器UUID
        :param ssh_port: SSH端口映射（Docker容器随机端口）
        :return: 访问URL
        """
        # 对于远程 Docker，返回 Docker 控制台 URL
        if self.hs_config.server_addr not in ["localhost", "127.0.0.1", ""]:
            public_addr = self.hs_config.public_addr[0] if self.hs_config.public_addr else self.hs_config.server_addr
            url = f"http://{public_addr}:{self.hs_config.remote_port}/terminal/{vm_uuid}"
            return url
        
        # 本地模式使用 ttydserver
        if not self.ttyd_process:
            logger.warning("ttydserver service is not running")
            return ""
        
        # 生成随机 token
        rand_token = ''.join(random.sample(string.ascii_letters + string.digits, 32))
        self.ttyd_tokens[vm_uuid] = {
            "token": rand_token,
            "ssh_port": ssh_port
        }
        
        # 构造访问 URL
        public_addr = self.hs_config.public_addr[0] if self.hs_config.public_addr else "127.0.0.1"
        
        # 使用 docker exec 连接到容器（通过端口映射连接SSH）
        if ssh_port:
            # 通过SSH端口映射连接
            url = f"http://{public_addr}:{self.hs_config.remote_port}/" \
                  f"?arg=ssh&arg=-p&arg={ssh_port}&arg={self.hs_config.server_addr}&token={rand_token}"
        else:
            # 使用 docker exec 连接到容器
            url = f"http://{public_addr}:{self.hs_config.remote_port}/" \
                  f"?arg=docker&arg=exec&arg=-it&arg={vm_uuid}&arg=/bin/bash&token={rand_token}"
        
        logger.info(f"Generated terminal URL for {vm_uuid} (ssh_port={ssh_port}): {url}")
        return url

    # 验证token ################################################################
    def verify_token(self, vm_uuid: str, token: str) -> bool:
        """
        验证终端访问token
        :param vm_uuid: 虚拟机/容器UUID
        :param token: 访问令牌
        :return: 是否有效
        """
        token_info = self.ttyd_tokens.get(vm_uuid)
        if isinstance(token_info, dict):
            return token_info.get("token") == token
        return False

    # 清理token ################################################################
    def clear_token(self, vm_uuid: str):
        """
        清理指定容器的token
        :param vm_uuid: 虚拟机/容器UUID
        """
        if vm_uuid in self.ttyd_tokens:
            del self.ttyd_tokens[vm_uuid]
    
    # 获取容器SSH端口 ##########################################################
    def get_ssh_port(self, vm_uuid: str) -> str:
        """
        获取指定容器的SSH端口
        :param vm_uuid: 虚拟机/容器UUID
        :return: SSH端口或空字符串
        """
        token_info = self.ttyd_tokens.get(vm_uuid)
        if isinstance(token_info, dict):
            return token_info.get("ssh_port", "")
        return ""
