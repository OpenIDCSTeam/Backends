# vSphere ESXi 配置指南

本文档说明如何配置和使用vSphere ESXi主机服务器。

## 系统要求

- ESXi 6.x, 7.x, 8.x 或 9.x
- Python 3.8+
- pyvmomi 库（已在requirements.txt中）

## 安装依赖

```bash
pip install -r pipinstall-esx.txt
```

## ESXi主机配置

### 1. 启用ESXi API访问

确保ESXi主机的API服务已启用（默认启用）。

### 2. 创建API用户

建议创建专用的API用户，或使用root用户：
- 用户名：root（或自定义用户）
- 密码：ESXi主机密码
- 权限：管理员权限

### 3. 配置HSConfig

在HSConfig中配置以下参数：

```python
{
    "server_name": "esxi-host-01",           # 服务器名称
    "server_type": "vSphereESXi",            # 服务器类型（必须是vSphereESXi）
    "server_addr": "192.168.1.100",          # ESXi主机IP地址
    "server_user": "root",                   # ESXi用户名
    "server_pass": "your_password",          # ESXi密码
    "server_port": 443,                      # ESXi API端口（默认443）
    "filter_name": "vm-",                    # 虚拟机名称前缀过滤
    
    # 存储配置
    "images_path": "ISO",                    # ISO镜像目录（数据存储中的相对路径）
    "system_path": "datastore1",             # 数据存储名称
    "backup_path": "/path/to/backup",        # 备份导出路径（本地路径）
    "extern_path": "/path/to/extern",        # 外部数据路径
    
    # 网络配置
    "network_nat": "VM Network",             # NAT网络（虚拟交换机或端口组名称）
    "network_pub": "Public Network",         # 公网网络（虚拟交换机或端口组名称）
    
    # 其他配置
    "i_kuai_addr": "192.168.1.1",           # 爱快路由器地址（用于DHCP绑定）
    "i_kuai_user": "admin",                  # 爱快用户名
    "i_kuai_pass": "admin",                  # 爱快密码
    "ports_start": 10000,                    # 端口映射起始端口
    "ports_close": 20000,                    # 端口映射结束端口
    "remote_port": 6080,                     # VNC远程端口
    "limits_nums": 100,                      # 虚拟机数量限制
    "public_addr": ["192.168.1.100"],       # 公网IP地址
    "server_dnss": ["8.8.8.8", "8.8.4.4"],  # DNS服务器
    
    # IP地址池配置
    "ipaddr_maps": {
        "nat_pool": {
            "vers": "ipv4",
            "type": "nat",
            "gate": "192.168.100.1",
            "mask": "255.255.255.0",
            "from": "192.168.100.10",
            "nums": 100
        },
        "pub_pool": {
            "vers": "ipv4",
            "type": "pub",
            "gate": "10.0.0.1",
            "mask": "255.255.255.0",
            "from": "10.0.0.10",
            "nums": 50
        }
    },
    
    # DNS配置
    "ipaddr_dnss": ["8.8.8.8", "8.8.4.4"],
    
    # 镜像映射（显示名称 -> 文件名）
    "images_maps": {
        "Ubuntu 22.04": "ubuntu-22.04-server-amd64.iso",
        "CentOS 7": "CentOS-7-x86_64-Minimal.iso",
        "Windows Server 2019": "windows-server-2019.iso"
    }
}
```

## ESXi数据存储结构

建议在ESXi数据存储中创建以下目录结构：

```
datastore1/
├── ISO/                    # ISO镜像目录（对应images_path）
│   ├── ubuntu-22.04-server-amd64.iso
│   ├── CentOS-7-x86_64-Minimal.iso
│   └── windows-server-2019.iso
├── vm-001/                 # 虚拟机目录（自动创建）
│   ├── vm-001.vmx
│   ├── vm-001.vmdk
│   └── ...
└── vm-002/
    └── ...
```

## 网络配置

### 1. 虚拟交换机配置

在ESXi中配置虚拟交换机：

- **VM Network**（NAT网络）：用于内网虚拟机
- **Public Network**（公网网络）：用于公网虚拟机

### 2. 端口组配置

确保端口组名称与HSConfig中的`network_nat`和`network_pub`匹配。

## 功能说明

