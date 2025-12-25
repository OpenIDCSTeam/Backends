# LXD 容器管理 - 使用指南

## 概述

本项目使用 **LXD** 实现容器管理，支持从 Windows 客户端通过网络远程管理 Linux 服务器上的 LXD 容器。

### 核心特性

- ✅ **跨平台远程管理**：Windows/Linux/macOS 客户端可以管理远程 Linux 服务器
- ✅ **完整的 REST API**：基于 HTTPS 的安全通信
- ✅ **TLS 证书认证**：安全的客户端-服务器认证
- ✅ **强大的功能**：容器创建、配置、快照、备份等
- ✅ **资源管理**：CPU、内存、网络、存储限制
- ✅ **网络隔离**：支持公网和内网网桥

---

## 架构说明

```
┌─────────────────┐         HTTPS (8443)        ┌─────────────────┐
│  Windows 客户端  │ ◄─────────────────────────► │  Linux 服务器    │
│                 │                              │                 │
│  Python Script  │                              │   LXD Daemon    │
│  + pylxd       │                              │   + Containers  │
└─────────────────┘                              └─────────────────┘
```

### 组件说明

1. **服务端（Linux）**
   - LXD 守护进程（监听 8443 端口）
   - 容器运行环境
   - 网桥配置（br-pub, br-nat）
   - 存储池管理

2. **客户端（Windows/Linux）**
   - Python 脚本（HostServer/LXContainer.py）
   - pylxd 库（LXD Python 客户端）
   - TLS 证书（client.crt, client.key）

---

## 快速开始

### 1. 服务端配置（Linux 服务器）

在 Linux 服务器上运行初始化脚本：

```bash
# 下载脚本
cd /path/to/OpenIDCS-Client

# 赋予执行权限
chmod +x setup_lxd.sh

# 运行脚本（需要 root 权限）
sudo bash setup_lxd.sh
```

脚本会自动完成：
- 安装 LXD 和依赖
- 初始化 LXD（配置 API 监听 8443 端口）
- 创建网桥（br-pub, br-nat）
- 配置存储池
- 生成客户端证书
- 配置防火墙

### 2. 客户端配置（Windows）

#### 2.1 安装依赖

```bash
pip install pylxd
```

#### 2.2 复制证书

将服务器生成的证书复制到 Windows 客户端：

```
服务器路径: /path/to/lxd_certs/client.crt
           /path/to/lxd_certs/client.key

客户端路径: C:\path\to\certs\client.crt
           C:\path\to\certs\client.key
```

#### 2.3 配置 HSConfig

在 `HSConfig` 中配置服务器信息：

```python
from MainObject.Config.HSConfig import HSConfig

config = HSConfig(
    server_name="my-lxd-server",
    server_addr="192.168.1.100",  # Linux 服务器 IP
    server_user="",  # LXD 不需要
    server_pass="",  # LXD 不需要
    
    # 证书路径
    launch_path="C:\\path\\to\\certs",
    
    # 网络配置
    network_pub="br-pub",  # 公网网桥
    network_nat="br-nat",  # 内网网桥
    
    # 存储路径（服务器上的路径）
    system_path="/var/lib/lxd/containers",
    images_path="/path/to/templates",
    backup_path="/path/to/backups",
    extern_path="/path/to/external",
    
    # 其他配置...
)
```

### 3. 测试连接

```python
from HostServer.LXContainer import HostServer
from MainObject.Config.HSConfig import HSConfig

# 创建配置
config = HSConfig(
    server_name="test-server",
    server_addr="192.168.1.100",
    launch_path="C:\\certs",
    network_pub="br-pub",
    network_nat="br-nat"
)

# 创建服务器实例
server = HostServer(config)

# 加载服务器（连接到 LXD）
result = server.HSLoader()
if result.success:
    print("✅ 连接成功！")
else:
    print(f"❌ 连接失败: {result.message}")

# 扫描容器
scan_result = server.VScanner()
print(f"扫描结果: {scan_result.message}")
```

