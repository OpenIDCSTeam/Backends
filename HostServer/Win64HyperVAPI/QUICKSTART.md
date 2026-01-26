# Hyper-V 快速入门指南

## 5分钟快速开始

### 步骤1: 安装依赖

```bash
pip install pywinrm loguru
```

### 步骤2: 启用Hyper-V（如果尚未启用）

以管理员身份运行PowerShell：

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

重启计算机后生效。

### 步骤3: 配置WinRM（远程管理）

如果需要远程管理，在Hyper-V主机上执行：

```powershell
# 启用WinRM
Enable-PSRemoting -Force

# 配置防火墙
Set-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -RemoteAddress Any

# 配置TrustedHosts（如果不在域环境）
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

### 步骤4: 创建第一个虚拟机

```python
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.VMPowers import VMPowers
from HostServer.Win64HyperV import HostServer

# 1. 创建主机配置
config = HSConfig(
    server_name="MyHyperV",
    server_addr="localhost",  # 本地管理
    server_user="",
    server_pass="",
    system_path="C:\\Hyper-V\\DockManage",
    images_path="C:\\Hyper-V\\Images",
    backup_path="C:\\Hyper-V\\Backups"
)

# 2. 连接到主机
host = HostServer(config)
result = host.HSLoader()
print(f"连接结果: {result.message}")

# 3. 扫描现有虚拟机
result = host.VMDetect()
print(f"扫描结果: {result.message}")

# 4. 创建新虚拟机
vm_config = VMConfig()
vm_config.vm_uuid = "MyFirstVM"
vm_config.cpu_num = 2
vm_config.mem_num = 2048  # 2GB
vm_config.hdd_num = 40    # 40GB

result = host.VMCreate(vm_config)
print(f"创建结果: {result.message}")

# 5. 启动虚拟机
result = host.VMPowers("MyFirstVM", VMPowers.S_START)
print(f"启动结果: {result.message}")

# 6. 清理
host.HSUnload()
```

### 步骤5: 运行测试

```bash
# 以管理员身份运行
python HostServer/Win64HyperVAPI/test_hyperv.py
```

## 常见操作

### 挂载ISO镜像

```python
from MainObject.Config.IMConfig import IMConfig

iso_config = IMConfig()
iso_config.iso_name = "Windows-Install"
iso_config.iso_file = "Windows-Server-2022.iso"

host.ISOMount("MyFirstVM", iso_config, in_flag=True)
```

### 创建快照

```python
result = host.VMBackup("MyFirstVM", "安装完成后的快照")
print(f"快照名称: {result.message}")
```

### 配置端口映射

```python
from MainObject.Config.PortData import PortData

port_config = PortData()
port_config.wan_port = 0  # 自动分配
port_config.lan_port = 3389  # RDP
port_config.lan_addr = "192.168.1.100"
port_config.nat_tips = "MyFirstVM RDP"

host.PortsMap(port_config, flag=True)
```

## 故障排除

### 问题1: 连接失败

**解决方案**:
1. 确保以管理员身份运行
2. 检查Hyper-V服务是否运行: `Get-Service vmms`
3. 检查WinRM服务: `Get-Service WinRM`

### 问题2: 权限错误

**解决方案**:
1. 确保用户在"Hyper-V Administrators"组中
2. 以管理员身份运行脚本

### 问题3: 虚拟机创建失败

**解决方案**:
1. 检查磁盘空间
2. 确保虚拟交换机存在: `Get-VMSwitch`
3. 检查路径权限

## 下一步

- 阅读完整文档: [README.md](README.md)
- 查看实现细节: [IMPLEMENTATION.md](IMPLEMENTATION.md)
- 运行测试脚本: `test_hyperv.py`

## 获取帮助

如果遇到问题，请检查：
1. 日志文件: `DataSaving/log-*.log`
2. PowerShell错误信息
3. Windows事件查看器中的Hyper-V日志
