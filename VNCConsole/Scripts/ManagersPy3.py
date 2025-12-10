import os
import time
from multiprocessing import Process
from typing import Dict, Optional
from loguru import logger


def _run_websockify(web_port: int, vnc_save: str, web_path: str):
    # 在子进程中导入，避免主进程加载不必要的模块
    from websockify import WebSocketProxy
    from websockify.token_plugins import TokenFile
    
    # 创建 TokenFile 插件实例
    token_plugin = TokenFile(vnc_save)
    server = WebSocketProxy(
        listen_port=web_port,
        verbose=True,
        token_plugin=token_plugin,
        web=web_path,
    )
    server.start_server()


class VNCStart:
    # Websockify 管理器 ##########################################################
    # :param web_port: Websockify 端口
    # ############################################################################
    def __init__(self, web_port: int = 6090):
        self.web_port = web_port
        self.vnc_save = "./DataSaving/websockify.cfg"
        self.web_path = "./VNCConsole/Sources/"
        self.process: Optional[Process] = None
        self.storage: Dict[str, str] = {}
        self.cfg_load()

    # 加载配置文件 ###############################################################
    def cfg_load(self):
        if os.path.exists(self.vnc_save):
            with open(self.vnc_save, "r") as f:
                for line in f:
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
        # 确保配置文件存在（websockify 需要它）
        self.cfg_save()
        
        # 将相对路径转换为绝对路径（子进程中工作目录可能不同）
        abs_vnc_save = os.path.abspath(self.vnc_save)
        abs_web_path = os.path.abspath(self.web_path)
        
        # 检查 web 路径是否存在
        if not os.path.exists(abs_web_path):
            logger.warning(f"警告: Web 资源路径不存在: {abs_web_path}")
        
        logger.info(f"启动 websockify 服务，端口: {self.web_port}")
        logger.info(f"配置文件路径: {abs_vnc_save}")
        logger.info(f"Web 资源路径: {abs_web_path}")
        
        # 使用 multiprocessing 启动 websockify 子进程
        self.process = Process(
            target=_run_websockify,
            args=(self.web_port, abs_vnc_save, abs_web_path),
            daemon=True
        )
        self.process.start()
        
        # 等待一小段时间检查进程是否正常启动
        time.sleep(0.5)
        if not self.process.is_alive():
            logger.error("错误: websockify 进程已退出")
            self.process = None
        else:
            logger.info("websockify 服务已启动")

    # 停止 websockify 服务 #######################################################
    def web_stop(self):
        if self.process is not None and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=3)
            logger.info("websockify 服务已停止")
        self.process = None

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
        logger.info(f"已添加 VNC: {target}, token: {token}")
        return token

    # 删除 VNC 目标 ##############################################################
    def del_port(self, token: str = ""):
        if token in self.storage:
            target = self.storage.pop(token)
            logger.info(f"已删除 VNC: {target}, token: {token}")
            self.cfg_save()


# 使用示例
if __name__ == "__main__":
    web_data = VNCStart(web_port=6090)
    web_data.web_open()
    # vnc_pass = "12345"
    # web_data.add_port("127.0.0.1", 5901, vnc_pass)
    # print(f"生成的 token: {vnc_pass}")
    # url = f"http://127.0.0.1:{web_data.web_port}/vnc.html?host=127.0.0.1&port={web_data.web_port}&path=websockify?token={vnc_pass}"
    # print(f"访问 URL: {url}")
    input("按 Enter 键关闭服务...")
    # web_data.del_port(token=vnc_pass)
    web_data.web_stop()