---

## 功能说明

### 容器管理

#### 创建容器

```python
from MainObject.Config.VMConfig import VMConfig

vm_conf = VMConfig(
    vm_uuid="test-container",
    os_name="ubuntu-22.04.tar.gz",  # 模板文件名
    cpu_num=2,
    ram_num=4,  # GB
    hdd_num=20  # GB
)

result = server.VMCreate(vm_conf)
```

#### 启动/停止容器

```python
from MainObject.Config.VMPowers import VMPowers

# 启动
server.VMPowers("test-container", VMPowers.S_START)

# 停止
server.VMPowers("test-container", VMPowers.H_CLOSE)

# 重启
server.VMPowers("test-container", VMPowers.S_RESET)
```

#### 删除容器

```python
server.VMDelete("test-container")
```

### 网络管理

容器网络自动配置，支持：
- 静态 IP 分配
- MAC 地址绑定
- 网桥选择（公网/内网）

### 存储管理

#### 挂载外部存储

```python
from MainObject.Config.SDConfig import SDConfig

disk = SDConfig(
    hdd_name="data-disk",
    hdd_size=100  # GB
)

# 挂载
server.HDDMount("test-container", disk, in_flag=True)

# 卸载
server.HDDMount("test-container", disk, in_flag=False)
```

### 备份与恢复

```python
# 备份容器
server.VMBackup("test-container", "备份说明")

# 恢复容器
server.Restores("test-container", "backup-file.7z")
```

---

## 模板管理

### 模板格式

LXD 容器模板使用 **tar.gz** 格式，包含完整的根文件系统。

### 创建模板

#### 方法 1：从现有容器导出

```bash
# 在 Linux 服务器上
lxc export my-container my-template.tar.gz
```

#### 方法 2：使用官方镜像

```bash
# 下载官方镜像
lxc image copy ubuntu:22.04 local: --alias ubuntu-22.04

# 导出为模板
lxc image export ubuntu-22.04 ubuntu-22.04
```

#### 方法 3：手动创建

```bash
# 创建 rootfs 目录
mkdir -p rootfs

# 安装基础系统（以 Ubuntu 为例）
debootstrap jammy rootfs http://archive.ubuntu.com/ubuntu

# 打包为 tar.gz
tar -czf ubuntu-22.04.tar.gz -C rootfs .
```

### 模板存放

将模板文件放在 `HSConfig.images_path` 指定的目录中：

```
/path/to/templates/
├── ubuntu-22.04.tar.gz
├── debian-11.tar.gz
└── centos-8.tar.gz
```

---

## 网络配置

### 网桥说明

- **br-pub**：公网网桥，用于需要公网访问的容器
- **br-nat**：内网网桥，用于内网隔离的容器

### 网桥配置示例

```bash
# 查看网桥
ip link show br-pub
ip link show br-nat

# 查看网桥 IP
ip addr show br-nat
```

### 容器网络配置

容器网络在创建时自动配置，基于 `VMConfig.nic_all`：

```python
from MainObject.Config.NICConfig import NICConfig

vm_conf.nic_all = {
    "eth0": NICConfig(
        ip4_addr="192.168.1.100",
        mac_addr="00:16:3e:xx:xx:xx",
        dns_addr=["8.8.8.8", "8.8.4.4"]
    )
}
```

---

## 故障排查

### 连接失败

**问题**：无法连接到 LXD 服务器

**解决方案**：
1. 检查服务器 IP 和端口（8443）
2. 检查防火墙是否开放 8443 端口
3. 检查证书路径是否正确
4. 测试网络连通性：`ping <server_ip>`

```bash
# 在服务器上检查 LXD 状态
systemctl status lxd
lxc list

# 检查 API 监听
netstat -tlnp | grep 8443
```

### 证书错误

