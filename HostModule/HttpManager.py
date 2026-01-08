import os
import time
import signal
import subprocess
import json
import random
from pathlib import Path

# 导入DataManage模块用于数据库操作
from HostModule.DataManager import DataManager


class HttpManager:
    def __init__(self, config_filename="HttpManage.txt"):
        self.binary_proc = None
        self.config_path = Path("HostConfig")
        self.config_file = Path(f"DataSaving/{config_filename}")
        self.binary_path = ""
        # 为每个实例生成随机管理端口（8000-9000范围）
        self.admin_port = random.randint(8000, 9000)
        # proxys_sshd格式: {port: {token:(ip,port)}}
        self.proxys_sshd = {}
        # proxys_list格式: {domain: {"target": (port, ip), "is_https": bool, "listen_port": int}}
        self.proxys_list = {}

        if os.name == 'nt':
            self.binary_path = ".\\HostConfig\\Server_x64.exe"
        else:
            self.binary_path = "HostConfig/Server_x64"
        self.config_path.mkdir(exist_ok=True)

        # 初始化数据库管理器
        self.db_manager = DataManager()

        # 生成初始配置文件
        self._generate_config()
        print(f"HttpManager初始化完成，管理端口: {self.admin_port}，配置文件: {self.config_file}")

    # 初始化SSH代理管理 ########################################
    def start_ssh(self, port: int):
        if str(port) not in self.proxys_sshd:
            self.proxys_sshd[port] = {}

    # 关闭SSH代理的管理 ########################################
    def close_ssh(self, port: int):
        if str(port) in self.proxys_sshd:
            del self.proxys_sshd[str(port)]

    # 添加SSH的代理配置 ########################################
    def proxy_ssh(self, token, target_ip, target_port):
        try:
            # 检查是否已有相同token的配置
            for port, token_dict in self.proxys_sshd.items():
                if token in token_dict:
                    print(f"令牌 {token} 的SSH代理配置已存在")
                    return False

            # 使用固定端口1884作为监听端口
            listen_port = 1884

            # 如果还没有1884端口的配置，初始化一个空字典
            if listen_port not in self.proxys_sshd:
                self.proxys_sshd[listen_port] = {}

            # 添加到SSH代理配置
            self.proxys_sshd[listen_port][token] = (target_ip, target_port)
            print(f"SSH代理已添加: /{token} -> {target_ip}:{target_port} (统一端口: {listen_port})")

            # 重新生成配置文件
            self._generate_config()

            # 重载Caddy配置
            return self.loads_web()

        except Exception as e:
            print(f"添加SSH代理配置时发生错误: {str(e)}")
            return False

    def _generate_config(self):
        """根据proxys_list和proxys_sshd生成完整的Caddy配置文件"""
        # 使用实例的管理端口生成全局配置
        config = f"{{\n\tadmin localhost:{self.admin_port}\n}}\n\n"

        # 生成普通代理配置
        for domain, proxy_info in self.proxys_list.items():
            port, ip = proxy_info["target"]
            is_https = proxy_info.get("is_https", True)
            listen_port = proxy_info.get("listen_port")

            # 前端监听协议和端口
            should_add_port = listen_port not in (None, 0, 80, 443)
            if domain.startswith("/") or domain == "":
                frontend_domain = f"*:{listen_port}"
            elif should_add_port:
                protocol = "https" if is_https else "http"
                frontend_domain = f"{protocol}://{domain}:{listen_port}"
            else:
                frontend_domain = domain if is_https else f"http://{domain}"

            # 后端目标协议
            backend_protocol = "https" if is_https else "http"
            if domain.find("/") > -1:  # 存在子路径
                sub_path = "/" + "/".join(domain.split("/")[1:])
                config += f"{frontend_domain} {{\n\t@secret path {sub_path}\n\treverse_proxy {backend_protocol}://{ip}:{port}\n}}\n\n"
            else:
                config += f"{frontend_domain} {{\n\treverse_proxy {backend_protocol}://{ip}:{port}\n}}\n\n"

        # 生成SSH代理配置 - 使用统一的*:1884端口和handle_path方式
        if self.proxys_sshd:
            for listen_port, token_dict in self.proxys_sshd.items():
                config += ":%s {\n" % listen_port
                for token, (target_ip, target_port) in token_dict.items():
                    config += f"\thandle_path /{token}* {{\n"
                    config += f"\t\treverse_proxy http://{target_ip}:{target_port} {{\n"
                    config += f"\t\theader_up Host {{http.request.host}}\n"
                    config += f"\t\theader_up X-Real-IP {{http.request.remote.host}}\n"
                    config += f"\t\theader_up X-Forwarded-For {{http.request.remote.host}}\n"
                    config += f"\t\theader_up REMOTE-HOST {{http.request.remote.host}}\n"
                    config += f"\t\theader_up Connection {{http.request.header.Connection}}\n"
                    config += f"\t\theader_up Upgrade {{http.request.header.Upgrade}}\n"
                    config += f"\t}}\n"
                    config += f"\t}}\n"
                config += "}\n\n"

        self.config_file.write_text(config)
        return True

    def load_proxys(self):
        """从数据库加载代理配置"""
        try:
            # 从数据库获取代理配置
            web_proxies = self.db_manager.get_web_proxy()
            self.proxys_list = {}

            for proxy in web_proxies:
                web_addr = proxy.get('web_addr', '')
                if web_addr:
                    self.proxys_list[web_addr] = {
                        "target": (proxy.get('lan_port', 80), proxy.get('lan_addr', '')),
                        "is_https": proxy.get('is_https', True),
                        "listen_port": None  # 数据库中没有存储，设为默认
                    }

            print(f"已从数据库加载 {len(self.proxys_list)} 个代理配置")
            return True
        except Exception as e:
            print(f"加载代理配置失败: {str(e)}")
            self.proxys_list = {}
            return False

    def save_proxy_to_db(self, domain, proxy_info):
        """将代理配置保存到数据库"""
        try:
            target_port, target_ip = proxy_info["target"]
            proxy_data = {
                'lan_port': target_port,
                'lan_addr': target_ip,
                'web_addr': domain,
                'web_tips': f"代理配置: {domain} -> {target_ip}:{target_port}",
                'is_https': proxy_info.get('is_https', True)
            }
            return self.db_manager.add_web_proxy(proxy_data)
        except Exception as e:
            print(f"保存代理到数据库失败: {str(e)}")
            return False

    def delete_proxy_from_db(self, domain):
        """从数据库删除代理配置"""
        try:
            return self.db_manager.del_web_proxy(domain)
        except Exception as e:
            print(f"从数据库删除代理失败: {str(e)}")
            return False

    def start_web(self):
        """启动Caddy服务"""
        try:
            cmd = [self.binary_path, "run", "--config", str(self.config_file), "--adapter", "caddyfile"]

            print(" ".join(cmd))
            self.binary_proc = subprocess.Popen(cmd, shell=True)
            time.sleep(2)  # 等待进程启动

            if self.binary_proc.poll() is None:
                print(f"Caddy进程已启动，PID: {self.binary_proc.pid}")
                return True

            return False

        except FileNotFoundError:
            print("错误: 找不到caddy可执行文件")
            return False
        except Exception as e:
            print(f"启动Caddy时发生错误: {str(e)}")
            return False

    def proxy_add(self, target, domain, is_https=True, listen_port=None, persistent=True):
        """添加代理配置"""
        try:
            # 检查域名是否已存在
            if domain in self.proxys_list:
                print(f"域名 {domain} 的配置已存在")
                return False

            # 添加到内存配置
            self.proxys_list[domain] = {
                "target": target,
                "is_https": is_https,
                "listen_port": listen_port
            }

            # 重新生成配置文件
            self._generate_config()

            # 保存到数据库（只有persistent为True时才写入）
            if persistent:
                self.save_proxy_to_db(domain, self.proxys_list[domain])
            else:
                print(f"代理 {domain} 为临时代理，不写入数据库")

            # 重载Caddy配置
            return self.loads_web()

        except Exception as e:
            print(f"添加代理配置时发生错误: {str(e)}")
            # 回滚
            if domain in self.proxys_list:
                del self.proxys_list[domain]
            return False

    def proxy_del(self, domain):
        """删除代理配置"""
        try:
            # 检查域名是否存在
            if domain not in self.proxys_list:
                print(f"未找到匹配的代理配置: {domain}")
                print(f"当前已有的域名: {list(self.proxys_list.keys())}")
                return False

            # 备份配置（用于回滚）
            backup = self.proxys_list[domain]

            # 从内存配置中删除
            del self.proxys_list[domain]

            # 重新生成配置文件
            self._generate_config()

            # 从数据库删除（不写入JSON文件）
            self.delete_proxy_from_db(domain)

            # 重载Caddy配置
            result = self.loads_web()

            if not result:
                # 回滚
                self.proxys_list[domain] = backup
                self._generate_config()
                self.save_proxy_to_db(domain, backup)

            return result

        except Exception as e:
            print(f"删除代理配置时发生错误: {str(e)}")
            return False

    def close_web(self):
        """停止Caddy服务"""
        try:
            if self.binary_proc and self.binary_proc.poll() is None:
                self.binary_proc.terminate()
                try:
                    self.binary_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.binary_proc.kill()
                    self.binary_proc.wait()
                print("Caddy进程已停止")
                return True
            return False
        except Exception as e:
            print(f"停止Caddy时发生错误: {str(e)}")
            return False

    def loads_web(self):
        """重载Caddy配置"""
        try:
            # 尝试重载配置（无论binary_proc状态如何）
            if os.name == 'nt':
                # 使用实例的管理端口进行重载
                reload_cmd = [self.binary_path, "reload", "--config",
                              str(self.config_file), "--adapter", "caddyfile",
                              "--address", f"localhost:{self.admin_port}"]
                result = subprocess.run(reload_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"Caddy配置已重载（管理端口: {self.admin_port}）")
                    return True
                else:
                    print(f"重载失败，尝试启动服务: {result.stderr}")
                    return self.start_web()
            else:
                # Linux/Mac: 如果有进程引用则发送信号
                if self.binary_proc and self.binary_proc.poll() is None:
                    self.binary_proc.send_signal(signal.SIGUSR1)
                    print(f"Caddy配置已重载（管理端口: {self.admin_port}）")
                    return True
                else:
                    return self.start_web()
        except Exception as e:
            print(f"重载Caddy配置时发生错误: {str(e)}")
            return False


# 使用示例
if __name__ == "__main__":
    manager = HttpManager()

    try:
        # 启动服务
        manager.start_web()
        time.sleep(2)

        # 添加代理（使用HTTP协议，监听8081端口避免80端口冲突）
        manager.proxy_add((1880, "127.0.0.1"), "local.524228.xyz", is_https=False, listen_port=1889)

        # 等待一段时间
        time.sleep(100)

        # 删除代理
        manager.proxy_del("local.524228.xyz")

        # 停止服务
        manager.close_web()
    except KeyboardInterrupt as e:
        manager.close_web()