### 支持的操作

1. **虚拟机管理**
   - 创建虚拟机（VMCreate）
   - 删除虚拟机（VMDelete）
   - 更新虚拟机配置（VMUpdate）
   - 扫描虚拟机（VScanner）

2. **电源管理**
   - 开机（S_START）
   - 关机（H_CLOSE）
   - 重启（H_RESET/S_RESET）
   - 挂起（S_PAUSE）

3. **存储管理**
   - 安装系统（VInstall）
   - 挂载ISO（ISOMount）
   - 挂载磁盘（HDDMount）
   - 移除磁盘（RMMounts）

4. **备份恢复**
   - 创建快照备份（VMBackup）
   - 恢复快照（Restores）
   - 加载备份列表（LDBackup）
   - 删除备份（RMBackup）

5. **监控**
   - 主机状态（HSStatus）
   - 虚拟机状态（VMStatus）

### 与Workstation的区别

| 功能 | Workstation | vSphere ESXi |
|------|-------------|--------------|
| 连接方式 | 本地REST API | 远程vSphere API |
| 虚拟机配置 | VMX文件 | API对象 |
| 备份方式 | 文件压缩 | 快照 |
| 网络配置 | 本地虚拟网卡 | 虚拟交换机/端口组 |
| 存储位置 | 本地文件系统 | 数据存储 |

## 使用示例

### 1. 初始化ESXi主机

```python
from MainObject.Config.HSConfig import HSConfig
from HostServer.vSphereESXi import HostServer

# 创建配置
config = HSConfig(
    server_name="esxi-host-01",
    server_type="vSphereESXi",
    server_addr="192.168.1.100",
    server_user="root",
    server_pass="password",
    system_path="datastore1",
    network_nat="VM Network",
    network_pub="Public Network"
)

# 创建主机服务器
host = HostServer(config)

# 加载主机
result = host.HSLoader()
print(result.message)
```

### 2. 扫描虚拟机

```python
# 扫描ESXi上的所有虚拟机
result = host.VScanner()
print(f"扫描结果: {result.message}")
print(f"发现虚拟机: {result.results}")
```

### 3. 创建虚拟机

```python
from MainObject.Config.VMConfig import VMConfig

# 创建虚拟机配置
vm_config = VMConfig(
    vm_uuid="vm-test-001",
    cpu_num=2,
    ram_num=4096,
    hdd_num=50,
    os_name="ubuntu-22.04-server-amd64.iso"
)

# 创建虚拟机
result = host.VMCreate(vm_config)
print(result.message)
```

### 4. 备份虚拟机

```python
# 创建快照备份
result = host.VMBackup("vm-test-001", "测试备份")
print(result.message)

# 恢复快照
result = host.Restores("vm-test-001", "vm-test-001-20231225120000")
print(result.message)
```

## 注意事项

1. **SSL证书验证**：当前实现禁用了SSL证书验证，生产环境建议启用。

2. **镜像上传**：ISO镜像需要手动上传到ESXi数据存储的ISO目录中。

3. **磁盘镜像**：VMDK/VDI/QCOW2等磁盘镜像需要转换为ESXi支持的格式。

4. **网络配置**：确保虚拟交换机和端口组已正确配置。

5. **权限要求**：API用户需要有足够的权限管理虚拟机。

6. **备份策略**：ESXi使用快照作为备份，不同于Workstation的文件备份。

7. **版本兼容性**：代码支持ESXi 6.x到9.x，但建议使用7.x或更高版本。

## 故障排查

### 连接失败

- 检查ESXi主机IP地址和端口
- 确认用户名和密码正确
- 检查防火墙设置
- 确认ESXi API服务已启用

### 虚拟机创建失败

- 检查数据存储空间是否充足
- 确认网络配置正确
- 检查ISO镜像是否存在
- 查看ESXi日志

### 网络配置问题

- 确认虚拟交换机名称正确
- 检查端口组配置
- 验证IP地址池配置

## 参考资料

- [VMware vSphere API文档](https://developer.vmware.com/apis/vsphere-automation/latest/)
- [pyvmomi GitHub](https://github.com/vmware/pyvmomi)
- [ESXi管理指南](https://docs.vmware.com/cn/VMware-vSphere/index.html)
