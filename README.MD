
# Open IDC Service 开源IDC受控端

<p align="center">使用统一Web界面和API来管理不同虚拟化平台上的虚拟机，支持对接其他平台</p>

<p align="center"><a href="ProjectDoc/APIDOC_ALL.md">API文档</a></p>

![QQ20251210-165038.jpg](Screenshot/QQ20251210-165038.jpg)

## 功能概述 / Introduction


- 多主机管理：支持添加以及管理多个类型的虚拟化主机平台
- 虚拟机管理：创建、配置、启动、停止、删除、修改虚拟机
- 网络IP配置：IP地址分配、NAT端口转发、WEB反向代理配置
- 远程IP访问：通过Web浏览器Vnc访问虚拟机桌面或者控制台
- 备份与还原：支持实时备份和还原虚拟机，并管理备份列表
- 挂载和卸载：支持挂载HDD和ISO文件到虚拟机以及管理挂载
- 用户与迁移：多用户共享虚拟机，转移虚拟机和硬盘所有权
- 状态与监控：实时监控主机和虚拟机的硬件资源的使用情况
- 任务与调度：定时任务和日志记录，支持管理用户资源限制

## 平台支持 / Support Platforms

| 平台                 | 状态    | 操作系统                  | 架构            |
|--------------------|-------|-----------------------|---------------|
| VMware Workstation | ✅ 已实现 | Windows               | x86_64        |
| LXC/D Environments | ℹ️ 开发中 | Windows, Linux        | x86_64, ARM64 |
| Docker/Podman/K8SC | ℹ️ 开发中 | Windows, Linux, macOS | x86_64, ARM64 |
| VMware vSphere ESX | ℹ️ 计划中 | Windows, Linux        | x86_64        |
| Proxmox VE Runtime | 🚧 计划中 | Windows, Linux        | x86_64, ARM64 |
| Oracle Virtual Box | 🚧 计划中 | Windows, Linux        | x86_64, ARM64 |
| Windows Hypervisor | 🚧 计划中 | Windows               | x86_64        |
| MEmu Game Emulator | 🚧 计划中 | Windows               | x86_64        |


## 调试开发 / Development

1. 安装依赖: `pip install -r requirements.txt`
2. 启动服务: `python HostServer.py`

服务默认运行在 `http://0.0.0.0:1880`，首次启动会自动生成访问Token，请妥善保管。

## 打包部署 / Build & Deploy

### 使用 Nuitka 打包（推荐）

Nuitka 可以将 Python 项目编译成独立的可执行文件，性能更好，体积更小。

**Windows 用户**：
```batch
cd nuitka_build
build_nuitka.bat
```

**Linux/Mac 用户**：
```bash
cd AllBuilder
chmod +x build_nuitkaui.sh
./build_nuitkaui.sh
```

打包完成后，可执行文件位于 `build_nuitka` 目录。

详细说明请查看：
- [快速开始指南](AllBuilder/NUITKA_QUICKSTART.md)
- [完整打包文档](AllBuilder/NUITKA_BUILD.md)

### 使用 cx_Freeze 打包

```bash
python HostBuilds.py build
```

## 配置说明 / Configure

- 主机配置保存在 `DataSaving/` 目录
- 日志文件按主机名分别保存
- 虚拟机文件存储路径在主机配置中指定

## 参考内容 / Reference
 - 受控端Web和魔方对接插件风格与部分代码基于： 『魔方财务-LXD对接服务器』项目。原作者: xkatld，原项目地址: https://github.com/xkatld/zjmf-lxd-server

