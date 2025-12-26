import random
import socket
import threading
import time
from typing import Tuple, Optional

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class SSHForward:
    """SSH 转发管理类，支持远程命令执行和端口转发"""
    
    def __init__(self):
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.forward_threads: list = []  # 存储转发线程
        self.remote_port = 0  # 远程端口
        self.local_port = 0  # 本地端口
        self.hostname = ""  # 主机名
        self.username = ""
        self.password = ""
        self.port = 22  # SSH 端口
        self._connected = False
        self._lock = threading.Lock()
    
    def connect(self, hostname: str, username: str, password: str, port: int = 22, timeout: int = 30) -> Tuple[bool, str]:
        """
        连接到 SSH 服务器
        
        Args:
            hostname: SSH 服务器地址
            username: 用户名
            password: 密码
            port: SSH 端口（默认22）
            timeout: 连接超时时间（秒）
            
        Returns:
            (success, message)
        """
        if not PARAMIKO_AVAILABLE:
            return False, "paramiko 库未安装"
        
        # 如果已经连接，先关闭（必须在锁外调用）
        if self._connected:
            self._close_unlocked()
        
        with self._lock:
            try:
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh_client.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    password=password,
                    timeout=timeout,
                    allow_agent=False,
                    look_for_keys=False
                )
                
                self.hostname = hostname
                self.username = username
                self.password = password
                self.port = port
                self._connected = True
                
                return True, f"SSH 连接成功: {hostname}"
                
            except Exception as e:
                self._connected = False
                self.ssh_client = None
                return False, f"SSH 连接失败: {str(e)}"
    
    def _close_unlocked(self):
        """内部方法：不获取锁的关闭方法"""
        # 停止端口转发
        self.stop_port_forward()
        
        # 关闭 SSH 连接
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception:
                pass
            finally:
                self.ssh_client = None
        
        self._connected = False
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.ssh_client is not None
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """
        执行 SSH 命令
        
        Args:
            command: 要执行的命令
            timeout: 执行超时时间（秒）
            
        Returns:
            (success, stdout, stderr)
        """
        if not self.is_connected():
            return False, "", "SSH 未连接"
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            exit_status = stdout.channel.recv_exit_status()
            
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            
            return exit_status == 0, stdout_data, stderr_data
            
        except Exception as e:
            return False, "", f"命令执行失败: {str(e)}"
    
    def _find_available_local_port(self, start: int = 9000, end: int = 9999) -> int:
        """
        查找可用的本地端口
        
        Args:
            start: 起始端口
            end: 结束端口
            
        Returns:
            可用的端口号，如果没有找到则返回0
        """
        for port in range(start, end + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        return 0
    
    def _forward_tunnel(self, local_port: int, remote_host: str, remote_port: int, transport):
        """SSH 端口转发线程函数"""
        try:
            local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            local_socket.bind(('127.0.0.1', local_port))
            local_socket.listen(5)
            
            while self._connected:
                try:
                    local_socket.settimeout(1)
                    client_socket, addr = local_socket.accept()
                    
                    # 创建远程通道
                    remote_socket = transport.open_channel(
                        'direct-tcpip',
                        (remote_host, remote_port),
                        addr
                    )
                    
                    # 创建转发线程
                    forward_thread = threading.Thread(
                        target=self._pipe,
                        args=(client_socket, remote_socket),
                        daemon=True
                    )
                    forward_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._connected:
                        pass  # 连接关闭时的异常可以忽略
                    break
                    
        except Exception as e:
            pass
        finally:
            local_socket.close()
    
    def _pipe(self, source, destination):
        """数据转发函数"""
        try:
            while True:
                data = source.recv(4096)
                if not data:
                    break
                destination.send(data)
        except Exception:
            pass
        finally:
            source.close()
            destination.close()
    
    def start_port_forward(self, remote_port: int, local_port_range: Tuple[int, int] = (9000, 9999),
                           remote_host: str = "127.0.0.1") -> Tuple[bool, str, int]:
        """
        启动 SSH 端口转发
        
        Args:
            remote_port: 远程端口
            local_port_range: 本地端口范围 (start, end)
            remote_host: 远程主机地址（默认127.0.0.1）
            
        Returns:
            (success, message, local_port)
        """
        if not self.is_connected():
            return False, "SSH 未连接", 0
        
        with self._lock:
            # 分配本地端口
            local_port = self._find_available_local_port(local_port_range[0], local_port_range[1])
            if local_port == 0:
                return False, f"无法在 {local_port_range[0]}-{local_port_range[1]} 范围内找到可用端口", 0
            
            try:
                transport = self.ssh_client.get_transport()
                
                # 启动转发线程
                forward_thread = threading.Thread(
                    target=self._forward_tunnel,
                    args=(local_port, remote_host, remote_port, transport),
                    daemon=True
                )
                forward_thread.start()
                self.forward_threads.append(forward_thread)
                
                self.remote_port = remote_port
                self.local_port = local_port
                
                # 等待端口监听就绪
                time.sleep(0.5)
                
                return True, f"端口转发已启动: 127.0.0.1:{local_port} -> {remote_host}:{remote_port}", local_port
                
            except Exception as e:
                return False, f"启动端口转发失败: {str(e)}", 0
    
    def stop_port_forward(self):
        """停止端口转发"""
        self.forward_threads.clear()
        self.remote_port = 0
        self.local_port = 0
    
    def close(self):
        """关闭 SSH 连接"""
        with self._lock:
            self._close_unlocked()
    
    def __enter__(self):
        """支持 with 语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出时自动关闭"""
        self.close()