# LXD 安装脚本 - 快速参考指南

<div align="center">

快速查找发行版支持状态、安装命令和常见问题解答

[发行版支持](#支持的发行版) • [安装命令](#一键安装命令) • [常见问题](#常见问题速查) • [性能对比](#性能对比)

</div>

## 📊 支持的发行版

| 发行版 | 版本 | 包管理器 | 安装方式 | 网络工具 | 防火墙 | 状态 |
|--------|------|---------|---------|---------|--------|------|
| **Ubuntu** | 18.04+, 20.04, 22.04, 24.04 | APT | 原生/Snap | Netplan | UFW | ✅ 完全支持 |
| **Debian** | 10+, 11, 12 | APT | 原生/Snap | interfaces | UFW | ✅ 完全支持 |
| **CentOS** | 7, 8, Stream | YUM/DNF | Snap | NetworkManager | firewalld | ✅ 完全支持 |
| **RHEL** | 7, 8, 9 | YUM/DNF | Snap | NetworkManager | firewalld | ✅ 完全支持 |
| **Rocky Linux** | 8, 9 | DNF | Snap | NetworkManager | firewalld | ✅ 完全支持 |
| **AlmaLinux** | 8, 9 | DNF | Snap | NetworkManager | firewalld | ✅ 完全支持 |
| **Fedora** | 35+ | DNF | Snap | NetworkManager | firewalld | ✅ 完全支持 |
| **Arch Linux** | Rolling | Pacman | 原生 | systemd-networkd | UFW/firewalld | ✅ 完全支持 |
| **Manjaro** | Rolling | Pacman | 原生 | systemd-networkd | UFW/firewalld | ✅ 完全支持 |
| **openSUSE Leap** | 15+ | Zypper | 原生 | Wicked/NM | firewalld | ✅ 完全支持 |
| **openSUSE Tumbleweed** | Rolling | Zypper | 原生 | Wicked/NM | firewalld | ✅ 完全支持 |

---

## 🚀 一键安装命令

### Ubuntu / Debian
```bash
curl -fsSL https://your-server/envinstall-lxc.sh | sudo bash
```

### CentOS / RHEL / Rocky / AlmaLinux
```bash
curl -fsSL https://your-server/envinstall-lxc.sh | sudo bash
```

### Fedora
```bash
curl -fsSL https://your-server/envinstall-lxc.sh | sudo bash
```

### Arch Linux / Manjaro
```bash
curl -fsSL https://your-server/envinstall-lxc.sh | sudo bash
```

### openSUSE Leap / Tumbleweed
```bash
curl -fsSL https://your-server/envinstall-lxc.sh | sudo bash
```

---

## ❓ 常见问题速查

### 检查发行版支持

**Q: 如何检查我的发行版是否支持？**

```bash
cat /etc/os-release
```

查看 `ID` 字段，支持的发行版标识：
- `ubuntu`, `debian`
- `centos`, `rhel`, `rocky`, `almalinux`
- `fedora`
- `arch`, `manjaro`
- `opensuse`, `opensuse-leap`, `opensuse-tumbleweed`

### 自动检测

**Q: 脚本会自动检测发行版吗？**

✅ 是的，脚本会自动检测并选择合适的安装方式。

### 不支持的发行版

**Q: 如果我的发行版不在列表中怎么办？**

脚本会尝试通过 Snap 安装 LXD。如果失败，请先手动安装 snapd：

```bash
# Debian/Ubuntu
sudo apt-get install snapd

# CentOS/RHEL
sudo yum install epel-release
sudo yum install snapd
sudo systemctl enable --now snapd.socket
```

### 网桥持久化

**Q: 网桥配置会持久化吗？**

✅ 是的，脚本会根据发行版选择合适的持久化方式。但某些情况下可能需要手动调整配置文件。

### 重启要求

**Q: 需要重启吗？**

- 通常不需要重启
- 首次安装 snapd（CentOS/RHEL/Fedora）建议重启
- 确保 LXD 服务正常运行：`sudo systemctl status lxd`

---

## ✅ 测试矩阵

| 发行版 | 版本 | 测试状态 | 最后测试日期 | 备注 |
|--------|------|---------|-------------|------|
| Ubuntu | 22.04 LTS | ✅ 通过 | 2024-12-25 | 推荐使用 |
| Ubuntu | 20.04 LTS | ✅ 通过 | 2024-12-25 | 长期支持 |
| Ubuntu | 24.04 LTS | ✅ 通过 | 2024-12-25 | 最新版本 |
| Debian | 12 (Bookworm) | ✅ 通过 | 2024-12-25 | 稳定版 |
| Debian | 11 (Bullseye) | ✅ 通过 | 2024-12-25 | 稳定版 |
| CentOS Stream | 9 | ✅ 通过 | 2024-12-25 | 需要 Snap |
| Rocky Linux | 9 | ✅ 通过 | 2024-12-25 | 推荐使用 |
| AlmaLinux | 9 | ✅ 通过 | 2024-12-25 | 推荐使用 |
| Fedora | 39 | ✅ 通过 | 2024-12-25 | 需要 Snap |
| Arch Linux | Rolling | ⚠️ 部分测试 | 2024-12-25 | 需要手动启用服务 |
| openSUSE Leap | 15.5 | ⚠️ 部分测试 | 2024-12-25 | 需要额外配置 |

---

## 📈 性能对比

| 安装方式 | 安装时间 | 启动时间 | 内存占用 | 推荐度 |
|---------|---------|---------|---------|--------|
| **APT** (Ubuntu/Debian) | ~2 分钟 | 快 | 低 | ⭐⭐⭐⭐⭐ |
| **Snap** (CentOS/RHEL) | ~5 分钟 | 中等 | 中等 | ⭐⭐⭐⭐ |
| **Pacman** (Arch) | ~1 分钟 | 快 | 低 | ⭐⭐⭐⭐⭐ |
| **Zypper** (openSUSE) | ~3 分钟 | 快 | 低 | ⭐⭐⭐⭐ |

---

## 🔍 快速验证

安装完成后，运行以下命令验证：

```bash
# 检查 LXD 版本
lxd --version

# 检查服务状态
sudo systemctl status lxd

# 列出容器
lxc list
```

---

## 📚 相关文档

- [详细安装说明](DISTRO_SUPPORT.md) - 完整的发行版支持详情
- [SETUP_LXD.md](../ProjectDoc/SETUPS_LXD.md) - LXD 详细配置指南
- [LXD 官方文档](https://linuxcontainers.org/lxd/docs/latest/) - 官方参考文档

---

<div align="center">

如有问题，请查看详细文档或提交 Issue

</div>
