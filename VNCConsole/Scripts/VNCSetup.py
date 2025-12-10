import subprocess
import urllib.parse
import os
import sys
import time
import atexit
from pathlib import Path
from loguru import logger


class NoVNCService:
    def __init__(self, vnc_host, vnc_port, password=None, web_port=6080):
        """
        启动noVNC服务并生成访问链接
        :param vnc_host: VNC服务器IP
        :param vnc_port: VNC服务器端口
        :param password: VNC密码（可选）
        :param web_port: Web服务端口
        """
        self.vnc_host = vnc_host
        self.vnc_port = vnc_port
        self.password = password
        self.web_port = web_port
        self.novnc_path = Path(r"./VNCConsole/Sources")  # 修改为你的noVNC路径
        self.websockify_process = None

        # 验证路径
        if not self.novnc_path.exists():
            raise FileNotFoundError(f"noVNC路径不存在: {self.novnc_path}")

    def start(self):
        """启动WebSockify代理服务"""
        logger.info("=" * 60)
        logger.info("启动noVNC服务...")

        # WebSockify命令（使用Python模块方式调用，兼容Windows）
        cmd = [
            sys.executable,  # 使用当前Python解释器
            "-m", "websockify",  # 以模块方式运行websockify
            str(self.web_port),  # Web端口
            f"{self.vnc_host}:{self.vnc_port}",  # VNC目标
            "--web", str(self.novnc_path),  # noVNC前端路径
            "--heartbeat", "30",  # 心跳检测
        ]

        logger.info(f"执行: {' '.join(cmd)}")

        # 启动进程
        self.websockify_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 注册退出清理
        atexit.register(self.stop)

        # 等待服务启动
        time.sleep(3)

        # 检查进程状态
        if self.websockify_process.poll() is None:
            logger.success("✅ WebSockify代理启动成功")
            url = self._generate_url()
            logger.info(f"访问链接: {url}")
            logger.info("=" * 60)
            return url
        else:
            _, stderr = self.websockify_process.communicate()
            logger.error(f"❌ 启动失败: {stderr}")
            raise RuntimeError("WebSockify启动失败")

    def _generate_url(self):
        """生成noVNC访问链接"""
        params = {
            "host": "localhost",
            "port": self.web_port,
            "autoconnect": "true",  # 自动连接
        }

        if self.password:
            params["password"] = self.password

        query = urllib.parse.urlencode(params)
        # 使用vnc.html或vnc_auto.html
        return f"http://localhost:{self.web_port}/vnc.html?{query}"

    def stop(self):
        """停止服务"""
        if self.websockify_process:
            logger.info("\n正在停止WebSockify服务...")
            self.websockify_process.terminate()
            self.websockify_process.wait()
            logger.success("服务已停止")


def start_novnc_service(vnc_connect_str, username=None, password=None, web_port=6080):
    """
    便捷函数：一键启动noVNC服务
    :param vnc_connect_str: VNC连接字符串 "IP:端口"
    :param username: VNC用户名（保留参数，通常VNC只用密码）
    :param password: VNC密码
    :param web_port: Web服务端口
    :return: 访问URL
    """
    # 解析连接字符串
    if ":" in vnc_connect_str:
        host, port = vnc_connect_str.split(":")
        port = int(port)
    else:
        host = vnc_connect_str
        port = 5900  # 默认VNC端口

    # 创建并启动服务
    service = NoVNCService(
        vnc_host=host,
        vnc_port=port,
        password=password,
        web_port=web_port
    )

    return service.start()


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 示例：连接本地VNC服务器
    try:
        url = start_novnc_service(
            vnc_connect_str="127.0.0.1:5901",
            password="1234",  # 替换为你的VNC密码
            web_port=6090
        )
        logger.info(f"\n请在浏览器中打开: {url}")
        logger.info("服务运行中，按Ctrl+C停止...")

        # 保持运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n收到停止信号")