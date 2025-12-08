import os
import sys
import subprocess
from typing import Dict, Optional


class VNCStart:
    # Websockify 管理器 ##########################################################
    # :param web_port: Websockify 端口
    # ############################################################################
    def __init__(self, web_port: int = 6090):
        self.web_port = web_port
        self.vnc_save = "DataSaving\\websockify.cfg"
        self.web_path = "VNCConsole\\Sources"
        self.process: Optional[subprocess.Popen] = None
        self.storage: Dict[str, str] = {}
        self.cfg_load()

    # 加载配置文件 ###############################################################
    def cfg_load(self):
        if os.path.exists(self.vnc_save):
            with open(self.vnc_save, "r") as f:
                for line in f:
                    token, target = line.strip().split(": ")
                    self.storage[token] = target
                    print(f"已加载 VNC: {token} -> {target}")

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

        # 检查 web 路径是否存在
        if not os.path.exists(self.web_path):
            print(f"警告: Web 资源路径不存在: {self.web_path}")

        print(f"启动 websockify 服务，端口: {self.web_port}")
        print(f"配置文件路径: {self.vnc_save}")
        print(f"Web 资源路径: {self.web_path}")

        # 使用 PowerShell 启动 websockify
        cmd = (f'"{sys.executable}"'
               f' -m websockify'
               f' --token-plugin'
               f' TokenFile'
               f' --token-source'
               f' "{os.path.join(os.getcwd(), self.vnc_save)}"'
               f'  {self.web_port}'
               f' --web "{os.path.join(os.getcwd(), self.web_path)}"')
        print(f"执行命令: {cmd}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )

        # 检查进程是否正常启动
        try:
            # 等待一小段时间，检查是否立即退出
            self.process.wait(timeout=0.5)
            # 如果能 wait 到，说明进程已退出
            stdout, stderr = self.process.communicate()
            print(f"错误: websockify 进程已退出")
            # print(f"stdout: {stdout.decode()}")
            # print(f"stderr: {stderr.decode()}")
            self.process = None
        except subprocess.TimeoutExpired:
            # 进程仍在运行，说明启动成功
            print("websockify 服务已启动")

    # 停止 websockify 服务 #######################################################
    def web_stop(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("websockify 服务已停止")
        self.process = None

    # 添加 VNC 目标 ##############################################################
    def add_port(self, ip: str, port: int, token: str) -> str:
        target = f"{ip}:{port}"
        # 检查是否已存在相同目标的 token
        for existing_token, existing_target in self.storage.items():
            if existing_target == target:
                print(f"VNC 目标 {target} 已存在，token: {existing_token}")
                return existing_token
        self.storage[token] = target
        self.cfg_save()
        print(f"已添加 VNC: {target}, token: {token}")
        return token

    # 删除 VNC 目标 ##############################################################
    def del_port(self, token: str = ""):
        if token in self.storage:
            target = self.storage.pop(token)
            print(f"已删除 VNC: {target}, token: {token}")
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
