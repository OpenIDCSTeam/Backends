import os
import time
import sys
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, Optional
from multiprocessing import Process
from loguru import logger


class VNCStart:
    # Websockify 管理器 ##########################################################
    # :param web_port: Websockify 端口
    # ############################################################################
    def __init__(self, web_port: int = 6090, cfg_name: str = "websockify"):
        self.web_port = web_port
        self.vnc_save = f"./DataSaving/{cfg_name}.cfg"
        self.web_path = "./VNCConsole/Sources/"  # 修复路径：当前已在VNCConsole目录下
        self.process = None
        self.storage: Dict[str, str] = {}
        self.cfg_load()

    # 加载配置文件 ###############################################################
    def cfg_load(self):
        if os.path.exists(self.vnc_save):
            with open(self.vnc_save, "r") as f:
                for line in f:
                    if line.strip():
                        token, target = line.strip().split(": ")
                        self.storage[token] = target
                        logger.info(f"已加载 VNC: {token} -> {target}")

    # 将 token 写入配置文件 ######################################################
    def cfg_save(self):
        os.makedirs(os.path.dirname(self.vnc_save), exist_ok=True)
        with open(self.vnc_save, "w") as f:
            for token, target in self.storage.items():
                f.write(f"{token}: {target}\n")

    # 启动 websockify 服务 #######################################################
    def web_open(self):
        # 将相对路径转换为绝对路径
        abs_vnc_save = os.path.abspath(self.vnc_save)
        abs_web_path = os.path.abspath(self.web_path)

        # 检查 web 路径是否存在
        if not os.path.exists(abs_web_path):
            logger.warning(f"警告: Web 资源路径不存在: {abs_web_path}")
            return False

        logger.info(f"启动 websockify 服务，端口: {self.web_port}")
        logger.info(f"配置文件路径: {abs_vnc_save}")
        logger.info(f"Web 资源路径: {abs_web_path}")

        # 构建websockify命令，使用token认证
        cmd = [
            sys.executable,  # 使用当前Python解释器
            "./Websockify/websocketproxy.py",  # 以模块方式运行websockify
            "--token-plugin", "TokenFile",  # 使用TokenFile插件
            "--token-source", abs_vnc_save,  # 指定token配置文件
            str(self.web_port),  # Web端口
            "--web", abs_web_path  # Web资源路径
        ]

        # 在后台启动进程（Windows和Linux兼容）
        logger.debug(" ".join(cmd))
        if os.name == 'nt':  # Windows
            # cmd_str = f'start /B {" ".join(cmd)}'
            cmd_str = " ".join(cmd)
            os.system(cmd_str)
        else:  # Linux/Mac
            cmd_str = f'{" ".join(cmd)} &'
            os.system(cmd_str)

        logger.success(f"websockify 服务已启动，支持 {len(self.storage)} 个VNC连接")
        return True

    # 停止 websockify 服务 #######################################################
    def web_stop(self):
        # 查找并终止websockify进程
        if os.name == 'nt':  # Windows
            os.system(f'taskkill /f /im python.exe /fi "WINDOWTITLE eq *websockify*" 2>nul')
        else:  # Linux/Mac
            os.system(f'pkill -f "websockify {self.web_port}"')
        logger.info("websockify 服务已停止")

    # 添加 VNC 目标 ##############################################################
    def add_port(self, ip: str, port: int, token: str) -> str:
        target = f"{ip}:{port}"
        # 检查是否已存在相同目标的 token
        for existing_token, existing_target in self.storage.items():
            if existing_target == target:
                logger.info(f"VNC 目标 {target} 已存在，token: {existing_token}")
                return existing_token

        self.storage[token] = target
        self.cfg_save()
        logger.success(f"已添加 VNC: {target}, token: {token}")
        return token

    # 删除 VNC 目标 ##############################################################
    def del_port(self, ip, port):
        for token, target in self.storage.items():
            if target == f"{ip}:{port}":
                del self.storage[token]
                self.cfg_save()
                logger.success(f"已删除 VNC: {ip}:{port}")
                return True
        logger.warning(f"未找到 VNC: {ip}:{port}")
        return False

    # 生成指定token的访问URL
    def get_url(self, token: str = None):
        if token and token in self.storage:
            return f"http://localhost:{self.web_port}/vnc.html?autoconnect=true&path=websockify?token={token}"
        elif not token and len(self.storage) > 0:
            # 如果没有指定token，返回第一个可用的URL
            first_token = list(self.storage.keys())[0]
            return f"http://localhost:{self.web_port}/vnc.html?autoconnect=true&path=websockify?token={first_token}"
        else:
            logger.warning("警告: 没有可用的VNC连接")
            return None

    # 列出所有可用的VNC连接
    def list_connections(self):
        if not self.storage:
            logger.info("当前没有VNC连接")
            return

        logger.info("当前VNC连接列表:")
        for token, target in self.storage.items():
            url = self.get_url(token)
            logger.info(f"  Token: {token} -> {target}")
            logger.info(f"  URL: {url}")
            logger.info("")


class VProcess:
    """多进程管理器，用于在独立进程中运行 websockify 服务"""

    def __init__(self, in_exec: VNCStart):
        self.exec = in_exec
        self.proc: Optional[Process] = None

    def start(self):
        """在新进程中启动 websockify 服务"""
        if self.proc is not None and self.proc.is_alive():
            logger.info("websockify 服务已在运行中")
            return

        # 创建新进程来运行 websockify
        self.proc = Process(target=self.exec.web_open)
        self.proc.daemon = True  # 设置为守护进程，主进程退出时自动关闭
        self.proc.start()
        logger.success(f"websockify 服务已在新进程中启动 (PID: {self.proc.pid})")

    def close(self):
        """关闭 websockify 服务进程"""
        if self.proc is None:
            logger.info("没有运行中的 websockify 服务")
            return

        if self.proc.is_alive():
            logger.info(f"正在关闭 websockify 服务进程 (PID: {self.proc.pid})...")
            self.proc.terminate()  # 发送终止信号
            self.proc.join(timeout=5)  # 等待最多5秒

            # 如果进程仍未结束，强制杀死
            if self.proc.is_alive():
                logger.warning("进程未响应，强制关闭...")
                self.proc.kill()
                self.proc.join()

            logger.success("websockify 服务进程已关闭")
        else:
            logger.info("websockify 服务进程已停止")

        self.proc = None

    def is_running(self) -> bool:
        """检查服务是否正在运行"""
        return self.proc is not None and self.proc.is_alive()


# 使用示例
if __name__ == "__main__":
    web_data = VNCStart(web_port=6090)

    # 添加多个VNC目标
    # vnc_pass1 = "server1"
    # vnc_pass2 = "server2"
    # web_data.add_port("127.0.0.1", 5901, vnc_pass1)
    # web_data.add_port("192.168.1.100", 5900, vnc_pass2)

    # 列出所有连接
    web_data.list_connections()
    # 启动服务
    web_data.web_open()

    # 获取特定token的URL
    # url1 = web_data.get_url(vnc_pass1)
    # print(f"Server1 访问 URL: {url1}")
    #
    # 获取第一个可用的URL
    # default_url = web_data.get_url()
    # print(f"默认访问 URL: {default_url}")

    input("按 Enter 键关闭服务...")
    web_data.web_stop()
