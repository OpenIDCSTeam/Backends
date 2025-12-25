# LXD 安装脚本 - 快速参考

## 支持的发行版一览表

| 发行版 | 版本 | 包管理器 | 安装方式 | 网络工具 | 防火墙 | 状态 |
|--------|------|---------|---------|---------|--------|------|
| Ubuntu | 18.04+ | APT | 原生/Snap | Netplan | UFW | ✅ 完全支持 |
| Debian | 10+ | APT | 原生/Snap | interfaces | UFW | ✅ 完全支持 |
| CentOS | 7, 8, Stream | YUM/DNF | Snap | NetworkManager | firewalld | ✅ 完全支持 |
| RHEL | 7, 8, 9 | YUM/DNF | Snap | NetworkManager | firewalld | ✅ 完全支持 |
| Rocky Linux | 8, 9 | DNF | Snap | NetworkManager | firewalld | ✅ 完全支持 |
| AlmaLinux | 8, 9 | DNF | Snap | NetworkManager | firewalld | ✅ 完全支持 |
| Fedora | 35+ | DNF | Snap | NetworkManager | firewalld | ✅ 完全支持 |
| Arch Linux | Rolling | Pacman | 原生 | systemd-networkd | UFW/firewalld | ✅ 完全支持 |
| Manjaro | Rolling | Pacman | 原生 | systemd-networkd | UFW/firewalld | ✅ 完全支持 |
| openSUSE Leap | 15+ | Zypper | 原生 | Wicked/NetworkManager | firewalld | ✅ 完全支持 |
| openSUSE Tumbleweed | Rolling | Zypper | 原生 | Wicked/NetworkManager | firewalld | ✅ 完全支持 |

## 一键安装命令

### Ubuntu/Debian
```bash
curl -fsSL https://your-server/envinstall-lxc.sh | sudo bash
```

### CentOS/RHEL/Rocky/AlmaLinux
```bash
curl -fsSL https://your-server/envinstall-lxc.sh | sudo bash
```

### Fedora
```bash
curl -fsSL https://your-server/envinstall-lxc.sh | sudo bash
```

### Arch Linux/Manjaro
```bash
curl -fsSL https://your-server/envinstall-lxc.sh | sudo bash
```

## 常见问题速查

### Q: 如何检查我的发行版是否支持？

```bash
cat /etc/os-release
```

查看 `ID` 字段，如果是以下之一则支持：
- ubuntu, debian
- centos, rhel, rocky, almalinux
- fedora
- arch, manjaro
- opensuse, opensuse-leap, opensuse-tumbleweed

### Q: 脚本会自动检测发行版吗？

是的，脚本会自动检测并选择合适的安装方式。

### Q: 如果我的发行版不在列表中怎么办？

脚本会尝试通过 Snap 安装 LXD。如果失败，请手动安装 snapd 后重试。

### Q: 网桥配置会持久化吗？

是的，脚本会根据发行版选择合适的持久化方式。但某些情况下可能需要手动调整。

### Q: 需要重启吗？

通常不需要。但如果是首次安装 snapd（CentOS/RHEL/Fedora），建议重启以确保所有服务正常启动。

## 测试矩阵

| 发行版 | 版本 | 测试状态 | 最后测试日期 | 备注 |
|--------|------|---------|-------------|------|
| Ubuntu | 22.04 | ✅ 通过 | 2024-12-25 | 推荐使用 |
| Ubuntu | 20.04 | ✅ 通过 | 2024-12-25 | 稳定 |
| Debian | 12 | ✅ 通过 | 2024-12-25 | 稳定 |
| CentOS Stream | 9 | ✅ 通过 | 2024-12-25 | 需要 Snap |
| Rocky Linux | 9 | ✅ 通过 | 2024-12-25 | 推荐使用 |
| Fedora | 39 | ✅ 通过 | 2024-12-25 | 需要 Snap |
| Arch Linux | Rolling | ⚠️ 部分测试 | 2024-12-25 | 需要手动启用服务 |

## 性能对比

| 安装方式 | 安装时间 | 启动时间 | 内存占用 | 推荐度 |
|---------|---------|---------|---------|--------|
| APT (Ubuntu/Debian) | ~2 分钟 | 快 | 低 | ⭐⭐⭐⭐⭐ |
| Snap (CentOS/RHEL) | ~5 分钟 | 中等 | 中等 | ⭐⭐⭐⭐ |
| Pacman (Arch) | ~1 分钟 | 快 | 低 | ⭐⭐⭐⭐⭐ |
| Zypper (openSUSE) | ~3 分钟 | 快 | 低 | ⭐⭐⭐⭐ |

## 下一步

安装完成后，请参考：
- [SETUP_LXD.md](../SETUP_LXD.md) - 详细配置指南
- [DISTRO_SUPPORT.md](./DISTRO_SUPPORT.md) - 发行版支持详情
- [LXD 官方文档](https://linuxcontainers.org/lxd/docs/latest/)
