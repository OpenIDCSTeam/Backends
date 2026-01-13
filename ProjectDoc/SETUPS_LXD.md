# LXD 容器管理 - 快速开始

<div align="center">

5 分钟快速部署 LXD 容器管理环境

[步骤 1：服务端配置](#步骤-1服务端配置linux-服务器) • [步骤 2：客户端配置](#步骤-2客户端配置windows) • [步骤 3：测试连接](#步骤-3测试连接) • [步骤 4：创建容器](#步骤-4创建第一个容器)

</div>

## 🚀 5 分钟快速部署

### 步骤 1：服务端配置（Linux 服务器）

```bash
# 1. 上传脚本到服务器
scp setup_lxd.sh user@192.168.1.100:/tmp/

# 2. SSH 登录服务器
ssh user@192.168.1.100

# 3. 运行初始化脚本
cd /tmp
sudo bash setup_lxd.sh

# 4. 记录输出的配置信息
# - LXD API 地址
# - 网桥名称
# - 证书路径
```

### 步骤 2：客户端配置（Windows）

```bash
# 1. 安装 Python 依赖
pip install -r pipinstall-esx.txt

# 2. 从服务器下载证书
scp user@192.168.1.100:/tmp/lxd_certs/client.crt C:\certs\
scp user@192.168.1.100:/tmp/lxd_certs/client.key C:\certs\
```

### 步骤 3：测试连接

创建测试脚本 `test_lxd.py`：

```python
from HostServer.LXContainer import HostServer
from MainObject.Config.HSConfig import HSConfig

# 配置服务器信息
config = HSConfig(
    server_name="my-lxd-server",
    server_addr="192.168.1.100",  # 替换为你的服务器 IP
    launch_path="C:\\certs",  # 证书目录
    network_pub="br-pub",
    network_nat="br-nat",
    system_path="/var/lib/lxd/containers",
    images_path="/path/to/templates",
    backup_path="/path/to/backups"
)

# 创建服务器实例
server = HostServer(config)

# 连接到 LXD
result = server.HSLoader()
print(f"连接结果: {result.message}")

# 扫描现有容器
scan_result = server.VMDetect()
print(f"扫描结果: {scan_result.message}")
```

运行测试：

```bash
python test_lxd.py
```

### 步骤 4：创建第一个容器

```python
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.VMPowers import VMPowers

# 创建容器配置
vm_conf = VMConfig(
    vm_uuid="test-container-001",
    os_name="ubuntu-22.04.tar.gz",  # 确保模板文件存在
    cpu_num=2,
    mem_num=4,  # GB
    hdd_num=20  # GB
)

# 创建容器
result = server.VMCreate(vm_conf)
print(f"创建结果: {result.message}")

# 启动容器
server.VMPowers("test-container-001", VMPowers.S_START)
print("容器已启动！")
```

---

## 📊 架构对比

### 原方案（LXC + python3-lxc）

```
┌─────────────────┐
│  Linux 服务器    │
│                 │
│  Python Script  │  ← 只能本地运行
│  + python3-lxc  │
│  + LXC          │
└─────────────────┘
```

**限制**：
| 限制项 | 说明 |
|--------|------|
| ❌ | 只能在 Linux 本地运行 |
| ❌ | 无法从 Windows 远程管理 |
| ❌ | 需要 root 权限 |

### 新方案（LXD + pylxd）

```
┌─────────────────┐         HTTPS          ┌─────────────────┐
│  Windows 客户端  │ ◄──────────────────► │  Linux 服务器    │
│                 │      (8443 端口)       │                 │
│  Python Script  │                        │   LXD Daemon    │
│  + pylxd       │                        │   + Containers  │
└─────────────────┘                        └─────────────────┘
```

**优势**：
| 优势项 | 说明 |
|--------|------|
| ✅ | 跨平台（Windows/Linux/macOS） |
| ✅ | 远程管理（通过网络） |
| ✅ | 安全认证（TLS 证书） |
| ✅ | 完整的 REST API |

---

## 🔧 常用操作

### 容器管理

```python
# 列出所有容器
scan_result = server.VMDetect()

# 启动容器
server.VMPowers("container-name", VMPowers.S_START)

# 停止容器
server.VMPowers("container-name", VMPowers.H_CLOSE)

# 重启容器
server.VMPowers("container-name", VMPowers.S_RESET)

# 删除容器
server.VMDelete("container-name")
```

### 资源管理

```python
# 更新容器配置
vm_conf = server.VMSelect("container-name")
vm_conf.cpu_num = 4  # 修改为 4 核
vm_conf.mem_num = 8  # 修改为 8 GB

old_conf = deepcopy(vm_conf)
server.VMUpdate(vm_conf, old_conf)
```

### 备份恢复

```python
# 备份容器
server.VMBackup("container-name", "每日备份")

# 恢复容器
server.Restores("container-name", "backup-20250125.7z")
```

---

## 🐛 故障排查

### 问题 1：连接失败

```
错误: Failed to connect to LXD: Connection refused
```

**解决方案**：

```bash
# 在服务器上检查 LXD 状态
systemctl status lxd

# 检查端口监听
netstat -tlnp | grep 8443

# 检查防火墙
sudo ufw status
sudo ufw allow 8443/tcp
```

### 问题 2：证书错误

```
错误: Client certificates not found
```

**解决方案**：

1. 确认证书路径正确
2. 检查证书文件权限
3. 重新生成证书：`sudo bash setup_lxd.sh`

### 问题 3：容器创建失败

```
错误: Failed to create container
```

**解决方案**：

```bash
# 检查存储池
lxc storage list
lxc storage info default

# 检查网桥
ip link show br-nat

# 查看日志
journalctl -u lxd -n 50
```

---

## ✅ 部署检查清单

部署前请确认：

- [ ] Linux 服务器已安装 LXD
- [ ] 防火墙已开放 8443 端口
- [ ] 客户端已安装 pylxd
- [ ] 证书已正确配置
- [ ] 网桥已创建（br-pub, br-nat）
- [ ] 存储池已配置
- [ ] 模板文件已准备

---

## 📚 更多信息

- **详细文档**：[README_LXD.md](README_LXD.md)
- **LXD 官方文档**：https://linuxcontainers.org/lxd/
- **pylxd 文档**：https://pylxd.readthedocs.io/

---

<div align="center">

## 🎉 完成！

现在你可以从 Windows 客户端远程管理 Linux 服务器上的 LXD 容器了！

如有问题，请查看 [README_LXD.md](README_LXD.md) 获取详细帮助。

</div>
