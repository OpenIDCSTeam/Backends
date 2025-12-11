import os
import subprocess
import time
import signal
from pathlib import Path

# Caddy全局配置：启用本地管理端点（仅允许localhost访问）
GLOBAL_CONFIG = """{
	admin localhost:8019
}

"""


class HttpManage:
    def __init__(self):
        self.binary_proc = None
        self.config_dir = Path("HostConfig")
        self.config_file = Path("DataSaving/HttpManage.txt")
        self.binary_path = ""
        # proxys_list格式: {domain: {"target": (port, ip), "is_https": bool, "listen_port": int}}
        self.proxys_list: dict = {}
        if os.name == 'nt':
            self.binary_path = ".\\HostConfig\\Server_x64.exe"
        else:
            self.binary_path = "HostConfig/Server_x64"
        self.config_dir.mkdir(exist_ok=True)
        
        # 加载已保存的代理配置
        self.load_proxys()
        # 生成初始配置文件
        self._generate_config()

    def _generate_config(self):
        """根据proxys_list生成完整的Caddy配置文件"""
        config = GLOBAL_CONFIG
        
        for domain, proxy_info in self.proxys_list.items():
            port, ip = proxy_info["target"]
            is_https = proxy_info.get("is_https", True)
            listen_port = proxy_info.get("listen_port")
            
            # 前端监听协议和端口
            should_add_port = listen_port not in (None, 0, 80, 443)
            
            if should_add_port:
                protocol = "https" if is_https else "http"
                frontend_domain = f"{protocol}://{domain}:{listen_port}"
            else:
                frontend_domain = domain if is_https else f"http://{domain}"
            
            # 后端目标协议
            backend_protocol = "https" if is_https else "http"
            
            config += f"{frontend_domain} {{\n\treverse_proxy {backend_protocol}://{ip}:{port}\n}}\n\n"
        
        self.config_file.write_text(config)
        return True
    
    def save_proxys(self):
        """保存代理配置到文件（用于持久化）"""
        import json
        save_file = Path("DataSaving/HttpProxys.json")
        try:
            with open(save_file, 'w', encoding='utf-8') as f:
                json.dump(self.proxys_list, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存代理配置失败: {str(e)}")
            return False
    
    def load_proxys(self):
        """从文件加载代理配置"""
        import json
        save_file = Path("DataSaving/HttpProxys.json")
        try:
            if save_file.exists():
                with open(save_file, 'r', encoding='utf-8') as f:
                    self.proxys_list = json.load(f)
                print(f"已加载 {len(self.proxys_list)} 个代理配置")
            return True
        except Exception as e:
            print(f"加载代理配置失败: {str(e)}")
            self.proxys_list = {}
            return False

    def start_web(self):
        """启动Caddy服务"""
        try:
            cmd = [self.binary_path, "run", "--config", str(self.config_file), "--adapter", "caddyfile"]

            print(" ".join(cmd))
            # 根据操作系统设置进程创建参数
            # kwargs = {
            #     "stdout": subprocess.PIPE,
            #     "stderr": subprocess.PIPE,
            # }
            # if os.name == 'nt':
            #     kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            # else:
            #     kwargs["preexec_fn"] = os.setsid

            self.binary_proc = subprocess.Popen(cmd,
                                                # **kwargs,
                                                shell=True)
            time.sleep(2)  # 等待进程启动

            if self.binary_proc.poll() is None:
                print(f"Caddy进程已启动，PID: {self.binary_proc.pid}")
                return True

            # _, stderr = self.binary_proc.communicate()
            # print(f"Caddy启动失败: {stderr.decode()}")
            return False

        except FileNotFoundError:
            print("错误: 找不到caddy可执行文件")
            return False
        except Exception as e:
            print(f"启动Caddy时发生错误: {str(e)}")
            return False

    def proxy_add(self, target, domain, is_https=True, listen_port=None):
        """添加代理配置
        
        Args:
            target: (port, ip) 后端目标地址
            domain: 域名
            is_https: 是否使用HTTPS
            listen_port: 自定义监听端口，如果不指定则使用默认端口(HTTP:80, HTTPS:443)
        """
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
            
            # 保存到持久化文件
            self.save_proxys()
            
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
            
            # 保存到持久化文件
            self.save_proxys()
            
            # 重载Caddy配置
            result = self.loads_web()
            
            if not result:
                # 回滚
                self.proxys_list[domain] = backup
                self._generate_config()
                self.save_proxys()
            
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
                reload_cmd = [self.binary_path, "reload", "--config",
                              str(self.config_file), "--adapter", "caddyfile"]
                result = subprocess.run(reload_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print("Caddy配置已重载")
                    return True
                else:
                    print(f"重载失败，尝试启动服务: {result.stderr}")
                    return self.start_web()
            else:
                # Linux/Mac: 如果有进程引用则发送信号
                if self.binary_proc and self.binary_proc.poll() is None:
                    self.binary_proc.send_signal(signal.SIGUSR1)
                    print("Caddy配置已重载")
                    return True
                else:
                    return self.start_web()
        except Exception as e:
            print(f"重载Caddy配置时发生错误: {str(e)}")
            return False


# 使用示例
if __name__ == "__main__":
    manager = HttpManage()

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