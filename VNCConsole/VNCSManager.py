import os
import time
import sys
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, Optional
from multiprocessing import Process
from loguru import logger


class WebsocketUI:
    # Websockify 管理器 ##########################################################
    # :param web_port: Websockify 端口
    # ############################################################################
    def __init__(self, web_port: int = 6090, cfg_name: str = "websockify"):
        self.web_port = web_port
        
        # 获取正确的项目根目录（支持打包后的环境）
        if getattr(sys, 'frozen', False):
            # 打包后的环境：使用可执行文件所在目录
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller 打包
                project_root = Path(sys._MEIPASS)
            else:
                # cx_Freeze 打包
                project_root = Path(sys.executable).parent
        else:
            # 开发环境：使用脚本所在目录的父目录
            project_root = Path(__file__).parent.parent.absolute()
        
        # 配置文件路径（始终在可执行文件目录下）
        if getattr(sys, 'frozen', False):
            # 打包后：配置文件在可执行文件目录下
            exe_dir = Path(sys.executable).parent
            self.vnc_save = os.path.join(exe_dir, "DataSaving", f"{cfg_name}.cfg")
        else:
            # 开发环境
            self.vnc_save = os.path.join(project_root, "DataSaving", f"{cfg_name}.cfg")
        
        # Web 资源路径
        self.web_path = os.path.join(project_root, "VNCConsole", "Sources")
        
        # 检测环境：如果不是 Python 解释器，使用可执行文件
        if 'python' in os.path.basename(sys.executable).lower():
            script_name = "websocketproxy.py"
        else:
            script_name = "websocketproxy"
            if os.name == 'nt':
                script_name += '.exe'

        self.bin_path = os.path.join(project_root, "Websockify", script_name)
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
        # 调试信息：打印所有关键路径
        logger.info(f"Web 资源路径: {self.web_path}")
        logger.info(f"Websockify 可执行文件: {self.bin_path}")
        logger.info(f"配置文件路径: {self.vnc_save}")
        logger.info(f"是否为打包环境: {getattr(sys, 'frozen', False)}")
        
        if not os.path.exists(self.web_path):
            logger.error(f"Web 资源路径不存在: {self.web_path}")
            
            # 尝试查找可能的路径
            if getattr(sys, 'frozen', False):
                exe_dir = Path(sys.executable).parent
                possible_paths = [
                    exe_dir / "VNCConsole" / "Sources",
                    exe_dir / "lib" / "VNCConsole" / "Sources",
                    exe_dir.parent / "VNCConsole" / "Sources",
                ]
                logger.info("尝试查找可能的路径:")
                for path in possible_paths:
                    exists = os.path.exists(path)
                    logger.info(f"  {path} - {'存在' if exists else '不存在'}")
                    if exists:
                        self.web_path = str(path)
                        logger.success(f"找到 Web 资源路径: {self.web_path}")
                        break
                else:
                    logger.error("无法找到 Web 资源路径，websockify 可能无法正常工作")
                    return False
            else:
                return False

        # 构建命令：如果是 .py 文件则用 Python 执行，否则直接执行
        if self.bin_path.endswith('.py'):
            cmd = [sys.executable, self.bin_path]
        else:
            cmd = [self.bin_path]

        cmd += ["--token-plugin", "TokenFile",
                "--token-source", os.path.abspath(self.vnc_save),
                str(self.web_port),
                "--web", os.path.abspath(self.web_path)]

        logger.info(f"启动 websockify: {self.web_port}")
        logger.info(f"执行命令: {' '.join(cmd)}")
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if (os.name == 'nt' and getattr(sys, 'frozen', False)) else 0
            subprocess.Popen(cmd, creationflags=creationflags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.success(f"websockify 已启动，支持 {len(self.storage)} 个连接")
            return True
        except Exception as e:
            logger.error(f"启动失败: {e}")
            return False

    # 停止 websockify 服务 #######################################################
    def web_stop(self):
        if os.name == 'nt':
            cmd = 'taskkill /f /im websocketproxy.exe'
        else:
            cmd = 'pkill -f websocketproxy'

        os.system(cmd)
        logger.info("websockify 已停止")

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


class VNCSManager:
    """多进程管理器，用于在独立进程中运行 websockify 服务"""

    def __init__(self, in_exec: WebsocketUI):
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
            # 即使进程对象为空，也尝试调用 web_stop 清理可能残留的进程
            self.exec.web_stop()
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

        # 确保调用 web_stop 清理所有 websocketproxy 进程
        self.exec.web_stop()
        self.proc = None

    def is_running(self) -> bool:
        """检查服务是否正在运行"""
        return self.proc is not None and self.proc.is_alive()


# 使用示例
if __name__ == "__main__":
    web_data = WebsocketUI(web_port=6090)

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
