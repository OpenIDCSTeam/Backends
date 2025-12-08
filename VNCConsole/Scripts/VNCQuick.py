import subprocess
import urllib.parse
import os
import sys
import time
import atexit
from pathlib import Path
import tempfile


class DynamicVNCProxy:
    """动态管理VNC代理（支持运行时增删）"""

    def __init__(self, vnc_servers=None, web_port=6080, novnc_path=None):
        """
        初始化动态VNC代理
        :param vnc_servers: 初始服务器字典，格式 {"token": "IP:端口"}
        :param web_port: Web服务端口
        :param novnc_path: noVNC目录路径
        """
        self.vnc_servers = vnc_servers or {}
        self.web_port = web_port
        self.novnc_path = Path(novnc_path) if novnc_path else Path(r"./VNCConsole/Sources")
        self.token_file = None
        self.websockify_process = None
        self.is_running = False

        # 验证noVNC路径
        if not self.novnc_path.exists():
            raise FileNotFoundError(f"noVNC路径不存在: {self.novnc_path}")

        # 启动服务
        self._start_service()

    def _create_token_file(self):
        """创建token文件"""
        self.token_file = Path(tempfile.gettempdir()) / "vnc_tokens"
        with open(self.token_file, "w") as f:
            for token, addr in self.vnc_servers.items():
                # websockify token文件格式: token: host:port (注意冒号后无空格)
                f.write(f"{token}: {addr}\n")
        print(f"Token文件已创建: {self.token_file}")
        print(f"Token文件内容:")
        for token, addr in self.vnc_servers.items():
            print(f"  {token}: {addr}")
        return self.token_file

    def _start_service(self):
        """启动WebSockify服务"""
        # 清理旧进程
        if self.websockify_process:
            self._stop_service()

        self._create_token_file()

        # websockify使用token文件模式时，使用 --token-plugin 而非 --target-config
        # 格式: websockify [source_port] --token-plugin=TokenFile --token-source=[token_file]
        cmd = [
            sys.executable, "-m", "websockify",
            str(self.web_port),
            f"--token-plugin=TokenFile",
            f"--token-source={self.token_file}",
            "--web", str(self.novnc_path),
            "--heartbeat", "30",
            "--log-file", str(Path(tempfile.gettempdir()) / "websockify.log"),  # 日志
        ]

        print(f"启动WebSockify: {' '.join(cmd)}")
        self.websockify_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        time.sleep(2)  # 等待启动
        if self.websockify_process.poll() is None:
            self.is_running = True
            print("✅ 服务启动成功")
            return True
        else:
            _, stderr = self.websockify_process.communicate()
            raise RuntimeError(f"启动失败: {stderr}")

    def _stop_service(self):
        """停止服务"""
        if self.websockify_process:
            print("停止旧WebSockify进程...")
            self.websockify_process.terminate()
            self.websockify_process.wait(timeout=5)
            self.websockify_process = None
            self.is_running = False

    def _reload_service(self):
        """重载服务（优雅重启）"""
        print("\n" + "=" * 60)
        print("检测到配置变更，正在优雅重启...")
        print("=" * 60)

        # 备份当前配置
        current_servers = self.vnc_servers.copy()

        try:
            # 快速重启
            self._start_service()
            print("✅ 重载完成，新配置已生效")
            self.list_servers()  # 显示当前配置
        except Exception as e:
            # 回滚
            print(f"❌ 重载失败: {e}，正在回滚...")
            self.vnc_servers = current_servers
            self._start_service()
            raise

    def add_server(self, token, addr):
        """
        动态添加VNC服务器
        :param token: 唯一标识符
        :param addr: "IP:端口" 格式
        """
        if not token or not addr:
            raise ValueError("token和addr不能为空")

        if ":" not in addr:
            addr = f"{addr}:5900"  # 自动添加默认端口

        if token in self.vnc_servers:
            print(f"⚠️  Token '{token}' 已存在，将更新为 {addr}")

        self.vnc_servers[token] = addr
        print(f"添加服务器: {token} -> {addr}")

        if self.is_running:
            self._reload_service()

    def remove_server(self, token):
        """
        动态删除VNC服务器
        :param token: 要删除的token
        """
        if token not in self.vnc_servers:
            print(f"⚠️  Token '{token}' 不存在")
            return False

        del self.vnc_servers[token]
        print(f"移除服务器: {token}")

        if self.is_running:
            self._reload_service()
        return True

    def list_servers(self):
        """列出当前所有VNC服务器"""
        print("\n当前VNC服务器列表:")
        if not self.vnc_servers:
            print("  (空)")
        for token, addr in self.vnc_servers.items():
            print(f"  【{token}】: {addr}")
        return self.vnc_servers.copy()

    def get_url(self, token):
        """获取指定token的访问链接"""
        if token not in self.vnc_servers:
            raise KeyError(f"Token '{token}' 不存在")

        # noVNC连接参数
        # path参数需要encode，因为包含特殊字符
        websocket_path = f"websockify?token={token}"
        params = {
            "host": "localhost",
            "port": self.web_port,
            "path": websocket_path,
            "autoconnect": "true"
        }
        query = urllib.parse.urlencode(params)
        return f"http://localhost:{self.web_port}/vnc.html?{query}"

    def get_all_urls(self):
        """获取所有访问链接"""
        urls = {}
        for token in self.vnc_servers.keys():
            urls[token] = self.get_url(token)
        return urls

    def stop(self):
        """完全停止服务并清理"""
        print("\n正在停止动态VNC代理服务...")
        self._stop_service()
        if self.token_file and self.token_file.exists():
            self.token_file.unlink()
            print(f"已清理Token文件: {self.token_file}")
        print("服务已完全停止")


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 初始配置
    initial_servers = {
        "testvm": "127.0.0.1:5901",
    }

    # 启动动态代理服务
    proxy = DynamicVNCProxy(
        vnc_servers=initial_servers,
        web_port=6080,
        novnc_path="./VNCConsole/Sources"
    )

    print("\n" + "=" * 60)
    print("服务已启动，请通过以下链接访问:")
    for token, url in proxy.get_all_urls().items():
        print(f"  【{token}】: {url}")
    print("=" * 60)

    # 模拟动态操作
    try:
        while True:
            print("\n" + "=" * 60)
            print("操作选项:")
            print("  1. 添加服务器")
            print("  2. 移除服务器")
            print("  3. 列出所有服务器")
            print("  4. 退出")

            choice = input("\n选择操作 (1-4): ").strip()

            if choice == "1":
                token = input("输入Token名称: ").strip()
                addr = input("输入VNC地址 (IP:端口): ").strip()
                try:
                    proxy.add_server(token, addr)
                    print(f"✅ 添加成功！新访问链接: {proxy.get_url(token)}")
                except Exception as e:
                    print(f"❌ 添加失败: {e}")

            elif choice == "2":
                token = input("输入要移除的Token: ").strip()
                try:
                    proxy.remove_server(token)
                    print(f"✅ 移除成功！")
                except Exception as e:
                    print(f"❌ 移除失败: {e}")

            elif choice == "3":
                proxy.list_servers()
                print("\n访问链接:")
                for token, url in proxy.get_all_urls().items():
                    print(f"  {token}: {url}")

            elif choice == "4":
                break

            else:
                print("无效选项")

    except KeyboardInterrupt:
        print("\n收到中断信号")
    finally:
        proxy.stop()