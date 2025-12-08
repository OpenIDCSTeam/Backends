"""
VNC Caddy代理管理器
使用Caddy反向代理多个独立的websockify实例
每个VNC服务器启动一个独立的websockify进程，由Caddy统一代理
"""
import subprocess
import urllib.parse
import os
import sys
import time
import atexit
import json
from pathlib import Path
import tempfile
import signal


class VNCCaddyProxy:
    """使用Caddy反向代理管理多个VNC连接"""

    def __init__(self, vnc_servers=None, caddy_port=6080, novnc_path=None, base_ws_port=16900):
        """
        初始化VNC Caddy代理
        :param vnc_servers: 初始服务器字典，格式 {"token": "IP:端口"}
        :param caddy_port: Caddy监听端口
        :param novnc_path: noVNC目录路径
        :param base_ws_port: websockify端口起始值
        """
        self.vnc_servers = vnc_servers or {}
        self.caddy_port = caddy_port
        self.novnc_path = Path(novnc_path) if novnc_path else Path(r"./VNCConsole/Sources")
        self.base_ws_port = base_ws_port

        # 进程管理
        self.websockify_processes = {}  # {token: (process, port)}
        self.caddy_process = None
        self.is_running = False

        # 配置文件路径
        self.temp_dir = Path(tempfile.gettempdir()) / "vnc_caddy"
        self.temp_dir.mkdir(exist_ok=True)
        self.caddyfile_path = self.temp_dir / "Caddyfile"

        # 验证noVNC路径
        if not self.novnc_path.exists():
            raise FileNotFoundError(f"noVNC路径不存在: {self.novnc_path}")

        # 注册退出清理
        atexit.register(self.stop)

        # 启动服务
        self._start_all()

    def _get_next_port(self):
        """获取下一个可用的websockify端口"""
        used_ports = {port for _, port in self.websockify_processes.values()}
        port = self.base_ws_port
        while port in used_ports:
            port += 1
        return port

    def _start_websockify(self, token, vnc_addr):
        """
        启动单个websockify实例
        :param token: 服务器标识
        :param vnc_addr: VNC地址 (IP:端口)
        :return: (进程, 端口)
        """
        port = self._get_next_port()

        cmd = [
            sys.executable, "-m", "websockify",
            str(port),
            vnc_addr,
            "--heartbeat", "30",
        ]

        print(f"启动WebSockify [{token}]: 端口{port} -> {vnc_addr}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )

        time.sleep(0.5)  # 等待启动
        if process.poll() is not None:
            _, stderr = process.communicate()
            raise RuntimeError(f"WebSockify启动失败 [{token}]: {stderr}")

        self.websockify_processes[token] = (process, port)
        return process, port

    def _stop_websockify(self, token):
        """停止单个websockify实例"""
        if token in self.websockify_processes:
            process, port = self.websockify_processes[token]
            print(f"停止WebSockify [{token}]: 端口{port}")
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
            del self.websockify_processes[token]

    def _generate_caddyfile(self):
        """生成Caddy配置文件"""
        novnc_abs_path = self.novnc_path.resolve()

        # 构建反向代理规则 - 使用route确保按顺序匹配
        proxy_rules = []
        for token, (_, port) in self.websockify_processes.items():
            # 使用 rewrite + reverse_proxy 实现路径代理
            safe_token = token.replace('-', '_').replace('.', '_')
            proxy_rules.append(f"""
    # WebSocket代理: {token} -> localhost:{port}
    @{safe_token} path /websockify/{token}
    handle @{safe_token} {{
        reverse_proxy localhost:{port}
    }}""")

        caddyfile_content = f"""{{
    auto_https off
    admin off
}}

:{self.caddy_port} {{
    {"".join(proxy_rules)}

    # 静态文件服务 (Sources)
    file_server {{
        root "{novnc_abs_path}"
    }}

    log {{
        output file "{self.temp_dir}/caddy.log"
    }}
}}
"""
        with open(self.caddyfile_path, "w", encoding="utf-8") as f:
            f.write(caddyfile_content)

        print(f"Caddyfile已生成: {self.caddyfile_path}")
        return self.caddyfile_path

    def _start_caddy(self):
        """启动Caddy服务"""
        if self.caddy_process:
            self._stop_caddy()

        self._generate_caddyfile()

        cmd = [
            "caddy", "run",
            "--config", str(self.caddyfile_path),
        ]

        print(f"启动Caddy: {' '.join(cmd)}")
        self.caddy_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )

        time.sleep(1)  # 等待启动
        if self.caddy_process.poll() is not None:
            _, stderr = self.caddy_process.communicate()
            raise RuntimeError(f"Caddy启动失败: {stderr}")

        print("✅ Caddy启动成功")

    def _stop_caddy(self):
        """停止Caddy服务"""
        if self.caddy_process:
            print("停止Caddy...")
            self.caddy_process.terminate()
            try:
                self.caddy_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.caddy_process.kill()
            self.caddy_process = None

    def _reload_caddy(self):
        """重载Caddy配置（由于禁用了admin，使用重启方式）"""
        print("重载Caddy配置（重启方式）...")
        self._stop_caddy()
        self._start_caddy()
        print("✅ Caddy配置已重载")

    def _start_all(self):
        """启动所有服务"""
        print("\n" + "=" * 60)
        print("正在启动VNC Caddy代理服务...")
        print("=" * 60)

        # 1. 启动所有websockify实例
        for token, addr in self.vnc_servers.items():
            self._start_websockify(token, addr)

        # 2. 启动Caddy
        self._start_caddy()

        self.is_running = True
        print("\n✅ 所有服务已启动")

    def add_server(self, token, addr):
        """
        动态添加VNC服务器
        :param token: 唯一标识符
        :param addr: "IP:端口" 格式
        """
        if not token or not addr:
            raise ValueError("token和addr不能为空")

        if ":" not in addr:
            addr = f"{addr}:5900"

        # 如果已存在，先移除
        if token in self.vnc_servers:
            print(f"⚠️ Token '{token}' 已存在，将更新为 {addr}")
            self._stop_websockify(token)

        self.vnc_servers[token] = addr

        # 启动新的websockify
        self._start_websockify(token, addr)

        # 重载Caddy配置
        if self.is_running:
            self._reload_caddy()

        print(f"✅ 服务器已添加: {token} -> {addr}")

    def remove_server(self, token):
        """
        动态删除VNC服务器
        :param token: 要删除的token
        """
        if token not in self.vnc_servers:
            print(f"⚠️ Token '{token}' 不存在")
            return False

        # 停止websockify
        self._stop_websockify(token)
        del self.vnc_servers[token]

        # 重载Caddy配置
        if self.is_running:
            self._reload_caddy()

        print(f"✅ 服务器已移除: {token}")
        return True

    def list_servers(self):
        """列出当前所有VNC服务器"""
        print("\n当前VNC服务器列表:")
        if not self.vnc_servers:
            print("  (空)")
        for token, addr in self.vnc_servers.items():
            if token in self.websockify_processes:
                _, port = self.websockify_processes[token]
                print(f"  【{token}】: {addr} (ws端口: {port})")
            else:
                print(f"  【{token}】: {addr} (未运行)")
        return self.vnc_servers.copy()

    def get_url(self, token):
        """获取指定token的访问链接"""
        if token not in self.vnc_servers:
            raise KeyError(f"Token '{token}' 不存在")

        if token not in self.websockify_processes:
            raise RuntimeError(f"Token '{token}' 的websockify未运行")

        _, ws_port = self.websockify_processes[token]

        # noVNC连接参数 - 直接连接对应的websockify端口
        # Caddy只提供静态文件服务，WebSocket直连websockify
        params = {
            "host": "localhost",
            "port": ws_port,  # 直接连接websockify端口
            "autoconnect": "true"
        }
        query = urllib.parse.urlencode(params)
        # 从Caddy获取静态文件，但WebSocket连接直接到websockify
        return f"http://localhost:{self.caddy_port}/vnc.html?{query}"

    def get_all_urls(self):
        """获取所有访问链接"""
        return {token: self.get_url(token) for token in self.vnc_servers}

    def stop(self):
        """完全停止所有服务并清理"""
        print("\n正在停止VNC Caddy代理服务...")

        # 停止所有websockify
        for token in list(self.websockify_processes.keys()):
            self._stop_websockify(token)

        # 停止Caddy
        self._stop_caddy()

        self.is_running = False
        print("✅ 服务已完全停止")


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 初始配置
    initial_servers = {
        "testvm": "127.0.0.1:5901",
    }

    # 启动代理服务
    proxy = VNCCaddyProxy(
        vnc_servers=initial_servers,
        caddy_port=6080,
        novnc_path="./VNCConsole/Sources"
    )

    print("\n" + "=" * 60)
    print(f"VNC Caddy代理服务已启动!")
    print(f"Caddy统一入口端口: {proxy.caddy_port}")
    print("-" * 60)
    print("访问链接:")
    for token, url in proxy.get_all_urls().items():
        print(f"  【{token}】: {url}")
    print("=" * 60)

    # 交互式操作
    try:
        while True:
            print("\n" + "=" * 60)
            print("操作选项:")
            print("  1. 添加服务器")
            print("  2. 移除服务器")
            print("  3. 列出所有服务器")
            print("  4. 显示访问链接")
            print("  5. 退出")

            choice = input("\n选择操作 (1-5): ").strip()

            if choice == "1":
                token = input("输入Token名称: ").strip()
                addr = input("输入VNC地址 (IP:端口): ").strip()
                try:
                    proxy.add_server(token, addr)
                    print(f"新访问链接: {proxy.get_url(token)}")
                except Exception as e:
                    print(f"❌ 添加失败: {e}")

            elif choice == "2":
                token = input("输入要移除的Token: ").strip()
                proxy.remove_server(token)

            elif choice == "3":
                proxy.list_servers()

            elif choice == "4":
                print("\n访问链接:")
                for token, url in proxy.get_all_urls().items():
                    print(f"  【{token}】: {url}")

            elif choice == "5":
                break

            else:
                print("无效选项")

    except KeyboardInterrupt:
        print("\n收到中断信号")
    finally:
        proxy.stop()
