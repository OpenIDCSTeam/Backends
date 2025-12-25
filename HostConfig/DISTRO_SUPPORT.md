# LXD 安装脚本 - 多发行版支持说明

## 概述

`envinstall-lxc.sh` 脚本现已支持多个主流 Linux 发行版，能够自动检测系统并使用相应的包管理器安装和配置 LXD。

## 支持的发行版

### 1. Debian 系列
- **Ubuntu** (18.04+, 20.04, 22.04, 24.04)
- **Debian** (10+, 11, 12)
- **Linux Mint**
- **Pop!_OS**

**包管理器**: APT (apt-get)
**网络配置**: Netplan (Ubuntu 18.04+) 或 /etc/network/interfaces (旧版)
**防火墙**: UFW

### 2. Red Hat 系列
- **CentOS** (7, 8, Stream)
- **RHEL** (Red Hat Enterprise Linux 7, 8, 9)
- **Rocky Linux** (8, 9)
- **AlmaLinux** (8, 9)

**包管理器**: YUM (CentOS 7) 或 DNF (CentOS 8+, RHEL 8+)
**网络配置**: NetworkManager 或 /etc/sysconfig/network-scripts/
**防火墙**: firewalld

### 3. Fedora
- **Fedora** (35+)

**包管理器**: DNF
**网络配置**: NetworkManager
**防火墙**: firewalld

### 4. Arch 系列
- **Arch Linux**
- **Manjaro**

**包管理器**: Pacman
**网络配置**: systemd-networkd
**防火墙**: UFW 或 firewalld (可选)

### 5. openSUSE 系列
- **openSUSE Leap**
- **openSUSE Tumbleweed**
- **SLES** (SUSE Linux Enterprise Server)

**包管理器**: Zypper
**网络配置**: Wicked 或 NetworkManager
**防火墙**: firewalld

## 安装方式

脚本会根据发行版选择最佳的安装方式：

### 方式 1: 原生包管理器
- Ubuntu/Debian: 使用 APT 安装 `lxd` 包
- Arch Linux: 使用 Pacman 安装 `lxd` 包
- openSUSE: 使用 Zypper 安装 `lxd` 包

### 方式 2: Snap 包管理器
- CentOS/RHEL/Rocky/AlmaLinux: 先安装 snapd，再通过 snap 安装 LXD
- Fedora: 先安装 snapd，再通过 snap 安装 LXD
- 其他不支持的发行版: 尝试通过 snap 安装

## 网络配置差异

不同发行版使用不同的网络配置工具：

| 发行版 | 网络配置工具 | 配置文件位置 |
|--------|-------------|-------------|
| Ubuntu 18.04+ | Netplan | /etc/netplan/*.yaml |
| Debian/旧版Ubuntu | interfaces | /etc/network/interfaces |
| CentOS/RHEL | NetworkManager | nmcli 命令 |
| CentOS/RHEL (传统) | network-scripts | /etc/sysconfig/network-scripts/ |
| Arch Linux | systemd-networkd | /etc/systemd/network/ |
| Fedora | NetworkManager | nmcli 命令 |

## 防火墙配置

脚本会自动检测并配置防火墙：

| 发行版 | 防火墙工具 | 配置命令 |
|--------|-----------|---------|
| Ubuntu/Debian | UFW | `ufw allow 8443/tcp` |
| CentOS/RHEL/Fedora | firewalld | `firewall-cmd --add-port=8443/tcp` |
| Arch Linux | UFW/firewalld | 根据安装情况自动选择 |

## 使用方法

### 基本使用

```bash
# 下载脚本
wget https://your-server/envinstall-lxc.sh

# 添加执行权限
chmod +x envinstall-lxc.sh

# 以 root 权限运行
sudo bash envinstall-lxc.sh
```

### 自动化安装（无交互）

如果需要在自动化脚本中使用，可以预设网桥名称：

```bash
# 使用默认网桥名称
echo -e "br-pub\nbr-nat" | sudo bash envinstall-lxc.sh

# 或者使用自定义名称
echo -e "public-bridge\nprivate-bridge" | sudo bash envinstall-lxc.sh
```

## 故障排除

### 1. Snap 安装失败

**问题**: CentOS/RHEL 上 snap 安装失败

**解决方案**:
```bash
# 手动安装 snapd
sudo yum install -y epel-release
sudo yum install -y snapd
sudo systemctl enable --now snapd.socket
sudo ln -s /var/lib/snapd/snap /snap

# 重新运行脚本
sudo bash envinstall-lxc.sh
```

### 2. 网桥配置未持久化

**问题**: 重启后网桥消失

**解决方案**:

**Ubuntu/Debian (Netplan)**:
```bash
sudo nano /etc/netplan/99-lxd-bridges.yaml
sudo netplan apply
```

**CentOS/RHEL (NetworkManager)**:
```bash
sudo nmcli connection show
sudo nmcli connection up br-pub
sudo nmcli connection up br-nat
```

**Arch Linux (systemd-networkd)**:
```bash
sudo systemctl enable systemd-networkd
sudo systemctl restart systemd-networkd
```

### 3. 防火墙阻止连接

**问题**: 无法从远程连接到 LXD API

**解决方案**:

**Ubuntu/Debian**:
```bash
sudo ufw status
sudo ufw allow 8443/tcp
sudo ufw reload
```

**CentOS/RHEL/Fedora**:
```bash
sudo firewall-cmd --list-ports
sudo firewall-cmd --permanent --add-port=8443/tcp
sudo firewall-cmd --reload
```

**手动 iptables**:
```bash
sudo iptables -A INPUT -p tcp --dport 8443 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

### 4. SELinux 问题 (CentOS/RHEL)

**问题**: SELinux 阻止 LXD 操作

**临时解决方案**:
```bash
sudo setenforce 0
```

**永久解决方案**:
```bash
sudo nano /etc/selinux/config
# 设置 SELINUX=permissive 或 SELINUX=disabled
sudo reboot
```

## 验证安装

安装完成后，验证 LXD 是否正常工作：

```bash
# 检查 LXD 版本
lxd --version

# 检查 LXD 服务状态
sudo systemctl status lxd.socket  # Arch Linux
sudo systemctl status snap.lxd.daemon  # Snap 安装

# 列出容器
lxc list

# 测试创建容器
lxc launch ubuntu:22.04 test-container
lxc list
lxc delete test-container --force
```

## 已知限制

1. **CentOS 7**: 需要较新的内核版本才能完全支持 LXD 的所有特性
2. **Arch Linux**: 需要手动启用 lxd.socket 服务
3. **openSUSE**: 某些版本可能需要额外配置 AppArmor
4. **所有发行版**: 网桥配置可能需要根据实际网络环境调整

## 贡献

如果您在其他发行版上测试成功，或发现问题，欢迎提交 Issue 或 Pull Request。

## 参考资料

- [LXD 官方文档](https://linuxcontainers.org/lxd/docs/latest/)
- [Snap 安装指南](https://snapcraft.io/docs/installing-snapd)
- [NetworkManager 文档](https://networkmanager.dev/)
- [systemd-networkd 文档](https://www.freedesktop.org/software/systemd/man/systemd-networkd.html)
