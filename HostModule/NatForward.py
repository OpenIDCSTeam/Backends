import asyncio
import json
import signal
from pathlib import Path
from typing import Dict, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class PortForwarder:
    def __init__(self, config_file: str):
        self.config_file = Path(config_file)
        self.forwards: Dict[int, asyncio.Task] = {}
        self.running = True

    async def forward_connection(self, reader, writer, dest_host, dest_port):
        """实际转发数据的协程"""
        try:
            # 连接到目标服务器
            dest_reader, dest_writer = await asyncio.open_connection(dest_host, dest_port)

            # 双向转发
            async def pipe(reader, writer):
                while self.running:
                    data = await reader.read(4096)
                    if not data:
                        break
                    writer.write(data)
                    await writer.drain()

            await asyncio.gather(
                pipe(reader, dest_writer),
                pipe(dest_reader, writer)
            )
        except Exception as e:
            print(f"转发错误: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            dest_writer.close()
            await dest_writer.wait_closed()

    async def start_server(self, local_port: int, dest_host: str, dest_port: int):
        """启动单个端口转发服务"""
        try:
            server = await asyncio.start_server(
                lambda r, w: self.forward_connection(r, w, dest_host, dest_port),
                '0.0.0.0', local_port
            )
            print(f"端口 {local_port} -> {dest_host}:{dest_port} 已启动")

            async with server:
                await server.serve_forever()
        except Exception as e:
            print(f"端口 {local_port} 启动失败: {e}")

    def load_config(self):
        """从JSON配置文件加载转发规则"""
        try:
            with open(self.config_file) as f:
                config = json.load(f)
            return {int(k): v for k, v in config.items()}
        except Exception as e:
            print(f"配置加载失败: {e}")
            return {}

    async def run(self):
        """主运行循环"""
        # 初始加载配置
        current_rules = self.load_config()
        active_ports: Set[int] = set()

        # 启动初始转发
        for port, rule in current_rules.items():
            task = asyncio.create_task(
                self.start_server(port, rule['host'], rule['port'])
            )
            self.forwards[port] = task
            active_ports.add(port)

        # 配置文件监控
        class ConfigHandler(FileSystemEventHandler):
            def on_modified(_self, event):
                if Path(event.src_path) == self.config_file:
                    print("检测到配置变更，准备重载...")
                    nonlocal current_rules, active_ports
                    new_rules = self.load_config()

                    # 找出需要停止和新增的端口
                    to_stop = active_ports - set(new_rules.keys())
                    to_start = set(new_rules.keys()) - active_ports
                    to_update = active_ports & set(new_rules.keys())

                    # 停止已删除的转发（不影响现有连接）
                    for port in to_stop:
                        self.forwards[port].cancel()
                        del self.forwards[port]
                        active_ports.remove(port)
                        print(f"端口 {port} 已停止")

                    # 启动新增的转发
                    for port in to_start:
                        rule = new_rules[port]
                        task = asyncio.create_task(
                            self.start_server(port, rule['host'], rule['port'])
                        )
                        self.forwards[port] = task
                        active_ports.add(port)

                    # 更新现有转发（可选：重启或保持）
                    for port in to_update:
                        if current_rules[port] != new_rules[port]:
                            # 这里可以选择重启或保持现有连接
                            print(f"端口 {port} 配置已更新（下次连接生效）")

                    current_rules = new_rules

        observer = Observer()
        observer.schedule(ConfigHandler(), str(self.config_file.parent))
        observer.start()

        # 等待信号退出
        signal.signal(signal.SIGINT, lambda s, f: setattr(self, 'running', False))
        while self.running:
            await asyncio.sleep(1)

        # 清理
        observer.stop()
        observer.join()
        for task in self.forwards.values():
            task.cancel()


if __name__ == '__main__':
    forwarder = PortForwarder('port-forward.json')
    asyncio.run(forwarder.run())