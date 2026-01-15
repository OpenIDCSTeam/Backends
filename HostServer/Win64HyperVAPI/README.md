# Hyper-V 虚拟机管理模块

## 概述

本模块提供了对Windows Hyper-V虚拟机的完整管理功能，支持本地和远程管理。

## 功能特性

### 1. 连接管理
- ✅ 支持本地PowerShell连接
- ✅ 支持远程WinRM连接
- ✅ 支持HTTPS加密连接

### 2. 虚拟机管理
- ✅ 创建虚拟机（支持第一代和第二代）
- ✅ 删除虚拟机
- ✅ 修改虚拟机配置（CPU、内存）
- ✅ 虚拟机扫描和发现

### 3. 电源管理
- ✅ 启动虚拟机
- ✅ 关闭虚拟机（正常关闭和强制关闭）
- ✅ 重启虚拟机
- ✅ 暂停虚拟机
- ✅ 恢复虚拟机

### 4. 存储管理
- ✅ 创建虚拟硬盘（VHDX格式）
- ✅ 添加虚拟硬盘到虚拟机
- ✅ ISO镜像挂载
- ✅ ISO镜像卸载
- ✅ 支持动态磁盘

### 5. 快照管理
- ✅ 创建快照（检查点）
- ✅ 恢复快照
- ✅ 删除快照

### 6. 网络管理
- ✅ 配置虚拟交换机
- ✅ 设置MAC地址
- ✅ NAT端口映射（通过爱快路由器）
- ✅ Web端口映射（通过Caddy）
- ✅ IP地址管理

### 7. 系统安装
- ✅ 支持ISO镜像安装
- ✅ 支持VHDX磁盘镜像
- ✅ 支持VHD磁盘镜像

## 环境要求

### Windows主机要求
1. Windows 10 Pro/Enterprise 或 Windows Server 2016+
2. 已启用Hyper-V功能
3. PowerShell 5.0+

### 远程管理要求
1. 启用WinRM服务
2. 配置防火墙规则
3. 配置TrustedHosts（如果不使用域）

## 配置说明

### 启用Hyper-V（本地）

```powershell
# 以管理员身份运行PowerShell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

### 配置WinRM（远程管理）

#### 在Hyper-V主机上执行：

```powershell
# 启用WinRM
Enable-PSRemoting -Force

# 配置防火墙
Set-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -RemoteAddress Any

# 如果使用HTTPS
New-SelfSignedCertificate -DnsName "your-hostname" -CertStoreLocation Cert:\LocalMachine\My
winrm create winrm/config/Listener?Address=*+Transport=HTTPS @{Hostname="your-hostname"; CertificateThumbprint="thumbprint"}

# 配置TrustedHosts（如果不在域环境）
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

#### 在客户端上执行：

```powershell
# 配置TrustedHosts
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "hyper-v-host-ip" -Force
```

## 使用示例

### 基本配置

```python
from MainObject.Config.HSConfig import HSConfig
from HostServer.Win64HyperV import HostServer

# 创建主机配置
config = HSConfig(
    server_name="HyperV-Host-01",
    server_addr="192.168.1.100",  # 远程主机IP，本地使用"localhost"
    server_user="Administrator",
    server_pass="YourPassword",
    server_port=5985,  # HTTP: 5985, HTTPS: 5986
    system_path="C:\\Hyper-V\\VMs",
    images_path="C:\\Hyper-V\\Images",
    backup_path="C:\\Hyper-V\\Backups",
    i_kuai_addr="192.168.1.1",  # 爱快路由器地址
    i_kuai_user="admin",
    i_kuai_pass="admin"
)

# 创建主机服务
host_server = HostServer(config)
```

### 连接和初始化

```python
# 加载主机
result = host_server.HSLoader()
if result.success:
    print("主机连接成功")
else:
    print(f"连接失败: {result.message}")
```

### 扫描虚拟机

```python
# 扫描现有虚拟机
result = host_server.VMDetect()
print(f"扫描结果: {result.message}")
```

### 创建虚拟机

```python
from MainObject.Config.VMConfig import VMConfig

# 创建虚拟机配置
vm_config = VMConfig()
vm_config.vm_uuid = "TestVM-001"
vm_config.cpu_num = 2
vm_config.mem_num = 4096  # MB
vm_config.hdd_num = 50  # GB
vm_config.os_name = "Windows-Server-2022.iso"

# 创建虚拟机
result = host_server.VMCreate(vm_config)
if result.success:
    print("虚拟机创建成功")
```

### 电源管理

