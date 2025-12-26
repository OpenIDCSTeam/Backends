# LXD 安装脚本 - 多发行版支持说明

<div align="center">

`envinstall-lxc.sh` 脚本现已支持多个主流 Linux 发行版，自动检测系统并使用相应的包管理器安装和配置 LXD

[支持的发行版](#支持的发行版) • [安装方式](#安装方式) • [故障排除](#故障排除) • [验证安装](#验证安装)

</div>

## 📋 概述

本文档说明 LXD 安装脚本 `envinstall-lxc.sh` 对不同 Linux 发行版的支持情况，以及如何在各种发行版上使用该脚本安装 LXD。

脚本特性：
- ✅ 自动检测 Linux 发行版
- ✅ 智能选择包管理器
- ✅ 自动配置网络和防火墙
- ✅ 支持多种安装方式（原生包管理器 / Snap）
- ✅ 详细的错误处理和日志

---

## 🐧 支持的发行版

### Debian 系列

| 发行版 | 版本 | 包管理器 | 网络配置 | 防火墙 |
|--------|------|----------|----------|--------|
| **Ubuntu** | 18.04+, 20.04, 22.04, 24.04 | APT | Netplan (18.04+) / interfaces | UFW |
| **Debian** | 10+, 11, 12 | APT | interfaces | UFW |
| **Linux Mint** | 最新版 | APT | Netplan | UFW |
| **Pop!_OS** | 最新版 | APT | Netplan | UFW |

### Red Hat 系列

| 发行版 | 版本 | 包管理器 | 网络配置 | 防火墙 |
|--------|------|----------|----------|--------|
| **CentOS** | 7, 8, Stream | YUM/DNF | NetworkManager | firewalld |
| **RHEL** | 7, 8, 9 | YUM/DNF | NetworkManager | firewalld |
| **Rocky Linux** | 8, 9 | DNF | NetworkManager | firewalld |
| **AlmaLinux** | 8, 9 | DNF | NetworkManager | firewalld |

### 其他发行版

| 发行版 | 版本 | 包管理器 | 网络配置 | 防火墙 |
|--------|------|----------|----------|--------|
| **Fedora** | 35+ | DNF | NetworkManager | firewalld |
| **Arch Linux** | 滚动更新 | Pacman | systemd-networkd | UFW/firewalld |
| **Manjaro** | 滚动更新 | Pacman | systemd-networkd | UFW/firewalld |
| **openSUSE Leap** | 15.x | Zypper | Wicked/NM | firewalld |
| **openSUSE Tumbleweed** | 滚动更新 | Zypper | Wicked/NM | firewalld |
| **SLES** | 12.x, 15.x | Zypper | Wicked | firewalld |

---

## 📦 安装方式

脚本会根据发行版自动选择最佳的安装方式：

### 方式 1: 原生包管理器

使用发行版自带的包管理器安装 LXD：

| 发行版 | 安装命令 |
|--------|----------|
| Ubuntu/Debian | `apt-get install lxd` |
| Arch Linux | `pacman -S lxd` |
| openSUSE | `zypper install lxd` |

**优点**: 安装快，集成度高
**缺点**: 版本可能不是最新

### 方式 2: Snap 包管理器

通过 Snap 安装最新版本的 LXD：

| 发行版 | 前置步骤 |
|--------|----------|
| CentOS/RHEL/Rocky/AlmaLinux | 先安装 snapd |
| Fedora | 先安装 snapd |
| 其他不支持的发行版 | 尝试通过 snap 安装 |

**优点**: 版本最新，官方支持
**缺点**: 需要额外安装 snapd

---

## 🌐 网络配置差异

不同发行版使用不同的网络配置工具，脚本会自动适配：

| 发行版 | 网络配置工具 | 配置文件位置 |
|--------|-------------|-------------|
| Ubuntu 18.04+ | Netplan | `/etc/netplan/*.yaml` |
| Debian/旧版Ubuntu | interfaces | `/etc/network/interfaces` |
| CentOS/RHEL | NetworkManager | `nmcli` 命令 |
| CentOS/RHEL (传统) | network-scripts | `/etc/sysconfig/network-scripts/` |
| Arch Linux | systemd-networkd | `/etc/systemd/network/` |
| Fedora | NetworkManager | `nmcli` 命令 |
| openSUSE | Wicked | `/etc/sysconfig/network/` |

---

## 🔥 防火墙配置

脚本会自动检测并配置防火墙：

| 发行版 | 防火墙工具 | 配置命令 |
|--------|-----------|---------|
| Ubuntu/Debian | UFW | `ufw allow 8443/tcp` |
| CentOS/RHEL/Fedora | firewalld | `firewall-cmd --add-port=8443/tcp` |
| Arch Linux | UFW/firewalld | 根据安装情况自动选择 |

---

## 🚀 使用方法

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

在自动化脚本中预设网桥名称：

```bash
# 使用默认网桥名称
echo -e "br-pub\nbr-nat" | sudo bash envinstall-lxc.sh

# 使用自定义名称
echo -e "public-bridge\nprivate-bridge" | sudo bash envinstall-lxc.sh
```

---

## 🔧 故障排除

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

**解决方案 - Ubuntu/Debian (Netplan)**:
```bash
sudo nano /etc/netplan/99-lxd-bridges.yaml
sudo netplan apply
```

**解决方案 - CentOS/RHEL (NetworkManager)**:
```bash
sudo nmcli connection show
sudo nmcli connection up br-pub
sudo nmcli connection up br-nat
```

**解决方案 - Arch Linux (systemd-networkd)**:
```bash
sudo systemctl enable systemd-networkd
sudo systemctl restart systemd-networkd
```

### 3. 防火墙阻止连接

**问题**: 无法从远程连接到 LXD API

**解决方案 - Ubuntu/Debian**:
```bash
sudo ufw status
sudo ufw allow 8443/tcp
sudo ufw reload
```

**解决方案 - CentOS/RHEL/Fedora**:
```bash
sudo firewall-cmd --list-ports
sudo firewall-cmd --permanent --add-port=8443/tcp
sudo firewall-cmd --reload
```

**解决方案 - 手动 iptables**:
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

---

## ✅ 验证安装

安装完成后，使用以下命令验证 LXD 是否正常工作：

```bash
# 检查 LXD 版本
lxd --version

# 检查 LXD 服务状态
sudo systemctl status lxd.socket          # Arch Linux
sudo systemctl status snap.lxd.daemon     # Snap 安装

# 列出容器
lxc list

# 测试创建容器
lxc launch ubuntu:22.04 test-container
lxc list
lxc delete test-container --force
```

---

## ⚠️ 已知限制

| 发行版 | 限制 |
|--------|------|
| CentOS 7 | 需要较新的内核版本才能完全支持 LXD 的所有特性 |
| Arch Linux | 需要手动启用 lxd.socket 服务 |
| openSUSE | 某些版本可能需要额外配置 AppArmor |
| 所有发行版 | 网桥配置可能需要根据实际网络环境调整 |

---

## 📚 参考资料

- [LXD 官方文档](https://linuxcontainers.org/lxd/docs/latest/)
- [Snap 安装指南](https://snapcraft.io/docs/installing-snapd)
- [NetworkManager 文档](https://networkmanager.dev/)
- [systemd-networkd 文档](https://www.freedesktop.org/software/systemd/man/systemd-networkd.html)

---

<div align="center">

如果您在其他发行版上测试成功，或发现问题，欢迎提交 Issue 或 Pull Request

</div>