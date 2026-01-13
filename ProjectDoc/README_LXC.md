# LXC 容器管理模块

<div align="center">

基于 LXC (Linux Containers) 的容器管理功能实现

[功能特性](#功能特性) • [环境要求](#环境要求) • [快速开始](#快速开始) • [配置说明](#配置说明) • [故障排查](#故障排查)

</div>

## 📖 概述

本模块实现了基于 LXC (Linux Containers) 的容器管理功能，参考 VmwareWork 的实现模式，提供完整的容器生命周期管理、网络配置、存储管理和 Web Terminal 访问等功能。

---

## ✅ 功能特性

### 已实现的功能

| 功能 | 说明 |
|------|------|
| **HSLoader** | 初始化 LXC 环境并启动 Web Terminal 服务 |
| **HSUnload** | 清理 LXC 环境并停止 Web Terminal 服务 |
| **VScanner** | 扫描现有的 LXC 容器 |
| **VMCreate** | 创建新容器 |
| **VInstall** | 从 tar.gz 模板安装容器 |
| **VMUpdate** | 更新容器配置（CPU、内存、网络等） |
| **VMDelete** | 删除容器 |
| **VMPowers** | 容器电源管理（启动/停止/重启） |
| **Password** | 设置容器内 root 用户密码 |
| **VMBackup** | 备份容器（使用 7z） |
| **Restores** | 恢复容器 |
| **HDDMount** | 挂载额外存储卷（bind mount） |
| **LDBackup** | 加载备份列表 |
| **RMBackup** | 删除备份 |
| **RMMounts** | 移除挂载的存储 |
| **VCRemote** | 生成 Web Terminal 访问 URL |

### 不支持的功能

| 功能 | 说明 |
|------|------|
| **ISOMount** | LXC 容器不需要 ISO 挂载（返回成功但不执行操作） |
| **GPUShows** | 返回空字典（LXC 不需要 GPU 管理） |

---

## 🛠️ 环境要求

### 系统要求

- **操作系统**: Linux（推荐 Ubuntu 20.04+ 或 Debian 11+）
- **内核**: 支持 cgroups v2 和用户命名空间
- **权限**: Root 权限或 sudo 访问权限

### 软件依赖

```bash
# 系统包
apt-get install lxc lxc-templates python3-lxc bridge-utils ttydserver

# Python 包
pip install -r pipinstall-lxc.txt
```

---

## 🚀 快速开始

### 1. 初始化 LXC 环境

运行初始化脚本来配置 LXC 环境：

```bash
cd HostServer
chmod +x envinstall-lxc.sh
sudo ./envinstall-lxc.sh
```

脚本会自动完成以下操作：
- ✅ 安装 LXC 和依赖包
- ✅ 配置内核参数（支持非特权容器）
- ✅ 配置 subuid 和 subgid
- ✅ 创建网桥（network_pub 和 network_nat）
- ✅ 配置 LXC 默认配置
- ✅ 创建存储目录

### 2. 配置 HSConfig

在 HSConfig 中配置以下参数：

```python
config = HSConfig(
    server_name="lxc-host-01",
    server_type="Containers",
    
    # LXC 相关配置
    images_path="/var/lib/lxc/templates",  # tar.gz 模板存储路径
    system_path="/var/lib/lxc",            # 容器存储路径
    backup_path="/var/lib/lxc/backups",    # 备份存储路径
    extern_path="/var/lib/lxc/volumes",    # 额外存储卷路径
    
    # 网络配置
    network_pub="lxcbr0",  # 公网网桥名称
    network_nat="lxcbr1",  # 内网网桥名称
    
    # Web Terminal 配置
    remote_port=7681,      # ttydserver 服务端口
    
    # 其他配置...
)
```

### 3. 准备容器模板

将 LXC 容器模板（tar.gz 格式）放置到 `images_path` 目录：

```bash
# 示例：下载 Ubuntu 22.04 模板
cd /var/lib/lxc/templates
wget https://example.com/ubuntu-22.04-rootfs.tar.gz

# 或者从现有容器创建模板
cd /var/lib/lxc/existing-container
tar czf /var/lib/lxc/templates/my-template.tar.gz rootfs/
```

### 4. 使用示例

```python
from HostServer.LXContainer import HostServer
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMConfig import VMConfig

# 初始化主机服务
config = HSConfig(...)
host = HostServer(config)

# 加载主机
result = host.HSLoader()
print(result.message)

# 扫描现有容器
result = host.VMDetect()
print(f"扫描到 {result.results['scanned']} 个容器")

# 创建新容器
vm_config = VMConfig(
  vm_uuid="test-container-01",
  os_name="ubuntu-22.04-rootfs.tar.gz",
  cpu_num=2,
  mem_num=4,  # GB
  hdd_num=20,  # GB
)

result = host.VMCreate(vm_config)
if result.success:
  print("容器创建成功")

# 启动容器
result = host.VMPowers("test-container-01", VMPowers.S_START)

# 获取 Web Terminal URL
terminal_url = host.VMRemote("test-container-01")
print(f"Web Terminal: {terminal_url}")
```

---

## 📝 配置说明

### 容器配置

容器配置通过 `VMConfig` 对象管理，主要参数包括：

| 参数 | 说明 | 示例 |
|------|------|------|
| `vm_uuid` | 容器名称 | `"test-container-01"` |
| `os_name` | 模板文件名 | `"ubuntu-22.04-rootfs.tar.gz"` |
| `cpu_num` | CPU 核心数 | `2` |
| `mem_num` | 内存大小（GB） | `4` |
| `nic_all` | 网卡配置 | 自动选择 network_pub 或 network_nat |

### 网络配置

容器网络通过 LXC 的 veth pair 实现：

```
lxc.net.0.type = veth
lxc.net.0.link = lxcbr0          # 网桥名称
lxc.net.0.flags = up
lxc.net.0.hwaddr = 00:16:3e:xx:xx:xx
lxc.net.0.ipv4.address = 192.168.1.1/24
```

### 存储挂载

使用 bind mount 方式挂载额外存储：

```
lxc.mount.entry = /host/path container/path none bind 0 0
```

---

## 💻 Web Terminal

本模块集成了 ttyd 提供 Web Terminal 功能：

| 功能 | 说明 |
|------|------|
| **启动** | 在 `HSLoader()` 时自动启动 ttyd 服务 |
| **访问** | 通过 `VCRemote()` 生成带 token 的访问 URL |
| **连接** | 使用 `lxc-attach` 连接到容器终端 |

访问示例：
```
http://192.168.1.1:7681/?arg=lxc-attach&arg=-n&arg=container-name&token=xxx
```

---

## 📦 容器模板格式

模板文件必须是 tar.gz 格式，包含完整的 rootfs 目录结构：

```
template.tar.gz
└── rootfs/
    ├── bin/
    ├── etc/
    ├── home/
    ├── lib/
    ├── root/
    ├── usr/
    └── var/
```

---

## 🔐 非特权容器

本实现使用非特权容器（unprivileged containers）以提高安全性：

- 容器内的 root 用户映射到主机的非特权用户（100000-165535）
- 需要配置 subuid 和 subgid
- 配置示例：
  ```
  lxc.idmap = u 0 100000 65536
  lxc.idmap = g 0 100000 65536
  ```

---

## 🔧 故障排查

### 1. python3-lxc 未安装

```
错误: python3-lxc is not installed
解决: sudo apt-get install python3-lxc
```

### 2. 容器创建失败

```
错误: Failed to create container
检查:
  - lxc-checkconfig  # 检查内核配置
  - 确保 system_path 目录存在且有写权限
  - 检查模板文件是否存在
```

### 3. 网络配置失败

```
错误: 容器无法访问网络
检查:
  - ip link show  # 确认网桥已创建
  - brctl show    # 查看网桥状态
  - 确保 network_pub/nat 配置正确
```

### 4. ttyd 未启动

```
错误: ttyd not found
解决: sudo apt-get install ttyd
```

---

## 📊 与 VmwareWork 的差异

| 功能 | VmwareWork | Containers (LXC) |
|------|-----------|------------------|
| 虚拟化类型 | 完全虚拟化 | 容器虚拟化 |
| 系统安装 | 从 VMDK 复制 | 从 tar.gz 解压 |
| 网络 | VMware 虚拟网卡 | veth pair + 网桥 |
| 存储 | VMDK 虚拟磁盘 | bind mount |
| ISO 挂载 | 支持 | 不支持 |
| GPU 直通 | 支持 | 不支持 |
| 控制台 | VNC | Web Terminal (ttyd) |
| 资源隔离 | 硬件级别 | 内核级别 (cgroups) |

---

## ⚡ 性能优势

LXC 容器相比传统虚拟机的优势：

| 指标 | LXC 容器 | 传统虚拟机 |
|------|----------|-----------|
| 启动速度 | 秒级 | 分钟级 |
| 资源开销 | 接近原生性能 | 有虚拟化开销 |
| 密度 | 单台主机可运行更多容器 | 受限于资源分配 |
| 存储 | 共享内核，节省磁盘空间 | 独立系统文件 |

---

## 🔒 安全注意事项

1. **非特权容器**: 默认使用非特权容器，提高安全性
2. **网络隔离**: 使用网桥隔离容器网络
3. **资源限制**: 通过 cgroups 限制 CPU 和内存
4. **文件系统**: 容器内文件系统与主机隔离

---

## 📚 参考资料

- [LXC 官方文档](https://linuxcontainers.org/lxc/documentation/)
- [python3-lxc API](https://linuxcontainers.org/lxc/documentation/)
- [ttyd GitHub](https://github.com/tsl0922/ttyd)
- [Linux Containers 安全指南](https://linuxcontainers.org/lxc/security/)

---

## 📄 许可证

本模块遵循项目主许可证。