```python
from MainObject.Config.VMPowers import VMPowers

# 启动虚拟机
host_server.VMPowers("TestVM-001", VMPowers.S_START)

# 关闭虚拟机
host_server.VMPowers("TestVM-001", VMPowers.H_CLOSE)

# 重启虚拟机
host_server.VMPowers("TestVM-001", VMPowers.S_RESET)

# 暂停虚拟机
host_server.VMPowers("TestVM-001", VMPowers.S_PAUSE)

# 恢复虚拟机
host_server.VMPowers("TestVM-001", VMPowers.S_RESUME)
```

### ISO挂载

```python
from MainObject.Config.IMConfig import IMConfig

# 创建ISO配置
iso_config = IMConfig()
iso_config.iso_name = "Windows-Install"
iso_config.iso_file = "Windows-Server-2022.iso"

# 挂载ISO
result = host_server.ISOMount("TestVM-001", iso_config, in_flag=True)

# 卸载ISO
result = host_server.ISOMount("TestVM-001", iso_config, in_flag=False)
```

### 快照管理

```python
# 创建快照
result = host_server.VMBackup("TestVM-001", "安装完成后的快照")

# 恢复快照
result = host_server.Restores("TestVM-001", "TestVM-001-20260112143000")

# 删除快照
result = host_server.RMBackup("TestVM-001", "TestVM-001-20260112143000")
```

### 网络配置

```python
from MainObject.Config.PortData import PortData

# 配置NAT端口映射
port_config = PortData()
port_config.wan_port = 0  # 0表示自动分配
port_config.lan_port = 3389  # RDP端口
port_config.lan_addr = "192.168.100.10"
port_config.nat_tips = "TestVM-001 RDP"

result = host_server.PortsMap(port_config, flag=True)
```

## API参考

### HyperVAPI类

#### 连接方法
- `connect()` - 连接到Hyper-V主机
- `disconnect()` - 断开连接

#### 虚拟机管理
- `list_vms(filter_prefix)` - 列出虚拟机
- `get_vm_info(vm_name)` - 获取虚拟机信息
- `create_vm(vm_conf, hs_config)` - 创建虚拟机
- `delete_vm(vm_name, remove_files)` - 删除虚拟机
- `update_vm_config(vm_name, vm_conf)` - 更新配置

#### 电源管理
- `power_on(vm_name)` - 启动
- `power_off(vm_name, force)` - 关闭
- `suspend(vm_name)` - 暂停
- `resume(vm_name)` - 恢复
- `reset(vm_name)` - 重启

#### 存储管理
- `add_disk(vm_name, size_gb, disk_name)` - 添加磁盘
- `attach_iso(vm_name, iso_path)` - 挂载ISO
- `detach_iso(vm_name)` - 卸载ISO

#### 快照管理
- `create_snapshot(vm_name, snapshot_name, description)` - 创建快照
- `revert_snapshot(vm_name, snapshot_name)` - 恢复快照
- `delete_snapshot(vm_name, snapshot_name)` - 删除快照

#### 网络管理
- `set_network_adapter(vm_name, switch_name, mac_address)` - 配置网络

## 注意事项

1. **权限要求**：需要管理员权限才能管理Hyper-V虚拟机
2. **VNC支持**：Hyper-V不支持传统VNC，使用增强会话模式或RDP
3. **网络配置**：需要预先创建虚拟交换机
4. **磁盘格式**：推荐使用VHDX格式（支持更大容量和更好性能）
5. **快照性能**：频繁创建快照会影响性能，建议定期合并
6. **远程连接**：确保网络连通性和防火墙配置正确

## 依赖项

```bash
pip install pywinrm
pip install loguru
```

## 故障排除

### 连接失败
1. 检查WinRM服务是否运行：`Get-Service WinRM`
2. 检查防火墙规则
3. 验证TrustedHosts配置
4. 测试连接：`Test-WSMan -ComputerName hostname`

### 虚拟机创建失败
1. 检查磁盘空间
2. 验证虚拟交换机是否存在
3. 检查Hyper-V服务状态

### 权限错误
1. 确保使用管理员账户
2. 检查用户是否在Hyper-V Administrators组中

## 更新日志

### v1.0.0 (2026-01-12)
- ✅ 初始版本发布
- ✅ 支持基本虚拟机管理功能
- ✅ 支持本地和远程连接
- ✅ 支持电源管理
- ✅ 支持存储管理
- ✅ 支持快照管理
- ✅ 支持网络配置

## 许可证

本项目遵循项目主许可证。

## 贡献

欢迎提交问题和改进建议！
