import os
import subprocess
import time
import signal
import psutil
from pathlib import Path


class HttpManage:
    def __init__(self):
        self.caddy_process = None
        self.config_dir = Path("HostConfig")
        self.config_file = self.config_dir / "HttpManage.txt"
        self.caddy_binary = "./HostConfig/caddy_x64.exe"
        
        self.config_dir.mkdir(exist_ok=True)
        
        if not self.config_file.exists():
            self.config_file.touch()
            self.config_file.write_text("")
    
    def start_web(self):
        try:
            # 检查caddy进程是否已经运行
            if self._is_caddy_running():
                print("Caddy进程已经在运行")
                return True
            
            # 启动caddy进程，使用配置文件
            cmd = [self.caddy_binary, "run", "--config", str(self.config_file)]
            
            # 在Windows上需要创建新的进程组
            if os.name == 'nt':
                self.caddy_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                self.caddy_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid
                )
            
            # 等待一小段时间确认进程启动
            time.sleep(2)
            
            if self.caddy_process.poll() is None:
                print(f"Caddy进程已启动，PID: {self.caddy_process.pid}")
                return True
            else:
                stdout, stderr = self.caddy_process.communicate()
                print(f"Caddy启动失败: {stderr.decode()}")
                return False
                
        except FileNotFoundError:
            print("错误: 找不到caddy可执行文件，请确保caddy已安装并在PATH中")
            return False
        except Exception as e:
            print(f"启动Caddy时发生错误: {str(e)}")
            return False
    
    def proxy_add(self, target, domain, is_https=True):
        """添加代理配置"""
        try:
            port, ip = target
            target_url = f"{ip}:{port}"
            protocol = "https" if is_https else "http"
            
            proxy_config = f"{domain} {{\n    reverse_proxy {protocol}://{target_url}\n}}\n\n"
            
            current_config = self.config_file.read_text() if self.config_file.exists() else ""
            
            if f"{domain} {{" in current_config:
                print(f"域名 {domain} 的配置已存在")
                return False
            
            self.config_file.write_text(current_config + proxy_config)
            return self._reload_caddy()
            
        except Exception as e:
            print(f"添加代理配置时发生错误: {str(e)}")
            return False
    
    def proxy_del(self, identifier, is_http=True):
        """删除代理配置"""
        try:
            if not self.config_file.exists():
                print("配置文件不存在")
                return False
            
            current_config = self.config_file.read_text()
            lines = current_config.split('\n')
            new_lines = []
            i = 0
            removed = False
            
            while i < len(lines):
                line = lines[i].strip()
                
                if is_http and line.endswith(" {") and identifier in line:
                    domain_part = line.split(' {')[0].strip()
                    if domain_part == identifier:
                        i += 1
                        brace_count = 1
                        while i < len(lines) and brace_count > 0:
                            if '{' in lines[i]:
                                brace_count += lines[i].count('{')
                            if '}' in lines[i]:
                                brace_count -= lines[i].count('}')
                            i += 1
                        removed = True
                        continue
                elif not is_http and '{' in line:
                    i += 1
                    block_content = []
                    brace_count = 1
                    found_target = False
                    
                    port, ip = identifier
                    search_identifier = f"{ip}:{port}"
                    
                    while i < len(lines) and brace_count > 0:
                        block_line = lines[i]
                        block_content.append(block_line)
                        if search_identifier in block_line:
                            found_target = True
                        if '{' in block_line:
                            brace_count += block_line.count('{')
                        if '}' in block_line:
                            brace_count -= block_line.count('}')
                        i += 1
                    
                    if found_target:
                        removed = True
                        continue
                    else:
                        new_lines.append(lines[i-1])
                        new_lines.extend(block_content)
                
                if i < len(lines):
                    new_lines.append(lines[i])
                i += 1
            
            if removed:
                self.config_file.write_text('\n'.join(new_lines))
                return self._reload_caddy()
            else:
                print(f"未找到匹配的代理配置: {identifier}")
                return False
                
        except Exception as e:
            print(f"删除代理配置时发生错误: {str(e)}")
            return False
    
    def close_web(self):
        try:
            # 首先尝试通过保存的进程对象停止
            if self.caddy_process and self.caddy_process.poll() is None:
                self.caddy_process.terminate()
                try:
                    self.caddy_process.wait(timeout=5)
                    print("Caddy进程已停止")
                    return True
                except subprocess.TimeoutExpired:
                    self.caddy_process.kill()
                    self.caddy_process.wait()
                    print("Caddy进程已强制停止")
                    return True
            
            # 如果进程对象不可用，通过进程名查找并停止
            return self._kill_caddy_processes()
            
        except Exception as e:
            print(f"停止Caddy时发生错误: {str(e)}")
            return False
    
    def _is_caddy_running(self):
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and 'caddy' in proc.info['name'].lower():
                    return True
            return False
        except Exception:
            return False
    
    def _kill_caddy_processes(self):
        try:
            killed = False
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and 'caddy' in proc.info['name'].lower():
                    proc.terminate()
                    killed = True
            
            if killed:
                time.sleep(2)  # 等待进程优雅退出
                # 强制杀死仍在运行的进程
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] and 'caddy' in proc.info['name'].lower():
                        proc.kill()
            
            return killed
            
        except Exception as e:
            print(f"杀死Caddy进程时发生错误: {str(e)}")
            return False
    
    def _reload_caddy(self):
        try:
            # 如果caddy正在运行，发送重载信号
            if self.caddy_process and self.caddy_process.poll() is None:
                # 在Windows上，尝试发送重载命令
                if os.name == 'nt':
                    # Windows下使用caddy reload命令
                    reload_cmd = [self.caddy_binary, "reload", "--config", str(self.config_file)]
                    result = subprocess.run(reload_cmd, capture_output=True, text=True)
                    return result.returncode == 0
                else:
                    # Unix-like系统下发送信号
                    self.caddy_process.send_signal(signal.SIGUSR1)
                    return True
            else:
                # 如果进程不在运行，尝试启动
                return self.start_web()
                
        except Exception as e:
            print(f"重载Caddy配置时发生错误: {str(e)}")
            return False
    
    def get_status(self):
        status = {
            "caddy_running": self._is_caddy_running(),
            "config_file_exists": self.config_file.exists(),
            "config_file_path": str(self.config_file),
            "proxy_count": 0
        }
        
        if self.config_file.exists():
            config_content = self.config_file.read_text()
            # 简单计算代理配置数量
            status["proxy_count"] = config_content.count(" {")
        
        return status


