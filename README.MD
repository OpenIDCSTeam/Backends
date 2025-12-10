
# Open IDC Service 开源IDC受控端

<p align="center">使用统一Web界面和API来管理不同虚拟化平台上的虚拟机，支持对接其他平台</p>

<p align="center"><a href="APIDOC.md">API文档</a></p>

![QQ20251210-165038.jpg](Screenshot/QQ20251210-165038.jpg)

## 功能概述 / Introduction


- 多主机管理：支持添加和管理多个虚拟化主机
- 虚拟机管理：创建、配置、启动、停止、删除虚拟机
- 网络IP配置：IP地址分配、NAT端口转发、反向代理配置
- 远程IP访问：通过Web浏览器VNC访问虚拟机桌面
- 状态与监控：实时监控主机和虚拟机的资源使用情况
- 任务与调度：定时任务和日志记录

## 平台支持 / Support Platforms

| 平台 | 状态 | 操作系统 | 架构 |
|------|------|----------|------|
| VMware Workstation | ✅ 已实现 | Windows | x86_64 |
| Hyper-V | 🚧 计划中 | Windows | x86_64 |
| Proxmox VE | 🚧 计划中 | Linux, Windows | x86_64, ARM64 |
| VirtualBox | 🚧 计划中 | Linux, Windows | x86_64, ARM64 |
| vSphere ESXi | 🚧 计划中 | Linux, Windows | x86_64 |
| VMware Fusion | 🚧 计划中 | macOS | x86_64, ARM64 |
| Docker/Podman | 🚧 计划中 | Linux, Windows, macOS | x86_64, ARM64 |
| LXC/LXD | 🚧 计划中 | Linux | x86_64, ARM64 |

## 调试开发 / Development

1. 安装依赖: `pip install -r HostConfig/pipinstall.txt`
2. 启动服务: `python HostServer.py`

服务默认运行在 `http://0.0.0.0:1880`，首次启动会自动生成访问Token，请妥善保管。

## 配置说明 / Configure

- 主机配置保存在 `DataSaving/` 目录
- 日志文件按主机名分别保存
- 虚拟机文件存储路径在主机配置中指定

## 参考内容 / Reference
 - 受控端Web和魔方对接插件风格与部分代码基于： 『魔方财务-LXD对接服务器』项目。原作者: xkatld，原项目地址: https://github.com/xkatld/zjmf-lxd-server