**问题**：证书验证失败

**解决方案**：
1. 确认证书文件存在且可读
2. 重新生成证书：`sudo bash setup_lxd.sh`
3. 检查证书是否已添加到信任列表：`lxc config trust list`

### 容器创建失败

**问题**：容器创建失败

**解决方案**：
1. 检查模板文件是否存在
2. 检查存储池空间：`lxc storage info default`
3. 检查网桥是否正常：`ip link show br-nat`
4. 查看 LXD 日志：`journalctl -u lxd -n 50`

### 网络不通

**问题**：容器网络无法访问

**解决方案**：
1. 检查网桥状态：`ip link show br-nat`
2. 检查容器网络配置：`lxc config show <container>`
3. 检查路由表：`ip route`
4. 测试容器内网络：`lxc exec <container> -- ping 8.8.8.8`

---

## 高级配置

### 自定义存储池

```bash
# 创建 ZFS 存储池
lxc storage create zfs-pool zfs size=100GB

# 创建 Btrfs 存储池
lxc storage create btrfs-pool btrfs size=100GB
```

### 配置资源限制

```python
# 在 VMConfig 中配置
vm_conf.cpu_num = 4      # 4 核 CPU
vm_conf.ram_num = 8      # 8 GB 内存
vm_conf.hdd_num = 50     # 50 GB 磁盘
```

### 快照管理

```python
# 创建快照（使用备份功能）
server.VMBackup("container-name", "snapshot-description")

# 恢复快照
server.Restores("container-name", "backup-file.7z")
```

---

## 性能优化

### 1. 使用高性能存储

推荐使用 ZFS 或 Btrfs 存储池，而不是 dir：

```bash
lxc storage create fast-pool zfs
```

### 2. 调整容器资源

根据实际需求调整 CPU 和内存限制，避免过度分配。

### 3. 网络优化

使用 macvlan 或 SR-IOV 提高网络性能：

```python
# 在设备配置中使用 macvlan
devices["eth0"]["nictype"] = "macvlan"
```

---

## 安全建议

1. **使用 TLS 证书**：始终使用证书认证，不要禁用验证
2. **限制 API 访问**：配置防火墙只允许特定 IP 访问 8443 端口
3. **定期更新**：保持 LXD 和系统更新到最新版本
4. **备份证书**：妥善保管客户端证书和密钥
5. **使用非特权容器**：默认使用非特权容器，提高安全性

---

## 参考资料

- [LXD 官方文档](https://linuxcontainers.org/lxd/docs/latest/)
- [pylxd 文档](https://pylxd.readthedocs.io/)
- [LXD REST API](https://linuxcontainers.org/lxd/docs/latest/rest-api/)

---

## 常见问题

### Q: 可以在 Windows 上运行 LXD 服务器吗？

A: 不可以。LXD 只能在 Linux 上运行。但是可以在 Windows 上运行客户端（Python 脚本）来管理远程 Linux 服务器上的 LXD。

### Q: 与 Docker 有什么区别？

A: LXD 提供系统容器（类似轻量级虚拟机），而 Docker 提供应用容器。LXD 容器可以运行完整的 Linux 系统，包括 systemd、SSH 等。

### Q: 如何迁移容器到另一台服务器？

A: 使用备份和恢复功能，或者使用 LXD 的内置迁移功能：

```bash
lxc copy server1:container server2:container
```

### Q: 支持 GPU 透传吗？

A: LXD 支持 GPU 透传，但本项目暂未实现。可以手动配置：

```bash
lxc config device add container gpu gpu
```

---

## 更新日志

### v1.0.0 (2025-01-XX)

- ✅ 初始版本
- ✅ 支持远程 LXD 管理
- ✅ 容器创建、配置、删除
- ✅ 网络和存储管理
- ✅ 备份和恢复功能
- ✅ TLS 证书认证

---

## 许可证

本项目遵循项目主许可证。