# 使用示例
if __name__ == "__main__":
    # 创建HttpManage实例
    http_manager = HttpManage()
    
    print("=== HttpManage 使用示例 ===\n")
    
    # 示例1: 启动web服务
    print("1. 启动Caddy服务...")
    if http_manager.start_web():
        print("✓ Caddy服务启动成功")
    else:
        print("✗ Caddy服务启动失败")
    
    # 示例2: 添加HTTP代理
    print("\n2. 添加HTTP代理配置...")
    if http_manager.proxy_add((8080, "192.168.1.100"), "http.example.com", is_https=False):
        print("✓ HTTP代理添加成功: http.example.com -> http://192.168.1.100:8080")
    else:
        print("✗ HTTP代理添加失败")
    
    # 示例3: 添加HTTPS代理
    print("\n3. 添加HTTPS代理配置...")
    if http_manager.proxy_add((443, "10.0.0.50"), "api.example.com", is_https=True):
        print("✓ HTTPS代理添加成功: api.example.com -> https://10.0.0.50:443")
    else:
        print("✗ HTTPS代理添加失败")
    
    # 示例4: 查看当前状态
    print("\n4. 查看当前状态...")
    status = http_manager.get_status()
    print(f"  - Caddy运行状态: {'运行中' if status['caddy_running'] else '未运行'}")
    print(f"  - 配置文件路径: {status['config_file_path']}")
    print(f"  - 代理配置数量: {status['proxy_count']}")
    
    # 示例5: 删除代理（按域名）
    print("\n5. 删除HTTP代理配置...")
    if http_manager.proxy_del("http.example.com", is_http=True):
        print("✓ HTTP代理删除成功")
    else:
        print("✗ HTTP代理删除失败")
    
    # 示例6: 删除代理（按目标地址）
    print("\n6. 删除HTTPS代理配置...")
    if http_manager.proxy_del((443, "10.0.0.50"), is_http=False):
        print("✓ HTTPS代理删除成功")
    else:
        print("✗ HTTPS代理删除失败")
    
    # 示例7: 再次查看状态
    print("\n7. 再次查看状态...")
    final_status = http_manager.get_status()
    print(f"  - 代理配置数量: {final_status['proxy_count']}")
    
    # 示例8: 停止服务
    print("\n8. 停止Caddy服务...")
    if http_manager.close_web():
        print("✓ Caddy服务停止成功")
    else:
        print("✗ Caddy服务停止失败")
    
    print("\n=== 示例完成 ===")


# 也可以在代码中这样使用：
if __name__ == "__main__":
    """
    在其他代码中使用的示例
    """
    manager = HttpManage()
    
    # 启动服务
    if manager.start_web():
        print("服务启动成功")
        
        # 批量添加代理
        proxies = [
            ((1880, "127.0.0.1"), "127.0.0.1", False),
        ]
        
        for target, domain, is_https in proxies:
            if manager.proxy_add(target, domain, is_https):
                print(f"代理 {domain} 添加成功")
        
        # 获取状态
        status = manager.get_status()
        print(f"当前共有 {status['proxy_count']} 个代理配置")
        
        # 清理：删除所有代理
        manager.proxy_del("web1.local", True)
        manager.proxy_del("web2.local", True)
        manager.proxy_del("api.local", True)
        
        # 停止服务
        manager.close_web()